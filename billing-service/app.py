"""Invoices, payment settlement and reports; external domains are resolved over HTTP."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

import requests  # Patched by the billing tests; the SePay client uses this same module.
from flask import g, request

from shared.audit import record_audit
from shared.auth import require_auth
from shared.db import get_db, placeholders
from shared.http import call_service
from shared.ratelimit import SlidingWindow
from shared.web import APIError, body, create_app as base_app, integer, iso_date, required

KINDS = {"monthly": ("electricity_fee", "water_fee"), "semiannual": ("service_fee", "parking_fee")}
UTILITY_FIELDS = ("electricity_usage", "electricity_unit_price", "water_usage", "water_unit_price")
# Which services an invoice pays for; a service with no charge on the invoice cannot be cut.
SERVICES = {
    "monthly": (("electricity", "electricity_fee"), ("water", "water_fee")),
    "semiannual": (("common_service", "service_fee"), ("parking", "parking_fee")),
}
SERVICE_NAMES = {"electricity": "điện", "water": "nước", "common_service": "dịch vụ chung", "parking": "gửi xe"}
METHOD_NAMES = {"cash": "Tiền mặt", "bank_transfer": "Chuyển khoản", "sepay": "VietQR · SePay"}
# The parent role of invoice management: admin and technician both inherit every right below,
# so a change here applies to both. Reports stay admin-only.
BILLING_MANAGERS = ("admin", "technician")


def today():
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


def kind_check(kind):
    if kind not in KINDS:
        raise APIError("Loại hóa đơn không hợp lệ", 404)
    return kind


def payment_mode():
    return "sepay"


def owned_apartments():
    if g.user["role"] in BILLING_MANAGERS:
        return None
    resident = call_service("resident", "/api/residents/me")
    return [int(value) for value in resident.get("apartment_ids", [])]


def ensure_owner(invoice):
    apartments = owned_apartments()
    if apartments is not None and invoice["apartment_id"] not in apartments:
        raise APIError("Bạn không có quyền truy cập hóa đơn này", 403)


def ownership_filter(apartments, prefix=""):
    if apartments is None:
        return "1=1", []
    if not apartments:
        return "1=0", []
    return f"{prefix}apartment_id IN ({placeholders(apartments)})", apartments


def invoice_row(kind, invoice_id):
    kind_check(kind)
    row = get_db().execute(invoice_select(kind) + " WHERE i.invoice_id=?", (invoice_id,)).fetchone()
    if row is None:
        raise APIError("Không tìm thấy hóa đơn", 404)
    return dict(row, invoice_type=kind)


def invoice_select(kind):
    # Settlement time belongs to the successful payment, never to a QR/session
    # or the time a user pressed 'I have transferred'. Keep old records intact.
    kind_check(kind)
    return (
        f"SELECT i.*, (SELECT p.paid_at FROM {kind}_payments p "
        "WHERE p.invoice_id=i.invoice_id AND p.status='success' "
        "ORDER BY p.payment_id LIMIT 1) AS paid_at, "
        "(SELECT b.status FROM bank_payment_intents b "
        f"WHERE b.invoice_type='{kind}' AND b.invoice_id=i.invoice_id "
        "AND b.status IN ('pending','awaiting_confirmation') LIMIT 1) AS active_payment_status "
        f"FROM {kind}_invoices i"
    )


def vietnam_time(value):
    if not value:
        return "Chưa ghi nhận"
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)  # SQLite CURRENT_TIMESTAMP
    return parsed.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y %H:%M:%S")


def billing_context(invoice, paid_at=None):
    return {
        "apartment_id": invoice["apartment_id"],
        "invoice_created_at": invoice.get("created_at"),
        "paid_at": paid_at,
    }


def money(value, name):
    amount = integer(value, name, min_value=0)
    if amount > 1_000_000_000:
        raise APIError(f"{name} không được vượt quá 1 tỷ đồng")
    return amount


def validated_fees(kind, data, original=None):
    values = {}
    utility_values = {}
    metered = kind == "monthly" and (
        any(field in data for field in UTILITY_FIELDS)
        or any((original or {}).get(field) is not None for field in UTILITY_FIELDS)
    )
    if metered:
        for utility, title in (("electricity", "điện"), ("water", "nước")):
            usage_field, price_field = utility + "_usage", utility + "_unit_price"
            raw = data.get(usage_field, (original or {}).get(usage_field))
            try:
                usage = Decimal(str(raw))
            except (InvalidOperation, ValueError):
                raise APIError(f"Lượng {title} tiêu thụ phải là số từ 0 đến 1.000.000")
            if not usage.is_finite() or not 0 <= usage <= 1_000_000 or usage != usage.quantize(Decimal("0.001")):
                raise APIError(f"Lượng {title} tiêu thụ phải từ 0 đến 1.000.000, tối đa 3 chữ số thập phân")
            price = money(data.get(price_field, (original or {}).get(price_field)), f"Đơn giá {title}")
            if price == 0:
                raise APIError(f"Đơn giá {title} phải lớn hơn 0")
            fee_field = utility + "_fee"
            values[fee_field] = money(
                int((usage * price).quantize(Decimal("1"), rounding=ROUND_HALF_UP)), f"Tiền {title}"
            )
            if fee_field in data and money(data[fee_field], fee_field) != values[fee_field]:
                raise APIError(f"Tiền {title} phải bằng lượng tiêu thụ nhân đơn giá, làm tròn đến đồng")
            utility_values.update({usage_field: float(usage), price_field: price})
    for field in KINDS[kind]:
        if field not in values:
            values[field] = money(data.get(field, (original or {}).get(field, 0)), field)
    values["total_amount"] = sum(values.values())
    if values["total_amount"] <= 0:
        raise APIError("Tổng hóa đơn phải lớn hơn 0")
    if "total_amount" in data and money(data["total_amount"], "total_amount") != values["total_amount"]:
        raise APIError("Tổng tiền phải bằng tổng các khoản phí")
    values.update(utility_values)
    return values


def enqueue(event_id, destination, path, payload):
    get_db().execute(
        "INSERT OR IGNORE INTO billing_outbox(event_id,destination,path,payload) VALUES (?,?,?,?)",
        (event_id, destination, path, json.dumps(payload, ensure_ascii=False)),
    )


def enqueue_notification(event_id, **fields):
    payload = {"event_id": event_id, "type": "private", **fields}
    enqueue(event_id, "notification", "/api/notifications/events", payload)


def invoice_notification(kind, invoice, event, title, content):
    enqueue_notification(
        f"billing:{event}:{kind}:{invoice['invoice_id']}",
        title=title,
        content=content,
        target_apartment_id=invoice["apartment_id"],
        billing_context=billing_context(invoice, invoice.get("paid_at") if event == "paid" else None),
    )


def settlement_events(kind, invoice, method=None, environment=None):
    test_label = " (SePay Test — không chuyển tiền thật)" if environment == "test" else ""
    invoice_notification(
        kind,
        invoice,
        "paid",
        "Đã nhận thanh toán" + test_label,
        f"Hóa đơn {invoice['period']}: {invoice['total_amount']:,} VND đã thanh toán{test_label}.",
    )
    label = "điện nước" if kind == "monthly" else "dịch vụ 6 tháng"
    enqueue_notification(
        f"billing:paid-admin:{kind}:{invoice['invoice_id']}",
        target_role="admin",
        title="Thanh toán hóa đơn thành công",
        billing_context=billing_context(invoice, invoice.get("paid_at")),
        content=f"Hóa đơn {label} #{invoice['invoice_id']} kỳ {invoice['period']}: "
        f"{invoice['total_amount']:,} VND đã thanh toán{test_label}.",
    )
    cut = (
        get_db()
        .execute(
            "SELECT service FROM invoice_service_cuts WHERE invoice_type=? AND invoice_id=? AND status='cut'",
            (kind, invoice["invoice_id"]),
        )
        .fetchall()
    )
    if cut:
        names = ", ".join(SERVICE_NAMES[row["service"]] for row in cut)
        enqueue_notification(
            f"billing:restore-needed:{kind}:{invoice['invoice_id']}",
            target_role="technician",
            title="Cần cấp lại dịch vụ cho căn hộ",
            billing_context=billing_context(invoice, invoice.get("paid_at")),
            content=f"Hóa đơn kỳ {invoice['period']} đã được thanh toán. Vui lòng cấp lại dịch vụ: {names}.",
        )


def dispatch_outbox(limit=25):
    """Deliver after commit; failures stay durable for the minute retry job."""
    db = get_db()
    events = db.execute(
        "SELECT * FROM billing_outbox WHERE delivered_at IS NULL ORDER BY attempts,created_at LIMIT ?",
        (limit,),
    ).fetchall()
    delivered = 0
    for event in events:
        try:
            payload = json.loads(event["payload"])
            call_service(event["destination"], event["path"], method="POST", json=payload, internal=True)
        except Exception as exc:
            db.execute(
                "UPDATE billing_outbox SET attempts=attempts+1,last_error=? WHERE event_id=?",
                (str(exc)[:500], event["event_id"]),
            )
        else:
            db.execute(
                "UPDATE billing_outbox SET delivered_at=CURRENT_TIMESTAMP,attempts=attempts+1,last_error=NULL WHERE event_id=?",
                (event["event_id"],),
            )
            delivered += 1
        db.commit()
    return delivered


def mark_overdue(as_of=None):
    """Move past-due invoices to overdue and tell the resident once, on the transition."""
    cutoff = as_of or today().isoformat()
    db = get_db()
    count = 0
    keys = []
    with db:
        db.execute("BEGIN IMMEDIATE")
        for kind in KINDS:
            rows = db.execute(
                f"SELECT * FROM {kind}_invoices WHERE status='unpaid' AND due_date<?", (cutoff,)
            ).fetchall()
            for row in rows:
                invoice = dict(row)
                keys.append(f"{kind}:{row['invoice_id']}")
                db.execute(
                    f"UPDATE {kind}_invoices SET status='overdue' WHERE invoice_id=? AND status='unpaid'",
                    (row["invoice_id"],),
                )
                invoice_notification(
                    kind,
                    invoice,
                    "overdue",
                    "Hóa đơn đã quá hạn",
                    f"Hóa đơn {row['period']} số tiền {row['total_amount']:,} VND đã quá hạn ngày {row['due_date']}. Vui lòng thanh toán.",
                )
                count += 1
        if count:
            # Invoices can now turn overdue during the day too; each batch gets its own summary.
            batch = hashlib.sha256(",".join(keys).encode()).hexdigest()[:12]
            enqueue_notification(
                f"billing:overdue-summary:{cutoff}:{batch}",
                target_role="admin",
                notify_staff=True,
                title="Báo cáo hóa đơn quá hạn",
                content=f"Ngày {cutoff}: {count} hóa đơn mới quá hạn.",
            )
    return count


def send_due_reminders(as_of=None):
    cutoff = as_of or today().isoformat()
    db = get_db()
    count = 0
    with db:
        for kind in KINDS:
            rows = db.execute(
                f"SELECT * FROM {kind}_invoices WHERE status='unpaid' AND due_date BETWEEN ? AND date(?, '+3 days')",
                (cutoff, cutoff),
            ).fetchall()
            for row in rows:
                before = db.total_changes
                invoice_notification(
                    kind,
                    dict(row),
                    f"due-reminder:{cutoff}",
                    "Sắp đến hạn thanh toán",
                    f"Hóa đơn {row['period']}: {row['total_amount']:,} VND, hạn {row['due_date']}.",
                )
                count += db.total_changes > before
    return count


def record_payment(kind, invoice, method, transaction, environment=None):
    db = get_db()
    if invoice["status"] == "paid":
        raise APIError("Hóa đơn đã được thanh toán", 409)
    existing = db.execute(
        "SELECT payment_id FROM vw_billing_all_payments WHERE transaction_code=? AND status='success'", (transaction,)
    ).fetchone()
    if existing:
        raise APIError("Mã giao dịch đã được sử dụng", 409)
    paid_at = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(timespec="seconds")
    cursor = db.execute(
        f"INSERT INTO {kind}_payments(invoice_id,amount,payment_method,transaction_code,paid_at,status) VALUES (?,?,?,?,?,'success')",
        (invoice["invoice_id"], invoice["total_amount"], method, transaction, paid_at),
    )
    db.execute(f"UPDATE {kind}_invoices SET status='paid' WHERE invoice_id=?", (invoice["invoice_id"],))
    settlement_events(kind, dict(invoice, paid_at=paid_at), method, environment)
    return cursor.lastrowid


def payment_row(kind, payment_id):
    kind_check(kind)
    row = (
        get_db()
        .execute("SELECT * FROM vw_billing_all_payments WHERE invoice_type=? AND payment_id=?", (kind, payment_id))
        .fetchone()
    )
    if not row:
        raise APIError("Không tìm thấy giao dịch", 404)
    result = dict(row)
    result["receipt_url"] = f"/api/billing/payments/{kind}/{payment_id}/receipt"
    return result


# The directory predates Python package naming conventions. Load its sibling
# domain module in both the normal entrypoint and importlib-based test harness.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sepay_payments import SePayPayments

bank_payments = SePayPayments(invoice_row, record_payment, enqueue)
payment_configuration = bank_payments.configuration
order_row = bank_payments.order
public_order = bank_payments.public_order
reconcile_order = bank_payments.reconcile
reconcile_pending_orders = bank_payments.reconcile_pending


def service_states(kind, invoice):
    cuts = {
        row["service"]: row
        for row in get_db().execute(
            "SELECT * FROM invoice_service_cuts WHERE invoice_type=? AND invoice_id=?", (kind, invoice["invoice_id"])
        )
    }
    states = []
    for service, fee in SERVICES[kind]:
        if invoice[fee] > 0:
            cut = cuts.get(service)
            states.append(
                {
                    "service": service,
                    "status": cut["status"] if cut else "active",
                    "cut_at": cut["cut_at"] if cut else None,
                    "restored_at": cut["restored_at"] if cut else None,
                }
            )
    return states


def half_year(day):
    return f"{day[:4]}-H{1 if int(day[5:7]) <= 6 else 2}"


def vehicle_billing_state(vehicle_id):
    """Whether this vehicle's fee has been collected, and whether an extra invoice can collect it."""
    vehicle = call_service("parking", f"/api/parking/vehicles/{vehicle_id}")
    period = half_year(vehicle["registered_date"])
    extra_period = f"{period}-XE{vehicle_id}"
    db = get_db()
    apartment_id, created = vehicle["apartment_id"], vehicle.get("created_at")
    extra = db.execute(
        "SELECT invoice_id,status FROM semiannual_invoices WHERE apartment_id=? AND period=?",
        (apartment_id, extra_period),
    ).fetchone()
    # Length 7 selects the regular YYYY-Hn invoices. One issued before the vehicle existed cannot include its fee.
    covered = db.execute(
        "SELECT 1 FROM semiannual_invoices WHERE apartment_id=? AND status='paid' AND parking_fee>0 "
        "AND length(period)=7 AND period>=? AND (? IS NULL OR created_at>=?) LIMIT 1",
        (apartment_id, period, created, created),
    ).fetchone()
    base = db.execute(
        "SELECT created_at,parking_fee FROM semiannual_invoices WHERE apartment_id=? AND period=?",
        (apartment_id, period),
    ).fetchone()
    result = {
        "vehicle_id": vehicle_id,
        "period": period,
        "invoice_period": extra_period,
        "fee_paid": bool(covered or (extra and extra["status"] == "paid")),
        "available": False,
        "reason": None,
        "amount": 0,
    }
    if vehicle["status"] != "active":
        result["reason"] = "Đăng ký này đã hủy."
    elif extra:
        result["reason"] = f"Xe đã có hóa đơn bổ sung #DV{extra['invoice_id']:04d} cho kỳ {period}."
    elif base is None:
        result["reason"] = f"Kỳ {period} chưa phát hành hóa đơn dịch vụ; phí xe này sẽ tự tính khi lập hóa đơn kỳ đó."
    elif base["parking_fee"] > 0 and (created is None or created <= base["created_at"]):
        result["reason"] = f"Phí xe này đã nằm trong hóa đơn dịch vụ kỳ {period}."
    else:
        items = call_service(
            "parking",
            "/api/parking/summary",
            params={"apartment_id": apartment_id, "period": period, "vehicle_id": vehicle_id},
            internal=True,
        )["items"]
        result.update(
            amount=sum(row["parking_fee"] for row in items),
            months=sum(row["vehicle_months"] for row in items),
            monthly_fee=vehicle["monthly_fee"],
            card_fee=sum(row["card_fee"] for row in items),
            apartment_id=apartment_id,
            plate_number=vehicle["plate_number"],
        )
        result["available"] = result["amount"] > 0
        if not result["available"]:
            result["reason"] = "Xe không phát sinh phí trong kỳ này."
    return result


