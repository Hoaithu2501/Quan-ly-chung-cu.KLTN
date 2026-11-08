"""Preview or apply the curated FAQ seed; never replaces the application DB."""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
SQL_PATH = ROOT / "scripts/sql/chatbot_faq_v3.sql"


def _path(value):
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def _connect(path, mode="ro"):
    return sqlite3.connect(path.as_uri() + f"?mode={mode}", uri=True, timeout=15)


def _rows(db):
    columns = {row[1] for row in db.execute("PRAGMA table_info(faq_knowledge_base)")}
    if not {"faq_id", "category", "question", "answer"} <= columns:
        raise ValueError("Missing or incompatible faq_knowledge_base table; initialize the application DB first.")
    return {row[0]: row[1:] for row in db.execute(
        "SELECT faq_id, category, question, answer FROM faq_knowledge_base ORDER BY faq_id")}


def execute_seed(db, script=None):
    """Run SQL within the caller's transaction without executescript's implicit commit."""
    before = _rows(db)
    pending = ""
    for line in (script if script is not None else SQL_PATH.read_text(encoding="utf-8")).splitlines(True):
        pending += line
        if sqlite3.complete_statement(pending):
            db.execute(pending)
            pending = ""
    if pending.strip():
        # A final comment is accepted by SQLite; an incomplete statement fails.
        db.execute(pending)
    after = _rows(db)
    inserted = [key for key in after if key not in before]
    updated = [key for key in before if before[key] != after.get(key)]
    duplicates = [dict(question=row[0], count=row[1]) for row in db.execute(
        "SELECT question, COUNT(*) FROM faq_knowledge_base GROUP BY question HAVING COUNT(*) > 1")]
    return {"inserted": len(inserted), "updated": len(updated),
            "unchanged": len(before) - len(updated), "total": len(after),
            "changes": [{"faq_id": key, "action": "insert" if key in inserted else "update",
                         "question": after[key][1],
                         "previous_answer": before[key][2] if key in before else None,
                         "answer": after[key][2]} for key in [*updated, *inserted]],
            "duplicate_questions": duplicates}


def seed_database(database, *, apply=False, backup_dir=None):
    target = _path(database)
    sources = [(ROOT / "QLCC.db").resolve()]
    if os.getenv("DATABASE_SEED_PATH"):
        sources.append(_path(os.environ["DATABASE_SEED_PATH"]))
    if any(target == source or (target.is_file() and source.is_file() and target.samefile(source))
           for source in sources):
        raise ValueError("Do not target source QLCC.db. Use the runtime database or a separate working copy.")
    if not target.is_file():
        raise ValueError(f"Database does not exist: {target}")
    if not apply:
        with closing(_connect(target)) as source, closing(sqlite3.connect(":memory:")) as preview:
            source.backup(preview)
            preview.execute("BEGIN")
            try:
                result = execute_seed(preview)
            finally:
                preview.rollback()
        return {"mode": "preview", "database": str(target), "backup": None, **result}

    backup_root = _path(backup_dir) if backup_dir else target.parent / "backups"
    with closing(_connect(target, "rw")) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("BEGIN IMMEDIATE")
        try:
            _rows(db)
            # The reserved write lock prevents changes while a separate reader
            # snapshots committed data, including WAL, before any seed statement.
            with closing(_connect(target)) as source, closing(sqlite3.connect(":memory:")) as snapshot:
                source.backup(snapshot)
                backup_root.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                backup = backup_root / f"QLCC-before-chatbot-faq-{stamp}.db"
                backup.open("xb").close()
                with closing(sqlite3.connect(backup)) as destination:
                    snapshot.backup(destination)
                    destination.execute("PRAGMA journal_mode=DELETE")
                    if destination.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                        raise ValueError("Backup integrity check failed; no changes applied.")
            result = execute_seed(db)
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Database integrity check failed; seed rolled back.")
            db.commit()
        except Exception:
            db.rollback()
            raise
    return {"mode": "applied", "database": str(target), "backup": str(backup), **result}


def main(argv=None):
    from shared.config import database_path

    parser = argparse.ArgumentParser(description="Preview FAQ v3 in memory; --apply creates a backup and saves it.")
    parser.add_argument("--database", default=str(database_path()), help="Runtime database path; default DATABASE_PATH.")
    parser.add_argument("--apply", action="store_true", help="Create a backup and commit the FAQ changes.")
    parser.add_argument("--backup-dir", help="Backup directory; default <database directory>/backups.")
    args = parser.parse_args(argv)
    try:
        result = seed_database(args.database, apply=args.apply, backup_dir=args.backup_dir)
    except (ValueError, OSError, sqlite3.Error) as exc:
        parser.exit(1, f"FAQ seed failed: {exc}\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    main()
