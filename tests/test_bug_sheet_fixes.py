"""Regression tests for the QLCC bug sheet tested on the live site on 2026-11-09."""
import sqlite3

import requests

from test_resident_memberships import make_apartment, register_resident

PASSWORD = "Membership!2026"


def confirm(c, profile, apartment_id):
    response = c.call("resident", f"/api/residents/{profile['resident_id']}/apartments", "POST",
                      json={"apartment_id": apartment_id})
    assert response.status_code == 201, response.text


def confirmed_resident(c, code, username):
    apartment_id = make_apartment(c, code)
    user_id, profile = register_resident(c, code, username)
    confirm(c, profile, apartment_id)
    return apartment_id, user_id, profile


def notices(c, **scope):
    return c.call("notification", "/api/notifications", **scope).json()["items"]


def change_password(c, user_id, current, new, confirm_password):
    return c.call("auth", "/api/auth/me/password", "POST", role="resident", user_id=user_id, json={
        "current_password": current, "new_password": new, "confirm_password": confirm_password})


def test_password_change_checks_in_the_agreed_order(service_cluster):
    c = service_cluster
    make_apartment(c, "PASS-ORDER")
    uid, _ = register_resident(c, "PASS-ORDER", "password.order")
    # Length comes first, then the current password, then the confirmation, then "must differ".
    short = change_password(c, uid, "wrong-current", "abc", "xyz")
    assert short.json()["error"] == "Mật khẩu cần từ 6 đến 30 ký tự."
    wrong = change_password(c, uid, "wrong-current", "NewPassword1", "Different1")
    assert wrong.json()["error"] == "Mật khẩu hiện tại không đúng."
    mismatch = change_password(c, uid, PASSWORD, PASSWORD, "Different1")
    assert mismatch.json()["error"] == "Mật khẩu mới và mật khẩu nhập lại không trùng khớp."
    same = change_password(c, uid, PASSWORD, PASSWORD, PASSWORD)
    assert same.json()["error"] == "Mật khẩu mới không được trùng với mật khẩu hiện tại."
    assert change_password(c, uid, PASSWORD, "NewPassword1", "NewPassword1").status_code == 200


def test_opening_a_notification_marks_it_read_for_every_role(service_cluster):
    c = service_cluster
    apartment_id, uid, _ = confirmed_resident(c, "READ-101", "read.user")
    created = c.call("notification", "/api/notifications", "POST",
                     json={"type": "general", "title": "Đọc thử", "content": "Nội dung"})
    identifier = created.json()["notification_id"]
    assert apartment_id
    for scope in ({"role": "admin"}, {"role": "technician"}, {"role": "resident", "user_id": uid}):
        row = next(n for n in notices(c, **scope) if n["notification_id"] == identifier)
        assert not row["is_read"]
        assert c.call("notification", f"/api/notifications/{identifier}/read", "POST", json={}, **scope).status_code == 200
        row = next(n for n in notices(c, **scope) if n["notification_id"] == identifier)
        assert row["is_read"]
    other_admin = next(n for n in notices(c, role="admin", user_id=2) if n["notification_id"] == identifier)
    assert not other_admin["is_read"]


def test_confirming_an_apartment_notifies_and_fills_the_apartment(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "CONFIRM-101")
    uid, profile = register_resident(c, "CONFIRM-101", "confirm.user")
    assert c.call("resident", f"/api/apartments/{apartment_id}").json()["status"] == "vacant"
    confirm(c, profile, apartment_id)
    row = c.call("resident", f"/api/apartments/{apartment_id}").json()
    assert row["status"] == "occupied" and row["current_resident"] == profile["full_name"]
    assert any("CONFIRM-101 đã được xác nhận" in n["title"] for n in notices(c, role="resident", user_id=uid))
    assert c.call("resident", f"/api/residents/{profile['resident_id']}/apartments/{apartment_id}", "DELETE").status_code == 200
    assert c.call("resident", f"/api/apartments/{apartment_id}").json()["status"] == "vacant"


