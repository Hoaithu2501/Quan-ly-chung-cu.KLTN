"""Parking policy and its six-month billing contract over real HTTP."""
import sqlite3
from scripts.ci.prepare_database import FIXTURE
from datetime import date
from pathlib import Path


def test_parking_migration_preserves_existing_rows_and_deleted_identifiers():
    root = Path(__file__).resolve().parents[1]
    with sqlite3.connect(":memory:") as db:
        db.executescript(FIXTURE.read_text(encoding="utf-8"))
        highest = db.execute("SELECT COALESCE(MAX(vehicle_id),0)+100 FROM vehicles").fetchone()[0]
        db.execute("INSERT INTO vehicles(vehicle_id,apartment_id,vehicle_type,monthly_fee,registered_date) "
                   "VALUES (?,1,'bicycle',30000,'2026-01-01')", (highest,))
        db.execute("DELETE FROM vehicles WHERE vehicle_id=?", (highest,))
        old_count = db.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0]
        db.executescript((root / "migrations/parking_policy.sql").read_text(encoding="utf-8"))
        assert db.execute("SELECT COUNT(*) FROM vehicles").fetchone()[0] == old_count
        assert db.execute("SELECT COUNT(*) FROM vehicles WHERE card_fee<>0").fetchone()[0] == 0
        assert db.execute("SELECT COUNT(*) FROM vehicles WHERE vehicle_type='bicycle' AND monthly_fee<>50000").fetchone()[0] == 0
        new_vehicle = db.execute("INSERT INTO vehicles(apartment_id,vehicle_type,plate_number,monthly_fee,registered_date) "
                                 "VALUES (1,'electric_bike','MIGRATION-ELECTRIC',100000,'2026-01-01')")
        assert new_vehicle.lastrowid == highest + 1
        assert db.execute("SELECT card_fee FROM vehicles WHERE vehicle_id=?", (new_vehicle.lastrowid,)).fetchone()[0] == 100000


def create_apartment(cluster, code):
    response = cluster.call("resident", "/api/apartments", method="POST", json={
        "code": code, "block": "TEST", "floor": 1, "area": 70})
    assert response.status_code == 201, response.text
    return response.json()["apartment_id"]


def create_vehicle(cluster, apartment_id, **overrides):
    values = {"apartment_id": apartment_id, "vehicle_type": "motorbike",
              "plate_number": "PARKING-TEST", "registered_date": "2026-07-01"}
    values.update(overrides)
    return cluster.call("parking", "/api/parking/vehicles", method="POST", json=values)


def test_vehicle_types_rates_plates_and_room_identifiers(service_cluster):
    cluster = service_cluster
    apartment_id = create_apartment(cluster, "PARK-101")
    motorbike = create_vehicle(cluster, apartment_id)
    assert motorbike.status_code == 201, motorbike.text
    assert motorbike.json()["monthly_fee"] == 100000
    assert motorbike.json()["card_fee"] == 100000
    electric = create_vehicle(cluster, apartment_id, vehicle_type="electric_bike", plate_number="ELECTRIC-101")
    assert electric.status_code == 201, electric.text
    assert electric.json()["monthly_fee"] == 100000
    assert create_vehicle(cluster, apartment_id, vehicle_type="electric_bike", plate_number=None).status_code == 400
    assert create_vehicle(cluster, apartment_id, plate_number=None).status_code == 400
    assert create_vehicle(cluster, apartment_id, vehicle_type="car", plate_number="CAR-101").status_code == 400
    assert create_vehicle(cluster, apartment_id, plate_number="WRONG-FEE", monthly_fee=120000).status_code == 400
    assert create_vehicle(cluster, apartment_id, vehicle_type="bicycle", monthly_fee=30000, plate_number=None).status_code == 400
    bikes = [create_vehicle(cluster, apartment_id, vehicle_type="bicycle", plate_number=None) for _ in range(2)]
    assert all(response.status_code == 201 for response in bikes)
    assert all(response.json()["monthly_fee"] == 50000 for response in bikes)
    identifiers = {response.json()["plate_number"] for response in bikes}
    assert len(identifiers) == 2 and all(value.startswith("PARK-101-XD-") for value in identifiers)
    path = f"/api/parking/vehicles/{bikes[0].json()['vehicle_id']}"
    assert cluster.call("parking", path, method="PATCH", json={"vehicle_type": "motorbike"}).status_code == 400
    new_apartment = create_apartment(cluster, "PARK-102")
    moved = cluster.call("parking", path, method="PATCH", json={"apartment_id": new_apartment})
    assert moved.status_code == 200, moved.text
    assert moved.json()["plate_number"].startswith("PARK-102-XD-")


