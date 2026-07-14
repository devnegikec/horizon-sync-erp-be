# Delivery Notes API Enhancement

## Summary

Enhanced the Delivery Notes API to return additional related data from warehouse and customer tables, as well as previously missing fields from the delivery_notes table.

## Changes Made

### 1. Repository Layer (`delivery_note_repository.py`)

- Added SQL joins with `Customer` and `Warehouse` tables
- Used `outerjoin` to handle cases where warehouse might be null
- Added `joinedload` for efficient loading of delivery note items

### 2. Model Layer (`delivery_note.py`)

- Added relationships to `Customer` and `Warehouse` models
- Enables easy access to related data through SQLAlchemy relationships

### 3. Service Layer (`delivery_note_service.py`)

- Updated `_to_response()` to include:
  - Customer information (name, code, phone, email)
  - Warehouse information (name, code)
  - Delivery note items with all fields
  - `extra_data` field
  - `remarks` field
- Updated `_to_list_item()` to include:
  - Customer information (name, code, phone, email)
  - Warehouse information (name, code)
  - `warehouse_id` field
  - `remarks` field

### 4. Schema Layer (`delivery_note.py`)

- Added `CustomerInfo` schema for embedded customer data
- Added `WarehouseInfo` schema for embedded warehouse data
- Added `DeliveryNoteItemResponse` schema with `extra_data` field
- Updated `DeliveryNoteResponse` to include:
  - `customer: CustomerInfo | None`
  - `warehouse: WarehouseInfo | None`
  - `items: list[DeliveryNoteItemResponse]`
  - `extra_data: dict | None`
- Updated `DeliveryNoteListItem` to include:
  - `customer: CustomerInfo | None`
  - `warehouse: WarehouseInfo | None`
  - `warehouse_id: UUID | None`
  - `remarks: str | None`

## API Response Examples

### GET /api/v1/delivery-notes/{id}

**Before:**

```json
{
  "id": "uuid",
  "delivery_note_no": "DN-001",
  "customer_id": "uuid",
  "warehouse_id": "uuid",
  "status": "draft",
  "delivery_date": "2024-01-01T00:00:00Z",
  "remarks": "Handle with care",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

**After:**

```json
{
  "id": "uuid",
  "delivery_note_no": "DN-001",
  "customer_id": "uuid",
  "customer": {
    "customer_name": "Acme Corp",
    "customer_code": "CUST-001",
    "phone": "+1234567890",
    "email": "contact@acme.com"
  },
  "warehouse_id": "uuid",
  "warehouse": {
    "warehouse_name": "Main Warehouse",
    "warehouse_code": "WH-001"
  },
  "status": "draft",
  "delivery_date": "2024-01-01T00:00:00Z",
  "remarks": "Handle with care",
  "extra_data": {
    "delivery_instructions": "Ring doorbell twice"
  },
  "items": [
    {
      "id": "uuid",
      "item_id": "uuid",
      "qty": 10.0,
      "uom": "PCS",
      "rate": 100.0,
      "amount": 1000.0,
      "warehouse_id": "uuid",
      "batch_no": "BATCH-001",
      "serial_nos": ["SN001", "SN002"],
      "sort_order": 0,
      "extra_data": {
        "notes": "Fragile items"
      }
    }
  ],
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

### GET /api/v1/delivery-notes (List)

**Before:**

```json
{
  "delivery_notes": [
    {
      "id": "uuid",
      "delivery_note_no": "DN-001",
      "customer_id": "uuid",
      "status": "draft",
      "delivery_date": "2024-01-01T00:00:00Z",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {...}
}
```

**After:**

```json
{
  "delivery_notes": [
    {
      "id": "uuid",
      "delivery_note_no": "DN-001",
      "customer_id": "uuid",
      "customer": {
        "customer_name": "Acme Corp",
        "customer_code": "CUST-001",
        "phone": "+1234567890",
        "email": "contact@acme.com"
      },
      "warehouse_id": "uuid",
      "warehouse": {
        "warehouse_name": "Main Warehouse",
        "warehouse_code": "WH-001"
      },
      "status": "draft",
      "delivery_date": "2024-01-01T00:00:00Z",
      "remarks": "Handle with care",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "pagination": {...}
}
```

## Benefits

1. **Reduced API Calls**: Frontend no longer needs to make separate calls to fetch customer and warehouse details
2. **Better Performance**: Uses SQL joins instead of multiple queries
3. **Complete Data**: All relevant fields are now included in responses
4. **Improved UX**: Frontend can display customer and warehouse names directly without additional lookups

## Fields Added

### Customer Information

- `customer_name` - Customer's full name
- `customer_code` - Customer's unique code
- `phone` - Customer's phone number
- `email` - Customer's email address

### Warehouse Information

- `warehouse_name` - Warehouse name
- `warehouse_code` - Warehouse unique code

### Delivery Note Fields

- `remarks` - Delivery notes/instructions (now in list response too)
- `extra_data` - Additional metadata (JSON field)
- `items` - Full list of delivery note items with all fields (in detail response)

### Delivery Note Item Fields

- `extra_data` - Additional metadata for each item

## Backward Compatibility

✅ All existing fields remain unchanged
✅ New fields are added as optional (nullable)
✅ Existing API consumers will continue to work without changes
✅ New consumers can take advantage of the additional data

## Testing

Test the enhanced endpoints:

```bash
# Get single delivery note with full details
curl -X GET "http://localhost:8001/api/v1/delivery-notes/{id}" \
  -H "Authorization: Bearer YOUR_TOKEN"

# List delivery notes with customer and warehouse info
curl -X GET "http://localhost:8001/api/v1/delivery-notes?page=1&page_size=20" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Notes

- Customer and warehouse data will be `null` if the relationships don't exist
- Uses `outerjoin` to handle optional warehouse relationships
- Items are only loaded in the detail endpoint (not in list for performance)
- All joins are performed at the database level for optimal performance
