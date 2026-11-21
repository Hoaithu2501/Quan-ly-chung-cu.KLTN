"""Management replies reach only the author and survive delivery failures."""
import json
import sqlite3
from concurrent.futures import ThreadPoolExecutor

from shared.web import APIError


def create_complaint(cluster):
    response = cluster.call("complaint", "/api/complaints", method="POST", role="resident", json={
        "type": "complaint", "category": "Vệ sinh", "content": "Hành lang cần được dọn dẹp."})
    assert response.status_code == 201, response.text
    return response.json()["complaint_id"]


def reply(cluster, identifier, **values):
    return cluster.call("complaint", f"/api/complaints/{identifier}", method="PATCH", json=values)


def outbox(cluster, identifier):
    """Reply events only; the notice telling management about a new request is tested elsewhere."""
    with sqlite3.connect(cluster.db_path) as db:
        db.row_factory = sqlite3.Row
        return [dict(row) for row in db.execute(
            "SELECT * FROM complaint_outbox WHERE complaint_id=? AND event_id LIKE 'complaint:reply:%' "
            "ORDER BY created_at,event_id", (identifier,))]


def notice_ids(cluster, *, role="resident", user_id=3):
    response = cluster.call("notification", "/api/notifications", role=role, user_id=user_id)
    assert response.status_code == 200, response.text
    return {row["notification_id"] for row in response.json()["items"]}


def event_notices(cluster, identifier):
    events = outbox(cluster, identifier)
    with sqlite3.connect(cluster.db_path) as db:
        return [row[0] for event in events for row in db.execute(
            "SELECT notification_id FROM notification_events WHERE event_id=?", (event["event_id"],))]


def test_reply_is_private_to_author_even_for_another_resident_in_same_apartment(service_cluster):
    cluster = service_cluster
    # Model two separate accounts sharing an apartment. A complaint reply must
    # remain personal even though ordinary apartment notices reach both people.
    with sqlite3.connect(cluster.db_path) as db:
        db.execute("UPDATE apartment_contracts SET apartment_id=1 WHERE resident_id=2")
    other_profile = cluster.call("resident", "/api/residents/me", role="resident", user_id=4)
    assert 1 in other_profile.json()["apartment_ids"]
    identifier = create_complaint(cluster)
    path = f"/api/complaints/{identifier}"
    for role, user_id in (("resident", 3), ("resident", 4), ("technician", 11)):
        denied = cluster.call("complaint", path, method="PATCH", role=role, user_id=user_id,
                              json={"response": "Không có quyền phản hồi."})
        assert denied.status_code == 403, denied.text
    response_text = "Ban quản lý đã bố trí nhân viên dọn hành lang vào sáng mai."
    updated = reply(cluster, identifier, status="processing", response=response_text)
    assert updated.status_code == 200, updated.text
    assert updated.json()["response"] == response_text
    [notice_id] = event_notices(cluster, identifier)
    assert notice_id in notice_ids(cluster)
    # Management wrote the reply itself: the notice is the resident's alone.
    assert notice_id not in notice_ids(cluster, role="admin", user_id=1)
    assert notice_id not in notice_ids(cluster, user_id=4)
    assert notice_id not in notice_ids(cluster, user_id=5)
    assert notice_id not in notice_ids(cluster, role="technician", user_id=11)
    rows = cluster.call("notification", "/api/notifications", role="resident", user_id=3).json()["items"]
    notice = next(row for row in rows if row["notification_id"] == notice_id)
    assert notice["type"] == "private" and notice["target_resident_id"] == 1
    assert str(identifier) in notice["title"] and response_text in notice["content"]
    for other in (4, 5):
        denied = cluster.call("notification", f"/api/notifications/{notice_id}/read", method="POST",
                              role="resident", user_id=other)
        assert denied.status_code == 403, denied.text
    for _ in range(2):
        marked = cluster.call("notification", f"/api/notifications/{notice_id}/read", method="POST", role="resident")
        assert marked.status_code == 200, marked.text
    with sqlite3.connect(cluster.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM notification_logs WHERE notification_id=? AND resident_id=1",
                          (notice_id,)).fetchone()[0] == 1


def test_management_keeps_its_own_notes_to_a_resident_but_not_the_automatic_ones(service_cluster):
    cluster = service_cluster
    written = cluster.call("notification", "/api/notifications", method="POST", json={
        "type": "private", "target_resident_id": 1, "title": "Nhắc riêng", "content": "Vui lòng liên hệ Ban quản lý."})
    assert written.status_code == 201, written.text
    note = written.json()["notification_id"]
    identifier = create_complaint(cluster)
    assert reply(cluster, identifier, response="Ban quản lý đã tiếp nhận.").status_code == 200
    [automatic] = event_notices(cluster, identifier)
    seen = notice_ids(cluster, role="admin", user_id=1)
    assert note in seen and automatic not in seen
    assert {note, automatic} <= notice_ids(cluster)


