"""Third round of the tester's bug sheet: usernames, management notices, leases, residents and parking periods."""

from datetime import date, timedelta
import sqlite3

from test_bug_sheet_fixes import confirm, confirmed_resident, notices
from test_resident_memberships import make_apartment, register_resident

MEMBER_PASSWORD = "Membership!2026"


def vehicle(c, apartment_id, plate, registered, months, kind="motorbike"):
    return c.call("parking", "/api/parking/vehicles", "POST", json={
        "apartment_id": apartment_id, "vehicle_type": kind, "plate_number": plate,
        "registered_date": registered, "registration_months": months})


def contract(c, apartment_id, resident_id, start, end, kind="rental"):
    response = c.call("resident", "/api/contracts", "POST", json={
        "apartment_id": apartment_id, "resident_id": resident_id, "contract_type": kind,
        "start_date": start, "end_date": end})
    assert response.status_code == 201, response.text
    return response.json()


def titles(c, **scope):
    return [n["title"] for n in notices(c, **scope)]


def test_registering_a_taken_username_names_the_problem(service_cluster):
    c = service_cluster
    make_apartment(c, "DUP-101")
    register_resident(c, "DUP-101", "taken.name")
    again = c.call("auth", "/api/auth/register", "POST", json={
        "username": "taken.name", "password": MEMBER_PASSWORD, "full_name": "Người Khác",
        "email": "nguoikhac@gmail.com", "phone": "0901234568", "apartment_code": "DUP-101"})
    assert again.status_code == 409
    assert again.json()["error"] == "Tên đăng nhập này đã được sử dụng. Vui lòng chọn tên đăng nhập khác."


def test_management_hears_about_new_requests_and_cancellations(service_cluster):
    c = service_cluster
    _, uid, _ = confirmed_resident(c, "REQ-101", "request.user")
    complaint = c.call("complaint", "/api/complaints", "POST", role="resident", user_id=uid,
                       json={"type": "complaint", "category": "Vệ sinh", "content": "Hành lang tầng 1 chưa được lau."})
    assert complaint.status_code == 201, complaint.text
    number = complaint.json()["complaint_id"]
    parking = c.call("complaint", "/api/complaints", "POST", role="resident", user_id=uid, json={
        "type": "registration", "category": "Đăng ký gửi xe",
        "content": "Loại xe: Xe máy\nBiển số: 29R1-10101\nCăn hộ: REQ-101\nNgày bắt đầu: 2027-01-05\n"
                   "Thời gian cam kết: 2 tháng"})
    assert parking.status_code == 201, parking.text
    assert c.call("complaint", f"/api/complaints/{number}/cancel", "POST", role="resident", user_id=uid).status_code == 200
    seen = titles(c)
    assert f"Yêu cầu mới #YC{number}: Góp ý / khiếu nại về Vệ sinh" in seen
    assert f"Yêu cầu mới #YC{parking.json()['complaint_id']}: Đơn đăng ký gửi xe" in seen
    assert f"Cư dân đã huỷ yêu cầu #YC{number}" in seen
    # These are for management only.
    assert not [t for t in titles(c, role="resident", user_id=uid) if t.startswith(("Yêu cầu mới", "Cư dân đã huỷ"))]


def test_approving_a_parking_application_points_at_parking_and_a_known_plate_renews(service_cluster):
    c = service_cluster
    _, uid, _ = confirmed_resident(c, "APR-101", "approve.user")

    def apply(months):
        response = c.call("complaint", "/api/complaints", "POST", role="resident", user_id=uid, json={
            "type": "registration", "category": "Đăng ký gửi xe",
            "content": f"Loại xe: Xe máy\nBiển số: 29P1-20202\nCăn hộ: APR-101\nNgày bắt đầu: 2027-01-10\n"
                       f"Thời gian cam kết: {months} tháng"})
        assert response.status_code == 201, response.text
        approved = c.call("complaint", f"/api/complaints/{response.json()['complaint_id']}", "PATCH",
                          json={"status": "resolved", "response": "Đồng ý."})
        assert approved.status_code == 200, approved.text
        return approved.json()

    first = apply(3)
    assert first["vehicle"]["minimum_end_date"] == "2027-04-09"
    assert first["response"].endswith("Xem tại Quản lý gửi xe.") and "›" not in first["response"]
    # The same plate again extends that registration from 10 April instead of failing as a duplicate.
    renewed = apply(2)
    assert "đã được gia hạn" in renewed["response"]
    assert renewed["vehicle"]["vehicle_id"] == first["vehicle"]["vehicle_id"]
    assert renewed["vehicle"]["minimum_end_date"] == "2027-06-09"
    # A renewal may add a single month.
    assert apply(1)["vehicle"]["minimum_end_date"] == "2027-07-09"


