from pathlib import Path
import shutil
import sqlite3

import pytest

from scripts.ci.prepare_database import prepare


def test_public_fixture_has_no_login_hashes_or_personal_contacts(tmp_path):
    path = prepare(tmp_path / "fixture.db")
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT COUNT(*) FROM apartments").fetchone()[0] == 270
        assert all(row[0] == "!disabled-synthetic-account" for row in db.execute("SELECT password_hash FROM users"))
        assert all(row[0].endswith("@example.invalid") for row in db.execute("SELECT email FROM users"))
        assert db.execute("SELECT COUNT(*) FROM residents WHERE id_card IS NOT NULL OR phone IS NOT NULL").fetchone()[0] == 0


def test_prepare_never_overwrites_existing_database(tmp_path):
    target = tmp_path / "existing.db"
    target.write_bytes(b"data to preserve")
    with pytest.raises(FileExistsError):
        prepare(target)
    assert target.read_bytes() == b"data to preserve"


def test_synthetic_fixture_bootstrap_and_migrations_are_repeatable(tmp_path, monkeypatch):
    from scripts.init_db import initialize

    source = prepare(tmp_path / "source.db")
    target = tmp_path / "application.db"
    monkeypatch.setenv("DATABASE_SEED_PATH", str(source))
    initialize(target, demo=True)
    initialize(target, demo=True)
    with sqlite3.connect(target) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT COUNT(*) FROM users WHERE username IN ('admin','resident','technician')").fetchone()[0] == 3
        assert db.execute("SELECT COUNT(*) FROM schema_migrations WHERE name='demo-users-v1'").fetchone()[0] == 1


def test_fresh_checkout_bootstraps_without_committed_database(tmp_path, monkeypatch):
    import scripts.init_db as initializer

    shutil.copytree(Path(__file__).resolve().parents[1] / "migrations", tmp_path / "migrations")
    monkeypatch.setattr(initializer, "ROOT", tmp_path)
    monkeypatch.delenv("DATABASE_SEED_PATH", raising=False)
    destination = initializer.initialize(tmp_path / "data/application.db", demo=True)
    assert (tmp_path / "QLCC.db").is_file()
    with sqlite3.connect(destination) as db:
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
        assert db.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0] == 1
