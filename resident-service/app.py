"""Owns apartments, residents, and apartment_contracts."""

from datetime import date
import math
import uuid
from flask import g
from shared.audit import record_audit
from shared.auth import require_auth, require_internal, auth_or_internal
from shared.db import get_db, placeholders
from shared.http import call_service
from shared.domain import local_today, notify
from shared.web import create_app as base_app, APIError, body, person_name, required, integer, iso_date, run


def text(value, name, max_length=200):
    if not isinstance(value, str) or not value.strip() or len(value) > max_length:
        raise APIError(f"{name} không hợp lệ.")
    return value.strip()


def optional_text(value, name, max_length):
    if value is None:
        return None
    if not isinstance(value, str) or len(value) > max_length:
        raise APIError(f"{name} không hợp lệ.")
    return value.strip() or None


def assert_single_apartment(db, resident, apartment_id, start=None, end=None):
    """One account, one apartment: another home needs its own account once this one has ended."""
    if resident is None or not resident["user_id"]:
        return
    today = local_today().isoformat()
    first, last = (start, end or "9999-12-31") if start else (today, today)
    linked = db.execute(
        "SELECT 1 FROM resident_apartment_memberships WHERE resident_id=? AND apartment_id<>? LIMIT 1",
        (resident["resident_id"], apartment_id),
    ).fetchone()
    contracted = db.execute(
        "SELECT 1 FROM apartment_contracts WHERE resident_id=? AND apartment_id<>? AND status='active' "
        "AND start_date<=? AND COALESCE(end_date,'9999-12-31')>=? LIMIT 1",
        (resident["resident_id"], apartment_id, last, first),
    ).fetchone()
    if linked or contracted:
        raise APIError("Mỗi tài khoản chỉ liên kết một căn hộ. Căn hộ khác cần đăng ký bằng tài khoản riêng.", 409)


def contract_resident_by_name(db, typed, contract_type):
    """A typed name may only ever resolve to one person; names are not unique."""
    wanted = text(typed, "Tên cư dân", 120).casefold()
    # casefold here because SQLite's LOWER() only understands ASCII, not Vietnamese.
    matches = [
        row["resident_id"]
        for row in db.execute("SELECT resident_id,full_name FROM residents")
        if row["full_name"].strip().casefold() == wanted
    ]
    if len(matches) > 1:
        raise APIError("Có nhiều cư dân trùng tên. Hãy chọn đúng cư dân theo mã hồ sơ.", 409)
    if matches:
        return matches[0]
    relation = "owner" if contract_type == "ownership" else "tenant"
    return db.execute(
        "INSERT INTO residents(full_name,relation_type) VALUES(?,?)", (str(typed).strip(), relation)
    ).lastrowid


def current_contracts(db, resident_id=None):
    query = "SELECT * FROM apartment_contracts WHERE status='active' AND start_date<=? AND (end_date IS NULL OR end_date>=?)"
    args = [local_today().isoformat()] * 2
    if resident_id is not None:
        query += " AND resident_id=?"
        args.append(resident_id)
    return db.execute(query, args).fetchall()


def profile(row):
    result = dict(row)
    db = get_db()
    result["contract_apartment_ids"] = sorted({c["apartment_id"] for c in current_contracts(db, row["resident_id"])})
    memberships = db.execute(
        "SELECT m.apartment_id,a.code,m.confirmed_by_user_id,m.confirmed_at "
        "FROM resident_apartment_memberships m JOIN apartments a ON a.apartment_id=m.apartment_id "
        "WHERE m.resident_id=? ORDER BY a.code,m.apartment_id",
        (row["resident_id"],),
    ).fetchall()
    result["verified_apartments"] = [dict(item) for item in memberships]
    result["verified_apartment_ids"] = [item["apartment_id"] for item in memberships]
    result["apartment_ids"] = sorted(set(result["contract_apartment_ids"]) | set(result["verified_apartment_ids"]))
    ids = result["apartment_ids"]
    result["apartment_codes"] = (
        [
            r["code"]
            for r in db.execute(
                f"SELECT code FROM apartments WHERE apartment_id IN ({placeholders(ids)}) ORDER BY code", ids
            )
        ]
        if ids
        else []
    )
    return result