def test_ticket_changes_reach_residents_management_and_all_technicians(service_cluster):
    c = service_cluster
    apartment_id, uid, _ = confirmed_resident(c, "TICKET-101", "ticket.user")
    with sqlite3.connect(c.db_path) as db:
        other = db.execute("INSERT INTO users(username,password_hash,role) VALUES('tech.two','x','technician')").lastrowid
        db.execute("INSERT INTO technicians(user_id,full_name,specialty) VALUES (?,'Kỹ thuật hai','general')", (other,))
    created = c.call("maintenance", "/api/maintenance/tickets", "POST", role="resident", user_id=uid, json={
        "apartment_id": apartment_id, "type": "repair", "description": "Rò nước"})
    assert created.status_code == 201, created.text
    ticket = created.json()["ticket_id"]
    title = f"Yêu cầu sửa chữa mới #{ticket}"
    for scope in ({"role": "resident", "user_id": uid}, {"role": "admin"}, {"role": "technician"},
                  {"role": "technician", "user_id": other}):
        assert any(n["title"] == title for n in notices(c, **scope)), scope
    # Unassigned work can be picked up by any technician, who then becomes the person in charge.
    picked = c.call("maintenance", f"/api/maintenance/tickets/{ticket}", "PATCH", role="technician", user_id=other,
                    json={"status": "in_progress"})
    assert picked.status_code == 200, picked.text
    assert any(row["ticket_id"] == ticket for row in
               c.call("maintenance", "/api/maintenance/tickets", role="technician").json()["items"])
    finished = c.call("maintenance", f"/api/maintenance/tickets/{ticket}", "PATCH", role="technician",
                      json={"status": "completed"})
    assert finished.status_code == 200, finished.text
    update = f"Cập nhật phiếu sửa chữa #{ticket}"
    assert len([n for n in notices(c, role="resident", user_id=uid) if n["title"] == update]) == 2


def test_management_can_file_a_ticket_for_a_shared_place(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "PLACE-101")
    shared = c.call("maintenance", "/api/maintenance/tickets", "POST",
                    json={"location": "Sảnh tòa A", "type": "repair", "description": "Hỏng đèn"})
    assert shared.status_code == 201, shared.text
    assert shared.json()["apartment_id"] is None and shared.json()["location"] == "Sảnh tòa A"
    home = c.call("maintenance", "/api/maintenance/tickets", "POST",
                  json={"location": "place-101", "type": "repair", "description": "Hỏng vòi"})
    assert home.json()["apartment_id"] == apartment_id and home.json()["location"] is None
    title = f"Yêu cầu sửa chữa mới #{shared.json()['ticket_id']}"
    assert any(n["title"] == title for n in notices(c, role="technician"))


def test_only_residents_send_requests_and_may_cancel_while_pending(service_cluster):
    c = service_cluster
    _, uid, profile = confirmed_resident(c, "CANCEL-101", "cancel.user")
    payload = {"type": "complaint", "category": "Tiếng ồn", "content": "Ồn ban đêm"}
    assert c.call("complaint", "/api/complaints", "POST", json={**payload, "resident_id": profile["resident_id"]}).status_code == 403
    assert c.call("complaint", "/api/complaints", "POST", role="technician", json=payload).status_code == 403
    scope = {"role": "resident", "user_id": uid}

    def send():
        return c.call("complaint", "/api/complaints", "POST", json=payload, **scope).json()["complaint_id"]

    first, second = send(), send()
    assert c.call("complaint", f"/api/complaints/{first}/cancel", "POST", json={}, role="resident").status_code == 403
    cancelled = c.call("complaint", f"/api/complaints/{first}/cancel", "POST", json={}, **scope)
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "cancelled"
    assert c.call("complaint", f"/api/complaints/{first}", "PATCH", json={"status": "processing"}).status_code == 409
    assert c.call("complaint", f"/api/complaints/{second}", "PATCH", json={"status": "processing"}).status_code == 200
    blocked = c.call("complaint", f"/api/complaints/{second}/cancel", "POST", json={}, **scope)
    assert blocked.status_code == 409
    assert blocked.json()["error"] == "Đơn đang ở trạng thái đang xử lý không thể huỷ yêu cầu."
    assert c.call("complaint", "/api/complaints/summary").json()["totals"]["cancelled_count"] >= 1


