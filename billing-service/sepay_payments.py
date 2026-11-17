"""SePay bank ledger, household payment sessions and verified settlement.

The bank can accept a saved QR more than once. Every incoming transfer is kept;
only its allocated part settles an invoice. Nothing here initiates a refund.
"""

from datetime import datetime, timedelta, timezone
import ipaddress
import os
import re
import unicodedata
import uuid
from urllib.parse import urlparse

import requests
from flask import Response, g, request

from shared.audit import record_audit
from shared.db import get_db
from shared.web import APIError, body, integer, secure_compare

# A QR saved in a banking app still works after its session closes, so recently
# closed sessions stay in the reconciliation sweep for a bounded time.
RECONCILE_CLOSED_FOR = timedelta(days=3)


def now():
    return datetime.now(timezone.utc)


def stamp(value=None):
    return (value or now()).isoformat(timespec="seconds")


def normalized(value):
    return re.sub(
        r"[^A-Z0-9]", "", unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode().upper()
    )


class SePayPayments:
    def __init__(self, invoice_row, record_payment, enqueue):
        self.invoice_row, self.record_payment, self.enqueue = invoice_row, record_payment, enqueue

    def configuration(self):
        names = (
            "SEPAY_BANK_CODE",
            "SEPAY_BANK_NAME",
            "SEPAY_ACCOUNT_NUMBER",
            "SEPAY_ACCOUNT_NAME",
            "SEPAY_WEBHOOK_API_KEY",
            "SEPAY_WEBHOOK_URL",
        )
        missing = [key for key in names if not os.getenv(key, "").strip()]
        issues = []
        environment = os.getenv("SEPAY_ENV", "test").strip()
        if os.getenv("PAYMENT_MODE", "sepay").strip() != "sepay":
            issues.append("PAYMENT_MODE phải là sepay")
        if environment not in ("test", "live"):
            issues.append("SEPAY_ENV phải là test hoặc live")
        key = os.getenv("SEPAY_WEBHOOK_API_KEY", "")
        if key and len(key.strip()) < 32:
            issues.append("SEPAY_WEBHOOK_API_KEY cần ít nhất 32 ký tự")
        for name, pattern in (
            ("SEPAY_BANK_CODE", r"[A-Za-z0-9]{2,30}"),
            ("SEPAY_ACCOUNT_NUMBER", r"[A-Za-z0-9]{1,50}"),
            ("SEPAY_PAYMENT_PREFIX", r"[A-Z]{2,5}"),
        ):
            value = os.getenv(name, "QLCC" if name == "SEPAY_PAYMENT_PREFIX" else "").strip()
            if value and not re.fullmatch(pattern, value):
                issues.append(f"{name} không hợp lệ")
        # This integration uses a main bank account, not bank-specific VA flows.
        unsupported = {
            "OCB",
            "970448",
            "KLB",
            "KIENLONGBANK",
            "970452",
            "MSB",
            "970426",
            "BIDV",
            "970418",
            "ICB",
            "VIETINBANK",
            "970415",
        }
        if any(normalized(os.getenv(name, "")) in unsupported for name in ("SEPAY_BANK_CODE", "SEPAY_BANK_NAME")):
            issues.append(
                "Bản hiện tại chưa hỗ trợ VA hoặc quy tắc QR riêng của ngân hàng này; dùng tài khoản Vietcombank hoặc ngân hàng không yêu cầu VA"
            )
        try:
            window = int(os.getenv("SEPAY_PAYMENT_WINDOW_MINUTES", "15"))
            if not 2 <= window <= 60:
                raise ValueError()
        except ValueError:
            issues.append("SEPAY_PAYMENT_WINDOW_MINUTES phải từ 2 đến 60")
        url = os.getenv("SEPAY_WEBHOOK_URL", "").strip()
        if url:
            try:
                parsed = urlparse(url)
                host = parsed.hostname or ""
                try:
                    public = ipaddress.ip_address(host).is_global
                except ValueError:
                    public = "." in host and not host.endswith((".local", ".localhost"))
                valid = (
                    parsed.scheme == "https"
                    and public
                    and parsed.path == "/api/billing/sepay/webhook"
                    and not parsed.username
                    and not parsed.password
                    and not parsed.query
                    and not parsed.fragment
                    and parsed.port in (None, 443)
                    and not any(c.isspace() for c in url)
                )
            except ValueError:
                valid = False
            if not valid:
                issues.append("SEPAY_WEBHOOK_URL phải là HTTPS công khai với đường dẫn /api/billing/sepay/webhook")
        token, account_id = os.getenv("SEPAY_API_TOKEN", "").strip(), os.getenv("SEPAY_BANK_ACCOUNT_ID", "").strip()
        if bool(token) != bool(account_id):
            issues.append("Đối soát API cần cả SEPAY_API_TOKEN và SEPAY_BANK_ACCOUNT_ID")
        if account_id:
            try:
                uuid.UUID(account_id)
            except ValueError:
                issues.append("SEPAY_BANK_ACCOUNT_ID phải là UUID của API v2")
        ready = not missing and not issues
        message = (
            "SePay Test Mode: chỉ dùng tài khoản Test và mô phỏng tiền vào trên SePay."
            if environment == "test"
            else "VietQR Live: xác nhận thanh toán qua SePay."
        )
        if not ready:
            message = "Chưa sẵn sàng thanh toán: " + "; ".join(
                (["thiếu " + ", ".join(missing)] if missing else []) + issues
            )
        return {
            "mode": "sepay",
            "environment": environment,
            "ready": ready,
            "missing": missing,
            "issues": issues,
            "message": message,
            "reconciliation_enabled": bool(ready and token and account_id),
        }

    def require_ready(self):
        config = self.configuration()
        if not config["ready"]:
            raise APIError(config["message"], 503)
        return config

    def order(self, order_id):
        row = get_db().execute("SELECT * FROM bank_payment_intents WHERE order_id=?", (order_id,)).fetchone()
        if row is None:
            raise APIError("Không tìm thấy phiên thanh toán VietQR", 404)
        return dict(row)

    def expire(self):
        get_db().execute(
            "UPDATE bank_payment_intents SET status='expired',updated_at=? WHERE status='pending' AND expires_at<=?",
            (stamp(), stamp()),
        )

    def allocated(self, order):
        return (
            get_db()
            .execute(
                "SELECT COALESCE(SUM(allocated_amount),0) FROM bank_transactions "
                "WHERE environment=? AND invoice_type=? AND invoice_id=?",
                (order["environment"], order["invoice_type"], order["invoice_id"]),
            )
            .fetchone()[0]
        )

    def public_order(self, order):
        # Expiring a view does not revoke a QR already saved in a banking app.
        if order["status"] == "pending" and order["expires_at"] <= stamp():
            with get_db():
                self.expire()
            order = self.order(order["order_id"])
        invoice = self.invoice_row(order["invoice_type"], order["invoice_id"])
        paid = self.allocated(order)
        remaining = max(0, invoice["total_amount"] - paid) if invoice["status"] != "paid" else 0
        user = getattr(g, "user", None)
        is_owner = bool(user and user["role"] == "resident" and user["user_id"] == order["payer_user_id"])
        can_pay = bool(
            is_owner
            and order["status"] == "pending"
            and remaining
            and self.configuration()["ready"]
            and order["environment"] == self.configuration()["environment"]
        )
        result = {
            key: order[key]
            for key in (
                "order_id",
                "invoice_type",
                "invoice_id",
                "amount",
                "environment",
                "status",
                "payment_id",
                "payer_user_id",
                "created_at",
                "expires_at",
            )
        }
        if invoice["status"] == "paid":
            result["status"] = "success"
        result.update(
            mode="sepay",
            is_owner=is_owner,
            can_pay=can_pay,
            paid_amount=paid,
            remaining_amount=remaining,
            invoice_created_at=invoice.get("created_at"),
            paid_at=invoice.get("paid_at"),
            transfer_content=order["transfer_content"] if can_pay else None,
            bank={
                "code": order["bank_code"],
                "name": order["bank_name"],
                "account_number": order["account_number"],
                "account_name": order["account_name"],
            }
            if can_pay
            else None,
            qr_image_url=f"/api/billing/orders/{order['order_id']}/qr" if can_pay else None,
            receipt_url=f"/api/billing/payments/{order['invoice_type']}/{order['payment_id']}/receipt"
            if order["payment_id"]
            else None,
        )
        result["message"] = (
            "Hóa đơn đã thanh toán. Không chuyển khoản thêm."
            if result["status"] == "success"
            else "Đã báo chuyển khoản, đang chờ ngân hàng xác nhận. Không chuyển thêm lần nữa."
            if order["status"] == "awaiting_confirmation"
            else "Thành viên khác đang thực hiện thanh toán. Vui lòng chờ cập nhật."
            if not is_owner and order["status"] == "pending"
            else "Phiên đã đóng; nếu đã chuyển tiền, hãy chờ đối soát và không chuyển lại."
            if order["status"] in ("expired", "cancelled")
            else "Chỉ chuyển số tiền còn lại một lần và giữ nguyên nội dung thanh toán."
        )
        if order.get("last_error"):
            result["message"] += " " + order["last_error"]
        return result

    def checkout(self, invoice):
        config = self.require_ready()
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            self.expire()
            invoice = self.invoice_row(invoice["invoice_type"], invoice["invoice_id"])
            if invoice["status"] == "paid":
                raise APIError("Hóa đơn đã được thanh toán", 409)
            row = db.execute(
                "SELECT * FROM bank_payment_intents WHERE environment=? AND invoice_type=? "
                "AND invoice_id=? AND status IN ('pending','awaiting_confirmation')",
                (config["environment"], invoice["invoice_type"], invoice["invoice_id"]),
            ).fetchone()
            created = row is None
            if created:
                order_id = "VQR-" + uuid.uuid4().hex
                reference = os.getenv("SEPAY_PAYMENT_PREFIX", "QLCC").strip() + uuid.uuid4().hex[:12].upper()
                expires = stamp(now() + timedelta(minutes=int(os.getenv("SEPAY_PAYMENT_WINDOW_MINUTES", "15"))))
                db.execute(
                    "INSERT INTO bank_payment_intents(order_id,invoice_type,invoice_id,payer_user_id,environment,amount,"
                    "transfer_content,bank_code,bank_name,account_number,account_name,status,created_at,expires_at,updated_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,'pending',?,?,?)",
                    (
                        order_id,
                        invoice["invoice_type"],
                        invoice["invoice_id"],
                        g.user["user_id"],
                        config["environment"],
                        invoice["total_amount"],
                        reference,
                        os.environ["SEPAY_BANK_CODE"].strip(),
                        os.environ["SEPAY_BANK_NAME"].strip(),
                        os.environ["SEPAY_ACCOUNT_NUMBER"].strip(),
                        os.environ["SEPAY_ACCOUNT_NAME"].strip(),
                        stamp(),
                        expires,
                        stamp(),
                    ),
                )
                row = self.order(order_id)
        return self.public_order(dict(row)), 201 if created else 200

    def owner_action(self, order, action):
        if g.user["user_id"] != order["payer_user_id"] or g.user["role"] != "resident":
            raise APIError("Chỉ người đang giữ phiên thanh toán được thực hiện thao tác này", 403)
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            self.expire()
            order = self.order(order["order_id"])
            if self.invoice_row(order["invoice_type"], order["invoice_id"])["status"] == "paid":
                return self.public_order(order)
            if action == "confirm" and order["status"] == "awaiting_confirmation":
                return self.public_order(order)
            if order["status"] != "pending":
                raise APIError("Phiên không còn chờ chuyển khoản; không chuyển thêm", 409)
            if action == "cancel" and self.allocated(order):
                raise APIError(
                    "Đã nhận một phần tiền; không hủy phiên, hãy thanh toán số còn lại hoặc liên hệ Ban quản lý", 409
                )
            db.execute(
                "UPDATE bank_payment_intents SET status=?,updated_at=? WHERE order_id=?",
                ("awaiting_confirmation" if action == "confirm" else "cancelled", stamp(), order["order_id"]),
            )
        return self.public_order(self.order(order["order_id"]))

    def release(self, kind, invoice_id, note):
        """Management closes a session whose 'I transferred' claim the bank never confirmed.

        The clock never does this, because money may still be on its way. A transfer that
        arrives later is still matched by its reference, so closing here cannot lose it.
        """
        db = get_db()
        row = db.execute(
            "SELECT * FROM bank_payment_intents WHERE invoice_type=? AND invoice_id=? "
            "AND status='awaiting_confirmation'",
            (kind, invoice_id),
        ).fetchone()
        if row is None:
            raise APIError("Hóa đơn không có phiên đang chờ ngân hàng xác nhận", 409)
        order = dict(row)
        config = self.configuration()
        bank_checked = bool(config["reconciliation_enabled"] and order["environment"] == config["environment"])
        if bank_checked:
            # Raises when SePay cannot be read: an unverified session stays locked.
            self.reconcile(order)
        with db:
            db.execute("BEGIN IMMEDIATE")
            order = self.order(order["order_id"])
            if order["status"] == "awaiting_confirmation":
                if self.allocated(order):
                    raise APIError("Ngân hàng đã ghi nhận tiền cho hóa đơn này; không thể mở khóa phiên", 409)
                db.execute(
                    "UPDATE bank_payment_intents SET status='expired',updated_at=? WHERE order_id=?",
                    (stamp(), order["order_id"]),
                )
                record_audit(
                    db,
                    "payment_session_released",
                    "bank_payment_intent",
                    order["order_id"],
                    {"invoice_type": kind, "invoice_id": invoice_id, "note": note, "bank_checked": bank_checked},
                )
        return self.public_order(self.order(order["order_id"]))

    def qr(self, order):
        public = self.public_order(order)
        if not public["can_pay"]:
            raise APIError("Phiên không cho phép hiển thị QR; hãy kiểm tra trạng thái hóa đơn", 403)
        params = {
            "acc": order["account_number"],
            "bank": order["bank_code"],
            "amount": public["remaining_amount"],
            "des": order["transfer_content"],
            "template": "compact",
            "holder": order["account_name"],
        }
        # Fixed HTTPS origin; never build a QR from arbitrary user-provided URLs.
        try:
            result = requests.get("https://vietqr.app/img", params=params, timeout=(5, 15), allow_redirects=False)
            result.raise_for_status()
            if (
                not result.headers.get("Content-Type", "").lower().startswith("image/png")
                or len(result.content) > 2_000_000
            ):
                raise ValueError()
        except (requests.RequestException, ValueError):
            raise APIError(
                "Chưa tải được VietQR. Không chuyển khoản nếu chưa kiểm tra đúng số tiền và người nhận.", 502
            )
        # A webhook can settle the invoice while the image provider is responding.
        latest = self.public_order(self.order(order["order_id"]))
        if not latest["can_pay"] or latest["remaining_amount"] != public["remaining_amount"]:
            raise APIError("Trạng thái thanh toán đã thay đổi; hãy tải lại hóa đơn", 409)
        return Response(result.content, mimetype="image/png")

    def reference(self, data):
        # Configuration changes only affect new orders. Saved QR codes and late
        # webhooks must still match references issued under earlier prefixes.
        prefixes = {os.getenv("SEPAY_PAYMENT_PREFIX", "QLCC").strip()}
        prefixes.update(
            row[0]
            for row in get_db().execute(
                "SELECT DISTINCT substr(transfer_content,1,length(transfer_content)-12) FROM bank_payment_intents"
            )
        )
        alternatives = "|".join(re.escape(prefix) for prefix in sorted(prefixes) if re.fullmatch(r"[A-Z]{2,5}", prefix))
        pattern = rf"(?<![A-Z0-9])(?:{alternatives})[0-9A-F]{{12}}(?![A-Z0-9])"
        candidates = set(re.findall(pattern, str(data.get("content", "")).upper()))
        code = data.get("code")
        if code is not None and not isinstance(code, str):
            raise APIError("Mã thanh toán không hợp lệ")
        if code and re.fullmatch(pattern, code.strip().upper()):
            candidates.add(code.strip().upper())
        return next(iter(candidates)) if len(candidates) == 1 else ""

    def transaction(self, data):
        config = self.require_ready()
        provider_id = data.get("id")
        valid_id = type(provider_id) is int and provider_id > 0
        if isinstance(provider_id, str):
            valid_id = bool(re.fullmatch(r"[1-9][0-9]{0,99}", provider_id))
            if not valid_id:
                try:
                    valid_id = bool(uuid.UUID(provider_id).int) and len(provider_id) == 36
                except ValueError:
                    pass
        if not valid_id:
            raise APIError("Mã giao dịch SePay không hợp lệ")
        direction = data.get("transferType")
        if direction not in ("in", "out"):
            raise APIError("Loại giao dịch SePay không hợp lệ")
        amount = integer(data.get("transferAmount"), "transferAmount", 1)
        if amount > 1_000_000_000:
            raise APIError("Số tiền vượt giới hạn xử lý")
        account = data.get("accountNumber")
        bank = data.get("gateway")
        if not isinstance(account, str) or not re.fullmatch(r"[A-Za-z0-9]{1,50}", account):
            raise APIError("Số tài khoản trong giao dịch không hợp lệ")
        if not isinstance(bank, str) or not 1 <= len(bank.strip()) <= 100:
            raise APIError("Ngân hàng trong giao dịch không hợp lệ")
        bank_reference = data.get("referenceCode") or ""
        if not isinstance(bank_reference, str) or len(bank_reference) > 150:
            raise APIError("Mã tham chiếu ngân hàng không hợp lệ")
        bank_reference = bank_reference.strip()
        reference = self.reference(data)
        environment = config["environment"]
        db = get_db()
        with db:
            db.execute("BEGIN IMMEDIATE")
            intent_row = db.execute(
                "SELECT * FROM bank_payment_intents WHERE transfer_content=? AND environment=?",
                (reference, environment),
            ).fetchone()
            intent = dict(intent_row) if intent_row else None
            expected_name = intent["bank_name"] if intent else os.environ["SEPAY_BANK_NAME"].strip()
            expected_code = intent["bank_code"] if intent else os.environ["SEPAY_BANK_CODE"].strip()
            bank_matches = normalized(bank) in (normalized(expected_name), normalized(expected_code))
            canonical_bank = normalized(expected_name) if bank_matches else normalized(bank)
            existing = db.execute(
                "SELECT t.* FROM bank_transaction_aliases a JOIN bank_transactions t USING(transaction_id) "
                "WHERE a.environment=? AND a.provider_id=?",
                (environment, str(provider_id)),
            ).fetchone()
            if existing is None and bank_reference:
                existing = db.execute(
                    "SELECT * FROM bank_transactions WHERE environment=? AND bank_name=? "
                    "AND account_number=? AND bank_reference=?",
                    (environment, canonical_bank, account, bank_reference),
                ).fetchone()
            if existing:
                if any(
                    existing[key] != value
                    for key, value in (
                        ("account_number", account),
                        ("bank_name", canonical_bank),
                        ("amount", amount),
                        ("direction", direction),
                        ("reference", reference),
                        ("bank_reference", bank_reference),
                    )
                ):
                    raise APIError("Mã giao dịch đã tồn tại với nội dung khác; cần đối soát", 409)
                db.execute(
                    "INSERT OR IGNORE INTO bank_transaction_aliases VALUES (?,?,?)",
                    (environment, str(provider_id), existing["transaction_id"]),
                )
                return dict(existing)
            invoice = self.invoice_row(intent["invoice_type"], intent["invoice_id"]) if intent else None
            expected_account = intent["account_number"] if intent else os.environ["SEPAY_ACCOUNT_NUMBER"].strip()
            allocated, unallocated, status, issue = (
                0,
                amount,
                "unmatched",
                "Không tìm thấy mã hóa đơn duy nhất trong giao dịch.",
            )
            if direction != "in" or account != expected_account or not bank_matches:
                status, issue, unallocated = "ignored", "Giao dịch không phải tiền vào đúng tài khoản nhận.", 0
            elif not bank_reference:
                issue = "Thiếu mã tham chiếu ngân hàng; cần đối soát trước khi ghi nhận."
            elif invoice:
                if invoice["status"] == "paid":
                    status, issue = "duplicate", "Hóa đơn đã trả nhưng có thêm một khoản chuyển tiền khác."
                else:
                    paid = self.allocated(intent)
                    allocated = min(amount, max(0, invoice["total_amount"] - paid))
                    unallocated = amount - allocated
                    status = (
                        "overpaid"
                        if unallocated
                        else "matched"
                        if paid + allocated >= invoice["total_amount"]
                        else "partial"
                    )
                    issue = (
                        "Có tiền chuyển vượt số còn phải trả."
                        if unallocated
                        else "Đã nhận một phần tiền; chưa đủ thanh toán hóa đơn."
                        if status == "partial"
                        else ""
                    )
            received_at = str(data.get("transactionDate") or stamp())[:80]
            cursor = db.execute(
                "INSERT INTO bank_transactions(environment,provider_id,account_number,bank_name,bank_reference,reference,direction,"
                "amount,allocated_amount,unallocated_amount,status,issue,invoice_type,invoice_id,received_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    environment,
                    str(provider_id),
                    account,
                    canonical_bank,
                    bank_reference,
                    reference,
                    direction,
                    amount,
                    allocated,
                    unallocated,
                    status,
                    issue,
                    invoice["invoice_type"] if invoice else None,
                    invoice["invoice_id"] if invoice else None,
                    received_at,
                ),
            )
            transaction_id = cursor.lastrowid
            db.execute(
                "INSERT INTO bank_transaction_aliases VALUES (?,?,?)", (environment, str(provider_id), transaction_id)
            )
            if allocated and invoice:
                if self.allocated(intent) >= invoice["total_amount"]:
                    payment_id = self.record_payment(
                        invoice["invoice_type"],
                        invoice,
                        "bank_transfer",
                        f"SEPAY-{environment.upper()}-{intent['order_id']}",
                        environment=environment,
                    )
                    db.execute(
                        "UPDATE bank_payment_intents SET status='success',payment_id=?,updated_at=? "
                        "WHERE invoice_type=? AND invoice_id=? AND environment=?",
                        (payment_id, stamp(), invoice["invoice_type"], invoice["invoice_id"], environment),
                    )
                else:
                    active = db.execute(
                        "SELECT order_id FROM bank_payment_intents WHERE invoice_type=? AND invoice_id=? "
                        "AND environment=? AND status IN ('pending','awaiting_confirmation')",
                        (invoice["invoice_type"], invoice["invoice_id"], environment),
                    ).fetchone()
                    if active:
                        expires = stamp(now() + timedelta(minutes=int(os.getenv("SEPAY_PAYMENT_WINDOW_MINUTES", "15"))))
                        db.execute(
                            "UPDATE bank_payment_intents SET status='pending',expires_at=?,updated_at=? WHERE order_id=?",
                            (expires, stamp(), active["order_id"]),
                        )
            if issue and status != "ignored":
                event = f"billing:bank-review:{environment}:{transaction_id}"
                self.enqueue(
                    event,
                    "notification",
                    "/api/notifications/events",
                    {
                        "event_id": event,
                        "type": "private",
                        "target_role": "admin",
                        "title": "Cần đối soát khoản chuyển ngân hàng",
                        "content": f"{'[SePay Test] ' if environment == 'test' else ''}Giao dịch #{transaction_id}: {amount:,} VND. "
                        f"{issue} Tiền chưa phân bổ: {unallocated:,} VND. Không tự hoàn tiền.",
                    },
                )
            return dict(
                db.execute("SELECT * FROM bank_transactions WHERE transaction_id=?", (transaction_id,)).fetchone()
            )

    def webhook(self):
        self.require_ready()
        provided = request.headers.get("Authorization", "")
        expected = "Apikey " + os.environ["SEPAY_WEBHOOK_API_KEY"].strip()
        if not secure_compare(provided, expected):
            raise APIError("Xác thực webhook SePay không hợp lệ", 403)
        self.transaction(body())
        # 201 also supports SePay webhooks that require this exact success code.
        return {"success": True}, 201

    def reconcile(self, order):
        config = self.require_ready()
        if order["environment"] != config["environment"]:
            raise APIError("Phiên thanh toán thuộc môi trường khác", 409)
        if not config["reconciliation_enabled"]:
            result = self.public_order(order)
            result["message"] += " Đối soát API chưa cấu hình; đang chờ webhook SePay."
            return result
        host = (
            "https://userapi-sandbox.sepay.vn/v2" if config["environment"] == "test" else "https://userapi.sepay.vn/v2"
        )
        try:
            for page in range(1, 21):
                response = requests.get(
                    host + "/transactions",
                    headers={"Authorization": "Bearer " + os.environ["SEPAY_API_TOKEN"].strip()},
                    params={
                        "q": order["transfer_content"],
                        "bank_account_id": os.environ["SEPAY_BANK_ACCOUNT_ID"].strip(),
                        "page": page,
                        "per_page": 100,
                        "transaction_date_sort": "asc",
                    },
                    timeout=(5, 15),
                    allow_redirects=False,
                )
                response.raise_for_status()
                result = response.json()
                if (
                    not isinstance(result, dict)
                    or result.get("status") != "success"
                    or not isinstance(result.get("data"), list)
                ):
                    raise ValueError()
                for item in result["data"]:
                    if (
                        not isinstance(item, dict)
                        or item.get("bank_account_id") != os.environ["SEPAY_BANK_ACCOUNT_ID"].strip()
                    ):
                        raise ValueError()
                    if item.get("transfer_type") not in (None, "in", "out"):
                        raise ValueError()
                    direction = item.get("transfer_type") or (
                        "in" if integer(item.get("amount_in", 0), "amount_in") > 0 else "out"
                    )
                    payload = {
                        "id": item.get("id"),
                        "gateway": item.get("bank_brand_name"),
                        "accountNumber": item.get("account_number"),
                        "transferType": direction,
                        "transferAmount": item.get("amount_in") if direction == "in" else item.get("amount_out"),
                        "referenceCode": item.get("reference_number"),
                        "code": item.get("code"),
                        "content": item.get("transaction_content"),
                        "transactionDate": item.get("transaction_date"),
                    }
                    if self.reference(payload) != order["transfer_content"]:
                        continue
                    self.transaction(payload)
                pagination = result.get("meta", {}).get("pagination", {})
                if not isinstance(pagination, dict):
                    raise ValueError()
                # SePay answers a search with no match with last_page 0: nothing arrived, not a failed check.
                last_page = integer(pagination.get("last_page", page), "last_page", 0)
                if last_page <= page and not pagination.get("has_more", False):
                    break
            else:
                raise ValueError()
        except (requests.RequestException, ValueError, TypeError, AttributeError, APIError):
            with get_db():
                get_db().execute(
                    "UPDATE bank_payment_intents SET last_checked_at=?,last_error=? WHERE order_id=?",
                    (
                        stamp(),
                        "Chưa đối soát hết với SePay; giữ nguyên mọi giao dịch đã xác minh, không chuyển lại.",
                        order["order_id"],
                    ),
                )
            raise APIError("Chưa đối soát đầy đủ với SePay. Không chuyển thêm khi chưa rõ kết quả.", 502)
        with get_db():
            get_db().execute(
                "UPDATE bank_payment_intents SET last_checked_at=?,last_error=NULL WHERE order_id=?",
                (stamp(), order["order_id"]),
            )
        return self.public_order(self.order(order["order_id"]))

    def reconcile_pending(self, limit=3):
        config = self.configuration()
        if not config["reconciliation_enabled"]:
            return 0
        # Open sessions first, so old history cannot starve a resident waiting on a payment.
        rows = (
            get_db()
            .execute(
                "SELECT order_id FROM bank_payment_intents WHERE environment=? "
                "AND (status IN ('pending','awaiting_confirmation') OR updated_at>=?) "
                "ORDER BY status NOT IN ('pending','awaiting_confirmation'),COALESCE(last_checked_at,''),created_at "
                "LIMIT ?",
                (config["environment"], stamp(now() - RECONCILE_CLOSED_FOR), limit),
            )
            .fetchall()
        )
        count = 0
        for row in rows:
            try:
                self.reconcile(self.order(row["order_id"]))
                count += 1
            except APIError:
                continue
        return count
