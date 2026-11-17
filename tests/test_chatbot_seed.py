"""FAQ preview, preservation and transaction checks on isolated SQLite databases."""
from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

import pytest

from scripts import apply_chatbot_faq as seed


SCHEMA = """
CREATE TABLE faq_knowledge_base (
    faq_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL
);
CREATE TABLE notifications (notification_id INTEGER PRIMARY KEY, content TEXT);
INSERT INTO notifications VALUES (1, 'Original notification history');
CREATE TABLE payments (payment_id INTEGER PRIMARY KEY, amount INTEGER NOT NULL);
INSERT INTO payments VALUES (1, 10000);
INSERT INTO faq_knowledge_base VALUES (81, 'Custom', 'Câu hỏi do quản lý tự nhập?', 'Nội dung riêng');
INSERT INTO faq_knowledge_base VALUES (9, 'Old', 'Số hotline của chung cư là gì?', '0243 000 1111');
INSERT INTO faq_knowledge_base VALUES (7, 'Old', 'Giá vé gửi xe tháng là bao nhiêu?', 'Xe máy 600.000 đồng/kỳ');
"""


def faq_rows(db):
    return db.execute("SELECT * FROM faq_knowledge_base ORDER BY faq_id").fetchall()


def test_seed_is_repeatable_preserves_custom_rows_ids_and_other_tables():
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(SCHEMA)
        custom = db.execute("SELECT * FROM faq_knowledge_base WHERE faq_id=81").fetchone()
        first = seed.execute_seed(db)
        after = faq_rows(db)
        assert first["updated"] == 2
        assert first["inserted"] > 0
        assert db.execute("SELECT * FROM faq_knowledge_base WHERE faq_id=81").fetchone() == custom
        assert "0228913665" in db.execute("SELECT answer FROM faq_knowledge_base WHERE faq_id=9").fetchone()[0]
        assert "xe điện" in db.execute("SELECT answer FROM faq_knowledge_base WHERE faq_id=7").fetchone()[0]
        assert all(row[0] > 81 for row in after if row[0] not in {7, 9, 81})
        assert db.execute("SELECT * FROM notifications").fetchall() == [(1, "Original notification history")]
        assert db.execute("SELECT * FROM payments").fetchall() == [(1, 10000)]
        second = seed.execute_seed(db)
        assert second["inserted"] == second["updated"] == 0
        assert faq_rows(db) == after
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


def test_seed_keeps_canonical_parking_policy_and_does_not_insert_legacy_aliases():
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(SCHEMA)
        policy = (seed.ROOT / "migrations/ui_policy_content.sql").read_text(encoding="utf-8")
        db.executescript(policy[policy.index("CREATE TEMP TABLE ui_parking_faq"):])
        canonical = {row[2]: row for row in faq_rows(db) if row[1] == "Gửi xe"}
        seed.execute_seed(db)
        current = {row[2]: row for row in faq_rows(db)}
        assert len(canonical) == 5
        for question, original in canonical.items():
            assert current[question] == original
        assert "Sửa chữa trong căn hộ có mất phí không?" not in current
        assert "Thẻ ra vào cư dân được cấp như thế nào?" not in current
        assert "Sửa chữa & bảo trì → Tạo yêu cầu" in current["Căn hộ bị hỏng điện nước thì báo ở đâu?"][3]
        assert "VietQR" in current["Có những hình thức thanh toán nào?"][3]
        assert "biên nhận nội bộ" in current["Có xuất hoá đơn điện tử không?"][3]


def test_payment_answers_stop_naming_the_removed_payment_buttons():
    """Existing databases get the new answers; an answer management rewrote is left alone."""
    root = seed.ROOT / "migrations"
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(SCHEMA)
        db.executemany(
            "INSERT INTO faq_knowledge_base(category,question,answer) VALUES ('Thanh toán',?,?)",
            [
                ("Có những hình thức thanh toán nào?", "MoMo"),
                ("Đã thanh toán nhưng hoá đơn vẫn báo chưa thanh toán thì làm gì?", "MoMo"),
                ("Thanh toán thiếu tiền thì hoá đơn có được tính là đã thanh toán không?", "Hiện chưa thể chia nhỏ"),
            ],
        )
        db.executescript((root / "chatbot_sepay_payment_guidance.sql").read_text(encoding="utf-8"))
        edited = "Câu trả lời Ban quản lý tự viết."
        db.execute(
            "UPDATE faq_knowledge_base SET answer=? WHERE question='Có những hình thức thanh toán nào?'", (edited,)
        )
        db.executescript((root / "0160_chatbot_payment_updates_automatically.sql").read_text(encoding="utf-8"))
        answers = dict(db.execute("SELECT question, answer FROM faq_knowledge_base WHERE category='Thanh toán'"))
    assert answers.pop("Có những hình thức thanh toán nào?") == edited
    for answer in answers.values():
        assert "tự cập nhật" in answer
        assert "Kiểm tra trạng thái" not in answer and "Tôi đã chuyển khoản" not in answer


