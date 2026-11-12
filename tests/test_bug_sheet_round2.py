"""Second round of the tester's bug sheet: card fee, vehicle lines, immediate overdue, technician access."""

import sqlite3

from test_bug_sheet_fixes import confirmed_resident
from test_resident_memberships import make_apartment


def vehicle(c, apartment_id, plate, kind="motorbike", registered="2026-11-09", months=2):
    return c.call("parking", "/api/parking/vehicles", "POST", json={
        "apartment_id": apartment_id, "vehicle_type": kind, "plate_number": plate,
        "registered_date": registered, "registration_months": months})


def cancel(c, vehicle_id):
    response = c.call("parking", f"/api/parking/vehicles/{vehicle_id}", "PATCH", json={"status": "cancelled"})
    assert response.status_code == 200, response.text


def test_a_vehicle_registered_before_is_never_charged_a_second_card(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "CARD-101")
    first = vehicle(c, apartment_id, "29A1-77777", registered="2020-01-01").json()
    assert first["card_fee"] == 100_000
    cancel(c, first["vehicle_id"])
    # The same plate written differently is still the same vehicle with the same card.
    again = vehicle(c, apartment_id, "29a1 777.77")
    assert again.status_code == 201, again.text
    assert again.json()["card_fee"] == 0
    duplicate = vehicle(c, apartment_id, "29A177777")
    assert duplicate.status_code == 409 and "đang hoạt động" in duplicate.json()["error"]
    # Correcting a new registration's plate to a known one drops its card fee.
    old = vehicle(c, apartment_id, "29A1-60000", registered="2020-01-01").json()
    cancel(c, old["vehicle_id"])
    typo = vehicle(c, apartment_id, "29A1-6000").json()
    assert typo["card_fee"] == 100_000
    fixed = c.call("parking", f"/api/parking/vehicles/{typo['vehicle_id']}", "PATCH", json={"plate_number": "29A1 60000"})
    assert fixed.status_code == 200 and fixed.json()["card_fee"] == 0
    # A bicycle comes back under its old code and keeps its card too.
    bicycle = vehicle(c, apartment_id, None, kind="bicycle", registered="2020-01-01").json()
    assert bicycle["card_fee"] == 100_000 and bicycle["plate_number"].startswith("CARD-101-XD-")
    cancel(c, bicycle["vehicle_id"])
    returning = vehicle(c, apartment_id, bicycle["plate_number"], kind="bicycle").json()
    assert returning["card_fee"] == 0
    assert vehicle(c, apartment_id, "--", kind="bicycle").status_code == 400


def test_service_invoice_detail_lists_each_vehicle_with_its_months_and_dates(service_cluster):
    c = service_cluster
    apartment_id, uid, _ = confirmed_resident(c, "LINES-101", "lines.user")
    early = vehicle(c, apartment_id, "29A1-81818", registered="2026-08-15", months=4).json()
    base = c.call("billing", "/api/billing/invoices/semiannual", "POST", json={
        "apartment_id": apartment_id, "period": "2026-H2", "service_fee": 1000, "due_date": "2099-01-01"}).json()
    # August to December at 100.000 each, plus the first card.
    assert base["parking_fee"] == 600_000
    # Recorded on the dates it would have happened: vehicle in August, invoice a few days later.
    with sqlite3.connect(c.db_path) as db:
        db.execute("UPDATE vehicles SET created_at='2026-08-15 08:00:00' WHERE vehicle_id=?", (early["vehicle_id"],))
        db.execute("UPDATE semiannual_invoices SET created_at='2026-08-20 00:00:00' WHERE invoice_id=?", (base["invoice_id"],))
    late = vehicle(c, apartment_id, "29A1-82828", registered="2026-11-09").json()
    route = f"/api/billing/invoices/semiannual/{base['invoice_id']}"
    for scope in ({"role": "admin"}, {"role": "resident", "user_id": uid}, {"role": "technician"}):
        lines = c.call("billing", route, **scope).json()["vehicles"]
        # The later vehicle is not on this invoice; it is billed on its own extra invoice.
        assert [line["vehicle_id"] for line in lines] == [early["vehicle_id"]], scope
    line = lines[0]
    assert line["plate_number"] == "29A1-81818" and line["vehicle_type"] == "motorbike"
    assert line["registration_months"] == 4 and line["registered_date"] == "2026-08-15"
    assert line["minimum_end_date"] == "2026-12-15"
    assert line["months"] == 5 and line["monthly_fee"] == 100_000 and line["card_fee"] == 100_000
    extra = c.call("billing", f"/api/billing/vehicle-billing/{late['vehicle_id']}/supplement", "POST",
                   json={"due_date": "2099-02-01"})
    assert extra.status_code == 201, extra.text
    lines = c.call("billing", f"/api/billing/invoices/semiannual/{extra.json()['invoice_id']}").json()["vehicles"]
    assert [(line["vehicle_id"], line["months"]) for line in lines] == [(late["vehicle_id"], 2)]
    monthly = c.call("billing", "/api/billing/invoices/monthly", "POST", json={
        "apartment_id": apartment_id, "period": "2099-01", "electricity_fee": 300, "water_fee": 200,
        "due_date": "2099-02-01"}).json()
    assert "vehicles" not in c.call("billing", f"/api/billing/invoices/monthly/{monthly['invoice_id']}").json()


