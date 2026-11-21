"""Regressions for the defects found in the security and reliability review."""
from contextlib import closing
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
from types import SimpleNamespace

import pytest
import requests
from werkzeug.security import generate_password_hash

from conftest import TEST_SEPAY_KEY, bank_webhook
from scripts import backup_db, init_db
from shared import firebase_push
from shared.ratelimit import SlidingWindow
from shared.web import APIError
from test_firebase_push import configured, register  # noqa: F401
from test_resident_memberships import create_invoice, make_apartment, register_resident

ROOT = Path(__file__).resolve().parents[1]


def new_contract(c, apartment_id, **fields):
    return c.call("resident", "/api/contracts", "POST", json={
        "apartment_id": apartment_id, "contract_type": "ownership", "start_date": "2026-01-01", **fields})


def test_contract_by_name_binds_the_registered_resident(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "RG-NEW")
    _, profile = register_resident(c, "RG-NEW", "rg.new")
    response = new_contract(c, apartment_id, resident_name="cư dân CÙNG căn hộ")
    assert response.status_code == 201, response.text
    assert response.json()["resident_id"] == profile["resident_id"]


def test_rejected_contract_leaves_no_orphan_resident(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "RG-OVERLAP")
    _, first = register_resident(c, "RG-OVERLAP", "rg.first")
    _, second = register_resident(c, "RG-OVERLAP", "rg.second")
    assert new_contract(c, apartment_id, resident_id=first["resident_id"]).status_code == 201
    assert new_contract(c, apartment_id, resident_id=second["resident_id"]).status_code == 409
    # Residents join by registering; a contract never creates one.
    assert new_contract(c, make_apartment(c, "RG-STRANGER"), resident_name="Người Bị Từ Chối").status_code == 404
    with sqlite3.connect(c.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM residents WHERE full_name='Người Bị Từ Chối'").fetchone()[0] == 0


def test_shared_names_never_bind_a_contract_to_the_wrong_person(service_cluster):
    c = service_cluster
    make_apartment(c, "RG-SAME-0")
    # The helper registers everyone under the same full name.
    ids = [register_resident(c, "RG-SAME-0", username)[1]["resident_id"] for username in ("same.one", "same.two")]
    saved = new_contract(c, make_apartment(c, "RG-SAME-1"), resident_id=ids[1], resident_name="Cư dân cùng căn hộ")
    assert saved.status_code == 201 and saved.json()["resident_id"] == ids[1]
    assert new_contract(c, make_apartment(c, "RG-SAME-2"), resident_name="CƯ DÂN CÙNG CĂN HỘ").status_code == 409


def awaiting_transfer(c, code, username):
    apartment_id = make_apartment(c, code)
    user_id, profile = register_resident(c, code, username)
    assert c.call("resident", f"/api/residents/{profile['resident_id']}/apartments", "POST",
                  json={"apartment_id": apartment_id}).status_code == 201
    invoice = create_invoice(c, apartment_id, "monthly")
    route = f"/api/billing/invoices/monthly/{invoice['invoice_id']}"
    scope = {"role": "resident", "user_id": user_id}
    order = c.call("billing", route + "/checkout", "POST", json={}, **scope).json()
    return route, scope, order, invoice


def confirm(c, order, scope):
    response = c.call("billing", f"/api/billing/orders/{order['order_id']}/confirm-transfer", "POST", json={}, **scope)
    assert response.status_code == 200 and response.json()["status"] == "awaiting_confirmation"


def test_management_can_release_a_transfer_the_bank_never_confirmed(service_cluster):
    c = service_cluster
    route, scope, order, _ = awaiting_transfer(c, "RG-STUCK", "stuck.owner")
    confirm(c, order, scope)
    assert c.call("billing", route).json()["active_payment_status"] == "awaiting_confirmation"
    assert c.call("billing", route + "/pay", "POST", json={"payment_method": "cash"}).status_code == 409
    release = route + "/release-payment"
    assert c.call("billing", release, "POST", json={"note": "x"}, **scope).status_code == 403
    assert c.call("billing", release, "POST", json={"note": "  "}).status_code == 400
    released = c.call("billing", release, "POST", json={"note": "Sao kê không có khoản chuyển"})
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "expired"
    assert c.call("billing", route).json()["active_payment_status"] is None
    assert c.call("billing", release, "POST", json={"note": "again"}).status_code == 409

    retry = c.call("billing", route + "/checkout", "POST", json={}, **scope)
    assert retry.status_code == 201 and retry.json()["can_pay"] and retry.json()["order_id"] != order["order_id"]
    with sqlite3.connect(c.db_path) as db:
        action, entity_id = db.execute("SELECT action,entity_id FROM audit_log ORDER BY audit_id DESC LIMIT 1").fetchone()
    assert action == "payment_session_released" and entity_id == order["order_id"]

    # Money arriving late on the released reference must still settle the invoice.
    late = c.call("billing", "/api/billing/sepay/webhook", "POST", json=bank_webhook(order),
                  headers={"Authorization": "Apikey " + TEST_SEPAY_KEY})
    assert late.status_code == 201, late.text
    assert c.call("billing", route).json()["status"] == "paid"


def test_release_is_refused_once_the_bank_has_recorded_money(service_cluster):
    c = service_cluster
    route, scope, order, _ = awaiting_transfer(c, "RG-PARTIAL", "partial.owner")
    partial = c.call("billing", "/api/billing/sepay/webhook", "POST", json=bank_webhook(order, amount=1000),
                     headers={"Authorization": "Apikey " + TEST_SEPAY_KEY})
    assert partial.status_code == 201, partial.text
    confirm(c, order, scope)
    assert c.call("billing", route + "/release-payment", "POST", json={"note": "x"}).status_code == 409


def test_release_stays_locked_when_the_bank_cannot_be_checked(service_cluster, monkeypatch):
    c = service_cluster
    route, scope, order, _ = awaiting_transfer(c, "RG-NOAPI", "noapi.owner")
    confirm(c, order, scope)
    monkeypatch.setenv("SEPAY_API_TOKEN", "x" * 40)
    monkeypatch.setenv("SEPAY_BANK_ACCOUNT_ID", "11111111-1111-1111-1111-111111111111")

    def unavailable(_):
        raise APIError("Chưa đối soát đầy đủ với SePay.", 502)

    monkeypatch.setattr(c.modules["billing"].bank_payments, "reconcile", unavailable)
    assert c.call("billing", route + "/release-payment", "POST", json={"note": "x"}).status_code == 502
    assert c.call("billing", route).json()["active_payment_status"] == "awaiting_confirmation"


def test_release_works_when_sepay_finds_no_transfer_for_the_session(service_cluster, monkeypatch):
    """SePay answers a search with no match with last_page 0. That is a clean "no money", not a failed check."""
    c = service_cluster
    route, scope, order, _ = awaiting_transfer(c, "RG-EMPTY", "empty.owner")
    confirm(c, order, scope)
    monkeypatch.setenv("SEPAY_API_TOKEN", "x" * 40)
    monkeypatch.setenv("SEPAY_BANK_ACCOUNT_ID", "11111111-1111-1111-1111-111111111111")

    def no_match(url, **kwargs):
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"status": "success", "data": [], "meta": {"pagination": {
            "total": 0, "per_page": 100, "current_page": 1, "last_page": 0, "has_more": False}}}).encode()
        return response

    payments = sys.modules[type(c.modules["billing"].bank_payments).__module__]
    monkeypatch.setattr(payments, "requests", SimpleNamespace(get=no_match, RequestException=requests.RequestException))
    released = c.call("billing", route + "/release-payment", "POST", json={"note": "Sao kê không có khoản chuyển"})
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "expired"
    with sqlite3.connect(c.db_path) as db:
        assert db.execute("SELECT last_error FROM bank_payment_intents WHERE order_id=?",
                          (order["order_id"],)).fetchone()[0] is None


