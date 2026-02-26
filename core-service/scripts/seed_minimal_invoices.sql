-- Seed script for 5 customer and 5 supplier invoices with realistic data
-- Organization and user IDs (replace with your actual UUIDs if needed)


-- All values are now hardcoded for compatibility with psql -f and input redirection
-- Organization and user IDs
-- Customer: Acme Corporation
-- Supplier: Steel India Ltd

BEGIN;

-- 5 Customer Invoices
INSERT INTO invoices (id, organization_id, invoice_no, invoice_type, party_id, party_type, posting_date, due_date, status, grand_total, outstanding_amount, currency, remarks, created_by, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'CUST-INV-001', 'sales', '60b23cd6-744b-495f-98e7-4730a6c1c1f9', 'CUSTOMER', '2026-02-01', '2026-03-01', 'paid', 1200.00, 1200.00, 'USD', 'Laptop sale', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'CUST-INV-002', 'sales', '60b23cd6-744b-495f-98e7-4730a6c1c1f9', 'CUSTOMER', '2026-02-02', '2026-03-02', 'paid', 850.00, 850.00, 'USD', 'Monitor sale', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'CUST-INV-003', 'sales', '60b23cd6-744b-495f-98e7-4730a6c1c1f9', 'CUSTOMER', '2026-02-03', '2026-03-03', 'paid', 450.00, 450.00, 'USD', 'Keyboard sale', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'CUST-INV-004', 'sales', '60b23cd6-744b-495f-98e7-4730a6c1c1f9', 'CUSTOMER', '2026-02-04', '2026-03-04', 'paid', 199.00, 199.00, 'USD', 'Mouse sale', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'CUST-INV-005', 'sales', '60b23cd6-744b-495f-98e7-4730a6c1c1f9', 'CUSTOMER', '2026-02-05', '2026-03-05', 'paid', 999.00, 999.00, 'USD', 'Headphone sale', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now());

-- 5 Supplier Invoices
INSERT INTO invoices (id, organization_id, invoice_no, invoice_type, party_id, party_type, posting_date, due_date, status, grand_total, outstanding_amount, currency, remarks, created_by, created_at, updated_at)
VALUES
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'SUPP-INV-001', 'purchase', 'f68137ef-49df-4ea5-8a57-fe22a0f446d2', 'SUPPLIER', '2026-02-01', '2026-03-01', 'paid', 1100.00, 1100.00, 'USD', 'Laptop purchase', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'SUPP-INV-002', 'purchase', 'f68137ef-49df-4ea5-8a57-fe22a0f446d2', 'SUPPLIER', '2026-02-02', '2026-03-02', 'paid', 800.00, 800.00, 'USD', 'Monitor purchase', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'SUPP-INV-003', 'purchase', 'f68137ef-49df-4ea5-8a57-fe22a0f446d2', 'SUPPLIER', '2026-02-03', '2026-03-03', 'paid', 400.00, 400.00, 'USD', 'Keyboard purchase', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'SUPP-INV-004', 'purchase', 'f68137ef-49df-4ea5-8a57-fe22a0f446d2', 'SUPPLIER', '2026-02-04', '2026-03-04', 'paid', 150.00, 150.00, 'USD', 'Mouse purchase', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', 'SUPP-INV-005', 'purchase', 'f68137ef-49df-4ea5-8a57-fe22a0f446d2', 'SUPPLIER', '2026-02-05', '2026-03-05', 'paid', 950.00, 950.00, 'USD', 'Headphone purchase', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now());

COMMIT;