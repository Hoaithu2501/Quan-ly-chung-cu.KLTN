-- Existing invoices keep their original fees; unknown usage/rates stay NULL.
ALTER TABLE monthly_invoices ADD COLUMN electricity_usage REAL
    CHECK(electricity_usage IS NULL OR electricity_usage BETWEEN 0 AND 1000000);
ALTER TABLE monthly_invoices ADD COLUMN electricity_unit_price INTEGER
    CHECK(electricity_unit_price IS NULL OR electricity_unit_price BETWEEN 1 AND 1000000000);
ALTER TABLE monthly_invoices ADD COLUMN water_usage REAL
    CHECK(water_usage IS NULL OR water_usage BETWEEN 0 AND 1000000);
ALTER TABLE monthly_invoices ADD COLUMN water_unit_price INTEGER
    CHECK(water_unit_price IS NULL OR water_unit_price BETWEEN 1 AND 1000000000);