def test_minimum_registration_term_and_cancellation_cannot_be_bypassed(service_cluster, monkeypatch):
    cluster = service_cluster
    apartment_id = create_apartment(cluster, "PARK-TERM")
    parking = cluster.modules["parking"]
    monkeypatch.setattr(parking, "local_today", lambda: date(2026, 8, 31))
    for invalid in (0, 1, "one", 2.5, True, 9_000_000_000_000):
        assert create_vehicle(cluster, apartment_id, registration_months=invalid).status_code == 400
    vehicle = create_vehicle(cluster, apartment_id)
    assert vehicle.status_code == 201, vehicle.text
    assert vehicle.json()["registration_months"] == 2
    assert vehicle.json()["minimum_end_date"] == "2026-09-01"
    path = f"/api/parking/vehicles/{vehicle.json()['vehicle_id']}"
    assert cluster.call("parking", path, method="PATCH", json={"status": "cancelled"}).status_code == 409
    assert cluster.call("parking", path, method="PATCH", json={"status": "cancelled", "registered_date": "2026-01-01"}).status_code == 400
    monkeypatch.setattr(parking, "local_today", lambda: date(2026, 9, 1))
    cancelled = cluster.call("parking", path, method="PATCH", json={"status": "cancelled", "cancelled_date": "2026-07-01"})
    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["cancelled_date"] == "2026-09-01"
    assert cluster.call("parking", path, method="PATCH", json={"status": "active"}).status_code == 409
    returning = create_vehicle(cluster, apartment_id, registered_date="2026-09-01")
    assert returning.status_code == 201, returning.text
    assert returning.json()["card_fee"] == 0
    end_of_month = create_vehicle(cluster, apartment_id, plate_number="PARK-LEAP", registered_date="2027-12-31")
    assert end_of_month.status_code == 201
    assert end_of_month.json()["minimum_end_date"] == "2028-02-29"


def test_semiannual_billing_counts_registered_months_and_card_only_once(service_cluster, monkeypatch):
    cluster = service_cluster
    apartment_id = create_apartment(cluster, "PARK-BILL")
    monkeypatch.setattr(cluster.modules["parking"], "local_today", lambda: date(2026, 9, 1))
    electric = create_vehicle(cluster, apartment_id, vehicle_type="electric_bike")
    assert electric.status_code == 201, electric.text
    bicycle = create_vehicle(cluster, apartment_id, vehicle_type="bicycle", plate_number=None, registered_date="2026-08-01")
    assert bicycle.status_code == 201, bicycle.text
    cancelled = cluster.call("parking", f"/api/parking/vehicles/{electric.json()['vehicle_id']}", method="PATCH", json={"status": "cancelled"})
    assert cancelled.status_code == 200, cancelled.text

    def quote(period):
        response = cluster.call("parking", "/api/parking/summary", internal=True,
                                params={"apartment_id": apartment_id, "period": period})
        assert response.status_code == 200, response.text
        return response.json()["items"]

    assert quote("2026-H1") == []
    first = quote("2026-H2")[0]
    assert first["vehicle_months"] == 7  # Electric July-August, bicycle August-December.
    assert first["recurring_fee"] == 450000
    assert first["card_fee"] == 200000
    assert first["parking_fee"] == 650000
    assert quote("2026-H2")[0] == first
    next_period = quote("2027-H1")[0]
    assert next_period["parking_fee"] == 300000
    assert next_period["card_fee"] == 0

    for period, parking_fee in (("2026-H2", 650000), ("2027-H1", 300000)):
        response = cluster.call("billing", "/api/billing/invoices/semiannual", method="POST", json={
            "apartment_id": apartment_id, "period": period, "due_date": "2027-07-01", "service_fee": 1000000})
        assert response.status_code == 201, response.text
        assert response.json()["parking_fee"] == parking_fee
        assert response.json()["total_amount"] == 1000000 + parking_fee
