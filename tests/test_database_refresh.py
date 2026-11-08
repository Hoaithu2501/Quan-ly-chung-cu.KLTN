from contextlib import closing
from pathlib import Path
import sqlite3

import pytest

from scripts.refresh_db import refresh_database, snapshot


def database(path):
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE apartments (apartment_id INTEGER PRIMARY KEY, code TEXT UNIQUE, status TEXT, area REAL);
            CREATE TABLE faq_knowledge_base (faq_id INTEGER PRIMARY KEY, question TEXT, answer TEXT);
            CREATE TABLE locations (location_id INTEGER PRIMARY KEY, name TEXT);
            CREATE TABLE notifications (notification_id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, content TEXT);
            INSERT INTO apartments VALUES (1,'A-0101','vacant',70);
            INSERT INTO faq_knowledge_base VALUES (1,'Question','Original answer');
            INSERT INTO locations VALUES (1,'Reception');
            INSERT INTO notifications VALUES (1,'Original notice','Content');
        """)
    return path


@pytest.fixture
def databases(tmp_path):
    source = database(tmp_path / "source.db")
    target = snapshot(source, tmp_path / "application.db")
    with sqlite3.connect(target) as db:
        db.executescript("""
            CREATE TABLE users (user_id INTEGER PRIMARY KEY, password_hash TEXT);
            INSERT INTO users VALUES (1,'real-password-hash');
            CREATE TABLE payments (payment_id INTEGER PRIMARY KEY, amount INTEGER);
            INSERT INTO payments VALUES (1,100000);
            CREATE TABLE notification_events (event_id TEXT PRIMARY KEY, notification_id INTEGER REFERENCES notifications(notification_id));
            INSERT INTO notifications VALUES (2,'Server payment received','Preserve this event');
            INSERT INTO notification_events VALUES ('payment-1',2);
            UPDATE apartments SET status='occupied';
        """)
    with sqlite3.connect(source) as db:
        db.executescript("""
            UPDATE apartments SET code='A-0201';
            INSERT INTO apartments VALUES (2,'A-0202','vacant',90);
            UPDATE faq_knowledge_base SET answer='Updated answer';
            INSERT INTO notifications VALUES (2,'Source announcement','New source content');
        """)
    return source, target


def test_preview_leaves_runtime_untouched(databases):
    source, target = databases
    before = target.read_bytes()
    result = refresh_database(target, source)
    assert not result["applied"] and result["backup"] is None
    assert result["changes"]["apartments"] == {"inserted": 1, "updated": 1, "unchanged": 0}
    assert result["changes"]["notifications"]["remapped"] == 1
    assert target.read_bytes() == before


def test_apply_backs_up_and_preserves_application_data(databases):
    source, target = databases
    original = source.read_bytes()
    result = refresh_database(target, source, apply=True)
    with sqlite3.connect(result["backup"]) as backup:
        assert backup.execute("SELECT COUNT(*) FROM apartments").fetchone()[0] == 1
        assert backup.execute("SELECT code FROM apartments").fetchone()[0] == "A-0101"
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT code,status FROM apartments WHERE apartment_id=1").fetchone() == ("A-0201", "occupied")
        assert db.execute("SELECT password_hash FROM users").fetchone()[0] == "real-password-hash"
        assert db.execute("SELECT amount FROM payments").fetchone()[0] == 100000
        assert db.execute("SELECT title FROM notifications WHERE notification_id=2").fetchone()[0] == "Server payment received"
        assert db.execute("SELECT notification_id FROM notification_events").fetchone()[0] == 2
        mapped = db.execute("SELECT notification_id FROM source_notification_imports WHERE source_notification_id=2").fetchone()[0]
        assert mapped != 2
        assert db.execute("SELECT title FROM notifications WHERE notification_id=?", (mapped,)).fetchone()[0] == "Source announcement"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    assert source.read_bytes() == original
    again = refresh_database(target, source, apply=True)
    assert all(value["inserted"] == value["updated"] == 0 for value in again["changes"].values())
    with sqlite3.connect(source) as db:
        db.execute("UPDATE notifications SET title='Revised source announcement' WHERE notification_id=2")
    updated = refresh_database(target, source, apply=True)
    assert updated["changes"]["notifications"]["updated"] == 1
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 3
        assert db.execute("SELECT title FROM notifications WHERE notification_id=?", (mapped,)).fetchone()[0] == "Revised source announcement"


def test_catalog_conflict_rolls_back_entire_import(databases):
    source, target = databases
    with sqlite3.connect(target) as db:
        db.execute("INSERT INTO apartments VALUES (99,'A-0202','occupied',95)")
    with pytest.raises(sqlite3.IntegrityError):
        refresh_database(target, source, apply=True)
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT code FROM apartments WHERE apartment_id=1").fetchone()[0] == "A-0101"
        assert db.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 2
    assert list((target.parent / "backups").glob("*.db"))


def test_snapshot_includes_committed_wal_and_refuses_overwrite(tmp_path):
    source = tmp_path / "wal.db"
    with closing(sqlite3.connect(source)) as writer:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("CREATE TABLE sample (value INTEGER)")
        writer.execute("INSERT INTO sample VALUES (42)")
        writer.commit()
        assert Path(str(source) + "-wal").exists()
        exported = snapshot(source, tmp_path / "export.db")
        with sqlite3.connect(exported) as db:
            assert db.execute("SELECT value FROM sample").fetchone()[0] == 42
            assert db.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        with pytest.raises(FileExistsError):
            snapshot(source, exported)


def test_refresh_rejects_transaction_tables_and_source_target(databases):
    source, target = databases
    with pytest.raises(ValueError):
        refresh_database(target, source, tables=["users"], apply=True)
    with pytest.raises(ValueError):
        refresh_database(source, source, apply=True)


def test_failed_migration_rolls_back_schema_and_ledger(tmp_path, monkeypatch):
    import scripts.init_db as initializer
    root = tmp_path / "project"
    root.mkdir()
    source = database(root / "QLCC.db")
    target = snapshot(source, root / "application.db")
    migrations = root / "migrations"
    migrations.mkdir()
    (migrations / "rebuild.sql").write_text("CREATE TABLE temporary_rebuild (value INTEGER); DROP TABLE apartments; SELECT * FROM missing_table;", encoding="utf-8")
    monkeypatch.setattr(initializer, "ROOT", root)
    monkeypatch.delenv("DATABASE_SEED_PATH", raising=False)
    with pytest.raises(sqlite3.OperationalError):
        initializer.initialize(target)
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT COUNT(*) FROM apartments").fetchone()[0] == 1
        assert not db.execute("SELECT name FROM sqlite_master WHERE name='temporary_rebuild'").fetchone()
        assert not db.execute("SELECT name FROM schema_migrations WHERE name='rebuild.sql'").fetchone()


def test_refresh_keeps_installed_current_policy(tmp_path, monkeypatch):
    from scripts.init_db import initialize
    from scripts.refresh_db import ROOT
    monkeypatch.delenv("DATABASE_SEED_PATH", raising=False)
    source = snapshot(ROOT / "QLCC.db", tmp_path / "source.db")
    target = snapshot(source, tmp_path / "application.db")
    initialize(target)
    with sqlite3.connect(target) as db:
        initial_count = db.execute("SELECT COUNT(*) FROM faq_knowledge_base").fetchone()[0]
    result = refresh_database(target, source, apply=True)
    assert result["content_policy"]["reapplied"]
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT COUNT(*) FROM faq_knowledge_base").fetchone()[0] == initial_count
        answer = db.execute("SELECT answer FROM faq_knowledge_base WHERE question=?", ("Làm sao để đăng ký gửi xe tháng?",)).fetchone()[0]
        assert "50.000" in answer and "100.000" in answer and "2 tháng" in answer
        assert "Ban quản lý" in answer and "ban quản lý" not in answer
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
