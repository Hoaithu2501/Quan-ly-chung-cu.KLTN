"""Check Firebase configuration without sending any push notification."""

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from shared.firebase_push import push_settings, access_credentials


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-auth", action="store_true", help="Verify the service account with Google OAuth")
    args = parser.parse_args()
    settings = push_settings()
    if not settings["configured"]:
        for error in settings["errors"]:
            print("Firebase:", error)
        return 1
    print("Firebase: cấu hình Web, VAPID và service account cùng project: OK")
    try:
        if args.check_auth:
            access_credentials(settings)
            print("Google OAuth: OK (chưa kiểm tra quyền gửi FCM hoặc việc nhận trên thiết bị).")
        else:
            from google.auth import load_credentials_from_file

            load_credentials_from_file(settings["credential_path"])
            print("Định dạng khóa service account: OK")
    except Exception:
        print(
            "Firebase: không xác thực được service account. Kiểm tra khóa, Internet và giờ hệ thống; không dán private key vào log/chat."
        )
        return 1
    print("Không gửi thông báo, không sửa database. Bước cuối: bật quyền và thử trên trình duyệt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
