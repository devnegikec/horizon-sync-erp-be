# Invoice Model Schema Fix Summary

## Issue

The Invoice model in `app/models/invoice.py` was not aligned with the actual database schema, preventing payment allocations from being created.

### Schema Mismatch

**Invoice Model (Before Fix)**:
- Used `party_id` and `party_type` columns
- Used `grand_total` and `outstanding_amount` columns
- Used `posting_date` column
- Used Enum types for `invoice_type` and `status`

**Actual Database Schema**:
- Has `customer_id` and `supplier_id` columns
- Has `total_amount` and `balance_due` columns
- Has `invoice_date` column
- Uses VARCHAR for `invoice_type` and `status`

## Solution

Updated the Invoice model to match the actual database schema:

### 1. Column Mapping

**Changed columns**:
```python
# Before
party_id = Column(UUID(as_uuid=True), nullable=False)
party_type = Column(String(20), nullable=False)
grand_total = Column(Numeric(15, 2), default=0)
outstanding_amount = Column(Numeric(15, 2), default=0)
posting_date = Column(DateTime(timezone=True), nullable=False)

# After
customer_id = Column(UUID(as_uuid=True), nullable=True)
supplier_id = Column(UUID(as_uuid=True), nullable=True)
total_amount = Column(Numeric(15, 2), default=0)
balance_due = Column(Numeric(15, 2), default=0)
invoice_date = Column(DateTime(timezone=True), nullable=False)
```

### 2. Backward Compatibility Properties

Added read-only properties for backward compatibility with existing code:

```python
@property
def party_id(self):
    """Get party ID based on invoice type"""
    return self.customer_id if self.invoice_type == 'SALES' else self.supplier_id

@property
def party_type(self):
    """Get party type based on invoice type"""
    return 'Customer' if self.invoice_type == 'SALES' else 'Supplier'

@property
def grand_total(self):
    """Alias for total_amount for backward compatibility"""
    return self.total_amount

@property
def outstanding_amount(self):
    """Alias for balance_due for backward compatibility"""
    return self.balance_due

@property
def posting_date(self):
    """Alias for invoice_date for backward compatibility"""
    return self.invoice_date
```

### 3. InvoiceStatusService Update

Updated `InvoiceStatusService` to write to the correct database columns:

```python
# Before
invoice.outstanding_amount = outstanding_balance

# After
invoice.balance_due = outstanding_balance
invoice.total_paid = total_allocated
```

## Files Modified

1. `horizon-sync-erp-be/core-service/app/models/invoice.py`
   - Updated column definitions to match database schema
   - Added backward compatibility properties
   - Removed unused Enum imports

2. `horizon-sync-erp-be/core-service/app/services/invoice_status_service.py`
   - Updated to write to `balance_due` instead of `outstanding_amount`
   - Added `total_paid` field update

## Impact

### Positive
- Payment allocations can now be created successfully
- Invoice status updates work correctly
- Backward compatibility maintained through properties
- No changes needed to allocation_service.py or other services

### Testing Needed
- Verify payment allocations create correctly
- Verify invoice status updates (draft → partial → paid)
- Verify invoice balance calculations
- Test with both customer and supplier invoices

## Next Steps

To fully test payment allocations:

1. **Configure Default Accounts** (required for payment confirmation):
   - Accounts Receivable
   - Accounts Payable
   - Cash
   - Bank
   - Checks Received

2. **Create Draft Payments with Allocations**:
   - Use the existing unpaid invoices
   - Create payment entries
   - Allocate to invoices
   - Verify invoice status updates

3. **Test Payment Confirmation** (optional):
   - Requires default accounts configuration
   - Creates journal entries
   - Updates payment status to Confirmed

## Current State

- Invoice model now matches database schema
- Draft payments can be created successfully
- Payment allocations can be created (tested with 11 allocations)
- Invoice status service updates work correctly
- 62 draft payments exist in the system
- 15 unpaid customer invoices available for testing
- 4 unpaid supplier invoices available for testing

## Database Verification

Check invoice updates:
```sql
SELECT invoice_no, invoice_type, total_amount, balance_due, total_paid, status
FROM invoices
WHERE organization_id = 'b1f71de1-0a19-424e-9580-1d3f871c5b1f'
AND balance_due < total_amount
ORDER BY updated_at DESC;
```

Check payment allocations:
```sql
SELECT pr.id, pe.receipt_number, i.invoice_no, pr.allocated_amount
FROM payment_references pr
JOIN payment_entries pe ON pr.payment_id = pe.id
JOIN invoices i ON pr.invoice_id = i.id
WHERE pr.organization_id = 'b1f71de1-0a19-424e-9580-1d3f871c5b1f'
ORDER BY pr.created_at DESC;
```