def test_parking_application_is_limited_to_the_accounts_apartment(service_cluster):
    c = service_cluster
    make_apartment(c, "PARK-OTHER")
    _, uid, _ = confirmed_resident(c, "PARK-MINE", "park.user")
    content = ("Loại xe: Xe máy\nBiển số: 29A1-11111\nCăn hộ: {}\nNgày bắt đầu: 2026-11-09\n"
               "Thời gian cam kết: 2 tháng\nGhi chú: Không có")

    def apply(code):
        return c.call("complaint", "/api/complaints", "POST", role="resident", user_id=uid, json={
            "type": "registration", "category": "Đăng ký gửi xe", "content": content.format(code)})

    assert apply("PARK-OTHER").status_code == 403
    assert apply("park-mine").status_code == 201


def test_account_screen_only_changes_the_role_and_staff_list_follows(service_cluster):
    c = service_cluster
    make_apartment(c, "ROLE-101")
    uid, profile = register_resident(c, "ROLE-101", "role.user")
    login = requests.post(c.urls["auth"] + "/api/auth/login", json={"username": "role.user", "password": PASSWORD}, timeout=10)
    old_token = login.json()["token"]
    assert c.call("auth", "/api/auth/users", "POST", json={"username": "x.new", "password": "abcdef"}).status_code == 405
    assert c.call("maintenance", "/api/maintenance/technicians", "POST", json={}).status_code == 405
    assert c.call("auth", f"/api/auth/users/{uid}", "PATCH", json={"status": "locked"}).status_code == 400
    assert c.call("auth", f"/api/auth/users/{uid}", "PATCH", json={"role": "owner"}).status_code == 400
    assert c.call("auth", "/api/auth/users/1", "PATCH", json={"role": "resident"}).status_code == 400

    def staff():
        return {row["user_id"]: row for row in c.call("maintenance", "/api/maintenance/technicians").json()["items"]}

    assert uid not in staff()
    changed = c.call("auth", f"/api/auth/users/{uid}", "PATCH", json={"role": "technician"})
    assert changed.status_code == 200 and changed.json()["role"] == "technician"
    assert staff()[uid]["full_name"] == profile["full_name"]
    assert requests.get(c.urls["auth"] + "/api/auth/me", headers={"Authorization": "Bearer " + old_token}, timeout=10).status_code == 401
    fresh = requests.post(c.urls["auth"] + "/api/auth/login", json={"username": "role.user", "password": PASSWORD}, timeout=10)
    assert fresh.json()["user"]["role"] == "technician"
    assert c.call("auth", f"/api/auth/users/{uid}", "PATCH", json={"role": "resident"}).status_code == 200
    assert uid not in staff()


def test_resident_turned_staff_and_staff_turned_resident_have_a_profile(service_cluster):
    c = service_cluster
    with sqlite3.connect(c.db_path) as db:
        uid = db.execute("INSERT INTO users(username,password_hash,role,full_name) VALUES('staff.res','x','admin','Nhân Viên')").lastrowid
    assert c.call("auth", f"/api/auth/users/{uid}", "PATCH", json={"role": "resident"}).status_code == 200
    profiles = c.call("resident", "/api/residents").json()["items"]
    assert next(p for p in profiles if p["user_id"] == uid)["full_name"] == "Nhân Viên"


def test_apartment_floor_and_area_must_be_positive(service_cluster):
    c = service_cluster

    def create(**changes):
        return c.call("resident", "/api/apartments", "POST", json={"code": "F-1", "block": "A", "floor": 2, "area": 50, **changes})

    assert create(floor=0).status_code == 400
    assert create(floor=-3).status_code == 400
    assert create(floor=201).status_code == 400
    assert create(area=0).status_code == 400
    assert create(area=-1).status_code == 400
    assert create(floor="12").status_code == 201


