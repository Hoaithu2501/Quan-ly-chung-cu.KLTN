"""Auth owns users only; resident profile provisioning uses HTTP."""

import re
import secrets
from datetime import datetime, timedelta, timezone
import jwt
from flask import g, request
from werkzeug.security import check_password_hash, generate_password_hash
from shared.audit import record_audit
from shared.auth import require_auth, auth_or_internal
from shared.config import secret
from shared.db import get_db
from shared.http import call_service
from shared.ratelimit import SlidingWindow
from shared.web import create_app as base_app, APIError, body, client_ip, integer, person_name, required, run

PASSWORD_HASHES = ("scrypt:", "pbkdf2:")
ROLES = ("admin", "resident", "technician")
# Verified for unknown usernames too, so response time does not reveal which accounts exist.
DECOY_HASH = generate_password_hash(secrets.token_urlsafe(32))


def public_user(row):
    return {
        k: row[k]
        for k in ("user_id", "username", "full_name", "email", "phone", "role", "status", "created_at", "lock_reason")
    }


def staff_id_card(value):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > 30:
        raise APIError("Thông tin cá nhân không hợp lệ.")
    return value.strip() or None


def validate_username(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_.-]{3,20}", value):
        raise APIError("Tên đăng nhập gồm 3–20 chữ cái, số, dấu chấm, gạch dưới hoặc gạch ngang.")


def validate_password(value):
    if not isinstance(value, str) or not 6 <= len(value) <= 30:
        raise APIError("Mật khẩu cần từ 6 đến 30 ký tự.")


def credentials(data):
    required(data, "username", "password")
    validate_username(data["username"])
    validate_password(data["password"])
    if data.get("email"):
        validate_email(data["email"])


def validate_email(value):
    if (
        not isinstance(value, str)
        or len(value) > 254
        or not re.fullmatch(r"[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*@gmail\.com", value, re.IGNORECASE)
    ):
        raise APIError("Email phải là địa chỉ hợp lệ có đuôi @gmail.com.")


def required_phone(value):
    if value is None or isinstance(value, str) and not value.strip():
        raise APIError("Vui lòng nhập số điện thoại.")
    if not isinstance(value, str) or len(value) > 20:
        raise APIError("Số điện thoại không hợp lệ (tối đa 20 ký tự).")
    return value.strip()


def session(row):
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": str(row["user_id"]),
            "role": row["role"],
            "username": row["username"],
            "ver": row["token_version"],
            "iss": "qlcc-auth",
            "iat": now,
            "exp": now + timedelta(hours=8),
        },
        secret("JWT_SECRET"),
        algorithm="HS256",
    )
    return {"token": token, "user": public_user(row)}


def user_by_id(user_id):
    return get_db().execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def caller_row():
    """The signed-in account, rejecting tokens issued before its latest password change."""
    row = user_by_id(g.user["user_id"])
    if row is not None and row["token_version"] != g.user.get("token_version", 0):
        raise APIError("Phiên đăng nhập đã hết hiệu lực. Vui lòng đăng nhập lại.", 401)
    return row


def active_caller():
    row = caller_row()
    if row is None or row["status"] != "active":
        raise APIError("Tài khoản không còn hoạt động.", 401)
    return row


def admin_active():
    row = caller_row()
    if not row or row["status"] != "active" or row["role"] != "admin":
        raise APIError("Tài khoản không còn quyền quản trị.", 403)
    return row


def account_name(row):
    """Residents keep their name on the resident profile, staff on the account."""
    if row["full_name"]:
        return row["full_name"]
    profiles = call_service("resident", "/api/residents", internal=True)["items"]
    return next((p["full_name"] for p in profiles if p["user_id"] == row["user_id"]), row["username"])


def sync_role_profile(row, role):
    """Prepare the profile the new role needs. Runs before any local write, so SQLite's lock is free."""
    name = account_name(row)
    if role == "resident":
        call_service(
            "resident",
            "/api/residents/provision",
            method="POST",
            internal=True,
            json={"user_id": row["user_id"], "full_name": name, "phone": row["phone"], "relation_type": "tenant"},
        )
    if "technician" in (role, row["role"]):
        call_service(
            "maintenance",
            f"/api/maintenance/technicians/accounts/{row['user_id']}",
            method="PUT",
            internal=True,
            json={"full_name": name, "active": role == "technician"},
        )
    return name


