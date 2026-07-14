-- Seed script for comprehensive default accounts and chart of accounts
-- For the expanded default account types in SystemConfiguration.tsx

-- Organization and user IDs (from existing seed patterns)
-- Organization: bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150 (Default Organization)
-- User: 8d509f22-5fe5-4765-9496-3a236cae2af1 (dnegi@gmail.com)

BEGIN;

-- First, create chart of accounts entries for the new default account types
-- Only create if they don't already exist

INSERT INTO accounts (id, organization_id, account_code, account_name, account_type, parent_account_id, currency, status, is_posting_account, description, created_by, updated_by, created_at, updated_at)
VALUES
  -- Revenue Accounts
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '4000', 'Sales Revenue', 'revenue', null, 'USD', 'ACTIVE', true, 'Primary sales revenue account', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '4010', 'Payment Discount Received', 'revenue', null, 'USD', 'ACTIVE', true, 'Early payment discounts from suppliers', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '4020', 'Foreign Exchange Gain', 'revenue', null, 'USD', 'ACTIVE', true, 'Gains from currency exchange differences', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  -- Expense Accounts
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '5000', 'Cost of Goods Sold', 'expense', null, 'USD', 'ACTIVE', true, 'Cost of inventory when sold', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '5010', 'Purchase Price Variance', 'expense', null, 'USD', 'ACTIVE', true, 'Variance between expected and actual purchase costs', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '5020', 'Payment Discount Given', 'expense', null, 'USD', 'ACTIVE', true, 'Early payment discounts given to customers', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '5030', 'Rounding Adjustment', 'expense', null, 'USD', 'ACTIVE', true, 'Small rounding differences in calculations', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '5040', 'Foreign Exchange Loss', 'expense', null, 'USD', 'ACTIVE', true, 'Losses from currency exchange differences', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '5050', 'Bad Debt Expense', 'expense', null, 'USD', 'ACTIVE', true, 'Write-offs of uncollectible receivables', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  -- Asset Accounts
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '1110', 'Cash', 'asset', null, 'USD', 'ACTIVE', true, 'Main cash account', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '1120', 'Bank Account', 'asset', null, 'USD', 'ACTIVE', true, 'Main bank account for transfers', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '1130', 'Checks Received', 'asset', null, 'USD', 'ACTIVE', true, 'Undeposited check payments', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '1200', 'Accounts Receivable', 'asset', null, 'USD', 'ACTIVE', true, 'Customer receivables', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '1300', 'Inventory', 'asset', null, 'USD', 'ACTIVE', true, 'Inventory and stock valuation', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '1400', 'Prepaid Expenses', 'asset', null, 'USD', 'ACTIVE', true, 'Advance payments for future expenses', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '1500', 'Input Tax Receivable', 'asset', null, 'USD', 'ACTIVE', true, 'VAT/tax paid on purchases, recoverable', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  -- Liability Accounts
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '2100', 'Accounts Payable', 'liability', null, 'USD', 'ACTIVE', true, 'Supplier payables', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '2200', 'Accrued Expenses', 'liability', null, 'USD', 'ACTIVE', true, 'Expenses incurred but not yet paid', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '2300', 'Sales Tax Payable', 'liability', null, 'USD', 'ACTIVE', true, 'Sales tax/VAT collected, payable to authorities', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now()),
  -- Equity Account
  (gen_random_uuid(), 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150', '3000', 'Retained Earnings', 'equity', null, 'USD', 'ACTIVE', true, 'Accumulated profits and retained earnings', '8d509f22-5fe5-4765-9496-3a236cae2af1', '8d509f22-5fe5-4765-9496-3a236cae2af1', now(), now())
ON CONFLICT (organization_id, account_code) DO NOTHING;

-- Now create default account mappings using the created accounts
-- We'll use the account_codes to reference the accounts (assuming they exist)

INSERT INTO default_accounts (id, organization_id, transaction_type, account_id, scenario, created_at, updated_at)
SELECT 
  gen_random_uuid(),
  'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150',
  default_mappings.transaction_type,
  accounts.id,
  default_mappings.scenario,
  now(),
  now()
FROM (
  VALUES
    -- Payment & Receivable Accounts
    ('accounts_receivable', '1200', null),
    ('accounts_payable', '2100', null),
    -- Cash & Bank Accounts
    ('cash', '1110', null),
    ('bank', '1120', null),
    ('checks_received', '1130', null),
    -- Revenue & Sales Accounts
    ('sales_revenue', '4000', null),
    ('cost_of_goods_sold', '5000', null),
    -- Inventory & Stock Accounts
    ('inventory', '1300', null),
    ('purchase_variance', '5010', null),
    -- Discount & Adjustment Accounts
    ('payment_discount_received', '4010', null),
    ('payment_discount_given', '5020', null),
    ('rounding_adjustment', '5030', null),
    -- Foreign Exchange Accounts
    ('exchange_rate_gain', '4020', null),
    ('exchange_rate_loss', '5040', null),
    -- Bad Debt & Write-offs
    ('bad_debt', '5050', null),
    -- Prepayments & Accruals
    ('prepaid_expenses', '1400', null),
    ('accrued_expenses', '2200', null),
    -- Tax Accounts
    ('tax_payable', '2300', null),
    ('tax_receivable', '1500', null),
    -- Equity Account
    ('retained_earnings', '3000', null)
) AS default_mappings(transaction_type, account_code, scenario)
JOIN accounts ON accounts.account_code = default_mappings.account_code 
  AND accounts.organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150'
ON CONFLICT (organization_id, transaction_type, scenario) DO UPDATE SET
  account_id = EXCLUDED.account_id,
  updated_at = EXCLUDED.updated_at;

COMMIT;

-- Verification queries (uncomment to run)
-- SELECT COUNT(*) as new_accounts FROM accounts WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150';
-- SELECT COUNT(*) as default_mappings FROM default_accounts WHERE organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150';
-- SELECT da.transaction_type, a.account_code, a.account_name, a.account_type 
-- FROM default_accounts da 
-- JOIN accounts a ON da.account_id = a.id 
-- WHERE da.organization_id = 'bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150' 
-- ORDER BY da.transaction_type;