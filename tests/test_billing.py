"""Invoice business rules and verified SePay bank settlement on isolated data."""
import importlib.util
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
import pytest
from flask import g

from conftest import TEST_SEPAY_KEY, bank_webhook, configure_sepay

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def billing(tmp_path, monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test-billing-jwt-secret-at-least-32-characters")
    monkeypatch.setenv("SERVICE_TOKEN", "test-billing-internal-at-least-32-characters")
    configure_sepay(monkeypatch)
    path = tmp_path / "billing.db"
    with sqlite3.connect(f"file:{(ROOT / 'QLCC.db').as_posix()}?mode=ro", uri=True) as source:
        with sqlite3.connect(path) as destination:
            source.backup(destination)
            for migration in sorted((ROOT / "migrations").glob("billing*.sql")):
                destination.executescript(migration.read_text(encoding="utf-8"))
    spec = importlib.util.spec_from_file_location("billing_under_test", ROOT / "billing-service/app.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []

    def peer(service, endpoint, **kwargs):
        calls.append((service, endpoint, kwargs))
        if service == "auth":
            return {"user": dict(g.user)}
        if endpoint == "/api/residents/me":
            return {"resident_id": g.user["user_id"],
                    "apartment_ids": [99] if g.user["user_id"] == 2 else [1]}
        if endpoint.startswith("/api/apartments/"):
            return {"apartment_id": int(endpoint.rsplit("/", 1)[1]), "code": "A101"}
        if service == "parking":
            return {"items": [{"apartment_id": 1, "monthly_fee": 150000}]}
        return {"ok": True}

    monkeypatch.setattr(module, "call_service", peer)
    monkeypatch.setattr("shared.http.call_service", peer)
    app = module.create_app()
    app.config.update(TESTING=True, DATABASE_PATH=str(path))
    return module, app, path, calls


def headers(role="admin", user_id=1, **extra):
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": str(user_id), "role": role, "username": "test",
                        "iss": "qlcc-auth", "iat": now, "exp": now + timedelta(hours=1)},
                       "test-billing-jwt-secret-at-least-32-characters", algorithm="HS256")
    return {"Authorization": "Bearer " + token, **extra}



def invoice(client, kind="monthly", **overrides):
    values = {"apartment_id": 1, "period": "2099-01" if kind == "monthly" else "2099-H1",
              "due_date": "2099-02-01"}
    values.update({"electricity_fee": 400000, "water_fee": 100000} if kind == "monthly" else {"service_fee": 3000000})
    values.update(overrides)
    response = client.post(f"/api/billing/invoices/{kind}", json=values, headers=headers())
    assert response.status_code == 201, response.json
    return response.json



def test_invoice_totals_parking_http_and_unique_period(billing):
    _, app, _, calls = billing
    client = app.test_client()
    monthly = invoice(client)
    assert monthly["total_amount"] == 500000
    halfyear = invoice(client, "semiannual")
    assert halfyear["parking_fee"] == 900000
    assert halfyear["total_amount"] == 3900000
    assert any(service == "parking" and args["internal"] for service, _, args in calls)
    duplicate = client.post("/api/billing/invoices/monthly", json={
        "apartment_id": 1, "period": "2099-01", "due_date": "2099-02-01", "water_fee": 1000}, headers=headers())
    assert duplicate.status_code == 409


@pytest.mark.parametrize("kind", ["monthly", "semiannual"])
def test_invoice_times_come_from_server_and_successful_payment(billing, kind):
    module, app, path, _ = billing
    client = app.test_client()
    started = datetime.now(timezone.utc).replace(microsecond=0)
    row = invoice(client, kind, created_at="2000-01-01", paid_at="2000-01-01")
    created = datetime.fromisoformat(row["created_at"]).replace(tzinfo=timezone.utc)
    assert created >= started and row["paid_at"] is None
    route = f"/api/billing/invoices/{kind}/{row['invoice_id']}"
    # Known SQLite UTC value also tests timezone conversion in receipts.
    with sqlite3.connect(path) as db:
        db.execute(f"UPDATE {kind}_invoices SET created_at=? WHERE invoice_id=?",
                   ("2026-11-06 18:30:45", row["invoice_id"]))
    payment = client.post(route + "/pay", headers=headers(), json={"payment_method": "cash"}).json
    assert datetime.fromisoformat(payment["paid_at"]).utcoffset() == timedelta(hours=7)
    for role in ("admin", "resident"):
        listed = client.get(f"/api/billing/invoices/{kind}", headers=headers(role)).json["items"]
        detail = client.get(route, headers=headers(role)).json
        assert detail == next(r for r in listed if r["invoice_id"] == row["invoice_id"])
        assert detail["created_at"] == "2026-11-06 18:30:45"
        assert detail["paid_at"] == payment["paid_at"] and detail["status"] == "paid"
    assert client.post(route + "/pay", headers=headers(), json={"payment_method": "cash"}).status_code == 409
    assert client.get(route, headers=headers()).json["paid_at"] == payment["paid_at"]
    receipt = client.get(f"/api/billing/payments/{kind}/{payment['payment_id']}/receipt", headers=headers())
    assert "07/11/2026 01:30:45" in receipt.text
    assert module.vietnam_time(payment["paid_at"]) in receipt.text



@pytest.mark.parametrize("fee", [-1, 1.5, True, "abc", 1_000_000_001])
def test_reject_invalid_money(billing, fee):
    _, app, _, _ = billing
    response = app.test_client().post("/api/billing/invoices/monthly", json={
        "apartment_id": 1, "period": "2099-01", "due_date": "2099-02-01", "water_fee": fee}, headers=headers())
    assert response.status_code == 400


