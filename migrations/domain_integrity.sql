-- Existing sample plates are unique. Enforce this under concurrent HTTP writes.
CREATE UNIQUE INDEX IF NOT EXISTS uq_active_vehicle_plate
ON vehicles(UPPER(plate_number))
WHERE status='active' AND plate_number IS NOT NULL AND TRIM(plate_number)<>'';
