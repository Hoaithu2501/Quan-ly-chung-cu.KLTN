-- Invoice context is descriptive; it never grants access to a notification.
CREATE TABLE IF NOT EXISTS notification_billing_context (
    notification_id INTEGER PRIMARY KEY REFERENCES notifications(notification_id) ON DELETE CASCADE,
    apartment_id INTEGER NOT NULL,
    apartment_code TEXT NOT NULL,
    invoice_created_at TEXT,
    paid_at TEXT
);

-- Recover context for already delivered billing events, without changing their
-- audience, content, read receipts or original timestamps (or sending again).
INSERT OR IGNORE INTO notification_billing_context
    (notification_id, apartment_id, apartment_code, invoice_created_at, paid_at)
SELECT e.notification_id, i.apartment_id, a.code, i.created_at,
       CASE WHEN e.event_id = 'billing:created:' || i.kind || ':' || i.invoice_id
            THEN NULL ELSE (
                SELECT p.paid_at FROM vw_billing_all_payments p
                WHERE p.invoice_type=i.kind AND p.invoice_id=i.invoice_id AND p.status='success'
                ORDER BY p.payment_id LIMIT 1
            ) END
FROM notification_events e
JOIN (
    SELECT 'monthly' AS kind, invoice_id, apartment_id, created_at FROM monthly_invoices
    UNION ALL
    SELECT 'semiannual', invoice_id, apartment_id, created_at FROM semiannual_invoices
) i ON e.event_id IN ('billing:created:' || i.kind || ':' || i.invoice_id,
                      'billing:paid:' || i.kind || ':' || i.invoice_id,
                      'billing:paid-admin:' || i.kind || ':' || i.invoice_id)
JOIN apartments a ON a.apartment_id=i.apartment_id;