def test_resident_reconcile_presses_are_throttled_but_admin_checks_are_not(service_cluster, monkeypatch):
    c = service_cluster
    _, scope, order, _ = awaiting_transfer(c, "RG-THROTTLE", "throttle.owner")
    module = c.modules["billing"]
    calls = []
    monkeypatch.setattr(module, "reconcile_order", lambda item: calls.append(item["order_id"]) or module.public_order(item))
    path = f"/api/billing/orders/{order['order_id']}/reconcile"
    for _ in range(3):
        assert c.call("billing", path, "POST", json={}, **scope).status_code == 200
    assert len(calls) == 1
    for _ in range(2):
        assert c.call("billing", path, "POST", json={}).status_code == 200
    assert len(calls) == 3


def login(c, username, password, ip):
    return requests.post(c.urls["auth"] + "/api/auth/login", json={"username": username, "password": password},
                         headers={"X-Client-IP": ip}, timeout=10)


def test_failed_logins_block_the_attacker_not_the_account_owner(service_cluster):
    c = service_cluster
    for _ in range(10):
        assert login(c, "admin01", "wrong-password", "203.0.113.5").status_code == 401
    assert login(c, "admin01", c.password, "203.0.113.5").status_code == 429
    assert login(c, "admin01", c.password, "203.0.113.9").status_code == 200


