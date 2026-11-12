CREATE TABLE IF NOT EXISTS bank_payment_intents (
    order_id TEXT PRIMARY KEY,
    invoice_type TEXT NOT NULL CHECK(invoice_type IN ('monthly','semiannual')),
    invoice_id INTEGER NOT NULL,
    payer_user_id INTEGER NOT NULL,
    environment TEXT NOT NULL CHECK(environment IN ('test','live')),
    amount INTEGER NOT NULL CHECK(amount>0),
    transfer_content TEXT NOT NULL UNIQUE,
    bank_code TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    account_number TEXT NOT NULL,
    account_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending','awaiting_confirmation','success','expired','cancelled')),
    payment_id INTEGER,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    last_checked_at TEXT,
    last_error TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_bank_active_invoice
ON bank_payment_intents(environment,invoice_type,invoice_id)
WHERE status IN ('pending','awaiting_confirmation');
CREATE TABLE IF NOT EXISTS bank_transactions (
    transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    environment TEXT NOT NULL CHECK(environment IN ('test','live')),
    provider_id TEXT NOT NULL,
    account_number TEXT NOT NULL,
    bank_name TEXT NOT NULL,
    bank_reference TEXT NOT NULL DEFAULT '',
    reference TEXT NOT NULL DEFAULT '',
    direction TEXT NOT NULL CHECK(direction IN ('in','out')),
    amount INTEGER NOT NULL CHECK(amount>0),
    allocated_amount INTEGER NOT NULL DEFAULT 0 CHECK(allocated_amount>=0 AND allocated_amount<=amount),
    unallocated_amount INTEGER NOT NULL DEFAULT 0 CHECK(unallocated_amount>=0 AND unallocated_amount<=amount),
    status TEXT NOT NULL CHECK(status IN ('matched','partial','overpaid','duplicate','unmatched','ignored')),
    issue TEXT NOT NULL DEFAULT '',
    invoice_type TEXT CHECK(invoice_type IN ('monthly','semiannual')),
    invoice_id INTEGER,
    received_at TEXT NOT NULL,
    resolution TEXT CHECK(resolution IN ('refunded','retained','reviewed')),
    resolution_note TEXT,
    resolved_by_user_id INTEGER,
    resolved_at TEXT,
    UNIQUE(environment,provider_id)
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_bank_reference
ON bank_transactions(environment,bank_name,account_number,bank_reference)
WHERE bank_reference<>'';
CREATE INDEX IF NOT EXISTS ix_bank_invoice ON bank_transactions(environment,invoice_type,invoice_id);
CREATE TABLE IF NOT EXISTS bank_transaction_aliases (
    environment TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    transaction_id INTEGER NOT NULL REFERENCES bank_transactions(transaction_id),
    PRIMARY KEY(environment,provider_id)
);
CREATE TABLE IF NOT EXISTS bank_transaction_resolutions (
    resolution_id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL REFERENCES bank_transactions(transaction_id),
    resolution TEXT NOT NULL,
    note TEXT NOT NULL,
    user_id INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
