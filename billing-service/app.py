"""Invoices, payment settlement and reports; external domains are resolved over HTTP."""
from __future__ import annotations

import html
import json
import os
import re
import sqlite3
import uuid
import sys
from pathlib import Path
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from zoneinfo import ZoneInfo

import requests
from flask import Response, g, request

from shared.auth import require_auth
from shared.db import get_db
from shared.http import call_service
from shared.web import APIError, body, create_app as base_app, integer, iso_date, required

KINDS = {"monthly": ("electricity_fee", "water_fee"),
         "semiannual": ("service_fee", "parking_fee")}
UTILITY_FIELDS = ("electricity_usage", "electricity_unit_price", "water_usage", "water_unit_price")


def today():
    return datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).date()


def kind_check(kind):
    if kind not in KINDS:
        raise APIError("Loại hóa đơn không hợp lệ", 404)
    return kind


def payment_mode():
    return "sepay"


def owned_apartments():
    if g.user["role"] == "admin":
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
    return f"{prefix}apartment_id IN ({','.join('?' for _ in apartments)})", apartments


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
    return (f"SELECT i.*, (SELECT p.paid_at FROM {kind}_payments p "
            "WHERE p.invoice_id=i.invoice_id AND p.status='success' "
            "ORDER BY p.payment_id LIMIT 1) AS paid_at "
            f"FROM {kind}_invoices i")


def vietnam_time(value):
    if not value:
        return "Chưa ghi nhận"
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)  # SQLite CURRENT_TIMESTAMP
    return parsed.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).strftime("%d/%m/%Y %H:%M:%S")


def billing_context(invoice, paid_at=None):
    return {"apartment_id": invoice["apartment_id"],
            "invoice_created_at": invoice.get("created_at"), "paid_at": paid_at}


def money(value, name):
    amount = integer(value, name, min_value=0)
    if amount > 1_000_000_000:
        raise APIError(f"{name} không được vượt quá 1 tỷ đồng")
    return amount


def validated_fees(kind, data, original=None):
    values = {}
    utility_values = {}
    metered = kind == "monthly" and (any(field in data for field in UTILITY_FIELDS) or
                                     any((original or {}).get(field) is not None for field in UTILITY_FIELDS))
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
            values[fee_field] = money(int((usage * price).quantize(Decimal("1"), rounding=ROUND_HALF_UP)), f"Tiền {title}")
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
        (event_id, destination, path, json.dumps(payload, ensure_ascii=False)))


def invoice_notification(kind, invoice, event, title, content):
    event_id = f"billing:{event}:{kind}:{invoice['invoice_id']}"
    enqueue(event_id, "notification", "/api/notifications/events", {
        "event_id": event_id, "type": "private", "title": title, "content": content,
        "target_apartment_id": invoice["apartment_id"],
        "billing_context": billing_context(invoice, invoice.get("paid_at") if event == "paid" else None)})


def settlement_events(kind, invoice, method=None, environment=None):
    test_label = " (SePay Test — không chuyển tiền thật)" if environment == "test" else ""
    invoice_notification(kind, invoice, "paid", "Đã nhận thanh toán" + test_label,
                         f"Hóa đơn {invoice['period']}: {invoice['total_amount']:,} VND đã thanh toán{test_label}.")
    label = "điện nước" if kind == "monthly" else "dịch vụ 6 tháng"
    enqueue(f"billing:paid-admin:{kind}:{invoice['invoice_id']}", "notification", "/api/notifications/events", {
        "event_id": f"billing:paid-admin:{kind}:{invoice['invoice_id']}",
        "type": "private", "target_role": "admin", "title": "Thanh toán hóa đơn thành công",
        "billing_context": billing_context(invoice, invoice.get("paid_at")),
        "content": f"Hóa đơn {label} #{invoice['invoice_id']} kỳ {invoice['period']}: "
                   f"{invoice['total_amount']:,} VND đã thanh toán{test_label}."})
    if invoice["status"] == "overdue":
        overdue = outstanding_overdue(invoice["apartment_id"])
        event_id = f"settled:{kind}:{invoice['invoice_id']}"
        enqueue(event_id, "maintenance", "/api/maintenance/events", {
            "event_id": event_id, "event_type": "invoice_settled", "invoice_type": kind,
            "invoice_id": invoice["invoice_id"], "apartment_id": invoice["apartment_id"],
            "period": invoice["period"], "all_debts_settled": overdue == 0})