def test_unchanged_replies_do_not_repeat_notifications_but_amended_closed_reply_does(service_cluster):
    cluster = service_cluster
    identifier = create_complaint(cluster)
    assert reply(cluster, identifier, status="pending").status_code == 200
    assert outbox(cluster, identifier) == []
    assert reply(cluster, identifier, status="resolved").status_code == 400
    assert reply(cluster, identifier, response="   ").status_code == 400
    first = "Ban quản lý đã tiếp nhận và sẽ kiểm tra."
    assert reply(cluster, identifier, response=first).status_code == 200
    assert len(outbox(cluster, identifier)) == 1
    assert reply(cluster, identifier, response="  " + first + "  ").status_code == 200
    assert reply(cluster, identifier, status="processing").status_code == 200
    closed = reply(cluster, identifier, status="resolved")
    assert closed.status_code == 200 and closed.json()["resolved_at"]
    resolved_at = closed.json()["resolved_at"]
    assert len(outbox(cluster, identifier)) == 1
    amended = reply(cluster, identifier, status="resolved", response="Đã dọn dẹp xong, cư dân vui lòng kiểm tra lại.")
    assert amended.status_code == 200, amended.text
    assert amended.json()["resolved_at"] == resolved_at
    assert len(outbox(cluster, identifier)) == 2
    assert len(event_notices(cluster, identifier)) == 2
    assert reply(cluster, identifier, status="processing").status_code == 409
    assert len(outbox(cluster, identifier)) == 2


def test_reply_is_saved_during_notification_outage_then_delivered_on_retry(service_cluster, monkeypatch):
    cluster = service_cluster
    identifier = create_complaint(cluster)
    complaint = cluster.modules["complaint"]
    original = complaint.call_service

    def unavailable(service, path, **kwargs):
        if service == "notification":
            raise APIError("Dịch vụ thông báo tạm thời không khả dụng.", 503)
        return original(service, path, **kwargs)

    monkeypatch.setattr(complaint, "call_service", unavailable)
    message = "Đã tiếp nhận, Ban quản lý sẽ phản hồi sau khi kiểm tra."
    saved = reply(cluster, identifier, status="processing", response=message)
    assert saved.status_code == 200 and saved.json()["response"] == message
    [event] = outbox(cluster, identifier)
    assert event["delivered_at"] is None and event["attempts"] >= 1
    assert event["last_error"]
    payload = json.loads(event["payload"])
    assert payload["target_resident_id"] == 1
    assert event_notices(cluster, identifier) == []
    monkeypatch.setattr(complaint, "call_service", original)
    with cluster.apps["complaint"].app_context():
        assert complaint.dispatch_outbox() == 1
        assert complaint.dispatch_outbox() == 0
    [delivered] = outbox(cluster, identifier)
    assert delivered["event_id"] == event["event_id"]
    assert delivered["delivered_at"] and delivered["last_error"] is None
    [notice_id] = event_notices(cluster, identifier)
    assert notice_id in notice_ids(cluster)


def test_lost_delivery_acknowledgement_does_not_duplicate_resident_notice(service_cluster, monkeypatch):
    cluster = service_cluster
    identifier = create_complaint(cluster)
    complaint = cluster.modules["complaint"]
    original = complaint.call_service

    def lose_acknowledgement(service, path, **kwargs):
        result = original(service, path, **kwargs)
        if service == "notification":
            raise APIError("Không nhận được phản hồi sau khi gửi.", 503)
        return result

    monkeypatch.setattr(complaint, "call_service", lose_acknowledgement)
    saved = reply(cluster, identifier, response="Ban quản lý đã tiếp nhận phản ánh của cư dân.")
    assert saved.status_code == 200, saved.text
    [pending] = outbox(cluster, identifier)
    assert pending["delivered_at"] is None
    [notice_id] = event_notices(cluster, identifier)
    monkeypatch.setattr(complaint, "call_service", original)
    with cluster.apps["complaint"].app_context():
        assert complaint.dispatch_outbox() == 1
        assert complaint.dispatch_outbox() == 0
    assert event_notices(cluster, identifier) == [notice_id]
    with sqlite3.connect(cluster.db_path) as db:
        assert db.execute("SELECT COUNT(*) FROM notification_events WHERE event_id=?",
                          (pending["event_id"],)).fetchone()[0] == 1


def test_concurrent_identical_replies_create_one_notification(service_cluster):
    cluster = service_cluster
    identifier = create_complaint(cluster)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reply(cluster, identifier, status="processing",
            response="Ban quản lý sẽ kiểm tra hành lang trong hôm nay."), range(2)))
    assert [response.status_code for response in results] == [200, 200]
    assert len(outbox(cluster, identifier)) == 1
    assert len(event_notices(cluster, identifier)) == 1
