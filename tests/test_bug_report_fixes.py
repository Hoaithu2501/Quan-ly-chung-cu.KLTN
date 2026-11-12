"""Regression tests for the resident web bug report of 2026-11-08."""
import sqlite3

from test_resident_memberships import make_apartment, register_resident


def test_new_account_only_sees_notifications_published_after_registration(service_cluster):
    c = service_cluster
    old = c.call("notification", "/api/notifications", "POST",
                 json={"type": "general", "title": "Thông báo cũ", "content": "Trước khi đăng ký"})
    assert old.status_code == 201, old.text
    with sqlite3.connect(c.db_path) as db:
        db.execute("UPDATE notifications SET created_at='2000-01-01 00:00:00' WHERE notification_id=?",
                   (old.json()["notification_id"],))
    make_apartment(c, "NOTICE-101")
    uid, _ = register_resident(c, "NOTICE-101", "notice.user")
    new = c.call("notification", "/api/notifications", "POST",
                 json={"type": "general", "title": "Thông báo mới", "content": "Sau khi đăng ký"})
    assert new.status_code == 201, new.text
    ids = {n["notification_id"] for n in
           c.call("notification", "/api/notifications", role="resident", user_id=uid).json()["items"]}
    assert new.json()["notification_id"] in ids
    assert old.json()["notification_id"] not in ids


def test_registration_notifies_management_to_confirm_the_apartment(service_cluster):
    c = service_cluster
    make_apartment(c, "NOTICE-ADMIN")
    register_resident(c, "NOTICE-ADMIN", "notice.admin")
    items = c.call("notification", "/api/notifications").json()["items"]
    notice = next(n for n in items if "NOTICE-ADMIN" in n["title"])
    assert notice["type"] == "private" and notice["target_role"] == "admin"
    assert "Xác nhận căn hộ" in notice["content"]


def test_new_password_must_differ_from_current_password(service_cluster):
    c = service_cluster
    make_apartment(c, "PASS-101")
    uid, _ = register_resident(c, "PASS-101", "password.same")
    response = c.call("auth", "/api/auth/me/password", "POST", role="resident", user_id=uid, json={
        "current_password": "Membership!2026", "new_password": "Membership!2026",
        "confirm_password": "Membership!2026"})
    assert response.status_code == 400
    assert response.json()["error"] == "Mật khẩu mới không được trùng với mật khẩu hiện tại."


def test_unconfirmed_resident_cannot_create_maintenance_ticket(service_cluster):
    c = service_cluster
    aid = make_apartment(c, "FIX-101")
    uid, profile = register_resident(c, "FIX-101", "fix.user")
    scope = {"role": "resident", "user_id": uid}
    blocked = c.call("maintenance", "/api/maintenance/tickets", "POST", json={
        "apartment_code": "FIX-101", "type": "repair", "description": "Rò nước"}, **scope)
    assert blocked.status_code == 403
    assert "chưa được Ban quản lý xác nhận" in blocked.json()["error"]
    assert c.call("resident", f"/api/residents/{profile['resident_id']}/apartments", "POST",
                  json={"apartment_id": aid}).status_code == 201
    created = c.call("maintenance", "/api/maintenance/tickets", "POST", json={
        "apartment_id": aid, "type": "repair", "description": "Rò nước", "priority": "high"}, **scope)
    assert created.status_code == 201, created.text
    assert created.json()["priority"] == "medium"  # residents do not set priority
    listed = c.call("maintenance", "/api/maintenance/tickets", **scope).json()["items"]
    assert [t["ticket_id"] for t in listed] == [created.json()["ticket_id"]]


def test_approving_parking_application_registers_vehicle_and_notifies_resident(service_cluster):
    c = service_cluster
    aid = make_apartment(c, "PARK-APPROVE")
    uid, profile = register_resident(c, "PARK-APPROVE", "park.approve")
    assert c.call("resident", f"/api/residents/{profile['resident_id']}/apartments", "POST",
                  json={"apartment_id": aid}).status_code == 201
    content = ("Loại xe: Xe đạp\nBiển số: Cấp mã theo căn hộ khi duyệt\nCăn hộ: PARK-APPROVE\n"
               "Ngày bắt đầu: 2026-11-10\nThời gian cam kết: 3 tháng (tối thiểu 2 tháng)\nGhi chú: Không có")
    request = c.call("complaint", "/api/complaints", "POST", role="resident", user_id=uid, json={
        "type": "registration", "category": "Đăng ký gửi xe", "content": content})
    assert request.status_code == 201, request.text
    approved = c.call("complaint", f"/api/complaints/{request.json()['complaint_id']}", "PATCH",
                      json={"status": "resolved", "response": "Đã duyệt đơn."})
    assert approved.status_code == 200, approved.text
    vehicle = approved.json()["vehicle"]
    assert vehicle["plate_number"] == "PARK-APPROVE-XD-1"
    assert vehicle["minimum_end_date"] == "2027-02-10"
    vehicles = c.call("parking", "/api/parking/vehicles", role="resident", user_id=uid).json()["items"]
    assert [v["vehicle_id"] for v in vehicles] == [vehicle["vehicle_id"]]
    notices = c.call("notification", "/api/notifications", role="resident", user_id=uid).json()["items"]
    assert any("PARK-APPROVE-XD-1" in (n["content"] or "") for n in notices)
    # The application is closed; editing the reply never registers a second vehicle.
    again = c.call("complaint", f"/api/complaints/{request.json()['complaint_id']}", "PATCH",
                   json={"status": "resolved", "response": "Đã duyệt đơn (cập nhật)."})
    assert again.status_code == 200 and "vehicle" not in again.json()
    second = c.call("parking", "/api/parking/vehicles", "POST", json={
        "apartment_id": aid, "vehicle_type": "bicycle", "registered_date": "2026-11-10"})
    assert second.json()["plate_number"] == "PARK-APPROVE-XD-2"


