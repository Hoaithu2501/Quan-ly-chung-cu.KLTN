"""Optional FCM HTTP v1 delivery. Private details remain in the authenticated inbox."""
import json
import os
from pathlib import Path

import requests

from shared.config import ROOT


def push_settings():
    errors = []
    try:
        raw = json.loads(os.getenv("FIREBASE_WEB_CONFIG") or "{}")
        if not isinstance(raw, dict):
            raise ValueError()
    except (ValueError, TypeError):
        raw = {}
        errors.append("FIREBASE_WEB_CONFIG phải là một JSON object trên một dòng.")
    keys = ("apiKey", "authDomain", "projectId", "storageBucket", "messagingSenderId", "appId", "vapidKey")
    config = {key: raw[key].strip() for key in keys if isinstance(raw.get(key), str)}
    if os.getenv("FIREBASE_VAPID_KEY", "").strip():
        config["vapidKey"] = os.environ["FIREBASE_VAPID_KEY"].strip()
    for key in ("apiKey", "projectId", "messagingSenderId", "appId", "vapidKey"):
        if not config.get(key):
            errors.append(f"Thiếu cấu hình Web: {key}.")
    project = os.getenv("FIREBASE_PROJECT_ID", "").strip() or config.get("projectId", "")
    if project and project != config.get("projectId"):
        errors.append("FIREBASE_PROJECT_ID phải trùng projectId của Web app.")
    value = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    path = Path(value) if value else None
    if path is not None and not path.is_absolute():
        path = ROOT / path
    if path is None:
        errors.append("Chưa đặt GOOGLE_APPLICATION_CREDENTIALS.")
    else:
        try:
            service = json.loads(path.read_text(encoding="utf-8-sig"))
            if (not isinstance(service, dict) or service.get("type") != "service_account"
                    or not service.get("private_key") or not service.get("client_email")):
                raise ValueError()
            if service.get("project_id") != project:
                errors.append("File service account và Web app không cùng Firebase project.")
        except (OSError, ValueError, TypeError):
            errors.append("Không đọc được file service account hợp lệ; kiểm tra đường dẫn và volume Docker.")
    return {"configured": not errors, "config": config, "project": project,
            "credential_path": str(path) if path else "", "errors": errors}


def access_credentials(settings):
    from google.auth import load_credentials_from_file
    from google.auth.transport.requests import Request

    credentials, _ = load_credentials_from_file(settings["credential_path"],
        scopes=["https://www.googleapis.com/auth/firebase.messaging"])
    # Bound OAuth requests as well as the FCM send request.
    transport = Request()
    credentials.refresh(lambda *args, **kwargs: transport(*args, **{**kwargs, "timeout": 10}))
    return credentials


def deliver(settings, notification, tokens, db):
    if not tokens:
        return {"configured": True, "sent": 0, "failed": 0}
    credentials = access_credentials(settings)
    sent = failed = 0
    private = notification["type"] == "private"
    for row in tokens:
        try:
            response = requests.post(
                f"https://fcm.googleapis.com/v1/projects/{settings['project']}/messages:send",
                headers={"Authorization": "Bearer " + credentials.token},
                json={"message": {
                    "token": row["token"],
                    # Data-only lets the worker verify the currently opted-in
                    # account before showing anything, including queued messages.
                    "data": {"notification_id": str(notification["notification_id"]),
                             "user_id": str(row["user_id"]),
                             "title": "An Cư · Thông báo riêng" if private else notification["title"],
                             "body": "Bạn có thông báo mới. Mở An Cư để xem chi tiết." if private else notification["content"][:500]},
                    "webpush": {"headers": {"TTL": "300", "Urgency": "normal"}}
                }}, timeout=(3, 5))
            if response.ok:
                sent += 1
            else:
                failed += 1
                try:
                    details = response.json().get("error", {}).get("details", [])
                except (ValueError, AttributeError):
                    details = []
                if isinstance(details, list) and any(isinstance(item, dict) and item.get("errorCode") == "UNREGISTERED"
                                                    for item in details):
                    db.execute("DELETE FROM notification_push_tokens WHERE token=?", (row["token"],))
        except requests.RequestException:
            failed += 1
    db.commit()
    return {"configured": True, "sent": sent, "failed": failed}
