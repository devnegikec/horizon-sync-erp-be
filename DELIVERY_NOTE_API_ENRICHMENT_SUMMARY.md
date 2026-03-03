# Delivery Note API Enrichment - Summary

## Overview

Enhanced the Delivery Note API endpoint `/api/v1/delivery-notes/{id}` to return enriched nested objects for items and reference documents, similar to the Pick List API enrichment.

## Changes Made

### 1. Schema Updates (`core-service/app/schemas/delivery_note.py`)

Added new nested reference models:

```python
class NestedReference(BaseModel):
    """Nested reference details (id, name, code)"""
    id: str
    name: str
    code: str

class NestedReferenceWithType(BaseModel):
    """Nested reference with type (for sales_order, pick_list, etc.)"""
    id: str
    reference_type: str
    name: str
    code: str
```

Updated response models:

- `DeliveryNoteItemResponse`: Added `item` nested field, removed redundant `item_id`
- `DeliveryNoteResponse`: Added `reference` nested field

### 2. Service Layer Updates (`core-service/app/services/delivery_note_service.py`)

Updated `_to_response()` method to:

1. **Query related entities**:
   - `Item` table for item details (item_code, item_name)
   - `SalesOrder` table for sales order reference details
   - `PickList` table for pick list reference details

2. **Build nested objects**:
   - Reference level: `reference` object with type (sales_order or pick_list)
   - Item level: Each item gets `item` object with id, name, code

3. **Return enriched response** with all nested data

### 3. API Response Format

**Before** (only IDs):

```json
{
  "reference_type": "sales_order",
  "reference_id": "9f03419b-98cf-44d6-9796-da53d0a1dc44",
  "items": [
    {
      "id": "uuid",
      "item_id": "a17ac10b-58cc-4372-a567-0e02b2c3d010",
      "qty": "50.000"
    }
  ]
}
```

**After** (enriched with nested objects, redundant IDs removed):

```json
{
  "reference_type": "sales_order",
  "reference_id": "9f03419b-98cf-44d6-9796-da53d0a1dc44",
  "reference": {
    "id": "9f03419b-98cf-44d6-9796-da53d0a1dc44",
    "reference_type": "sales_order",
    "name": "SO-2026-0001",
    "code": "SO-2026-0001"
  },
  "items": [
    {
      "id": "uuid",
      "item": {
        "id": "a17ac10b-58cc-4372-a567-0e02b2c3d010",
        "name": "A4 Printer Paper",
        "code": "OFF-PPR-A4"
      },
      "qty": "50.000",
      "uom": "REM",
      "rate": "25.00",
      "amount": "1250.00"
    }
  ]
}
```

## Benefits

1. **Reduced API Calls**: Frontend doesn't need separate calls to fetch item/reference details
2. **Better UX**: Can display item names and reference codes immediately
3. **Type Safety**: Pydantic models ensure consistent structure
4. **Cleaner Response**: Removed redundant `item_id` field from items since it's in `item.id`
5. **Consistent with Pick List API**: Same enrichment pattern across related APIs

## Frontend Integration

Frontend can now directly access:

- `deliveryNote.reference.code` - Reference document code (SO or PL number)
- `deliveryNote.reference.reference_type` - Type of reference (sales_order or pick_list)
- `item.item.name` - Item name
- `item.item.code` - Item code

## Example Response

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "delivery_note_no": "DN-2026-0001",
  "customer_id": "uuid",
  "customer": {
    "customer_name": "Huge Rock",
    "customer_code": "HRU-01",
    "phone": "+1234567890",
    "email": "contact@hugerock.com"
  },
  "delivery_date": "2026-03-02T17:35:19.771769Z",
  "status": "submitted",
  "warehouse_id": "uuid",
  "warehouse": {
    "warehouse_name": "Main Warehouse",
    "warehouse_code": "WH-MAIN"
  },
  "pick_list_id": "uuid",
  "reference_type": "sales_order",
  "reference_id": "uuid",
  "reference": {
    "id": "uuid",
    "reference_type": "sales_order",
    "name": "SO-2026-0001",
    "code": "SO-2026-0001"
  },
  "remarks": null,
  "items": [
    {
      "id": "uuid",
      "item": {
        "id": "uuid",
        "name": "A4 Printer Paper",
        "code": "OFF-PPR-A4"
      },
      "qty": "50.000",
      "uom": "REM",
      "rate": "25.00",
      "amount": "1250.00",
      "warehouse_id": "uuid",
      "batch_no": null,
      "serial_nos": null,
      "sort_order": 0,
      "extra_data": null
    }
  ],
  "submitted_at": "2026-03-02T17:35:19.771769Z",
  "created_by": "uuid",
  "updated_by": "uuid",
  "created_at": "2026-03-02T17:33:22.601133Z",
  "updated_at": "2026-03-02T17:35:19.825475Z"
}
```

## Testing

To test the changes:

```bash
# Start the service
docker compose up core-service

# Call the endpoint
curl -X GET "http://localhost:8001/api/v1/delivery-notes/{delivery_note_id}" \
  -H "Authorization: Bearer {token}"
```

Expected response includes:

- ✅ `reference` object with type, name, and code
- ✅ Each item has `item` object with id, name, and code
- ✅ No redundant `item_id` field in items

## Files Modified

1. `core-service/app/schemas/delivery_note.py` - Added nested reference models, updated item response
2. `core-service/app/services/delivery_note_service.py` - Added enrichment logic to `_to_response()`

## Notes

- Only the `get_by_id` endpoint is enriched (detail view)
- List endpoint remains lightweight for performance
- All joins are performed in the service layer
- No database schema changes required
- Supports both `sales_order` and `pick_list` reference types
