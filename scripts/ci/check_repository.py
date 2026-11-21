"""Reject runtime data and private credentials accidentally tracked by Git."""

from contextlib import closing
from pathlib import Path, PurePosixPath
import re
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_KEY = re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
# The one database allowed in Git: the anonymized copy for reviewers (scripts/export_public_db.py).
PUBLIC_DATABASE = "database/QLCC_an_danh.db"
# Each query counts rows that would show the file was not anonymized.
NOT_ANONYMIZED = (
    "SELECT COUNT(*) FROM users WHERE password_hash NOT LIKE '!%'",
    "SELECT COUNT(*) FROM users WHERE email IS NOT NULL AND email NOT LIKE '%@example.invalid'",
    "SELECT COUNT(*) FROM users WHERE id_card IS NOT NULL",
    "SELECT COUNT(*) FROM residents WHERE id_card IS NOT NULL",
    "SELECT COUNT(*) FROM notification_push_tokens",
    "SELECT COUNT(*) FROM audit_log WHERE client_ip IS NOT NULL",
    "SELECT COUNT(*) FROM complaints WHERE attachments IS NOT NULL",
    "SELECT COUNT(*) FROM bank_transactions WHERE account_number<>'0000000000'",
    "SELECT COUNT(*) FROM bank_payment_intents WHERE account_number<>'0000000000'",
)


def anonymized_copy(path):
    """True only when no account can sign in and no ID, email, IP, device token, attachment or bank account remains.

    A copy of the live database put at this path fails, so it can never be pushed by mistake.
    """
    try:
        with closing(sqlite3.connect(Path(path).resolve().as_uri() + "?mode=ro", uri=True)) as db:
            return not any(db.execute(query).fetchone()[0] for query in NOT_ANONYMIZED)
    except sqlite3.Error:
        return False


def check_repository():
    git_root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    if git_root.resolve() != ROOT.resolve():
        raise RuntimeError("The Git repository must be rooted at QLCC, not its parent directory")
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    problems = []
    for filename in filter(None, files):
        path = PurePosixPath(filename)
        name = path.name.lower()
        if filename == PUBLIC_DATABASE:
            if not anonymized_copy(ROOT / filename):
                problems.append(filename + ": must be produced by scripts/export_public_db.py (anonymized)")
            continue
        private = (
            (name.startswith(".env") and name != ".env.example")
            or any(
                part in {".venv", "node_modules", "backups", "logs", ".runtime", "test-results", "__pycache__"}
                for part in path.parts
            )
            or (path.parts[0] == "secrets" and name != ".gitkeep")
            or name.endswith((".db", ".db-wal", ".db-shm", ".db-journal", ".sqlite", ".sqlite3", ".pem", ".key"))
            or name == "firebase-credentials.json"
        )
        if private:
            problems.append(filename + ": runtime data/credential file")
            continue
        local = ROOT / filename
        if local.is_file() and PRIVATE_KEY.search(local.read_bytes()):
            problems.append(filename + ": private key content")
    if problems:
        raise RuntimeError("Remove these files from Git before pushing:\n" + "\n".join(problems))
    print(f"Repository check OK: {len([f for f in files if f])} tracked files, no database/runtime credentials.")


if __name__ == "__main__":
    check_repository()