def test_login_rejects_an_oversized_username(service_cluster):
    assert login(service_cluster, "u" * 61, "password", "203.0.113.5").status_code == 400


def test_sliding_window_counts_clears_and_stays_bounded():
    window = SlidingWindow(2, 60, max_keys=3)
    assert window.hit("a") and window.hit("a") and not window.hit("a") and window.exceeded("a")
    window.clear("a")
    assert not window.exceeded("a")
    for key in range(50):
        window.record(key)
    assert len(window._events) <= 3


def test_expired_window_entries_are_forgotten():
    window = SlidingWindow(1, 0)
    window.record("a")
    assert not window.exceeded("a") and "a" not in window._events


def test_unconfirmed_resident_cannot_act_on_a_claimed_apartment(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "RG-CLAIM")
    user_id, profile = register_resident(c, "RG-CLAIM", "claim.only")
    scope = {"role": "resident", "user_id": user_id}
    ticket = {"apartment_id": apartment_id, "description": "Yêu cầu sửa chữa"}
    assert c.call("maintenance", "/api/maintenance/tickets", "POST", json=ticket, **scope).status_code == 403
    assert c.call("resident", f"/api/residents/{profile['resident_id']}/apartments", "POST",
                  json={"apartment_id": apartment_id}).status_code == 201
    assert c.call("maintenance", "/api/maintenance/tickets", "POST", json=ticket, **scope).status_code == 201


def test_unknown_apartment_code_is_an_error_not_a_ticket_without_apartment(service_cluster):
    response = service_cluster.call("maintenance", "/api/maintenance/tickets", "POST",
                                    json={"apartment_code": "KHONG-TON-TAI", "description": "Sửa"})
    assert response.status_code == 404, response.text


def test_real_short_names_are_accepted(service_cluster):
    c = service_cluster
    make_apartment(c, "RG-NAME")
    response = requests.post(c.urls["auth"] + "/api/auth/register", timeout=10, json={
        "username": "le.van.an", "password": "Password123", "full_name": "Lê Văn An", "email": "levanan@gmail.com",
        "phone": "0900000003", "apartment_code": "RG-NAME"})
    assert response.status_code == 201, response.text