def utility_invoice_payload(**changes):
    return {"apartment_id": 1, "period": "2099-05", "due_date": "2099-06-01",
            "electricity_usage": "0.145", "electricity_unit_price": 100,
            "water_usage": "1.234", "water_unit_price": 1000, **changes}


def test_utility_invoice_calculation_edit_and_receipt(billing):
    _, app, _, _ = billing
    client = app.test_client()
    response = client.post("/api/billing/invoices/monthly", json=utility_invoice_payload(), headers=headers())
    assert response.status_code == 201, response.json
    row = response.json
    assert (row["electricity_fee"], row["water_fee"], row["total_amount"]) == (15, 1234, 1249)
    assert row["electricity_usage"] == .145 and row["water_unit_price"] == 1000
    route = f"/api/billing/invoices/monthly/{row['invoice_id']}"
    # Editing a rate recomputes the fee; editing the deadline preserves inputs.
    edited = client.patch(route, json={"electricity_unit_price": 200}, headers=headers())
    assert edited.status_code == 200 and edited.json["electricity_fee"] == 29
    assert edited.json["total_amount"] == 1263
    assert client.patch(route, json={"electricity_fee": 1}, headers=headers()).status_code == 400
    updated = client.patch(route, json={"due_date": "2099-06-02"}, headers=headers()).json
    assert updated["total_amount"] == 1263 and updated["electricity_usage"] == .145
    assert client.get(route, headers=headers("resident")).json == updated
    # Once QR details exist, its amount/calculation cannot be changed.
    response = client.post(route + "/checkout", json={}, headers=headers("resident"))
    assert response.status_code == 201, response.json
    order = response.json
    assert client.patch(route, json={"water_usage": 5}, headers=headers()).status_code == 409
    response = deliver(client, order)
    assert response.status_code == 201
    paid_order = client.get(f"/api/billing/orders/{order['order_id']}", headers=headers("resident")).json
    receipt = client.get(paid_order["receipt_url"], headers=headers("resident"))
    assert "0.145 kWh" in receipt.text and "1.234 m³" in receipt.text
    assert paid_order["paid_at"] == client.get(route, headers=headers()).json["paid_at"]


@pytest.mark.parametrize("changes", [
    {"electricity_usage": -1}, {"electricity_usage": True}, {"electricity_usage": "NaN"},
    {"electricity_usage": "Infinity"}, {"electricity_usage": "0.0001"},
    {"water_usage": None}, {"water_usage": 1000001},
    {"electricity_unit_price": 0}, {"water_unit_price": -1}, {"water_unit_price": 1.5},
    {"electricity_fee": 999}, {"total_amount": 1},
    {"water_usage": 1000000, "water_unit_price": 1000000},
])
def test_utility_invoice_rejects_invalid_or_tampered_calculation(billing, changes):
    _, app, path, _ = billing
    response = app.test_client().post("/api/billing/invoices/monthly",
                                     json=utility_invoice_payload(**changes), headers=headers())
    assert response.status_code == 400, response.json
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM monthly_invoices WHERE period='2099-05'").fetchone()[0] == 0


def test_database_guards_calculation_and_single_settlement(billing):
    _, app, path, _ = billing
    client = app.test_client()
    response = client.post("/api/billing/invoices/monthly", json=utility_invoice_payload(), headers=headers())
    assert response.status_code == 201
    identifier = response.json["invoice_id"]
    with sqlite3.connect(path) as db:
        for assignment in ("electricity_fee=1", "water_usage=NULL", "water_usage=-1",
                           "electricity_usage=0.1451", "water_unit_price=1.5", "water_unit_price=0"):
            with pytest.raises(sqlite3.IntegrityError):
                db.execute("UPDATE monthly_invoices SET " + assignment + " WHERE invoice_id=?", (identifier,))
        with pytest.raises(sqlite3.IntegrityError):
            db.execute("INSERT INTO monthly_invoices(apartment_id,period,due_date,electricity_fee,water_fee,electricity_usage) "
                       "VALUES (1,'2099-07','2099-08-01',15,1234,0.145)")
        db.execute("UPDATE monthly_invoices SET total_amount=999 WHERE invoice_id=?", (identifier,))
        assert db.execute("SELECT total_amount FROM monthly_invoices WHERE invoice_id=?", (identifier,)).fetchone()[0] == 1249
    for kind, row in (("monthly", response.json), ("semiannual", invoice(client, "semiannual"))):
        result = client.post(f"/api/billing/invoices/{kind}/{row['invoice_id']}/pay", json={"payment_method": "cash"}, headers=headers())
        assert result.status_code == 201
        with sqlite3.connect(path) as db:
            with pytest.raises(sqlite3.IntegrityError):
                db.execute(f"INSERT INTO {kind}_payments(invoice_id,amount,payment_method,status) VALUES (?,?,'cash','success')",
                           (row["invoice_id"], row["total_amount"]))



def test_roles_and_resident_ownership_enforced(billing):
    _, app, _, _ = billing
    client = app.test_client()
    other = invoice(client, apartment_id=2)
    path = f"/api/billing/invoices/monthly/{other['invoice_id']}"
    assert client.get(path).status_code == 401
    assert client.get(path, headers=headers("technician")).status_code == 403
    assert client.get(path, headers=headers("resident")).status_code == 403
    assert client.post(path + "/checkout", json={}, headers=headers("resident")).status_code == 403
    assert client.post(path + "/pay", json={}, headers=headers("resident")).status_code == 403
    rows = client.get("/api/billing/invoices/monthly", headers=headers("resident")).json["items"]
    assert all(row["apartment_id"] == 1 for row in rows)



