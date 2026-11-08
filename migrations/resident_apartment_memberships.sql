-- BQL confirms co-residents without creating or changing legal contracts.
CREATE TABLE IF NOT EXISTS resident_apartment_memberships (
    resident_id INTEGER NOT NULL REFERENCES residents(resident_id) ON DELETE CASCADE,
    apartment_id INTEGER NOT NULL REFERENCES apartments(apartment_id) ON DELETE CASCADE,
    confirmed_by_user_id INTEGER NOT NULL,
    confirmed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (resident_id, apartment_id)
);

CREATE INDEX IF NOT EXISTS idx_resident_memberships_apartment
    ON resident_apartment_memberships(apartment_id);