def own_profile():
    row = (
        get_db()
        .execute("SELECT * FROM residents WHERE user_id=? ORDER BY resident_id LIMIT 1", (g.user["user_id"],))
        .fetchone()
    )
    if row is None:
        raise APIError("Chưa có hồ sơ cư dân. Vui lòng liên hệ Ban quản lý.", 404)
    return profile(row)


def apartment(row):
    result = dict(row)
    contracts = (
        get_db()
        .execute(
            "SELECT c.*,r.full_name,r.phone FROM apartment_contracts c JOIN residents r ON r.resident_id=c.resident_id WHERE c.apartment_id=? ORDER BY c.start_date DESC",
            (row["apartment_id"],),
        )
        .fetchall()
    )
    today = local_today().isoformat()
    current = [
        c
        for c in contracts
        if c["status"] == "active" and c["start_date"] <= today and (not c["end_date"] or c["end_date"] >= today)
    ]
    owner = next((c for c in current if c["contract_type"] == "ownership"), None)
    # While a lease runs the tenant is the occupant, so the lease decides the occupancy details.
    active = next((c for c in current if c["contract_type"] == "rental"), owner)
    # Management can confirm that someone lives here without drawing up a contract.
    members = (
        get_db()
        .execute(
            "SELECT r.full_name,r.phone,r.relation_type FROM resident_apartment_memberships m "
            "JOIN residents r ON r.resident_id=m.resident_id WHERE m.apartment_id=? "
            "ORDER BY m.confirmed_at,m.resident_id",
            (row["apartment_id"],),
        )
        .fetchall()
    )
    member = members[0] if members else None
    if owner is None:
        owner = next((m for m in members if m["relation_type"] == "owner"), None)
    member_type = None
    if member:
        member_type = "ownership" if member["relation_type"] == "owner" else "rental"
    result.update(
        status="occupied" if active or member else "vacant",
        owner_name=owner["full_name"] if owner else None,
        owner_phone=owner["phone"] if owner else None,
        current_resident=active["full_name"] if active else member["full_name"] if member else None,
        contract_type=active["contract_type"] if active else member_type,
        start_date=active["start_date"] if active else None,
        end_date=active["end_date"] if active else None,
        remaining_days=(date.fromisoformat(active["end_date"]) - local_today()).days
        if active and active["end_date"]
        else None,
    )
    return result


def resident_row(resident_id):
    row = get_db().execute("SELECT * FROM residents WHERE resident_id=?", (resident_id,)).fetchone()
    if row is None:
        raise APIError("Không tìm thấy cư dân.", 404)
    return row


def apartment_row(apartment_id):
    row = get_db().execute("SELECT * FROM apartments WHERE apartment_id=?", (apartment_id,)).fetchone()
    if row is None:
        raise APIError("Không tìm thấy căn hộ.", 404)
    return row


def visible_apartment(result):
    """Technicians only need the location, and an owner's phone number stays with management."""
    if g.user["role"] == "technician":
        return {key: result[key] for key in ("apartment_id", "code", "block", "floor", "status")}
    if g.user["role"] == "resident":
        result.pop("owner_phone")
    return result


def sync_occupancy(db, apartment_id):
    occupied = (
        any(c["apartment_id"] == apartment_id for c in current_contracts(db))
        or db.execute(
            "SELECT 1 FROM resident_apartment_memberships WHERE apartment_id=? LIMIT 1", (apartment_id,)
        ).fetchone()
    )
    db.execute(
        "UPDATE apartments SET status=? WHERE apartment_id=?", ("occupied" if occupied else "vacant", apartment_id)
    )