def test_existing_duplicate_questions_keep_both_ids_and_are_reported():
    with closing(sqlite3.connect(":memory:")) as db:
        db.executescript(SCHEMA)
        db.execute("INSERT INTO faq_knowledge_base VALUES (90, 'Old', 'Số hotline của chung cư là gì?', 'Old second answer')")
        result = seed.execute_seed(db)
        matches = db.execute("SELECT faq_id, answer FROM faq_knowledge_base WHERE question=? ORDER BY faq_id",
                             ("Số hotline của chung cư là gì?",)).fetchall()
        assert [row[0] for row in matches] == [9, 90]
        assert all("0228913665" in row[1] for row in matches)
        assert result["duplicate_questions"] == [{"question": "Số hotline của chung cư là gì?", "count": 2}]


def test_preview_changes_only_memory_and_creates_no_backup():
    with TemporaryDirectory(prefix="qlcc-faq-test-") as folder:
        path = Path(folder) / "runtime.db"
        with closing(sqlite3.connect(path)) as db:
            db.executescript(SCHEMA)
            before = faq_rows(db)
        files_before = set(Path(folder).iterdir())
        result = seed.seed_database(path)
        assert result["mode"] == "preview"
        assert result["backup"] is None
        assert result["inserted"] > 0
        assert set(Path(folder).iterdir()) == files_before
        with closing(sqlite3.connect(path)) as db:
            assert faq_rows(db) == before


def test_apply_backs_up_committed_wal_and_preserves_payments():
    with TemporaryDirectory(prefix="qlcc-faq-test-") as folder:
        path = Path(folder) / "runtime.db"
        with closing(sqlite3.connect(path)) as keeper:
            keeper.execute("PRAGMA journal_mode=WAL")
            keeper.execute("PRAGMA wal_autocheckpoint=0")
            keeper.executescript(SCHEMA)
            keeper.execute("INSERT INTO payments VALUES (2, 54321)")
            keeper.commit()
            before = faq_rows(keeper)
            assert Path(str(path) + "-wal").stat().st_size > 0
            result = seed.seed_database(path, apply=True)
            assert result["mode"] == "applied"
            with closing(sqlite3.connect(result["backup"])) as backup:
                assert faq_rows(backup) == before
                assert backup.execute("SELECT * FROM payments").fetchall() == [(1, 10000), (2, 54321)]
                assert backup.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
            assert keeper.execute("SELECT * FROM payments").fetchall() == [(1, 10000), (2, 54321)]
            assert len(faq_rows(keeper)) > len(before)


def test_sql_error_rolls_back_entire_seed_and_keeps_backup(monkeypatch):
    with TemporaryDirectory(prefix="qlcc-faq-test-") as folder:
        path = Path(folder) / "runtime.db"
        bad_script = Path(folder) / "invalid.sql"
        bad_script.write_text(seed.SQL_PATH.read_text(encoding="utf-8") +
                              "\nINSERT INTO faq_knowledge_base(question, answer) VALUES ('bad', NULL);\n",
                              encoding="utf-8")
        with closing(sqlite3.connect(path)) as db:
            db.executescript(SCHEMA)
            before = faq_rows(db)
        monkeypatch.setattr(seed, "SQL_PATH", bad_script)
        with pytest.raises(sqlite3.IntegrityError):
            seed.seed_database(path, apply=True)
        with closing(sqlite3.connect(path)) as db:
            assert faq_rows(db) == before
            assert db.execute("SELECT * FROM payments").fetchall() == [(1, 10000)]
        assert len(list((Path(folder) / "backups").glob("*.db"))) == 1


def test_rejects_source_database_and_missing_target(monkeypatch):
    with pytest.raises(ValueError, match="source QLCC.db"):
        seed.seed_database(seed.ROOT / "QLCC.db", apply=True)
    with TemporaryDirectory(prefix="qlcc-faq-test-") as folder:
        source = Path(folder) / "seed.db"
        with closing(sqlite3.connect(source)) as db:
            db.executescript(SCHEMA)
        monkeypatch.setenv("DATABASE_SEED_PATH", str(source))
        with pytest.raises(ValueError, match="source QLCC.db"):
            seed.seed_database(source, apply=True)
        missing = Path(folder) / "missing.db"
        with pytest.raises(ValueError, match="does not exist"):
            seed.seed_database(missing)
        assert not missing.exists()
