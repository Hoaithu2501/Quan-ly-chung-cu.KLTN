"""Technician assignments and repair/service-restoration workflows."""
from flask import g, request

from shared.auth import require_auth, require_internal
from shared.db import get_db
from shared.domain import apartment_access, enum, one, resident_profile, text
from shared.http import call_service
from shared.web import APIError, body, create_app as service_app, integer, required, run


def create_app():
    app = service_app("maintenance")

    @app.get("/api/maintenance/technicians")
    @require_auth("admin", "technician")
    def technicians():
        db = get_db()
        query = "SELECT t.*, (SELECT COUNT(*) FROM maintenance_tickets m WHERE m.technician_id=t.technician_id AND m.status<>'completed') AS open_tickets FROM technicians t"
        args = []
        if g.user["role"] == "technician":
            query += " WHERE t.technician_id=(SELECT MIN(technician_id) FROM technicians WHERE user_id=?)"
            args.append(g.user["user_id"])
        return {"items": [dict(r) for r in db.execute(query + " ORDER BY full_name", args)]}

    def technician_values(data, old=None):
        merged = dict(old or {})
        merged.update(data)
        required(merged, "user_id", "full_name", "specialty")
        user_id = integer(merged["user_id"], "user_id", min_value=1)
        users = call_service("auth", "/api/auth/users")["items"]
        if not any(u["user_id"] == user_id and u["role"] == "technician" for u in users):
            raise APIError("Tài khoản phải có vai trò kỹ thuật viên.")
        duplicate = get_db().execute("SELECT technician_id FROM technicians WHERE user_id=? AND technician_id<>?", (user_id, (old or {}).get("technician_id", 0))).fetchone()
        if duplicate:
            raise APIError("Tài khoản đã có hồ sơ kỹ thuật viên.", 409)
        return user_id, text(merged["full_name"], "Họ tên", limit=200), enum(merged["specialty"], ("parking", "payment", "general"), "specialty")

    @app.post("/api/maintenance/technicians")
    @require_auth("admin")
    def add_technician():
        values = technician_values(body())
        db = get_db()
        cursor = db.execute("INSERT INTO technicians(user_id,full_name,specialty) VALUES (?,?,?)", values)
        db.commit()
        return one(db, "technicians", "technician_id", cursor.lastrowid), 201

    @app.patch("/api/maintenance/technicians/<int:technician_id>")
    @require_auth("admin")
    def update_technician(technician_id):
        db = get_db()
        old = one(db, "technicians", "technician_id", technician_id)
        values = technician_values(body(), old)
        db.execute("UPDATE technicians SET user_id=?,full_name=?,specialty=? WHERE technician_id=?", (*values, technician_id))
        db.commit()
        return one(db, "technicians", "technician_id", technician_id)

    @app.get("/api/maintenance/tickets")
    @require_auth("admin", "resident", "technician")
    def tickets():
        query = "SELECT m.*,t.full_name AS technician_name,c.outcome FROM maintenance_tickets m LEFT JOIN technicians t ON t.technician_id=m.technician_id LEFT JOIN cut_service_resolutions c ON c.ticket_id=m.ticket_id WHERE 1=1"
        args = []
        if g.user["role"] == "technician":
            # The supplied seed links distinct people to repeated user IDs.
            # Only the canonical profile can use that login until repaired.
            query += " AND t.technician_id=(SELECT MIN(technician_id) FROM technicians WHERE user_id=?)"
            args.append(g.user["user_id"])
        elif g.user["role"] == "resident":
            ids = resident_profile().get("apartment_ids", [])
            if not ids:
                return {"items": []}
            query += " AND m.apartment_id IN (" + ",".join("?" for _ in ids) + ")"
            args.extend(ids)
        if request.args.get("status"):
            query += " AND m.status=?"
            args.append(enum(request.args["status"], ("pending", "in_progress", "completed"), "status"))
        return {"items": [dict(r) for r in get_db().execute(query + " ORDER BY CASE m.status WHEN 'pending' THEN 0 WHEN 'in_progress' THEN 1 ELSE 2 END,m.ticket_id DESC", args)]}

    @app.post("/api/maintenance/tickets")
    @require_auth("admin", "resident")
    def add_ticket():
        data = body()
        required(data, "description")
        role = g.user["role"]
        apartment_id = data.get("apartment_id")
        if apartment_id is None and data.get("apartment_code"):
            code_input = str(data["apartment_code"]).strip().upper()
            try:
                apts = call_service("resident", "/api/apartments", internal=True).get("items", [])
                found = next((a for a in apts if a["code"].upper() == code_input), None)
                if found:
                    apartment_id = found["apartment_id"]
            except Exception:
                pass
        if apartment_id is not None:
            apartment_id = apartment_access(apartment_id)
        elif role == "resident":
            raise APIError("Cần chọn căn hộ cho phiếu yêu cầu.")
        kinds = ("repair", "maintenance", "cut_service", "restore_service") if role == "admin" else ("repair", "maintenance")
        kind = enum(data.get("type", "repair"), kinds, "type")
        priority = enum(data.get("priority", "medium"), ("low", "medium", "high"), "priority")
        technician_id = data.get("technician_id")
        if technician_id is not None:
            if role != "admin":
                raise APIError("Chỉ Ban quản lý được phân công kỹ thuật viên.", 403)
            technician_id = integer(technician_id, "technician_id", min_value=1)
            one(get_db(), "technicians", "technician_id", technician_id)
        db = get_db()
        cursor = db.execute("INSERT INTO maintenance_tickets(apartment_id,technician_id,type,description,priority) VALUES (?,?,?,?,?)", (apartment_id, technician_id, kind, text(data["description"], "Nội dung"), priority))
        db.commit()
        return one(db, "maintenance_tickets", "ticket_id", cursor.lastrowid), 201

    @app.patch("/api/maintenance/tickets/<int:ticket_id>")
    @require_auth("admin", "technician")
    def update_ticket(ticket_id):
        db = get_db()
        # Serialize with settlement events so a stale technician update cannot
        # reopen a cut ticket that payment just cancelled.
        db.execute("BEGIN IMMEDIATE")
        old = one(db, "maintenance_tickets", "ticket_id", ticket_id)
        data = body()
        if g.user["role"] == "technician":
            assigned = db.execute("SELECT 1 FROM technicians WHERE technician_id=? AND technician_id=(SELECT MIN(technician_id) FROM technicians WHERE user_id=?)", (old["technician_id"], g.user["user_id"])).fetchone()
            if not assigned:
                raise APIError("Bạn chỉ được cập nhật công việc đã được phân công.", 403)
            if any(key != "status" for key in data):
                raise APIError("Kỹ thuật viên chỉ được thay đổi trạng thái công việc.", 403)
        if old["status"] == "completed":
            raise APIError("Phiếu đã đóng. Hãy tạo phiếu mới nếu cần xử lý tiếp.", 409)
        new_status = enum(data.get("status", old["status"]), ("pending", "in_progress", "completed"), "status")
        if old["status"] == "pending" and new_status == "completed":
            raise APIError("Cần nhận xử lý phiếu trước khi hoàn thành.", 409)
        if old["status"] == "in_progress" and new_status == "pending":
            raise APIError("Phiếu đang xử lý không thể quay lại trạng thái chờ.", 409)
        technician_id = data.get("technician_id", old["technician_id"])
        if technician_id is not None:
            technician_id = integer(technician_id, "technician_id", min_value=1)
            one(db, "technicians", "technician_id", technician_id)
        if new_status != "pending" and technician_id is None:
            raise APIError("Cần phân công kỹ thuật viên trước khi xử lý.")
        description = text(data.get("description", old["description"]), "Nội dung")
        priority = enum(data.get("priority", old["priority"]), ("low", "medium", "high"), "priority")
        db.execute("UPDATE maintenance_tickets SET technician_id=?,description=?,priority=?,status=?,completed_at=CASE WHEN ?='completed' THEN CURRENT_TIMESTAMP ELSE NULL END WHERE ticket_id=?", (technician_id, description, priority, new_status, new_status, ticket_id))
        db.commit()
        return one(db, "maintenance_tickets", "ticket_id", ticket_id)

    @app.post("/api/maintenance/events")
    @require_internal
    def billing_event():
        data = body()
        required(data, "event_id", "event_type", "apartment_id", "all_debts_settled")
        event_id = text(data["event_id"], "event_id", limit=200)
        enum(data["event_type"], ("invoice_settled",), "event_type")
        apartment_id = integer(data["apartment_id"], "apartment_id", min_value=1)
        if not isinstance(data["all_debts_settled"], bool):
            raise APIError("all_debts_settled phải là boolean.")
        db = get_db()
        # Acquire SQLite's write lock before the idempotency read.
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM maintenance_events WHERE event_id=?", (event_id,)).fetchone():
            db.rollback()
            return {"event_id": event_id, "duplicate": True}
        db.execute("INSERT INTO maintenance_events(event_id,event_type,apartment_id) VALUES (?,?,?)", (event_id, "invoice_settled", apartment_id))
        cancelled, restore_id = 0, None
        if data["all_debts_settled"]:
            cuts = db.execute("SELECT m.* FROM maintenance_tickets m LEFT JOIN cut_service_resolutions c ON c.ticket_id=m.ticket_id WHERE m.apartment_id=? AND m.type='cut_service' AND c.ticket_id IS NULL", (apartment_id,)).fetchall()
            needs_restore = False
            for cut in cuts:
                # A started disconnection may already have interrupted supply, so
                # request restoration even if its completion was not recorded.
                started = cut["status"] in ("completed", "in_progress")
                outcome = "restore_requested" if started else "cancelled"
                needs_restore = needs_restore or started
                if cut["status"] != "completed":
                    db.execute("UPDATE maintenance_tickets SET status='completed',completed_at=CURRENT_TIMESTAMP,description=COALESCE(description,'') || ? WHERE ticket_id=?", ("\nĐã thanh toán: dừng yêu cầu cắt dịch vụ.", cut["ticket_id"]))
                    cancelled += 1
                db.execute("INSERT INTO cut_service_resolutions(ticket_id,event_id,outcome) VALUES (?,?,?)", (cut["ticket_id"], event_id, outcome))
            if needs_restore:
                existing = db.execute("SELECT ticket_id FROM maintenance_tickets WHERE apartment_id=? AND type='restore_service' AND status<>'completed' ORDER BY ticket_id DESC LIMIT 1", (apartment_id,)).fetchone()
                if existing:
                    restore_id = existing["ticket_id"]
                else:
                    cursor = db.execute("INSERT INTO maintenance_tickets(apartment_id,type,description,priority,status) VALUES (?,'restore_service',?,'high','pending')", (apartment_id, "Đã thanh toán các hóa đơn quá hạn. Kiểm tra và khôi phục dịch vụ cho căn hộ."))
                    restore_id = cursor.lastrowid
        db.commit()
        return {"event_id": event_id, "duplicate": False, "cancelled": cancelled, "restore_ticket_id": restore_id}, 201

    return app


app = create_app()
if __name__ == "__main__":
    run(app, 5005)
