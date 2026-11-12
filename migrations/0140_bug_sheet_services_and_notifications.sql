-- Read state for staff accounts. Residents keep theirs in notification_logs.
CREATE TABLE notification_staff_reads (
    notification_id INTEGER NOT NULL REFERENCES notifications(notification_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL,
    read_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (notification_id, user_id)
);

-- Technicians share one inbox: a row here shows the notification to all of them.
CREATE TABLE notification_staff_audience (
    notification_id INTEGER PRIMARY KEY REFERENCES notifications(notification_id) ON DELETE CASCADE
);

-- Service cuts now live on their own screen, so overdue invoices no longer open repair tickets.
-- Tickets already created stay in the repair list untouched.
DROP TRIGGER IF EXISTS trg_auto_ticket_monthly_overdue;
DROP TRIGGER IF EXISTS trg_auto_ticket_semiannual_overdue;
UPDATE billing_outbox SET delivered_at=CURRENT_TIMESTAMP,last_error='retired'
WHERE destination='maintenance' AND delivered_at IS NULL;

-- A free-text place such as the lobby, for requests that are not about one apartment.
ALTER TABLE maintenance_tickets ADD COLUMN location TEXT;

-- The technician list follows account roles; a former technician's tickets keep their name.
ALTER TABLE technicians ADD COLUMN active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0,1));
INSERT INTO technicians(user_id,full_name,specialty)
SELECT u.user_id,COALESCE(NULLIF(TRIM(u.full_name),''),u.username),'general'
FROM users u
WHERE u.role='technician' AND NOT EXISTS (SELECT 1 FROM technicians t WHERE t.user_id=u.user_id);
UPDATE technicians SET active=0
WHERE user_id IS NULL OR user_id NOT IN (SELECT user_id FROM users WHERE role='technician');

-- Tells a vehicle registered after the half-year invoice apart from one already billed on it.
-- Older vehicles stay NULL and count as billed.
ALTER TABLE vehicles ADD COLUMN created_at TEXT;

-- SQLite cannot widen a CHECK, so the table is rebuilt to allow a resident to withdraw a request.
-- Dropping the old table cascades into complaint_outbox, so its rows are set aside and put back.
PRAGMA defer_foreign_keys=ON;
CREATE TEMP TABLE complaint_outbox_kept AS SELECT * FROM complaint_outbox;
CREATE TABLE complaints_with_cancel (
    complaint_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    resident_id      INTEGER NOT NULL,
    type             TEXT NOT NULL CHECK (type IN ('complaint','registration')),
    category         TEXT,
    content          TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','processing','resolved','rejected','cancelled')),
    response         TEXT,
    created_at       TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at      TEXT,
    attachments      TEXT
);
INSERT INTO complaints_with_cancel(complaint_id,resident_id,type,category,content,status,response,created_at,resolved_at,attachments)
SELECT complaint_id,resident_id,type,category,content,status,response,created_at,resolved_at,attachments FROM complaints;
DROP TABLE complaints;
ALTER TABLE complaints_with_cancel RENAME TO complaints;
INSERT INTO complaint_outbox SELECT * FROM complaint_outbox_kept;
DROP TABLE complaint_outbox_kept;
CREATE INDEX IF NOT EXISTS idx_domain_complaints_resident ON complaints(resident_id, created_at);
