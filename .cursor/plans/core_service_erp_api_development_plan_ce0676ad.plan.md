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
- ✅ **Phase 3 - Stock Management APIs**: Complete
- Batches API
- Serial Numbers API (serial_nos + serial_no_history)
- Stock Entries API (stock_entries + stock_entry_items)
- Stock Levels API
- Stock Movements API
- Stock Reconciliations API (header + items)
- Stock Settings API (one per org)
- Put Away Rules API
- ✅ **Phase 2 - Item-Related APIs**: Complete
- Item Prices API (item_prices)
- Item Suppliers API (item_suppliers)
- ✅ **Phase 4 - Quality Management APIs**: Complete (quality_inspection_templates, quality_inspections)
- ✅ **Phase 5 - Order Processing APIs**: Complete (pick_lists, delivery_notes, purchase_receipts)
- ✅ **Phase 6 - Landed Cost APIs**: Complete (landed_cost_vouchers)
- ✅ **Phase 7 - Billing APIs**: Complete (invoices, payments, journal_entries)
- ✅ **RBAC**: Core-service APIs respect role-based access from identity-service (permissions in /me, require_permission enforced)

## API Development Order

The APIs should be built in the following order to respect dependencies:

### Phase 1: Master Data APIs (Foundation)

1. **Warehouses API** (`warehouses_extended`)

- Independent, no dependencies
- Required by: items, stock entries, delivery notes, purchase receipts

1. **Item Groups API** (`item_groups`)

- Independent (self-referencing for hierarchy)
- Required by: items

1. **Customers API** (`customers`)

- Independent
- Required by: delivery notes, invoices, payments

1. **Suppliers API** (`suppliers`)

- Independent
- Required by: purchase receipts, invoices, payments, item_suppliers

1. **Chart of Accounts API** (`chart_of_accounts`)

- Independent (self-referencing for hierarchy)
- Required by: journal entries, warehouses (stock_account_id)

### Phase 2: Item-Related APIs

1. **Item Prices API** (`item_prices`)

- Depends on: items
- Price list management for items

1. **Item Suppliers API** (`item_suppliers`)

- Depends on: items, suppliers
- Supplier relationships for items

### Phase 3: Stock Management APIs

1. **Batches API** (`batches`)

- Depends on: items
- Batch tracking for items

1. **Serial Numbers API** (`serial_nos`, `serial_no_history`)

- Depends on: items, warehouses_extended
- Serial number tracking

1. **Stock Entries API** (`stock_entries`, `stock_entry_items`)

- Depends on: items, warehouses_extended
- Stock movement management

1. **Stock Levels API** (`stock_levels`)

- Depends on: items (via products), warehouses
- Current stock tracking

1. **Stock Movements API** (`stock_movements`)

- Depends on: items (via products), warehouses
- Stock movement audit trail

1. **Stock Reconciliations API** (`stock_reconciliations`, `stock_reconciliation_items`)

- Depends on: items, warehouses_extended
- Stock reconciliation management

1. **Stock Settings API** (`stock_settings`)

- Depends on: warehouses_extended (default_warehouse_id)
- Organization-level stock settings

1. **Put Away Rules API** (`put_away_rules`)

- Depends on: items, item_groups, warehouses_extended
- Automated put-away rules

### Phase 4: Quality Management APIs

1. **Quality Inspection Templates API** (`quality_inspection_templates`, `quality_inspection_parameters`)

- Depends on: items, item_groups
- Template management

1. **Quality Inspections API** (`quality_inspections`, `quality_inspection_readings`)

- Depends on: items, quality_inspection_templates
- Inspection record management

### Phase 5: Order Processing APIs

1. **Pick Lists API** (`pick_lists`, `pick_list_items`)

- Depends on: items, warehouses_extended
- Warehouse picking operations

1. **Delivery Notes API** (`delivery_notes`, `delivery_note_items`)

- Depends on: customers, items, warehouses_extended, pick_lists (optional)
- Sales delivery documentation

1. **Purchase Receipts API** (`purchase_receipts`, `purchase_receipt_items`)

- Depends on: suppliers, items, warehouses_extended
- Purchase receipt documentation

### Phase 6: Landed Cost APIs

