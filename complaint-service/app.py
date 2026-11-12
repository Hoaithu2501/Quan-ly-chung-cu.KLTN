"""Residents submit complaints/registrations; management records resolutions."""

import json
import re
import uuid
from urllib.parse import urlparse

from flask import g, request

from shared.auth import require_auth
from shared.db import get_db
from shared.domain import enum, local_today, one, resident_profile, text
from shared.http import call_service
from shared.web import APIError, body, create_app as service_app, integer, required, run


def dispatch_outbox(limit=25):
    """Delivery is retried with the same event id after a lost response or outage."""
    db = get_db()
    events = db.execute(
        "SELECT event_id,payload FROM complaint_outbox WHERE delivered_at IS NULL "
        "ORDER BY attempts,created_at,event_id LIMIT ?",
        (limit,),
    ).fetchall()
    delivered = 0
    for event in events:
        try:
            call_service(
                "notification",
                "/api/notifications/events",
                method="POST",
                json=json.loads(event["payload"]),
                internal=True,
            )
        except Exception as exc:
            db.execute(
                "UPDATE complaint_outbox SET attempts=attempts+1,last_error=? WHERE event_id=?",
                (type(exc).__name__, event["event_id"]),
            )
        else:
            db.execute(
                "UPDATE complaint_outbox SET delivered_at=CURRENT_TIMESTAMP,attempts=attempts+1,"
                "last_error=NULL WHERE event_id=?",
                (event["event_id"],),
            )
            delivered += 1
        db.commit()
    return delivered


def enqueue_reply(complaint):
    status_names = {
        "pending": "Chờ xử lý",
        "processing": "Đang xử lý",
        "resolved": "Đã giải quyết",
        "rejected": "Từ chối",
        "cancelled": "Đã huỷ",
    }
    identifier = complaint["complaint_id"]
    reply = complaint["response"]
    excerpt = reply[:3000] + ("…" if len(reply) > 3000 else "")
    payload = {
        "event_id": "complaint:reply:" + uuid.uuid4().hex,
        "type": "private",
        "target_resident_id": complaint["resident_id"],
        "title": f"Ban quản lý đã phản hồi yêu cầu #YC{identifier}",
        "content": f"Yêu cầu #YC{identifier} — {status_names[complaint['status']]}.\n"
        f"Phản hồi của Ban quản lý:\n{excerpt}\n\n"
        "Bạn vào Khiếu nại & đăng ký, mở yêu cầu này để xem đầy đủ phản hồi.",
    }
    get_db().execute(
        "INSERT INTO complaint_outbox(event_id,complaint_id,payload) VALUES (?,?,?)",
        (payload["event_id"], identifier, json.dumps(payload, ensure_ascii=False)),
    )


STATUSES = ("pending", "processing", "resolved", "rejected", "cancelled")
CLOSED = ("resolved", "rejected", "cancelled")
ATTACHMENT_TYPES = (
    "image/png",
    "image/jpeg",
    "image/gif",
    "image/webp",
    "application/pdf",
    "text/plain",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.ms-excel",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
ATTACHMENT_LIMIT = 600 * 1024  # base64 characters; the gateway accepts 1 MB per request.
PARKING_CATEGORY = "Đăng ký gửi xe"
VEHICLE_TYPES = {"xe máy": "motorbike", "xe điện": "electric_bike", "xe đạp": "bicycle"}


def attachment_values(value):
    """Files are stored as data URLs; links must be http(s)."""
    if value is None:
        return None
    if not isinstance(value, list) or len(value) > 5:
        raise APIError("Tối đa 5 tài liệu đính kèm.")
    result, total = [], 0
    for item in value:
        if not isinstance(item, dict):
            raise APIError("Tài liệu đính kèm không hợp lệ.")
        name = text(item.get("name") or "Tài liệu", "Tên tài liệu", limit=200)
        if item.get("url"):
            url = text(item["url"], "Liên kết", limit=1000)
            if urlparse(url).scheme not in ("http", "https") or not urlparse(url).netloc:
                raise APIError("Liên kết đính kèm phải bắt đầu bằng http:// hoặc https://.")
            result.append({"name": name, "url": url})
            continue
        data = item.get("data")
        match = re.fullmatch(r"data:([\w.+-]+/[\w.+-]+);base64,([A-Za-z0-9+/=]+)", data or "")
        if not match or match.group(1) not in ATTACHMENT_TYPES:
            raise APIError("Chỉ đính kèm ảnh, PDF, Word, Excel hoặc tệp văn bản.")
        total += len(data)
        if total > ATTACHMENT_LIMIT:
            raise APIError("Tổng dung lượng tệp đính kèm tối đa khoảng 450 KB.")
        result.append({"name": name, "type": match.group(1), "data": data})
    return json.dumps(result, ensure_ascii=False) if result else None


def complaint_result(row, names=None):
    result = dict(row)
    try:
        result["attachments"] = json.loads(result.get("attachments") or "[]")
    except ValueError:
        result["attachments"] = []
    if names is not None:
        result["resident_name"] = names.get(result["resident_id"])
    return result


def parking_request(content):
    """The resident parking form writes one "Nhãn: giá trị" line per field."""
    fields = {}
    for line in str(content or "").splitlines():
        key, _, value = line.partition(":")
        # The form writes its fields first and the free-text note last, so a note cannot replace a field.
        fields.setdefault(key.strip().casefold(), value.strip())
    kind = next(
        (code for label, code in VEHICLE_TYPES.items() if fields.get("loại xe", "").casefold().startswith(label)), None
    )
    months = re.match(r"\d+", fields.get("thời gian cam kết", ""))
    if not kind or not fields.get("căn hộ") or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fields.get("ngày bắt đầu", "")):
        raise APIError("Không đọc được thông tin xe trong đơn. Hãy đăng ký phương tiện tại Quản lý gửi xe.", 409)
    plate = fields.get("biển số", "")
    if not plate or plate.casefold().startswith("cấp mã"):
        plate = None
    return {
        "vehicle_type": kind,
        "plate_number": plate,
        "apartment_code": fields["căn hộ"],
        "registered_date": fields["ngày bắt đầu"],
        "registration_months": int(months.group()) if months else 2,
    }