def test_non_ascii_credentials_are_rejected_cleanly(service_cluster):
    c = service_cluster
    bad = "café".encode("latin-1")
    assert requests.post(c.urls["billing"] + "/api/billing/sepay/webhook", json={},
                         headers={"Authorization": b"Apikey " + bad}, timeout=10).status_code == 403
    assert requests.post(c.urls["resident"] + "/api/residents/provision", json={},
                         headers={"X-Service-Token": bad}, timeout=10).status_code == 401


def registered_session(c, code, username):
    make_apartment(c, code)
    created = requests.post(c.urls["auth"] + "/api/auth/register", timeout=10, json={
        "username": username, "password": "OldPassword1", "full_name": "Nguyễn Văn Kiểm Thử",
        "email": username.replace(".", "") + "@gmail.com", "phone": "0900000004", "apartment_code": code})
    assert created.status_code == 201, created.text
    return created.json()["user"]["user_id"], {"Authorization": "Bearer " + created.json()["token"]}


def signed_in(c, service, path, bearer):
    return requests.get(c.urls[service] + path, headers=bearer, timeout=10).status_code


def test_changing_a_password_signs_out_other_devices(service_cluster):
    c = service_cluster
    _, old = registered_session(c, "RG-TOKEN", "token.owner")
    changed = requests.post(c.urls["auth"] + "/api/auth/me/password", headers=old, timeout=10, json={
        "current_password": "OldPassword1", "new_password": "NewPassword1", "confirm_password": "NewPassword1"})
    assert changed.status_code == 200, changed.text
    assert signed_in(c, "auth", "/api/auth/me", old) == 401
    assert signed_in(c, "resident", "/api/residents/me", old) == 401
    assert signed_in(c, "resident", "/api/residents/me", {"Authorization": "Bearer " + changed.json()["token"]}) == 200


def test_role_change_revokes_the_users_sessions(service_cluster):
    c = service_cluster
    user_id, old = registered_session(c, "RG-ROLE", "role.owner")
    assert c.call("auth", f"/api/auth/users/{user_id}", "PATCH", json={"role": "technician"}).status_code == 200
    assert signed_in(c, "auth", "/api/auth/me", old) == 401


def test_reconciliation_prefers_open_sessions_and_ignores_old_history(service_cluster, monkeypatch):
    c = service_cluster
    payments = c.modules["billing"].bank_payments
    now = "2099-01-01T00:00:00+00:00"
    rows = (("OLD", "success", "2026-01-01T00:00:00+00:00", None), ("OPEN", "pending", now, "2099-06-01"),
            ("RECENT", "expired", now, None))
    with sqlite3.connect(c.db_path) as db:
        for index, (order_id, status, updated, checked) in enumerate(rows):
            db.execute("INSERT INTO bank_payment_intents(order_id,invoice_type,invoice_id,payer_user_id,environment,amount,"
                       "transfer_content,bank_code,bank_name,account_number,account_name,status,created_at,expires_at,updated_at,"
                       "last_checked_at) VALUES (?,'monthly',?,1,'test',1000,?,'VCB','Vietcombank','0123456789','X',?,?,?,?,?)",
                       (order_id, 900000 + index, f"QLCCAAAAAAAAAAA{index}", status, updated, updated, updated, checked))
    monkeypatch.setenv("SEPAY_API_TOKEN", "x" * 40)
    monkeypatch.setenv("SEPAY_BANK_ACCOUNT_ID", "11111111-1111-1111-1111-111111111111")
    seen = []
    monkeypatch.setattr(payments, "reconcile", lambda order: seen.append(order["order_id"]))
    with c.apps["billing"].app_context():
        payments.reconcile_pending()
    assert seen == ["OPEN", "RECENT"]


