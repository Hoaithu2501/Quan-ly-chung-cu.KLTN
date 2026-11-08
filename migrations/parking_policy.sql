-- Keep legacy registrations and already-issued invoices. Existing cards are
-- considered issued; only newly registered vehicles incur the card fee.
DROP VIEW IF EXISTS vw_vehicle_summary_by_apartment;
CREATE TABLE vehicles_policy (
    vehicle_id INTEGER PRIMARY KEY AUTOINCREMENT,
    apartment_id INTEGER NOT NULL,
    plate_number TEXT,
    vehicle_type TEXT NOT NULL CHECK(vehicle_type IN ('bicycle','motorbike','electric_bike')),
    monthly_fee INTEGER NOT NULL CHECK(monthly_fee IN (50000,100000)),
    registered_date TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active','cancelled')),
    registration_months INTEGER NOT NULL DEFAULT 2 CHECK(registration_months >= 2),
    cancelled_date TEXT,
    card_fee INTEGER NOT NULL DEFAULT 100000 CHECK(card_fee IN (0,100000))
);
INSERT INTO vehicles_policy(vehicle_id,apartment_id,plate_number,vehicle_type,monthly_fee,
                            registered_date,status,registration_months,cancelled_date,card_fee)
SELECT vehicle_id,apartment_id,
       CASE WHEN plate_number IS NULL OR TRIM(plate_number)='' THEN
           COALESCE((SELECT code FROM apartments WHERE apartments.apartment_id=vehicles.apartment_id),
                    CAST(apartment_id AS TEXT)) || '-XD-' || vehicle_id
           ELSE plate_number END,
       vehicle_type,CASE WHEN vehicle_type='bicycle' THEN 50000 ELSE 100000 END,
       registered_date,status,2,CASE WHEN status='cancelled' THEN registered_date END,0
FROM vehicles;
-- Preserve AUTOINCREMENT history even when the previous highest ID was deleted.
UPDATE sqlite_sequence SET seq=MAX(seq,COALESCE((SELECT seq FROM sqlite_sequence WHERE name='vehicles'),0))
WHERE name='vehicles_policy';
DROP TABLE vehicles;
ALTER TABLE vehicles_policy RENAME TO vehicles;
CREATE INDEX idx_domain_vehicle_apartment ON vehicles(apartment_id,status);
CREATE UNIQUE INDEX uq_active_vehicle_plate ON vehicles(UPPER(plate_number))
WHERE status='active' AND plate_number IS NOT NULL AND TRIM(plate_number)<>'';
CREATE VIEW vw_vehicle_summary_by_apartment AS
SELECT apartment_id,
       SUM(CASE WHEN vehicle_type IN ('motorbike','electric_bike') THEN 1 ELSE 0 END) AS so_xe_may,
       SUM(CASE WHEN vehicle_type='bicycle' THEN 1 ELSE 0 END) AS so_xe_dap,
       SUM(monthly_fee) AS tong_phi_thang
FROM vehicles WHERE status='active' GROUP BY apartment_id;