def test_report_reconciles_issued_with_collected_and_outstanding(service_cluster):
    c = service_cluster

    def report(year):
        return c.call("billing", f"/api/billing/reports?year={year}").json()["totals"]

    apartment_id = make_apartment(c, "REPORT-101")
    old = c.call("billing", "/api/billing/invoices/semiannual", "POST", json={
        "apartment_id": apartment_id, "period": "2095-H2", "service_fee": 1000, "parking_fee": 0, "due_date": "2096-01-15"})
    assert old.status_code == 201, old.text
    paid = c.call("billing", f"/api/billing/invoices/semiannual/{old.json()['invoice_id']}/pay", "POST", json={"payment_method": "cash"})
    assert paid.status_code == 201, paid.text
    with sqlite3.connect(c.db_path) as db:
        # Paid in the following year: it belongs to the 2095 invoices, not to 2096.
        db.execute("UPDATE semiannual_payments SET paid_at='2096-01-10 09:00:00' WHERE payment_id=?", (paid.json()["payment_id"],))
    assert c.call("billing", "/api/billing/invoices/monthly", "POST", json={
        "apartment_id": apartment_id, "period": "2096-03", "electricity_fee": 300, "water_fee": 200, "due_date": "2096-04-15"}).status_code == 201
    later, earlier = report(2096), report(2095)
    assert later["billed_amount"] == 500 and later["collected_amount"] == 0 and later["outstanding_amount"] == 500
    assert earlier["billed_amount"] == earlier["collected_amount"] == earlier["semiannual_collected_amount"] == 1000


def overdue_invoice(c, apartment_id):
    created = c.call("billing", "/api/billing/invoices/monthly", "POST", json={
        "apartment_id": apartment_id, "period": "2001-01", "electricity_fee": 300, "water_fee": 200, "due_date": "2001-02-01"})
    assert created.status_code == 201, created.text
    billing = c.modules["billing"]
    with c.apps["billing"].app_context():
        billing.mark_overdue("2001-02-02")
        billing.dispatch_outbox()
    return created.json()["invoice_id"]


def test_service_cut_and_restore_follow_the_invoice(service_cluster):
    c = service_cluster
    apartment_id, uid, _ = confirmed_resident(c, "CUT-101", "cut.user")
    invoice = overdue_invoice(c, apartment_id)
    tickets = c.call("maintenance", "/api/maintenance/tickets").json()["items"]
    assert not [row for row in tickets if row["apartment_id"] == apartment_id]
    assert c.call("billing", "/api/billing/services", role="resident", user_id=uid).status_code == 403

    def service(action, name="electricity", **scope):
        return c.call("billing", f"/api/billing/services/monthly/{invoice}", "POST", json={"service": name, "action": action},
                      **(scope or {"role": "technician"}))

    def listed():
        return next(row for row in c.call("billing", "/api/billing/services", role="technician").json()["items"]
                    if row["invoice_id"] == invoice and row["invoice_type"] == "monthly")

    assert listed()["apartment_code"] == "CUT-101"
    assert [s["service"] for s in listed()["services"]] == ["electricity", "water"]
    assert service("cut", role="admin").status_code == 403
    assert service("cut", name="parking").status_code == 400
    assert service("restore").status_code == 409
    cut = service("cut")
    assert cut.status_code == 200, cut.text
    assert service("cut").status_code == 409
    assert {s["service"]: s["status"] for s in cut.json()["services"]} == {"electricity": "cut", "water": "active"}
    for scope in ({"role": "resident", "user_id": uid}, {"role": "admin"}, {"role": "technician"}):
        assert any(n["title"] == "Đã tạm ngưng dịch vụ điện" for n in notices(c, **scope)), scope
    assert c.call("billing", f"/api/billing/invoices/monthly/{invoice}/pay", "POST", json={"payment_method": "cash"}).status_code == 201
    with c.apps["billing"].app_context():
        c.modules["billing"].dispatch_outbox()
    assert listed()["status"] == "paid"
    assert any(n["title"] == "Cần cấp lại dịch vụ cho căn hộ" for n in notices(c, role="technician"))
    assert not any(n["title"] == "Cần cấp lại dịch vụ cho căn hộ" for n in notices(c, role="resident", user_id=uid))
    assert service("restore").status_code == 200
    assert any(n["title"] == "Đã cấp lại dịch vụ điện" for n in notices(c, role="resident", user_id=uid))
    detail = c.call("billing", f"/api/billing/invoices/monthly/{invoice}").json()
    assert {s["service"]: s["status"] for s in detail["services"]} == {"electricity": "restored", "water": "active"}
    assert not [row for row in c.call("billing", "/api/billing/services", role="technician").json()["items"]
                if row["invoice_id"] == invoice and row["invoice_type"] == "monthly"]


