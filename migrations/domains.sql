CREATE TABLE IF NOT EXISTS maintenance_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    apartment_id INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS cut_service_resolutions (
    ticket_id INTEGER PRIMARY KEY REFERENCES maintenance_tickets(ticket_id),
    event_id TEXT NOT NULL,
    outcome TEXT NOT NULL CHECK (outcome IN ('cancelled', 'restore_requested')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS notification_events (
    event_id TEXT PRIMARY KEY,
    notification_id INTEGER NOT NULL REFERENCES notifications(notification_id),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS notification_push_tokens (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    resident_id INTEGER,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS notification_audience (
    notification_id INTEGER PRIMARY KEY REFERENCES notifications(notification_id),
    target_role TEXT NOT NULL CHECK (target_role IN ('admin'))
);
CREATE TABLE IF NOT EXISTS notification_push_roles (
    user_id INTEGER PRIMARY KEY,
    role TEXT NOT NULL CHECK (role IN ('admin','resident','technician'))
);
CREATE INDEX IF NOT EXISTS idx_domain_tickets_assignment ON maintenance_tickets(technician_id, status);
CREATE INDEX IF NOT EXISTS idx_domain_notices_apartment ON notifications(target_apartment_id, created_at);
CREATE INDEX IF NOT EXISTS idx_domain_notice_reads ON notification_logs(notification_id, resident_id);
CREATE INDEX IF NOT EXISTS idx_domain_complaints_resident ON complaints(resident_id, created_at);
CREATE INDEX IF NOT EXISTS idx_domain_vehicle_apartment ON vehicles(apartment_id, status);