def test_manual_payment_amount_idempotency_and_receipt(billing):
    _, app, database, _ = billing
    client = app.test_client()
    item = invoice(client)
    path = f"/api/billing/invoices/monthly/{item['invoice_id']}/pay"
    auth = headers(**{"Idempotency-Key": "manual-1"})
    assert client.post(path, json={"amount": 1}, headers=auth).status_code == 400
    response = client.post(path, json={"payment_method": "bank_transfer"}, headers=auth)
    assert response.status_code == 201
    again = client.post(path, json={"payment_method": "bank_transfer"}, headers=auth)
    assert again.status_code == 200
    assert again.json["payment_id"] == response.json["payment_id"]
    assert client.post(path, json={"payment_method": "bank_transfer", "amount": 1000}, headers=auth).status_code == 409
    assert client.post(path, json={"payment_method": "cash"}, headers=auth).status_code == 409
    receipt = client.get(response.json["receipt_url"], headers=headers("resident"))
    assert receipt.status_code == 200
    assert "attachment" in receipt.headers["Content-Disposition"]
    assert b"500,000 VND" in receipt.data
    with sqlite3.connect(database) as db:
        notices = db.execute("SELECT payload FROM billing_outbox WHERE event_id=?",
                             (f"billing:paid-admin:monthly:{item['invoice_id']}",)).fetchall()
    assert len(notices) == 1
    assert json.loads(notices[0][0])["target_role"] == "admin"



def test_overdue_transition_idempotent_and_settlement_outbox(billing):
    module, app, path, _ = billing
    client = app.test_client()
    item = invoice(client, period="2001-01", due_date="2001-02-01", apartment_id=99)
    with app.app_context():
        assert module.mark_overdue("2001-02-02") == 1
        assert module.mark_overdue("2001-02-03") == 0
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM maintenance_tickets WHERE apartment_id=99 AND type='cut_service'").fetchone()[0] == 1
    result = client.post(f"/api/billing/invoices/monthly/{item['invoice_id']}/pay", json={}, headers=headers())
    assert result.status_code == 201
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT COUNT(*) FROM billing_outbox WHERE event_id=?", (f"settled:monthly:{item['invoice_id']}",)).fetchone()[0] == 1
    with app.app_context():
        assert module.dispatch_outbox() >= 3



def test_outbox_failure_is_retried_without_losing_event(billing, monkeypatch):
    module, app, path, calls = billing
    invoice(app.test_client())
    original = module.call_service

    def failing(*args, **kwargs):
        raise RuntimeError("temporary peer outage")

    monkeypatch.setattr(module, "call_service", failing)
    with app.app_context():
        assert module.dispatch_outbox() == 0
    with sqlite3.connect(path) as db:
        row = db.execute("SELECT attempts,delivered_at FROM billing_outbox").fetchone()
        assert row == (1, None)
    monkeypatch.setattr(module, "call_service", original)
    with app.app_context():
        assert module.dispatch_outbox() == 1
        assert module.dispatch_outbox() == 0



def test_report_distinguishes_billed_and_collected(billing):
    _, app, _, _ = billing
    client = app.test_client()
    invoice(client)
    invoice(client, "semiannual")
    report = client.get("/api/billing/reports?year=2099&group=quarter", headers=headers()).json
    assert len(report["items"]) == 4
    assert report["totals"]["billed_amount"] == 4400000
    assert report["totals"]["collected_amount"] == 0
    assert report["items"][0]["invoice_count"] == 2
    assert client.get("/api/billing/reports", headers=headers("resident")).status_code == 403



def test_settlement_does_not_restore_when_another_due_debt_is_not_yet_scanned(billing):
    module, app, path, _ = billing
    client = app.test_client()
    first = invoice(client, apartment_id=99, period="2001-01", due_date="2001-02-01")
    with app.app_context():
        module.mark_overdue("2001-02-02")
    invoice(client, apartment_id=99, period="2001-02", due_date="2001-03-01")
    assert client.post(f"/api/billing/invoices/monthly/{first['invoice_id']}/pay", json={}, headers=headers()).status_code == 201
    with sqlite3.connect(path) as db:
        payload = db.execute("SELECT payload FROM billing_outbox WHERE event_id=?", (f"settled:monthly:{first['invoice_id']}",)).fetchone()[0]
    assert json.loads(payload)["all_debts_settled"] is False



def test_due_reminders_are_deduplicated_per_day(billing):
    module, app, path, _ = billing
    invoice(app.test_client())
    with app.app_context():
        assert module.send_due_reminders("2099-01-29") == 1
        assert module.send_due_reminders("2099-01-29") == 0
        assert module.send_due_reminders("2099-01-30") == 1


def checkout(billing, *, kind="monthly", user_id=1, **values):
    client = billing[1].test_client()
    item = invoice(client, kind, **values)
    response = client.post(f"/api/billing/invoices/{kind}/{item['invoice_id']}/checkout",
                           json={}, headers=headers("resident", user_id=user_id))
    assert response.status_code == 201, response.json
    return client, item, response.json


def deliver(client, order, *, transaction_id=100001, amount=None, **changes):
    return client.post("/api/billing/sepay/webhook",
                       json=bank_webhook(order, transaction_id=transaction_id, amount=amount, **changes),
                       headers={"Authorization": "Apikey " + TEST_SEPAY_KEY})


def invoice_status(client, item, kind="monthly"):
    return client.get(f"/api/billing/invoices/{kind}/{item['invoice_id']}", headers=headers()).json["status"]


def payment_count(database, item, kind="monthly"):
    with sqlite3.connect(database) as db:
        return db.execute(f"SELECT COUNT(*) FROM {kind}_payments WHERE invoice_id=?",
                          (item["invoice_id"],)).fetchone()[0]


