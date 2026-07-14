# Stock Management Seed Data

This document describes the seed data created for Stock Management features including Stock Levels, Stock Movements, Stock Entries, and Stock Reconciliations.

## Overview

The `seed_stock_data.py` script creates realistic stock management data that demonstrates the complete lifecycle of inventory management in an ERP system.

## Prerequisites

Before running this script, ensure:

1. **Identity Service is seeded**: The script requires organization and user data from identity-service
2. **Core Service basic data is seeded**: Run `seed_data.py` first to create items and warehouses
3. **Database is accessible**: Both identity_db and core_db must be running

## Running the Script

```bash
# From the core-service directory
cd core-service

# Run the stock seed script
python scripts/seed_stock_data.py

# Or from the scripts directory
cd scripts
python seed_stock_data.py
```

## Data Created

### 1. Stock Entries (4 entries)

Stock entries represent physical movements of inventory with proper documentation.

#### STE-2024-001: Material Receipt (Raw Materials)

- **Type**: Material Receipt
- **Warehouse**: Main Warehouse
- **Date**: 30 days ago
- **Items**:
  - Steel Sheet (RM-STEEL-001): 500 Kg @ ₹75/Kg = ₹37,500
  - ABS Plastic (RM-PLAST-001): 125 Kg @ ₹100/Kg = ₹12,500
- **Total Value**: ₹50,000
- **Status**: Submitted

#### STE-2024-002: Material Receipt (Finished Goods)

- **Type**: Material Receipt
- **Warehouse**: Main Warehouse
- **Date**: 28 days ago
- **Items**:
  - Widget Pro (FG-WIDGET-001): 100 Nos @ ₹350/Nos = ₹35,000
  - Gadget Max (FG-GADGET-001): 50 Nos @ ₹750/Nos = ₹37,500
  - Packaging Box (CON-PACK-001): 1000 Nos @ ₹18/Nos = ₹18,000
- **Total Value**: ₹90,500
- **Status**: Submitted

#### STE-2024-003: Material Transfer

- **Type**: Material Transfer
- **From**: Main Warehouse
- **To**: Retail Store
- **Date**: 25 days ago
- **Items**:
  - Widget Pro: 30 Nos @ ₹350/Nos = ₹10,500
  - Gadget Max: 20 Nos @ ₹750/Nos = ₹15,000
- **Total Value**: ₹25,500
- **Status**: Submitted

#### STE-2024-004: Material Issue (Sales)

- **Type**: Material Issue
- **From**: Retail Store
- **Date**: 20 days ago
- **Items**:
  - Widget Pro: 10 Nos @ ₹350/Nos = ₹3,500
  - Gadget Max: 5 Nos @ ₹750/Nos = ₹3,750
- **Total Value**: ₹7,250
- **Status**: Submitted

### 2. Stock Movements (11 movements)

Stock movements provide an audit trail of all inventory changes.

| #   | Product       | Warehouse | Type | Qty  | Cost | Reference    | Date        |
| --- | ------------- | --------- | ---- | ---- | ---- | ------------ | ----------- |
| 1   | Steel Sheet   | Main      | IN   | 500  | ₹75  | STE-2024-001 | 30 days ago |
| 2   | ABS Plastic   | Main      | IN   | 125  | ₹100 | STE-2024-001 | 30 days ago |
| 3   | Widget Pro    | Main      | IN   | 100  | ₹350 | STE-2024-002 | 28 days ago |
| 4   | Gadget Max    | Main      | IN   | 50   | ₹750 | STE-2024-002 | 28 days ago |
| 5   | Packaging Box | Main      | IN   | 1000 | ₹18  | STE-2024-002 | 28 days ago |
| 6   | Widget Pro    | Main      | OUT  | 30   | ₹350 | STE-2024-003 | 25 days ago |
| 7   | Widget Pro    | Store     | IN   | 30   | ₹350 | STE-2024-003 | 25 days ago |
| 8   | Gadget Max    | Main      | OUT  | 20   | ₹750 | STE-2024-003 | 25 days ago |
| 9   | Gadget Max    | Store     | IN   | 20   | ₹750 | STE-2024-003 | 25 days ago |
| 10  | Widget Pro    | Store     | OUT  | 10   | ₹350 | STE-2024-004 | 20 days ago |
| 11  | Gadget Max    | Store     | OUT  | 5    | ₹750 | STE-2024-004 | 20 days ago |

