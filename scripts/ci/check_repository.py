"""Reject runtime data and private credentials accidentally tracked by Git."""

from pathlib import Path, PurePosixPath
import re
import subprocess

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_KEY = re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")


def check_repository():
    git_root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    if git_root.resolve() != ROOT.resolve():
        raise RuntimeError("The Git repository must be rooted at QLCC, not its parent directory")
    files = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode("utf-8").split("\0")
    problems = []
    for filename in filter(None, files):
        path = PurePosixPath(filename)
        name = path.name.lower()
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
