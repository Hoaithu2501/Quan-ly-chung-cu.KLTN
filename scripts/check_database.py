"""Read-only audit of the Docker database and optional Windows database copies.

Never falls back to a local database when Docker is unavailable. No row values,
credentials or device tokens are included in the report.
"""
import argparse
from contextlib import closing
import inspect
import json
from pathlib import Path, PurePosixPath
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SERVICES = {'auth', 'resident', 'billing', 'parking', 'maintenance',
            'notification', 'complaint', 'chatbot', 'gateway'}


def inspect_database(path):
    path = Path(path).resolve()
    # mode=ro prevents a typo from creating a new, empty database.
    with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=15)) as db:
        db.execute('BEGIN')
        tables = [row[0] for row in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name NOT LIKE 'sqlite_%' ORDER BY name")]
        counts = {}
        for table in tables:
            quoted = '"' + table.replace('"', '""') + '"'
            counts[table] = db.execute('SELECT count(*) FROM ' + quoted).fetchone()[0]
        return {
            'path': str(path),
            'integrity': [row[0] for row in db.execute('PRAGMA integrity_check')],
            'foreign_key_issues': len(db.execute('PRAGMA foreign_key_check').fetchall()),
            'table_count': len(tables),
            'counts': counts,
        }


def inspect_topology(containers):
    services, errors, identities = [], [], set()
    for container in containers:
        config = container.get('Config', {})
        name = (config.get('Labels') or {}).get('com.docker.compose.service', '')
        if name not in SERVICES | {'db-init'}:
            continue
        env = dict(item.split('=', 1) for item in config.get('Env', []) if '=' in item)
        path = env.get('DATABASE_PATH', '')
        location = PurePosixPath(path)
        mounts = [m for m in container.get('Mounts', [])
                  if path and location.is_absolute()
                  and location.is_relative_to(PurePosixPath(m['Destination']))]
        # A more specific bind mount can override a parent volume.
        mount = max(mounts, key=lambda m: len(m['Destination']), default={})
        storage = mount.get('Name') or mount.get('Source')
        if not storage:
            errors.append(f'{name}: database is missing or not on a shared mount')
        else:
            relative = str(location.relative_to(PurePosixPath(mount['Destination'])))
            identities.add((mount.get('Type'), storage, relative))
        services.append({'service': name, 'state': container.get('State', {}).get('Status'),
                         'database': path, 'storage': storage, 'mount_type': mount.get('Type')})
    missing = SERVICES - {item['service'] for item in services}
    if missing:
        errors.append('Missing containers: ' + ', '.join(sorted(missing)))
    if len(identities) != 1:
        errors.append('Services do not resolve to one shared database')
    return {'same_database': not errors, 'services': sorted(services, key=lambda s: s['service']),
            'errors': errors}


def docker_command(*args):
    try:
        result = subprocess.run(['docker', *args], cwd=ROOT, capture_output=True,
                                text=True, encoding='utf-8', timeout=60)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('Cannot reach Docker. Start Docker Desktop and try again.') from exc
    if result.returncode:
        # Do not echo Docker config or environment parsing errors containing secrets.
        raise RuntimeError('Docker command failed. Check Docker Desktop and `docker compose ps -a`.')
    return result.stdout


def docker_report():
    ids = docker_command('compose', 'ps', '-aq').split()
    if not ids:
        raise RuntimeError('No Compose containers found. No local database was used instead.')
    topology = inspect_topology(json.loads(docker_command('inspect', *ids)))
    # Run the current audit code without rebuilding or copying files into containers.
    program = ('import os,json,sqlite3\nfrom pathlib import Path\n'
               'from contextlib import closing\n' + inspect.getsource(inspect_database) +
               '\nprint(json.dumps(inspect_database(os.environ["DATABASE_PATH"])))')
    topology['database'] = json.loads(docker_command(
        'compose', 'exec', '-T', 'auth', 'python', '-c', program))
    return topology


def local_inventory():
    files = [ROOT / 'QLCC.db', *sorted((ROOT / 'data').glob('*.db')),
             *sorted((ROOT / 'backups').rglob('*.db'))]
    reports = []
    for path in files:
        if not path.is_file():
            continue
        try:
            report = inspect_database(path)
        except sqlite3.Error as exc:
            report = {'error': type(exc).__name__}
        report['path'] = str(path.relative_to(ROOT))
        reports.append(report)
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', action='store_true', help='Also inspect source, local and backup DBs')
    parser.add_argument('--json', action='store_true', help='Print counts and topology as JSON')
    args = parser.parse_args()
    try:
        report = docker_report()
    except (RuntimeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if args.inventory:
        report['local_copies'] = local_inventory()
    db = report['database']
    healthy = report['same_database'] and db['integrity'] == ['ok'] and db['foreign_key_issues'] == 0
    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=True))
    else:
        print('Docker database:', db['path'])
        print('All services share one database:', 'OK' if report['same_database'] else 'FAIL')
        for item in report['services']:
            print(f"  {item['service']}: {item['storage']} -> {item['database']} ({item['state']})")
        print('Integrity:', ', '.join(db['integrity']))
        print('Foreign-key issues:', db['foreign_key_issues'])
        print('Tables:', db['table_count'])
        for name, count in db['counts'].items():
            print(f'  {name}: {count}')
        for error in report['errors']:
            print('ERROR:', error)
        for item in report.get('local_copies', []):
            print('Local/source/backup copy (not the Docker database):', item['path'],
                  f"tables={item.get('table_count', '?')}", item.get('error', ''))
    return 0 if healthy else 1


if __name__ == '__main__':
    sys.exit(main())
