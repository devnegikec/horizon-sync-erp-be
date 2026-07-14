-- ===========================================
-- Seed Permissions for Four Modules
-- ===========================================
-- Modules: Sales & Orders, Procurement, Inventory, Accounting
--
-- Usage (run in this order to avoid "unsafe use of new value" error):
--
--   # 1. Add enum values first (commits in separate transaction)
--   docker compose exec postgres psql -U horizon_user -d identity_db -f /app/scripts/seed_permissions_four_modules_enums.sql
--
--   # 2. Insert permissions
--   docker compose exec postgres psql -U horizon_user -d identity_db -f /app/scripts/seed_permissions_four_modules.sql

-- ===========================================
-- Step 2: Insert permissions (skip if code exists)
-- ===========================================

-- ---------- 1. Sales & Orders ----------
INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'customer.read', 'View Customers', 'View customers and contacts', 'customer'::resourcetype, 'read'::actiontype, 'sales', 'Sales & Orders', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'customer.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'customer.create', 'Create Customers', 'Create new customers', 'customer'::resourcetype, 'create'::actiontype, 'sales', 'Sales & Orders', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'customer.create');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'customer.update', 'Edit Customers', 'Edit existing customers', 'customer'::resourcetype, 'update'::actiontype, 'sales', 'Sales & Orders', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'customer.update');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'customer.delete', 'Delete Customers', 'Delete customers', 'customer'::resourcetype, 'delete'::actiontype, 'sales', 'Sales & Orders', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'customer.delete');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'sales_order.read', 'View Sales Orders', 'View sales orders and quotes', 'sales_order'::resourcetype, 'read'::actiontype, 'sales', 'Sales & Orders', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'sales_order.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'sales_order.create', 'Create Sales Orders', 'Create new sales orders', 'sales_order'::resourcetype, 'create'::actiontype, 'sales', 'Sales & Orders', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'sales_order.create');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'sales_order.update', 'Edit Sales Orders', 'Edit sales orders', 'sales_order'::resourcetype, 'update'::actiontype, 'sales', 'Sales & Orders', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'sales_order.update');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'sales_order.delete', 'Delete Sales Orders', 'Delete sales orders', 'sales_order'::resourcetype, 'delete'::actiontype, 'sales', 'Sales & Orders', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'sales_order.delete');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'invoice.read', 'View Invoices', 'View sales invoices', 'invoice'::resourcetype, 'read'::actiontype, 'sales', 'Sales & Orders', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'invoice.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'invoice.create', 'Create Invoices', 'Create sales invoices', 'invoice'::resourcetype, 'create'::actiontype, 'sales', 'Sales & Orders', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'invoice.create');


-- ---------- 2. Procurement ----------
INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'supplier.read', 'View Suppliers', 'View suppliers and vendors', 'supplier'::resourcetype, 'read'::actiontype, 'procurement', 'Procurement', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'supplier.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'supplier.create', 'Create Suppliers', 'Create new suppliers', 'supplier'::resourcetype, 'create'::actiontype, 'procurement', 'Procurement', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'supplier.create');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'supplier.update', 'Edit Suppliers', 'Edit existing suppliers', 'supplier'::resourcetype, 'update'::actiontype, 'procurement', 'Procurement', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'supplier.update');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'supplier.delete', 'Delete Suppliers', 'Delete suppliers', 'supplier'::resourcetype, 'delete'::actiontype, 'procurement', 'Procurement', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'supplier.delete');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'purchase_order.read', 'View Purchase Orders', 'View purchase orders', 'purchase_order'::resourcetype, 'read'::actiontype, 'procurement', 'Procurement', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'purchase_order.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'purchase_order.create', 'Create Purchase Orders', 'Create new purchase orders', 'purchase_order'::resourcetype, 'create'::actiontype, 'procurement', 'Procurement', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'purchase_order.create');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'purchase_order.update', 'Edit Purchase Orders', 'Edit purchase orders', 'purchase_order'::resourcetype, 'update'::actiontype, 'procurement', 'Procurement', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'purchase_order.update');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'purchase_order.delete', 'Delete Purchase Orders', 'Delete purchase orders', 'purchase_order'::resourcetype, 'delete'::actiontype, 'procurement', 'Procurement', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'purchase_order.delete');