@pytest.mark.parametrize("kind", ["monthly", "semiannual"])
def test_resident_only_checkout_has_trusted_amount_and_no_external_create(billing, monkeypatch, kind):
    module, app, database, _ = billing
    monkeypatch.setattr(module.requests, "post", lambda *a, **k: pytest.fail("checkout must not create bank transfers"))
    client = app.test_client()
    item = invoice(client, kind)
    route = f"/api/billing/invoices/{kind}/{item['invoice_id']}/checkout"
    for auth, status in (({}, 401), (headers(), 403), (headers("technician"), 403),
                         (headers("resident", user_id=2), 403)):
        assert client.post(route, json={}, headers=auth).status_code == status
    result = client.post(route, json={"amount": 1, "payer_user_id": 3,
                                      "account_number": "ATTACKER", "transfer_content": "ATTACKER"},
                         headers=headers("resident"))
    assert result.status_code == 201, result.json
    order = result.json
    assert order["mode"] == "sepay" and order["status"] == "pending"
    assert order["amount"] == item["total_amount"] and order["can_pay"] is True
    assert order["transfer_content"] and order["expires_at"]
    assert order["payer_user_id"] == 1 and order["bank"]["account_number"] == "0123456789"
    assert order["transfer_content"] != "ATTACKER"
    assert client.get(f"/api/billing/orders/{order['order_id']}", headers=headers()).status_code == 200
    assert client.get(f"/api/billing/orders/{order['order_id']}", headers=headers("resident", user_id=2)).status_code == 403
    assert payment_count(database, item, kind) == 0


def test_one_household_payment_owner_hides_qr_from_other_members(billing):
    _, app, database, _ = billing
    client, item, order = checkout(billing)
    route = f"/api/billing/orders/{order['order_id']}"
    other = client.post(f"/api/billing/invoices/monthly/{item['invoice_id']}/checkout",
                        json={}, headers=headers("resident", user_id=3))
    assert other.status_code in (200, 201), other.json
    assert other.json["order_id"] == order["order_id"]
    assert other.json["can_pay"] is False
    assert not other.json.get("qr_image_url")
    assert client.post(route + "/confirm-transfer", json={}, headers=headers("resident", user_id=3)).status_code == 403
    assert client.post(route + "/cancel", json={}, headers=headers("resident", user_id=3)).status_code == 403
    assert client.post(f"/api/billing/invoices/monthly/{item['invoice_id']}/pay", json={}, headers=headers()).status_code == 409
    assert payment_count(database, item) == 0


def test_bank_intent_reserves_invoice_amount_until_resolved(billing):
    client, item, _ = checkout(billing)
    route = f"/api/billing/invoices/monthly/{item['invoice_id']}"
    assert client.patch(route, json={"water_fee": 1}, headers=headers()).status_code == 409
    assert client.post(route + "/pay", json={"payment_method": "cash"}, headers=headers()).status_code == 409


def test_legacy_test_order_does_not_block_sepay_and_is_preserved(billing):
    _, app, database, _ = billing
    client = app.test_client()
    item = invoice(client)
    with sqlite3.connect(database) as db:
        db.execute("INSERT INTO payment_orders(order_id,request_id,invoice_type,invoice_id,user_id,amount,mode,order_info) "
                   "VALUES ('LEGACY-TEST','LEGACY-REQUEST','monthly',?,1,500000,'sandbox','Prior provider test')",
                   (item["invoice_id"],))
    created = client.post(f"/api/billing/invoices/monthly/{item['invoice_id']}/checkout", json={}, headers=headers("resident"))
    assert created.status_code == 201, created.json
    assert created.json["order_id"] != "LEGACY-TEST" and created.json["mode"] == "sepay"
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT status,payment_id FROM payment_orders WHERE order_id='LEGACY-TEST'").fetchone() == ("pending", None)
    assert deliver(client, created.json).status_code == 201
    assert payment_count(database, item) == 1
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT status,payment_id FROM payment_orders WHERE order_id='LEGACY-TEST'").fetchone() == ("pending", None)


def test_qr_image_is_only_available_to_current_payer(billing, monkeypatch):
    module, _, _, _ = billing
    client, _, order = checkout(billing)
    assert order["qr_image_url"].startswith("/api/billing/")
    assert client.get(order["qr_image_url"], headers=headers("resident", user_id=3)).status_code == 403
    assert client.get(order["qr_image_url"], headers=headers()).status_code == 403
    assert client.get(order["qr_image_url"]).status_code == 401
    fetched = []

    def image(url, **kwargs):
        fetched.append(url)
        response = module.requests.Response()
        response.status_code = 200
        response._content = b"\x89PNG\r\n\x1a\nTEST"
        response.headers["Content-Type"] = "image/png"
        return response

    monkeypatch.setattr(module.requests, "get", image)
    response = client.get(order["qr_image_url"], headers=headers("resident"))
    assert response.status_code == 200 and response.mimetype == "image/png"
    assert len(fetched) == 1 and fetched[0].startswith("https://")
    assert TEST_SEPAY_KEY not in fetched[0]


def test_concurrent_checkout_grants_exactly_one_payer(billing):
    _, app, database, _ = billing
    client = app.test_client()
    item = invoice(client)
    route = f"/api/billing/invoices/monthly/{item['invoice_id']}/checkout"

    def submit(user_id):
        with app.test_client() as separate:
            result = separate.post(route, json={}, headers=headers("resident", user_id=user_id))
            assert result.status_code in (200, 201), result.json
            return result.json

    with ThreadPoolExecutor(max_workers=2) as pool:
        orders = list(pool.map(submit, (1, 3)))
    assert orders[0]["order_id"] == orders[1]["order_id"]
    assert sum(order["can_pay"] for order in orders) == 1
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM bank_payment_intents WHERE invoice_type='monthly' AND invoice_id=?",
                          (item["invoice_id"],)).fetchone()[0] == 1


