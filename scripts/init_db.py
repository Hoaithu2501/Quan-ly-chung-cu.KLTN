"""Idempotent bootstrap; never modifies the delivered source QLCC.db."""
import argparse
import os
from pathlib import Path
import secrets
import sqlite3
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def initialize(path=None, demo=False):
    from shared.config import database_path
    destination=Path(path) if path else database_path()
    if not destination.is_absolute(): destination=ROOT/destination
    original=ROOT/'QLCC.db'
    source=Path(os.getenv('DATABASE_SEED_PATH','')) if os.getenv('DATABASE_SEED_PATH') else original
    if not source.is_file(): source=original
    if destination.resolve() in (original.resolve(),source.resolve()):
        raise RuntimeError('DATABASE_PATH must not point to the original QLCC.db. Use data/QLCC.db.')
    destination.parent.mkdir(parents=True,exist_ok=True)
    if not destination.exists():
        if not source.is_file():
            # Fresh clones contain a public SQL fixture instead of a private DB.
            from scripts.ci.prepare_database import prepare
            prepare(original)
            source=original
        with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as src, sqlite3.connect(destination) as target:
            src.backup(target)
    with sqlite3.connect(destination) as db:
        db.execute('PRAGMA journal_mode=WAL')
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=15000')
        db.execute('CREATE TABLE IF NOT EXISTS schema_migrations(name TEXT PRIMARY KEY,applied_at TEXT DEFAULT CURRENT_TIMESTAMP)')
        if 'area' not in [r[1] for r in db.execute('PRAGMA table_info(apartments)')]:
            # Existing source has no area. Leave unknown areas NULL rather than invent data.
            db.execute('ALTER TABLE apartments ADD COLUMN area REAL CHECK(area IS NULL OR area>0)')
        for migration in sorted((ROOT/'migrations').glob('*.sql')):
            if not db.execute('SELECT 1 FROM schema_migrations WHERE name=?',(migration.name,)).fetchone():
                # Rebuild migrations and their ledger entry must commit together.
                # executescript commits pending work first, so include the complete
                # transaction in the script rather than relying on the connection context.
                name=migration.name.replace("'", "''")
                try:
                    db.executescript("BEGIN IMMEDIATE;\n"+migration.read_text(encoding='utf-8')+
                                     f"\nINSERT INTO schema_migrations(name) VALUES('{name}');\nCOMMIT;")
                except Exception:
                    db.rollback()
                    raise
        if demo and not db.execute("SELECT 1 FROM schema_migrations WHERE name='demo-users-v1'").fetchone():
            from werkzeug.security import generate_password_hash
            accounts=[('admin','Admin@12345','admin'),('resident','Resident@12345','resident'),('technician','Tech@12345','technician')]
            ids={}
            for username,password,role in accounts:
                if db.execute('SELECT 1 FROM users WHERE username=?',(username,)).fetchone():
                    raise RuntimeError(f'Cannot seed demo: username {username} already exists.')
                cur=db.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(username,generate_password_hash(password),role))
                ids[role]=cur.lastrowid
            db.execute('UPDATE residents SET user_id=? WHERE resident_id=1',(ids['resident'],))
            db.execute('UPDATE technicians SET user_id=? WHERE technician_id=1',(ids['technician'],))
            db.execute("INSERT INTO schema_migrations(name) VALUES('demo-users-v1')")
        db.commit()
        result=db.execute('PRAGMA integrity_check').fetchone()[0]
        if result!='ok': raise RuntimeError(result)
    return destination

def ensure_env():
    env_path=ROOT/'.env'
    content=env_path.read_text(encoding='utf-8') if env_path.exists() else (ROOT/'.env.example').read_text(encoding='utf-8')
    lines=content.splitlines()
    for name in ('JWT_SECRET','SERVICE_TOKEN','SEPAY_WEBHOOK_API_KEY'):
        idx=next((i for i,line in enumerate(lines) if line.startswith(name+'=')),None)
        if idx is None: lines.append(name+'='+secrets.token_urlsafe(48))
        elif not lines[idx].split('=',1)[1].strip(): lines[idx]=name+'='+secrets.token_urlsafe(48)
    env_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='Create application DB copy and apply pending migrations.')
    parser.add_argument('--demo',action='store_true',help='Create three local demo login accounts once')
    args=parser.parse_args()
    ensure_env()
    path=initialize(demo=args.demo)
    print(f'Database ready: {path}')
    if args.demo: print('Demo: admin / Admin@12345 | resident / Resident@12345 | technician / Tech@12345')
