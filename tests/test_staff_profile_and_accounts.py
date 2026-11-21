"""Personal details for staff, shared contact details, and one apartment per account."""
import sqlite3

import requests

from test_resident_memberships import make_apartment, register_resident


def test_admin_edits_own_profile_and_it_appears_on_the_session(service_cluster):
    c = service_cluster
    update = {"full_name": "Trần Quản Lý", "id_card": "079000000001", "phone": "0901000000", "email": "quanly@gmail.com"}
    saved = c.call("auth", "/api/auth/me", "PATCH", role="admin", json=update)
    assert saved.status_code == 200, saved.text
    assert saved.json()["profile"]["full_name"] == update["full_name"]
    assert saved.json()["user"]["full_name"] == update["full_name"]
    me = c.call("auth", "/api/auth/me", role="admin").json()["user"]
    assert (me["full_name"], me["id_card"], me["phone"], me["email"]) == (
        update["full_name"], update["id_card"], update["phone"], update["email"])
    assert "id_card" not in c.call("auth", "/api/auth/users").json()["items"][0]


def test_an_older_email_does_not_block_editing_other_details(service_cluster):
    c = service_cluster
    current = c.call("auth", "/api/auth/me", role="admin").json()["user"]["email"]
    assert not current.endswith("@gmail.com")
    saved = c.call("auth", "/api/auth/me", "PATCH", role="admin", json={"email": current, "full_name": "Tên Mới Của Admin"})
    assert saved.status_code == 200, saved.text
    assert saved.json()["user"]["email"] == current


def test_staff_profile_validates_input_and_keeps_role_fixed(service_cluster):
    c = service_cluster
    for bad in ({"full_name": "a"}, {"email": "x@example.com"}, {"phone": ""}, {"id_card": "9" * 31}, {"role": "resident"}):
        assert c.call("auth", "/api/auth/me", "PATCH", role="admin", json=bad).status_code == 400, bad
    assert c.call("auth", "/api/auth/me", role="admin").json()["user"]["role"] == "admin"


def test_technician_rename_reaches_the_assignment_list(service_cluster):
    c = service_cluster
    response = c.call("auth", "/api/auth/me", "PATCH", role="technician", json={"full_name": "Kỹ Thuật Mới"})
    assert response.status_code == 200, response.text
    with sqlite3.connect(c.db_path) as db:
        canonical = db.execute("SELECT full_name FROM technicians WHERE user_id=11 ORDER BY technician_id LIMIT 1").fetchone()[0]
    assert canonical == "Kỹ Thuật Mới"
    assert c.call("maintenance", "/api/maintenance/technicians/me", "PATCH", role="resident",
                  json={"full_name": "Không được"}).status_code == 403


def test_staff_can_change_their_own_password(service_cluster):
    c = service_cluster
    old = c.headers("admin")
    changed = requests.post(c.urls["auth"] + "/api/auth/me/password", headers=old, timeout=10, json={
        "current_password": c.password, "new_password": "AdminNew123", "confirm_password": "AdminNew123"})
    assert changed.status_code == 200, changed.text
    assert requests.get(c.urls["auth"] + "/api/auth/me", headers=old, timeout=10).status_code == 401
    fresh = {"Authorization": "Bearer " + changed.json()["token"]}
    assert requests.get(c.urls["auth"] + "/api/auth/me", headers=fresh, timeout=10).status_code == 200


def test_separate_accounts_may_share_email_and_phone(service_cluster):
    c = service_cluster
    make_apartment(c, "SHARE-1")
    make_apartment(c, "SHARE-2")
    payload = {"password": "Password123", "full_name": "Chủ Hai Căn", "email": "chung@gmail.com", "phone": "0900000099"}
    for username, code in (("share.one", "SHARE-1"), ("share.two", "SHARE-2")):
        response = requests.post(c.urls["auth"] + "/api/auth/register", timeout=10,
                                 json={**payload, "username": username, "apartment_code": code})
        assert response.status_code == 201, response.text
    assert requests.post(c.urls["auth"] + "/api/auth/register", timeout=10, json={
        **payload, "username": "share.one", "apartment_code": "SHARE-1"}).status_code == 409


def test_account_keeps_one_apartment_until_the_link_ends(service_cluster):
    c = service_cluster
    first, second = make_apartment(c, "ONE-1"), make_apartment(c, "ONE-2")
    _, profile = register_resident(c, "ONE-1", "one.home")
    path = f"/api/residents/{profile['resident_id']}/apartments"
    assert c.call("resident", path, "POST", json={"apartment_id": first}).status_code == 201
    blocked = c.call("resident", path, "POST", json={"apartment_id": second})
    assert blocked.status_code == 409 and "tài khoản riêng" in blocked.json()["error"]
    contract = {"apartment_id": second, "resident_id": profile["resident_id"], "contract_type": "rental",
                "start_date": "2030-01-01", "end_date": "2030-12-31"}
    assert c.call("resident", "/api/contracts", "POST", json=contract).status_code == 409
    assert c.call("resident", f"{path}/{first}", "DELETE").status_code == 200
    assert c.call("resident", path, "POST", json={"apartment_id": second}).status_code == 201


def test_an_ended_contract_frees_the_account_for_a_new_apartment(service_cluster):
    c = service_cluster
    first, second = make_apartment(c, "END-1"), make_apartment(c, "END-2")
    _, profile = register_resident(c, "END-1", "end.home")
    base = {"resident_id": profile["resident_id"], "contract_type": "rental"}
    assert c.call("resident", "/api/contracts", "POST", json={
        **base, "apartment_id": first, "start_date": "2020-01-01", "end_date": "2020-12-31"}).status_code == 201
    assert c.call("resident", "/api/contracts", "POST", json={
        **base, "apartment_id": second, "start_date": "2021-01-01", "end_date": "2021-12-31"}).status_code == 201


def test_residents_without_an_account_are_not_limited(service_cluster):
    c = service_cluster
    # Management can no longer add residents, but profiles without an account remain from earlier data.
    with sqlite3.connect(c.db_path) as db:
        resident_id = db.execute(
            "INSERT INTO residents(full_name,relation_type) VALUES ('Chủ Sở Hữu','owner')").lastrowid
    for code in ("FREE-1", "FREE-2"):
        response = c.call("resident", "/api/contracts", "POST", json={
            "apartment_id": make_apartment(c, code), "resident_id": resident_id,
            "contract_type": "ownership", "start_date": "2026-01-01"})
        assert response.status_code == 201, response.text


def test_rebuilt_account_table_keeps_usernames_unique_and_ids(service_cluster):
    with sqlite3.connect(service_cluster.db_path) as db:
        columns = {row[1] for row in db.execute("PRAGMA table_info(users)")}
        assert {"token_version", "lock_reason", "full_name", "id_card"} <= columns
        assert db.execute("SELECT COUNT(*) FROM users WHERE user_id=1 AND role='admin'").fetchone()[0] == 1
        technician = db.execute("SELECT full_name FROM users WHERE user_id=11").fetchone()[0]
        assert technician, "technicians keep their name from the assignment list"


def test_chatbot_points_vehicle_changes_at_the_new_form(service_cluster):
    with sqlite3.connect(service_cluster.db_path) as db:
        answer = db.execute("SELECT answer FROM faq_knowledge_base WHERE question LIKE 'Đăng ký thêm, huỷ%'").fetchone()
    if answer:
        assert "Đăng ký thủ tục" not in answer[0]
