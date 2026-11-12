"""Technician assignments and repair/service-restoration workflows."""

import uuid

from flask import g, request

from shared.auth import require_auth, require_internal
from shared.db import get_db, placeholders
from shared.domain import apartment_access, enum, notify, one, resident_profile, text
from shared.http import call_service
from shared.web import APIError, body, create_app as service_app, integer, required, run

# The seed links several profiles to one login; only the lowest id is that person's own.
OWN_TECHNICIAN_ID = "(SELECT MIN(technician_id) FROM technicians WHERE user_id=?)"
TICKET_STATUSES = ("pending", "in_progress", "completed")
PRIORITIES = ("low", "medium", "high")
TICKET_KINDS = {
    "repair": "sửa chữa",
    "maintenance": "bảo trì",
    "cut_service": "cắt dịch vụ",
    "restore_service": "cấp lại dịch vụ",
}
STATUS_NAMES = {"pending": "Chờ xử lý", "in_progress": "Đang xử lý", "completed": "Hoàn thành"}


def notify_ticket(ticket, title, detail):
    """The apartment's residents, management and every technician see the same ticket update."""
    audience = (
        {"target_apartment_id": ticket["apartment_id"]}
        if ticket["apartment_id"] is not None
        else {"target_role": "admin"}
    )
    summary = (ticket["description"] or "")[:300]
    notify(
        f"ticket:{ticket['ticket_id']}:{uuid.uuid4().hex}",
        title=title,
        content=f"{detail}\nNội dung: {summary}",
        notify_staff=True,
        **audience,
    )


