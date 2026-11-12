"""Actual HTTP orchestration across billing, resident, parking and event consumers."""

import sqlite3
from pathlib import Path

from conftest import TEST_SEPAY_KEY, bank_webhook


def test_real_http_invoice_overdue_payment_and_restoration(service_cluster):
    cluster = service_cluster
    response = cluster.call("resident", "/api/apartments", method="POST", json={
        "code": "HTTP-BILLING-01", "block": "TEST", "floor": 1, "area": 70})
    assert response.status_code == 201, response.text
    apartment_id = response.json()["apartment_id"]
    cluster.release_apartments(3)
    resident_id = cluster.call("resident", "/api/residents/me", role="resident").json()["resident_id"]
    response = cluster.call("resident", "/api/contracts", method="POST", json={
        "apartment_id": apartment_id, "resident_id": resident_id, "contract_type": "rental",
        "start_date": "2000-01-01", "end_date": "2099-12-31"})
    assert response.status_code == 201, response.text
    for kind, fee, plate in (("motorbike", 100000, "HTTP-BILLING"), ("bicycle", 50000, None)):
        response = cluster.call("parking", "/api/parking/vehicles", method="POST", json={
            "apartment_id": apartment_id, "vehicle_type": kind, "monthly_fee": fee,
            "plate_number": plate, "registered_date": "2001-01-01"})
        assert response.status_code == 201, response.text

    response = cluster.call("billing", "/api/billing/invoices/semiannual", method="POST", json={
        "apartment_id": apartment_id, "period": "2001-H1", "due_date": "2001-07-01", "service_fee": 3000000})
    assert response.status_code == 201, response.text
    halfyear = response.json()
    assert halfyear["parking_fee"] == 1100000  # Six months plus two cards, issued once.
    assert halfyear["total_amount"] == 4100000
    response = cluster.call("billing", "/api/billing/invoices/monthly", method="POST", json={
        "apartment_id": apartment_id, "period": "2001-06", "due_date": "2001-07-01", "electricity_fee": 400000, "water_fee": 100000})
    assert response.status_code == 201, response.text
    monthly = response.json()
    billing = cluster.modules["billing"]
    # Issued after their due date, so both are overdue at once; a later scan changes nothing.
    assert halfyear["status"] == monthly["status"] == "overdue"
    with cluster.apps["billing"].app_context():
        assert billing.mark_overdue("2001-07-02") == 0
        while billing.dispatch_outbox():
            pass

    def tickets():
        response = cluster.call("maintenance", "/api/maintenance/tickets")
        assert response.status_code == 200
        return [row for row in response.json()["items"] if row["apartment_id"] == apartment_id]

    # Overdue invoices are handled on the technician's service screen, not as repair tickets.
    assert tickets() == []

    response = cluster.call("billing", f"/api/billing/invoices/semiannual/{halfyear['invoice_id']}/pay",
                            method="POST", json={"payment_method": "cash"})
    assert response.status_code == 201, response.text
    with cluster.apps["billing"].app_context():
        assert billing.dispatch_outbox() == 2

    response = cluster.call("billing", f"/api/billing/invoices/monthly/{monthly['invoice_id']}/checkout",
                            method="POST", role="resident", json={})
    assert response.status_code == 201, response.text
    order = response.json()
    response = cluster.call("billing", "/api/billing/sepay/webhook", method="POST",
                            json=bank_webhook(order), headers={"Authorization": "Apikey " + TEST_SEPAY_KEY})
    assert response.status_code == 201, response.text
    settled_order = cluster.call("billing", f"/api/billing/orders/{order['order_id']}", role="resident").json()
    payment_id = settled_order["payment_id"]
    with cluster.apps["billing"].app_context():
        assert billing.dispatch_outbox() == 2
        assert billing.dispatch_outbox() == 0
    assert tickets() == []
    receipt = cluster.call("billing", f"/api/billing/payments/monthly/{payment_id}/receipt")
    assert receipt.status_code == 200 and "SEPAY" in receipt.json()["notice"].upper()
    notices = cluster.call("notification", "/api/notifications").json()["items"]
    assert len([row for row in notices if row["target_apartment_id"] == apartment_id]) == 6
    with sqlite3.connect(cluster.db_path) as db:
        admin_notice_ids = set()
        for kind, item in (("monthly", monthly), ("semiannual", halfyear)):
            rows = db.execute("SELECT e.notification_id FROM notification_events e "
                              "JOIN notification_audience a ON a.notification_id=e.notification_id "
                              "WHERE e.event_id=? AND a.target_role='admin'",
                              (f"billing:paid-admin:{kind}:{item['invoice_id']}",)).fetchall()
            assert len(rows) == 1
            admin_notice_ids.add(rows[0][0])
    assert admin_notice_ids <= {row["notification_id"] for row in notices}
    for notice in notices:
        if notice["notification_id"] in admin_notice_ids:
            assert notice["target_apartment_id"] is None  # Context must not grant resident access.
            assert notice["related_apartment_id"] == apartment_id
            assert notice["related_apartment_code"] == "HTTP-BILLING-01"
            assert notice["invoice_created_at"] and notice["paid_at"]
    resident_notices = cluster.call("notification", "/api/notifications", role="resident").json()["items"]
    assert not admin_notice_ids & {row["notification_id"] for row in resident_notices}
    # The migration enriches old notifications without emitting duplicates,
    # changing their original date/content, or widening their audience.
    with sqlite3.connect(cluster.db_path) as db:
        before = db.execute("SELECT * FROM notifications ORDER BY notification_id").fetchall()
        db.execute("DELETE FROM notification_billing_context")
        script = (Path(__file__).resolve().parents[1] / "migrations/notifications_billing_context.sql").read_text(encoding="utf-8")
        db.executescript(script)
        db.executescript(script)
        assert db.execute("SELECT * FROM notifications ORDER BY notification_id").fetchall() == before
    notices = cluster.call("notification", "/api/notifications").json()["items"]
    assert all(n["related_apartment_code"] == "HTTP-BILLING-01" and n["paid_at"]
               for n in notices if n["notification_id"] in admin_notice_ids)
    resident_notices = cluster.call("notification", "/api/notifications", role="resident").json()["items"]
    assert not admin_notice_ids & {row["notification_id"] for row in resident_notices}