def register_vehicle(c, apartment_id, plate="29A1-22222", registered="2026-11-09", months=2):
    created = c.call("parking", "/api/parking/vehicles", "POST", json={
        "apartment_id": apartment_id, "vehicle_type": "motorbike", "plate_number": plate,
        "registered_date": registered, "registration_months": months})
    assert created.status_code == 201, created.text
    return created.json()


def test_vehicle_commitment_can_shrink_until_paid_and_can_be_renewed(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "VEH-101")
    # January to April; the first half-year allows up to June.
    vehicle = register_vehicle(c, apartment_id, registered="2027-01-10", months=4)
    route = f"/api/parking/vehicles/{vehicle['vehicle_id']}"
    shorter = c.call("parking", route, "PATCH", json={"registration_months": 3})
    assert shorter.status_code == 200, shorter.text
    assert c.call("parking", route, "PATCH", json={"registration_months": 1}).status_code == 400
    # March is the last month; renewing adds April and May, still inside the first half-year.
    renewed = c.call("parking", route + "/renew", "POST", json={"months": 2})
    assert renewed.status_code == 200 and renewed.json()["registration_months"] == 5
    assert c.call("parking", route + "/renew", "POST", role="resident", json={"months": 2}).status_code == 403
    created = c.call("billing", "/api/billing/invoices/semiannual", "POST", json={
        "apartment_id": apartment_id, "period": "2027-H1", "service_fee": 1000, "due_date": "2099-01-01"})
    assert created.status_code == 201, created.text
    assert created.json()["parking_fee"] > 0
    assert c.call("billing", f"/api/billing/invoices/semiannual/{created.json()['invoice_id']}/pay", "POST",
                  json={"payment_method": "cash"}).status_code == 201
    blocked = c.call("parking", route, "PATCH", json={"registration_months": 3})
    assert blocked.status_code == 409
    assert "không được rút ngắn" in blocked.json()["error"]


def test_lapsed_commitment_is_renewed_from_today(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "VEH-OLD")
    vehicle = register_vehicle(c, apartment_id, plate="29A1-33333", registered="2020-01-15")
    with c.apps["parking"].app_context():
        fewest, _ = c.modules["parking"].registration_window(c.modules["parking"].local_today())
    renewed = c.call("parking", f"/api/parking/vehicles/{vehicle['vehicle_id']}/renew", "POST",
                     json={"months": fewest}).json()
    assert renewed["minimum_end_date"] > "2026-01-01"


def test_extra_invoice_collects_a_vehicle_registered_after_the_half_year_invoice(service_cluster):
    c = service_cluster
    apartment_id, uid, _ = confirmed_resident(c, "SUP-101", "sup.user")
    base = c.call("billing", "/api/billing/invoices/semiannual", "POST", json={
        "apartment_id": apartment_id, "period": "2026-H2", "service_fee": 1000, "parking_fee": 0, "due_date": "2099-01-01"})
    assert base.status_code == 201, base.text
    with sqlite3.connect(c.db_path) as db:
        db.execute("UPDATE semiannual_invoices SET created_at='2026-07-01 00:00:00' WHERE invoice_id=?", (base.json()["invoice_id"],))
    vehicle = register_vehicle(c, apartment_id, plate="29A1-44444", registered="2026-11-09")
    route = f"/api/billing/vehicle-billing/{vehicle['vehicle_id']}"
    state = c.call("billing", route).json()
    # November and December at 100.000 each, plus the one-off card.
    assert state["available"] and state["amount"] == 300_000 and state["months"] == 2 and state["card_fee"] == 100_000
    assert c.call("billing", route, role="resident", user_id=uid).status_code == 403
    extra = c.call("billing", route + "/supplement", "POST", json={"due_date": "2099-02-01"})
    assert extra.status_code == 201, extra.text
    assert extra.json()["parking_fee"] == 300_000 and extra.json()["period"] == f"2026-H2-XE{vehicle['vehicle_id']}"
    again = c.call("billing", route + "/supplement", "POST", json={"due_date": "2099-02-01"})
    assert again.status_code == 409
    assert "đã có hóa đơn bổ sung" in again.json()["error"]
    assert c.call("billing", "/api/billing/reports?year=2026").json()["totals"]["semiannual_billed_amount"] >= 300_000
    listed = c.call("billing", "/api/billing/invoices/semiannual", role="resident", user_id=uid).json()["items"]
    assert any(row["invoice_id"] == extra.json()["invoice_id"] for row in listed)
    assert not c.call("billing", route).json()["fee_paid"]
    assert c.call("billing", f"/api/billing/invoices/semiannual/{extra.json()['invoice_id']}/pay", "POST",
                  json={"payment_method": "cash"}).status_code == 201
    assert c.call("billing", route).json()["fee_paid"]


