-- Notification owns recipient scope; resident identifiers are resolved over HTTP.
CREATE TABLE IF NOT EXISTS notification_resident_audience (
    notification_id INTEGER PRIMARY KEY REFERENCES notifications(notification_id) ON DELETE CASCADE,
    resident_id INTEGER NOT NULL CHECK (resident_id > 0)
);
CREATE INDEX IF NOT EXISTS ix_notification_resident_audience
    ON notification_resident_audience(resident_id, notification_id);

-- Complaint owns delivery attempts, committed atomically with each new reply.
CREATE TABLE IF NOT EXISTS complaint_outbox (
    event_id TEXT PRIMARY KEY,
    complaint_id INTEGER NOT NULL REFERENCES complaints(complaint_id) ON DELETE CASCADE,
    payload TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    delivered_at TEXT,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT
);