def test_invoice_access_requires_verified_current_contract_not_registered_apartment(service_cluster):
    cluster = service_cluster
    apartments = []
    for code in ("HTTP-SCOPE-OWN", "HTTP-SCOPE-OTHER"):
        response = cluster.call("resident", "/api/apartments", method="POST", json={
            "code": code, "block": "TEST", "floor": 1, "area": 70})
        assert response.status_code == 201, response.text
        apartments.append(response.json())
    own, other = apartments
    resident_id = cluster.call("resident", "/api/residents/me", role="resident").json()["resident_id"]
    response = cluster.call("resident", f"/api/residents/{resident_id}", method="PATCH", json={
        "registered_apartment_code": own["code"]})
    assert response.status_code == 200, response.text
    contract = {"apartment_id": own["apartment_id"], "resident_id": resident_id,
                "contract_type": "rental", "start_date": "2000-01-01", "end_date": "2001-12-31"}
    response = cluster.call("resident", "/api/contracts", method="POST", json=contract)
    assert response.status_code == 201, response.text

    invoices = {}
    for kind in ("monthly", "semiannual"):
        for apartment in apartments:
            payload = {"apartment_id": apartment["apartment_id"],
                       "period": "2099-01" if kind == "monthly" else "2099-H1", "due_date": "2099-02-01"}
            payload.update({"electricity_fee": 10000, "water_fee": 20000}
                           if kind == "monthly" else {"service_fee": 30000})
            response = cluster.call("billing", f"/api/billing/invoices/{kind}", method="POST", json=payload)
            assert response.status_code == 201, response.text
            invoices[kind, apartment["apartment_id"]] = response.json()

    profile = cluster.call("resident", "/api/residents/me", role="resident").json()
    assert profile["registered_apartment_code"] == own["code"]
    assert own["apartment_id"] not in profile["apartment_ids"]
    for kind in ("monthly", "semiannual"):
        invoice_id = invoices[kind, own["apartment_id"]]["invoice_id"]
        route = f"/api/billing/invoices/{kind}/{invoice_id}"
        assert cluster.call("billing", route, role="resident").status_code == 403
        rows = cluster.call("billing", f"/api/billing/invoices/{kind}", role="resident").json()["items"]
        assert not any(row["apartment_id"] == own["apartment_id"] for row in rows)

    # The management-approved current contract is the only change that grants access.
    cluster.release_apartments(3)
    response = cluster.call("resident", "/api/contracts", method="POST", json={
        **contract, "start_date": "2020-01-01", "end_date": "2099-12-31"})
    assert response.status_code == 201, response.text
    for kind in ("monthly", "semiannual"):
        mine = invoices[kind, own["apartment_id"]]
        theirs = invoices[kind, other["apartment_id"]]
        rows = cluster.call("billing", f"/api/billing/invoices/{kind}", role="resident").json()["items"]
        assert any(row["invoice_id"] == mine["invoice_id"] for row in rows)
        assert not any(row["invoice_id"] == theirs["invoice_id"] for row in rows)
        own_route = f"/api/billing/invoices/{kind}/{mine['invoice_id']}"
        other_route = f"/api/billing/invoices/{kind}/{theirs['invoice_id']}"
        assert cluster.call("billing", own_route, role="resident").status_code == 200
        assert cluster.call("billing", other_route, role="resident").status_code == 403
        assert cluster.call("billing", own_route + "/checkout", method="POST", json={}).status_code == 403
        assert cluster.call("billing", other_route + "/checkout", method="POST", role="resident", json={}).status_code == 403
        response = cluster.call("billing", own_route + "/checkout", method="POST", role="resident", json={})
        assert response.status_code == 201, response.text
        order_id = response.json()["order_id"]
        assert cluster.call("billing", f"/api/billing/orders/{order_id}").status_code == 200
        assert cluster.call("billing", f"/api/billing/orders/{order_id}/confirm-transfer", method="POST", json={}).status_code == 403
    with sqlite3.connect(cluster.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM bank_payment_intents").fetchone()[0] == 2
