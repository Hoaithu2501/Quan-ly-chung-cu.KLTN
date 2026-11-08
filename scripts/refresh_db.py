"""Import source catalogs without replacing accounts or application transactions.

The default command is a preview. SQLite backups include committed WAL data.
Stop application services before applying an import and schema migrations.
"""
import argparse
from contextlib import closing
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
TABLES = ("apartments", "faq_knowledge_base", "locations", "notifications")


def _path(value):
    path = Path(value)
    return (path if path.is_absolute() else ROOT / path).resolve()


def _read_only(path):
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=15)


def snapshot(source, destination):
    """Create a standalone DB snapshot, including committed source WAL changes."""
    source, destination = _path(source), _path(destination)
    if source == destination:
        raise ValueError("Snapshot destination must differ from its source.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(_read_only(source)) as src:
        # Never silently overwrite an existing DB through the export option.
        destination.open("xb").close()
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
            # A backup can inherit WAL mode. Make the export self-contained so
            # read-only Docker mounts never need to create -wal/-shm sidecars.
            dst.execute("PRAGMA journal_mode=DELETE")
            if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Source database integrity check failed.")
    return destination


def _columns(db, table):
    rows = db.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [row[1] for row in rows], [row[1] for row in rows if row[5]]


def _merge_catalog(src, dst, table):
    columns, keys = _columns(src, table)
    destination_columns, destination_keys = _columns(dst, table)
    if not columns or len(keys) != 1 or keys != destination_keys:
        raise RuntimeError(f"Missing or incompatible table: {table}")
    columns = [column for column in columns if column in destination_columns]
    key = keys[0]
    # Occupancy follows active contracts; source metadata must not reset it.
    editable = [column for column in columns if column != key and not (table == "apartments" and column == "status")]
    quoted = ",".join(f'"{column}"' for column in columns)
    result = {"inserted": 0, "updated": 0, "unchanged": 0}
    for row in src.execute(f'SELECT {quoted} FROM "{table}" ORDER BY "{key}"'):
        values = dict(zip(columns, row))
        existing = dst.execute(f'SELECT {quoted} FROM "{table}" WHERE "{key}"=?', (values[key],)).fetchone()
        if existing is None:
            dst.execute(f'INSERT INTO "{table}" ({quoted}) VALUES ({",".join("?" for _ in columns)})', row)
            result["inserted"] += 1
        elif any(existing[columns.index(column)] != values[column] for column in editable):
            updates = ",".join(f'"{column}"=?' for column in editable)
            dst.execute(f'UPDATE "{table}" SET {updates} WHERE "{key}"=?', [values[column] for column in editable] + [values[key]])
            result["updated"] += 1
        else:
            result["unchanged"] += 1
    return result


def _merge_notifications(src, dst):
    columns, keys = _columns(src, "notifications")
    destination_columns, destination_keys = _columns(dst, "notifications")
    if keys != ["notification_id"] or destination_keys != keys or any(column not in destination_columns for column in columns):
        raise RuntimeError("Missing or incompatible table: notifications")
    dst.execute("""CREATE TABLE IF NOT EXISTS source_notification_imports (
        source_notification_id INTEGER PRIMARY KEY,
        notification_id INTEGER NOT NULL UNIQUE REFERENCES notifications(notification_id)
    )""")
    protected = set()
    for table in ("notification_events", "notification_audience"):
        if dst.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone():
            protected.update(row[0] for row in dst.execute(f'SELECT notification_id FROM "{table}"'))
    fields = [column for column in columns if column != "notification_id"]
    quoted = ",".join(f'"{column}"' for column in fields)
    assignments = ",".join(f'"{column}"=?' for column in fields)
    matches = " AND ".join(f'"{column}" IS ?' for column in fields)
    result = {"inserted": 0, "updated": 0, "unchanged": 0, "remapped": 0}
    for row in src.execute(f'SELECT notification_id,{quoted} FROM notifications ORDER BY notification_id'):
        source_id, values = row[0], row[1:]
        mapping = dst.execute("SELECT notification_id FROM source_notification_imports WHERE source_notification_id=?", (source_id,)).fetchone()
        target_id = mapping[0] if mapping else None
        if target_id in protected:
            # An imported notice later used by an application event must remain intact.
            dst.execute("DELETE FROM source_notification_imports WHERE source_notification_id=?", (source_id,))
            target_id = None
        if target_id is None:
            # IDs may have been independently allocated by the source and server.
            # Reuse only identical, unclaimed, non-event records on the first import.
            candidates = dst.execute(f"SELECT notification_id FROM notifications WHERE {matches} AND notification_id NOT IN (SELECT notification_id FROM source_notification_imports) ORDER BY notification_id", values).fetchall()
            target_id = next((candidate[0] for candidate in candidates if candidate[0] not in protected), None)
            if target_id is None:
                occupied = dst.execute("SELECT 1 FROM notifications WHERE notification_id=?", (source_id,)).fetchone()
                if occupied:
                    target_id = dst.execute(f'INSERT INTO notifications ({quoted}) VALUES ({",".join("?" for _ in fields)})', values).lastrowid
                else:
                    dst.execute(f'INSERT INTO notifications (notification_id,{quoted}) VALUES ({",".join("?" for _ in columns)})', (source_id, *values))
                    target_id = source_id
                result["inserted"] += 1
            else:
                result["unchanged"] += 1
            dst.execute("INSERT INTO source_notification_imports VALUES (?,?)", (source_id, target_id))
        else:
            existing = dst.execute(f'SELECT {quoted} FROM notifications WHERE notification_id=?', (target_id,)).fetchone()
            if existing != values:
                dst.execute(f'UPDATE notifications SET {assignments} WHERE notification_id=?', (*values, target_id))
                result["updated"] += 1
            else:
                result["unchanged"] += 1
        if target_id != source_id:
            result["remapped"] += 1
    return result


def _merge(src, dst, tables):
    changes = {}
    for table in tables:
        changes[table] = _merge_notifications(src, dst) if table == "notifications" else _merge_catalog(src, dst, table)
    policy = {"reapplied": False, "changed_rows": 0}
    ledger = dst.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'").fetchone()
    if ledger and dst.execute("SELECT 1 FROM schema_migrations WHERE name='ui_policy_content.sql'").fetchone():
        # A later import must not replace the current parking policy with old FAQ
        # content or restore inconsistent management labels from the source.
        # execute statements individually: executescript would commit this import.
        before = dst.total_changes
        statement = ""
        for line in (ROOT / "migrations" / "ui_policy_content.sql").read_text(encoding="utf-8").splitlines(keepends=True):
            statement += line
            if sqlite3.complete_statement(statement):
                dst.execute(statement)
                statement = ""
        if statement.strip():
            dst.execute(statement)
        policy = {"reapplied": True, "changed_rows": dst.total_changes - before}
    if dst.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
        raise RuntimeError("Destination integrity check failed; import rolled back.")
    if dst.execute("PRAGMA foreign_key_check").fetchone():
        raise RuntimeError("Destination foreign-key check failed; import rolled back.")
    return changes, policy


def refresh_database(path=None, source=None, tables=TABLES, apply=False, backup_dir=None):
    from shared.config import database_path
    destination = _path(path or database_path())
    source = _path(source or ROOT / "QLCC.db")
    tables = tuple(dict.fromkeys(tables))
    if not tables or any(table not in TABLES for table in tables):
        raise ValueError("Only source catalogs and notifications may be refreshed.")
    if destination in (source, (ROOT / "QLCC.db").resolve()):
        raise ValueError("Application destination must not be the source QLCC.db.")
    if not destination.is_file():
        raise ValueError("Initialize the application database before refreshing it.")
    # Freeze source input once; reading .db alone would miss committed WAL data.
    with tempfile.TemporaryDirectory(prefix="qlcc-source-") as directory:
        source_snapshot = snapshot(source, Path(directory) / "source.db")
        with closing(_read_only(source_snapshot)) as src:
            if not apply:
                preview = snapshot(destination, Path(directory) / "preview.db")
                with closing(sqlite3.connect(preview)) as dst:
                    dst.execute("PRAGMA foreign_keys=ON")
                    with dst:
                        changes, policy = _merge(src, dst, tables)
                return {"applied": False, "changes": changes, "content_policy": policy, "backup": None}
            with closing(sqlite3.connect(destination, timeout=15)) as dst:
                dst.execute("PRAGMA foreign_keys=ON")
                dst.execute("BEGIN IMMEDIATE")
                try:
                    # This write reservation blocks concurrent writes while a separate
                    # read connection captures the exact state preceding the import.
                    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
                    folder = _path(backup_dir) if backup_dir else destination.parent / "backups"
                    backup = snapshot(destination, folder / f"{destination.stem}-before-refresh-{stamp}.db")
                    changes, policy = _merge(src, dst, tables)
                    dst.commit()
                except Exception:
                    dst.rollback()
                    raise
                return {"applied": True, "changes": changes, "content_policy": policy, "backup": str(backup)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", help="Application DB path (defaults to DATABASE_PATH)")
    parser.add_argument("--source", help="Updated source DB path (defaults to root QLCC.db)")
    parser.add_argument("--tables", nargs="+", choices=TABLES, default=TABLES)
    parser.add_argument("--apply", action="store_true", help="Apply changes with an automatic SQLite backup; otherwise preview")
    parser.add_argument("--backup-dir", help="Backup folder (defaults to backups/ beside the application DB)")
    parser.add_argument("--snapshot-to", help="Export a consistent source snapshot for Docker, then exit")
    args = parser.parse_args()
    if args.snapshot_to:
        print(json.dumps({"snapshot": str(snapshot(args.source or ROOT / "QLCC.db", args.snapshot_to))}))
        return
    print(json.dumps(refresh_database(args.database, args.source, args.tables, args.apply, args.backup_dir), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