def test_parking_approval_stays_within_the_applicants_own_apartment(service_cluster):
    c = service_cluster
    own = make_apartment(c, "PARK-OWN")
    make_apartment(c, "PARK-OTHER")
    uid, profile = register_resident(c, "PARK-OWN", "park.owner")
    assert c.call("resident", f"/api/residents/{profile['resident_id']}/apartments", "POST",
                  json={"apartment_id": own}).status_code == 201

    def approve(content):
        created = c.call("complaint", "/api/complaints", "POST", role="resident", user_id=uid, json={
            "type": "registration", "category": "Đăng ký gửi xe", "content": content})
        assert created.status_code == 201, created.text
        return c.call("complaint", f"/api/complaints/{created.json()['complaint_id']}", "PATCH",
                      json={"status": "resolved", "response": "Đã duyệt."})

    form = ("Loại xe: Xe đạp\nBiển số: Cấp mã theo căn hộ khi duyệt\nCăn hộ: {apartment}\n"
            "Ngày bắt đầu: 2026-11-10\nThời gian cam kết: 3 tháng\nGhi chú: {note}")
    wrong = form.format(apartment="PARK-OTHER", note="Không có")
    assert c.call("complaint", "/api/complaints", "POST", role="resident", user_id=uid, json={
        "type": "registration", "category": "Đăng ký gửi xe", "content": wrong}).status_code == 403
    # An application already on file from before that check is still refused at approval.
    with sqlite3.connect(c.db_path) as db:
        filed = db.execute("INSERT INTO complaints(resident_id,type,category,content) VALUES (?,?,?,?)",
                           (profile["resident_id"], "registration", "Đăng ký gửi xe", wrong)).lastrowid
    refused = c.call("complaint", f"/api/complaints/{filed}", "PATCH", json={"status": "resolved", "response": "Đã duyệt."})
    assert refused.status_code == 409 and "PARK-OTHER" in refused.json()["error"]
    # A note typed after the real fields cannot move the charge to another household.
    approved = approve(form.format(apartment="PARK-OWN", note="Xe đỏ\nCăn hộ: PARK-OTHER\nNgày bắt đầu: 2099-01-01"))
    assert approved.status_code == 200, approved.text
    assert approved.json()["vehicle"]["apartment_id"] == own
    assert approved.json()["vehicle"]["registered_date"] == "2026-11-10"


def test_procedure_registration_keeps_attachments_and_sender_for_management(service_cluster):
    c = service_cluster
    make_apartment(c, "PROC-101")
    uid, profile = register_resident(c, "PROC-101", "procedure.user")
    attachments = [{"name": "cccd.png", "data": "data:image/png;base64,iVBORw0KGgo="},
                   {"name": "Hồ sơ", "url": "https://example.com/ho-so"}]
    response = c.call("complaint", "/api/complaints", "POST", role="resident", user_id=uid, json={
        "type": "registration", "category": "Đăng ký tạm trú", "content": "Đăng ký tạm trú cho người thân",
        "attachments": attachments})
    assert response.status_code == 201, response.text
    stored = [{**attachments[0], "type": "image/png"}, attachments[1]]
    assert response.json()["attachments"] == stored
    for bad in ([{"name": "x.html", "data": "data:text/html;base64,PGI+"}],
                [{"name": "x", "url": "javascript:alert(1)"}]):
        assert c.call("complaint", "/api/complaints", "POST", role="resident", user_id=uid, json={
            "type": "registration", "category": "X", "content": "Y", "attachments": bad}).status_code == 400
    row = next(r for r in c.call("complaint", "/api/complaints").json()["items"]
               if r["complaint_id"] == response.json()["complaint_id"])
    assert row["resident_name"] == profile["full_name"]
    assert row["attachments"] == stored and row["created_at"]