def outstanding_overdue(apartment_id):
    return get_db().execute(
        "SELECT COUNT(*) FROM vw_billing_all_invoices WHERE apartment_id=? "
        "AND (status='overdue' OR (status='unpaid' AND due_date<?))",
        (apartment_id, today().isoformat())).fetchone()[0]


def dispatch_outbox(limit=25):
    """Deliver after commit; failures stay durable for the minute retry job."""
    db = get_db()
    events = db.execute("SELECT * FROM billing_outbox WHERE delivered_at IS NULL "
                        "ORDER BY attempts,CASE destination WHEN 'maintenance' THEN 0 ELSE 1 END,created_at LIMIT ?",
                        (limit,)).fetchall()
    delivered = 0
    for event in events:
        try:
            payload = json.loads(event["payload"])
            # A delayed settlement must reflect debts that may have appeared since enqueue.
            if event["destination"] == "maintenance":
                count = outstanding_overdue(payload["apartment_id"])
                payload["all_debts_settled"] = count == 0
            call_service(event["destination"], event["path"], method="POST", json=payload, internal=True)
        except Exception as exc:
            db.execute("UPDATE billing_outbox SET attempts=attempts+1,last_error=? WHERE event_id=?",
                       (str(exc)[:500], event["event_id"]))
        else:
            db.execute("UPDATE billing_outbox SET delivered_at=CURRENT_TIMESTAMP,attempts=attempts+1,last_error=NULL WHERE event_id=?",
                       (event["event_id"],))
            delivered += 1
        db.commit()
    return delivered


def mark_overdue(as_of=None):
    """Original DB triggers create cut tickets exactly once on the transition."""
    cutoff = as_of or today().isoformat()
    db = get_db()
    count = 0
    with db:
        db.execute("BEGIN IMMEDIATE")
        for kind in KINDS:
            rows = db.execute(f"SELECT * FROM {kind}_invoices WHERE status='unpaid' AND due_date<?", (cutoff,)).fetchall()
            for row in rows:
                invoice = dict(row)
                db.execute(f"UPDATE {kind}_invoices SET status='overdue' WHERE invoice_id=? AND status='unpaid'", (row["invoice_id"],))
                invoice_notification(kind, invoice, "overdue", "Hóa đơn đã quá hạn",
                                     f"Hóa đơn {row['period']} số tiền {row['total_amount']:,} VND đã quá hạn ngày {row['due_date']}. Vui lòng thanh toán.")
                count += 1
        if count:
            event_id = f"billing:overdue-summary:{cutoff}"
            enqueue(event_id, "notification", "/api/notifications/events", {
                "event_id": event_id, "type": "private", "target_role": "admin",
                "title": "Báo cáo hóa đơn quá hạn", "content": f"Ngày {cutoff}: {count} hóa đơn mới quá hạn."})
    return count


def send_due_reminders(as_of=None):
    cutoff = as_of or today().isoformat()
    db = get_db()
    count = 0
    with db:
        for kind in KINDS:
            rows = db.execute(f"SELECT * FROM {kind}_invoices WHERE status='unpaid' "
                              "AND due_date BETWEEN ? AND date(?, '+3 days')", (cutoff, cutoff)).fetchall()
            for row in rows:
                before = db.total_changes
                invoice_notification(kind, dict(row), f"due-reminder:{cutoff}", "Sắp đến hạn thanh toán",
                                     f"Hóa đơn {row['period']}: {row['total_amount']:,} VND, hạn {row['due_date']}.")
                count += db.total_changes > before
    return count


