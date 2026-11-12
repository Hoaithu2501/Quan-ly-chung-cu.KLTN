-- SePay is the only payment provider. These tables belonged to the retired test
-- providers and nothing reads them; settled payments live in *_payments and are untouched.
DROP TABLE IF EXISTS payment_order_provider_state;
DROP TABLE IF EXISTS payment_orders;
