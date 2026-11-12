import hmac
import os
import re
import sqlite3
from datetime import date
from flask import Flask, jsonify, request
from werkzeug.exceptions import HTTPException
from shared.db import close_db, get_db


class APIError(Exception):
    def __init__(self, message, status=400):
        self.message, self.status = message, status
        super().__init__(message)


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise APIError("Nội dung yêu cầu phải là JSON object.")
    return data


def required(data, *keys):
    for key in keys:
        if key not in data or data[key] is None or (isinstance(data[key], str) and not data[key].strip()):
            raise APIError(f"Thiếu thông tin: {key}")


def integer(value, name, min_value=0):
    if isinstance(value, bool) or not re.fullmatch(r"-?\d+", str(value)):
        raise APIError(f"{name} phải là số nguyên.")
    number = int(value)
    if number < min_value or number > 9_000_000_000_000:
        raise APIError(f"{name} không nằm trong khoảng hợp lệ.")
    return number


def iso_date(value, name="date"):
    try:
        if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            raise ValueError()
        date.fromisoformat(value)
        return value
    except (TypeError, ValueError):
        raise APIError(f"{name} phải có định dạng YYYY-MM-DD hợp lệ.")


def person_name(value):
    if not isinstance(value, str) or not 2 <= len(value.strip()) <= 50:
        raise APIError("Họ tên phải có từ 2 đến 50 ký tự.")
    return value.strip()


def secure_compare(provided, expected):
    # compare_digest raises TypeError on non-ASCII str, and headers are caller-controlled.
    return hmac.compare_digest(
        str(provided).encode("utf-8", "surrogatepass"), str(expected).encode("utf-8", "surrogatepass")
    )


def client_ip():
    """Caller address stamped by the gateway; domain services are never public."""
    return request.headers.get("X-Client-IP") or request.remote_addr or "unknown"


def create_app(name):
    app = Flask(name)
    app.json.ensure_ascii = False
    app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024
    app.teardown_appcontext(close_db)

    @app.errorhandler(APIError)
    def api_error(error):
        return jsonify(error=error.message), error.status

    @app.errorhandler(sqlite3.IntegrityError)
    def integrity_error(error):
        app.logger.info("Integrity constraint: %s", error)
        return jsonify(error="Dữ liệu trùng lặp hoặc vi phạm ràng buộc."), 409

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.description), error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        app.logger.exception("Unhandled request error")
        return jsonify(error="Không thể xử lý yêu cầu. Vui lòng thử lại."), 500

    @app.after_request
    def headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["Referrer-Policy"] = "same-origin"
        # API data stays uncached; static files keep the policy set when they were served.
        response.headers.setdefault("Cache-Control", "no-store")
        return response

    @app.get("/health")
    def health():
        if name != "gateway":
            try:
                get_db().execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
            except sqlite3.Error:
                app.logger.exception("Database health check failed")
                return {"service": name, "status": "unavailable", "database": "unavailable"}, 503
        return {"service": name, "status": "ok"}

    @app.get("/openapi.json")
    def openapi():
        from shared.openapi import enrich_operation, SECURITY_SCHEMES

        paths = {}
        for rule in app.url_map.iter_rules():
            if not rule.rule.startswith("/api/"):
                continue
            path = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", rule.rule)
            operations = {}
            for method in sorted(rule.methods - {"OPTIONS", "HEAD"}):
                operation = {
                    "summary": rule.endpoint.replace("_", " "),
                    "security": [{"BearerAuth": []}],
                    "responses": {
                        "200": {"description": "Success"},
                        "400": {"description": "Validation error"},
                        "401": {"description": "Unauthorized"},
                        "403": {"description": "Forbidden"},
                    },
                }
                if rule.arguments:
                    operation["parameters"] = [
                        {"name": a, "in": "path", "required": True, "schema": {"type": "string"}}
                        for a in rule.arguments
                    ]
                if method in {"POST", "PATCH", "PUT"}:
                    operation["requestBody"] = {
                        "content": {"application/json": {"schema": {"type": "object", "additionalProperties": True}}}
                    }
                operations[method.lower()] = enrich_operation(path, method, operation)
            paths.setdefault(path, {}).update(operations)
        return {
            "openapi": "3.0.3",
            "info": {"title": name + " API", "version": "1.0.0"},
            "paths": paths,
            "components": {"securitySchemes": SECURITY_SCHEMES},
        }

    @app.get("/docs")
    def docs():
        return """<!doctype html><html lang="vi"><head><meta charset="utf-8"><title>API Explorer</title>
<link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.29.0/swagger-ui.css"></head>
<body><div id="swagger-ui"></div><script src="https://unpkg.com/swagger-ui-dist@5.29.0/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({url:'./openapi.json',dom_id:'#swagger-ui',persistAuthorization:true});</script></body></html>"""

    return app


def run(app, port):
    from waitress import serve

    serve(app, host=os.getenv("HOST", "127.0.0.1"), port=port, threads=8)