def test_an_apartment_lists_every_resident_and_locked_accounts_move_out(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "ALL-101")
    first_uid, first = register_resident(c, "ALL-101", "first.member")
    confirm(c, first, apartment_id)
    second_uid, second = register_resident(c, "ALL-101", "second.member")
    confirm(c, second, apartment_id)
    owner_uid, owner = register_resident(c, "ALL-101", "owner.member")
    confirm(c, owner, apartment_id)

    def apartment():
        return c.call("resident", f"/api/apartments/{apartment_id}").json()

    listed = apartment()
    assert [r["resident_id"] for r in listed["current_residents"]] == [
        first["resident_id"], second["resident_id"], owner["resident_id"]]
    assert listed["status"] == "occupied"
    # No lease has ended yet, so there is nothing to lock.
    early = c.call("resident", f"/api/residents/{first['resident_id']}/lock-apartment", "POST")
    assert early.status_code == 409
    today = date.today()
    contract(c, apartment_id, first["resident_id"], "2026-01-01", (today - timedelta(days=1)).isoformat())
    contract(c, apartment_id, owner["resident_id"], "2020-01-01", None, kind="ownership")
    assert c.call("resident", f"/api/residents/{first['resident_id']}").json()["lease_ended"] is True
    locked = c.call("resident", f"/api/residents/{first['resident_id']}/lock-apartment", "POST")
    assert locked.status_code == 200, locked.text
    # The owner still holds a running contract and keeps the account.
    assert sorted(locked.json()["locked_user_ids"]) == sorted([first_uid, second_uid])
    assert [r["resident_id"] for r in apartment()["current_residents"]] == [owner["resident_id"]]
    login = c.call("auth", "/api/auth/login", "POST", json={"username": "second.member", "password": MEMBER_PASSWORD})
    assert login.status_code == 403 and login.json()["code"] == "ACCOUNT_LOCKED"
    assert login.json()["reason"] == "Hợp đồng thuê nhà đã quá hạn, tài khoản đã bị khóa."
    assert c.call("resident", "/api/residents/me", role="resident", user_id=second_uid).status_code == 401
    reopened = c.call("resident", f"/api/residents/{second['resident_id']}/unlock", "POST")
    assert reopened.status_code == 200 and reopened.json()["unlocked_user_ids"] == [second_uid]
    # The apartment link was kept, so the resident is back at once.
    assert [r["resident_id"] for r in apartment()["current_residents"]] == [owner["resident_id"], second["resident_id"]]
    login = c.call("auth", "/api/auth/login", "POST", json={"username": "second.member", "password": MEMBER_PASSWORD})
    assert login.status_code == 200
    assert c.call("resident", f"/api/residents/{first['resident_id']}/unlock", "POST", role="resident",
                  user_id=owner_uid).status_code == 403
    actions = [row[0] for row in sqlite3.connect(c.db_path).execute(
        "SELECT action FROM audit_log WHERE action LIKE 'account_%' ORDER BY audit_id")]
    assert actions == ["account_locked", "account_locked", "account_unlocked"]


def lease_titles(c, code, **scope):
    return [t for t in titles(c, **scope) if code in t and "hợp đồng thuê" in t.lower()]


