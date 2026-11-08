"""Small validation helpers shared by the independently deployed domain services."""
from datetime import datetime, timedelta, timezone

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
        prof = resident_profile()
        apt_ids = prof.get("apartment_ids", [])
        if apartment_id not in apt_ids:
            reg_code = prof.get("registered_apartment_code")
            matched = False
            if reg_code:
                try:
                    apts = call_service("resident", "/api/apartments", internal=True).get("items", [])
                    matched = any(a["apartment_id"] == apartment_id and str(a["code"]).upper() == str(reg_code).upper() for a in apts)
                except Exception:
                    matched = False
            if not matched:
                raise APIError("Bạn không có quyền truy cập căn hộ này.", 403)
    else:
        call_service("resident", f"/api/apartments/{apartment_id}", internal=True)
    return apartment_id


def one(db, table, key, identifier):
    # The caller supplies fixed table and key constants, never user input.
    item = db.execute(f"SELECT * FROM {table} WHERE {key}=?", (identifier,)).fetchone()
    if item is None:
        raise APIError("Không tìm thấy dữ liệu.", 404)
    return dict(item)
