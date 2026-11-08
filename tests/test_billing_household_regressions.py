"""Actual HTTP household coordination and simultaneous bank arrivals."""
from concurrent.futures import ThreadPoolExecutor
import json
import sqlite3

import pytest

from conftest import TEST_SEPAY_KEY, bank_webhook
from test_resident_memberships import create_invoice, make_apartment, register_resident


@pytest.mark.parametrize("kind", ["monthly", "semiannual"])
def test_verified_household_shares_one_payer_and_records_both_bank_arrivals(service_cluster, kind):
    c = service_cluster
    apartment_id = make_apartment(c, "SHARED-SETTLEMENT")
    scopes = []
    for username in ("shared.first", "shared.second"):
        user_id, profile = register_resident(c, "SHARED-SETTLEMENT", username)
        confirmed = c.call("resident", f"/api/residents/{profile['resident_id']}/apartments",
                           "POST", json={"apartment_id": apartment_id})
        assert confirmed.status_code == 201, confirmed.text
        scopes.append({"role": "resident", "user_id": user_id})
    outsider_id, _ = register_resident(c, "SHARED-SETTLEMENT", "shared.unconfirmed")
    outsider = {"role": "resident", "user_id": outsider_id}
    item = create_invoice(c, apartment_id, kind)
    route = f"/api/billing/invoices/{kind}/{item['invoice_id']}"
    assert c.call("billing", route + "/checkout", "POST", json={}).status_code == 403
    assert c.call("billing", route + "/checkout", "POST", json={}, **outsider).status_code == 403

    def checkout(scope):
        response = c.call("billing", route + "/checkout", "POST", json={}, **scope)
        assert response.status_code in (200, 201), response.text
        return response.json()

    with ThreadPoolExecutor(max_workers=2) as pool:
        orders = list(pool.map(checkout, scopes))
    assert orders[0]["order_id"] == orders[1]["order_id"]
    assert sum(order["can_pay"] for order in orders) == 1
    order_route = f"/api/billing/orders/{orders[0]['order_id']}"
    owner_index = next(index for index, order in enumerate(orders) if order["can_pay"])
    assert c.call("billing", order_route, **outsider).status_code == 403
    assert c.call("billing", order_route + "/confirm-transfer", "POST", json={}).status_code == 403
    assert c.call("billing", order_route + "/confirm-transfer", "POST", json={},
                  **scopes[1-owner_index]).status_code == 403
    confirmed = c.call("billing", order_route + "/confirm-transfer", "POST", json={}, **scopes[owner_index])
    assert confirmed.status_code == 200 and confirmed.json()["status"] == "awaiting_confirmation"
    assert c.call("billing", route, **scopes[0]).json()["status"] != "paid"

    def settle(transaction_id):
        response = c.call("billing", "/api/billing/sepay/webhook", "POST",
                          json=bank_webhook(orders[owner_index], transaction_id=transaction_id),
                          headers={"Authorization": "Apikey " + TEST_SEPAY_KEY})
        assert response.status_code == 201, response.text

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(settle, (301, 302)))
    paid = c.call("billing", order_route, **scopes[0]).json()
    for scope in scopes:
        assert c.call("billing", route, **scope).json()["status"] == "paid"
        assert c.call("billing", paid["receipt_url"], **scope).status_code == 200
        assert c.call("billing", route + "/checkout", "POST", json={}, **scope).status_code == 409
    assert c.call("billing", "/api/billing/sepay/transactions", **scopes[0]).status_code == 403
    transactions = c.call("billing", "/api/billing/sepay/transactions").json()["items"]
    assert len(transactions) == 2
    assert sum(row["allocated_amount"] for row in transactions) == item["total_amount"]
    assert sum(row["unallocated_amount"] for row in transactions) == item["total_amount"]
    with sqlite3.connect(c.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM bank_payment_intents WHERE invoice_type=? AND invoice_id=?",
                          (kind, item["invoice_id"])).fetchone()[0] == 1
        assert db.execute(f"SELECT COUNT(*) FROM {kind}_payments WHERE invoice_id=?",
                          (item["invoice_id"],)).fetchone()[0] == 1
        notices = db.execute("SELECT payload FROM billing_outbox WHERE event_id=?",
                             (f"billing:paid-admin:{kind}:{item['invoice_id']}",)).fetchall()
        assert len(notices) == 1 and json.loads(notices[0][0])["target_role"] == "admin"
