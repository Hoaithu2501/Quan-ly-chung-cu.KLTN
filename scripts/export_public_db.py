"""Export database/QLCC_an_danh.db: the running system's data with every personal detail replaced.

Rows, amounts, dates, statuses and links between tables stay as they are, so the file matches the
system and the screenshots in the report. Who the people are does not survive: names, usernames,
phones, ID numbers, emails, real number plates, bank accounts, IP addresses, device tokens and
attachments are replaced or removed, and the result is scanned for anything left behind.

    docker compose exec -T backup python scripts/backup_db.py --output /backups
    python scripts/export_public_db.py                 # newest backup in backups/
    python scripts/export_public_db.py --source FILE   # or a given copy

Only a copy is read; the live database is never opened.
"""

import argparse
from contextlib import closing
import os
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "database" / "QLCC_an_danh.db"
HIDDEN = "[đã ẩn]"
FAKE_ACCOUNT = "0000000000"
FAKE_ACCOUNT_NAME = "BAN QUAN LY AN CU"
# Demo account names are product words, not people; renaming them would also rewrite role names in the data.
SYSTEM_USERNAMES = {"admin", "resident", "technician", "service"}
USERNAME_PREFIX = {"admin": "bql", "resident": "cudan", "technician": "ktv"}
STAFF_NAME = {"admin": "Quản lý", "resident": "Cư dân", "technician": "Kỹ thuật viên"}
# Phones (10), old and new ID cards (9, 12) and bank accounts (up to 14) in free text.
LONG_NUMBER = re.compile(r"(?<!\d)\d{9,14}(?!\d)")
# The registration notice for management: "<full name> (tài khoản <username>, SĐT ...)". It names the
# person even when the name is one word, which free text cannot search for safely ("Ánh" in "phản ánh").
REGISTRATION = re.compile(r"(?m)^([^\n()]{1,80}?) \(tài khoản ([\w.-]+), SĐT")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Operational queues and leftovers with nothing a reviewer needs; their payloads repeat personal text.
CLEARED = ("billing_outbox", "complaint_outbox", "notification_push_roles", "notification_push_tokens")
DROPPED = ("source_notification_imports",)
# Left alone by the free-text pass: generated identifiers that tie rows together and hold no names,
# and the fields already given made-up values above (a fake phone or account is a long number too).
UNTOUCHED_COLUMNS = {
    "order_id", "event_id", "request_key", "transfer_content", "path",
    "phone", "password_hash", "account_number", "provider_id", "bank_reference", "transaction_code", "plate_number",
}


def plate_key(plate):
    return re.sub(r"[^0-9A-Z]", "", str(plate or "").upper())


def text_columns(db):
    for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        columns = [row[1] for row in db.execute(f'PRAGMA table_info("{table}")') if (row[2] or "").upper() in ("TEXT", "")]
        if columns:
            yield table, columns