def test_extra_invoice_needs_a_vehicle_the_issued_invoice_could_not_include(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "SUP-NO")
    vehicle = register_vehicle(c, apartment_id, plate="29A1-55555", registered="2026-11-09")
    route = f"/api/billing/vehicle-billing/{vehicle['vehicle_id']}"
    assert "chưa phát hành" in c.call("billing", route).json()["reason"]
    assert c.call("billing", "/api/billing/invoices/semiannual", "POST", json={
        "apartment_id": apartment_id, "period": "2026-H2", "service_fee": 1000, "due_date": "2099-01-01"}).status_code == 201
    state = c.call("billing", route).json()
    assert not state["available"] and "đã nằm trong hóa đơn" in state["reason"]
    assert c.call("billing", route + "/supplement", "POST", json={"due_date": "2099-02-01"}).status_code == 409


def test_older_vehicle_can_be_billed_when_the_invoice_charged_no_parking(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "SUP-OLD")
    assert c.call("billing", "/api/billing/invoices/semiannual", "POST", json={
        "apartment_id": apartment_id, "period": "2026-H2", "service_fee": 1000, "parking_fee": 0, "due_date": "2099-01-01"}).status_code == 201
    vehicle = register_vehicle(c, apartment_id, plate="29A1-66666", registered="2026-11-09")
    with sqlite3.connect(c.db_path) as db:
        db.execute("UPDATE vehicles SET created_at=NULL WHERE vehicle_id=?", (vehicle["vehicle_id"],))
    assert c.call("billing", f"/api/billing/vehicle-billing/{vehicle['vehicle_id']}").json()["available"]


def test_chat_suggestions_exist_in_the_database_and_are_answered(service_cluster):
    c = service_cluster
    items = c.call("chatbot", "/api/chatbot/suggestions", role="resident").json()["items"]
    assert len(items) == 3
    with sqlite3.connect(c.db_path) as db:
        places = {row[0] for row in db.execute("SELECT name FROM locations")}
        questions = {row[0] for row in db.execute("SELECT question FROM faq_knowledge_base")}
    assert items[0].removesuffix(" ở đâu?") in places
    assert set(items[1:]) <= questions
    for question in items:
        answer = c.call("chatbot", "/api/chatbot/ask", "POST", role="resident", json={"question": question}).json()
        assert answer["matched"], question
    target = items[1]
    with sqlite3.connect(c.db_path) as db:
        db.execute("DELETE FROM faq_knowledge_base WHERE question=?", (target,))
    assert target not in c.call("chatbot", "/api/chatbot/suggestions", role="resident").json()["items"]


def test_receipt_is_data_for_the_image_download(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "RECEIPT-101")
    created = c.call("billing", "/api/billing/invoices/monthly", "POST", json={
        "apartment_id": apartment_id, "period": "2097-01", "electricity_fee": 300, "water_fee": 200, "due_date": "2097-02-01"})
    payment = c.call("billing", f"/api/billing/invoices/monthly/{created.json()['invoice_id']}/pay", "POST",
                     json={"payment_method": "cash"}).json()
    receipt = c.call("billing", f"/api/billing/payments/monthly/{payment['payment_id']}/receipt").json()
    rows = dict(receipt["rows"])
    assert rows["Căn hộ"] == "RECEIPT-101" and rows["Hình thức"] == "Tiền mặt" and receipt["title"]


def test_technician_can_correct_a_guest_parking_amount(service_cluster):
    c = service_cluster
    created = c.call("parking", "/api/parking/guest-daily", "POST", role="technician",
                     json={"parking_date": "2020-02-02", "daily_revenue": 1000})
    assert created.status_code == 201, created.text
    updated = c.call("parking", f"/api/parking/guest-daily/{created.json()['record_id']}", "PUT", role="technician",
                     json={"parking_date": "2020-02-02", "daily_revenue": 2500})
    assert updated.status_code == 200 and updated.json()["daily_revenue"] == 2500