def test_confirm_transfer_locks_order_without_marking_invoice_paid(billing):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    route = f"/api/billing/orders/{order['order_id']}"
    confirmed = client.post(route + "/confirm-transfer", json={}, headers=headers("resident"))
    assert confirmed.status_code == 200, confirmed.json
    assert confirmed.json["status"] == "awaiting_confirmation"
    assert invoice_status(client, item) == "unpaid" and payment_count(database, item) == 0
    assert client.post(route + "/cancel", json={}, headers=headers("resident")).status_code == 409
    assert client.post(f"/api/billing/invoices/monthly/{item['invoice_id']}/pay", json={}, headers=headers()).status_code == 409
    assert deliver(client, order).status_code == 201
    assert invoice_status(client, item) == "paid"


def test_awaiting_confirmation_never_expires_into_another_payer(billing):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    route = f"/api/billing/orders/{order['order_id']}"
    assert client.post(route + "/confirm-transfer", json={}, headers=headers("resident")).status_code == 200
    with sqlite3.connect(database) as db:
        db.execute("UPDATE bank_payment_intents SET expires_at='2000-01-01T00:00:00+00:00' WHERE order_id=?",
                   (order["order_id"],))
    tracked = client.get(route, headers=headers("resident")).json
    assert tracked["status"] == "awaiting_confirmation" and tracked["can_pay"] is False
    other = client.post(f"/api/billing/invoices/monthly/{item['invoice_id']}/checkout", json={}, headers=headers("resident", user_id=3))
    assert other.status_code in (200, 201)
    assert other.json["order_id"] == order["order_id"] and other.json["can_pay"] is False
    assert invoice_status(client, item) == "unpaid" and payment_count(database, item) == 0


def test_owner_cancel_allows_next_member_checkout_but_late_bank_transfer_is_not_lost(billing):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    route = f"/api/billing/orders/{order['order_id']}"
    assert client.post(route + "/cancel", json={}, headers=headers("resident")).status_code == 200
    new = client.post(f"/api/billing/invoices/monthly/{item['invoice_id']}/checkout", json={},
                      headers=headers("resident", user_id=3))
    assert new.status_code == 201 and new.json["order_id"] != order["order_id"]
    assert new.json["can_pay"] is True
    assert deliver(client, order).status_code == 201
    assert invoice_status(client, item) == "paid" and payment_count(database, item) == 1
    latest = client.get(f"/api/billing/orders/{new.json['order_id']}", headers=headers("resident", user_id=3)).json
    assert latest["can_pay"] is False


def test_expired_qr_releases_payer_but_keeps_late_payment_reference(billing):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    with sqlite3.connect(database) as db:
        db.execute("UPDATE bank_payment_intents SET expires_at='2000-01-01T00:00:00+00:00' WHERE order_id=?",
                   (order["order_id"],))
    old = client.get(f"/api/billing/orders/{order['order_id']}", headers=headers("resident")).json
    assert old["status"] == "expired" and old["can_pay"] is False
    assert deliver(client, order).status_code == 201
    assert invoice_status(client, item) == "paid" and payment_count(database, item) == 1


@pytest.mark.parametrize("kind", ["monthly", "semiannual"])
def test_verified_webhook_settles_once_and_emits_one_admin_notification(billing, kind):
    _, _, database, _ = billing
    client, item, order = checkout(billing, kind=kind)
    first = deliver(client, order)
    second = deliver(client, order)
    assert first.status_code == second.status_code == 201
    assert first.json["success"] is True
    assert invoice_status(client, item, kind) == "paid" and payment_count(database, item, kind) == 1
    final = client.get(f"/api/billing/orders/{order['order_id']}", headers=headers("resident")).json
    assert final["status"] == "success" and final["payment_id"]
    receipt = client.get(final["receipt_url"], headers=headers("resident", user_id=3))
    assert receipt.status_code == 200 and "attachment" in receipt.headers["Content-Disposition"]
    assert "SEPAY" in receipt.text.upper()
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM billing_outbox WHERE event_id=?",
                          (f"billing:paid-admin:{kind}:{item['invoice_id']}",)).fetchone()[0] == 1
        assert db.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0] == 1


@pytest.mark.parametrize("auth", [None, "Apikey wrong", "Bearer " + TEST_SEPAY_KEY])
def test_webhook_requires_its_own_api_key_and_cannot_be_forged_by_resident(billing, auth):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    response = client.post("/api/billing/sepay/webhook", json=bank_webhook(order),
                           headers={} if auth is None else {"Authorization": auth})
    assert response.status_code == 403
    assert payment_count(database, item) == 0
    assert invoice_status(client, item) == "unpaid"


@pytest.mark.parametrize("changes", [
    {"gateway": "Otherbank"}, {"accountNumber": "9999999999"},
    {"code": "QLCCUNKNOWN", "content": "No invoice code"}, {"transferType": "out"},
])
def test_authenticated_nonmatching_transactions_are_recorded_without_settlement(billing, changes):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    result = deliver(client, order, **changes)
    assert result.status_code == 201 and result.json["success"] is True
    assert payment_count(database, item) == 0 and invoice_status(client, item) == "unpaid"
    rows = client.get("/api/billing/sepay/transactions", headers=headers()).json["items"]
    assert len(rows) == 1


@pytest.mark.parametrize("changes", [
    {"transferAmount": True}, {"transferAmount": 1.5}, {"transferAmount": -1},
    {"id": True}, {"id": None}, {"id": -1}, {"id": "not-a-provider-id"},
    {"transferType": "invalid"},
])
def test_webhook_rejects_invalid_core_fields_without_settlement(billing, changes):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    result = deliver(client, order, **changes)
    assert result.status_code == 400, result.json
    assert payment_count(database, item) == 0


