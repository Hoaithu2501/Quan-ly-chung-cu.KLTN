"""Monthly vehicle registrations and the guest parking daily cash ledger."""

import calendar
import re
from datetime import date, datetime, timedelta, timezone

from flask import g, request

from shared.auth import auth_or_internal, require_auth
from shared.db import get_db, placeholders
from shared.domain import apartment_access, enum, local_today, one, resident_profile, text
from shared.http import call_service
from shared.web import APIError, body, create_app as service_app, integer, iso_date, required, run


MONTHLY_FEES = {"bicycle": 50_000, "motorbike": 100_000, "electric_bike": 100_000}
CARD_FEE = 100_000


def plate_key(plate):
    """29A1-111.11, 29a1 11111 and 29A111111 are the same plate."""
    return re.sub(r"[^0-9A-Z]", "", str(plate or "").upper())


def known_plates(db, exclude_id=0):
    """Every other registration ever made, by normalized plate: 'active' if one is still running."""
    plates = {}
    for row in db.execute(
        "SELECT plate_number,status FROM vehicles WHERE plate_number IS NOT NULL AND vehicle_id<>?", (exclude_id,)
    ):
        key = plate_key(row["plate_number"])
        if plates.get(key) != "active":
            plates[key] = row["status"]
    return plates


def month_start(start, months):
    """The same day `months` calendar months later, or that month's last day when it is shorter
    (31/01 + 1 month = 28/02). Always inside calendar month start.month + months."""
    year, month = divmod(start.year * 12 + start.month - 1 + months, 12)
    return date(year, month + 1, min(start.day, calendar.monthrange(year, month + 1)[1]))


def registration_end(registered, months):
    """Calendar months from the start date, like a monthly ticket: 20/11 for 2 months runs to the end of 19/01."""
    try:
        return month_start(date.fromisoformat(str(registered)), months) - timedelta(days=1)
    except (ValueError, OverflowError):
        raise APIError("Thời gian đăng ký không hợp lệ.")


def registration_window(start, renewal=False):
    """(fewest, most) months a registration starting in this month may cover.

    At least 2 months, and every month must begin within the six-month fee period (January-June
    or July-December), where all of them are billed: the days of the last month that run into the
    next period are paid for already. June is the last month of H1, so a June registration may
    run seven months; nothing begins in the next year, so a December registration is one month.
    Renewing a vehicle already registered may add a single month.
    """
    last = 12 if start.month >= 6 else 6
    longest = last - start.month + 1
    return (1 if renewal else min(2, longest)), longest


def check_window(start, months, action="Đăng ký", renewal=False):
    fewest, most = registration_window(start, renewal)
    if not fewest <= months <= most:
        last = 12 if start.month >= 6 else 6
        span = f"đúng {most} tháng" if fewest == most else f"từ {fewest} đến {most} tháng"
        raise APIError(
            f"{action} bắt đầu tháng {start.month}/{start.year} được chọn {span} "
            f"(tính cả tháng bắt đầu; kỳ thu phí kết thúc tháng {last}/{start.year})."
        )


def vehicle_result(row):
    result = dict(row)
    end = registration_end(result["registered_date"], result["registration_months"])
    # The API name is kept: it is the date the registration runs out.
    result["minimum_end_date"] = end.isoformat()
    result["registration_expired"] = result["status"] == "active" and end < local_today()
    return result


def apartment_filter(args):
    """The optional ?apartment_id= narrowing shared by the parking lists."""
    if not request.args.get("apartment_id"):
        return ""
    args.append(integer(request.args["apartment_id"], "apartment_id", min_value=1))
    return " AND apartment_id=?"


