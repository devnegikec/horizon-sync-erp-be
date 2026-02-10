# Stock Levels API - Item and Warehouse Details

## ✅ Already Implemented!

The stock levels API **already includes** item name, code, warehouse name, and code in the response.

## Response Structure

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "product_id": "uuid",
  "warehouse_id": "uuid",
  "quantity_on_hand": 500,
  "quantity_reserved": 50,
  "quantity_available": 450,
  "last_counted_at": "2024-01-01T00:00:00Z",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "product": {
    "name": "RAMA Mixture",
    "code": "RAMA-T-002"
  },
  "warehouse": {
    "name": "Main Warehouse",
    "code": "WH-MAIN"
  }
}
```

## Test the API

### 1. Get Authentication Token

First, login to get an access token:

```bash
# Login
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@example.com",
    "password": "your_password"
  }'
```

Save the `access_token` from the response.

### 2. List Stock Levels

```bash
# List all stock levels (with item and warehouse details)
curl -X GET "http://localhost:8001/api/v1/stock-levels?page=1&page_size=10" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

**Expected Response:**

```json
{
  "stock_levels": [
    {
      "id": "8e15d1e9-97bd-4a33-a1f8-4d3df506a458",
      "product_id": "...",
      "warehouse_id": "...",
      "quantity_on_hand": 500,
      "quantity_reserved": 50,
      "quantity_available": 450,
      "last_counted_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-01T00:00:00Z",
      "product": {
        "name": "RAMA Mixture",
        "code": "RAMA-T-002"
      },
      "warehouse": {
        "name": "Main Warehouse",
        "code": "WH-MAIN"
      }
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_items": 7,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

### 3. Get Stock Level by ID

```bash
# Get specific stock level
curl -X GET "http://localhost:8001/api/v1/stock-levels/{level_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4. Get Stock Level by Location

```bash
# Get stock level for specific item in specific warehouse
curl -X GET "http://localhost:8001/api/v1/stock-levels/by-location?item_id={item_id}&warehouse_id={warehouse_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 5. Filter by Item

```bash
# Get all stock levels for a specific item
curl -X GET "http://localhost:8001/api/v1/stock-levels?item_id={item_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 6. Filter by Warehouse

```bash
# Get all stock levels in a specific warehouse
curl -X GET "http://localhost:8001/api/v1/stock-levels?warehouse_id={warehouse_id}" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Implementation Details

### Schema (Already Implemented)

```python
class ProductInfo(BaseModel):
    """Product (item) name and code from Items table."""
    name: str
    code: str

class WarehouseInfo(BaseModel):
    """Warehouse name and code from warehouses_extended table."""
    name: str
    code: str

class StockLevelResponse(BaseModel):
    id: UUID
    organization_id: UUID
    product_id: UUID
    warehouse_id: UUID
    quantity_on_hand: int
    quantity_reserved: int
    quantity_available: int
    last_counted_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    product: ProductInfo | None = None  # ✅ Item details
    warehouse: WarehouseInfo | None = None  # ✅ Warehouse details
```

### Repository (Already Implemented)

The repository uses `joinedload` to eagerly load the related item and warehouse:

```python
def get_by_id(self, level_id: UUID, organization_id: UUID) -> StockLevel | None:
    return (
        self.db.query(StockLevel)
        .options(
            joinedload(StockLevel.product),  # ✅ Load item
            joinedload(StockLevel.warehouse),  # ✅ Load warehouse
        )
        .filter(...)
        .first()
    )
```

### Conversion Function (Already Implemented)

```python
def stock_level_to_response(s: "StockLevel") -> StockLevelResponse:
    product = None
    if getattr(s, "product", None) is not None:
        product = ProductInfo(
            name=s.product.item_name,  # ✅ Item name
            code=s.product.item_code   # ✅ Item code
        )

    warehouse = None
    if getattr(s, "warehouse", None) is not None:
        warehouse = WarehouseInfo(
            name=s.warehouse.name,  # ✅ Warehouse name
            code=s.warehouse.code   # ✅ Warehouse code
        )

    return StockLevelResponse(
        ...,
        product=product,
        warehouse=warehouse,
    )
```

## Verify in Database

You can verify the data exists:

```bash
docker exec -it horizon_postgres psql -U horizon_user -d core_db -c "
SELECT
    sl.id,
    i.item_code,
    i.item_name,
    w.code as warehouse_code,
    w.name as warehouse_name,
    sl.quantity_on_hand,
    sl.quantity_reserved,
    sl.quantity_available
FROM stock_levels sl
JOIN items i ON sl.product_id = i.id
JOIN warehouses_extended w ON sl.warehouse_id = w.id
ORDER BY w.code, i.item_code;
"
```

## Summary

✅ **Item details** (name and code) are already included in the response via the `product` field
✅ **Warehouse details** (name and code) are already included in the response via the `warehouse` field
✅ All endpoints return these details: list, get by ID, get by location
✅ The implementation uses proper eager loading to avoid N+1 queries

**No changes needed - the feature is already fully implemented!** 🎉