def test_lease_notices_reach_management_and_each_resident_separately(service_cluster):
    c = service_cluster
    apartment_id, uid, profile = confirmed_resident(c, "LEASE-101", "lease.user")
    partner_uid, partner = register_resident(c, "LEASE-101", "lease.partner")
    confirm(c, partner, apartment_id)
    today = date.today()
    end = today + timedelta(days=40)
    lease = contract(c, apartment_id, profile["resident_id"], "2026-01-01", end.isoformat())
    module, app = c.modules["resident"], c.apps["resident"]

    def run(as_of):
        with app.app_context():
            module.lease_reminders(as_of)

    run(today)  # Forty days before the end: too early.
    assert not lease_titles(c, "LEASE-101", role="resident", user_id=uid) and not lease_titles(c, "LEASE-101")
    run(end - timedelta(days=30))
    run(end - timedelta(days=29))  # Hourly runs never repeat a notice.
    # A month ahead: every resident of the apartment and management, each with their own notice.
    for resident in (uid, partner_uid):
        assert lease_titles(c, "LEASE-101", role="resident", user_id=resident) == [
            "Hợp đồng thuê căn hộ LEASE-101 của bạn sắp hết hạn"]
    assert lease_titles(c, "LEASE-101") == [f"Căn hộ LEASE-101: hợp đồng thuê sắp hết hạn ({end:%d/%m/%Y})"]
    run(end)
    assert lease_titles(c, "LEASE-101") == [
        "Căn hộ LEASE-101: hợp đồng thuê đã hết hạn", f"Căn hộ LEASE-101: hợp đồng thuê sắp hết hạn ({end:%d/%m/%Y})"]
    for resident in (uid, partner_uid):
        assert lease_titles(c, "LEASE-101", role="resident", user_id=resident) == [
            "Hợp đồng thuê căn hộ LEASE-101 của bạn đã hết hạn", "Hợp đồng thuê căn hộ LEASE-101 của bạn sắp hết hạn"]
    management = next(n for n in notices(c) if n["title"] == "Căn hộ LEASE-101: hợp đồng thuê đã hết hạn")
    assert f"#HD{lease['contract_id']}" in management["content"] and "Khóa tài khoản căn hộ" in management["content"]
    mine = next(n for n in notices(c, role="resident", user_id=uid) if n["title"].endswith("của bạn đã hết hạn"))
    assert "liên hệ Ban quản lý để gia hạn" in mine["content"] and "Khóa tài khoản căn hộ" not in mine["content"]
    # A renewal for the same tenant stops the reminders for the old lease (entered first here,
    # because saving a lease that ends within a month sends its reminder at once).
    other_id, other_uid, other = confirmed_resident(c, "LEASE-102", "renewed.user")
    old_end = today + timedelta(days=10)
    contract(c, other_id, other["resident_id"], (old_end + timedelta(days=1)).isoformat(), "2099-12-31")
    contract(c, other_id, other["resident_id"], "2026-01-01", old_end.isoformat())
    run(today)
    run(old_end)
    assert not lease_titles(c, "LEASE-102", role="resident", user_id=other_uid) and not lease_titles(c, "LEASE-102")
    assert lease["status"] == "active"


def test_management_gets_the_end_date_notice_even_after_an_earlier_wording_was_sent(service_cluster):
    c = service_cluster
    apartment_id, _, profile = confirmed_resident(c, "OLD-101", "old.wording")
    lease = contract(c, apartment_id, profile["resident_id"], "2026-01-01", "2099-12-31")
    today = date.today()
    with c.apps["resident"].app_context():
        # What an earlier version sent under the id it used for management's notice.
        c.modules["resident"].notify(f"lease-ended:{lease['contract_id']}:{today.isoformat()}", target_role="admin",
                                     title="Căn hộ OLD-101 hết hạn hợp đồng thuê", content="Bản cũ.")
    saved = c.call("resident", f"/api/contracts/{lease['contract_id']}", "PATCH", json={"end_date": today.isoformat()})
    assert saved.status_code == 200, saved.text
    assert "Căn hộ OLD-101: hợp đồng thuê đã hết hạn" in titles(c)


