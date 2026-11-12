"""Shared integration harness: eight actual Flask apps on ephemeral HTTP ports."""
import importlib.util
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import jwt
import pytest
import requests
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server


from scripts.ci.prepare_database import prepare
from scripts.init_db import migration_files


ROOT = Path(__file__).resolve().parents[1]
TEST_SECRET ="integration-test-jwt-secret-with-32-characters"
TEST_INTERNAL = "integration-test-service-token-with-32-characters"
TEST_PASSWORD = "TestPassword!2026"
TEST_SEPAY_KEY = "integration-sepay-key-at-least-32-characters"


def configure_sepay(monkeypatch):
    """Only isolated test credentials; no real bank/provider network is needed."""
    settings = {
        "PAYMENT_MODE": "sepay", "SEPAY_ENV": "test", "SEPAY_BANK_CODE": "VCB",
        "SEPAY_BANK_NAME": "Vietcombank", "SEPAY_ACCOUNT_NUMBER": "0123456789",
        "SEPAY_ACCOUNT_NAME": "BQL TEST", "SEPAY_WEBHOOK_API_KEY": TEST_SEPAY_KEY,
        "SEPAY_WEBHOOK_URL": "https://example.test/api/billing/sepay/webhook",
        "SEPAY_API_TOKEN": "", "SEPAY_BANK_ACCOUNT_ID": "",
        "SEPAY_PAYMENT_PREFIX": "QLCC", "SEPAY_PAYMENT_WINDOW_MINUTES": "15",
    }
    for name, value in settings.items():
        monkeypatch.setenv(name, value)


@pytest.fixture(autouse=True)
def test_payment_environment(monkeypatch):
    """A developer's .env may say SEPAY_ENV=live; tests must never inherit that."""
    monkeypatch.setenv("SEPAY_ENV", "test")


def bank_webhook(order, *, transaction_id=100001, amount=None, **changes):
    payload = {
        "id": transaction_id, "gateway": "Vietcombank", "transactionDate": "2026-11-06 12:00:00",
        "accountNumber": "0123456789", "code": order["transfer_content"],
        "content": "Transfer " + order["transfer_content"], "transferType": "in",
        "transferAmount": order["amount"] if amount is None else amount,
        "referenceCode": "BANKREF" + str(transaction_id), "subAccount": None,
    }
    return {**payload, **changes}


@pytest.fixture
def service_cluster(tmp_path, monkeypatch):
    """Each test receives isolated data and real inter-service HTTP transport."""
    database = tmp_path / "integration.db"
    prepare(database)
    with sqlite3.connect(database) as destination:
        if "area" not in {row[1] for row in destination.execute("PRAGMA table_info(apartments)")}:
            destination.execute("ALTER TABLE apartments ADD COLUMN area REAL")
        destination.execute("UPDATE apartments SET area=70 WHERE area IS NULL")
        for migration in migration_files():
            destination.executescript(migration.read_text(encoding="utf-8"))
        destination.execute("UPDATE users SET password_hash=?", (generate_password_hash(TEST_PASSWORD),))
    monkeypatch.setenv("JWT_SECRET", TEST_SECRET)
    monkeypatch.setenv("SERVICE_TOKEN", TEST_INTERNAL)
    configure_sepay(monkeypatch)
    monkeypatch.setenv("SCHEDULER_ENABLED", "false")
    # Integration and browser tests use local FAQ answers, never a real provider.
    monkeypatch.setenv("LLM_API_KEY", "")
    monkeypatch.delenv("GOOGLE_APPLICATION_CREDENTIALS", raising=False)
    urls, modules, apps, servers = {}, {}, {}, []

    for name in ("auth", "resident", "billing", "parking", "maintenance", "notification", "complaint", "chatbot"):
        spec = importlib.util.spec_from_file_location("integration_" + name, ROOT / f"{name}-service/app.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        app = module.create_app()
        app.config.update(TESTING=True, DATABASE_PATH=str(database))
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True)
        thread.start()
        servers.append((server, thread))
        urls[name] = f"http://127.0.0.1:{server.server_port}"
        modules[name], apps[name] = module, app
        monkeypatch.setenv(name.upper() + "_SERVICE_URL", urls[name])

    def headers(role="admin", user_id=None, internal=False, **extra):
        if internal:
            return {"X-Service-Token": TEST_INTERNAL, **extra}
        identifier = user_id if user_id is not None else {"admin": 1, "resident": 3, "technician": 11}[role]
        now = datetime.now(timezone.utc)
        token = jwt.encode({"sub": str(identifier), "role": role, "username": role + str(identifier), "iss": "qlcc-auth", "iat": now, "exp": now + timedelta(hours=1)}, TEST_SECRET, algorithm="HS256")
        return {"Authorization": "Bearer " + token, **extra}

    def call(service, path, method="GET", role="admin", user_id=None, json=None, internal=False, headers=None, **kwargs):
        request_headers = cluster.headers(role, user_id, internal, **(headers or {}))
        return requests.request(method, urls[service] + path, headers=request_headers, json=json, timeout=15, **kwargs)

    def release_apartments(user_id):
        """Sample accounts already hold an apartment; an account may only hold one at a time."""
        with sqlite3.connect(database) as db:
            db.execute("UPDATE apartment_contracts SET status='terminated' WHERE resident_id IN (SELECT resident_id FROM residents WHERE user_id=?)", (user_id,))
            db.execute("DELETE FROM resident_apartment_memberships WHERE resident_id IN (SELECT resident_id FROM residents WHERE user_id=?)", (user_id,))

    cluster = SimpleNamespace(urls=urls, modules=modules, apps=apps, db_path=database, password=TEST_PASSWORD, call=call, headers=headers,
                              release_apartments=release_apartments)
    yield cluster
    for server, thread in reversed(servers):
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
