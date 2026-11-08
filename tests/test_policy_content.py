"""Content migration updates current policy without rewriting event history."""
import sqlite3
from pathlib import Path


def test_policy_content_migration_is_repeatable_and_preserves_history():
    root = Path(__file__).resolve().parents[1]
    script = (root / "migrations/ui_policy_content.sql").read_text(encoding="utf-8")
    with sqlite3.connect(":memory:") as db:
        db.row_factory = sqlite3.Row
        with sqlite3.connect(f"file:{(root / 'QLCC.db').as_posix()}?mode=ro", uri=True) as source:
            source.backup(db)
        prose_fields = {"locations": {"name", "description"},
                        "notifications": {"title", "content"},
                        "complaints": {"category", "content", "response"},
                        "maintenance_tickets": {"description"}}
        previous = {table: [dict(row) for row in db.execute(f"SELECT * FROM {table}")]
                    for table in prose_fields}
        db.executescript(script)
        for table, fields in prose_fields.items():
            expected = [{key: (value.replace("ban quản lý", "Ban quản lý").replace("Ban Quản Lý", "Ban quản lý")
                               if key in fields and isinstance(value, str) else value)
                         for key, value in row.items()} for row in previous[table]]
            assert [dict(row) for row in db.execute(f"SELECT * FROM {table}")] == expected
        answer = db.execute("SELECT answer FROM faq_knowledge_base WHERE question=?",
                            ("Làm sao để đăng ký gửi xe tháng?",)).fetchone()[0]
        for requirement in ("xe máy", "xe điện", "xe đạp", "không nhận ô tô", "biển số", "mã xe theo số căn hộ",
                            "2 tháng", "50.000", "100.000", "6 tháng", "một lần", "Ban quản lý"):
            assert requirement in answer
        tables = [*prose_fields, "faq_knowledge_base"]
        first = {table: [tuple(row) for row in db.execute(f"SELECT * FROM {table}")] for table in tables}
        db.executescript(script)
        second = {table: [tuple(row) for row in db.execute(f"SELECT * FROM {table}")] for table in tables}
        assert first == second