def test_same_provider_id_with_changed_core_data_is_conflict(billing):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    assert deliver(client, order).status_code == 201
    changed = deliver(client, order, transferAmount=1)
    assert changed.status_code == 409
    assert payment_count(database, item) == 1


def test_bank_reference_alias_prevents_same_transfer_double_counted(billing):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    assert deliver(client, order, transaction_id=100001, amount=100000, referenceCode="SAMEBANKREF").status_code == 201
    assert deliver(client, order, transaction_id=100002, amount=100000, referenceCode="SAMEBANKREF").status_code == 201
    assert invoice_status(client, item) == "unpaid" and payment_count(database, item) == 0
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0] == 1


def test_partial_transfers_accumulate_to_full_invoice_and_never_settle_early(billing):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    assert deliver(client, order, transaction_id=101, amount=200000).status_code == 201
    assert invoice_status(client, item) == "unpaid" and payment_count(database, item) == 0
    partial = client.get(f"/api/billing/orders/{order['order_id']}", headers=headers("resident")).json
    assert partial["paid_amount"] == 200000 and partial["remaining_amount"] == 300000
    assert deliver(client, order, transaction_id=102, amount=300000).status_code == 201
    assert invoice_status(client, item) == "paid" and payment_count(database, item) == 1
    assert deliver(client, order, transaction_id=101, amount=200000).status_code == 201
    assert deliver(client, order, transaction_id=102, amount=300000).status_code == 201
    assert payment_count(database, item) == 1
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0] == 2


def test_two_real_transfers_record_excess_and_notify_management_once_per_transfer(billing):
    _, app, database, _ = billing
    client, item, order = checkout(billing)

    def send(transaction_id):
        with app.test_client() as separate:
            response = deliver(separate, order, transaction_id=transaction_id)
            assert response.status_code == 201, response.json

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(send, (100001, 100002)))
    assert invoice_status(client, item) == "paid" and payment_count(database, item) == 1
    rows = client.get("/api/billing/sepay/transactions", headers=headers()).json["items"]
    assert len(rows) == 2
    assert sum(row["allocated_amount"] for row in rows) == item["total_amount"]
    assert sum(row["unallocated_amount"] for row in rows) == item["total_amount"]
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM billing_outbox WHERE event_id=?",
                          (f"billing:paid-admin:monthly:{item['invoice_id']}",)).fetchone()[0] == 1
        admin_notices = [json.loads(row[0]) for row in db.execute("SELECT payload FROM billing_outbox WHERE destination='notification'")
                         if json.loads(row[0]).get("target_role") == "admin"]
        assert len(admin_notices) >= 2  # Settlement plus a warning about the extra transfer.
        issue_before = db.execute("SELECT COUNT(*) FROM billing_outbox").fetchone()[0]
    assert deliver(client, order, transaction_id=100001).status_code == 201
    assert deliver(client, order, transaction_id=100002).status_code == 201
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM billing_outbox").fetchone()[0] == issue_before


def test_overpayment_preserved_and_resolution_is_admin_bookkeeping_only(billing, monkeypatch):
    module, _, database, _ = billing
    client, item, order = checkout(billing)
    assert deliver(client, order, amount=600000).status_code == 201
    listing = "/api/billing/sepay/transactions"
    assert client.get(listing, headers=headers("resident")).status_code == 403
    row = client.get(listing, headers=headers()).json["items"][0]
    assert row["allocated_amount"] == 500000 and row["unallocated_amount"] == 100000
    route = f"{listing}/{row['transaction_id']}/resolve"
    monkeypatch.setattr(module.requests, "post", lambda *a, **k: pytest.fail("resolution must never transfer real money"))
    assert client.post(route, json={"resolution": "refunded", "note": ""}, headers=headers()).status_code == 400
    assert client.post(route, json={"resolution": "refunded", "note": "Bank receipt recorded"}, headers=headers("resident")).status_code == 403
    resolved = client.post(route, json={"resolution": "refunded", "note": "Bank receipt recorded"}, headers=headers())
    assert resolved.status_code == 200, resolved.json
    assert payment_count(database, item) == 1


def test_overdue_invoice_can_still_be_paid_with_fresh_bank_intent(billing):
    _, _, database, _ = billing
    client, item, order = checkout(billing, period="2001-01", due_date="2001-02-01")
    assert order["status"] == "pending" and order["can_pay"] is True
    assert deliver(client, order).status_code == 201
    assert invoice_status(client, item) == "paid" and payment_count(database, item) == 1


def test_configuration_exposes_no_webhook_key_and_missing_config_blocks_checkout(billing, monkeypatch):
    _, app, database, _ = billing
    client = app.test_client()
    assert client.get("/api/billing/payment-config").status_code == 401
    ready = client.get("/api/billing/payment-config", headers=headers("resident"))
    assert ready.status_code == 200 and ready.json["ready"] is True
    assert TEST_SEPAY_KEY not in ready.text
    monkeypatch.setenv("SEPAY_WEBHOOK_API_KEY", "")
    missing = client.get("/api/billing/payment-config", headers=headers("resident"))
    assert missing.json["ready"] is False
    item = invoice(client)
    response = client.post(f"/api/billing/invoices/monthly/{item['invoice_id']}/checkout", json={}, headers=headers("resident"))
    assert response.status_code == 503 and payment_count(database, item) == 0
    assert client.post("/api/billing/sepay/webhook", json={}).status_code == 503


def test_local_simulation_endpoint_is_removed(billing):
    client, _, order = checkout(billing)
    assert client.post(f"/api/billing/orders/{order['order_id']}/simulate", json={}, headers=headers("resident")).status_code == 404


