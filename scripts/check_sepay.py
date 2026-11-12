"""Read-only SePay configuration, gateway and API checks; never creates a payment."""

import argparse
import importlib.util
import os
from pathlib import Path
import sys
from urllib.parse import urlparse
import uuid

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def load_billing():
    spec = importlib.util.spec_from_file_location("sepay_check_billing", ROOT / "billing-service/app.py")
    billing = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(billing)
    return billing


def check_api(config, normalize):
    """Verify only the configured receiver; never print provider bodies or tokens."""
    if not config["reconciliation_enabled"]:
        print("API: cần cả SEPAY_API_TOKEN và SEPAY_BANK_ACCOUNT_ID hợp lệ.")
        return False
    host = "userapi-sandbox.sepay.vn" if config["environment"] == "test" else "userapi.sepay.vn"
    account_id = str(uuid.UUID(os.environ["SEPAY_BANK_ACCOUNT_ID"].strip()))
    try:
        response = requests.get(
            f"https://{host}/v2/bank-accounts/{account_id}",
            headers={"Authorization": "Bearer " + os.environ["SEPAY_API_TOKEN"].strip()},
            timeout=(5, 15),
            allow_redirects=False,
        )
        if response.status_code != 200:
            print(f"API: HTTP {response.status_code}; kiểm tra đúng môi trường, token và UUID tài khoản.")
            return False
        payload = response.json()
        account = payload.get("data") if isinstance(payload, dict) and payload.get("status") == "success" else None
        if not isinstance(account, dict):
            raise ValueError()
        bank_aliases = {normalize(account.get(field, "")) for field in ("bank_code", "bank_short_name", "bank_bin")}
        matched = (
            str(uuid.UUID(str(account.get("id")))) == account_id
            and account.get("account_number") == os.environ["SEPAY_ACCOUNT_NUMBER"].strip()
            and normalize(account.get("account_holder_name", "")) == normalize(os.environ["SEPAY_ACCOUNT_NAME"])
            and normalize(os.environ["SEPAY_BANK_CODE"]) in bank_aliases
            and normalize(os.environ["SEPAY_BANK_NAME"]) in bank_aliases
            # Live responses can encode this flag as "1", unlike the numeric documentation example.
            and account.get("active") in (1, True, "1")
        )
        print(
            "API: "
            + (
                "OK, tài khoản đang hoạt động và khớp cấu hình."
                if matched
                else "Tài khoản không khớp cấu hình hoặc chưa hoạt động; kiểm tra lại thông tin người nhận."
            )
        )
        return matched
    except (requests.RequestException, ValueError, TypeError, AttributeError):
        print("API: không nhận được dữ liệu hợp lệ; không xuất nội dung phản hồi hoặc thông tin bí mật.")
        return False


def main(argv=None):
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--probe", action="store_true", help="Check gateway and webhook rejection without authorization."
    )
    parser.add_argument("--gateway", default="http://localhost:5000")
    parser.add_argument(
        "--check-api", action="store_true", help="Read receiver details with the environment's SePay API v2 token."
    )
    args = parser.parse_args(argv)
    gateway = urlparse(args.gateway)
    if (
        gateway.scheme not in ("http", "https")
        or not gateway.hostname
        or gateway.username
        or gateway.password
        or gateway.query
        or gateway.fragment
        or gateway.path not in ("", "/")
    ):
        parser.error("--gateway phải là origin HTTP(S), không có thông tin đăng nhập hoặc đường dẫn.")
    billing = load_billing()
    config = billing.payment_configuration()
    print("PAYMENT_MODE:", config["mode"])
    print("SEPAY_ENV:", config["environment"])
    print("Cấu hình:", config["message"])
    print("API đối soát:", "Đã cấu hình" if config["reconciliation_enabled"] else "Chưa cấu hình (chỉ nhận webhook)")
    ok = config["ready"]
    if args.probe:
        try:
            response = requests.get(args.gateway.rstrip("/") + "/health", timeout=(3, 5), allow_redirects=False)
            healthy = response.status_code == 200 and response.json().get("service") == "gateway"
            print("Gateway:", "OK" if healthy else "Chưa nhận được health của gateway QLCC.")
            ok = ok and healthy
        except (requests.RequestException, ValueError, AttributeError):
            print("Gateway: chưa truy cập được; khởi chạy dự án trước.")
            ok = False
        if config["ready"]:
            try:
                # Deliberately no Authorization header: cannot settle an invoice.
                response = requests.post(
                    os.environ["SEPAY_WEBHOOK_URL"].strip(), json={}, timeout=(5, 15), allow_redirects=False
                )
                rejected = response.status_code == 403 and isinstance(response.json().get("error"), str)
                print(
                    "Webhook:",
                    "OK, từ chối yêu cầu không có API key."
                    if rejected
                    else f"Cần kiểm tra URL, tunnel hoặc cấu hình container (HTTP {response.status_code}).",
                )
                ok = ok and rejected
            except (requests.RequestException, ValueError, AttributeError):
                print("Webhook: chưa nhận được phản hồi API hợp lệ; kiểm tra tunnel HTTPS.")
                ok = False
        else:
            print("Webhook: chưa kiểm tra vì cấu hình chưa đầy đủ.")
    if args.check_api:
        from sepay_payments import normalized

        api_ok = check_api(config, normalized)
        ok = ok and api_ok
    print("Không tạo giao dịch, không ghi nhận thanh toán và không chuyển tiền.")
    print("Hướng dẫn: docs/TEST_THANH_TOAN_HOA_DON.md")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
