"""Build a database from the public sample data. Refuses to overwrite an existing file."""

from contextlib import closing
from pathlib import Path
import sqlite3

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/demo.sql"


def prepare(destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive creation protects a developer's existing source database.
    with destination.open("xb"):
        pass
    try:
        with closing(sqlite3.connect(destination)) as db:
            db.executescript(FIXTURE.read_text(encoding="utf-8"))
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("Invalid fixture database")
            if db.execute("PRAGMA foreign_key_check").fetchall():
                raise RuntimeError("Fixture contains foreign-key violations")
    except BaseException:
        destination.unlink(missing_ok=True)
        raise
    return destination
