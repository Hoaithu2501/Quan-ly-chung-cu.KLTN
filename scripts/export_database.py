"""Make a self-contained copy of a SQLite database, including committed WAL data.

The source is opened read-only and an existing file is never overwritten.
"""

from contextlib import closing
from pathlib import Path
import sqlite3


def create_snapshot(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    if source == destination:
        raise ValueError("Export must not replace the source database.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=15)) as src:
        # Exclusive creation protects previous exports and unrelated databases.
        with destination.open("xb"):
            pass
        with closing(sqlite3.connect(destination)) as dst:
            src.backup(dst)
            dst.execute("PRAGMA journal_mode=DELETE")
            if dst.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                raise RuntimeError("Export integrity check failed.")
            if dst.execute("PRAGMA foreign_key_check").fetchone():
                raise RuntimeError("Export has foreign-key violations.")
    return destination
