"""Residents submit complaints/registrations; management records resolutions."""
import json
import uuid

from flask import g, request

from shared.auth import require_auth
from shared.db import get_db
from shared.domain import enum, one, resident_profile, text
from shared.http import call_service
from shared.web import APIError, body, create_app as service_app, integer, required, run


def dispatch_outbox(limit=25):
    """Delivery is retried with the same event id after a lost response or outage."""
    db = get_db()
    events = db.execute("SELECT event_id,payload FROM complaint_outbox WHERE delivered_at IS NULL "
                        "ORDER BY attempts,created_at,event_id LIMIT ?", (limit,)).fetchall()
    delivered = 0
    for event in events:
        try:
            call_service("notification", "/api/notifications/events", method="POST",
                         json=json.loads(event["payload"]), internal=True)
        except Exception as exc:
            db.execute("UPDATE complaint_outbox SET attempts=attempts+1,last_error=? WHERE event_id=?",
                       (type(exc).__name__, event["event_id"]))
        else:
            db.execute("UPDATE complaint_outbox SET delivered_at=CURRENT_TIMESTAMP,attempts=attempts+1,"
                       "last_error=NULL WHERE event_id=?", (event["event_id"],))
            delivered += 1
        db.commit()
    return delivered


def enqueue_reply(complaint):
    status_names = {"pending": "Chờ xử lý", "processing": "Đang xử lý",
                    "resolved": "Đã giải quyết", "rejected": "Từ chối"}
    identifier = complaint["complaint_id"]
    reply = complaint["response"]
    excerpt = reply[:3000] + ("…" if len(reply) > 3000 else "")
    payload = {"event_id": "complaint:reply:" + uuid.uuid4().hex, "type": "private",
               "target_resident_id": complaint["resident_id"],
               "title": f"Ban quản lý đã phản hồi yêu cầu #YC{identifier}",
               "content": f"Yêu cầu #YC{identifier} — {status_names[complaint['status']]}.\n"
                          f"Phản hồi của Ban quản lý:\n{excerpt}\n\n"
                          "Bạn vào Khiếu nại & đăng ký, mở yêu cầu này để xem đầy đủ phản hồi."}
    get_db().execute("INSERT INTO complaint_outbox(event_id,complaint_id,payload) VALUES (?,?,?)",
                     (payload["event_id"], identifier, json.dumps(payload, ensure_ascii=False)))


def create_app():
    app = service_app("complaint")

    @app.get("/api/complaints")
    @require_auth("admin", "resident")
    def complaints():
        query, args = "SELECT * FROM complaints WHERE 1=1", []
        if g.user["role"] == "resident":
            query += " AND resident_id=?"
            args.append(resident_profile()["resident_id"])
        if request.args.get("status"):
            query += " AND status=?"
            args.append(enum(request.args["status"], ("pending", "processing", "resolved", "rejected"), "status"))
        return {"items": [dict(r) for r in get_db().execute(query + " ORDER BY complaint_id DESC", args)]}

    @app.post("/api/complaints")
    @require_auth("admin", "resident")
    def add_complaint():
        data = body()
        required(data, "type", "content")
        if g.user["role"] == "resident":
            resident_id = resident_profile()["resident_id"]
            if data.get("resident_id") is not None and integer(data["resident_id"], "resident_id", min_value=1) != resident_id:
                raise APIError("Bạn chỉ được tạo đơn cho chính mình.", 403)
        else:
            required(data, "resident_id")
            resident_id = integer(data["resident_id"], "resident_id", min_value=1)
            residents = call_service("resident", "/api/residents", internal=True)["items"]
            if not any(r["resident_id"] == resident_id for r in residents):
                raise APIError("Cư dân không tồn tại.", 404)
        kind = enum(data["type"], ("complaint", "registration"), "type")
        category = text(data.get("category"), "Danh mục", limit=150, optional=True)
        content = text(data["content"], "Nội dung", limit=10000)
        db = get_db()
        cursor = db.execute("INSERT INTO complaints(resident_id,type,category,content) VALUES (?,?,?,?)", (resident_id, kind, category, content))
        db.commit()
        return one(db, "complaints", "complaint_id", cursor.lastrowid), 201

    @app.patch("/api/complaints/<int:complaint_id>")
    @require_auth("admin")
    def update_complaint(complaint_id):
        data = body()
        if set(data) - {"status", "response"}:
            raise APIError("Chỉ được cập nhật trạng thái và phản hồi của yêu cầu.")
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            old = one(db, "complaints", "complaint_id", complaint_id)
            status = enum(data.get("status", old["status"]), ("pending", "processing", "resolved", "rejected"), "status")
            if old["status"] in ("resolved", "rejected") and status != old["status"]:
                raise APIError("Đơn đã đóng. Cư dân có thể tạo đơn mới nếu cần.", 409)
            if old["status"] == "processing" and status == "pending":
                raise APIError("Đơn đang xử lý không thể trở về trạng thái chờ.", 409)
            response = text(data.get("response", old["response"]), "Phản hồi", limit=10000,
                            optional=status not in ("resolved", "rejected"))
            if old["response"] and not response:
                raise APIError("Vui lòng nhập nội dung phản hồi thay cho việc xóa phản hồi đã gửi.")
            db.execute("UPDATE complaints SET status=?,response=?,resolved_at=CASE WHEN ? IN ('resolved','rejected') THEN COALESCE(resolved_at,CURRENT_TIMESTAMP) ELSE NULL END WHERE complaint_id=?", (status, response, status, complaint_id))
            updated = one(db, "complaints", "complaint_id", complaint_id)
            if response and response != (old["response"] or "").strip():
                enqueue_reply(updated)
        # A delivery failure never undoes the management response just committed.
        try:
            dispatch_outbox()
        except Exception:
            app.logger.warning("Reply saved; notification delivery will retry.")
        return updated

    app.extensions["complaint_jobs"] = {"outbox": dispatch_outbox}
    return app


app = create_app()
if __name__ == "__main__":
    from scheduler import start_scheduler
    start_scheduler(app)
    run(app, 5007)