1. **Landed Cost Vouchers API** (`landed_cost_vouchers`, `landed_cost_purchase_receipts`, `landed_cost_items`, `landed_cost_taxes_and_charges`)

- Depends on: purchase_receipts, items
- Landed cost allocation

### Phase 7: Billing APIs

1. **Invoices API** (`invoices`, `invoice_items`)

- Depends on: customers, suppliers
- Sales and purchase invoicing

1. **Payments API** (`payments`, `payment_allocations`)

- Depends on: customers, suppliers, invoices
- Payment processing

1. **Journal Entries API** (`journal_entries`, `journal_entry_lines`)

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

1. `items` (already exists)
2. `item_prices`
3. `item_suppliers`

**Group 3: Stock Management Tables**

1. `batches`
2. `serial_nos`
3. `serial_no_history`
4. `stock_entries`
5. `stock_entry_items`
6. `stock_levels`
7. `stock_movements`
8. `stock_reconciliations`
9. `stock_reconciliation_items`
10. `stock_settings`
11. `put_away_rules`

**Group 4: Quality Management Tables**

1. `quality_inspection_templates`
2. `quality_inspection_parameters`
3. `quality_inspections`
4. `quality_inspection_readings`

**Group 5: Order Processing Tables**

1. `pick_lists`
2. `pick_list_items`
3. `delivery_notes`
4. `delivery_note_items`
5. `purchase_receipts`
6. `purchase_receipt_items`

**Group 6: Landed Cost Tables**

1. `landed_cost_vouchers`
2. `landed_cost_purchase_receipts`
3. `landed_cost_items`
4. `landed_cost_taxes_and_charges`

**Group 7: Billing Tables**

1. `invoices`
2. `invoice_items`
3. `payments`
4. `payment_allocations`
5. `journal_entries`
6. `journal_entry_lines`

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

## Schema vs API Coverage (Why Some Tables Have No Standalone API)

`schema.dbml` defines **63 tables**. Core-service ERP exposes **standalone (top-level) APIs** only for **parent/primary entities**. Many tables are either child tables (managed via parent APIs), owned by another service (Identity), or out of scope for the current ERP API set.

### Tables With Standalone APIs (Parent / Primary Entities)

| Table(s)                                                                                                      | API                              | Notes                                                                             |
| ------------------------------------------------------------------------------------------------------------- | -------------------------------- | --------------------------------------------------------------------------------- |
| `warehouses_extended`                                                                                         | Warehouses API                   | Plan uses `warehouses_extended`; schema also has `warehouses` (see Out of scope). |
| `item_groups`                                                                                                 | Item Groups API                  |                                                                                   |
| `items`                                                                                                       | Items API                        |                                                                                   |
| `item_prices`                                                                                                 | Item Prices API                  |                                                                                   |
| `item_suppliers`                                                                                              | Item Suppliers API               |                                                                                   |
| `customers`                                                                                                   | Customers API                    |                                                                                   |
| `suppliers`                                                                                                   | Suppliers API                    |                                                                                   |
| `chart_of_accounts`                                                                                           | Chart of Accounts API            |                                                                                   |
| `batches`                                                                                                     | Batches API                      |                                                                                   |
| `serial_nos`, `serial_no_history`                                                                             | Serial Numbers API               | History is part of serial-number flow.                                            |
| `stock_entries`, `stock_entry_items`                                                                          | Stock Entries API                | Line items are sub-resource of stock entry.                                       |
| `stock_levels`                                                                                                | Stock Levels API                 | Implementation may use item/product mapping.                                      |
| `stock_movements`                                                                                             | Stock Movements API              | Implementation may use item/product mapping.                                      |
| `stock_reconciliations`, `stock_reconciliation_items`                                                         | Stock Reconciliations API        | Items are sub-resource of reconciliation.                                         |
| `stock_settings`                                                                                              | Stock Settings API               |                                                                                   |
| `put_away_rules`                                                                                              | Put Away Rules API               |                                                                                   |
| `quality_inspection_templates`, `quality_inspection_parameters`                                               | Quality Inspection Templates API | Parameters are sub-resource of template.                                          |
| `quality_inspections`, `quality_inspection_readings`                                                          | Quality Inspections API          | Readings are sub-resource of inspection.                                          |
| `pick_lists`, `pick_list_items`                                                                               | Pick Lists API                   | Items are sub-resource of pick list.                                              |
| `delivery_notes`, `delivery_note_items`                                                                       | Delivery Notes API               | Items are sub-resource of delivery note.                                          |
| `purchase_receipts`, `purchase_receipt_items`                                                                 | Purchase Receipts API            | Items are sub-resource of purchase receipt.                                       |
| `landed_cost_vouchers`, `landed_cost_purchase_receipts`, `landed_cost_items`, `landed_cost_taxes_and_charges` | Landed Cost Vouchers API         | All child tables are part of voucher API.                                         |
| `invoices`, `invoice_items`                                                                                   | Invoices API                     | Line items are sub-resource of invoice.                                           |
| `payments`, `payment_allocations`                                                                             | Payments API                     | Allocations are sub-resource of payment.                                          |
| `journal_entries`, `journal_entry_lines`                                                                      | Journal Entries API              | Lines are sub-resource of journal entry.                                          |

