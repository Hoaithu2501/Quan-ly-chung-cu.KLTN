"""Keep rotating, verified copies of the application database outside its volume.

Each copy is a self-contained SQLite backup that has passed integrity and
foreign-key checks. Only files named QLCC-auto-*.db are ever rotated, so manual
backups kept in the same folder are never removed.
"""

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sqlite3
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.export_database import create_snapshot  # noqa: E402

PREFIX = "QLCC-auto-"


def backup_once(source, folder, keep):
    folder = Path(folder)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    path = create_snapshot(source, folder / f"{PREFIX}{stamp}.db")
    for stale in sorted(folder.glob(PREFIX + "*.db"), reverse=True)[keep:]:
        stale.unlink()
    return path


def main():
    from shared.config import database_path

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=str(ROOT / "backups"))
    parser.add_argument("--keep", type=int, default=14, help="Number of automatic backups to retain")
    parser.add_argument("--loop", action="store_true", help="Keep running and back up on an interval")
    parser.add_argument("--interval-hours", type=float, default=24)
    args = parser.parse_args()
    if args.keep < 1 or args.interval_hours <= 0:
        parser.error("--keep and --interval-hours must be positive")
    source = os.getenv("DATABASE_PATH") and Path(os.environ["DATABASE_PATH"]) or database_path()
    while True:
        try:
            print(f"Backup ready: {backup_once(source, args.output, args.keep)}", flush=True)
        except (OSError, RuntimeError, sqlite3.Error) as exc:
            print(f"Backup failed: {exc}", file=sys.stderr, flush=True)
            if not args.loop:
                return 1
        if not args.loop:
            return 0
        time.sleep(args.interval_hours * 3600)


if __name__ == "__main__":
    sys.exit(main())
