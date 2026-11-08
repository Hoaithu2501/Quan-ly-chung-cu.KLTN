"""Export the complete Docker SQLite database, including committed WAL data.

The live database is opened read-only. An existing export is never overwritten.
"""
import argparse
from contextlib import closing
import hashlib
import inspect
import json
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.check_database import docker_command, inspect_database, inspect_topology


def create_snapshot(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError('Export must not replace the source database.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.as_uri() + '?mode=ro', uri=True, timeout=15)) as src:
        # Exclusive creation protects previous exports and unrelated databases.
        with destination.open('xb'):
            pass
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
            dst.execute('PRAGMA journal_mode=DELETE')
            if dst.execute('PRAGMA integrity_check').fetchall() != [('ok',)]:
                raise RuntimeError('Export integrity check failed.')
            if dst.execute('PRAGMA foreign_key_check').fetchone():
                raise RuntimeError('Export has foreign-key violations.')
    return destination


def export_docker(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f'Export already exists: {destination}. Choose a new output path.')
    ids = docker_command('compose', 'ps', '-aq').split()
    if not ids:
        raise RuntimeError('No Docker containers found.')
    topology = inspect_topology(json.loads(docker_command('inspect', *ids)))
    if not topology['same_database']:
        raise RuntimeError('Containers do not share one database; audit them before exporting.')
    remote = '/tmp/qlcc-export-' + uuid.uuid4().hex + '.db'
    program = ('import os,sqlite3,json,hashlib,sys\nfrom pathlib import Path\n'
               'from contextlib import closing\n' + inspect.getsource(create_snapshot) +
               '\np=create_snapshot(os.environ["DATABASE_PATH"],sys.argv[1])\n'
               'print(json.dumps({"sha256":hashlib.sha256(p.read_bytes()).hexdigest()}))')
    try:
        result = json.loads(docker_command('compose', 'exec', '-T', 'auth',
                                          'python', '-c', program, remote))
        destination.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='qlcc-export-') as folder:
            staged = Path(folder) / 'snapshot.db'
            docker_command('compose', 'cp', 'auth:' + remote, str(staged))
            checksum = hashlib.sha256(staged.read_bytes()).hexdigest()
            if checksum != result['sha256']:
                raise RuntimeError('Export checksum changed during copy.')
            report = inspect_database(staged)
            if report['integrity'] != ['ok'] or report['foreign_key_issues']:
                raise RuntimeError('Export verification failed.')
            with destination.open('xb') as output, staged.open('rb') as source:
                shutil.copyfileobj(source, output)
            if hashlib.sha256(destination.read_bytes()).hexdigest() != checksum:
                raise RuntimeError('Saved export checksum mismatch.')
            report['path'] = str(destination)
            report['sha256'] = checksum
            return report
    finally:
        # Only remove the uniquely named temporary export, never the live file.
        cleanup = ('from pathlib import Path; import sys; p=Path(sys.argv[1]); '
                   'assert p.parent == Path("/tmp") and p.name.startswith("qlcc-export-"); '
                   'p.unlink(missing_ok=True)')
        try:
            docker_command('compose', 'exec', '-T', 'auth', 'python', '-c', cleanup, remote)
        except RuntimeError:
            print('Temporary export cleanup failed inside the container; live data is unchanged.',
                  file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default=str(ROOT / 'data' / 'QLCC.snapshot.db'))
    args = parser.parse_args()
    try:
        report = export_docker(args.output)
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=True, indent=2))
    return 0


if __name__ == '__main__':
    sys.exit(main())