### Child / Detail Tables (No Standalone API — Managed via Parent)

These are created, updated, and deleted only through their parent API (e.g. create delivery note with `delivery_note_items` in the same request). They are not missing; they are intentionally not top-level resources.

| Table                                                                                 | Parent entity / API                    |
| ------------------------------------------------------------------------------------- | -------------------------------------- |
| `stock_entry_items`                                                                   | Stock Entries API                      |
| `stock_reconciliation_items`                                                          | Stock Reconciliations API              |
| `serial_no_history`                                                                   | Serial Numbers API (lifecycle/history) |
| `quality_inspection_parameters`                                                       | Quality Inspection Templates API       |
| `quality_inspection_readings`                                                         | Quality Inspections API                |
| `pick_list_items`                                                                     | Pick Lists API                         |
| `delivery_note_items`                                                                 | Delivery Notes API                     |
| `purchase_receipt_items`                                                              | Purchase Receipts API                  |
| `landed_cost_purchase_receipts`, `landed_cost_items`, `landed_cost_taxes_and_charges` | Landed Cost Vouchers API               |
| `invoice_items`                                                                       | Invoices API                           |
| `payment_allocations`                                                                 | Payments API                           |
| `journal_entry_lines`                                                                 | Journal Entries API                    |

### Identity / Other Services (Not Core-Service ERP)

These tables are owned by the Identity service or other subsystems; core-service ERP does not expose APIs for them.

| Table(s)                                                                                                      | Service / purpose                                 |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `users`, `organizations`, `organization_settings`                                                             | Identity                                          |
| `roles`, `permissions`, `role_permissions`                                                                    | Identity (RBAC)                                   |
| `user_organization_roles`, `user_teams`, `teams`, `team_members`                                              | Identity                                          |
| `invitations`, `email_verifications`, `password_resets`, `refresh_tokens`                                     | Identity (auth)                                   |
| `activity_logs`, `audit_logs`                                                                                 | Cross-cutting / audit (may be identity or shared) |
| `subscription_plans`, `subscriptions`, `subscription_invoices`, `subscription_payments`, `subscription_usage` | Billing / subscriptions                           |

### In Schema But Not in Current ERP API Scope

| Table(s)             | Reason                                                                                                                                                                                 |
| -------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `warehouses`         | Plan and APIs use `warehouses_extended`; schema references `warehouses` for `stock_levels` and `stock_movements`. Implementation may use only `warehouses_extended` and map as needed. |
| `products`           | Schema uses `products` for `stock_levels` and `stock_movements`; ERP APIs use **items** as the primary entity. Products may be legacy or a separate catalog; not in current API scope. |
| `product_categories` | Tied to `products`; same as above.                                                                                                                                                     |

### Summary

- **Standalone APIs:** All primary ERP entities listed in Phases 1–7 have APIs; child tables are covered as sub-resources of those APIs.
- **“Missing” APIs:** There are no standalone APIs for (1) child/detail tables by design, (2) Identity/auth tables (different service), (3) `warehouses` / `products` / `product_categories` (out of current scope or alternate model). No core ERP **parent** table from the plan is missing an API.

## Next Steps

1. Review and confirm this plan
2. Create SQL scripts for table creation
3. Create seed data scripts
4. Implement APIs in the specified order
5. Add tests for each API
6. Update API documentation
