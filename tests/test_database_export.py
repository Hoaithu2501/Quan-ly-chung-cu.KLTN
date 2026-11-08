from contextlib import closing
import sqlite3

import pytest

from scripts.export_database import create_snapshot


def test_snapshot_preserves_committed_wal_without_changing_source(tmp_path):
    source = tmp_path / 'source.db'
    target = tmp_path / 'snapshot.db'
    with closing(sqlite3.connect(source)) as writer:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.executescript('CREATE TABLE payment (id INTEGER PRIMARY KEY, amount INTEGER);'
                             'INSERT INTO payment VALUES (1, 15000);')
        before = source.read_bytes()
        wal = source.with_name(source.name + '-wal').read_bytes()
        create_snapshot(source, target)
        assert source.read_bytes() == before
        assert source.with_name(source.name + '-wal').read_bytes() == wal
        with closing(sqlite3.connect(target.as_uri() + '?mode=ro', uri=True)) as db:
            assert db.execute('SELECT * FROM payment').fetchall() == [(1, 15000)]
            assert db.execute('PRAGMA journal_mode').fetchone()[0] == 'delete'
            assert db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert not target.with_name(target.name + '-wal').exists()


def test_snapshot_refuses_overwrite_same_path_and_missing_source(tmp_path):
    source = tmp_path / 'source.db'
    with closing(sqlite3.connect(source)) as db:
        db.execute('CREATE TABLE item (id INTEGER PRIMARY KEY)')
    target = tmp_path / 'existing.db'
    target.write_bytes(b'preserve-existing-file')
    with pytest.raises(FileExistsError):
        create_snapshot(source, target)
    assert target.read_bytes() == b'preserve-existing-file'
    with pytest.raises(ValueError):
        create_snapshot(source, source)
    with pytest.raises(sqlite3.OperationalError):
        create_snapshot(tmp_path / 'missing.db', tmp_path / 'new.db')
    assert not (tmp_path / 'missing.db').exists()
    assert not (tmp_path / 'new.db').exists()
