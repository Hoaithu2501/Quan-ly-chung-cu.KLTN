"""Create the application database when it is missing and apply pending migrations. Safe to run repeatedly."""

import argparse
from contextlib import closing
import json
import os
from pathlib import Path
import secrets
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEMO_ACCOUNTS = (
    ("admin", "Admin@12345", "admin"),
    ("resident", "Resident@12345", "resident"),
    ("technician", "Tech@12345", "technician"),
)
# Runtime containers run as this unprivileged user; see the Dockerfile.
APP_UID = 10001


def live_payments():
    return os.getenv("SEPAY_ENV", "test").strip().lower() == "live"


def migration_files(folder=None):
    """Numbered files (0100_x.sql) run after the original unnumbered set, in numeric order.

    The unnumbered names keep their historical alphabetical order because applied
    migrations are recorded by filename, so they can never be renamed.
    """

    def order(path):
        prefix = path.name.split("_", 1)[0]
        return (1, int(prefix), path.name) if prefix.isdigit() else (0, 0, path.name)

    return sorted(Path(folder or ROOT / "migrations").glob("*.sql"), key=order)


def assert_no_public_demo_passwords(db):
    """Fail closed: a published password must never guard an account handling real money."""
    from werkzeug.security import check_password_hash

    exposed = [
        username
        for username, password, _ in DEMO_ACCOUNTS
        if any(
            row[0].startswith(("scrypt:", "pbkdf2:")) and check_password_hash(row[0], password)
            for row in db.execute("SELECT password_hash FROM users WHERE username=? AND status='active'", (username,))
        )
    ]
    if exposed:
        raise RuntimeError(
            "SEPAY_ENV=live but these accounts still use the published demo password: " + ", ".join(exposed)
        )


def share_data_directory(path=None):
    """Hand the database folder to the unprivileged runtime user (Docker init runs as root)."""
    from shared.config import database_path

    if not hasattr(os, "geteuid") or os.geteuid() != 0:
        return
    folder = Path(path) if path else database_path().parent
    for item in (folder, *folder.rglob("*")):
        os.chown(item, APP_UID, APP_UID)


def ensure_generated_secrets(path=None):
    """A clean checkout has no .env, so the first container start creates its own secrets, once."""
    from shared.config import GENERATED_SECRETS

    path = Path(path) if path else GENERATED_SECRETS
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    values = {name: secrets.token_urlsafe(48) for name in ("JWT_SECRET", "SERVICE_TOKEN")}
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as output:
        json.dump(values, output)
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        os.chown(path, APP_UID, APP_UID)


def initialize(path=None, demo=False):
    from scripts.ci.prepare_database import prepare
    from shared.config import database_path

    destination = Path(path) if path else database_path()
    if not destination.is_absolute():
        destination = ROOT / destination
    if not destination.exists():
        # A new installation starts from the public sample data. Existing data is never replaced.
        prepare(destination)
    if demo and live_payments():
        print("SEPAY_ENV=live: demo accounts were not created.")
        demo = False
    with closing(sqlite3.connect(destination)) as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=15000")
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations(name TEXT PRIMARY KEY,applied_at TEXT DEFAULT CURRENT_TIMESTAMP)"
        )
        if "area" not in [r[1] for r in db.execute("PRAGMA table_info(apartments)")]:
            # Existing source has no area. Leave unknown areas NULL rather than invent data.
            db.execute("ALTER TABLE apartments ADD COLUMN area REAL CHECK(area IS NULL OR area>0)")
        for migration in migration_files():
            if not db.execute("SELECT 1 FROM schema_migrations WHERE name=?", (migration.name,)).fetchone():
                # Rebuild migrations and their ledger entry must commit together.
                # executescript commits pending work first, so include the complete
                # transaction in the script rather than relying on the connection context.
                name = migration.name.replace("'", "''")
                try:
                    db.executescript(
                        "BEGIN IMMEDIATE;\n"
                        + migration.read_text(encoding="utf-8")
                        + f"\nINSERT INTO schema_migrations(name) VALUES('{name}');\nCOMMIT;"
                    )
                except Exception:
                    db.rollback()
                    raise
        if demo and not db.execute("SELECT 1 FROM schema_migrations WHERE name='demo-users-v1'").fetchone():
            from werkzeug.security import generate_password_hash

            ids = {}
            for username, password, role in DEMO_ACCOUNTS:
                if db.execute("SELECT 1 FROM users WHERE username=?", (username,)).fetchone():
                    raise RuntimeError(f"Cannot seed demo: username {username} already exists.")
                cur = db.execute(
                    "INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",
                    (username, generate_password_hash(password), role),
                )
                ids[role] = cur.lastrowid
            db.execute("UPDATE residents SET user_id=? WHERE resident_id=1", (ids["resident"],))
            db.execute("UPDATE technicians SET user_id=?,active=1 WHERE technician_id=1", (ids["technician"],))
            db.execute("INSERT INTO schema_migrations(name) VALUES('demo-users-v1')")
        db.commit()
        result = db.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise RuntimeError(result)
        if live_payments():
            assert_no_public_demo_passwords(db)
    return destination


def ensure_env():
    env_path = ROOT / ".env"
    content = (
        env_path.read_text(encoding="utf-8")
        if env_path.exists()
        else (ROOT / ".env.example").read_text(encoding="utf-8")
    )
    lines = content.splitlines()
    for name in ("JWT_SECRET", "SERVICE_TOKEN", "SEPAY_WEBHOOK_API_KEY"):
        idx = next((i for i, line in enumerate(lines) if line.startswith(name + "=")), None)
        if idx is None:
            lines.append(name + "=" + secrets.token_urlsafe(48))
        elif not lines[idx].split("=", 1)[1].strip():
            lines[idx] = name + "=" + secrets.token_urlsafe(48)
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Create three local demo login accounts once")
    parser.add_argument("--container", action="store_true", help="Docker start-up: settings come from the environment")
    args = parser.parse_args()
    if args.container:
        from shared.config import database_path

        # A new database gets the published demo logins unless INIT_DEMO says otherwise.
        # An existing database is left alone, and SEPAY_ENV=live refuses them either way.
        setting = os.getenv("INIT_DEMO", "").strip().lower()
        ensure_generated_secrets()
        initialize(demo=setting == "true" or (not setting and not database_path().exists()))
        share_data_directory()
        sys.exit()
    ensure_env()
    path = initialize(demo=args.demo)
    print(f"Database ready: {path}")
    if args.demo and not live_payments():
        print("Demo: admin / Admin@12345 | resident / Resident@12345 | technician / Tech@12345")
