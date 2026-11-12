"""Domain contracts with eight real services and an isolated database copy."""
import sqlite3
from concurrent.futures import ThreadPoolExecutor
import pytest


@pytest.fixture
def domains(service_cluster):
    def call(service, path, method="GET", role="admin", user_id=None, json=None, internal=False):
        # Explicitly map the two resident identities to source database users.
        user_id = {21: 3, 22: 4}.get(user_id, user_id)
        return service_cluster.call(service, path, method, role, user_id, json, internal)
    return call, service_cluster.db_path, service_cluster.modules


def test_vehicle_scope_and_internal_summary(domains):
    call, _, _ = domains
    own = call("parking", "/api/parking/vehicles", role="resident", user_id=21)
    assert own.status_code == 200
    assert own.json()["items"] and {row["apartment_id"] for row in own.json()["items"]} == {1}
    forbidden = call("parking", "/api/parking/vehicles", "POST", role="resident", user_id=21, json={"apartment_id": 2, "vehicle_type": "motorbike", "plate_number": "TEST-001", "monthly_fee": 100000})
    assert forbidden.status_code == 403
    payload = {"apartment_id": 1, "vehicle_type": "motorbike", "plate_number": "TEST-001", "monthly_fee": 100000}
    assert call("parking", "/api/parking/vehicles", "POST", json=payload).status_code == 201
    assert call("parking", "/api/parking/vehicles", "POST", json=payload).status_code == 409
    summary = call("parking", "/api/parking/summary?apartment_id=1", internal=True)
    assert summary.status_code == 200
    assert summary.json()["items"][0]["monthly_fee"] >= 100000


def test_guest_revenue_validated_and_one_entry_per_day(domains):
    call, _, _ = domains
    payload = {"parking_date": "2020-01-02", "daily_revenue": 125000}
    response = call("parking", "/api/parking/guest-daily", "POST", role="technician", user_id=11, json=payload)
    assert response.status_code == 201
    assert call("parking", "/api/parking/guest-daily", "POST", json=payload).status_code == 409
    assert call("parking", "/api/parking/guest-daily", "POST", json={"parking_date": "2020-01-03", "daily_revenue": -1}).status_code == 400
    assert call("parking", "/api/parking/guest-daily", "POST", json={"parking_date": "2099-01-03", "daily_revenue": 1}).status_code == 400
    assert call("parking", "/api/parking/guest-daily", role="resident", user_id=21).status_code == 403


def test_any_technician_can_work_a_ticket_assigned_to_a_colleague(domains):
    call, _, _ = domains
    created = call("maintenance", "/api/maintenance/tickets", "POST", json={"apartment_id": 1, "description": "Test repair", "technician_id": 1})
    assert created.status_code == 201
    path = "/api/maintenance/tickets/" + str(created.json()["ticket_id"])
    rows = call("maintenance", "/api/maintenance/tickets", role="technician", user_id=12).json()["items"]
    assert created.json()["ticket_id"] in {row["ticket_id"] for row in rows}
    assert call("maintenance", path, "PATCH", role="technician", user_id=12, json={"status": "completed"}).status_code == 409
    assert call("maintenance", path, "PATCH", role="technician", user_id=12, json={"status": "in_progress"}).status_code == 200
    assert call("maintenance", path, "PATCH", role="technician", user_id=11, json={"description": "Đổi nội dung"}).status_code == 403
    assert call("maintenance", path, "PATCH", role="technician", user_id=11, json={"status": "completed"}).status_code == 200
    assert call("maintenance", path, "PATCH", json={"status": "pending"}).status_code == 409


def test_vehicle_plate_uniqueness_survives_concurrent_requests(domains):
    call, _, _ = domains
    payload = {"apartment_id": 1, "vehicle_type": "motorbike", "plate_number": "CONCURRENT-123", "monthly_fee": 100000}
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: call("parking", "/api/parking/vehicles", "POST", json=payload).status_code, range(2)))
    assert sorted(results) == [201, 409]


def test_notification_private_scope_and_read_idempotency(domains):
    call, database, _ = domains
    created = call("notification", "/api/notifications", "POST", json={"type": "private", "title": "Resident one", "content": "Private detail", "target_apartment_id": 1})
    assert created.status_code == 201
    identifier = created.json()["notification_id"]
    assert created.json()["push"]["configured"] is False
    other = call("notification", "/api/notifications", role="resident", user_id=22).json()["items"]
    assert identifier not in {row["notification_id"] for row in other}
    assert call("notification", f"/api/notifications/{identifier}/read", "POST", role="resident", user_id=22).status_code == 403
    for _ in range(2):
        assert call("notification", f"/api/notifications/{identifier}/read", "POST", role="resident", user_id=21).status_code == 200
    with sqlite3.connect(database) as db:
        assert db.execute("SELECT COUNT(*) FROM notification_logs WHERE notification_id=? AND resident_id=1", (identifier,)).fetchone()[0] == 1
    event = {"event_id": "admin-report-001", "type": "private", "target_role": "admin", "title": "Report", "content": "Internal payment report"}
    private = call("notification", "/api/notifications/events", "POST", json=event, internal=True)
    assert private.status_code == 201
    private_id = private.json()["notification_id"]
    assert call("notification", "/api/notifications/events", "POST", json=event, internal=True).json()["duplicate"] is True
    resident_notices = call("notification", "/api/notifications", role="resident", user_id=21).json()["items"]
    assert private_id not in {row["notification_id"] for row in resident_notices}


def test_complaint_identity_and_resolution(domains):
    call, _, _ = domains
    payload = {"type": "complaint", "category": "Vệ sinh", "content": "Hành lang cần được dọn dẹp"}
    created = call("complaint", "/api/complaints", "POST", role="resident", user_id=21, json=payload)
    assert created.status_code == 201 and created.json()["resident_id"] == 1
    assert call("complaint", "/api/complaints", "POST", role="resident", user_id=21, json={**payload, "resident_id": 2}).status_code == 403
    path = "/api/complaints/" + str(created.json()["complaint_id"])
    assert call("complaint", path, "PATCH", json={"status": "resolved"}).status_code == 400
    resolved = call("complaint", path, "PATCH", json={"status": "resolved", "response": "Đã hoàn tất vệ sinh."})
    assert resolved.status_code == 200 and resolved.json()["resolved_at"]


def test_chatbot_normalizes_accents_and_does_not_invent_answers(domains):
    call, _, _ = domains
    pet = call("chatbot", "/api/chatbot/ask", "POST", json={"question": "Co duoc nuoi thu cung khong?"})
    assert pet.status_code == 200 and pet.json()["matched"]
    assert "thú cưng" in pet.json()["answer"]
    location = call("chatbot", "/api/chatbot/ask", "POST", json={"question": "Hieu thuoc o dau?"})
    assert location.json()["source"] == "location"
    unknown = call("chatbot", "/api/chatbot/ask", "POST", json={"question": "Tốc độ ánh sáng trong chân không?"})
    assert unknown.json()["matched"] is False