def test_dead_push_tokens_do_not_hold_the_database_write_lock(configured, monkeypatch):  # noqa: F811
    cluster, _ = configured
    register(cluster, "dead")
    register(cluster, "alive", user_id=4)
    writable = []

    def send(url, **kwargs):
        with closing(sqlite3.connect(cluster.db_path, timeout=1)) as other:
            other.execute("BEGIN IMMEDIATE")
            other.rollback()
        writable.append(True)
        if kwargs["json"]["message"]["token"] == "dead":
            return SimpleNamespace(ok=False, json=lambda: {"error": {"details": [{"errorCode": "UNREGISTERED"}]}})
        return SimpleNamespace(ok=True)

    monkeypatch.setattr(firebase_push.requests, "post", send)
    result = cluster.call("notification", "/api/notifications", "POST",
                          json={"type": "general", "title": "Tiêu đề", "content": "Nội dung"})
    assert result.status_code == 201, result.text
    assert result.json()["push"] == {"configured": True, "sent": 1, "failed": 1} and len(writable) == 2
    with sqlite3.connect(cluster.db_path) as db:
        tokens = {row[0] for row in db.execute("SELECT token FROM notification_push_tokens")}
    assert "dead" not in tokens and "alive" in tokens


def test_management_actions_are_audited_and_the_trail_is_append_only(service_cluster):
    c = service_cluster
    invoice = create_invoice(c, make_apartment(c, "RG-AUDIT"), "monthly")
    paid = c.call("billing", f"/api/billing/invoices/monthly/{invoice['invoice_id']}/pay", "POST", json={"payment_method": "cash"})
    assert paid.status_code == 201, paid.text
    entries = c.call("auth", "/api/auth/audit-log").json()["items"]
    assert entries[0]["action"] == "manual_payment_recorded" and entries[0]["actor_user_id"] == 1
    assert c.call("auth", "/api/auth/audit-log", role="resident").status_code == 403
    with sqlite3.connect(c.db_path) as db:
        for statement in ("UPDATE audit_log SET action='x'", "DELETE FROM audit_log"):
            with pytest.raises(sqlite3.Error, match="append-only"):
                db.execute(statement)


