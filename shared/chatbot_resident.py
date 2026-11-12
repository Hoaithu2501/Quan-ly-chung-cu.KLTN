"""Opt-in invoice lookup with the current resident's JWT; never sent to an LLM."""

import os
import re

from shared.chatbot_retrieval import normalize
from shared.http import call_service
from shared.web import APIError


def personal_invoice_question(question):
    value = " " + normalize(question) + " "
    billing = any(term in value for term in ("hoa don", "thanh toan", "con no", "no phi", "han dong tien"))
    own = any(
        term in value
        for term in (
            "cua toi",
            "cua minh",
            "cua em",
            "cua anh",
            "cua chi",
            "toi con no",
            "minh con no",
            "toi da thanh toan",
            "toi da dong",
            "toi phai tra bao nhieu",
            "minh phai tra bao nhieu",
        )
    )
    return billing and own


def _reply(answer, verified=False):
    return {"answer": answer, "verified": verified}


def resident_reply(question, user):
    if not personal_invoice_question(question):
        return None
    if user["role"] != "resident":
        return _reply(
            "Bạn vào Hóa đơn & thanh toán để xem các hóa đơn mình được phép xem. Nếu muốn hỏi hóa đơn của chính mình trong trò chuyện, bạn cần đăng nhập bằng tài khoản cư dân."
        )
    if os.getenv("CHATBOT_RESIDENT_CONTEXT_ENABLED", "false").lower() not in ("true", "1", "yes"):
        return _reply(
            "Bạn vào Hóa đơn & thanh toán để xem số tiền cần trả, hạn thanh toán và hóa đơn đã trả hay chưa. Hiện mình chưa thể xem hóa đơn của bạn ngay trong trò chuyện."
        )
    try:
        invoices = []
        for kind in ("monthly", "semiannual"):
            # No internal credentials or user-supplied apartment filter. Billing owns scope.
            result = call_service("billing", "/api/billing/invoices/" + kind)
            rows = result["items"]
            if not isinstance(rows, list):
                raise ValueError("Invalid invoice list")
            for row in rows:
                if (
                    not isinstance(row, dict)
                    or type(row.get("total_amount")) is not int
                    or row["total_amount"] < 0
                    or type(row.get("invoice_id")) is not int
                    or row.get("status") not in ("unpaid", "overdue", "paid")
                    or not re.fullmatch(r"\d{4}-(?:\d{2}|H[12])", str(row.get("period", "")))
                    or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(row.get("due_date", "")))
                ):
                    raise ValueError("Invalid invoice")
                invoices.append(
                    {key: row[key] for key in ("invoice_id", "period", "due_date", "total_amount", "status")}
                )
    except APIError as exc:
        if exc.status in (401, 403):
            raise
        return _reply(
            "Mình chưa xem được hóa đơn của bạn lúc này nên chưa thể xác nhận số tiền hoặc việc đã thanh toán. Bạn mở Hóa đơn & thanh toán để kiểm tra lại nhé."
        )
    except (ValueError, KeyError, TypeError):
        return _reply(
            "Thông tin hóa đơn hiện chưa đủ để mình trả lời chính xác. Bạn mở Hóa đơn & thanh toán để kiểm tra, hoặc nhờ Ban quản lý hỗ trợ."
        )
    if not invoices:
        return _reply(
            "Mình chưa tìm thấy hóa đơn nào cho tài khoản của bạn. Bạn vào Hồ sơ cá nhân kiểm tra tài khoản đã được gắn đúng căn hộ chưa nhé.",
            True,
        )
    query = normalize(question)
    history = any(term in query for term in ("da thanh toan", "lich su", "da tra", "da dong"))
    selected = [row for row in invoices if (row["status"] == "paid") == history]
    selected.sort(key=lambda row: row["due_date"], reverse=history)
    if not selected:
        return _reply(
            "Mình chưa tìm thấy hóa đơn nào được xác nhận đã thanh toán cho tài khoản của bạn."
            if history
            else "Hiện không có hóa đơn nào cần thanh toán trong danh sách hóa đơn của bạn.",
            True,
        )
    title = "đã thanh toán" if history else "chưa thanh toán"
    lines = [f"Bạn có {len(selected)} hóa đơn {title}."]
    for row in selected[:5]:
        amount = f"{row['total_amount']:,}".replace(",", ".")
        lines.append(
            f"• Kỳ {row['period']}: {amount} đồng; hạn {row['due_date']}"
            + ("; quá hạn." if row["status"] == "overdue" else ".")
        )
    lines.append("Xem đầy đủ tại Hóa đơn & thanh toán" + (" → Lịch sử thanh toán." if history else "."))
    return _reply("\n".join(lines), True)
