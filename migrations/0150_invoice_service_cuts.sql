-- Which service a technician cut for an overdue invoice, and whether it came back after payment.
CREATE TABLE invoice_service_cuts (
    cut_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_type TEXT NOT NULL CHECK (invoice_type IN ('monthly','semiannual')),
    invoice_id INTEGER NOT NULL,
    service TEXT NOT NULL CHECK (service IN ('electricity','water','common_service','parking')),
    status TEXT NOT NULL DEFAULT 'cut' CHECK (status IN ('cut','restored')),
    cut_by_user_id INTEGER NOT NULL,
    cut_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    restored_by_user_id INTEGER,
    restored_at TEXT,
    UNIQUE (invoice_type, invoice_id, service)
);