def test_saving_a_lease_end_date_sends_its_notices_at_once(service_cluster):
    c = service_cluster
    apartment_id, uid, profile = confirmed_resident(c, "SOON-101", "soon.user")
    lease = contract(c, apartment_id, profile["resident_id"], "2026-01-01", "2099-12-31")
    today = date.today()

    def end_on(day):
        saved = c.call("resident", f"/api/contracts/{lease['contract_id']}", "PATCH", json={"end_date": day.isoformat()})
        assert saved.status_code == 200, saved.text

    assert not lease_titles(c, "SOON-101", role="resident", user_id=uid)
    soon = today + timedelta(days=12)
    end_on(soon)  # No waiting for the hourly run.
    assert lease_titles(c, "SOON-101", role="resident", user_id=uid) == ["Hợp đồng thuê căn hộ SOON-101 của bạn sắp hết hạn"]
    assert lease_titles(c, "SOON-101") == [f"Căn hộ SOON-101: hợp đồng thuê sắp hết hạn ({soon:%d/%m/%Y})"]
    end_on(today)
    end_on(today)  # Saving again does not repeat the notices.
    assert lease_titles(c, "SOON-101").count("Căn hộ SOON-101: hợp đồng thuê đã hết hạn") == 1
    assert lease_titles(c, "SOON-101", role="resident", user_id=uid).count(
        "Hợp đồng thuê căn hộ SOON-101 của bạn đã hết hạn") == 1
    locked = c.call("resident", f"/api/residents/{profile['resident_id']}/lock-apartment", "POST")
    assert locked.status_code == 200 and locked.json()["locked_user_ids"] == [uid]


def test_ending_a_lease_by_hand_notifies_everyone_and_locking_empties_the_apartment(service_cluster):
    c = service_cluster
    apartment_id, uid, profile = confirmed_resident(c, "HAND-101", "hand.user")
    lease = contract(c, apartment_id, profile["resident_id"], "2026-01-01", "2099-07-20")
    expired = c.call("resident", f"/api/contracts/{lease['contract_id']}", "PATCH", json={"status": "expired"})
    assert expired.status_code == 200, expired.text
    assert lease_titles(c, "HAND-101") == ["Căn hộ HAND-101: hợp đồng thuê đã hết hạn"]
    assert lease_titles(c, "HAND-101", role="resident", user_id=uid) == ["Hợp đồng thuê căn hộ HAND-101 của bạn đã hết hạn"]
    # Until management locks the account, the resident still lives there and can pay what is owed.
    assert c.call("resident", f"/api/apartments/{apartment_id}").json()["status"] == "occupied"
    locked = c.call("resident", f"/api/residents/{profile['resident_id']}/lock-apartment", "POST")
    assert locked.status_code == 200 and locked.json()["locked_user_ids"] == [uid]
    emptied = c.call("resident", f"/api/apartments/{apartment_id}").json()
    assert emptied["status"] == "vacant" and emptied["current_residents"] == [] and emptied["current_resident"] is None
    with sqlite3.connect(c.db_path) as db:
        assert db.execute("SELECT status FROM apartments WHERE apartment_id=?", (apartment_id,)).fetchone()[0] == "vacant"


def test_residents_join_only_by_registering(service_cluster):
    c = service_cluster
    assert c.call("resident", "/api/residents", "POST", json={
        "full_name": "Người Thêm Tay", "relation_type": "tenant"}).status_code == 405
    apartment_id = make_apartment(c, "NAME-101")
    before = len(c.call("resident", "/api/residents").json()["items"])
    unknown = c.call("resident", "/api/contracts", "POST", json={
        "apartment_id": apartment_id, "resident_name": "Người Chưa Đăng Ký", "contract_type": "rental",
        "start_date": "2026-01-01", "end_date": "2026-12-31"})
    assert unknown.status_code == 404 and "tự đăng ký tài khoản" in unknown.json()["error"]
    assert len(c.call("resident", "/api/residents").json()["items"]) == before


