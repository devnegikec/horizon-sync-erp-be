psql -U <your_db_user> -d <your_db_name> -f core-service/scripts/seed_minimal_invoices.sql
-- Seed script for 5 customer and 5 supplier invoices with realistic data
-- Organization and user IDs (replace with your actual UUIDs if needed)

-- Use actual IDs from seed_full_flow.sql
\set org_id   'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
\set user_id  '8d509f22-5fe5-4765-9496-3a236cae2af1'

-- Customers (using Acme Corporation for all 5 for demo, update as needed)
\set cust1 '60b23cd6-744b-495f-98e7-4730a6c1c1f9'
\set cust2 '60b23cd6-744b-495f-98e7-4730a6c1c1f9'
\set cust3 '60b23cd6-744b-495f-98e7-4730a6c1c1f9'
\set cust4 '60b23cd6-744b-495f-98e7-4730a6c1c1f9'
\set cust5 '60b23cd6-744b-495f-98e7-4730a6c1c1f9'

-- Suppliers (using Steel India Ltd for all 5 for demo, update as needed)
\set supp1 'f68137ef-49df-4ea5-8a57-fe22a0f446d2'
\set supp2 'f68137ef-49df-4ea5-8a57-fe22a0f446d2'
\set supp3 'f68137ef-49df-4ea5-8a57-fe22a0f446d2'
\set supp4 'f68137ef-49df-4ea5-8a57-fe22a0f446d2'
\set supp5 'f68137ef-49df-4ea5-8a57-fe22a0f446d2'

-- 5 Customer Invoices
INSERT INTO invoices (id, organization_id, invoice_no, invoice_type, party_id, party_type, posting_date, due_date, status, grand_total, outstanding_amount, currency, remarks, created_by, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, 'CUST-INV-001', 'sales', :cust1, 'CUSTOMER', '2026-02-01', '2026-03-01', 'unpaid', 1200.00, 1200.00, 'USD', 'Laptop sale', :user_id, now(), now()),
  (gen_random_uuid(), :org_id, 'CUST-INV-002', 'sales', :cust2, 'CUSTOMER', '2026-02-02', '2026-03-02', 'unpaid', 850.00, 850.00, 'USD', 'Monitor sale', :user_id, now(), now()),
  (gen_random_uuid(), :org_id, 'CUST-INV-003', 'sales', :cust3, 'CUSTOMER', '2026-02-03', '2026-03-03', 'unpaid', 450.00, 450.00, 'USD', 'Keyboard sale', :user_id, now(), now()),
  (gen_random_uuid(), :org_id, 'CUST-INV-004', 'sales', :cust4, 'CUSTOMER', '2026-02-04', '2026-03-04', 'unpaid', 199.00, 199.00, 'USD', 'Mouse sale', :user_id, now(), now()),
  (gen_random_uuid(), :org_id, 'CUST-INV-005', 'sales', :cust5, 'CUSTOMER', '2026-02-05', '2026-03-05', 'unpaid', 999.00, 999.00, 'USD', 'Headphone sale', :user_id, now(), now());

-- 5 Supplier Invoices
INSERT INTO invoices (id, organization_id, invoice_no, invoice_type, party_id, party_type, posting_date, due_date, status, grand_total, outstanding_amount, currency, remarks, created_by, created_at, updated_at)
VALUES
  (gen_random_uuid(), :org_id, 'SUPP-INV-001', 'purchase', :supp1, 'SUPPLIER', '2026-02-01', '2026-03-01', 'unpaid', 1100.00, 1100.00, 'USD', 'Laptop purchase', :user_id, now(), now()),
  (gen_random_uuid(), :org_id, 'SUPP-INV-002', 'purchase', :supp2, 'SUPPLIER', '2026-02-02', '2026-03-02', 'unpaid', 800.00, 800.00, 'USD', 'Monitor purchase', :user_id, now(), now()),
  (gen_random_uuid(), :org_id, 'SUPP-INV-003', 'purchase', :supp3, 'SUPPLIER', '2026-02-03', '2026-03-03', 'unpaid', 400.00, 400.00, 'USD', 'Keyboard purchase', :user_id, now(), now()),
  (gen_random_uuid(), :org_id, 'SUPP-INV-004', 'purchase', :supp4, 'SUPPLIER', '2026-02-04', '2026-03-04', 'unpaid', 150.00, 150.00, 'USD', 'Mouse purchase', :user_id, now(), now()),
  (gen_random_uuid(), :org_id, 'SUPP-INV-005', 'purchase', :supp5, 'SUPPLIER', '2026-02-05', '2026-03-05', 'unpaid', 950.00, 950.00, 'USD', 'Headphone purchase', :user_id, now(), now());