def create_app():
    app = base_app("resident")

    @app.get("/api/apartments")
    @auth_or_internal("admin", "resident", "technician")
    def apartments():
        rows = get_db().execute("SELECT * FROM apartments ORDER BY block,floor,code").fetchall()
        if g.user["role"] == "resident":
            ids = own_profile()["apartment_ids"]
            rows = [r for r in rows if r["apartment_id"] in ids]
        return {"items": [visible_apartment(apartment(r)) for r in rows]}

    @app.get("/api/apartments/<int:apartment_id>")
    @auth_or_internal("admin", "resident", "technician")
    def get_apartment(apartment_id):
        row = apartment_row(apartment_id)
        if g.user["role"] == "resident" and apartment_id not in own_profile()["apartment_ids"]:
            raise APIError("Không có quyền truy cập căn hộ này.", 403)
        return visible_apartment(apartment(row))

    def apartment_data(data, old=None):
        values = dict(old or {})
        values.update(data)
        required(values, "code", "block", "floor", "area")
        code = text(values["code"], "Mã căn hộ", 30)
        block = text(values["block"], "Tòa nhà", 30)
        floor = integer(values["floor"], "Tầng", 1)
        if floor > 200:
            raise APIError("Tầng không được quá 200.")
        try:
            area = float(values["area"])
        except (ValueError, TypeError):
            raise APIError("Diện tích không hợp lệ.")
        if not math.isfinite(area) or area <= 0 or area > 10000:
            raise APIError("Diện tích phải lớn hơn 0 và không quá 10000 m².")
        return code, block, floor, area

    @app.post("/api/apartments")
    @require_auth("admin")
    def create_apartment():
        values = apartment_data(body())
        db = get_db()
        cur = db.execute("INSERT INTO apartments(code,block,floor,area) VALUES(?,?,?,?)", values)
        db.commit()
        return apartment(db.execute("SELECT * FROM apartments WHERE apartment_id=?", (cur.lastrowid,)).fetchone()), 201

    @app.patch("/api/apartments/<int:apartment_id>")
    @require_auth("admin")
    def update_apartment(apartment_id):
        db = get_db()
        old = apartment_row(apartment_id)
        values = apartment_data(body(), old)
        db.execute("UPDATE apartments SET code=?,block=?,floor=?,area=? WHERE apartment_id=?", (*values, apartment_id))
        db.commit()
        return apartment(db.execute("SELECT * FROM apartments WHERE apartment_id=?", (apartment_id,)).fetchone())

    @app.get("/api/residents/me")
    @require_auth("resident")
    def resident_me():
        return own_profile()

    @app.patch("/api/residents/me")
    @require_auth("resident")
    def update_own_profile():
        data = body()
        old = own_profile()
        if set(data) - {"full_name", "phone", "id_card"}:
            raise APIError("Chỉ được cập nhật họ tên, số điện thoại và CCCD.")
        name = old["full_name"]
        if "full_name" in data:
            name = person_name(data["full_name"])
        values = {}
        for key, limit in (("phone", 20), ("id_card", 30)):
            value = data.get(key, old[key])
            if key == "phone" and key in data and (value is None or isinstance(value, str) and not value.strip()):
                raise APIError("Vui lòng nhập số điện thoại.")
            if value is not None and (not isinstance(value, str) or len(value) > limit):
                raise APIError("Thông tin cá nhân không hợp lệ.")
            values[key] = value.strip() or None if isinstance(value, str) else None
        db = get_db()
        db.execute(
            "UPDATE residents SET full_name=?,phone=?,id_card=? WHERE resident_id=?",
            (name, values["phone"], values["id_card"], old["resident_id"]),
        )
        db.commit()
        return own_profile()

    @app.get("/api/residents")
    @auth_or_internal("admin")
    def residents():
        return {"items": [profile(r) for r in get_db().execute("SELECT * FROM residents ORDER BY resident_id")]}

    @app.get("/api/residents/<int:resident_id>")
    @auth_or_internal("admin", "resident")
    def get_resident(resident_id):
        row = resident_row(resident_id)
        if g.user["role"] == "resident" and row["user_id"] != g.user["user_id"]:
            raise APIError("Không có quyền truy cập.", 403)
        return profile(row)

    def membership_entities(resident_id, apartment_id):
        db = get_db()
        resident = resident_row(resident_id)
        apartment_row(apartment_id)
        return db, resident

    @app.post("/api/residents/<int:resident_id>/apartments")
    @require_auth("admin")
    def confirm_resident_apartment(resident_id):
        data = body()
        required(data, "apartment_id")
        if set(data) - {"apartment_id"}:
            raise APIError("Chỉ được chọn căn hộ cần xác nhận.")
        apartment_id = integer(data["apartment_id"], "Căn hộ", 1)
        db, resident = membership_entities(resident_id, apartment_id)
        assert_single_apartment(db, resident, apartment_id)
        with db:
            cur = db.execute(
                "INSERT OR IGNORE INTO resident_apartment_memberships "
                "(resident_id,apartment_id,confirmed_by_user_id) VALUES (?,?,?)",
                (resident_id, apartment_id, g.user["user_id"]),
            )
            if cur.rowcount:
                record_audit(
                    db, "apartment_membership_confirmed", "resident", resident_id, {"apartment_id": apartment_id}
                )
                sync_occupancy(db, apartment_id)
        if cur.rowcount:
            code = apartment_row(apartment_id)["code"]
            notify(
                f"apartment-confirmed:{resident_id}:{apartment_id}:{uuid.uuid4().hex}",
                target_resident_id=resident_id,
                title=f"Căn hộ {code} đã được xác nhận",
                content=f"Ban quản lý đã xác nhận bạn thuộc căn hộ {code}. "
                "Bạn có thể xem hóa đơn, gửi yêu cầu và sử dụng các tiện ích của căn hộ.",
            )
        return profile(resident), 201 if cur.rowcount else 200

    @app.delete("/api/residents/<int:resident_id>/apartments/<int:apartment_id>")
    @require_auth("admin")
    def revoke_resident_apartment(resident_id, apartment_id):
        db, resident = membership_entities(resident_id, apartment_id)
        with db:
            removed = db.execute(
                "DELETE FROM resident_apartment_memberships WHERE resident_id=? AND apartment_id=?",
                (resident_id, apartment_id),
            ).rowcount
            if removed:
                record_audit(
                    db, "apartment_membership_revoked", "resident", resident_id, {"apartment_id": apartment_id}
                )
                sync_occupancy(db, apartment_id)
        return profile(resident)

    def save_resident(data, resident_id=None, provision=False):
        db = get_db()
        old = None
        if resident_id:
            old = resident_row(resident_id)
        values = dict(old or {})
        values.update(data)
        required(values, "full_name", "relation_type")
        name = text(values["full_name"], "Họ tên", 120)
        relation = values["relation_type"]
        if relation not in ("owner", "tenant"):
            raise APIError("Loại cư dân không hợp lệ.")
        user_id = values.get("user_id") or None
        if user_id:
            user_id = integer(user_id, "user_id", 1)
            if not provision:
                users = call_service("auth", "/api/auth/users", internal=True)["items"]
                if not any(u["user_id"] == user_id and u["role"] in ("resident", "technician", "admin") for u in users):
                    raise APIError("Tài khoản phải có vai trò cư dân, kỹ thuật viên hoặc Ban quản lý.")
            existing = db.execute("SELECT * FROM residents WHERE user_id=?", (user_id,)).fetchone()
            if existing and existing["resident_id"] != resident_id:
                if provision:
                    return profile(existing)
                raise APIError("Tài khoản đã có hồ sơ cư dân.", 409)
        params = (
            user_id,
            name,
            optional_text(values.get("id_card"), "CCCD", 30),
            optional_text(values.get("phone"), "Số điện thoại", 20),
            relation,
        )
        if old:
            db.execute(
                "UPDATE residents SET user_id=?,full_name=?,id_card=?,phone=?,relation_type=? WHERE resident_id=?",
                (*params, resident_id),
            )
        else:
            cur = db.execute(
                "INSERT INTO residents(user_id,full_name,id_card,phone,relation_type) VALUES(?,?,?,?,?)", params
            )
            resident_id = cur.lastrowid
        if "registered_apartment_code" in data:
            code_val = str(data["registered_apartment_code"]).strip() if data["registered_apartment_code"] else None
            db.execute("UPDATE residents SET registered_apartment_code=? WHERE resident_id=?", (code_val, resident_id))
        db.commit()
        return profile(db.execute("SELECT * FROM residents WHERE resident_id=?", (resident_id,)).fetchone())

    @app.post("/api/residents")
    @require_auth("admin")
    def create_resident():
        return save_resident(body()), 201

    @app.patch("/api/residents/<int:resident_id>")
    @require_auth("admin")
    def update_resident(resident_id):
        return save_resident(body(), resident_id)

    @app.post("/api/residents/provision")
    @require_internal
    def provision():
        return save_resident(body(), provision=True), 201

    @app.get("/api/contracts")
    @require_auth("admin", "resident")
    def contracts():
        db = get_db()
        query = "SELECT c.*,a.code,r.full_name FROM apartment_contracts c JOIN apartments a ON a.apartment_id=c.apartment_id JOIN residents r ON r.resident_id=c.resident_id"
        args = []
        if g.user["role"] == "resident":
            query += " WHERE c.resident_id=?"
            args = [own_profile()["resident_id"]]
        rows = []
        for row in db.execute(query + " ORDER BY c.contract_id DESC", args):
            item = dict(row)
            item["remaining_days"] = (
                (date.fromisoformat(row["end_date"]) - local_today()).days if row["end_date"] else None
            )
            item["effective_status"] = (
                "expired"
                if row["status"] == "active" and row["end_date"] and row["end_date"] < local_today().isoformat()
                else row["status"]
            )
            rows.append(item)
        return {"items": rows}

    def save_contract(data, contract_id=None):
        db = get_db()
        old = None
        # Taken first: the overlap check and any new resident must share one transaction.
        db.execute("BEGIN IMMEDIATE")
        if contract_id:
            old = db.execute("SELECT * FROM apartment_contracts WHERE contract_id=?", (contract_id,)).fetchone()
            if old is None:
                raise APIError("Không tìm thấy hợp đồng.", 404)
        values = dict(old or {})
        values.update(data)
        if data.get("resident_name") and data.get("resident_id") is None:
            values["resident_id"] = contract_resident_by_name(db, data["resident_name"], values.get("contract_type"))
        required(values, "apartment_id", "resident_id", "contract_type", "start_date")
        aid = integer(values["apartment_id"], "Căn hộ", 1)
        rid = integer(values["resident_id"], "Cư dân", 1)
        typ = values["contract_type"]
        status = values.get("status", "active")
        if typ not in ("ownership", "rental") or status not in ("active", "expired", "terminated"):
            raise APIError("Loại hoặc trạng thái hợp đồng không hợp lệ.")
        start = iso_date(values["start_date"], "Ngày bắt đầu")
        end = values.get("end_date") or None
        if typ == "rental" and not end:
            raise APIError("Hợp đồng thuê cần ngày kết thúc.")
        if end:
            iso_date(end, "Ngày kết thúc")
            if end < start:
                raise APIError("Ngày kết thúc phải từ ngày bắt đầu trở đi.")
        if status == "active":
            duplicate = db.execute(
                "SELECT contract_id FROM apartment_contracts WHERE apartment_id=? AND contract_type=? AND status='active' "
                "AND contract_id<>? AND start_date<=? AND COALESCE(end_date,'9999-12-31')>=?",
                (aid, typ, contract_id or 0, end or "9999-12-31", start),
            ).fetchone()
            if duplicate:
                raise APIError(
                    f"Căn hộ đã có hợp đồng {'sở hữu' if typ == 'ownership' else 'thuê'} trong khoảng thời gian này.",
                    409,
                )
            assert_single_apartment(
                db, db.execute("SELECT * FROM residents WHERE resident_id=?", (rid,)).fetchone(), aid, start, end
            )
        params = (aid, rid, typ, start, end, status)
        if old:
            db.execute(
                "UPDATE apartment_contracts SET apartment_id=?,resident_id=?,contract_type=?,start_date=?,end_date=?,status=? WHERE contract_id=?",
                (*params, contract_id),
            )
        else:
            cur = db.execute(
                "INSERT INTO apartment_contracts(apartment_id,resident_id,contract_type,start_date,end_date,status) VALUES(?,?,?,?,?,?)",
                params,
            )
            contract_id = cur.lastrowid
        sync_occupancy(db, aid)
        if old and old["apartment_id"] != aid:
            sync_occupancy(db, old["apartment_id"])
        db.commit()
        return dict(db.execute("SELECT * FROM apartment_contracts WHERE contract_id=?", (contract_id,)).fetchone())

    @app.post("/api/contracts")
    @require_auth("admin")
    def create_contract():
        return save_contract(body()), 201

    @app.patch("/api/contracts/<int:contract_id>")
    @require_auth("admin")
    def update_contract(contract_id):
        return save_contract(body(), contract_id)

    return app


app = create_app()
if __name__ == "__main__":
    run(app, 5002)