def record_payment(kind, invoice, method, transaction, environment=None):
    db = get_db()
    if invoice["status"] == "paid":
        raise APIError("Hóa đơn đã được thanh toán", 409)
    existing = db.execute("SELECT payment_id FROM vw_billing_all_payments WHERE transaction_code=? AND status='success'", (transaction,)).fetchone()
    if existing:
        raise APIError("Mã giao dịch đã được sử dụng", 409)
    paid_at = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(timespec="seconds")
    cursor = db.execute(
        f"INSERT INTO {kind}_payments(invoice_id,amount,payment_method,transaction_code,paid_at,status) VALUES (?,?,?,?,?,'success')",
        (invoice["invoice_id"], invoice["total_amount"], method, transaction, paid_at))
    db.execute(f"UPDATE {kind}_invoices SET status='paid' WHERE invoice_id=?", (invoice["invoice_id"],))
    settlement_events(kind, dict(invoice, paid_at=paid_at), method, environment)
    return cursor.lastrowid


def payment_row(kind, payment_id):
    kind_check(kind)
    row = get_db().execute("SELECT * FROM vw_billing_all_payments WHERE invoice_type=? AND payment_id=?",
                           (kind, payment_id)).fetchone()
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


def create_app():
    app = base_app("billing")

    @app.get("/api/billing/payment-config")
    @require_auth("admin", "resident")
    def payment_config():
        return payment_configuration()

    @app.get("/api/billing/invoices/<kind>")
    @require_auth("admin", "resident")
    def list_invoices(kind):
        kind_check(kind)
        clause, args = ownership_filter(owned_apartments(), "i.")
        for field in ("status", "period", "apartment_id"):
            if request.args.get(field):
                clause += f" AND i.{field}=?"
                args.append(request.args[field])
        rows = get_db().execute(invoice_select(kind) + f" WHERE {clause} ORDER BY i.period DESC,i.invoice_id DESC", args).fetchall()
        return {"items": [dict(row, invoice_type=kind) for row in rows]}

    @app.post("/api/billing/invoices/<kind>")
    @require_auth("admin")
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
            summary = call_service("parking", "/api/parking/summary", params={"apartment_id": apartment_id, "period": period}, internal=True)
            data["parking_fee"] = sum(row.get("parking_fee", row.get("monthly_fee", row.get("tong_phi_thang", 0)) * 6)
                                      for row in summary.get("items", []))
        fees = validated_fees(kind, data)
        columns = ["apartment_id", "period", "due_date", *fees]
        values = [apartment_id, period, due_date, *fees.values()]
        db = get_db()
        try:
            with db:
                cursor = db.execute(f"INSERT INTO {kind}_invoices({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})", values)
                invoice = invoice_row(kind, cursor.lastrowid)
                invoice_notification(kind, invoice, "created", "Hóa đơn mới",
                                     f"Hóa đơn kỳ {period}: {fees['total_amount']:,} VND, hạn thanh toán {due_date}.")
        except sqlite3.IntegrityError:
            raise APIError("Căn hộ đã có hóa đơn trong kỳ này", 409)
        return invoice, 201

    @app.get("/api/billing/invoices/<kind>/<int:invoice_id>")
    @require_auth("admin", "resident")
    def get_invoice(kind, invoice_id):
        invoice = invoice_row(kind, invoice_id)
        ensure_owner(invoice)
        return invoice

    @app.patch("/api/billing/invoices/<kind>/<int:invoice_id>")
    @require_auth("admin")
    def edit_invoice(kind, invoice_id):
        kind_check(kind)
        data = body()
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            invoice = invoice_row(kind, invoice_id)
            if invoice["status"] != "unpaid":
                raise APIError("Chỉ được sửa hóa đơn chưa thanh toán và chưa quá hạn", 409)
            if db.execute("SELECT 1 FROM bank_payment_intents WHERE invoice_type=? AND invoice_id=? AND status IN ('pending','awaiting_confirmation')", (kind, invoice_id)).fetchone():
                raise APIError("Hóa đơn đang có lệnh thanh toán chờ xử lý", 409)
            # Saved QR codes remain usable at the bank after a session expires.
            if set(data) - {"due_date"} and db.execute(
                    "SELECT 1 FROM bank_payment_intents WHERE invoice_type=? AND invoice_id=?",
                    (kind, invoice_id)).fetchone():
                raise APIError("Hóa đơn đã phát hành mã chuyển khoản; không thay đổi số tiền để tránh lệch đối soát", 409)
            allowed = {*KINDS[kind], "total_amount", "due_date"}
            if kind == "monthly":
                allowed.update(UTILITY_FIELDS)
            if set(data) - allowed:
                raise APIError("Chỉ được sửa phí và hạn thanh toán")
            values = validated_fees(kind, data, invoice)
            values["due_date"] = iso_date(data.get("due_date", invoice["due_date"]), "due_date")
            db.execute(f"UPDATE {kind}_invoices SET {','.join(key+'=?' for key in values)} WHERE invoice_id=?", [*values.values(), invoice_id])
        return invoice_row(kind, invoice_id)

    @app.post("/api/billing/invoices/<kind>/<int:invoice_id>/pay")
    @require_auth("admin")
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
                    if (existing["invoice_type"], existing["invoice_id"], existing["payment_method"]) != (kind, invoice_id, method):
                        raise APIError("Idempotency-Key đã dùng cho yêu cầu khác", 409)
                    previous = payment_row(kind, existing["payment_id"])
                    if ("amount" in data and money(data["amount"], "amount") != previous["amount"]
                            or "transaction_code" in data and data["transaction_code"] != previous["transaction_code"]):
                        raise APIError("Idempotency-Key đã dùng với nội dung khác", 409)
                    return previous
            invoice = invoice_row(kind, invoice_id)
            if "amount" in data and money(data["amount"], "amount") != invoice["total_amount"]:
                raise APIError("Cần thanh toán toàn bộ và đúng số tiền hóa đơn")
            if db.execute("SELECT 1 FROM bank_payment_intents WHERE invoice_type=? AND invoice_id=? AND status IN ('pending','awaiting_confirmation')", (kind, invoice_id)).fetchone():
                raise APIError("Đang có lệnh QR chờ xử lý; không ghi nhận trùng thanh toán", 409)
            if db.execute("SELECT 1 FROM bank_transactions WHERE invoice_type=? AND invoice_id=? AND allocated_amount>0",
                          (kind, invoice_id)).fetchone():
                raise APIError("Đã nhận tiền qua SePay; hãy đối soát khoản đã nhận, không ghi nhận thêm toàn bộ hóa đơn", 409)
            payment_id = record_payment(kind, invoice, method, transaction)
            if key:
                db.execute("INSERT INTO billing_payment_keys VALUES (?,?,?,?,?)", (key, kind, invoice_id, payment_id, method))
        return payment_row(kind, payment_id), 201

    @app.post("/api/billing/invoices/<kind>/<int:invoice_id>/checkout")
    @require_auth("resident")
    def checkout(kind, invoice_id):
        invoice = invoice_row(kind, invoice_id)
        ensure_owner(invoice)
        return bank_payments.checkout(invoice)

    @app.get("/api/billing/orders/<order_id>")
    @require_auth("admin", "resident")
    def get_order(order_id):
        order = order_row(order_id)
        ensure_owner(invoice_row(order["invoice_type"], order["invoice_id"]))
        return public_order(order)

    @app.post("/api/billing/orders/<order_id>/reconcile")
    @require_auth("admin", "resident")
    def refresh_order(order_id):
        order = order_row(order_id)
        ensure_owner(invoice_row(order["invoice_type"], order["invoice_id"]))
        return reconcile_order(order)

    @app.get("/api/billing/orders/<order_id>/qr")
    @require_auth("resident")
    def order_qr(order_id):
        order = order_row(order_id)
        ensure_owner(invoice_row(order["invoice_type"], order["invoice_id"]))
        return bank_payments.qr(order)

    @app.post("/api/billing/orders/<order_id>/confirm-transfer")
    @require_auth("resident")
    def confirm_transfer(order_id):
        order = order_row(order_id)
        ensure_owner(invoice_row(order["invoice_type"], order["invoice_id"]))
        return bank_payments.owner_action(order, "confirm")

    @app.post("/api/billing/orders/<order_id>/cancel")
    @require_auth("resident")
    def cancel_order(order_id):
        order = order_row(order_id)
        ensure_owner(invoice_row(order["invoice_type"], order["invoice_id"]))
        return bank_payments.owner_action(order, "cancel")

    @app.post("/api/billing/sepay/webhook")
    def sepay_webhook():
        return bank_payments.webhook()

    @app.get("/api/billing/sepay/transactions")
    @require_auth("admin")
    def bank_transactions():
        return {"items": [dict(row) for row in get_db().execute(
            "SELECT * FROM bank_transactions ORDER BY transaction_id DESC LIMIT 1000")]}

    @app.post("/api/billing/sepay/transactions/<int:transaction_id>/resolve")
    @require_auth("admin")
    def resolve_bank_transaction(transaction_id):
        from sepay_payments import stamp
        data = body()
        resolution, note = data.get("resolution"), data.get("note")
        if resolution not in ("refunded", "retained", "reviewed") or not isinstance(note, str) or not 1 <= len(note.strip()) <= 2000:
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
                db.execute("UPDATE bank_transactions SET resolution=?,resolution_note=?,resolved_by_user_id=?,resolved_at=? WHERE transaction_id=?",
                           (resolution, note.strip(), g.user["user_id"], stamp(), transaction_id))
                db.execute("INSERT INTO bank_transaction_resolutions(transaction_id,resolution,note,user_id,created_at) VALUES (?,?,?,?,?)",
                           (transaction_id, resolution, note.strip(), g.user["user_id"], stamp()))
        return dict(db.execute("SELECT * FROM bank_transactions WHERE transaction_id=?", (transaction_id,)).fetchone())

    @app.get("/api/billing/payments")
    @require_auth("admin", "resident")
    def list_payments():
        clause, args = ownership_filter(owned_apartments())
        if request.args.get("kind"):
            clause += " AND invoice_type=?"
            args.append(kind_check(request.args["kind"]))
        rows = get_db().execute(f"SELECT * FROM vw_billing_all_payments WHERE {clause} ORDER BY paid_at DESC,payment_id DESC", args).fetchall()
        return {"items": [dict(row, receipt_url=f"/api/billing/payments/{row['invoice_type']}/{row['payment_id']}/receipt") for row in rows]}

    @app.get("/api/billing/payments/<kind>/<int:payment_id>/receipt")
    @require_auth("admin", "resident")
    def receipt(kind, payment_id):
        payment = payment_row(kind, payment_id)
        ensure_owner(payment)
        if payment["status"] != "success":
            raise APIError("Chỉ xuất biên nhận cho giao dịch thành công", 409)
        escape = lambda value: html.escape(str(value or ""))
        invoice = invoice_row(kind, payment["invoice_id"])
        rows = [("Mã biên nhận", f"{kind.upper()}-{payment_id}"), ("Căn hộ (ID)", payment["apartment_id"]),
                ("Kỳ dịch vụ", payment["period"]), ("Số tiền", f"{payment['amount']:,} VND"),
                ("Hình thức", payment["payment_method"]), ("Mã giao dịch", payment["transaction_code"]),
                ("Thời gian lập hóa đơn (giờ Việt Nam)", vietnam_time(invoice["created_at"])),
                ("Thời gian thanh toán (giờ Việt Nam)", vietnam_time(payment["paid_at"]))]
        if kind == "monthly" and invoice.get("electricity_usage") is not None:
            rows.extend((
                ("Cách tính tiền điện", f"{invoice['electricity_usage']:g} kWh × {invoice['electricity_unit_price']:,} VND/kWh = {invoice['electricity_fee']:,} VND"),
                ("Cách tính tiền nước", f"{invoice['water_usage']:g} m³ × {invoice['water_unit_price']:,} VND/m³ = {invoice['water_fee']:,} VND")))
        content = "".join(f"<tr><th>{escape(label)}</th><td>{escape(value)}</td></tr>" for label, value in rows)
        demo = str(payment["transaction_code"] or "").startswith("DEMO-")
        test_payment = str(payment["transaction_code"] or "").startswith("SEPAY-TEST-")
        legacy_test = str(payment["transaction_code"] or "").startswith("MOMO-")
        markup = ('<!doctype html><html lang="vi"><meta charset="utf-8"><title>Biên nhận thanh toán</title>'
                  '<style>body{font:16px system-ui;max-width:760px;margin:60px auto;color:#183d35}th,td{text-align:left;padding:14px;border-bottom:1px solid #ddd}table{width:100%}h1{font-size:30px}</style>'
                  '<h1>Biên nhận thanh toán điện tử</h1><p>Hệ thống Quản lý chung cư</p>'
                  + ('<p><strong>MÔ PHỎNG DEMO — không xác nhận chuyển tiền thật.</strong></p>' if demo else '')
                  + ('<p><strong>SEPAY TEST — giao dịch thử nghiệm, không thu tiền thật.</strong></p>' if test_payment else '')
                  + ('<p><strong>GIAO DỊCH TEST CŨ — không xác nhận thu tiền thật.</strong></p>' if legacy_test else '')
                  + f'<table>{content}</table><p>Biên nhận dịch vụ nội bộ, không thay thế hóa đơn thuế.</p></html>')
        return Response(markup, mimetype="text/html", headers={"Content-Disposition": f'attachment; filename="receipt-{kind}-{payment_id}.html"'})

    @app.get("/api/billing/summary")
    @require_auth("admin", "resident")
    def summary():
        clause, args = ownership_filter(owned_apartments())
        row = get_db().execute(f"""SELECT COUNT(*) invoice_count,
            COALESCE(SUM(status='paid'),0) paid_count, COALESCE(SUM(status='overdue'),0) overdue_count,
            COALESCE(SUM(CASE WHEN status<>'paid' THEN total_amount ELSE 0 END),0) outstanding_amount,
            COALESCE(SUM(CASE WHEN status='overdue' THEN total_amount ELSE 0 END),0) overdue_amount,
            COALESCE(SUM(CASE WHEN status='paid' THEN total_amount ELSE 0 END),0) paid_amount
            FROM vw_billing_all_invoices WHERE {clause}""", args).fetchone()
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
        rows = get_db().execute("SELECT * FROM vw_billing_all_invoices WHERE substr(report_period,1,4)=?", (str(year),)).fetchall()
        payments = get_db().execute("SELECT * FROM vw_billing_all_payments WHERE status='success' AND substr(paid_at,1,4)=?", (str(year),)).fetchall()
        def key(period):
            month = int(period[5:7])
            return period[:7] if group == "month" else f"{year}-Q{(month - 1) // 3 + 1}"
        buckets = {}
        for number in range(1, 13 if group == "month" else 5):
            period = f"{year}-{number:02d}" if group == "month" else f"{year}-Q{number}"
            buckets[period] = {"period": period, "billed_amount": 0, "collected_amount": 0,
                               "outstanding_amount": 0, "invoice_count": 0, "paid_count": 0}
        for row in rows:
            item = buckets[key(row["report_period"])]
            item["billed_amount"] += row["total_amount"]
            item["invoice_count"] += 1
            item["paid_count"] += row["status"] == "paid"
            item["outstanding_amount"] += row["total_amount"] if row["status"] != "paid" else 0
        for row in payments:
            buckets[key(row["paid_at"])]["collected_amount"] += row["amount"]
        totals = {field: sum(row[field] for row in buckets.values()) for field in ("billed_amount", "collected_amount", "outstanding_amount", "invoice_count", "paid_count")}
        monthly = [dict(row) for row in get_db().execute("SELECT * FROM vw_monthly_revenue_report WHERE substr(period,1,4)=? ORDER BY period", (str(year),))]
        return {"items": list(buckets.values()), "totals": totals, "monthly_breakdown": monthly,
                "accounting_note": "Phát hành theo kỳ dịch vụ (H1 tháng 1, H2 tháng 7); thực thu theo ngày thanh toán. Phí vãng lai thuộc Parking Service."}

    @app.post("/api/billing/overdue/run")
    @require_auth("admin")
    def run_overdue():
        count = mark_overdue()
        reminders = send_due_reminders()
        return {"updated_count": count, "reminder_count": reminders, "date": today().isoformat()}

    app.extensions["billing_jobs"] = {"overdue": mark_overdue, "reminders": send_due_reminders,
                                      "outbox": dispatch_outbox, "sepay": reconcile_pending_orders}
    return app


app = create_app()

if __name__ == "__main__":
    from scheduler import start_scheduler
    from shared.web import run
    start_scheduler(app)
    run(app, 5003)