def invoice_vehicles(invoice):
    """The registrations behind a service invoice's parking fee, for its detail view."""
    if invoice["parking_fee"] <= 0:
        return []
    period, _, vehicle_id = invoice["period"].partition("-XE")
    params = {"apartment_id": invoice["apartment_id"], "period": period}
    if vehicle_id:
        params["vehicle_id"] = int(vehicle_id)
    try:
        items = call_service("parking", "/api/parking/summary", params=params, internal=True)["items"]
    except APIError:
        return []  # The invoice itself still opens while parking is unavailable.
    vehicles = [vehicle for item in items for vehicle in item.get("vehicles", [])]
    if not vehicle_id:
        # A vehicle added after the invoice was issued is billed on its own extra invoice.
        vehicles = [v for v in vehicles if not v.get("created_at") or v["created_at"] <= invoice["created_at"]]
    return vehicles


def owned_order(order_id):
    """The payment order, once the caller is confirmed to have access to its invoice."""
    order = order_row(order_id)
    ensure_owner(invoice_row(order["invoice_type"], order["invoice_id"]))
    return order


def has_open_payment(db, kind, invoice_id):
    return db.execute(
        "SELECT 1 FROM bank_payment_intents WHERE invoice_type=? AND invoice_id=? "
        "AND status IN ('pending','awaiting_confirmation')",
        (kind, invoice_id),
    ).fetchone()