def create_app():
    app = service_app("parking")

    @app.get("/api/parking/vehicles")
    @auth_or_internal("admin", "resident", "technician")
    def vehicles():
        query, args = "SELECT * FROM vehicles WHERE 1=1", []
        if g.user["role"] == "resident":
            ids = resident_profile().get("apartment_ids", [])
            if not ids:
                return {"items": []}
            query += " AND apartment_id IN (" + placeholders(ids) + ")"
            args.extend(ids)
        query += apartment_filter(args)
        if request.args.get("status"):
            query += " AND status=?"
            args.append(enum(request.args["status"], ("active", "cancelled"), "status"))
        return {"items": [vehicle_result(r) for r in get_db().execute(query + " ORDER BY vehicle_id DESC", args)]}

    def vehicle_values(data, old=None):
        merged = dict(old or {})
        merged.update(data)
        required(merged, "apartment_id", "vehicle_type")
        apartment_id = apartment_access(merged["apartment_id"])
        kind = enum(merged["vehicle_type"], tuple(MONTHLY_FEES), "vehicle_type")
        fee = MONTHLY_FEES[kind]
        if "monthly_fee" in data and integer(data["monthly_fee"], "monthly_fee", min_value=0) != fee:
            raise APIError(f"Phí gửi xe loại này phải là {fee:,} VNĐ/tháng.")
        plate = merged.get("plate_number")
        if (
            old
            and old["vehicle_type"] == "bicycle"
            and re.search(r"-XD-\d+$", str(old["plate_number"] or ""))
            and plate == old["plate_number"]
            and (apartment_id != old["apartment_id"] or kind != "bicycle")
        ):
            # A generated room identifier cannot become a motorbike plate or
            # keep pointing at a previous room after the bicycle is moved.
            plate = None
        plate = text(plate, "Biển số", limit=30).upper() if plate else None
        if plate and not plate_key(plate):
            raise APIError("Biển số phải có chữ hoặc số.")
        if kind in ("motorbike", "electric_bike") and not plate:
            raise APIError("Xe máy và xe điện cần có biển số.")
        registered = iso_date(merged.get("registered_date", local_today().isoformat()), "registered_date")
        months = integer(merged.get("registration_months", 2), "registration_months", min_value=1)
        start = date.fromisoformat(registered)
        if not old:
            check_window(start, months)
        elif months != old["registration_months"]:
            # Renewals may have taken an older registration past its first period; only growing it is limited.
            fewest, most = registration_window(start)
            if months < fewest or (months > old["registration_months"] and months > most):
                check_window(start, months, "Đăng ký")
        earliest_end = registration_end(registered, months)
        status = enum(merged.get("status", "active"), ("active", "cancelled"), "status")
        cancelled = (old or {}).get("cancelled_date")
        if not old and status != "active":
            raise APIError("Đăng ký mới phải ở trạng thái đang hoạt động.")
        if old and registered != old["registered_date"]:
            raise APIError("Không được thay đổi ngày bắt đầu của đăng ký đã tạo.")
        if old and old["status"] == "cancelled":
            raise APIError("Đăng ký đã hủy không thể thay đổi. Hãy tạo đăng ký mới.", 409)
        if old and months < old["registration_months"]:
            # Nothing has been collected yet, so the commitment can still be corrected.
            if call_service("billing", f"/api/billing/vehicle-billing/{old['vehicle_id']}")["fee_paid"]:
                raise APIError("Xe đã đóng phí gửi nên không được rút ngắn thời gian đăng ký.", 409)
        if status == "cancelled":
            if local_today() < earliest_end:
                raise APIError(f"Chỉ được hủy từ ngày {earliest_end.isoformat()} sau thời gian đăng ký tối thiểu.", 409)
            cancelled = local_today().isoformat()
        if plate and status == "active":
            if known_plates(get_db(), (old or {}).get("vehicle_id", 0)).get(plate_key(plate)) == "active":
                raise APIError(
                    "Biển số này đã có đăng ký đang hoạt động. Nếu đăng ký đó đã hết hạn, hãy dùng Gia hạn.", 409
                )
        return {
            "apartment_id": apartment_id,
            "plate_number": plate,
            "vehicle_type": kind,
            "monthly_fee": fee,
            "registered_date": registered,
            "status": status,
            "registration_months": months,
            "cancelled_date": cancelled,
        }

    def room_prefix(values):
        # Fetched before any write: SQLite's single write lock must not span an HTTP call.
        if values["plate_number"]:
            return None
        apartment = call_service("resident", f"/api/apartments/{values['apartment_id']}", internal=True)
        return f"{str(apartment['code']).upper()[:18]}-XD-"

    def assign_room_identifier(db, prefix, vehicle_id):
        if prefix is None:
            return
        # Căn hộ - loại xe - số thứ tự xe trong căn hộ, e.g. A101-XD-1.
        used = {
            str(row["plate_number"]).upper()
            for row in db.execute(
                "SELECT plate_number FROM vehicles WHERE UPPER(plate_number) LIKE ? AND vehicle_id<>?",
                (prefix + "%", vehicle_id),
            )
        }
        sequence = 1
        while f"{prefix}{sequence}" in used:
            sequence += 1
        db.execute("UPDATE vehicles SET plate_number=? WHERE vehicle_id=?", (f"{prefix}{sequence}", vehicle_id))

    @app.post("/api/parking/vehicles")
    @require_auth("admin")
    def add_vehicle():
        values = vehicle_values(body())
        prefix = room_prefix(values)
        db = get_db()
        # A vehicle registered before already has its card: never charge the issuance fee twice.
        has_card = values["plate_number"] and plate_key(values["plate_number"]) in known_plates(db)
        values["card_fee"] = 0 if has_card else CARD_FEE
        values["created_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        cursor = db.execute(
            f"INSERT INTO vehicles({','.join(values)}) VALUES ({placeholders(values)})", list(values.values())
        )
        assign_room_identifier(db, prefix, cursor.lastrowid)
        db.commit()
        return vehicle_result(one(db, "vehicles", "vehicle_id", cursor.lastrowid)), 201

    @app.get("/api/parking/vehicles/<int:vehicle_id>")
    @auth_or_internal("admin")
    def get_vehicle(vehicle_id):
        return vehicle_result(one(get_db(), "vehicles", "vehicle_id", vehicle_id))

    @app.post("/api/parking/vehicles/<int:vehicle_id>/renew")
    @require_auth("admin")
    def renew_vehicle(vehicle_id):
        """Renewing follows the registration rules for the month the extra time starts.

        Before the registration runs out, the extra months follow straight on. After it ran out,
        the months in between are not owed, so the old registration closes on its end date and
        a new one starts today with the same plate and card (no second card fee).
        """
        data = body()
        required(data, "months")
        added = integer(data["months"], "months", min_value=1)
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            vehicle = one(db, "vehicles", "vehicle_id", vehicle_id)
            if vehicle["status"] != "active":
                raise APIError("Đăng ký đã hủy không thể gia hạn. Hãy tạo đăng ký mới.", 409)
            end = registration_end(vehicle["registered_date"], vehicle["registration_months"])
            today = local_today()
            if end >= today:
                check_window(end + timedelta(days=1), added, "Gia hạn", renewal=True)
                db.execute(
                    "UPDATE vehicles SET registration_months=registration_months+? WHERE vehicle_id=?", (added, vehicle_id)
                )
                renewed_id = vehicle_id
            else:
                check_window(today, added, "Gia hạn", renewal=True)
                db.execute(
                    "UPDATE vehicles SET status='cancelled',cancelled_date=? WHERE vehicle_id=?",
                    ((end + timedelta(days=1)).isoformat(), vehicle_id),
                )
                values = {
                    key: vehicle[key] for key in ("apartment_id", "plate_number", "vehicle_type", "monthly_fee")
                }
                values.update(
                    registered_date=today.isoformat(),
                    registration_months=added,
                    status="active",
                    card_fee=0,
                    created_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                )
                renewed_id = db.execute(
                    f"INSERT INTO vehicles({','.join(values)}) VALUES ({placeholders(values)})", list(values.values())
                ).lastrowid
        return vehicle_result(one(db, "vehicles", "vehicle_id", renewed_id))

    @app.patch("/api/parking/vehicles/<int:vehicle_id>")
    @require_auth("admin")
    def update_vehicle(vehicle_id):
        db = get_db()
        old = one(db, "vehicles", "vehicle_id", vehicle_id)
        values = vehicle_values(body(), old)
        prefix = room_prefix(values)
        # Correcting the plate to one registered before means the card already exists.
        if (
            values["plate_number"]
            and plate_key(values["plate_number"]) != plate_key(old["plate_number"])
            and plate_key(values["plate_number"]) in known_plates(db, vehicle_id)
        ):
            values["card_fee"] = 0
        db.execute(
            f"UPDATE vehicles SET {','.join(key + '=?' for key in values)} WHERE vehicle_id=?",
            [*values.values(), vehicle_id],
        )
        assign_room_identifier(db, prefix, vehicle_id)
        db.commit()
        return vehicle_result(one(db, "vehicles", "vehicle_id", vehicle_id))

    @app.get("/api/parking/summary")
    @auth_or_internal("admin", "technician")
    def summary():
        period = request.args.get("period")
        if period:
            if not re.fullmatch(r"\d{4}-H[12]", period) or int(period[:4]) < 2000:
                raise APIError("Kỳ gửi xe phải là YYYY-H1 hoặc YYYY-H2, từ năm 2000.")
            year, half = int(period[:4]), int(period[-1])
            first_month = 1 if half == 1 else 7
            start = date(year, first_month, 1)
            end = date(year, first_month + 5, calendar.monthrange(year, first_month + 5)[1])
            first_index = year * 12 + first_month - 1
            query, args = "SELECT * FROM vehicles WHERE registered_date<=?", [end.isoformat()]
            query += apartment_filter(args)
            if request.args.get("vehicle_id"):
                query += " AND vehicle_id=?"
                args.append(integer(request.args["vehicle_id"], "vehicle_id", min_value=1))
            totals = {}
            for row in get_db().execute(query, args):
                registered = date.fromisoformat(row["registered_date"])
                registered_until = registration_end(row["registered_date"], row["registration_months"])
                cancelled = date.fromisoformat(row["cancelled_date"]) if row["cancelled_date"] else None
                # Each registered month is billed in the period it begins in, so the days a last month
                # runs into the next period are never billed twice. Months after a cancellation are not owed.
                registered_index = registered.year * 12 + registered.month - 1
                months = sum(
                    1
                    for k in range(row["registration_months"])
                    if first_index <= registered_index + k <= first_index + 5
                    and (cancelled is None or month_start(registered, k) < cancelled)
                )
                if not months:
                    continue
                card_fee = row["card_fee"] if start <= registered <= end else 0
                total = totals.setdefault(
                    row["apartment_id"],
                    {
                        "apartment_id": row["apartment_id"],
                        "vehicle_count": 0,
                        "vehicle_months": 0,
                        "monthly_fee": 0,
                        "recurring_fee": 0,
                        "card_fee": 0,
                        "parking_fee": 0,
                        "vehicles": [],
                    },
                )
                # Per vehicle, so an invoice can show what each registration was billed for.
                total["vehicles"].append(
                    {
                        "vehicle_id": row["vehicle_id"],
                        "plate_number": row["plate_number"],
                        "vehicle_type": row["vehicle_type"],
                        "status": row["status"],
                        "registered_date": row["registered_date"],
                        "registration_months": row["registration_months"],
                        "minimum_end_date": registered_until.isoformat(),
                        "cancelled_date": row["cancelled_date"],
                        "created_at": row["created_at"],
                        "monthly_fee": row["monthly_fee"],
                        "months": months,
                        "card_fee": card_fee,
                    }
                )
                total["vehicle_count"] += 1
                total["vehicle_months"] += months
                total["monthly_fee"] += row["monthly_fee"]
                total["recurring_fee"] += row["monthly_fee"] * months
                total["card_fee"] += card_fee
                total["parking_fee"] += row["monthly_fee"] * months + card_fee
            return {"period": period, "items": [totals[key] for key in sorted(totals)]}
        query = "SELECT apartment_id,COUNT(*) AS vehicle_count,COALESCE(SUM(monthly_fee),0) AS monthly_fee,COALESCE(SUM(monthly_fee),0) AS tong_phi_thang FROM vehicles WHERE status='active'"
        args = []
        query += apartment_filter(args)
        return {
            "items": [dict(r) for r in get_db().execute(query + " GROUP BY apartment_id ORDER BY apartment_id", args)]
        }

    @app.get("/api/parking/guest-daily")
    @auth_or_internal("admin", "technician")
    def guest_daily():
        query, args = "SELECT * FROM guest_parking_daily WHERE 1=1", []
        for parameter, operator in (("from", ">="), ("to", "<=")):
            if request.args.get(parameter):
                query += f" AND parking_date{operator}?"
                args.append(iso_date(request.args[parameter], parameter))
        return {"items": [dict(r) for r in get_db().execute(query + " ORDER BY parking_date DESC", args)]}

    def daily_values(data):
        required(data, "parking_date", "daily_revenue")
        day = iso_date(data["parking_date"], "parking_date")
        if str(day) > local_today().isoformat():
            raise APIError("Không thể ghi nhận doanh thu của ngày tương lai.")
        return day, integer(data["daily_revenue"], "daily_revenue", min_value=0)

    @app.post("/api/parking/guest-daily")
    @require_auth("admin", "technician")
    def add_daily():
        day, revenue = daily_values(body())
        db = get_db()
        if db.execute("SELECT 1 FROM guest_parking_daily WHERE parking_date=?", (day,)).fetchone():
            raise APIError("Ngày này đã được ghi nhận. Hãy chỉnh sửa bản ghi hiện có.", 409)
        cursor = db.execute("INSERT INTO guest_parking_daily(parking_date,daily_revenue) VALUES (?,?)", (day, revenue))
        db.commit()
        return one(db, "guest_parking_daily", "record_id", cursor.lastrowid), 201

    @app.put("/api/parking/guest-daily/<int:record_id>")
    @require_auth("admin", "technician")
    def update_daily(record_id):
        db = get_db()
        old = one(db, "guest_parking_daily", "record_id", record_id)
        old.update(body())
        day, revenue = daily_values(old)
        if db.execute(
            "SELECT 1 FROM guest_parking_daily WHERE parking_date=? AND record_id<>?", (day, record_id)
        ).fetchone():
            raise APIError("Ngày này đã có bản ghi doanh thu.", 409)
        db.execute(
            "UPDATE guest_parking_daily SET parking_date=?,daily_revenue=? WHERE record_id=?", (day, revenue, record_id)
        )
        db.commit()
        return one(db, "guest_parking_daily", "record_id", record_id)

    return app


app = create_app()
if __name__ == "__main__":
    run(app, 5004)