### 3. Stock Levels (7 levels)

Current inventory levels across warehouses.

#### Main Warehouse

| Product       | Code          | On Hand  | Reserved | Available |
| ------------- | ------------- | -------- | -------- | --------- |
| Steel Sheet   | RM-STEEL-001  | 500 Kg   | 50 Kg    | 450 Kg    |
| ABS Plastic   | RM-PLAST-001  | 125 Kg   | 25 Kg    | 100 Kg    |
| Widget Pro    | FG-WIDGET-001 | 70 Nos   | 10 Nos   | 60 Nos    |
| Gadget Max    | FG-GADGET-001 | 30 Nos   | 5 Nos    | 25 Nos    |
| Packaging Box | CON-PACK-001  | 1000 Nos | 100 Nos  | 900 Nos   |

#### Retail Store

| Product    | Code          | On Hand | Reserved | Available |
| ---------- | ------------- | ------- | -------- | --------- |
| Widget Pro | FG-WIDGET-001 | 20 Nos  | 0 Nos    | 20 Nos    |
| Gadget Max | FG-GADGET-001 | 15 Nos  | 0 Nos    | 15 Nos    |

### 4. Stock Reconciliations (2 reconciliations)

Physical count adjustments and corrections.

#### RECON-2024-001: Monthly Physical Count

- **Purpose**: Physical Stock Count - Monthly
- **Date**: 15 days ago
- **Status**: Submitted
- **Items**:
  1. Widget Pro (Main Warehouse)
     - Current: 70 Nos
     - Counted: 68 Nos
     - Difference: -2 Nos (shortage)
  2. Packaging Box (Main Warehouse)
     - Current: 1000 Nos
     - Counted: 995 Nos
     - Difference: -5 Nos (damaged)
  3. Gadget Max (Retail Store)
     - Current: 15 Nos
     - Counted: 16 Nos
     - Difference: +1 Nos (found extra)

#### RECON-2024-002: Damage Write-off

- **Purpose**: Damage Write-off
- **Date**: 10 days ago
- **Status**: Submitted
- **Items**:
  1. Steel Sheet (Main Warehouse)
     - Current: 500 Kg
     - Adjusted: 495 Kg
     - Difference: -5 Kg (rust damage)

## Data Relationships

```
Organization (from identity_db)
    ↓
Warehouses (from seed_data.py)
    ↓
Items (from seed_data.py)
    ↓
Stock Entries → Stock Entry Items
    ↓
Stock Movements (audit trail)
    ↓
Stock Levels (current inventory)
    ↓
Stock Reconciliations → Reconciliation Items
```

## Use Cases Demonstrated

### 1. **Receiving Inventory**

- Stock Entry Type: Material Receipt
- Creates: Stock Entry + Stock Movements (IN)
- Updates: Stock Levels

### 2. **Transferring Between Warehouses**

- Stock Entry Type: Material Transfer
- Creates: Stock Entry + Stock Movements (OUT from source, IN to target)
- Updates: Stock Levels in both warehouses

### 3. **Issuing/Selling Inventory**

- Stock Entry Type: Material Issue
- Creates: Stock Entry + Stock Movements (OUT)
- Updates: Stock Levels

### 4. **Physical Count Adjustments**

- Stock Reconciliation
- Creates: Reconciliation + Reconciliation Items
- Updates: Stock Levels (when posted)

### 5. **Damage/Loss Write-offs**

- Stock Reconciliation (Damage purpose)
- Creates: Reconciliation + Reconciliation Items
- Updates: Stock Levels (when posted)