def register_vehicle(complaint):
    """Approving a parking application creates the vehicle with the admin's token."""
    data = parking_request(complaint["content"])
    apartments = call_service("resident", "/api/apartments", internal=True)["items"]
    apartment = next((a for a in apartments if str(a["code"]).casefold() == data["apartment_code"].casefold()), None)
    if apartment is None:
        raise APIError(f"Không tìm thấy căn hộ {data['apartment_code']} trong đơn đăng ký.", 409)
    # Fees follow the apartment, so a resident may only register a vehicle for their own home.
    applicant = call_service("resident", f"/api/residents/{complaint['resident_id']}", internal=True)
    if apartment["apartment_id"] not in applicant.get("apartment_ids", []):
        raise APIError(
            f"Người gửi đơn chưa được xác nhận thuộc căn hộ {apartment['code']}. "
            "Hãy xác nhận căn hộ ở Cư dân & hợp đồng trước khi duyệt.",
            409,
        )
    payload = {key: data[key] for key in ("vehicle_type", "registered_date", "registration_months")}
    payload["apartment_id"] = apartment["apartment_id"]
    if data["plate_number"]:
        payload["plate_number"] = data["plate_number"]
    return call_service("parking", "/api/parking/vehicles", method="POST", json=payload)


def create_app():
    app = service_app("complaint")

    @app.get("/api/complaints/summary")
    @require_auth("admin")
    def complaint_summary():
        year = integer(request.args.get("year", local_today().year), "year", min_value=2000)
        if year > 9999:
            raise APIError("Năm không hợp lệ.")
        group = enum(request.args.get("group", "month"), ("month", "quarter"), "group")

        def period_of(month):
            return f"{year}-{month:02d}" if group == "month" else f"{year}-Q{(month - 1) // 3 + 1}"

        items = {
            period: {"period": period, "complaint_count": 0, "registration_count": 0}
            for period in map(period_of, range(1, 13))
        }
        totals = {"complaint_count": 0, "registration_count": 0, **{status + "_count": 0 for status in STATUSES}}
        # created_at is stored in UTC; the report follows the Vietnamese calendar.
        rows = get_db().execute(
            "SELECT type,status,datetime(created_at,'+7 hours') AS local_time FROM complaints "
            "WHERE substr(datetime(created_at,'+7 hours'),1,4)=?",
            (str(year),),
        )
        for row in rows:
            items[period_of(int(row["local_time"][5:7]))][row["type"] + "_count"] += 1
            totals[row["type"] + "_count"] += 1
            totals[row["status"] + "_count"] += 1
        return {"items": list(items.values()), "totals": totals}

    @app.get("/api/complaints")
    @require_auth("admin", "resident")
    def complaints():
        query, args = "SELECT * FROM complaints WHERE 1=1", []
        if g.user["role"] == "resident":
            query += " AND resident_id=?"
            args.append(resident_profile()["resident_id"])
        if request.args.get("status"):
            query += " AND status=?"
            args.append(enum(request.args["status"], STATUSES, "status"))
        names = None
        if g.user["role"] == "admin":
            try:
                names = {
                    r["resident_id"]: r["full_name"]
                    for r in call_service("resident", "/api/residents", internal=True)["items"]
                }
            except APIError:
                names = {}
        return {
            "items": [complaint_result(r, names) for r in get_db().execute(query + " ORDER BY complaint_id DESC", args)]
        }

    @app.post("/api/complaints")
    @require_auth("resident")
    def add_complaint():
        data = body()
        required(data, "type", "content")
        profile = resident_profile()
        resident_id = profile["resident_id"]
        if (
            data.get("resident_id") is not None
            and integer(data["resident_id"], "resident_id", min_value=1) != resident_id
        ):
            raise APIError("Bạn chỉ được tạo đơn cho chính mình.", 403)
        kind = enum(data["type"], ("complaint", "registration"), "type")
        category = text(data.get("category"), "Danh mục", limit=150, optional=True)
        content = text(data["content"], "Nội dung", limit=10000)
        if kind == "registration" and category == PARKING_CATEGORY:
            own = {
                str(code).casefold()
                for code in (*profile.get("apartment_codes", []), profile.get("registered_apartment_code"))
                if code
            }
            if parking_request(content)["apartment_code"].casefold() not in own:
                raise APIError("Chỉ được đăng ký gửi xe cho căn hộ của tài khoản này.", 403)
        attachments = attachment_values(data.get("attachments"))
        db = get_db()
        cursor = db.execute(
            "INSERT INTO complaints(resident_id,type,category,content,attachments) VALUES (?,?,?,?,?)",
            (resident_id, kind, category, content, attachments),
        )
        db.commit()
        return complaint_result(one(db, "complaints", "complaint_id", cursor.lastrowid)), 201

    @app.post("/api/complaints/<int:complaint_id>/cancel")
    @require_auth("resident")
    def cancel_complaint(complaint_id):
        resident_id = resident_profile()["resident_id"]
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            row = one(db, "complaints", "complaint_id", complaint_id)
            if row["resident_id"] != resident_id:
                raise APIError("Bạn chỉ được huỷ yêu cầu của chính mình.", 403)
            if row["status"] == "processing":
                raise APIError("Đơn đang ở trạng thái đang xử lý không thể huỷ yêu cầu.", 409)
            if row["status"] != "pending":
                raise APIError("Chỉ được huỷ yêu cầu đang chờ xử lý.", 409)
            db.execute(
                "UPDATE complaints SET status='cancelled',resolved_at=CURRENT_TIMESTAMP WHERE complaint_id=?",
                (complaint_id,),
            )
        return complaint_result(one(db, "complaints", "complaint_id", complaint_id))

    @app.patch("/api/complaints/<int:complaint_id>")
    @require_auth("admin")
    def update_complaint(complaint_id):
        data = body()
        if set(data) - {"status", "response"}:
            raise APIError("Chỉ được cập nhật trạng thái và phản hồi của yêu cầu.")
        db = get_db()
        current = one(db, "complaints", "complaint_id", complaint_id)
        vehicle = None
        if (
            current["type"] == "registration"
            and current["category"] == PARKING_CATEGORY
            and data.get("status") == "resolved"
            and current["status"] not in CLOSED
        ):
            # Parking writes the same SQLite file, so it runs before this service locks it.
            vehicle = register_vehicle(current)
            note = (
                f"Phương tiện đã được duyệt: {vehicle['plate_number']} "
                f"(hiệu lực từ {vehicle['registered_date']} đến {vehicle['minimum_end_date']}). "
                "Xem tại Quản lý gửi xe › Phương tiện đăng ký."
            )
            data["response"] = f"{str(data.get('response') or '').strip()}\n\n{note}".strip()
        with db:
            db.execute("BEGIN IMMEDIATE")
            old = one(db, "complaints", "complaint_id", complaint_id)
            status = enum(data.get("status", old["status"]), STATUSES, "status")
            if old["status"] in CLOSED and status != old["status"]:
                raise APIError("Đơn đã đóng. Cư dân có thể tạo đơn mới nếu cần.", 409)
            if status == "cancelled" and old["status"] != "cancelled":
                raise APIError("Chỉ cư dân gửi đơn mới được huỷ yêu cầu.", 403)
            if old["status"] == "processing" and status == "pending":
                raise APIError("Đơn đang xử lý không thể trở về trạng thái chờ.", 409)
            response = text(
                data.get("response", old["response"]),
                "Phản hồi",
                limit=10000,
                optional=status not in ("resolved", "rejected"),
            )
            if old["response"] and not response:
                raise APIError("Vui lòng nhập nội dung phản hồi thay cho việc xóa phản hồi đã gửi.")
            db.execute(
                "UPDATE complaints SET status=?,response=?,resolved_at=CASE WHEN ? IN ('resolved','rejected') THEN COALESCE(resolved_at,CURRENT_TIMESTAMP) ELSE NULL END WHERE complaint_id=?",
                (status, response, status, complaint_id),
            )
            updated = one(db, "complaints", "complaint_id", complaint_id)
            if response and response != (old["response"] or "").strip():
                enqueue_reply(updated)
        # A delivery failure never undoes the management response just committed.
        try:
            dispatch_outbox()
        except Exception:
            app.logger.warning("Reply saved; notification delivery will retry.")
        result = complaint_result(updated)
        if vehicle:
            result["vehicle"] = vehicle
        return result

    app.extensions["complaint_jobs"] = {"outbox": dispatch_outbox}
    return app


app = create_app()
if __name__ == "__main__":
    from scheduler import start_scheduler

    start_scheduler(app)
    run(app, 5007)
