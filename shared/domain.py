"""Small validation helpers shared by the independently deployed domain services."""

from datetime import datetime, timedelta, timezone
import logging

from flask import g

from shared.http import call_service
from shared.web import APIError, integer


def local_today():
    return datetime.now(timezone(timedelta(hours=7))).date()


def text(value, name, *, limit=5000, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value.strip():
        raise APIError(f"{name} không được để trống.")
    value = value.strip()
    if len(value) > limit:
        raise APIError(f"{name} không được quá {limit} ký tự.")
    return value


def enum(value, choices, name):
    if value not in choices:
        raise APIError(f"{name} phải là một trong: {', '.join(choices)}.")
    return value


def resident_profile():
    return call_service("resident", "/api/residents/me")


def apartment_access(apartment_id):
    apartment_id = integer(apartment_id, "apartment_id", min_value=1)
    if g.user["role"] == "resident":
        # A self-declared apartment code grants nothing until management confirms it.
        if apartment_id not in resident_profile().get("apartment_ids", []):
            raise APIError("Bạn chưa được xác nhận thuộc căn hộ này. Vui lòng liên hệ Ban quản lý.", 403)
    else:
        call_service("resident", f"/api/apartments/{apartment_id}", internal=True)
    return apartment_id


def notify(event_id, **fields):
    """Call after commit, without an open write: a lost notification must not undo the action."""
    try:
        call_service(
            "notification",
            "/api/notifications/events",
            method="POST",
            internal=True,
            json={"event_id": event_id, "type": "private", **fields},
        )
    except APIError:
        logging.getLogger(__name__).warning("Notification %s was not delivered.", event_id)


def one(db, table, key, identifier):
    # The caller supplies fixed table and key constants, never user input.
    item = db.execute(f"SELECT * FROM {table} WHERE {key}=?", (identifier,)).fetchone()
    if item is None:
        raise APIError("Không tìm thấy dữ liệu.", 404)
    return dict(item)