@pytest.fixture
def gateway(monkeypatch):
    spec = importlib.util.spec_from_file_location("gateway_under_test", ROOT / "gateway/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    forwarded = {}

    def request(method, url, **kwargs):
        forwarded.update(method=method, url=url, **kwargs)
        return SimpleNamespace(content=b"{}", status_code=200, headers={"Content-Type": "application/json"})

    monkeypatch.setattr(module, "pooled_session", lambda retry_reads=True: SimpleNamespace(request=request))
    return module.create_app().test_client(), forwarded


def test_gateway_stamps_the_real_caller_and_drops_forged_headers(gateway):
    client, forwarded = gateway
    client.get("/api/billing/invoices/monthly?status=paid&status=unpaid",
               headers={"CF-Connecting-IP": "198.51.100.7", "X-Client-IP": "1.1.1.1", "X-Service-Token": "forged"})
    assert forwarded["headers"]["X-Client-IP"] == "198.51.100.7"
    assert "X-Service-Token" not in forwarded["headers"]
    assert forwarded["params"] == {"status": ["paid", "unpaid"]}


def test_gateway_ignores_a_malformed_cloudflare_header(gateway):
    client, forwarded = gateway
    client.get("/api/apartments", headers={"CF-Connecting-IP": "not-an-ip"}, environ_base={"REMOTE_ADDR": "192.0.2.4"})
    assert forwarded["headers"]["X-Client-IP"] == "192.0.2.4"


def test_gateway_stamps_the_caller_that_tailscale_funnel_reports(gateway):
    client, forwarded = gateway
    funnel = {"Tailscale-Funnel-Request": "?1", "X-Forwarded-For": "203.0.113.9"}
    client.get("/api/apartments", headers=funnel, environ_base={"REMOTE_ADDR": "172.17.0.1"})
    assert forwarded["headers"]["X-Client-IP"] == "203.0.113.9"
    # Without the Funnel mark, X-Forwarded-For is just a header anyone on the network can send.
    client.get("/api/apartments", headers={"X-Forwarded-For": "203.0.113.9"}, environ_base={"REMOTE_ADDR": "172.17.0.1"})
    assert forwarded["headers"]["X-Client-IP"] == "172.17.0.1"


@pytest.mark.parametrize("tunnel", [
    {"CF-Connecting-IP": "198.51.100.7"},
    {"Tailscale-Funnel-Request": "?1", "X-Forwarded-For": "198.51.100.7"},
], ids=["cloudflare", "tailscale-funnel"])
def test_tunnel_serves_everything_by_default_and_only_the_webhook_when_restricted(gateway, monkeypatch, tunnel):
    client, _ = gateway
    assert client.get("/api/apartments", headers=tunnel).status_code == 200
    monkeypatch.setenv("TUNNEL_ACCESS", "webhook")
    assert client.get("/api/apartments", headers=tunnel).status_code == 404
    assert client.get("/", headers=tunnel).status_code == 404
    assert client.post("/api/billing/sepay/webhook", json={}, headers=tunnel).status_code == 200
    assert client.get("/api/apartments").status_code == 200


def test_gateway_browser_policy_and_cache_headers(gateway):
    client, _ = gateway
    page, script, image, api = client.get("/"), client.get("/app.js"), client.get("/assets/favicon.svg"), client.get("/api/apartments")
    assert "script-src 'self' https://www.gstatic.com" in page.headers["Content-Security-Policy"]
    assert "unsafe-inline" not in page.headers["Content-Security-Policy"].split("script-src")[1].split(";")[0]
    assert "Content-Security-Policy" not in client.get("/docs").headers
    assert "no-store" not in script.headers["Cache-Control"] and script.headers.get("ETag")
    assert "max-age=604800" in image.headers["Cache-Control"]
    assert api.headers["Cache-Control"] == "no-store"
    for response in (page, script, image):
        response.close()


def test_home_screen_icons_are_served_at_their_declared_sizes(gateway):
    """iPhone ignores SVG icons and needs an opaque apple-touch-icon; Android reads the manifest PNGs."""
    client, _ = gateway
    page = client.get("/")
    assert b'rel="apple-touch-icon" href="/assets/icons/apple-touch-icon.png"' in page.data
    manifest = client.get("/manifest.webmanifest")
    assert manifest.headers["Content-Type"].startswith("application/manifest+json")
    icons = [("/assets/icons/apple-touch-icon.png", "180x180", "any")]
    icons += [(icon["src"], icon["sizes"], icon["purpose"]) for icon in manifest.get_json(force=True)["icons"]
              if icon["type"] == "image/png"]
    assert {purpose for _, _, purpose in icons} == {"any", "maskable"}
    for src, sizes, purpose in icons:
        image = client.get(src)
        data = image.data
        assert image.status_code == 200 and data[:8] == b"\x89PNG\r\n\x1a\n", src
        width, height = int.from_bytes(data[16:20], "big"), int.from_bytes(data[20:24], "big")
        assert f"{width}x{height}" == sizes, src
        if src.endswith("apple-touch-icon.png") or purpose == "maskable":
            assert data[25] == 2, f"{src} must be opaque RGB"  # transparency turns black or is cropped away
        image.close()
    for response in (page, manifest):
        response.close()


def test_retired_payment_provider_tables_are_gone_on_every_database(service_cluster, tmp_path):
    with sqlite3.connect(service_cluster.db_path) as db:
        names = {row[0] for row in db.execute("SELECT name FROM sqlite_master")}
    assert not names & {"payment_orders", "payment_order_provider_state", "uq_active_payment_order"}
    # A database that still holds them, with foreign keys enforced as at startup.
    script = (ROOT / "migrations/0110_remove_legacy_payment_tables.sql").read_text(encoding="utf-8")
    with closing(sqlite3.connect(tmp_path / "old.db")) as db:
        db.execute("PRAGMA foreign_keys=ON")
        db.executescript("CREATE TABLE payment_orders(order_id TEXT PRIMARY KEY);"
                         "CREATE TABLE payment_order_provider_state(order_id TEXT PRIMARY KEY REFERENCES payment_orders(order_id));"
                         "INSERT INTO payment_orders VALUES('A');INSERT INTO payment_order_provider_state VALUES('A');")
        db.executescript(script)
        assert db.execute("SELECT COUNT(*) FROM sqlite_master WHERE name LIKE 'payment_order%'").fetchone()[0] == 0


def test_numbered_migrations_run_after_the_original_set(tmp_path):
    for name in ("zeta.sql", "0200_b.sql", "0100_a.sql", "alpha.sql"):
        (tmp_path / name).write_text("", encoding="utf-8")
    assert [path.name for path in init_db.migration_files(tmp_path)] == ["alpha.sql", "zeta.sql", "0100_a.sql", "0200_b.sql"]


def test_published_demo_passwords_are_refused_in_live_mode(tmp_path):
    with closing(sqlite3.connect(tmp_path / "accounts.db")) as db:
        db.execute("CREATE TABLE users(username TEXT,password_hash TEXT,status TEXT)")
        db.execute("INSERT INTO users VALUES('admin',?,'active')", (generate_password_hash("Admin@12345"),))
        with pytest.raises(RuntimeError, match="admin"):
            init_db.assert_no_public_demo_passwords(db)
        db.execute("UPDATE users SET password_hash=?", (generate_password_hash("Different-Password-1"),))
        init_db.assert_no_public_demo_passwords(db)


def test_demo_accounts_are_never_created_in_live_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("SEPAY_ENV", "live")
    destination = init_db.initialize(tmp_path / "application.db", demo=True)
    with closing(sqlite3.connect(destination)) as db:
        assert db.execute("SELECT COUNT(*) FROM schema_migrations WHERE name='demo-users-v1'").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM users WHERE username='admin'").fetchone()[0] == 0


def test_backup_rotates_only_automatic_copies_and_is_restorable(tmp_path):
    source = tmp_path / "application.db"
    with closing(sqlite3.connect(source)) as db:
        db.execute("CREATE TABLE sample(value TEXT)")
        db.execute("INSERT INTO sample VALUES('kept')")
        db.commit()
    folder = tmp_path / "backups"
    folder.mkdir()
    manual = folder / "QLCC-before-upgrade.db"
    manual.write_bytes(b"manual backup")
    for stamp in ("20260101-000000", "20260102-000000", "20260103-000000"):
        (folder / f"QLCC-auto-{stamp}.db").write_bytes(b"old")
    created = backup_db.backup_once(source, folder, keep=2)
    automatic = sorted(path.name for path in folder.glob("QLCC-auto-*.db"))
    assert manual.read_bytes() == b"manual backup" and len(automatic) == 2 and created.name == automatic[-1]
    with closing(sqlite3.connect(created)) as db:
        assert db.execute("SELECT value FROM sample").fetchone()[0] == "kept"


def test_a_checkout_without_env_uses_secrets_generated_once(tmp_path, monkeypatch):
    from shared import config

    location = tmp_path / "generated" / "secrets.json"
    monkeypatch.setenv("JWT_SECRET", "")
    monkeypatch.setattr(config, "GENERATED_SECRETS", location)
    with pytest.raises(RuntimeError):
        config.secret("JWT_SECRET")
    init_db.ensure_generated_secrets(location)
    first = config.secret("JWT_SECRET")
    assert len(first) >= 32 and config.secret("SERVICE_TOKEN") != first
    init_db.ensure_generated_secrets(location)
    assert config.secret("JWT_SECRET") == first
    monkeypatch.setenv("JWT_SECRET", "value-from-env-file-with-more-than-32-characters")
    assert config.secret("JWT_SECRET") == "value-from-env-file-with-more-than-32-characters"