def create_app():
    app = base_app("auth")
    # Failures only. The pair limit stops guessing one account from one address; the wider
    # limits stop spraying many accounts or guessing one account from many addresses.
    failed_pair = SlidingWindow(10, 300)
    failed_ip = SlidingWindow(60, 300)
    failed_user = SlidingWindow(40, 300)
    registrations = SlidingWindow(20, 3600)

    @app.post("/api/auth/login")
    def login():
        data = body()
        required(data, "username", "password")
        username, password = data["username"], data["password"]
        if not isinstance(username, str) or not isinstance(password, str) or len(password) > 128 or len(username) > 60:
            raise APIError("Thông tin đăng nhập không hợp lệ.", 400)
        ip = client_ip()
        limits = ((failed_pair, (ip, username)), (failed_ip, ip), (failed_user, username))
        if any(window.exceeded(key) for window, key in limits):
            raise APIError("Đăng nhập sai quá nhiều lần. Thử lại sau 5 phút.", 429)
        row = get_db().execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        real_hash = bool(row) and row["password_hash"].startswith(PASSWORD_HASHES)
        valid = check_password_hash(row["password_hash"] if real_hash else DECOY_HASH, password) and real_hash
        if not valid:
            for window, key in limits:
                window.record(key)
            raise APIError("Sai tên đăng nhập hoặc mật khẩu, vui lòng kiểm tra lại", 401)
        if row["status"] == "locked":
            return {"error": "Tài khoản đã bị khóa.", "code": "ACCOUNT_LOCKED", "reason": row["lock_reason"]}, 403
        failed_pair.clear((ip, username))
        return session(row)

    @app.get("/api/auth/me")
    @require_auth()
    def me():
        row = active_caller()
        return {"user": {**public_user(row), "id_card": row["id_card"]}}

    @app.post("/api/auth/register")
    def register():
        if not registrations.hit(client_ip()):
            raise APIError("Đăng ký quá nhiều lần từ địa chỉ này. Vui lòng thử lại sau.", 429)
        data = body()
        credentials(data)
        required(data, "full_name", "email", "apartment_code")
        validate_email(data["email"])
        data["email"] = data["email"].lower()
        data["phone"] = required_phone(data.get("phone"))
        full_name = person_name(data["full_name"])
        if data.get("role", "resident") != "resident":
            raise APIError("Đăng ký công khai chỉ dành cho cư dân.", 403)
        apartment_code = data["apartment_code"]
        if not isinstance(apartment_code, str) or not apartment_code.strip() or len(apartment_code.strip()) > 30:
            raise APIError("Số căn hộ không hợp lệ (tối đa 30 ký tự).")
        apartments = call_service("resident", "/api/apartments", internal=True)["items"]
        matched = next((a for a in apartments if a["code"].casefold() == apartment_code.strip().casefold()), None)
        if matched is None:
            raise APIError("Không tìm thấy căn hộ. Vui lòng kiểm tra lại số căn hộ.")
        db = get_db()
        cursor = db.execute(
            "INSERT INTO users(username,password_hash,email,phone,role,status) VALUES(?,?,?,?,?,?)",
            (
                data["username"],
                generate_password_hash(data["password"]),
                data.get("email") or None,
                data.get("phone"),
                "resident",
                "locked",
            ),
        )
        user_id = cursor.lastrowid
        db.commit()  # Release SQLite write lock before the other service writes.
        try:
            call_service(
                "resident",
                "/api/residents/provision",
                method="POST",
                internal=True,
                json={
                    "user_id": user_id,
                    "full_name": full_name,
                    "phone": data.get("phone"),
                    "relation_type": "tenant",
                    "registered_apartment_code": matched["code"],
                },
            )
        except APIError:
            # No cross-service deletion: a timeout might have committed a profile. Keep account
            # locked for reconciliation through the administration screen.
            raise APIError("Chưa tạo được hồ sơ cư dân. Tài khoản đã khóa; liên hệ Ban quản lý để hoàn tất.", 503)
        db.execute("UPDATE users SET status='active' WHERE user_id=?", (user_id,))
        db.commit()
        try:
            # Management must confirm the apartment link before the resident can use it.
            call_service(
                "notification",
                "/api/notifications/events",
                method="POST",
                internal=True,
                json={
                    "event_id": f"resident-registered:{user_id}",
                    "type": "private",
                    "target_role": "admin",
                    "title": f"Cư dân mới chờ xác nhận căn hộ {matched['code']}",
                    "content": (
                        f"{data['full_name'].strip()} (tài khoản {data['username']}, SĐT {data['phone']}) "
                        f"vừa đăng ký và khai báo căn hộ {matched['code']}. Vào Cư dân & hợp đồng, "
                        'chọn "Xác nhận căn hộ" sau khi kiểm tra thông tin cư trú.'
                    ),
                },
            )
        except APIError:
            app.logger.warning("Registration saved; management notification was not delivered.")
        return session(user_by_id(user_id)), 201

    @app.patch("/api/auth/me")
    @require_auth()
    def update_me():
        data = body()
        if set(data) - {"full_name", "id_card", "phone", "email", "username"}:
            raise APIError("Chỉ được cập nhật thông tin cá nhân.")
        db = get_db()
        row = active_caller()
        username = data.get("username", row["username"])
        if "username" in data:
            validate_username(username)
        if db.execute("SELECT 1 FROM users WHERE username=? AND user_id<>?", (username, row["user_id"])).fetchone():
            raise APIError("Tên đăng nhập đã được sử dụng.", 409)
        email = data.get("email", row["email"])
        # An existing address is left alone, so older accounts can still edit their other details.
        if "email" in data and email != row["email"]:
            validate_email(email)
            email = email.lower()
        phone = required_phone(data["phone"]) if "phone" in data else row["phone"]
        full_name, id_card = row["full_name"], row["id_card"]
        # Other services are called before any local write, so SQLite's write lock is free.
        if row["role"] == "resident":
            profile_data = {k: v for k, v in data.items() if k in ("full_name", "id_card")}
            if "phone" in data:
                profile_data["phone"] = phone
            profile = call_service("resident", "/api/residents/me", method="PATCH", json=profile_data)
        else:
            if "full_name" in data:
                full_name = person_name(data["full_name"])
            if "id_card" in data:
                id_card = staff_id_card(data["id_card"])
            if row["role"] == "technician" and "full_name" in data:
                call_service(
                    "maintenance", "/api/maintenance/technicians/me", method="PATCH", json={"full_name": full_name}
                )
            profile = {"full_name": full_name, "id_card": id_card, "phone": phone}
        db.execute(
            "UPDATE users SET username=?,email=?,phone=?,full_name=?,id_card=? WHERE user_id=?",
            (username, email, phone, full_name, id_card, row["user_id"]),
        )
        db.commit()
        return {
            **session(user_by_id(row["user_id"])),
            "profile": profile,
        }

    @app.post("/api/auth/me/password")
    @require_auth()
    def change_password():
        data = body()
        required(data, "current_password", "new_password", "confirm_password")
        validate_password(data["new_password"])
        validate_password(data["confirm_password"])
        if not isinstance(data["current_password"], str) or len(data["current_password"]) > 128:
            raise APIError("Mật khẩu hiện tại không đúng.")
        db = get_db()
        row = active_caller()
        if not row["password_hash"].startswith(PASSWORD_HASHES) or not check_password_hash(
            row["password_hash"], data["current_password"]
        ):
            raise APIError("Mật khẩu hiện tại không đúng.")
        if data["new_password"] != data["confirm_password"]:
            raise APIError("Mật khẩu mới và mật khẩu nhập lại không trùng khớp.")
        if check_password_hash(row["password_hash"], data["new_password"]):
            raise APIError("Mật khẩu mới không được trùng với mật khẩu hiện tại.")
        db.execute(
            "UPDATE users SET password_hash=?,token_version=token_version+1 WHERE user_id=?",
            (generate_password_hash(data["new_password"]), row["user_id"]),
        )
        db.commit()
        # Other devices are signed out; this one continues with a fresh token.
        return {
            "message": "Đã đổi mật khẩu thành công.",
            **session(user_by_id(row["user_id"])),
        }

    @app.get("/api/auth/users")
    @auth_or_internal("admin")
    def users():
        if g.user["role"] == "admin":
            admin_active()
        return {"items": [public_user(r) for r in get_db().execute("SELECT * FROM users ORDER BY user_id")]}

    @app.patch("/api/auth/users/<int:user_id>")
    @require_auth("admin")
    def update_user(user_id):
        admin_active()
        data = body()
        if set(data) != {"role"}:
            raise APIError("Chỉ được thay đổi vai trò của tài khoản.")
        role = data["role"]
        if role not in ROLES:
            raise APIError("Vai trò không hợp lệ.")
        # Otherwise the only administrator could remove the last way back into this screen.
        if user_id == g.user["user_id"]:
            raise APIError("Không thể tự đổi vai trò của tài khoản đang sử dụng.")
        row = user_by_id(user_id)
        if row is None:
            raise APIError("Không tìm thấy tài khoản.", 404)
        if role == row["role"]:
            return public_user(row)
        full_name = sync_role_profile(row, role)
        db = get_db()
        with db:
            # The old token still names the old role, so that session ends and the next login shows the new one.
            db.execute(
                "UPDATE users SET role=?,full_name=?,token_version=token_version+1 WHERE user_id=?",
                (role, full_name, user_id),
            )
            record_audit(db, "account_role_changed", "user", user_id, {"from": row["role"], "to": role})
        return public_user(user_by_id(user_id))

    @app.get("/api/auth/audit-log")
    @require_auth("admin")
    def audit_log():
        admin_active()
        limit = min(integer(request.args.get("limit", 200), "limit", min_value=1), 1000)
        return {
            "items": [
                dict(r) for r in get_db().execute("SELECT * FROM audit_log ORDER BY audit_id DESC LIMIT ?", (limit,))
            ]
        }

    return app


app = create_app()
if __name__ == "__main__":
    run(app, 5001)
