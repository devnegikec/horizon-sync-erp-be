# Core Service - Database Tables Summary

## Overview

Core Service manages **Inventory**, **Lead-to-Order**, and **Billing** modules. This document lists all tables required for the core-service database.

## Total Tables: **39 Tables**

---

## 📦 INVENTORY MANAGEMENT (20 tables)

### Core Inventory

1. **`warehouses_extended`** - Warehouse master with hierarchy, capacity, location
2. **`item_groups`** - Item categorization (hierarchical)
3. **`items`** - Core inventory items with stock settings
4. **`item_prices`** - Item pricing by price list
5. **`item_suppliers`** - Item-supplier relationships

### Stock Management

6. **`batches`** - Batch tracking for items
7. **`serial_nos`** - Serial number tracking
8. **`serial_no_history`** - Serial number transaction history
9. **`stock_entries`** - Stock movement entries (receipt, issue, transfer)
10. **`stock_entry_items`** - Stock entry line items
11. **`stock_levels`** - Current stock levels per warehouse
12. **`stock_movements`** - Stock movement audit trail
13. **`stock_reconciliations`** - Stock reconciliation documents
14. **`stock_reconciliation_items`** - Reconciliation line items
15. **`stock_settings`** - Stock management settings per organization

### Warehouse Operations

16. **`put_away_rules`** - Automated put-away rules

### Quality Management

17. **`quality_inspection_templates`** - Quality inspection templates
18. **`quality_inspection_parameters`** - Template parameters
19. **`quality_inspections`** - Quality inspection records
20. **`quality_inspection_readings`** - Inspection parameter readings

---

## 🛒 LEAD TO ORDER (12 tables)

### Master Data

21. **`customers`** - Customer master data
22. **`suppliers`** - Supplier master data

### Order Processing

23. **`pick_lists`** - Warehouse pick lists
24. **`pick_list_items`** - Pick list line items
25. **`delivery_notes`** - Sales delivery documentation
26. **`delivery_note_items`** - Delivery note line items
27. **`purchase_receipts`** - Purchase receipt documentation
28. **`purchase_receipt_items`** - Purchase receipt line items

### Landed Cost

29. **`landed_cost_vouchers`** - Landed cost allocation vouchers
30. **`landed_cost_purchase_receipts`** - Purchase receipts in voucher
31. **`landed_cost_items`** - Items with allocated costs
32. **`landed_cost_taxes_and_charges`** - Additional charges

---

## 💰 BILLING (7 tables)

### Accounting

33. **`chart_of_accounts`** - Chart of accounts (hierarchical)
34. **`journal_entries`** - Journal entry headers
35. **`journal_entry_lines`** - Journal entry line items

### Invoicing & Payments

36. **`invoices`** - Sales and purchase invoices
37. **`invoice_items`** - Invoice line items
38. **`payments`** - Payment transactions
39. **`payment_allocations`** - Payment to invoice allocations

---

## Table Dependencies

```
warehouses_extended (standalone)
    └── item_groups (standalone)
        └── items
            ├── item_prices
            ├── item_suppliers
            ├── batches
            ├── serial_nos
            ├── stock_entries
            │   └── stock_entry_items
            ├── stock_levels
            ├── stock_movements
            ├── stock_reconciliation_items
            └── quality_inspections
                └── quality_inspection_readings

customers ──┐
            ├── delivery_notes
            │   └── delivery_note_items
            ├── invoices
            │   └── invoice_items
            └── payments
                └── payment_allocations

suppliers ──┐
            ├── purchase_receipts
            │   └── purchase_receipt_items
            ├── invoices
            └── payments

pick_lists
    └── pick_list_items

landed_cost_vouchers
    ├── landed_cost_purchase_receipts
    ├── landed_cost_items
    └── landed_cost_taxes_and_charges

chart_of_accounts
    └── journal_entry_lines
        └── journal_entries
```

---

## How to Use

### Option 1: Create All Tables (Recommended)

```bash
# Connect to core_db
docker compose exec postgres psql -U horizon_user -d core_db

# Run the script
\i /path/to/core-service/scripts/create_tables.sql
```

### Option 2: Create Only Warehouses Table

```bash
docker compose exec postgres psql -U horizon_user -d core_db

# Run warehouses script
\i /path/to/core-service/scripts/create_warehouses_table.sql
```

### Option 3: Use Alembic Migrations (Recommended for Production)

```bash
# Migrations are automatically created and run via Alembic
# The create_tables.sql is for reference or manual setup
```

---

## Notes

- All tables include `organization_id` for multi-tenancy
- All tables include audit fields (`created_by`, `updated_by`, `created_at`, `updated_at`)
- Soft deletes are supported via `deleted_at` where applicable
- Foreign keys ensure referential integrity
- Indexes are created on frequently queried columns