class Anonymizer:
    def __init__(self, db):
        self.db = db
        self.replacements = {}  # real text (lower case) -> stand-in, applied inside free text
        self.secrets = set()  # every real value removed, for the final scan
        self.short_names = 0
        self.display_names = {}  # new username -> the stand-in name shown for that account

    def remember(self, real, stand_in, in_text=True):
        real = str(real or "").strip()
        if not real:
            return
        self.secrets.add(real)
        if in_text:
            self.replacements.setdefault(real.lower(), stand_in)

    def name(self, real, stand_in):
        """One person keeps one stand-in everywhere; very short names are not searched for in free text."""
        real = str(real or "").strip()
        if not real:
            return None
        known = self.replacements.get(real.lower())
        if known:
            return known
        searchable = " " in real and len(real) >= 5
        self.short_names += not searchable
        self.remember(real, stand_in, in_text=searchable)
        return stand_in

    def people(self):
        db = self.db
        users = db.execute("SELECT user_id,username,email,phone,role,full_name,id_card FROM users ORDER BY user_id").fetchall()
        # Two passes, so a new name never collides with an old one still in the table.
        db.execute("UPDATE users SET username='~'||user_id")
        for user_id, username, email, phone, role, full_name, id_card in users:
            new = username if username in SYSTEM_USERNAMES else f"{USERNAME_PREFIX.get(role, 'tk')}{user_id:02d}"
            if new != username:
                self.remember(username, new)
            self.remember(email, f"{new}@example.invalid")
            # Known numbers of any length, as typed in test data; the long-number rule catches the rest.
            self.remember(phone, HIDDEN)
            self.remember(id_card, HIDDEN)
            staff = self.name(full_name, f"{STAFF_NAME.get(role, 'Tài khoản')} {user_id:02d}")
            db.execute(
                "UPDATE users SET username=?,password_hash='!anonymized-account',email=?,phone=?,full_name=?,id_card=NULL "
                "WHERE user_id=?",
                (new, f"{new}@example.invalid" if email else None, f"0900{user_id:06d}" if phone else None, staff, user_id),
            )
        for resident_id, full_name, phone, id_card in db.execute(
            "SELECT resident_id,full_name,phone,id_card FROM residents ORDER BY resident_id"
        ).fetchall():
            self.remember(phone, HIDDEN)
            self.remember(id_card, HIDDEN)
            db.execute(
                "UPDATE residents SET full_name=?,phone=?,id_card=NULL WHERE resident_id=?",
                (self.name(full_name, f"Cư dân {resident_id:02d}"), f"0910{resident_id:06d}" if phone else None, resident_id),
            )
        for technician_id, full_name in db.execute(
            "SELECT technician_id,full_name FROM technicians ORDER BY technician_id"
        ).fetchall():
            db.execute(
                "UPDATE technicians SET full_name=? WHERE technician_id=?",
                (self.name(full_name, f"Kỹ thuật viên {technician_id:02d}"), technician_id),
            )
        # The name each account now shows: its resident profile, else the staff name, else the username.
        for username, shown in db.execute(
            "SELECT u.username,COALESCE((SELECT r.full_name FROM residents r WHERE r.user_id=u.user_id "
            "ORDER BY r.resident_id LIMIT 1),u.full_name,u.username) FROM users u"
        ):
            self.display_names[username] = shown

    def plates(self):
        """Real number plates become made-up ones; generated codes such as B804-XD-2 name a room, not a person."""
        fake = {}
        for vehicle_id, plate in self.db.execute(
            "SELECT vehicle_id,plate_number FROM vehicles WHERE plate_number IS NOT NULL ORDER BY vehicle_id"
        ).fetchall():
            if re.search(r"-XD-\d+$", plate, re.IGNORECASE):
                continue
            # The same vehicle registered twice keeps one made-up plate.
            stand_in = fake.setdefault(plate_key(plate), f"99X9-{vehicle_id:03d}.{vehicle_id % 100:02d}")
            self.remember(plate, stand_in)
            self.db.execute("UPDATE vehicles SET plate_number=? WHERE vehicle_id=?", (stand_in, vehicle_id))

    def payments(self):
        db = self.db
        for table in ("bank_payment_intents", "bank_transactions"):
            for (account,) in db.execute(f"SELECT DISTINCT account_number FROM {table}"):
                self.remember(account, FAKE_ACCOUNT, in_text=False)
        for (holder,) in db.execute("SELECT DISTINCT account_name FROM bank_payment_intents"):
            self.remember(holder, FAKE_ACCOUNT_NAME)
        db.execute("UPDATE bank_payment_intents SET account_number=?,account_name=?", (FAKE_ACCOUNT, FAKE_ACCOUNT_NAME))
        providers = {}
        for (provider,) in db.execute(
            "SELECT provider_id FROM bank_transactions UNION SELECT provider_id FROM bank_transaction_aliases ORDER BY 1"
        ):
            providers[provider] = f"SEPAY-{len(providers) + 1:04d}"
        for transaction_id, provider, reference in db.execute(
            "SELECT transaction_id,provider_id,bank_reference FROM bank_transactions"
        ).fetchall():
            self.remember(reference, f"REF{transaction_id:06d}")
            db.execute(
                "UPDATE bank_transactions SET provider_id=?,account_number=?,bank_reference=? WHERE transaction_id=?",
                (providers[provider], FAKE_ACCOUNT, f"REF{transaction_id:06d}" if reference else "", transaction_id),
            )
        for provider, stand_in in providers.items():
            db.execute("UPDATE bank_transaction_aliases SET provider_id=? WHERE provider_id=?", (stand_in, provider))
        for kind, prefix in (("monthly", "HD"), ("semiannual", "DV")):
            db.execute(
                f"UPDATE {kind}_payments SET transaction_code='{prefix}-GD'||printf('%04d',payment_id) "
                "WHERE transaction_code IS NOT NULL"
            )

    def free_text(self, allowed_numbers):
        """Known names, usernames, plates and holders become their stand-ins; long numbers and emails are hidden."""
        keys = sorted(self.replacements, key=len, reverse=True)
        known = re.compile(
            "|".join(rf"(?<![\w.@]){re.escape(key)}(?![\w@])" for key in keys), re.IGNORECASE
        ) if keys else None

        def registered(match):
            shown = self.display_names.get(match.group(2))
            if shown is None:
                # An account renamed or removed since: its old username is personal too.
                return f"{HIDDEN} (tài khoản {HIDDEN}, SĐT"
            return f"{shown} (tài khoản {match.group(2)}, SĐT"

        def clean(value):
            if known:
                value = known.sub(lambda match: self.replacements[match.group(0).lower()], value)
            # After the usernames above were replaced, so the account named here is the new one.
            value = REGISTRATION.sub(registered, value)
            value = LONG_NUMBER.sub(lambda match: match.group(0) if match.group(0) in allowed_numbers else HIDDEN, value)
            return EMAIL.sub(lambda match: match.group(0) if match.group(0).endswith("@example.invalid") else HIDDEN, value)

        for table, columns in text_columns(self.db):
            if table in ("faq_knowledge_base", "locations", "schema_migrations"):
                continue  # Published policy text and migration names.
            for column in columns:
                if column in UNTOUCHED_COLUMNS:
                    continue
                rows = self.db.execute(
                    f'SELECT rowid,"{column}" FROM "{table}" WHERE typeof("{column}")=\'text\''
                ).fetchall()
                for rowid, value in rows:
                    cleaned = clean(value)
                    if cleaned != value:
                        self.db.execute(f'UPDATE "{table}" SET "{column}"=? WHERE rowid=?', (cleaned, rowid))

    def leftovers(self):
        """Real values of five characters or more still found anywhere: none is allowed."""
        found = []
        needles = [secret.lower() for secret in self.secrets if len(secret) >= 5]
        for table, columns in text_columns(self.db):
            for column in columns:
                for (value,) in self.db.execute(f'SELECT "{column}" FROM "{table}" WHERE typeof("{column}")=\'text\''):
                    lowered = value.lower()
                    if any(needle in lowered for needle in needles):
                        found.append(f"{table}.{column}")
                        break
        return sorted(set(found))


