import sqlite3
from flask import g, current_app
from shared.config import database_path


def get_db():
    if "db" not in g:
        path = current_app.config.get("DATABASE_PATH") or database_path()
        g.db = sqlite3.connect(str(path), timeout=15)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys=ON")
        g.db.execute("PRAGMA busy_timeout=15000")
    return g.db


def placeholders(values):
    """One "?" per value, for an SQL IN list or VALUES clause."""
    return ",".join("?" for _ in values)


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