def test_parking_registrations_stay_inside_their_fee_period(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "WIN-101")
    # Starting in January: at most six months, all beginning by June. Calendar months from the
    # start date, so 10 January for six months runs to the end of 9 July.
    assert vehicle(c, apartment_id, "29W1-00001", "2027-01-10", 7).status_code == 400
    january = vehicle(c, apartment_id, "29W1-00002", "2027-01-10", 6)
    assert january.status_code == 201 and january.json()["minimum_end_date"] == "2027-07-09"
    # May leaves two months in the period; June is the last month, so it may run to December.
    assert vehicle(c, apartment_id, "29W1-00003", "2027-05-05", 3).status_code == 400
    june = vehicle(c, apartment_id, "29W1-00004", "2027-06-05", 7)
    assert june.status_code == 201 and june.json()["minimum_end_date"] == "2028-01-04"
    # At least two months, except December: one month, the last that may begin this year.
    assert vehicle(c, apartment_id, "29W1-00005", "2027-03-01", 1).status_code == 400
    december = vehicle(c, apartment_id, "29W1-00006", "2027-12-10", 1)
    assert december.status_code == 201 and december.json()["minimum_end_date"] == "2028-01-09"
    assert vehicle(c, apartment_id, "29W1-00007", "2027-12-01", 2).status_code == 400
    # Each month is billed in the period it begins in. H2 bills June's six later months and
    # December's month, but nothing for January's, whose first days of July were paid in H1.
    summary = c.call("parking", f"/api/parking/summary?period=2027-H2&apartment_id={apartment_id}").json()["items"][0]
    billed = {line["vehicle_id"]: line["months"] for line in summary["vehicles"]}
    assert january.json()["vehicle_id"] not in billed
    assert billed[june.json()["vehicle_id"]] == 6 and billed[december.json()["vehicle_id"]] == 1
    # The days running into January 2028 were paid in H2: the next period bills nothing.
    assert c.call("parking", f"/api/parking/summary?period=2028-H1&apartment_id={apartment_id}").json()["items"] == []
    # Renewing before it runs out follows straight on, within the next period's limit.
    route = f"/api/parking/vehicles/{january.json()['vehicle_id']}/renew"
    assert c.call("parking", route, "POST", json={"months": 7}).status_code == 400
    renewed = c.call("parking", route, "POST", json={"months": 6})
    assert renewed.status_code == 200 and renewed.json()["minimum_end_date"] == "2028-01-09"
    assert renewed.json()["vehicle_id"] == january.json()["vehicle_id"]


def test_a_lapsed_registration_is_not_billed_until_renewed_and_renewal_starts_today(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "LAPSE-101")
    old = vehicle(c, apartment_id, "29L1-30303", "2026-01-05", 2).json()
    assert old["minimum_end_date"] == "2026-03-04" and old["registration_expired"] is True
    h1 = c.call("parking", f"/api/parking/summary?period=2026-H1&apartment_id={apartment_id}").json()["items"][0]
    assert [line["months"] for line in h1["vehicles"]] == [2]
    assert c.call("parking", f"/api/parking/summary?period=2026-H2&apartment_id={apartment_id}").json()["items"] == []
    with c.apps["parking"].app_context():
        today = c.modules["parking"].local_today()
        fewest, _ = c.modules["parking"].registration_window(today)
    renewed = c.call("parking", f"/api/parking/vehicles/{old['vehicle_id']}/renew", "POST", json={"months": fewest})
    assert renewed.status_code == 200, renewed.text
    fresh = renewed.json()
    # The months in between are not owed, and the card already exists.
    assert fresh["vehicle_id"] != old["vehicle_id"] and fresh["registered_date"] == today.isoformat()
    assert fresh["card_fee"] == 0 and fresh["registration_expired"] is False
    previous = c.call("parking", f"/api/parking/vehicles/{old['vehicle_id']}").json()
    assert previous["status"] == "cancelled" and previous["cancelled_date"] == "2026-03-05"


def test_a_registered_vehicle_may_be_renewed_for_a_single_month(service_cluster):
    c = service_cluster
    apartment_id = make_apartment(c, "ONE-101")
    # A new registration still needs two months.
    assert vehicle(c, apartment_id, "29O1-10001", "2027-01-10", 1).status_code == 400
    running = vehicle(c, apartment_id, "29O1-10001", "2027-01-10", 2).json()
    renewed = c.call("parking", f"/api/parking/vehicles/{running['vehicle_id']}/renew", "POST", json={"months": 1})
    assert renewed.status_code == 200, renewed.text
    assert renewed.json()["registration_months"] == 3 and renewed.json()["minimum_end_date"] == "2027-04-09"
    # One that already ran out starts again today, also for a single month.
    lapsed = vehicle(c, apartment_id, "29O1-10002", "2026-01-05", 2).json()
    again = c.call("parking", f"/api/parking/vehicles/{lapsed['vehicle_id']}/renew", "POST", json={"months": 1})
    assert again.status_code == 200, again.text
    assert again.json()["registration_months"] == 1 and again.json()["registered_date"] == date.today().isoformat()
    assert c.call("parking", f"/api/parking/vehicles/{running['vehicle_id']}/renew", "POST",
                  json={"months": 0}).status_code == 400