def test_absent_mode_defaults_to_sepay_test_and_rejects_unsupported_modes(billing, monkeypatch):
    module, app, _, _ = billing
    monkeypatch.delenv("PAYMENT_MODE")
    assert module.payment_mode() == "sepay"
    for month, mode in enumerate(("demo", "sandbox", "momo", "production"), start=1):
        monkeypatch.setenv("PAYMENT_MODE", mode)
        assert module.payment_configuration()["ready"] is False
        item = invoice(app.test_client(), period=f"2099-{month:02}")
        response = app.test_client().post(f"/api/billing/invoices/monthly/{item['invoice_id']}/checkout", json={}, headers=headers("resident"))
        assert response.status_code == 503


SEPAY_ACCOUNT_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
API_TRANSACTION_ID = "11111111-1111-4111-8111-111111111111"


def api_row(order, *, transaction_id=API_TRANSACTION_ID, amount=None, bank_reference="BANKREF100001", **changes):
    row = {
        "id": transaction_id, "bank_brand_name": "Vietcombank", "account_number": "0123456789",
        "bank_account_id": SEPAY_ACCOUNT_ID, "transfer_type": "in",
        "amount_in": order["amount"] if amount is None else amount, "amount_out": 0,
        "transaction_content": "Transfer " + order["transfer_content"],
        "reference_number": bank_reference, "code": order["transfer_content"],
        "transaction_date": "2026-11-06 12:00:00",
    }
    return {**row, **changes}


def mock_sepay_api(billing, monkeypatch, pages, *, environment="test"):
    module = billing[0]
    monkeypatch.setenv("SEPAY_ENV", environment)
    monkeypatch.setenv("SEPAY_API_TOKEN", "unit-api-token-never-display-in-url")
    monkeypatch.setenv("SEPAY_BANK_ACCOUNT_ID", SEPAY_ACCOUNT_ID)
    calls = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        expected = "https://userapi-sandbox.sepay.vn/v2/transactions" if environment == "test" else "https://userapi.sepay.vn/v2/transactions"
        assert url == expected
        assert kwargs["headers"]["Authorization"] == "Bearer unit-api-token-never-display-in-url"
        assert kwargs["params"]["bank_account_id"] == SEPAY_ACCOUNT_ID
        assert kwargs["params"]["per_page"] == 100
        page = int(kwargs["params"]["page"])
        assert 1 <= page <= len(pages)
        result = module.requests.Response()
        result.status_code = 200
        result._content = json.dumps({"status": "success", "data": pages[page - 1], "meta": {"pagination": {
            "current_page": page, "last_page": len(pages), "has_more": page < len(pages)}}}).encode()
        return result

    monkeypatch.setattr(module.requests, "get", get)
    return calls


def test_api_reconciliation_recovers_missed_webhook_and_alias_deduplicates_delivery(billing, monkeypatch):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    calls = mock_sepay_api(billing, monkeypatch, [[api_row(order)]])
    route = f"/api/billing/orders/{order['order_id']}/reconcile"
    recovered = client.post(route, json={}, headers=headers("resident"))
    assert recovered.status_code == 200, recovered.json
    assert recovered.json["status"] == "success"
    assert len(calls) == 1 and calls[0][1]["params"]["q"] == order["transfer_content"]
    assert deliver(client, order).status_code == 201
    assert payment_count(database, item) == 1
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM bank_transactions").fetchone()[0] == 1


def test_scheduled_reconciliation_without_logged_in_user_recovers_payment(billing, monkeypatch):
    module, app, database, _ = billing
    client, item, order = checkout(billing)
    mock_sepay_api(billing, monkeypatch, [[api_row(order)]])
    with app.app_context():
        assert not hasattr(g, "user")
        assert module.reconcile_pending_orders() == 1
        result = module.public_order(module.order_row(order["order_id"]))
        assert result["status"] == "success" and not result["can_pay"]
    assert invoice_status(client, item) == "paid" and payment_count(database, item) == 1


def test_prefix_change_preserves_old_webhook_and_duplicate_delivery(billing, monkeypatch):
    _, _, database, _ = billing
    client, item, old_order = checkout(billing)
    assert old_order["transfer_content"].startswith("QLCC")
    assert deliver(client, old_order, amount=200000).status_code == 201
    monkeypatch.setenv("SEPAY_PAYMENT_PREFIX", "TTHD")
    # The same transaction must still deduplicate after changing configuration.
    assert deliver(client, old_order, amount=200000).status_code == 201
    assert deliver(client, old_order, transaction_id=100002, amount=300000).status_code == 201
    assert invoice_status(client, item) == "paid" and payment_count(database, item) == 1
    new_item = invoice(client, period="2099-02")
    new_order = client.post(f"/api/billing/invoices/monthly/{new_item['invoice_id']}/checkout",
                            json={}, headers=headers("resident")).json
    assert new_order["transfer_content"].startswith("TTHD")
    assert len(new_order["transfer_content"]) == 16


def test_reconciliation_recovers_old_prefix_after_configuration_change(billing, monkeypatch):
    module, app, database, _ = billing
    client, item, order = checkout(billing)
    monkeypatch.setenv("SEPAY_PAYMENT_PREFIX", "TTHD")
    mock_sepay_api(billing, monkeypatch, [[api_row(order)]])
    with app.app_context():
        assert module.reconcile_pending_orders() == 1
    assert invoice_status(client, item) == "paid" and payment_count(database, item) == 1


def test_two_references_across_prefix_change_require_manual_review(billing, monkeypatch):
    _, _, database, _ = billing
    client, item, old_order = checkout(billing)
    monkeypatch.setenv("SEPAY_PAYMENT_PREFIX", "TTHD")
    second_item = invoice(client, period="2099-02")
    new_order = client.post(f"/api/billing/invoices/monthly/{second_item['invoice_id']}/checkout",
                            json={}, headers=headers("resident")).json
    response = deliver(client, old_order, code=new_order["transfer_content"],
                       content=old_order["transfer_content"] + " " + new_order["transfer_content"])
    assert response.status_code == 201
    assert payment_count(database, item) == payment_count(database, second_item) == 0
    with sqlite3.connect(database) as db:
        row = db.execute("SELECT status,allocated_amount,unallocated_amount FROM bank_transactions").fetchone()
    assert row == ("unmatched", 0, old_order["amount"])


