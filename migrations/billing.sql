-- Billing owns these records; identifiers of other services are logical references.
CREATE TABLE IF NOT EXISTS billing_payment_keys (
    request_key TEXT PRIMARY KEY,
    invoice_type TEXT NOT NULL,
    invoice_id INTEGER NOT NULL,
    payment_id INTEGER NOT NULL,
    payment_method TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS billing_outbox (
    event_id TEXT PRIMARY KEY,
    destination TEXT NOT NULL,
    path TEXT NOT NULL,
    payload TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    delivered_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_billing_outbox_pending ON billing_outbox(delivered_at, created_at);
CREATE VIEW IF NOT EXISTS vw_billing_all_invoices AS
SELECT 'monthly' AS invoice_type, invoice_id, apartment_id, period,
       period AS report_period, total_amount, due_date, status
FROM monthly_invoices
UNION ALL
SELECT 'semiannual', invoice_id, apartment_id, period,
       substr(period,1,4) || CASE substr(period,6,2) WHEN 'H1' THEN '-01' ELSE '-07' END,
       total_amount, due_date, status
FROM semiannual_invoices;
CREATE VIEW IF NOT EXISTS vw_billing_all_payments AS
SELECT 'monthly' AS invoice_type, p.payment_id, p.invoice_id, i.apartment_id,
       i.period, p.amount, p.payment_method, p.transaction_code, p.paid_at, p.status
FROM monthly_payments p JOIN monthly_invoices i ON i.invoice_id=p.invoice_id
UNION ALL
SELECT 'semiannual', p.payment_id, p.invoice_id, i.apartment_id,
       i.period, p.amount, p.payment_method, p.transaction_code, p.paid_at, p.status
FROM semiannual_payments p JOIN semiannual_invoices i ON i.invoice_id=p.invoice_id;
