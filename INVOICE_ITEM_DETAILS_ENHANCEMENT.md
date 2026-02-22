# Invoice Item Details Enhancement

## Summary

Enhanced invoice items in the `GET /api/v1/invoices/{id}` endpoint to include comprehensive item details matching the quotation API format.

## New Fields Added to Invoice Items

### Item Details

- **description** - Item description from items table
- **min_order_qty** - Minimum order quantity
- **max_order_qty** - Maximum order quantity
- **standard_rate** - Standard selling rate

### Tax Information

- **tax_template_id** - ID of the applicable tax template
- **tax_rate** - Total tax rate (sum of all tax rules)
- **tax_amount** - Calculated tax amount (amount × tax_rate / 100)
- **total_amount** - Line total including tax (amount + tax_amount)
- **tax_info** - Complete tax template breakdown with:
  - `id` - Tax template ID
  - `template_name` - Template name (e.g., "GST 18")
  - `template_code` - Template code (e.g., "GST_18")
  - `is_compound` - Whether any rule is compound
  - `breakup` - Array of tax rules with:
    - `rule_name` - Rule name (e.g., "CGST", "SGST")
    - `tax_type` - Tax type (e.g., "GST")
    - `rate` - Tax rate percentage
    - `is_compound` - Whether this rule is compound

## Implementation Details

### Files Modified

1. **`core-service/app/services/invoice_service.py`**
   - Added `StockLevelRepository` and `TaxTemplateRepository` imports
   - Added `_get_item_details()` method to fetch comprehensive item information
   - Updated `_to_response()` to include item details using spread operator

2. **`core-service/app/schemas/invoice.py`**
   - Updated `InvoiceItemResponse` schema to include new fields

### How It Works

For each invoice item, the service:

1. **Fetches item details** from the `items` table:
   - description
   - min_order_qty, max_order_qty
   - standard_rate

2. **Retrieves applicable tax template**:
   - Queries `tax_templates` based on organization, transaction type, item, and item_group
   - Calculates total tax rate from all tax rules
   - Computes tax amount: `amount × tax_rate / 100`
   - Computes total amount: `amount + tax_amount`

3. **Builds tax info breakdown**:
   - Extracts all tax rules from the template
   - Formats as array with rule details

## API Response Example

```json
{
  "invoice_no": "INV-SEED-001",
  "customer": {
    "customer_name": "Acme Corporation",
    "customer_code": "CUST-001",
    ...
  },
  "items": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "invoice_id": "uuid",
      "item_id": "uuid",
      "item_code": "HZN-LP-01",
      "item_name": "Horizon Pro Laptop",
      "description": "High-performance workstation for developers.",
      "qty": "3.000",
      "uom": "Unit",
      "rate": "1200.00",
      "amount": "3600.00",
      "sort_order": 1,
      "tax_template_id": "668321a8-31d6-4c26-9908-6e904d6a60d7",
      "tax_rate": "18.00",
      "tax_amount": "648.00",
      "total_amount": "4248.00",
      "min_order_qty": 1,
      "max_order_qty": 50,
      "standard_rate": "1200.00",
      "tax_info": {
        "id": "668321a8-31d6-4c26-9908-6e904d6a60d7",
        "template_name": "GST 18",
        "template_code": "GST_18",
        "is_compound": true,
        "breakup": [
          {
            "rule_name": "CGST",
            "tax_type": "GST",
            "rate": 9.0,
            "is_compound": true
          },
          {
            "rule_name": "SCST",
            "tax_type": "GST",
            "rate": 9.0,
            "is_compound": true
          }
        ]
      },
      "extra_data": null,
      "created_at": "2026-01-30T16:00:00Z",
      "updated_at": "2026-01-30T16:00:00Z"
    }
  ]
}
```

## Tax Calculation Logic

```python
# Get applicable tax template for the item
tax_result = tax_template_repo.get_applicable_template(
    organization_id=organization_id,
    transaction_type="Sales",
    item_id=item.id,
    item_group_id=item.item_group_id,
)

# Calculate total tax rate (sum of all rules)
total_tax_rate = sum(
    float(rule.tax_rate or 0)
    for rule in template.tax_rules
)

# Calculate tax amount
tax_amount = amount × (total_tax_rate / 100)

# Calculate total amount
total_amount = amount + tax_amount
```

## Backward Compatibility

✅ **Fully backward compatible**

- All new fields are optional in the schema
- Existing clients can ignore the new fields
- No breaking changes to existing fields

## Performance Considerations

- **Additional queries per item**:
  - 1 query to fetch item details from `items` table
  - 1 query to fetch applicable tax template
- **Optimization**: Items are eagerly loaded with `joinedload`, so the main invoice query is still efficient
- **Caching opportunity**: Tax templates could be cached per organization

## Edge Cases Handled

1. **Item not found**: Returns default values (null/0) for item-specific fields
2. **No tax template**: Returns null for tax fields, "0.00" for tax_rate and tax_amount
3. **No item_id**: Returns default values for all item-related fields

## Testing

Test with the provided token:

```bash
curl -X GET "http://localhost:8001/api/v1/invoices/d0000001-0001-4000-a000-000000000005" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

Verify:

- ✅ All items include description
- ✅ Tax information is present and accurate
- ✅ Tax breakdown matches template rules
- ✅ Calculations are correct (tax_amount, total_amount)
- ✅ Min/max order quantities are present
- ✅ Standard rate is included

## Future Enhancements

1. **Cache tax templates** - Reduce database queries for frequently used templates
2. **Include item_group details** - Add item group information like in quotations
3. **Include stock_levels** - Show current stock availability
4. **Batch fetch items** - Optimize to fetch all items in a single query
5. **Support purchase invoices** - Adjust transaction_type based on invoice_type
