-- A new migration is needed for databases that already applied billing.sql.
-- Keep provider state separate so existing orders and invoices remain intact.
CREATE TABLE IF NOT EXISTS payment_order_provider_state (
    order_id TEXT PRIMARY KEY REFERENCES payment_orders(order_id),
    provider_result_code INTEGER,
    provider_message TEXT,
    last_checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
