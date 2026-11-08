-- Each physical FK stays inside the owning service.
CREATE INDEX IF NOT EXISTS idx_residents_user ON residents(user_id);
CREATE INDEX IF NOT EXISTS idx_contracts_resident_status ON apartment_contracts(resident_id,status);
CREATE INDEX IF NOT EXISTS idx_contracts_apartment_dates ON apartment_contracts(apartment_id,start_date,end_date);
CREATE INDEX IF NOT EXISTS idx_monthly_due ON monthly_invoices(status,due_date);
CREATE INDEX IF NOT EXISTS idx_semiannual_due ON semiannual_invoices(status,due_date);
