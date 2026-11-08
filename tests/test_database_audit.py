from contextlib import closing
import sqlite3

import pytest

from scripts.check_database import SERVICES, inspect_database, inspect_topology


def containers():
    return [dict(Config={'Labels': {'com.docker.compose.service': name},
                         'Env': ['DATABASE_PATH=/app/data/QLCC.db', 'SECRET=do-not-print']},
                 State={'Status': 'running'},
                 Mounts=[{'Type': 'volume', 'Name': 'qlcc_qlcc-data',
                          'Destination': '/app/data', 'Source': '/var/lib/docker/volumes/data'}])
            for name in sorted(SERVICES | {'db-init'})]


def test_topology_detects_different_volumes_and_missing_services():
    items = containers()
    report = inspect_topology(items)
    assert report['same_database']
    assert 'do-not-print' not in str(report)
    items[0]['Mounts'][0]['Name'] = 'old-project-data'
    assert not inspect_topology(items)['same_database']
    assert not inspect_topology(containers()[1:])['same_database']


def test_topology_detects_overridden_database_file():
    items = containers()
    items[0]['Mounts'].append({'Type': 'bind', 'Source': '/another/QLCC.db',
                               'Destination': '/app/data/QLCC.db'})
    assert not inspect_topology(items)['same_database']


def test_read_only_audit_sees_committed_wal_and_excludes_private_data(tmp_path):
    path = tmp_path / 'runtime.db'
    with closing(sqlite3.connect(path)) as writer:
        writer.execute('PRAGMA journal_mode=WAL')
        writer.executescript("CREATE TABLE users (id INTEGER PRIMARY KEY, token TEXT);"
                             "INSERT INTO users VALUES (1, 'private-device-token');")
        before = path.read_bytes()
        wal = path.with_name(path.name + '-wal').read_bytes()
        report = inspect_database(path)
        assert report['counts']['users'] == 1
        assert report['integrity'] == ['ok']
        assert 'private-device-token' not in str(report)
        assert path.read_bytes() == before
        assert path.with_name(path.name + '-wal').read_bytes() == wal


def test_missing_database_is_not_created_and_broken_foreign_key_is_reported(tmp_path):
    missing = tmp_path / 'typo.db'
    with pytest.raises(sqlite3.OperationalError):
        inspect_database(missing)
    assert not missing.exists()
    path = tmp_path / 'broken-reference.db'
    with closing(sqlite3.connect(path)) as db:
        db.executescript('CREATE TABLE parent (id INTEGER PRIMARY KEY);'
                         'CREATE TABLE child (parent_id INTEGER REFERENCES parent(id));'
                         'INSERT INTO child VALUES (9);')
    assert inspect_database(path)['foreign_key_issues'] == 1
