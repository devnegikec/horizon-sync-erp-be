# Smart Picking Stock Reservation Enhancement

## Summary

Enhanced the Smart Picking system to show reserved stock quantities and automatically reserve stock when sales orders are confirmed.

## Changes Made

### 1. Added `quantity_reserved` to Allocation Suggestion Response

**File**: `core-service/app/schemas/smart_picking.py`

Added `quantity_reserved: int` field to `AllocationSuggestionItem` schema so the frontend can see how much stock is already reserved by other confirmed orders.

**File**: `core-service/app/services/smart_picking_service.py`

Updated `suggest_allocation()` method to include `quantity_reserved` in the response for each warehouse allocation suggestion.

### 2. Automatic Stock Reservation on Sales Order Confirmation

**File**: `core-service/app/services/sales_order_service.py`

Added new method `_reserve_stock_and_split_items()` that is automatically called when a sales order status changes from `DRAFT` to `CONFIRMED`.

**Behavior**:

When confirming a sales order, the system now:

1. **Queries stock levels** ordered by `quantity_available DESC` (richest warehouse first)
2. **Validates sufficient stock** exists across all warehouses
3. **Splits items across warehouses** if a single warehouse cannot fulfill the full quantity
4. **Creates multiple `sales_order_items`** entries for the same item if split across warehouses
5. **Reserves stock** by updating `stock_levels`:
   - `quantity_reserved` += allocated_qty
   - `quantity_available` -= allocated_qty
6. **Stores warehouse_id** in `sales_order_items.extra_data` for each allocation
7. **Adjusts amounts proportionally** when splitting (rate, amount, tax_amount, total_amount)

**Example**:

If a sales order has:

- Item A: 60 pieces

And stock levels are:

- Warehouse 1: 50 available
- Warehouse 2: 30 available

On confirmation, the system creates:

- `sales_order_items` entry 1: Item A, 50 pieces, Warehouse 1
- `sales_order_items` entry 2: Item A, 10 pieces, Warehouse 2

And updates stock_levels:

- Warehouse 1: `quantity_reserved` += 50, `quantity_available` -= 50
- Warehouse 2: `quantity_reserved` += 10, `quantity_available` -= 10

### 3. Updated Frontend Steering File

**File**: `.kiro/steering/frontend-smart-picking-module.md`

Updated the frontend documentation to:

1. **Add `quantity_reserved` field** to TypeScript types and API response examples
2. **Document the automatic stock reservation** behavior when confirming sales orders
3. **Update workflow diagram** to show confirmation step
4. **Add "Reserved" column** to the allocation table component example
5. **Explain that multiple sales_order_items** may exist for the same item if split across warehouses

## API Changes

### GET /api/v1/smart-picking/suggest-allocation/{sales_order_id}

**Response now includes**:

```json
{
  "suggestions": [
    {
      "item_id": "uuid",
      "warehouse_id": "uuid",
      "current_available": 120,
      "quantity_reserved": 30, // NEW FIELD
      "suggested_qty": 50
    }
  ]
}
```

### PUT /api/v1/sales-orders/{id}/status

**New behavior when status changes to "confirmed"**:

- Automatically reserves stock across warehouses
- Splits sales_order_items if needed
- Validates sufficient stock exists (raises 422 if insufficient)

## Database Impact

### stock_levels table

When confirming a sales order:

- `quantity_reserved` is incremented
- `quantity_available` is decremented
- `quantity_on_hand` remains unchanged

### sales_order_items table

When confirming a sales order with items that need multi-warehouse fulfillment:

- Multiple rows created for the same item (one per warehouse)
- `extra_data` column stores `{"warehouse_id": "uuid"}`
- `qty`, `amount`, `tax_amount`, `total_amount` are split proportionally

## Error Handling

### Insufficient Stock on Confirmation

If a sales order cannot be fulfilled with available stock:

**Error**: `422 Unprocessable Entity`

```json
{
  "detail": "Insufficient stock for item Widget A: required=100, available=75"
}
```

### No Stock Available

If no stock exists for an item:

**Error**: `422 Unprocessable Entity`

```json
{
  "detail": "No stock available for item {item_id}"
}
```

## Testing Recommendations

### Backend Tests

1. **Test stock reservation on confirmation**:
   - Confirm SO with sufficient stock in single warehouse
   - Confirm SO requiring multi-warehouse split
   - Verify stock_levels updated correctly
   - Verify multiple sales_order_items created

2. **Test insufficient stock scenarios**:
   - Confirm SO with insufficient total stock
   - Verify error message and no partial reservation

3. **Test allocation suggestions**:
   - Verify `quantity_reserved` appears in response
   - Verify suggestions account for already-reserved stock

### Frontend Tests

1. **Display reserved stock**:
   - Show `quantity_reserved` column in allocation table
   - Verify reserved stock is displayed correctly

2. **Handle multi-warehouse items**:
   - Display multiple rows for same item if split across warehouses
   - Show warehouse info for each allocation

## Migration Notes

**No database migration required** — all fields already exist:

- `stock_levels.quantity_reserved` (already exists)
- `stock_levels.quantity_available` (already exists)
- `sales_order_items.extra_data` (already exists, JSONB column)

## Backward Compatibility

✅ **Fully backward compatible**

- Existing sales orders are not affected
- Only new confirmations trigger stock reservation
- API response adds new field but doesn't break existing clients
- Frontend can gracefully handle missing `quantity_reserved` (defaults to 0)

## Performance Considerations

- Uses `SELECT ... FOR UPDATE` row locks to prevent race conditions
- All operations within a single transaction
- Minimal additional queries (1 per item to fetch stock levels)

## Future Enhancements

1. **Unreserve stock on cancellation**: When SO is cancelled, decrement `quantity_reserved`
2. **Reservation timeout**: Auto-release reservations after X days if not fulfilled
3. **Reservation history**: Track reservation changes in audit log
4. **Partial confirmation**: Allow confirming only items with sufficient stock