def summaries(c):
    with sqlite3.connect(c.db_path) as db:
        return db.execute("SELECT COUNT(*) FROM billing_outbox WHERE event_id LIKE 'billing:overdue-summary:%'").fetchone()[0]


def test_an_invoice_past_its_due_date_shows_overdue_at_once(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "LATE-101")
    before = summaries(c)
    late = c.call("billing", "/api/billing/invoices/monthly", "POST", json={
        "apartment_id": apartment_id, "period": "2001-01", "electricity_fee": 300, "water_fee": 200, "due_date": "2001-02-01"})
    assert late.status_code == 201, late.text
    assert late.json()["status"] == "overdue"
    assert c.call("billing", f"/api/billing/invoices/monthly/{late.json()['invoice_id']}").json()["status"] == "overdue"
    on_time = c.call("billing", "/api/billing/invoices/monthly", "POST", json={
        "apartment_id": apartment_id, "period": "2099-01", "electricity_fee": 300, "water_fee": 200, "due_date": "2099-02-01"})
    assert on_time.json()["status"] == "unpaid"
    moved = c.call("billing", f"/api/billing/invoices/monthly/{on_time.json()['invoice_id']}", "PATCH",
                   json={"due_date": "2001-03-01"})
    assert moved.status_code == 200 and moved.json()["status"] == "overdue"
    # Two batches on the same day each reach management; neither replaces the other.
    assert summaries(c) == before + 2
    with sqlite3.connect(c.db_path) as db:
        overdue = db.execute("SELECT COUNT(*) FROM billing_outbox WHERE event_id IN (?,?)", (
            f"billing:overdue:monthly:{late.json()['invoice_id']}",
            f"billing:overdue:monthly:{on_time.json()['invoice_id']}")).fetchone()[0]
    assert overdue == 2


def test_technicians_inherit_invoice_management_but_not_reports_or_notices(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "TECH-BILL")
    tech = {"role": "technician"}
    # Issued and adjusted by a technician, exactly as management would.
    created = c.call("billing", "/api/billing/invoices/monthly", "POST", json={
        "apartment_id": apartment_id, "period": "2099-03", "electricity_fee": 300, "water_fee": 200,
        "due_date": "2099-04-01"}, **tech)
    assert created.status_code == 201, created.text
    identifier = created.json()["invoice_id"]
    edited = c.call("billing", f"/api/billing/invoices/monthly/{identifier}", "PATCH", json={"due_date": "2099-04-15"}, **tech)
    assert edited.status_code == 200 and edited.json()["due_date"] == "2099-04-15"
    rows = c.call("billing", "/api/billing/invoices/monthly", **tech).json()["items"]
    assert identifier in {row["invoice_id"] for row in rows}
    assert c.call("billing", f"/api/billing/invoices/monthly/{identifier}", **tech).status_code == 200
    assert c.call("billing", "/api/billing/summary", **tech).status_code == 200
    assert c.call("billing", "/api/billing/payment-config", **tech).status_code == 200
    assert c.call("billing", "/api/billing/sepay/transactions", **tech).status_code == 200
    # Nothing is waiting for the bank, so there is no session to release: refused on the rule, not the role.
    release = c.call("billing", f"/api/billing/invoices/monthly/{identifier}/release-payment", "POST",
                     json={"note": "Đã kiểm tra"}, **tech)
    assert release.status_code == 409, release.text
    # Like management, a technician records cash only for the full amount, and only once.
    route = f"/api/billing/invoices/monthly/{identifier}/pay"
    assert c.call("billing", route, "POST", json={"payment_method": "cash", "amount": 1}, **tech).status_code == 400
    paid = c.call("billing", route, "POST", json={"payment_method": "cash"}, **tech)
    assert paid.status_code == 201, paid.text
    assert c.call("billing", route, "POST", json={"payment_method": "cash"}, **tech).status_code == 409
    assert c.call("billing", f"/api/billing/invoices/monthly/{identifier}").json()["status"] == "paid"
    with sqlite3.connect(c.db_path) as db:
        actor = db.execute("SELECT actor_user_id FROM audit_log WHERE action='manual_payment_recorded' AND entity_id=? "
                           "ORDER BY audit_id DESC LIMIT 1", (str(identifier),)).fetchone()[0]
    assert actor == c.call("auth", "/api/auth/me", **tech).json()["user"]["user_id"]
    payments = c.call("billing", "/api/billing/payments", **tech).json()["items"]
    payment = next(row for row in payments if row["invoice_id"] == identifier and row["invoice_type"] == "monthly")
    assert c.call("billing", payment["receipt_url"], **tech).status_code == 200
    assert c.call("billing", "/api/billing/reports?year=2099", **tech).status_code == 403
    assert c.call("billing", "/api/billing/reports?year=2099").status_code == 200
    notice = {"type": "general", "title": "Thử", "content": "Nội dung"}
    assert c.call("notification", "/api/notifications", "POST", json=notice, **tech).status_code == 403
    assert c.call("notification", "/api/notifications", "POST", json=notice).status_code == 201
