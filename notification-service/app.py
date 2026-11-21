"""Scoped announcements, read receipts and optional Firebase Cloud Messaging."""

from flask import g

from shared.auth import require_auth, require_internal
from shared.db import get_db, placeholders
from shared.domain import apartment_access, enum, one, resident_profile, text
from shared.http import call_service
from shared.firebase_push import push_settings, deliver
from shared.web import APIError, body, create_app as service_app, integer, required, run


STAFF_AUDIENCE = "EXISTS (SELECT 1 FROM notification_staff_audience a WHERE a.notification_id=n.notification_id)"
READ_BY_RESIDENT = (
    "COALESCE((SELECT MAX(l.is_read) FROM notification_logs l "
    "WHERE l.notification_id=n.notification_id AND l.resident_id=?),0)"
)
READ_BY_STAFF = (
    "EXISTS (SELECT 1 FROM notification_staff_reads r WHERE r.notification_id=n.notification_id AND r.user_id=?)"
)


def create_app():
    app = service_app("notification")

    @app.get("/api/notifications")
    @require_auth("admin", "resident", "technician")
    def notifications():
        db = get_db()
        profile = resident_profile() if g.user["role"] == "resident" else None
        args = [profile["resident_id"] if profile else g.user["user_id"]]
        query = (
            "SELECT n.*,c.apartment_id AS related_apartment_id,c.apartment_code AS related_apartment_code,"
            "c.invoice_created_at,c.paid_at,"
            "(SELECT a.target_role FROM notification_audience a WHERE a.notification_id=n.notification_id) AS target_role,"
            "(SELECT a.resident_id FROM notification_resident_audience a WHERE a.notification_id=n.notification_id) AS target_resident_id,"
            f"{READ_BY_RESIDENT if profile else READ_BY_STAFF} AS is_read FROM notifications n "
            "LEFT JOIN notification_billing_context c ON c.notification_id=n.notification_id"
        )
        if profile:
            ids = profile.get("apartment_ids", [])
            query += " WHERE (n.type='general' OR EXISTS (SELECT 1 FROM notification_resident_audience a WHERE a.notification_id=n.notification_id AND a.resident_id=?)"
            args.append(profile["resident_id"])
            if ids:
                query += (
                    " OR (n.target_apartment_id IN ("
                    + placeholders(ids)
                    + ") AND NOT EXISTS (SELECT 1 FROM notification_resident_audience a WHERE a.notification_id=n.notification_id))"
                )
                args.extend(ids)
            query += ")"
            # A new account only sees announcements published after it was created.
            created_at = g.user.get("created_at")
            if created_at:
                query += " AND n.created_at>=?"
                args.append(created_at)
        elif g.user["role"] == "technician":
            query += f" WHERE n.type='general' OR n.created_by=? OR {STAFF_AUDIENCE}"
            args.append(g.user["user_id"])
        else:
            # Automatic notices addressed to one resident (a reply to their request, their apartment
            # confirmed) report what management itself just did, so they stay out of its inbox.
            # Notices a manager wrote to a resident stay listed.
            query += (
                " WHERE n.created_by IS NOT NULL OR NOT EXISTS "
                "(SELECT 1 FROM notification_resident_audience a WHERE a.notification_id=n.notification_id)"
            )
        return {
            "items": [dict(r) for r in db.execute(query + " ORDER BY n.created_at DESC,n.notification_id DESC", args)]
        }

    def notification_values(data):
        required(data, "type", "title", "content")
        kind = enum(data["type"], ("general", "private"), "type")
        target = None
        target_role = data.get("target_role")
        target_resident = data.get("target_resident_id")
        if target_role is not None:
            enum(target_role, ("admin", "technician"), "target_role")
            if kind != "private" or data.get("target_apartment_id") is not None or target_resident is not None:
                raise APIError("Thông báo cho Ban quản lý phải là thông báo riêng và không chọn căn hộ.")
        if target_resident is not None:
            if kind != "private" or target_role is not None or data.get("target_apartment_id") is not None:
                raise APIError("Thông báo cho một cư dân phải là thông báo riêng và chỉ chọn người nhận đó.")
            resident_id = integer(target_resident, "target_resident_id", min_value=1)
            call_service("resident", f"/api/residents/{resident_id}", internal=True)
        if kind == "private" and target_role is None and target_resident is None:
            required(data, "target_apartment_id")
            target = apartment_access(data["target_apartment_id"])
        return kind, text(data["title"], "Tiêu đề", limit=250), text(data["content"], "Nội dung", limit=10000), target

    def store_audience(db, notification_id, data):
        if data.get("target_role") == "admin":
            db.execute(
                "INSERT INTO notification_audience(notification_id,target_role) VALUES (?,?)",
                (notification_id, data["target_role"]),
            )
        if data.get("target_role") == "technician" or data.get("notify_staff"):
            db.execute("INSERT INTO notification_staff_audience(notification_id) VALUES (?)", (notification_id,))
        if data.get("target_resident_id") is not None:
            db.execute(
                "INSERT INTO notification_resident_audience(notification_id,resident_id) VALUES (?,?)",
                (notification_id, int(data["target_resident_id"])),
            )

    def send_push(notification):
        settings = push_settings()
        if not settings["configured"]:
            return {"configured": False, "sent": 0, "failed": 0}
        # The inbox is committed first: an FCM outage must not lose it.
        try:
            db = get_db()
            tokens = [dict(row) for row in db.execute("SELECT token,user_id,resident_id FROM notification_push_tokens")]
            if not tokens:
                return {"configured": True, "sent": 0, "failed": 0}
            users = {
                u["user_id"]: u
                for u in call_service("auth", "/api/auth/users", internal=True)["items"]
                if u["status"] == "active"
            }
            tokens = [row for row in tokens if row["user_id"] in users]

            def staff(row):
                return notification.get("notify_staff") and users[row["user_id"]]["role"] in ("admin", "technician")

            if notification.get("target_role"):
                tokens = [
                    row for row in tokens if users[row["user_id"]]["role"] == notification["target_role"] or staff(row)
                ]
            elif notification["type"] == "private":
                residents = call_service("resident", "/api/residents", internal=True)["items"]
                target = notification.get("target_resident_id")
                eligible = {
                    (r["user_id"], r["resident_id"])
                    for r in residents
                    if (
                        r["resident_id"] == target
                        if target is not None
                        else notification["target_apartment_id"] in r.get("apartment_ids", [])
                    )
                }
                tokens = [
                    row
                    for row in tokens
                    if staff(row)
                    or (
                        users[row["user_id"]]["role"] == "resident" and (row["user_id"], row["resident_id"]) in eligible
                    )
                ]
            result = deliver(settings, notification, tokens, db)
            if result["failed"]:
                app.logger.warning("Firebase: %s delivery failures; inbox preserved.", result["failed"])
            return result
        except Exception:
            app.logger.warning("Firebase delivery unavailable; notification remains in the inbox.")
            return {
                "configured": True,
                "sent": 0,
                "failed": 1,
                "error": "Không gửi được push; thông báo đã lưu trong hệ thống.",
            }

    def published(db, notification_id, data, **extra):
        """The stored notification with its audience attached, after trying to push it."""
        result = one(db, "notifications", "notification_id", notification_id)
        result["target_role"] = data.get("target_role")
        target_resident = data.get("target_resident_id")
        result["target_resident_id"] = None if target_resident is None else int(target_resident)
        result["notify_staff"] = bool(data.get("notify_staff"))
        result.update(extra)
        result["push"] = send_push(result)
        return result, 201

    @app.post("/api/notifications")
    @require_auth("admin")
    def add_notification():
        data = body()
        values = notification_values(data)
        db = get_db()
        cursor = db.execute(
            "INSERT INTO notifications(type,title,content,target_apartment_id,created_by) VALUES (?,?,?,?,?)",
            (*values, g.user["user_id"]),
        )
        store_audience(db, cursor.lastrowid, data)
        db.commit()
        return published(db, cursor.lastrowid, data)

    @app.post("/api/notifications/events")
    @require_internal
    def notification_event():
        data = body()
        required(data, "event_id")
        event_id = text(data["event_id"], "event_id", limit=200)
        db = get_db()
        previous = db.execute(
            "SELECT notification_id FROM notification_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if previous:
            return {"notification_id": previous["notification_id"], "duplicate": True}
        values = notification_values(data)
        context = data.get("billing_context")
        context_values = None
        if context is not None:
            if not isinstance(context, dict):
                raise APIError("Thông tin hóa đơn không hợp lệ")
            apartment_id = integer(context.get("apartment_id"), "apartment_id", min_value=1)
            apartment = call_service("resident", f"/api/apartments/{apartment_id}", internal=True)
            context_values = (
                apartment_id,
                apartment["code"],
                context.get("invoice_created_at"),
                context.get("paid_at"),
            )
        db.execute("BEGIN IMMEDIATE")
        previous = db.execute(
            "SELECT notification_id FROM notification_events WHERE event_id=?", (event_id,)
        ).fetchone()
        if previous:
            db.rollback()
            return {"notification_id": previous["notification_id"], "duplicate": True}
        cursor = db.execute(
            "INSERT INTO notifications(type,title,content,target_apartment_id,created_by) VALUES (?,?,?,?,NULL)", values
        )
        identifier = cursor.lastrowid
        store_audience(db, identifier, data)
        if context_values:
            db.execute(
                "INSERT INTO notification_billing_context "
                "(notification_id,apartment_id,apartment_code,invoice_created_at,paid_at) VALUES (?,?,?,?,?)",
                (identifier, *context_values),
            )
        db.execute("INSERT INTO notification_events(event_id,notification_id) VALUES (?,?)", (event_id, identifier))
        db.commit()
        return published(db, identifier, data, duplicate=False)

    @app.post("/api/notifications/<int:notification_id>/read")
    @require_auth("admin", "resident", "technician")
    def mark_read(notification_id):
        db = get_db()
        notification = one(db, "notifications", "notification_id", notification_id)
        if g.user["role"] != "resident":
            visible = (
                g.user["role"] == "admin"
                or notification["type"] == "general"
                or notification["created_by"] == g.user["user_id"]
                or db.execute(
                    "SELECT 1 FROM notification_staff_audience WHERE notification_id=?", (notification_id,)
                ).fetchone()
            )
            if not visible:
                raise APIError("Bạn không có quyền truy cập thông báo này.", 403)
            db.execute(
                "INSERT OR IGNORE INTO notification_staff_reads(notification_id,user_id) VALUES (?,?)",
                (notification_id, g.user["user_id"]),
            )
            db.commit()
            return {"notification_id": notification_id, "is_read": True}
        profile = resident_profile()
        audience = db.execute(
            "SELECT resident_id FROM notification_resident_audience WHERE notification_id=?", (notification_id,)
        ).fetchone()
        allowed = (
            audience["resident_id"] == profile["resident_id"]
            if audience
            else notification["type"] == "general"
            or notification["target_apartment_id"] in profile.get("apartment_ids", [])
        )
        if not allowed:
            raise APIError("Bạn không có quyền truy cập thông báo này.", 403)
        db.execute("BEGIN IMMEDIATE")
        cursor = db.execute(
            "UPDATE notification_logs SET is_read=1 WHERE notification_id=? AND resident_id=?",
            (notification_id, profile["resident_id"]),
        )
        if cursor.rowcount == 0:
            db.execute(
                "INSERT INTO notification_logs(notification_id,resident_id,is_read) VALUES (?,?,1)",
                (notification_id, profile["resident_id"]),
            )
        db.commit()
        return {"notification_id": notification_id, "is_read": True}

    @app.get("/api/notifications/<int:notification_id>/receipts")
    @require_auth("admin")
    def receipts(notification_id):
        one(get_db(), "notifications", "notification_id", notification_id)
        return {
            "items": [
                dict(row)
                for row in get_db().execute(
                    "SELECT * FROM notification_logs WHERE notification_id=? ORDER BY sent_at DESC", (notification_id,)
                )
            ]
        }

    @app.get("/api/notifications/push-config")
    @require_auth("admin", "resident", "technician")
    def push_config():
        settings = push_settings()
        result = {"configured": settings["configured"], "config": settings["config"]}
        if g.user["role"] == "admin":
            result["errors"] = settings["errors"]
        return result

    @app.post("/api/notifications/push-tokens")
    @require_auth("admin", "resident", "technician")
    def register_push():
        data = body()
        required(data, "token")
        token = text(data["token"], "token", limit=4096)
        profile = resident_profile() if g.user["role"] == "resident" else None
        db = get_db()
        db.execute(
            "INSERT INTO notification_push_tokens(token,user_id,resident_id) VALUES (?,?,?) ON CONFLICT(token) DO UPDATE SET user_id=excluded.user_id,resident_id=excluded.resident_id",
            (token, g.user["user_id"], profile["resident_id"] if profile else None),
        )
        db.execute(
            "INSERT INTO notification_push_roles(user_id,role) VALUES (?,?) ON CONFLICT(user_id) DO UPDATE SET role=excluded.role",
            (g.user["user_id"], g.user["role"]),
        )
        db.commit()
        return {"registered": True}, 201

    @app.delete("/api/notifications/push-tokens")
    @require_auth("admin", "resident", "technician")
    def unregister_push():
        data = body()
        required(data, "token")
        token = text(data["token"], "token", limit=4096)
        db = get_db()
        db.execute("DELETE FROM notification_push_tokens WHERE token=? AND user_id=?", (token, g.user["user_id"]))
        db.commit()
        return {"removed": True}

    return app


app = create_app()
if __name__ == "__main__":
    run(app, 5006)
