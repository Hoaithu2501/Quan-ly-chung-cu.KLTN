"""FCM delivery contracts using isolated databases and a fake FCM transport."""
import json
import sqlite3
from types import SimpleNamespace

import pytest
import requests

from shared import firebase_push


@pytest.fixture
def configured(service_cluster, monkeypatch, tmp_path):
    key = tmp_path / "firebase.json"
    key.write_text(json.dumps({"type": "service_account", "project_id": "ancu-test",
                              "client_email": "test@example.invalid", "private_key": "fake-private-key"}))
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", str(key))
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "ancu-test")
    monkeypatch.setenv("FIREBASE_WEB_CONFIG", json.dumps({"projectId": "ancu-test", "apiKey": "public-web-key",
        "messagingSenderId": "123", "appId": "1:123:web:abc", "private_key": "must-not-be-returned"}))
    monkeypatch.setenv("FIREBASE_VAPID_KEY", "public-vapid-key")
    monkeypatch.setattr(firebase_push, "access_credentials", lambda _: SimpleNamespace(token="fake-oauth"))
    sent = []
    def send(url, **kwargs):
        assert url == "https://fcm.googleapis.com/v1/projects/ancu-test/messages:send"
        sent.append(kwargs["json"]["message"])
        return SimpleNamespace(ok=True)
    monkeypatch.setattr(firebase_push.requests, "post", send)
    return service_cluster, sent


def register(cluster, token, role="resident", user_id=3):
    response = cluster.call("notification", "/api/notifications/push-tokens", "POST",
                            role=role, user_id=user_id, json={"token": token})
    assert response.status_code == 201, response.text


def notice(cluster, **kwargs):
    response = cluster.call("notification", "/api/notifications", "POST",
                            json={"type": "private", "title": "Test", "content": "Private invoice information", **kwargs})
    assert response.status_code == 201, response.text
    return response.json()


def test_config_checks_project_file_and_exposes_only_public_fields(configured, monkeypatch):
    cluster, _ = configured
    response = cluster.call("notification", "/api/notifications/push-config").json()
    assert response["configured"] and not response["errors"]
    assert "private_key" not in response["config"]
    assert "credential_path" not in response
    monkeypatch.setenv("FIREBASE_PROJECT_ID", "wrong-project")
    assert not cluster.call("notification", "/api/notifications/push-config").json()["configured"]
    monkeypatch.setenv("GOOGLE_APPLICATION_CREDENTIALS", "missing-secret-file.json")
    response = cluster.call("notification", "/api/notifications/push-config", role="resident").json()
    assert not response["configured"] and "errors" not in response
    monkeypatch.setenv("FIREBASE_WEB_CONFIG", "[]")
    assert not firebase_push.push_settings()["configured"]


def test_private_apartment_scope_and_no_sensitive_push_body(configured):
    cluster, sent = configured
    register(cluster, "apt-1")
    register(cluster, "apt-2", user_id=4)
    register(cluster, "admin", role="admin", user_id=1)
    result = notice(cluster, target_apartment_id=1)
    assert result["push"] == {"configured": True, "sent": 1, "failed": 0}
    assert [m["token"] for m in sent] == ["apt-1"]
    assert sent[0]["data"]["user_id"] == "3"
    assert "Private invoice information" not in json.dumps(sent)
    assert "notification" not in sent[0]  # Worker must check ownership first.


def test_all_current_household_members_receive_apartment_push(configured):
    cluster, sent = configured
    with sqlite3.connect(cluster.db_path) as db:
        resident_id = db.execute("SELECT resident_id FROM residents WHERE user_id=4").fetchone()[0]
    response = cluster.call("resident", f"/api/residents/{resident_id}/apartments", "POST",
                            json={"apartment_id": 1})
    assert response.status_code in (200, 201), response.text
    register(cluster, "member-1")
    register(cluster, "member-2", user_id=4)
    notice(cluster, target_apartment_id=1)
    assert {m["token"] for m in sent} == {"member-1", "member-2"}


def test_personal_and_admin_targets_do_not_cross_accounts(configured):
    cluster, sent = configured
    register(cluster, "resident")
    register(cluster, "other", user_id=4)
    register(cluster, "admin", role="admin", user_id=1)
    with sqlite3.connect(cluster.db_path) as db:
        resident_id = db.execute("SELECT resident_id FROM residents WHERE user_id=3").fetchone()[0]
    notice(cluster, target_resident_id=resident_id)
    assert [m["token"] for m in sent] == ["resident"]
    sent.clear()
    notice(cluster, target_role="admin")
    assert [m["token"] for m in sent] == ["admin"]


def test_locked_accounts_and_stale_roles_are_excluded(configured):
    cluster, sent = configured
    register(cluster, "resident")
    register(cluster, "admin", role="admin", user_id=1)
    with sqlite3.connect(cluster.db_path) as db:
        db.execute("UPDATE users SET status='locked' WHERE user_id=3")
        # Stored role is intentionally stale; current Auth data is authoritative.
        db.execute("UPDATE notification_push_roles SET role='admin' WHERE user_id=3")
    notice(cluster, type="general")
    assert [m["token"] for m in sent] == ["admin"]


def test_token_transfer_and_owner_only_unregister(configured):
    cluster, sent = configured
    register(cluster, "shared-browser")
    register(cluster, "shared-browser", user_id=4)
    assert cluster.call("notification", "/api/notifications/push-tokens", "DELETE", role="resident",
                        json={"token": "shared-browser"}).status_code == 200
    notice(cluster, target_apartment_id=1)
    assert not sent
    notice(cluster, type="general")
    assert [m["data"]["user_id"] for m in sent] == ["4"]
    cluster.call("notification", "/api/notifications/push-tokens", "DELETE", role="resident", user_id=4,
                 json={"token": "shared-browser"})
    sent.clear()
    notice(cluster, type="general")
    assert not sent


@pytest.mark.parametrize("failure", ["unregistered", "permission", "network"])
def test_provider_failure_preserves_inbox_and_only_removes_dead_tokens(configured, monkeypatch, failure):
    cluster, _ = configured
    register(cluster, "recipient")
    def reject(*args, **kwargs):
        if failure == "network":
            raise requests.Timeout()
        code = "UNREGISTERED" if failure == "unregistered" else "PERMISSION_DENIED"
        return SimpleNamespace(ok=False, json=lambda: {"error": {"details": [{"errorCode": code}]}})
    monkeypatch.setattr(firebase_push.requests, "post", reject)
    result = notice(cluster, target_apartment_id=1)
    assert result["push"]["failed"] == 1
    with sqlite3.connect(cluster.db_path) as db:
        assert db.execute("SELECT 1 FROM notifications WHERE notification_id=?", (result["notification_id"],)).fetchone()
        assert bool(db.execute("SELECT 1 FROM notification_push_tokens WHERE token='recipient'").fetchone()) == (failure != "unregistered")


def test_duplicate_internal_event_sends_push_once(configured):
    cluster, sent = configured
    register(cluster, "resident")
    payload = {"event_id": "firebase:paid:test", "type": "private", "target_apartment_id": 1,
               "title": "Payment", "content": "Test"}
    for _ in range(2):
        response = cluster.call("notification", "/api/notifications/events", "POST", json=payload, internal=True)
        assert response.status_code in (200, 201)
    assert len(sent) == 1


def test_missing_firebase_still_stores_notification(service_cluster):
    result = notice(service_cluster, target_apartment_id=1)
    assert result["push"] == {"configured": False, "sent": 0, "failed": 0}