def create_app():
    app = service_app("maintenance")

    @app.get("/api/maintenance/technicians")
    @require_auth("admin", "technician")
    def technicians():
        db = get_db()
        query = "SELECT t.*, (SELECT COUNT(*) FROM maintenance_tickets m WHERE m.technician_id=t.technician_id AND m.status<>'completed') AS open_tickets FROM technicians t"
        args = []
        query += " WHERE t.active=1"
        if g.user["role"] == "technician":
            query += f" AND t.technician_id={OWN_TECHNICIAN_ID}"
            args.append(g.user["user_id"])
        return {"items": [dict(r) for r in db.execute(query + " ORDER BY full_name", args)]}

    @app.put("/api/maintenance/technicians/accounts/<int:user_id>")
    @require_internal
    def sync_technician_account(user_id):
        """Called when an account gains or loses the technician role; tickets keep their history."""
        data = body()
        required(data, "full_name", "active")
        if not isinstance(data["active"], bool):
            raise APIError("active phải là boolean.")
        name = text(data["full_name"], "Họ tên", limit=200)
        db = get_db()
        if data["active"] and not db.execute("SELECT 1 FROM technicians WHERE user_id=?", (user_id,)).fetchone():
            db.execute("INSERT INTO technicians(user_id,full_name,specialty) VALUES (?,?,'general')", (user_id, name))
        db.execute("UPDATE technicians SET active=? WHERE user_id=?", (int(data["active"]), user_id))
        db.commit()
        return {"user_id": user_id, "active": data["active"]}

    def technician_values(data, old=None):
        merged = dict(old or {})
        merged.update(data)
        required(merged, "user_id", "full_name", "specialty")
        user_id = integer(merged["user_id"], "user_id", min_value=1)
        users = call_service("auth", "/api/auth/users")["items"]
        if not any(u["user_id"] == user_id and u["role"] == "technician" for u in users):
            raise APIError("Tài khoản phải có vai trò kỹ thuật viên.")
        duplicate = (
            get_db()
            .execute(
                "SELECT technician_id FROM technicians WHERE user_id=? AND technician_id<>?",
                (user_id, (old or {}).get("technician_id", 0)),
            )
            .fetchone()
        )
        if duplicate:
            raise APIError("Tài khoản đã có hồ sơ kỹ thuật viên.", 409)
        return (
            user_id,
            text(merged["full_name"], "Họ tên", limit=200),
            enum(merged["specialty"], ("parking", "payment", "general"), "specialty"),
        )

    @app.patch("/api/maintenance/technicians/me")
    @require_auth("technician")
    def rename_own_profile():
        data = body()
        required(data, "full_name")
        db = get_db()
        # The seed links several rows to one login; only the canonical profile is shown to it.
        db.execute(
            f"UPDATE technicians SET full_name=? WHERE technician_id={OWN_TECHNICIAN_ID}",
            (text(data["full_name"], "Họ tên", limit=200), g.user["user_id"]),
        )
        db.commit()
        return {"updated": True}

    @app.patch("/api/maintenance/technicians/<int:technician_id>")
    @require_auth("admin")
    def update_technician(technician_id):
        db = get_db()
        old = one(db, "technicians", "technician_id", technician_id)
        values = technician_values(body(), old)
        db.execute(
            "UPDATE technicians SET user_id=?,full_name=?,specialty=? WHERE technician_id=?", (*values, technician_id)
        )
        db.commit()
        return one(db, "technicians", "technician_id", technician_id)

    @app.get("/api/maintenance/tickets")
    @require_auth("admin", "resident", "technician")
    def tickets():
        query = "SELECT m.*,t.full_name AS technician_name FROM maintenance_tickets m LEFT JOIN technicians t ON t.technician_id=m.technician_id WHERE 1=1"
        args = []
        # Technicians work as one team: every technician sees every ticket.
        if g.user["role"] == "resident":
            ids = resident_profile().get("apartment_ids", [])
            if not ids:
                return {"items": []}
            query += " AND m.apartment_id IN (" + placeholders(ids) + ")"
            args.extend(ids)
        if request.args.get("status"):
            query += " AND m.status=?"
            args.append(enum(request.args["status"], TICKET_STATUSES, "status"))
        return {
            "items": [
                dict(r)
                for r in get_db().execute(
                    query
                    + " ORDER BY CASE m.status WHEN 'pending' THEN 0 WHEN 'in_progress' THEN 1 ELSE 2 END,m.ticket_id DESC",
                    args,
                )
            ]
        }

    @app.post("/api/maintenance/tickets")
    @require_auth("admin", "resident")
    def add_ticket():
        data = body()
        required(data, "description")
        role = g.user["role"]
        apartment_id = data.get("apartment_id")
        confirmed = []
        if role == "resident":
            # Only apartments confirmed by management; a self-declared code is not enough.
            confirmed = resident_profile().get("apartment_ids", [])
            if not confirmed:
                raise APIError(
                    "Tài khoản chưa được Ban quản lý xác nhận liên kết căn hộ. "
                    "Vui lòng chờ xác nhận trước khi gửi yêu cầu sửa chữa.",
                    403,
                )
        if apartment_id is None and data.get("apartment_code"):
            code_input = text(data["apartment_code"], "Mã căn hộ", limit=30).upper()
            apartments = call_service("resident", "/api/apartments", internal=True).get("items", [])
            found = next((a for a in apartments if a["code"].upper() == code_input), None)
            if found is None:
                raise APIError("Không tìm thấy căn hộ. Vui lòng kiểm tra lại mã căn hộ.", 404)
            apartment_id = found["apartment_id"]
        if role == "resident":
            if apartment_id is None and len(confirmed) == 1:
                apartment_id = confirmed[0]
            if apartment_id is None:
                raise APIError("Cần chọn căn hộ cho phiếu yêu cầu.")
            apartment_id = integer(apartment_id, "apartment_id", min_value=1)
            if apartment_id not in confirmed:
                raise APIError("Bạn chỉ được gửi yêu cầu cho căn hộ đã được xác nhận.", 403)
        elif apartment_id is not None:
            apartment_id = apartment_access(apartment_id)
        location = None
        if role == "admin" and data.get("location"):
            # Either an apartment code or a shared place such as the lobby.
            typed = text(data["location"], "Căn hộ / địa điểm", limit=120)
            apartments = call_service("resident", "/api/apartments", internal=True).get("items", [])
            found = next((a for a in apartments if a["code"].casefold() == typed.casefold()), None)
            apartment_id, location = (found["apartment_id"], None) if found else (None, typed)
        kinds = (
            ("repair", "maintenance", "cut_service", "restore_service")
            if role == "admin"
            else ("repair", "maintenance")
        )
        kind = enum(data.get("type", "repair"), kinds, "type")
        # Residents do not set priority; management triages it.
        priority = "medium" if role == "resident" else enum(data.get("priority", "medium"), PRIORITIES, "priority")
        technician_id = data.get("technician_id")
        if technician_id is not None:
            if role != "admin":
                raise APIError("Chỉ Ban quản lý được phân công kỹ thuật viên.", 403)
            technician_id = integer(technician_id, "technician_id", min_value=1)
            one(get_db(), "technicians", "technician_id", technician_id)
        db = get_db()
        cursor = db.execute(
            "INSERT INTO maintenance_tickets(apartment_id,technician_id,type,description,priority,location) VALUES (?,?,?,?,?,?)",
            (apartment_id, technician_id, kind, text(data["description"], "Nội dung"), priority, location),
        )
        db.commit()
        ticket = one(db, "maintenance_tickets", "ticket_id", cursor.lastrowid)
        notify_ticket(
            ticket,
            f"Yêu cầu {TICKET_KINDS[kind]} mới #{ticket['ticket_id']}",
            f"Phiếu #{ticket['ticket_id']} vừa được tạo, trạng thái {STATUS_NAMES[ticket['status']]}.",
        )
        return ticket, 201

    @app.patch("/api/maintenance/tickets/<int:ticket_id>")
    @require_auth("admin", "technician")
    def update_ticket(ticket_id):
        db = get_db()
        # Serialize with settlement events so a stale technician update cannot
        # reopen a cut ticket that payment just cancelled.
        db.execute("BEGIN IMMEDIATE")
        old = one(db, "maintenance_tickets", "ticket_id", ticket_id)
        data = body()
        if g.user["role"] == "technician" and any(key != "status" for key in data):
            raise APIError("Kỹ thuật viên chỉ được thay đổi trạng thái công việc.", 403)
        if old["status"] == "completed":
            raise APIError("Phiếu đã đóng. Hãy tạo phiếu mới nếu cần xử lý tiếp.", 409)
        new_status = enum(data.get("status", old["status"]), TICKET_STATUSES, "status")
        if old["status"] == "pending" and new_status == "completed":
            raise APIError("Cần nhận xử lý phiếu trước khi hoàn thành.", 409)
        if old["status"] == "in_progress" and new_status == "pending":
            raise APIError("Phiếu đang xử lý không thể quay lại trạng thái chờ.", 409)
        technician_id = data.get("technician_id", old["technician_id"])
        if technician_id is None and g.user["role"] == "technician" and new_status != "pending":
            # A technician picking up an unassigned ticket becomes the person in charge of it.
            own = db.execute(f"SELECT {OWN_TECHNICIAN_ID} AS id", (g.user["user_id"],)).fetchone()
            technician_id = own["id"]
        if technician_id is not None:
            technician_id = integer(technician_id, "technician_id", min_value=1)
            one(db, "technicians", "technician_id", technician_id)
        if new_status != "pending" and technician_id is None:
            raise APIError("Cần phân công kỹ thuật viên trước khi xử lý.")
        description = text(data.get("description", old["description"]), "Nội dung")
        priority = enum(data.get("priority", old["priority"]), PRIORITIES, "priority")
        db.execute(
            "UPDATE maintenance_tickets SET technician_id=?,description=?,priority=?,status=?,completed_at=CASE WHEN ?='completed' THEN CURRENT_TIMESTAMP ELSE NULL END WHERE ticket_id=?",
            (technician_id, description, priority, new_status, new_status, ticket_id),
        )
        db.commit()
        ticket = one(db, "maintenance_tickets", "ticket_id", ticket_id)
        changes = []
        if new_status != old["status"]:
            changes.append(f"Trạng thái mới: {STATUS_NAMES[new_status]}.")
        if technician_id != old["technician_id"] and technician_id is not None:
            name = one(db, "technicians", "technician_id", technician_id)["full_name"]
            changes.append(f"Kỹ thuật viên phụ trách: {name}.")
        if changes:
            notify_ticket(ticket, f"Cập nhật phiếu {TICKET_KINDS[ticket['type']]} #{ticket_id}", " ".join(changes))
        return ticket

    return app


app = create_app()
if __name__ == "__main__":
    run(app, 5005)