-- ---------- 3. Inventory ----------
INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'item.read', 'View Items', 'View items and products', 'item'::resourcetype, 'read'::actiontype, 'inventory', 'Inventory', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'item.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'item.create', 'Create Items', 'Create new items', 'item'::resourcetype, 'create'::actiontype, 'inventory', 'Inventory', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'item.create');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'item.update', 'Edit Items', 'Edit existing items', 'item'::resourcetype, 'update'::actiontype, 'inventory', 'Inventory', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'item.update');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'item.delete', 'Delete Items', 'Delete items', 'item'::resourcetype, 'delete'::actiontype, 'inventory', 'Inventory', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'item.delete');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'warehouse.read', 'View Warehouses', 'View warehouses and locations', 'warehouse'::resourcetype, 'read'::actiontype, 'inventory', 'Inventory', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'warehouse.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'warehouse.create', 'Create Warehouses', 'Create new warehouses', 'warehouse'::resourcetype, 'create'::actiontype, 'inventory', 'Inventory', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'warehouse.create');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'stock_entry.read', 'View Stock Movements', 'View stock entries and movements', 'stock_entry'::resourcetype, 'read'::actiontype, 'inventory', 'Inventory', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'stock_entry.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'stock_entry.create', 'Create Stock Movements', 'Create stock entries', 'stock_entry'::resourcetype, 'create'::actiontype, 'inventory', 'Inventory', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'stock_entry.create');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'batch.read', 'View Batches', 'View batch/lot information', 'batch'::resourcetype, 'read'::actiontype, 'inventory', 'Inventory', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'batch.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'serial.read', 'View Serial Numbers', 'View serial number tracking', 'serial'::resourcetype, 'read'::actiontype, 'inventory', 'Inventory', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'serial.read');


-- ---------- 4. Accounting ----------
INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'chart_of_account.read', 'View Chart of Accounts', 'View chart of accounts', 'chart_of_account'::resourcetype, 'read'::actiontype, 'accounting', 'Accounting', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'chart_of_account.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'chart_of_account.create', 'Create Chart of Accounts', 'Create accounts', 'chart_of_account'::resourcetype, 'create'::actiontype, 'accounting', 'Accounting', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'chart_of_account.create');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'chart_of_account.update', 'Edit Chart of Accounts', 'Edit accounts', 'chart_of_account'::resourcetype, 'update'::actiontype, 'accounting', 'Accounting', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'chart_of_account.update');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'payment.read', 'View Payments', 'View payments and transactions', 'payment'::resourcetype, 'read'::actiontype, 'accounting', 'Accounting', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'payment.read');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'payment.create', 'Process Payments', 'Record and process payments', 'payment'::resourcetype, 'create'::actiontype, 'accounting', 'Accounting', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'payment.create');

INSERT INTO permissions (id, code, name, description, resource, action, module, category, is_active, created_at, updated_at)
SELECT gen_random_uuid(), 'payment.update', 'Edit Payments', 'Edit payment records', 'payment'::resourcetype, 'update'::actiontype, 'accounting', 'Accounting', true, NOW(), NOW()
WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = 'payment.update');


-- ===========================================
-- Step 3: Update Python ResourceType enum (app/models/base.py)
-- ===========================================
-- Add these to ResourceType enum for the app to recognize the new resources:
--   CUSTOMER = "customer"
--   SALES_ORDER = "sales_order"
--   INVOICE = "invoice"
--   SUPPLIER = "supplier"
--   PURCHASE_ORDER = "purchase_order"
--   CHART_OF_ACCOUNT = "chart_of_account"
--   PAYMENT = "payment"

-- ===========================================
-- Step 4: Update permission_service grouping (Python)
-- ===========================================
-- Add these mappings to get_permissions_grouped_by_category() in permission_service.py
-- if you want icons for the new categories:
--
--   "sales": "Sales & Orders",
--   "procurement": "Procurement",
--   "inventory": "Inventory",
--   "accounting": "Accounting",
--
--   "Sales & Orders": "shopping-cart",
--   "Procurement": "truck",
--   "Inventory": "box",
--   "Accounting": "calculator",

-- ===========================================
-- Verify
-- ===========================================
SELECT category, COUNT(*) as permission_count
FROM permissions
WHERE category IN ('Sales & Orders', 'Procurement', 'Inventory', 'Accounting')
GROUP BY category
ORDER BY category;

SELECT 'Seed completed. Permissions created for 4 modules.' AS status;
