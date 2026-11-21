"""database/QLCC_an_danh.db holds no personal data and keeps the structure the migrations build."""

from contextlib import closing
import sqlite3

from scripts.ci.check_repository import anonymized_copy
from scripts.export_public_db import DESTINATION, export
from scripts.init_db import initialize

SECRETS = ("Nguyễn Văn Bí Mật", "Trần Thị Riêng Tư", "bi.mat", "bimat@gmail.com", "0912345678", "1234567",
           "079099001122", "29A1-555.55", "0123456789", "FT26324123456", "NGUYEN VAN CHU TAI KHOAN", "203.0.113.5")


def objects(path):
    """Tables, views, indexes and triggers: what must match the code."""
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        return db.execute(
            "SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type,name"
        ).fetchall()


def all_text(path):
    with closing(sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)) as db:
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")]
        return "\n".join(
            str(value)
            for table in tables
            for row in db.execute(f'SELECT * FROM "{table}"')
            for value in row
            if isinstance(value, str)
        )


def test_committed_copy_is_anonymized_and_matches_the_current_migrations(tmp_path):
    assert DESTINATION.is_file(), "Run: python scripts/export_public_db.py"
    assert anonymized_copy(DESTINATION)
    fresh = initialize(tmp_path / "fresh.db")
    assert objects(DESTINATION) == objects(fresh), (
        "database/QLCC_an_danh.db is out of date: deploy, take a backup, run python scripts/export_public_db.py "
        "and commit the file"
    )


def test_export_replaces_every_personal_detail_and_keeps_the_business_data(tmp_path):
    source = initialize(tmp_path / "source.db")
    with closing(sqlite3.connect(source)) as db, db:
        db.execute("UPDATE users SET username='bi.mat',email='bimat@gmail.com',phone='0912345678',"
                   "full_name='Nguyễn Văn Bí Mật',id_card='001203004005',password_hash='scrypt:32768:8:1$s$h' WHERE user_id=1")
        db.execute("UPDATE residents SET full_name='Trần Thị Riêng Tư',phone='1234567',id_card='079099001122' WHERE resident_id=1")
        db.execute("UPDATE residents SET full_name='Ánh' WHERE resident_id=2")
        db.execute("UPDATE vehicles SET plate_number='29A1-555.55' WHERE vehicle_id=1")
        db.execute("UPDATE complaints SET content='Biển số: 29A1-555.55\nGhi chú: gọi 0912345678',"
                   "attachments='[{\"name\":\"cccd.png\"}]' WHERE complaint_id=1")
        notices = (
            "Ánh (tài khoản bi.mat, SĐT 1234567) vừa đăng ký và khai báo căn hộ A101.",
            "Nguyễn Văn Bí Mật và Trần Thị Riêng Tư, email bimat@gmail.com, CCCD 079099001122.",
            "Cư dân có ý kiến, phản ánh xin gọi 0228913665.",
        )
        for content in notices:
            db.execute("INSERT INTO notifications(type,title,content) VALUES ('general','Tin',?)", (content,))
        db.execute("INSERT INTO faq_knowledge_base(category,question,answer) VALUES ('Liên hệ','Hotline?','Gọi 0228913665.')")
        db.execute("INSERT INTO audit_log(actor_user_id,actor_username,action,entity,details,client_ip) "
                   "VALUES (1,'bi.mat','test','user','{\"note\": \"Trần Thị Riêng Tư\"}','203.0.113.5')")
        db.execute("INSERT INTO notification_push_tokens(token,user_id) VALUES ('device-token-secret',1)")
        db.execute("INSERT INTO bank_transactions(environment,provider_id,account_number,bank_name,bank_reference,reference,"
                   "direction,amount,status,received_at) VALUES ('live','987654','0123456789','Vietcombank',"
                   "'FT26324123456','TTHD0001','in',10000,'matched','2026-11-01 10:00:00')")
        db.execute("INSERT INTO bank_payment_intents(order_id,invoice_type,invoice_id,payer_user_id,environment,amount,"
                   "transfer_content,bank_code,bank_name,account_number,account_name,status,created_at,expires_at,updated_at) "
                   "VALUES ('VQR-1','monthly',1,1,'live',10000,'TTHD0001','VCB','Vietcombank','0123456789',"
                   "'NGUYEN VAN CHU TAI KHOAN','expired','2026-11-01','2026-11-01','2026-11-01')")
        totals = db.execute("SELECT COUNT(*),SUM(total_amount),SUM(status='paid') FROM monthly_invoices").fetchone()
        triggers = db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0]
    assert not anonymized_copy(source)

    exported, _ = export(source, tmp_path / "public.db")

    assert anonymized_copy(exported)
    text = all_text(exported).lower()
    for secret in SECRETS:
        assert secret.lower() not in text, secret
    assert "device-token-secret" not in text and "cccd.png" not in text
    # Ordinary words, the published hotline and the stand-in for a one-word name survive.
    assert "phản ánh" in text and "0228913665" in text
    with closing(sqlite3.connect(exported)) as db:
        registration = db.execute("SELECT content FROM notifications WHERE content LIKE '%(tài khoản %'").fetchone()[0]
        # Account 1 is a manager in the sample data, so the notice shows that account's stand-in name.
        assert registration.startswith("Quản lý 01 (tài khoản bql01, SĐT [đã ẩn])")
        assert db.execute("SELECT COUNT(*),SUM(total_amount),SUM(status='paid') FROM monthly_invoices").fetchone() == totals
        assert db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='trigger'").fetchone()[0] == triggers
        assert db.execute("SELECT plate_number FROM vehicles WHERE vehicle_id=1").fetchone()[0].startswith("99X9-")
