---
name: Core Service ERP API Development Plan
overview: Create a comprehensive plan for building the core-service ERP APIs with step-by-step table creation SQL scripts and seed data. The plan includes API development order based on dependencies, complete table creation scripts with all enum types, and seed data scripts.
todos: []
isProject: false
---

# Core Service ERP API Development Plan

## Overview

This plan outlines the complete development strategy for the core-service ERP system, including API creation order, database table setup, and seed data. The system is organized into three main modules: **Inventory Management**, **Lead-to-Order**, and **Billing**.

## Current Status

- ✅ **Identity Service**: Complete (users, organizations, roles, permissions)
- ✅ **Items API**: Complete (CRUD operations for items)
- ✅ **Phase 1 - Master Data APIs**: Complete
- ✅ Warehouses API (tested)
- ✅ Item Groups API (tested)
- ✅ Customers API
- ✅ Suppliers API
- ✅ Chart of Accounts API
- ⏳ **Phase 2+**: To be built following this plan

## API Development Order

The APIs should be built in the following order to respect dependencies:

### Phase 1: Master Data APIs (Foundation)

1. **Warehouses API** (`warehouses_extended`)

- Independent, no dependencies
- Required by: items, stock entries, delivery notes, purchase receipts

2. **Item Groups API** (`item_groups`)

- Independent (self-referencing for hierarchy)
- Required by: items

3. **Customers API** (`customers`)

- Independent
- Required by: delivery notes, invoices, payments

4. **Suppliers API** (`suppliers`)

- Independent
- Required by: purchase receipts, invoices, payments, item_suppliers

5. **Chart of Accounts API** (`chart_of_accounts`)

- Independent (self-referencing for hierarchy)
- Required by: journal entries, warehouses (stock_account_id)

### Phase 2: Item-Related APIs

6. **Item Prices API** (`item_prices`)

- Depends on: items
- Price list management for items

7. **Item Suppliers API** (`item_suppliers`)

- Depends on: items, suppliers
- Supplier relationships for items

### Phase 3: Stock Management APIs

8. **Batches API** (`batches`)

- Depends on: items
- Batch tracking for items

9. **Serial Numbers API** (`serial_nos`, `serial_no_history`)

- Depends on: items, warehouses_extended
- Serial number tracking

10. **Stock Entries API** (`stock_entries`, `stock_entry_items`)

- Depends on: items, warehouses_extended
- Stock movement management

11. **Stock Levels API** (`stock_levels`)

- Depends on: items (via products), warehouses
- Current stock tracking

12. **Stock Movements API** (`stock_movements`)

- Depends on: items (via products), warehouses
- Stock movement audit trail

13. **Stock Reconciliations API** (`stock_reconciliations`, `stock_reconciliation_items`)

- Depends on: items, warehouses_extended
- Stock reconciliation management

14. **Stock Settings API** (`stock_settings`)

- Depends on: warehouses_extended (default_warehouse_id)
- Organization-level stock settings

15. **Put Away Rules API** (`put_away_rules`)

- Depends on: items, item_groups, warehouses_extended
- Automated put-away rules

### Phase 4: Quality Management APIs

16. **Quality Inspection Templates API** (`quality_inspection_templates`, `quality_inspection_parameters`)

- Depends on: items, item_groups
- Template management

17. **Quality Inspections API** (`quality_inspections`, `quality_inspection_readings`)

- Depends on: items, quality_inspection_templates
- Inspection record management

### Phase 5: Order Processing APIs

18. **Pick Lists API** (`pick_lists`, `pick_list_items`)

- Depends on: items, warehouses_extended
- Warehouse picking operations

19. **Delivery Notes API** (`delivery_notes`, `delivery_note_items`)

- Depends on: customers, items, warehouses_extended, pick_lists (optional)
- Sales delivery documentation

20. **Purchase Receipts API** (`purchase_receipts`, `purchase_receipt_items`)

- Depends on: suppliers, items, warehouses_extended
- Purchase receipt documentation

### Phase 6: Landed Cost APIs

21. **Landed Cost Vouchers API** (`landed_cost_vouchers`, `landed_cost_purchase_receipts`, `landed_cost_items`, `landed_cost_taxes_and_charges`)

- Depends on: purchase_receipts, items
- Landed cost allocation

### Phase 7: Billing APIs

22. **Invoices API** (`invoices`, `invoice_items`)

- Depends on: customers, suppliers
- Sales and purchase invoicing

23. **Payments API** (`payments`, `payment_allocations`)

- Depends on: customers, suppliers, invoices
- Payment processing

24. **Journal Entries API** (`journal_entries`, `journal_entry_lines`)

- Depends on: chart_of_accounts
- Accounting journal entries

## Database Setup

### Step 1: Create Enum Types

All enum types must be created first before any tables. The enum types are defined in `core-service/scripts/fix_enums.sql`:

