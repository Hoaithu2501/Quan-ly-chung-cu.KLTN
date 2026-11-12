from functools import wraps
import jwt
from flask import g, request
from shared.config import secret
from shared.web import APIError, secure_compare

SERVICE_USER = {"user_id": 0, "role": "service", "username": "service"}


def is_internal():
    provided = request.headers.get("X-Service-Token", "")
    return bool(provided) and secure_compare(provided, secret("SERVICE_TOKEN"))


def require_internal(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        if not is_internal():
            raise APIError("Yêu cầu xác thực service.", 401)
        g.user = SERVICE_USER
        return function(*args, **kwargs)

    return wrapped


def require_auth(*roles):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                raise APIError("Vui lòng đăng nhập.", 401)
            try:
                payload = jwt.decode(
                    header[7:],
                    secret("JWT_SECRET"),
                    algorithms=["HS256"],
                    issuer="qlcc-auth",
                    options={"require": ["sub", "exp", "iat", "role"]},
                )
                g.user = {
                    "user_id": int(payload["sub"]),
                    "role": payload["role"],
                    "username": payload.get("username", ""),
                    "token_version": payload.get("ver", 0),
                }
            except (jwt.InvalidTokenError, ValueError, KeyError):
                raise APIError("Phiên đăng nhập không hợp lệ hoặc đã hết hạn.", 401)
            # Auth re-checks status and token version, so locks and password changes apply at once.
            if not request.path.startswith("/api/auth/"):
                from shared.http import call_service

                result = call_service("auth", "/api/auth/me")
                g.user = result["user"]
            if roles and g.user["role"] not in roles:
                raise APIError("Bạn không có quyền thực hiện thao tác này.", 403)
            return function(*args, **kwargs)

        return wrapped

    return decorate


def auth_or_internal(*roles):
    def decorate(function):
        authenticated = require_auth(*roles)(function)

        @wraps(function)
        def wrapped(*args, **kwargs):
            if is_internal():
                g.user = SERVICE_USER
                return function(*args, **kwargs)
            return authenticated(*args, **kwargs)

        return wrapped

    return decorate