def create_app():
    app = base_app("billing")
    # One press can read up to 20 pages from SePay; keep residents within its API limits.
    resident_reconciles = SlidingWindow(1, 15)

    @app.get("/api/billing/payment-config")
    @require_auth(*BILLING_MANAGERS, "resident")
    def payment_config():
        return payment_configuration()

    def issue_invoice(kind, apartment_id, period, due_date, fees):
        columns = ["apartment_id", "period", "due_date", *fees]
        values = [apartment_id, period, due_date, *fees.values()]
        db = get_db()
        with db:
            cursor = db.execute(
                f"INSERT INTO {kind}_invoices({','.join(columns)}) VALUES ({placeholders(columns)})",
                values,
            )
            invoice = invoice_row(kind, cursor.lastrowid)
            invoice_notification(
                kind,
                invoice,
                "created",
                "Hóa đơn mới",
                f"Hóa đơn kỳ {period}: {fees['total_amount']:,} VND, hạn thanh toán {due_date}.",
            )
        # A due date already in the past makes it overdue now, not at the next nightly scan.
        if due_date < today().isoformat():
            mark_overdue()
            invoice = invoice_row(kind, invoice["invoice_id"])
        return invoice

    @app.get("/api/billing/invoices/<kind>")
    @require_auth(*BILLING_MANAGERS, "resident")
    def list_invoices(kind):
        kind_check(kind)
        clause, args = ownership_filter(owned_apartments(), "i.")
        for field in ("status", "period", "apartment_id"):
            if request.args.get(field):
                clause += f" AND i.{field}=?"
                args.append(request.args[field])
        rows = (
            get_db()
            .execute(invoice_select(kind) + f" WHERE {clause} ORDER BY i.period DESC,i.invoice_id DESC", args)
            .fetchall()
        )
        return {"items": [dict(row, invoice_type=kind) for row in rows]}

    @app.post("/api/billing/invoices/<kind>")
    @require_auth(*BILLING_MANAGERS)
    def create_invoice(kind):
        kind_check(kind)
        data = body()
        required(data, "apartment_id", "period", "due_date")
        apartment_id = integer(data["apartment_id"], "apartment_id", min_value=1)
        period = str(data["period"])
        regex = r"\d{4}-(0[1-9]|1[0-2])" if kind == "monthly" else r"\d{4}-H[12]"
        if not re.fullmatch(regex, period):
            raise APIError("Kỳ hóa đơn phải là YYYY-MM hoặc YYYY-H1/H2 tương ứng")
        if int(period[:4]) < 2000:
            raise APIError("Năm của kỳ hóa đơn phải từ 2000")
        due_date = iso_date(data["due_date"], "due_date")
        call_service("resident", f"/api/apartments/{apartment_id}", internal=True)
        if kind == "semiannual" and "parking_fee" not in data:
            summary = call_service(
                "parking",
                "/api/parking/summary",
                params={"apartment_id": apartment_id, "period": period},
                internal=True,
            )
            data["parking_fee"] = sum(
                row.get("parking_fee", row.get("monthly_fee", row.get("tong_phi_thang", 0)) * 6)
                for row in summary.get("items", [])
            )
        try:
            return issue_invoice(kind, apartment_id, period, due_date, validated_fees(kind, data)), 201
        except sqlite3.IntegrityError:
            raise APIError("Căn hộ đã có hóa đơn trong kỳ này", 409)

    @app.get("/api/billing/invoices/<kind>/<int:invoice_id>")
    @require_auth(*BILLING_MANAGERS, "resident")
    def get_invoice(kind, invoice_id):
        invoice = invoice_row(kind, invoice_id)
        ensure_owner(invoice)
        result = dict(invoice, services=service_states(kind, invoice))
        if kind == "semiannual":
            result["vehicles"] = invoice_vehicles(invoice)
        return result

    @app.get("/api/billing/vehicle-billing/<int:vehicle_id>")
    @require_auth("admin")
    def vehicle_billing(vehicle_id):
        return vehicle_billing_state(vehicle_id)

    @app.post("/api/billing/vehicle-billing/<int:vehicle_id>/supplement")
    @require_auth("admin")
    def parking_supplement(vehicle_id):
        data = body()
        required(data, "due_date")
        due_date = iso_date(data["due_date"], "due_date")
        state = vehicle_billing_state(vehicle_id)
        if not state["available"]:
            raise APIError(state["reason"], 409)
        fees = validated_fees("semiannual", {"service_fee": 0, "parking_fee": state["amount"]})
        try:
            return issue_invoice("semiannual", state["apartment_id"], state["invoice_period"], due_date, fees), 201
        except sqlite3.IntegrityError:
            raise APIError("Xe đã có hóa đơn bổ sung trong kỳ này", 409)

    @app.get("/api/billing/services")
    @require_auth(*BILLING_MANAGERS)
    def service_invoices():
        """Overdue invoices, plus paid ones whose services are still waiting to be restored."""
        codes = {
            a["apartment_id"]: a["code"] for a in call_service("resident", "/api/apartments", internal=True)["items"]
        }
        items = []
        for kind in KINDS:
            rows = get_db().execute(
                invoice_select(kind) + " WHERE i.status='overdue' OR EXISTS (SELECT 1 FROM invoice_service_cuts c "
                "WHERE c.invoice_type=? AND c.invoice_id=i.invoice_id AND c.status='cut')",
                (kind,),
            )
            items += [
                dict(
                    row,
                    invoice_type=kind,
                    apartment_code=codes.get(row["apartment_id"]),
                    services=service_states(kind, row),
                )
                for row in rows.fetchall()
            ]
        return {"items": sorted(items, key=lambda row: (row["status"] == "paid", row["due_date"]))}

    @app.post("/api/billing/services/<kind>/<int:invoice_id>")
    @require_auth("technician")
    def update_service(kind, invoice_id):
        kind_check(kind)
        data = body()
        required(data, "service", "action")
        service, action = data["service"], data["action"]
        if action not in ("cut", "restore"):
            raise APIError("Thao tác phải là cut hoặc restore")
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            invoice = invoice_row(kind, invoice_id)
            fee = dict(SERVICES[kind]).get(service)
            if fee is None or invoice[fee] <= 0:
                raise APIError("Hóa đơn này không có dịch vụ đó")
            current = db.execute(
                "SELECT status FROM invoice_service_cuts WHERE invoice_type=? AND invoice_id=? AND service=?",
                (kind, invoice_id, service),
            ).fetchone()
            name = SERVICE_NAMES[service]
            if action == "cut":
                if invoice["status"] != "overdue":
                    raise APIError("Chỉ cắt dịch vụ của hóa đơn quá hạn", 409)
                if current:
                    raise APIError(f"Dịch vụ {name} đã được ghi nhận cắt", 409)
                db.execute(
                    "INSERT INTO invoice_service_cuts(invoice_type,invoice_id,service,cut_by_user_id) VALUES (?,?,?,?)",
                    (kind, invoice_id, service, g.user["user_id"]),
                )
                title = f"Đã tạm ngưng dịch vụ {name}"
                content = (
                    f"Hóa đơn kỳ {invoice['period']} ({invoice['total_amount']:,} VND) đã quá hạn nên dịch vụ {name} "
                    "của căn hộ bị tạm ngưng. Dịch vụ sẽ được cấp lại sau khi hóa đơn được thanh toán."
                )
            else:
                if invoice["status"] != "paid":
                    raise APIError("Chỉ cấp lại dịch vụ sau khi hóa đơn đã thanh toán", 409)
                if not current or current["status"] != "cut":
                    raise APIError(f"Dịch vụ {name} không ở trạng thái đã cắt", 409)
                db.execute(
                    "UPDATE invoice_service_cuts SET status='restored',restored_by_user_id=?,restored_at=CURRENT_TIMESTAMP "
                    "WHERE invoice_type=? AND invoice_id=? AND service=?",
                    (g.user["user_id"], kind, invoice_id, service),
                )
                title = f"Đã cấp lại dịch vụ {name}"
                content = (
                    f"Dịch vụ {name} của căn hộ đã được cấp lại sau khi thanh toán hóa đơn kỳ {invoice['period']}."
                )
            enqueue_notification(
                f"billing:service-{action}:{kind}:{invoice_id}:{service}",
                target_apartment_id=invoice["apartment_id"],
                notify_staff=True,
                title=title,
                content=content,
                billing_context=billing_context(invoice, invoice.get("paid_at")),
            )
        dispatch_outbox()
        return dict(invoice_row(kind, invoice_id), services=service_states(kind, invoice_row(kind, invoice_id)))

    @app.patch("/api/billing/invoices/<kind>/<int:invoice_id>")
    @require_auth(*BILLING_MANAGERS)
    def edit_invoice(kind, invoice_id):
        kind_check(kind)
        data = body()
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            invoice = invoice_row(kind, invoice_id)
            if invoice["status"] != "unpaid":
                raise APIError("Chỉ được sửa hóa đơn chưa thanh toán và chưa quá hạn", 409)
            if has_open_payment(db, kind, invoice_id):
                raise APIError("Hóa đơn đang có lệnh thanh toán chờ xử lý", 409)
            # Saved QR codes remain usable at the bank after a session expires.
            if (
                set(data) - {"due_date"}
                and db.execute(
                    "SELECT 1 FROM bank_payment_intents WHERE invoice_type=? AND invoice_id=?", (kind, invoice_id)
                ).fetchone()
            ):
                raise APIError(
                    "Hóa đơn đã phát hành mã chuyển khoản; không thay đổi số tiền để tránh lệch đối soát", 409
                )
            allowed = {*KINDS[kind], "total_amount", "due_date"}
            if kind == "monthly":
                allowed.update(UTILITY_FIELDS)
            if set(data) - allowed:
                raise APIError("Chỉ được sửa phí và hạn thanh toán")
            values = validated_fees(kind, data, invoice)
            values["due_date"] = iso_date(data.get("due_date", invoice["due_date"]), "due_date")
            db.execute(
                f"UPDATE {kind}_invoices SET {','.join(key + '=?' for key in values)} WHERE invoice_id=?",
                [*values.values(), invoice_id],
            )
        if values["due_date"] < today().isoformat():
            mark_overdue()
        return invoice_row(kind, invoice_id)

    @app.post("/api/billing/invoices/<kind>/<int:invoice_id>/pay")
    @require_auth(*BILLING_MANAGERS)
    def manual_payment(kind, invoice_id):
        kind_check(kind)
        data = body()
        method = data.get("payment_method", "cash")
        if method not in ("cash", "bank_transfer"):
            raise APIError("Chỉ ghi nhận tiền mặt hoặc chuyển khoản đã thực nhận; VietQR tự xác nhận qua SePay")
        raw_key = request.headers.get("Idempotency-Key")
        if raw_key and len(raw_key) > 120:
            raise APIError("Idempotency-Key tối đa 120 ký tự")
        key = f"{g.user['user_id']}:{raw_key}" if raw_key else None
        transaction = str(data.get("transaction_code") or f"MANUAL-{uuid.uuid4().hex}")
        if len(transaction) > 150:
            raise APIError("Mã giao dịch quá dài")
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            if key:
                existing = db.execute("SELECT * FROM billing_payment_keys WHERE request_key=?", (key,)).fetchone()
                if existing:
                    if (existing["invoice_type"], existing["invoice_id"], existing["payment_method"]) != (
                        kind,
                        invoice_id,
                        method,
                    ):
                        raise APIError("Idempotency-Key đã dùng cho yêu cầu khác", 409)
                    previous = payment_row(kind, existing["payment_id"])
                    if (
                        "amount" in data
                        and money(data["amount"], "amount") != previous["amount"]
                        or "transaction_code" in data
                        and data["transaction_code"] != previous["transaction_code"]
                    ):
                        raise APIError("Idempotency-Key đã dùng với nội dung khác", 409)
                    return previous
            invoice = invoice_row(kind, invoice_id)
            if "amount" in data and money(data["amount"], "amount") != invoice["total_amount"]:
                raise APIError("Cần thanh toán toàn bộ và đúng số tiền hóa đơn")
            if has_open_payment(db, kind, invoice_id):
                raise APIError("Đang có lệnh QR chờ xử lý; không ghi nhận trùng thanh toán", 409)
            if db.execute(
                "SELECT 1 FROM bank_transactions WHERE invoice_type=? AND invoice_id=? AND allocated_amount>0",
                (kind, invoice_id),
            ).fetchone():
                raise APIError(
                    "Đã nhận tiền qua SePay; hãy đối soát khoản đã nhận, không ghi nhận thêm toàn bộ hóa đơn", 409
                )
            payment_id = record_payment(kind, invoice, method, transaction)
            if key:
                db.execute(
                    "INSERT INTO billing_payment_keys VALUES (?,?,?,?,?)", (key, kind, invoice_id, payment_id, method)
                )
            record_audit(
                db,
                "manual_payment_recorded",
                f"{kind}_invoice",
                invoice_id,
                {
                    "payment_id": payment_id,
                    "method": method,
                    "amount": invoice["total_amount"],
                    "transaction_code": transaction,
                },
            )
        return payment_row(kind, payment_id), 201

    @app.post("/api/billing/invoices/<kind>/<int:invoice_id>/release-payment")
    @require_auth(*BILLING_MANAGERS)
    def release_payment(kind, invoice_id):
        invoice_row(kind, invoice_id)
        note = body().get("note")
        if not isinstance(note, str) or not 1 <= len(note.strip()) <= 500:
            raise APIError("Cần ghi lý do mở khóa từ 1 đến 500 ký tự")
        return bank_payments.release(kind, invoice_id, note.strip())

    @app.post("/api/billing/invoices/<kind>/<int:invoice_id>/checkout")
    @require_auth("resident")
    def checkout(kind, invoice_id):
        invoice = invoice_row(kind, invoice_id)
        ensure_owner(invoice)
        return bank_payments.checkout(invoice)

    @app.get("/api/billing/orders/<order_id>")
    @require_auth(*BILLING_MANAGERS, "resident")
    def get_order(order_id):
        order = owned_order(order_id)
        return public_order(order)

    @app.post("/api/billing/orders/<order_id>/reconcile")
    @require_auth(*BILLING_MANAGERS, "resident")
    def refresh_order(order_id):
        order = owned_order(order_id)
        if g.user["role"] == "resident" and not resident_reconciles.hit(order_id):
            return public_order(order)
        return reconcile_order(order)

    @app.get("/api/billing/orders/<order_id>/qr")
    @require_auth("resident")
    def order_qr(order_id):
        order = owned_order(order_id)
        return bank_payments.qr(order)

    @app.post("/api/billing/orders/<order_id>/confirm-transfer")
    @require_auth("resident")
    def confirm_transfer(order_id):
        order = owned_order(order_id)
        return bank_payments.owner_action(order, "confirm")

    @app.post("/api/billing/orders/<order_id>/cancel")
    @require_auth("resident")
    def cancel_order(order_id):
        order = owned_order(order_id)
        return bank_payments.owner_action(order, "cancel")

    @app.post("/api/billing/sepay/webhook")
    def sepay_webhook():
        return bank_payments.webhook()

    @app.get("/api/billing/sepay/transactions")
    @require_auth(*BILLING_MANAGERS)
    def bank_transactions():
        return {
            "items": [
                dict(row)
                for row in get_db().execute("SELECT * FROM bank_transactions ORDER BY transaction_id DESC LIMIT 1000")
            ]
        }

    @app.post("/api/billing/sepay/transactions/<int:transaction_id>/resolve")
    @require_auth(*BILLING_MANAGERS)
    def resolve_bank_transaction(transaction_id):
        from sepay_payments import stamp

        data = body()
        resolution, note = data.get("resolution"), data.get("note")
        if (
            resolution not in ("refunded", "retained", "reviewed")
            or not isinstance(note, str)
            or not 1 <= len(note.strip()) <= 2000
        ):
            raise APIError("Cần chọn cách xử lý và ghi chú từ 1 đến 2000 ký tự")
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM bank_transactions WHERE transaction_id=?", (transaction_id,)).fetchone()
            if row is None:
                raise APIError("Không tìm thấy giao dịch ngân hàng", 404)
            if not row["issue"] or row["status"] == "ignored":
                raise APIError("Giao dịch này không có khoản cần xử lý", 409)
            if resolution in ("refunded", "retained") and not row["unallocated_amount"]:
                raise APIError("Chỉ ghi nhận hoàn/giữ tiền cho khoản chưa phân bổ", 409)
            if row["resolution"] != resolution or row["resolution_note"] != note.strip():
                db.execute(
                    "UPDATE bank_transactions SET resolution=?,resolution_note=?,resolved_by_user_id=?,resolved_at=? WHERE transaction_id=?",
                    (resolution, note.strip(), g.user["user_id"], stamp(), transaction_id),
                )
                db.execute(
                    "INSERT INTO bank_transaction_resolutions(transaction_id,resolution,note,user_id,created_at) VALUES (?,?,?,?,?)",
                    (transaction_id, resolution, note.strip(), g.user["user_id"], stamp()),
                )
        return dict(db.execute("SELECT * FROM bank_transactions WHERE transaction_id=?", (transaction_id,)).fetchone())

    @app.get("/api/billing/payments")
    @require_auth(*BILLING_MANAGERS, "resident")
    def list_payments():
        clause, args = ownership_filter(owned_apartments())
        if request.args.get("kind"):
            clause += " AND invoice_type=?"
            args.append(kind_check(request.args["kind"]))
        rows = (
            get_db()
            .execute(
                f"SELECT * FROM vw_billing_all_payments WHERE {clause} ORDER BY paid_at DESC,payment_id DESC", args
            )
            .fetchall()
        )
        return {
            "items": [
                dict(row, receipt_url=f"/api/billing/payments/{row['invoice_type']}/{row['payment_id']}/receipt")
                for row in rows
            ]
        }

    @app.get("/api/billing/payments/<kind>/<int:payment_id>/receipt")
    @require_auth(*BILLING_MANAGERS, "resident")
    def receipt(kind, payment_id):
        payment = payment_row(kind, payment_id)
        ensure_owner(payment)
        if payment["status"] != "success":
            raise APIError("Chỉ xuất biên nhận cho giao dịch thành công", 409)
        invoice = invoice_row(kind, payment["invoice_id"])
        apartment = call_service("resident", f"/api/apartments/{payment['apartment_id']}", internal=True)
        rows = [
            ("Mã biên nhận", f"{kind.upper()}-{payment_id}"),
            ("Căn hộ", apartment["code"]),
            ("Kỳ dịch vụ", payment["period"]),
            ("Số tiền", f"{payment['amount']:,} VND"),
            ("Hình thức", METHOD_NAMES.get(payment["payment_method"], payment["payment_method"])),
            ("Mã giao dịch", payment["transaction_code"]),
            ("Thời gian lập hóa đơn (giờ Việt Nam)", vietnam_time(invoice["created_at"])),
            ("Thời gian thanh toán (giờ Việt Nam)", vietnam_time(payment["paid_at"])),
        ]
        if kind == "monthly" and invoice.get("electricity_usage") is not None:
            rows.extend(
                (
                    (
                        "Cách tính tiền điện",
                        f"{invoice['electricity_usage']:g} kWh × {invoice['electricity_unit_price']:,} VND/kWh = {invoice['electricity_fee']:,} VND",
                    ),
                    (
                        "Cách tính tiền nước",
                        f"{invoice['water_usage']:g} m³ × {invoice['water_unit_price']:,} VND/m³ = {invoice['water_fee']:,} VND",
                    ),
                )
            )
        code = str(payment["transaction_code"] or "")
        notice = None
        if code.startswith("DEMO-"):
            notice = "MÔ PHỎNG DEMO — không xác nhận chuyển tiền thật."
        elif code.startswith("SEPAY-TEST-"):
            notice = "SEPAY TEST — giao dịch thử nghiệm, không thu tiền thật."
        return {
            "title": "Biên nhận thanh toán điện tử",
            "issuer": "Hệ thống Quản lý chung cư",
            "notice": notice,
            "rows": [[label, str(value or "")] for label, value in rows],
            "footer": "Biên nhận dịch vụ nội bộ, không thay thế hóa đơn thuế.",
        }

    @app.get("/api/billing/summary")
    @require_auth(*BILLING_MANAGERS, "resident")
    def summary():
        clause, args = ownership_filter(owned_apartments())
        row = (
            get_db()
            .execute(
                f"""SELECT COUNT(*) invoice_count,
            COALESCE(SUM(status='paid'),0) paid_count, COALESCE(SUM(status='overdue'),0) overdue_count,
            COALESCE(SUM(CASE WHEN status<>'paid' THEN total_amount ELSE 0 END),0) outstanding_amount,
            COALESCE(SUM(CASE WHEN status='overdue' THEN total_amount ELSE 0 END),0) overdue_amount,
            COALESCE(SUM(CASE WHEN status='paid' THEN total_amount ELSE 0 END),0) paid_amount
            FROM vw_billing_all_invoices WHERE {clause}""",
                args,
            )
            .fetchone()
        )
        return dict(row, payment_mode=payment_mode())

    @app.get("/api/billing/reports")
    @require_auth("admin")
    def reports():
        year = integer(request.args.get("year", today().year), "year", min_value=2000)
        if year > 9999:
            raise APIError("Năm không hợp lệ")
        group = request.args.get("group", "month")
        if group not in ("month", "quarter"):
            raise APIError("group phải là month hoặc quarter")
        rows = (
            get_db()
            .execute("SELECT * FROM vw_billing_all_invoices WHERE substr(report_period,1,4)=?", (str(year),))
            .fetchall()
        )

        def key(period):
            month = int(period[5:7])
            return period[:7] if group == "month" else f"{year}-Q{(month - 1) // 3 + 1}"

        buckets = {}
        for number in range(1, 13 if group == "month" else 5):
            period = f"{year}-{number:02d}" if group == "month" else f"{year}-Q{number}"
            buckets[period] = {
                "period": period,
                "billed_amount": 0,
                "collected_amount": 0,
                "outstanding_amount": 0,
                "invoice_count": 0,
                "paid_count": 0,
                "monthly_billed_amount": 0,
                "semiannual_billed_amount": 0,
                "monthly_collected_amount": 0,
                "semiannual_collected_amount": 0,
            }
        for row in rows:
            item = buckets[key(row["report_period"])]
            item["billed_amount"] += row["total_amount"]
            item[row["invoice_type"] + "_billed_amount"] += row["total_amount"]
            item["invoice_count"] += 1
            if row["status"] == "paid":
                item["paid_count"] += 1
                item["collected_amount"] += row["total_amount"]
                item[row["invoice_type"] + "_collected_amount"] += row["total_amount"]
            else:
                item["outstanding_amount"] += row["total_amount"]
        # Guest parking is cash counted per day by Parking; it is revenue but not an invoice.
        guests = call_service(
            "parking",
            "/api/parking/guest-daily",
            internal=True,
            params={"from": f"{year}-01-01", "to": f"{year}-12-31"},
        )["items"]
        for item in buckets.values():
            item["guest_amount"] = 0
        for row in guests:
            buckets[key(row["parking_date"])]["guest_amount"] += row["daily_revenue"]
        for item in buckets.values():
            item["revenue_amount"] = item["collected_amount"] + item["guest_amount"]
        totals = {
            field: sum(row[field] for row in buckets.values())
            for field in next(iter(buckets.values()))
            if field != "period"
        }
        monthly = [
            dict(row)
            for row in get_db().execute(
                "SELECT * FROM vw_monthly_revenue_report WHERE substr(period,1,4)=? ORDER BY period", (str(year),)
            )
        ]
        return {
            "items": list(buckets.values()),
            "totals": totals,
            "monthly_breakdown": monthly,
            "accounting_note": "Phát hành, đã thu và còn phải thu cùng tính theo kỳ của hóa đơn (H1 tháng 1, H2 tháng 7), nên phát hành = đã thu + còn phải thu. Vé vãng lai không có hóa đơn: tính theo ngày ghi nhận và chỉ cộng vào tổng doanh thu.",
        }

    @app.post("/api/billing/overdue/run")
    @require_auth(*BILLING_MANAGERS)
    def run_overdue():
        count = mark_overdue()
        reminders = send_due_reminders()
        return {"updated_count": count, "reminder_count": reminders, "date": today().isoformat()}

    app.extensions["billing_jobs"] = {
        "overdue": mark_overdue,
        "reminders": send_due_reminders,
        "outbox": dispatch_outbox,
        "sepay": reconcile_pending_orders,
    }
    return app


app = create_app()

if __name__ == "__main__":
    from scheduler import start_scheduler
    from shared.web import run

    start_scheduler(app)
    run(app, 5003)