## Testing Scenarios

### Scenario 1: Check Stock Levels

```bash
# Query stock levels for a specific item
SELECT * FROM stock_levels
WHERE product_id = (SELECT id FROM items WHERE item_code = 'FG-WIDGET-001');
```

### Scenario 2: View Movement History

```bash
# Get all movements for an item
SELECT * FROM stock_movements
WHERE product_id = (SELECT id FROM items WHERE item_code = 'FG-WIDGET-001')
ORDER BY performed_at DESC;
```

### Scenario 3: Check Stock Entry Details

```bash
# Get stock entry with items
SELECT se.*, sei.*
FROM stock_entries se
JOIN stock_entry_items sei ON se.id = sei.stock_entry_id
WHERE se.stock_entry_no = 'STE-2024-001';
```

### Scenario 4: Review Reconciliations

```bash
# Get reconciliation with adjustments
SELECT sr.*, sri.*
FROM stock_reconciliations sr
JOIN stock_reconciliation_items sri ON sr.id = sri.reconciliation_id
WHERE sr.reconciliation_no = 'RECON-2024-001';
```

## API Testing

### Get Stock Levels

```bash
GET /api/v1/stock-levels?warehouse_id={warehouse_id}
GET /api/v1/stock-levels?item_id={item_id}
```

### Get Stock Movements

```bash
GET /api/v1/stock-movements?item_id={item_id}
GET /api/v1/stock-movements?warehouse_id={warehouse_id}
GET /api/v1/stock-movements?movement_type=in
```

### Get Stock Entries

```bash
GET /api/v1/stock-entries
GET /api/v1/stock-entries/{entry_id}
GET /api/v1/stock-entries?stock_entry_type=material_receipt
```

### Get Stock Reconciliations

```bash
GET /api/v1/stock-reconciliations
GET /api/v1/stock-reconciliations/{reconciliation_id}
```

## Data Validation

After running the seed script, verify:

1. **Stock Levels Match Movements**:

   - Widget Pro in Main: 100 (received) - 30 (transferred) = 70 ✓
   - Widget Pro in Store: 30 (received) - 10 (sold) = 20 ✓

2. **Reconciliation Adjustments**:

   - Widget Pro adjusted from 70 to 68 (2 shortage)
   - Packaging adjusted from 1000 to 995 (5 damaged)

3. **Movement Types**:
   - IN movements increase stock
   - OUT movements decrease stock
   - TRANSFER creates both OUT and IN movements

## Troubleshooting

### Error: "No items or warehouses found"

**Solution**: Run `seed_data.py` first to create basic inventory data

### Error: "Default organization not found"

**Solution**: Ensure identity-service is seeded first

### Error: "Stock data already seeded"

**Solution**: The script detects existing data and skips seeding. To re-seed, delete existing stock data first.

## Cleanup

To remove seeded stock data:

```sql
-- Delete in order (respecting foreign keys)
DELETE FROM stock_reconciliation_items WHERE organization_id = '{org_id}';
DELETE FROM stock_reconciliations WHERE organization_id = '{org_id}';
DELETE FROM stock_entry_items WHERE organization_id = '{org_id}';
DELETE FROM stock_entries WHERE organization_id = '{org_id}';
DELETE FROM stock_movements WHERE organization_id = '{org_id}';
DELETE FROM stock_levels WHERE organization_id = '{org_id}';
```

## Next Steps

After seeding stock data, you can:

1. Test stock management APIs
2. Create additional stock entries
3. Perform stock reconciliations
4. Generate stock reports
5. Test inventory valuation
6. Implement stock alerts (reorder levels)

## Notes

- All dates are relative to current date (30 days back to present)
- Serial numbers are included for serialized items
- Batch numbers are included for batched items
- All monetary values are in INR (₹)
- Stock levels include reserved quantities for pending orders
- Reconciliations demonstrate both shortages and overages
