# Invoice API Enhancement - Customer/Supplier Details & Items

## Summary

Enhanced the `GET /api/v1/invoices/{id}` endpoint to return customer/supplier details and invoice items, matching the format of the quotations API.

## Changes Made

### 1. Added InvoiceItem Model

**File**: `core-service/app/models/invoice.py`

Created the `InvoiceItem` model to represent invoice line items:

```python
class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: UUID
    organization_id: UUID
    invoice_id: UUID (FK to invoices)
    item_id: UUID (FK to items, nullable)
    description: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total_amount: Decimal
```

Added relationship to Invoice model:

```python
items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")
```

### 2. Updated Invoice Repository

**File**: `core-service/app/repositories/invoice_repository.py`

Modified `get_by_id()` to eagerly load invoice items using `joinedload`:

```python
query = (
    self.db.query(Invoice)
    .options(joinedload(Invoice.items))
    .filter(...)
)
```

### 3. Enhanced Invoice Service

**File**: `core-service/app/services/invoice_service.py`

Updated `_to_response()` method to include:

1. **Customer details** (when `party_type == "customer"`):

   - customer_name
   - customer_code
   - email
   - phone
   - address
   - address_line1
   - address_line2
   - city
   - state
   - postal_code
   - country
   - tax_number
   - status

2. **Supplier details** (when `party_type == "supplier"`):

   - supplier_name
   - supplier_code
   - email
   - phone
   - address
   - address_line1
   - address_line2
   - city
   - state
   - postal_code
   - country
   - tax_number
   - status

3. **Invoice items** array with:
   - id
   - organization_id
   - invoice_id
   - item_id
   - item_code
   - item_name
   - qty
   - uom
   - rate
   - amount
   - sort_order
   - extra_data
   - created_at
   - updated_at

## API Response Format

### GET /api/v1/invoices/{id}

**Response** (`200 OK`):

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "invoice_no": "INV-2025-001",
  "invoice_type": "sales",
  "party_id": "uuid",
  "party_type": "customer",
  "posting_date": "2025-06-15T00:00:00Z",
  "due_date": "2025-07-15T00:00:00Z",
  "status": "submitted",
  "grand_total": "16815.00",
  "outstanding_amount": "16815.00",
  "currency": "INR",
  "reference_type": "sales_order",
  "reference_id": "uuid",
  "remarks": null,
  "submitted_at": "2025-06-15T10:30:00Z",
  "created_by": "uuid",
  "updated_by": "uuid",
  "created_at": "2025-06-15T10:30:00Z",
  "updated_at": "2025-06-15T10:30:00Z",
  "customer": {
    "customer_name": "Acme Corporation",
    "customer_code": "CUST-001",
    "email": "contact@acme.com",
    "phone": "+1-555-0100",
    "address": "123 Business St",
    "address_line1": "Suite 100",
    "address_line2": null,
    "city": "New York",
    "state": "NY",
    "postal_code": "10001",
    "country": "USA",
    "tax_number": "12-3456789",
    "status": "active"
  },
  "items": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "invoice_id": "uuid",
      "item_id": "uuid",
      "item_code": "HZN-LP-01",
      "item_name": "Horizon Pro Laptop",
      "qty": "10.000",
      "uom": "Unit",
      "rate": "1200.00",
      "amount": "12000.00",
      "sort_order": 1,
      "extra_data": null,
      "created_at": "2025-06-15T10:30:00Z",
      "updated_at": "2025-06-15T10:30:00Z"
    },
    {
      "id": "uuid",
      "organization_id": "uuid",
      "invoice_id": "uuid",
      "item_id": "uuid",
      "item_code": "HZN-MO-05",
      "item_name": "Optical Gaming Mouse",
      "qty": "50.000",
      "uom": "Piece",
      "rate": "45.00",
      "amount": "2250.00",
      "sort_order": 2,
      "extra_data": null,
      "created_at": "2025-06-15T10:30:00Z",
      "updated_at": "2025-06-15T10:30:00Z"
    }
  ]
}
```

### For Purchase Invoices (party_type = "supplier")

The response includes `supplier` object instead of `customer`:

```json
{
  ...
  "party_type": "supplier",
  "supplier": {
    "supplier_name": "TechWorld Supplies",
    "supplier_code": "SUPP-002",
    "email": "sales@techworld.com",
    "phone": "+1-555-0200",
    "address": "456 Vendor Ave",
    "address_line1": null,
    "address_line2": null,
    "city": "San Francisco",
    "state": "CA",
    "postal_code": "94102",
    "country": "USA",
    "tax_number": "98-7654321",
    "status": "active"
  },
  "items": [...]
}
```

## Database Schema

### invoice_items Table

```sql
CREATE TABLE IF NOT EXISTS invoice_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL,
    invoice_id UUID NOT NULL,
    item_id UUID,
    item_code VARCHAR(100),
    item_name VARCHAR(255),
    qty NUMERIC(15,3) NOT NULL,
    uom VARCHAR(50) NOT NULL,
    rate NUMERIC(15,2),
    amount NUMERIC(15,2),
    sort_order INTEGER DEFAULT 0,
    extra_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_invi_invoice FOREIGN KEY (invoice_id)
        REFERENCES invoices(id) ON DELETE CASCADE,
    CONSTRAINT fk_invi_item FOREIGN KEY (item_id)
        REFERENCES items(id) ON DELETE SET NULL
);
```

## Backward Compatibility

✅ **Fully backward compatible**

- Existing invoice endpoints continue to work
- New fields (`customer`/`supplier`, `items`) are added to the response
- No breaking changes to existing fields
- Clients that don't expect these fields can safely ignore them

## Testing Recommendations

### Manual Testing

1. **Test sales invoice with customer**:

   ```bash
   GET /api/v1/invoices/{sales_invoice_id}
   ```

   - Verify `customer` object is present
   - Verify all customer fields are populated
   - Verify `items` array is present

2. **Test purchase invoice with supplier**:

   ```bash
   GET /api/v1/invoices/{purchase_invoice_id}
   ```

   - Verify `supplier` object is present
   - Verify all supplier fields are populated
   - Verify `items` array is present

3. **Test invoice without items**:

   - Verify response doesn't include `items` key or includes empty array

4. **Test invoice with deleted customer/supplier**:
   - Verify response doesn't include `customer`/`supplier` key

### Automated Tests

```python
def test_get_invoice_with_customer_details():
    # Create invoice with customer
    response = client.get(f"/api/v1/invoices/{invoice_id}")
    assert response.status_code == 200
    data = response.json()
    assert "customer" in data
    assert data["customer"]["customer_name"] == "Acme Corporation"
    assert data["customer"]["email"] == "contact@acme.com"

def test_get_invoice_with_items():
    response = client.get(f"/api/v1/invoices/{invoice_id}")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert "qty" in data["items"][0]
    assert "rate" in data["items"][0]
    assert "item_code" in data["items"][0]
    assert "item_name" in data["items"][0]
```

## Performance Considerations

- Uses `joinedload` for eager loading of items (single query)
- Customer/supplier details fetched with a separate query (could be optimized with relationship if needed)
- No N+1 query issues

## Future Enhancements

1. **Add item details**: Include item_code, item_name from items table
2. **Add tax template details**: Include tax template breakdown
3. **Add payment history**: Show payments made against this invoice
4. **Add stock level info**: Show current stock for each item
5. **Optimize customer/supplier loading**: Use relationship instead of separate query