- `itemtype`: stock, non_stock, service, fixed_asset
- `itemstatus`: active, inactive, discontinued
- `valuationmethod`: fifo, lifo, moving_average, standard
- `documentstatus`: draft, submitted, cancelled
- `warehousetype`: warehouse, store, virtual, transit
- `stockentrytype`: material_receipt, material_issue, material_transfer, manufacture, repack, send_to_subcontractor
- `stockentrystatus`: draft, submitted, cancelled
- `movementtype`: in, out, transfer, adjustment
- `batchstatus`: active, expired, consumed
- `inspectiontype`: incoming, outgoing, in_process
- `inspectionstatus`: pending, accepted, rejected
- `readingtype`: numeric, text, pass_fail

### Step 2: Create Tables in Dependency Order

Tables must be created in the following order:

**Group 1: Independent Master Tables**

1. `warehouses_extended`
2. `item_groups`
3. `customers`
4. `suppliers`
5. `chart_of_accounts`

**Group 2: Item-Related Tables**

6. `items` (already exists)
7. `item_prices`
8. `item_suppliers`

**Group 3: Stock Management Tables**

9. `batches`
10. `serial_nos`
11. `serial_no_history`
12. `stock_entries`
13. `stock_entry_items`
14. `stock_levels`
15. `stock_movements`
16. `stock_reconciliations`
17. `stock_reconciliation_items`
18. `stock_settings`
19. `put_away_rules`

**Group 4: Quality Management Tables**

20. `quality_inspection_templates`
21. `quality_inspection_parameters`
22. `quality_inspections`
23. `quality_inspection_readings`

**Group 5: Order Processing Tables**

24. `pick_lists`
25. `pick_list_items`
26. `delivery_notes`
27. `delivery_note_items`
28. `purchase_receipts`
29. `purchase_receipt_items`

**Group 6: Landed Cost Tables**

30. `landed_cost_vouchers`
31. `landed_cost_purchase_receipts`
32. `landed_cost_items`
33. `landed_cost_taxes_and_charges`

**Group 7: Billing Tables**

34. `invoices`
35. `invoice_items`
36. `payments`
37. `payment_allocations`
38. `journal_entries`
39. `journal_entry_lines`

### Step 3: Create Indexes

Indexes should be created after tables for:

- `organization_id` (all tables)
- Foreign key columns
- Frequently queried columns (codes, names, dates)
- Search columns (item_code, item_name, barcode)

### Step 4: Seed Data

Seed data should be created in the following order:

1. Organizations (from identity-service)
2. Warehouses
3. Item Groups
4. Customers
5. Suppliers
6. Chart of Accounts
7. Items (sample data)
8. Item Prices
9. Item Suppliers
10. Stock Settings

## File Structure

The following files will be created:

### SQL Scripts

- `core-service/scripts/01_create_enums.sql` - All enum type definitions
- `core-service/scripts/02_create_tables.sql` - All table creation scripts in dependency order
- `core-service/scripts/03_create_indexes.sql` - All index creation scripts
- `core-service/scripts/04_seed_data.sql` - Seed data for development/testing

### API Implementation Files (per API)

For each API, create:

- `app/models/{entity}.py` - SQLAlchemy model
- `app/schemas/{entity}.py` - Pydantic schemas (create, update, response, list)
- `app/repositories/{entity}_repository.py` - Data access layer
- `app/services/{entity}_service.py` - Business logic
- `app/api/v1/endpoints/{entity}.py` - API endpoints
- Update `app/api/v1/router.py` - Register routes

## Key Implementation Details

### Multi-Tenancy

- All tables include `organization_id` for data isolation
- All queries must filter by `organization_id`
- Use `current_user.organization_id` from dependencies

### Audit Fields

- All tables include: `created_by`, `updated_by`, `created_at`, `updated_at`
- Soft deletes use `deleted_at` where applicable

### Enum Handling

- Enums are stored in PostgreSQL as custom types
- Python enums in `app/models/base.py` must match database enum values
- Use lowercase enum values in database (as per `fix_enums.sql`)

### Foreign Key Relationships

- Use `ON DELETE CASCADE` for child records that should be deleted with parent
- Use `ON DELETE SET NULL` for optional relationships
- Use `ON DELETE RESTRICT` for critical relationships

### JSONB Fields

- `extra_data`, `tags`, `custom_fields`, `images` use JSONB for flexibility
- Validate JSONB structure in service layer

## Testing Strategy

For each API:

1. Unit tests for service layer
2. Integration tests for repository layer
3. API endpoint tests (using FastAPI TestClient)
4. Test CRUD operations
5. Test filtering, pagination, sorting
6. Test multi-tenancy isolation
7. Test enum validation
8. Test foreign key constraints

## Next Steps

1. Review and confirm this plan
2. Create SQL scripts for table creation
3. Create seed data scripts
4. Implement APIs in the specified order
5. Add tests for each API
6. Update API documentation