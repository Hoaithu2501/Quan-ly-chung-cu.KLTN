"""Create an isolated Compose test environment; never reads or edits .env."""
from pathlib import Path
import secrets


def write_test_env(destination):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    values = {
        "CI_SMOKE_TEST": "true", "INIT_DEMO": "true",
        "JWT_SECRET": secrets.token_urlsafe(48),
        "SERVICE_TOKEN": secrets.token_urlsafe(48),
        "SEPAY_WEBHOOK_API_KEY": secrets.token_urlsafe(48),
        "PAYMENT_MODE": "sepay", "SEPAY_ENV": "test",
        "SEPAY_API_TOKEN": "", "SEPAY_BANK_ACCOUNT_ID": "",
        "SEPAY_BANK_CODE": "VCB", "SEPAY_BANK_NAME": "Vietcombank",
        "SEPAY_ACCOUNT_NUMBER": "0123456789", "SEPAY_ACCOUNT_NAME": "CI TEST",
        "SEPAY_PAYMENT_PREFIX": "TTHD",
        "SEPAY_WEBHOOK_URL": "https://example.invalid/api/billing/sepay/webhook",
        "LLM_API_KEY": "", "GOOGLE_APPLICATION_CREDENTIALS": "",
        "FIREBASE_PROJECT_ID": "", "FIREBASE_WEB_CONFIG": "", "FIREBASE_VAPID_KEY": "",
        "SCHEDULER_ENABLED": "false",
    }
    with destination.open("x", encoding="utf-8", newline="\n") as output:
        output.write("".join(f"{key}={value}\n" for key, value in values.items()))
    return destination


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default=".runtime/ci.env")
    print(f"Isolated test configuration ready: {write_test_env(parser.parse_args().output)}")
