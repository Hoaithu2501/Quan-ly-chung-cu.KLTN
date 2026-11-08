-- A bank transfer is journaled in bank_transactions; invoice payment is the
-- one final settlement, not each incoming transfer or webhook delivery.
CREATE UNIQUE INDEX IF NOT EXISTS uq_monthly_successful_payment
ON monthly_payments(invoice_id) WHERE status='success';
CREATE UNIQUE INDEX IF NOT EXISTS uq_semiannual_successful_payment
ON semiannual_payments(invoice_id) WHERE status='success';

-- Keep the original AFTER triggers that derive total_amount from the two fees.
-- NULL usage/rates identify legacy fee-only invoices. Metered invoices require
-- all four inputs and exact half-up rounding using integer thousandths.
CREATE TRIGGER validate_monthly_calculation_insert
BEFORE INSERT ON monthly_invoices
WHEN typeof(NEW.electricity_fee)<>'integer' OR typeof(NEW.water_fee)<>'integer'
  OR NEW.electricity_fee<0 OR NEW.water_fee<0
  OR NEW.electricity_fee>1000000000 OR NEW.water_fee>1000000000
  OR ((NEW.electricity_usage IS NOT NULL OR NEW.water_usage IS NOT NULL
       OR NEW.electricity_unit_price IS NOT NULL OR NEW.water_unit_price IS NOT NULL) AND (
    NEW.electricity_usage IS NULL OR NEW.water_usage IS NULL
    OR NEW.electricity_unit_price IS NULL OR NEW.water_unit_price IS NULL
    OR typeof(NEW.electricity_unit_price)<>'integer' OR typeof(NEW.water_unit_price)<>'integer'
    OR round(NEW.electricity_usage,3)<>NEW.electricity_usage OR round(NEW.water_usage,3)<>NEW.water_usage
    OR NEW.electricity_fee<>(CAST(round(NEW.electricity_usage*1000) AS INTEGER)*NEW.electricity_unit_price+500)/1000
    OR NEW.water_fee<>(CAST(round(NEW.water_usage*1000) AS INTEGER)*NEW.water_unit_price+500)/1000
  ))
BEGIN
    SELECT RAISE(ABORT, 'Invalid utility usage, unit price or calculated fee');
END;

CREATE TRIGGER validate_monthly_calculation_update
BEFORE UPDATE OF electricity_fee,water_fee,electricity_usage,water_usage,electricity_unit_price,water_unit_price
ON monthly_invoices
WHEN typeof(NEW.electricity_fee)<>'integer' OR typeof(NEW.water_fee)<>'integer'
  OR NEW.electricity_fee<0 OR NEW.water_fee<0
  OR NEW.electricity_fee>1000000000 OR NEW.water_fee>1000000000
  OR ((NEW.electricity_usage IS NOT NULL OR NEW.water_usage IS NOT NULL
       OR NEW.electricity_unit_price IS NOT NULL OR NEW.water_unit_price IS NOT NULL) AND (
    NEW.electricity_usage IS NULL OR NEW.water_usage IS NULL
    OR NEW.electricity_unit_price IS NULL OR NEW.water_unit_price IS NULL
    OR typeof(NEW.electricity_unit_price)<>'integer' OR typeof(NEW.water_unit_price)<>'integer'
    OR round(NEW.electricity_usage,3)<>NEW.electricity_usage OR round(NEW.water_usage,3)<>NEW.water_usage
    OR NEW.electricity_fee<>(CAST(round(NEW.electricity_usage*1000) AS INTEGER)*NEW.electricity_unit_price+500)/1000
    OR NEW.water_fee<>(CAST(round(NEW.water_usage*1000) AS INTEGER)*NEW.water_unit_price+500)/1000
  ))
BEGIN
    SELECT RAISE(ABORT, 'Invalid utility usage, unit price or calculated fee');
END;