def test_reconciliation_scans_later_pages_even_after_invoice_is_paid(billing, monkeypatch):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    pages = [[api_row(order)], [api_row(order, transaction_id="22222222-2222-4222-8222-222222222222", bank_reference="SECONDTRANSFER")]]
    calls = mock_sepay_api(billing, monkeypatch, pages)
    response = client.post(f"/api/billing/orders/{order['order_id']}/reconcile", json={}, headers=headers())
    assert response.status_code == 200, response.json
    assert [call[1]["params"]["page"] for call in calls] == [1, 2]
    rows = client.get("/api/billing/sepay/transactions", headers=headers()).json["items"]
    assert len(rows) == 2 and sum(row["unallocated_amount"] for row in rows) == item["total_amount"]
    assert payment_count(database, item) == 1


@pytest.mark.parametrize("changes", [
    {"account_number": "9999999999"}, {"bank_brand_name": "Otherbank"},
    {"code": "WRONGCODE", "transaction_content": "No invoice reference"},
])
def test_api_matching_is_verified_in_addition_to_server_filters(billing, monkeypatch, changes):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    mock_sepay_api(billing, monkeypatch, [[api_row(order, **changes)]])
    response = client.post(f"/api/billing/orders/{order['order_id']}/reconcile", json={}, headers=headers("resident"))
    assert response.status_code == 200, response.json
    assert invoice_status(client, item) == "unpaid" and payment_count(database, item) == 0


def test_reconciliation_network_failure_keeps_payer_reservation(billing, monkeypatch):
    module, _, database, _ = billing
    client, item, order = checkout(billing)
    mock_sepay_api(billing, monkeypatch, [[]])

    def timeout(*args, **kwargs):
        raise module.requests.Timeout("provider temporarily unavailable")

    monkeypatch.setattr(module.requests, "get", timeout)
    response = client.post(f"/api/billing/orders/{order['order_id']}/reconcile", json={}, headers=headers("resident"))
    assert response.status_code == 502
    tracked = client.get(f"/api/billing/orders/{order['order_id']}", headers=headers("resident")).json
    assert tracked["status"] == "pending" and tracked["can_pay"] is True
    assert payment_count(database, item) == 0


def test_partial_transfer_resets_awaiting_state_and_qr_uses_only_remainder(billing, monkeypatch):
    module, _, _, _ = billing
    client, _, order = checkout(billing)
    confirmed = client.post(f"/api/billing/orders/{order['order_id']}/confirm-transfer", json={}, headers=headers("resident"))
    assert confirmed.status_code == 200
    assert deliver(client, order, amount=200000).status_code == 201
    partial = client.get(f"/api/billing/orders/{order['order_id']}", headers=headers("resident")).json
    assert partial["status"] == "pending" and partial["can_pay"] is True
    assert partial["remaining_amount"] == 300000
    requests_seen = []

    def image(url, **kwargs):
        requests_seen.append((url, kwargs))
        response = module.requests.Response()
        response.status_code = 200
        response._content = b"\x89PNG\r\n\x1a\nTEST"
        response.headers["Content-Type"] = "image/png"
        return response

    monkeypatch.setattr(module.requests, "get", image)
    assert client.get(partial["qr_image_url"], headers=headers("resident")).status_code == 200
    query = requests_seen[0][0] + " " + str(requests_seen[0][1].get("params", {}))
    assert "300000" in query and "500000" not in query


def test_qr_download_rejects_stale_amount_when_partial_payment_arrives_during_fetch(billing, monkeypatch):
    module, app, _, _ = billing
    client, _, order = checkout(billing)

    def image_after_partial(url, **kwargs):
        with ThreadPoolExecutor(max_workers=1) as pool:
            callback = pool.submit(lambda: deliver(app.test_client(), order, amount=200000).status_code).result()
        assert callback == 201
        response = module.requests.Response()
        response.status_code = 200
        response._content = b"\x89PNG\r\n\x1a\nOLD-500000-QR"
        response.headers["Content-Type"] = "image/png"
        return response

    monkeypatch.setattr(module.requests, "get", image_after_partial)
    response = client.get(order["qr_image_url"], headers=headers("resident"))
    assert response.status_code == 409
    tracked = client.get(f"/api/billing/orders/{order['order_id']}", headers=headers("resident")).json
    assert tracked["remaining_amount"] == 300000


@pytest.mark.parametrize("operation", ["edit", "manual_payment"])
def test_expired_partial_intent_still_protects_verified_bank_allocation(billing, operation):
    _, _, database, _ = billing
    client, item, order = checkout(billing)
    assert deliver(client, order, amount=200000).status_code == 201
    with sqlite3.connect(database) as db:
        db.execute("UPDATE bank_payment_intents SET expires_at='2000-01-01T00:00:00+00:00' WHERE order_id=?",
                   (order["order_id"],))
    tracked = client.get(f"/api/billing/orders/{order['order_id']}", headers=headers("resident")).json
    assert tracked["status"] == "expired"
    route = f"/api/billing/invoices/monthly/{item['invoice_id']}"
    if operation == "edit":
        response = client.patch(route, json={"electricity_fee": 0, "water_fee": 100000}, headers=headers())
    else:
        response = client.post(route + "/pay", json={"payment_method": "cash"}, headers=headers())
    assert response.status_code == 409
    assert invoice_status(client, item) == "unpaid" and payment_count(database, item) == 0