def test_chatbot_answers_follow_policies_as_management_changes_them(service_cluster):
    c = service_cluster
    question = "Sân pickleball trên sân thượng mở cửa lúc mấy giờ?"

    def ask():
        response = c.call("chatbot", "/api/chatbot/ask", "POST", role="resident", user_id=3, json={"question": question})
        assert response.status_code == 200, response.text
        return response.json()

    assert not ask()["matched"]
    created = c.call("chatbot", "/api/chatbot/faqs", "POST", json={
        "category": "Tiện ích", "question": question, "answer": "Mở từ 6 giờ đến 21 giờ."})
    assert created.status_code == 201, created.text
    faq_id = created.json()["faq_id"]
    answer = ask()
    assert answer["matched"] and answer["source_id"] == faq_id and "6 giờ" in answer["answer"]
    updated = c.call("chatbot", f"/api/chatbot/faqs/{faq_id}", "PATCH", json={"answer": "Tạm đóng cửa đến tháng 12."})
    assert updated.status_code == 200, updated.text
    answer = ask()
    assert "Tạm đóng cửa" in answer["answer"] and "6 giờ" not in answer["answer"]
    assert c.call("chatbot", f"/api/chatbot/faqs/{faq_id}", "DELETE").status_code == 200
    answer = ask()
    assert not answer["matched"] and "Tạm đóng cửa" not in answer["answer"]


def test_apartment_shows_owner_alongside_the_current_tenant(service_cluster):
    c = service_cluster
    aid = make_apartment(c, "OWNER-101")
    owner_uid, owner = register_resident(c, "OWNER-101", "owner.one")
    tenant_uid, tenant = register_resident(c, "OWNER-101", "tenant.one")
    _, other = register_resident(c, "OWNER-101", "tenant.two")

    def contract(profile, kind, **extra):
        return c.call("resident", "/api/contracts", "POST", json={
            "apartment_id": aid, "resident_id": profile["resident_id"], "contract_type": kind,
            "start_date": "2026-01-01", **extra})

    assert contract(owner, "ownership").status_code == 201
    assert contract(tenant, "rental", end_date="2099-12-31").status_code == 201
    assert contract(other, "rental", end_date="2099-12-31").status_code == 409
    row = c.call("resident", f"/api/apartments/{aid}").json()
    assert row["owner_name"] == owner["full_name"] and row["owner_phone"] == owner["phone"]
    assert row["current_resident"] == tenant["full_name"] and row["contract_type"] == "rental"
    assert row["remaining_days"] > 0 and row["status"] == "occupied"
    seen_by_tenant = c.call("resident", f"/api/apartments/{aid}", role="resident", user_id=tenant_uid).json()
    assert seen_by_tenant["owner_name"] == owner["full_name"] and "owner_phone" not in seen_by_tenant
    assert "owner_name" not in c.call("resident", f"/api/apartments/{aid}", role="technician").json()


def test_reports_count_complaints_and_split_revenue_by_invoice_kind(service_cluster):
    c = service_cluster
    with sqlite3.connect(c.db_path) as db:
        db.execute("UPDATE complaints SET created_at='2001-01-01 00:00:00'")
    for kind, category in (("complaint", "Tiếng ồn"), ("complaint", "Vệ sinh"), ("registration", "Tạm trú")):
        assert c.call("complaint", "/api/complaints", "POST", role="resident", user_id=3, json={
            "type": kind, "category": category, "content": "Nội dung"}).status_code == 201
    with sqlite3.connect(c.db_path) as db:
        # 18:30 UTC on 31 March is already 1 April in Vietnam, so it belongs to the second quarter.
        db.execute("UPDATE complaints SET created_at='2097-03-31 18:30:00' WHERE created_at>'2001-01-02'")
    assert c.call("complaint", "/api/complaints/summary", role="resident", user_id=3).status_code == 403
    quarters = c.call("complaint", "/api/complaints/summary?year=2097&group=quarter").json()
    assert {r["period"]: r["complaint_count"] for r in quarters["items"]} == {
        "2097-Q1": 0, "2097-Q2": 2, "2097-Q3": 0, "2097-Q4": 0}
    assert quarters["totals"]["complaint_count"] == 2 and quarters["totals"]["registration_count"] == 1
    assert quarters["totals"]["pending_count"] == 3
    months = c.call("complaint", "/api/complaints/summary?year=2097").json()
    assert len(months["items"]) == 12 and months["items"][3]["registration_count"] == 1
    assert c.call("billing", "/api/billing/invoices/monthly", "POST", json={
        "apartment_id": 1, "period": "2098-03", "electricity_fee": 100, "water_fee": 50,
        "due_date": "2098-04-15"}).status_code == 201
    assert c.call("billing", "/api/billing/invoices/semiannual", "POST", json={
        "apartment_id": 1, "period": "2098-H1", "service_fee": 200, "parking_fee": 0,
        "due_date": "2098-07-01"}).status_code == 201
    totals = c.call("billing", "/api/billing/reports?year=2098").json()["totals"]
    assert totals["monthly_billed_amount"] == 150 and totals["semiannual_billed_amount"] == 200
    assert totals["billed_amount"] == 350 and totals["monthly_collected_amount"] == 0