def anonymize(db):
    """Triggers are set aside meanwhile: the audit trail refuses edits, and payment triggers would
    recalculate invoices. They are put back unchanged, so the copy keeps the system's exact rules."""
    triggers = db.execute("SELECT name,sql FROM sqlite_master WHERE type='trigger' ORDER BY rowid").fetchall()
    for name, _ in triggers:
        db.execute(f'DROP TRIGGER "{name}"')
    work = replace_personal_data(db)
    for _, sql in triggers:
        db.execute(sql)
    return work


def replace_personal_data(db):
    allowed_numbers = set()
    for (text,) in db.execute("SELECT answer FROM faq_knowledge_base UNION ALL SELECT description FROM locations"):
        allowed_numbers.update(LONG_NUMBER.findall(text or ""))
    for table in CLEARED:
        db.execute(f'DELETE FROM "{table}"')
    for table in DROPPED:
        db.execute(f'DROP TABLE IF EXISTS "{table}"')
    db.execute("UPDATE audit_log SET client_ip=NULL")
    db.execute("UPDATE complaints SET attachments=NULL")
    work = Anonymizer(db)
    work.people()
    work.plates()
    work.payments()
    work.free_text(allowed_numbers)
    # Known usernames were replaced above; any other belongs to an account renamed or removed since.
    db.execute(
        "UPDATE audit_log SET actor_username=? WHERE actor_username IS NOT NULL "
        "AND actor_username NOT IN (SELECT username FROM users) "
        f"AND actor_username NOT IN ({','.join('?' * len(SYSTEM_USERNAMES))})",
        (HIDDEN, *sorted(SYSTEM_USERNAMES)),
    )
    left = work.leftovers()
    if left:
        raise RuntimeError("Personal data is still present in: " + ", ".join(left))
    return work


def newest_backup():
    copies = sorted((ROOT / "backups").glob("QLCC-auto-*.db"))
    if not copies:
        raise SystemExit("No backup in backups/. Run: docker compose exec -T backup python scripts/backup_db.py --output /backups")
    return copies[-1]


def export(source, destination=DESTINATION):
    """Built beside the old file and swapped in only when complete and clean."""
    source, destination = Path(source).resolve(), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    building = destination.with_name(destination.name + ".building")
    building.unlink(missing_ok=True)
    try:
        with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original, closing(
            sqlite3.connect(building)
        ) as copy:
            original.backup(copy)
        with closing(sqlite3.connect(building)) as db:
            work = anonymize(db)
            db.commit()
            db.execute("PRAGMA journal_mode=DELETE")
            db.execute("VACUUM")
            if db.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise RuntimeError("The exported database failed its integrity check.")
            if db.execute("PRAGMA foreign_key_check").fetchone():
                raise RuntimeError("The exported database has broken links between tables.")
        os.replace(building, destination)
    finally:
        building.unlink(missing_ok=True)
    return destination, work


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", help="A copy of the database (default: newest backups/QLCC-auto-*.db)")
    args = parser.parse_args()
    source = Path(args.source) if args.source else newest_backup()
    path, work = export(source)
    print(f"Exported {path.relative_to(ROOT)} from {source.name} ({path.stat().st_size // 1024} KB).")
    print(f"Replaced {len(work.secrets)} personal values; {work.short_names} one-word names were replaced only in their own field.")
    sys.exit(0)
