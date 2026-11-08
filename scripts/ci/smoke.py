"""Run inside the disposable gateway container, against the built images."""
import os
import sqlite3

import requests


def main():
    if os.getenv("CI_SMOKE_TEST") != "true" or os.getenv("SEPAY_ENV") != "test":
        raise RuntimeError("This smoke test is only for the isolated CI stack")
    base = "http://127.0.0.1:5000"
    response = requests.get(base + "/api-status", timeout=25)
    response.raise_for_status()
    services = response.json()["services"]
    assert len(services) == 8 and set(services.values()) == {"ok"}, services
    for asset in ("/", "/app.js", "/styles.css", "/firebase-messaging-sw.js"):
        response = requests.get(base + asset, timeout=10)
        assert response.status_code == 200 and response.content, asset
    accounts = (
        ("admin", "Admin@12345", "/api/apartments"),
        ("resident", "Resident@12345", "/api/billing/invoices/monthly"),
        ("technician", "Tech@12345", "/api/maintenance/tickets"),
    )
    for username, password, path in accounts:
        response = requests.post(base + "/api/auth/login", json={"username": username, "password": password}, timeout=15)
        assert response.status_code == 200, (username, response.status_code)
        headers = {"Authorization": "Bearer " + response.json()["token"]}
        response = requests.get(base + path, headers=headers, timeout=15)
        assert response.status_code == 200 and "items" in response.json(), (username, path)
    assert requests.get(base + "/api/billing/invoices/monthly", timeout=10).status_code == 401
    assert requests.post(base + "/api/billing/sepay/webhook", json={}, timeout=10).status_code == 401
    with sqlite3.connect("file:/app/data/QLCC.db?mode=ro", uri=True) as db:
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []
    print("Smoke OK: 8 services, frontend, 3 roles, protected routes, SQLite integrity/FKs.")


if __name__ == "__main__":
    main()
