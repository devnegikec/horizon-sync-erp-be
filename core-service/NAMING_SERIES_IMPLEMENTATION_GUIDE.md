# Quick Implementation Guide: Auto-Update Naming Series

## For Other Document Types (Sales Orders, Invoices, etc.)

Follow these steps to add automatic naming series updates to any document creation endpoint.

## Step-by-Step Implementation

### 1. Add Required Imports

At the top of your endpoint file (e.g., `app/api/v1/endpoints/sales_orders.py`):

```python
import logging
from fastapi import Request  # Add this if not present

from app.services.organization_client import organization_client
from app.utils.naming_series import extract_number_from_document_no

logger = logging.getLogger(__name__)
```

### 2. Update the Create Endpoint

Modify your POST endpoint to include the naming series update logic:

```python
@router.post("", response_model=YourDocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    body: YourDocumentCreate,
    request: Request,  # ← Add this parameter
    current_user: CurrentUser = Depends(require_permission(YOUR_PERMISSION)),
    db: Session = Depends(get_db),
):
    """Create document. Requires your.permission."""
    svc = YourDocumentService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)

    # ========== ADD THIS BLOCK ==========
    # Update naming series in identity service
    if data.get("your_document_no_field"):  # e.g., "sales_order_no", "invoice_no"
        current_number = extract_number_from_document_no(data["your_document_no_field"])

        if current_number is not None:
            auth_header = request.headers.get("Authorization", "")

            try:
                await organization_client.update_naming_series(
                    organization_id=current_user.organization_id,
                    document_type="your_document_type",  # e.g., "sales_order", "invoice"
                    current_number=current_number,
                    auth_token=auth_header.replace("Bearer ", ""),
                )
            except Exception as e:
                logger.error(
                    f"Failed to update naming series for {data['your_document_no_field']}: {e}"
                )
    # ====================================

    return YourDocumentResponse.model_validate(data)
```

### 3. Document Type Mapping

Ensure your document prefix is mapped in `app/utils/naming_series.py`:

```python
prefix_map = {
    "QT": "quotation",
    "SO": "sales_order",
    "INV": "invoice",
    "PO": "purchase_order",
    "DN": "delivery_note",
    "PR": "purchase_receipt",
    "PAY": "payment",
    "PL": "pick_list",
    "MR": "material_request",
    "RFQ": "rfq",
    # Add your document type if not listed
}
```

## Real Examples

### Sales Order

```python
# app/api/v1/endpoints/sales_orders.py

@router.post("", response_model=SalesOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_sales_order(
    body: SalesOrderCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission(SALES_ORDER_CREATE)),
    db: Session = Depends(get_db),
):
    svc = SalesOrderService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)

    if data.get("sales_order_no"):
        current_number = extract_number_from_document_no(data["sales_order_no"])
        if current_number is not None:
            auth_header = request.headers.get("Authorization", "")
            try:
                await organization_client.update_naming_series(
                    organization_id=current_user.organization_id,
                    document_type="sales_order",
                    current_number=current_number,
                    auth_token=auth_header.replace("Bearer ", ""),
                )
            except Exception as e:
                logger.error(f"Failed to update naming series: {e}")

    return SalesOrderResponse.model_validate(data)
```

### Invoice

```python
# app/api/v1/endpoints/invoices.py

@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission(INVOICE_CREATE)),
    db: Session = Depends(get_db),
):
    svc = InvoiceService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)

    if data.get("invoice_no"):
        current_number = extract_number_from_document_no(data["invoice_no"])
        if current_number is not None:
            auth_header = request.headers.get("Authorization", "")
            try:
                await organization_client.update_naming_series(
                    organization_id=current_user.organization_id,
                    document_type="invoice",
                    current_number=current_number,
                    auth_token=auth_header.replace("Bearer ", ""),
                )
            except Exception as e:
                logger.error(f"Failed to update naming series: {e}")

    return InvoiceResponse.model_validate(data)
```

### Purchase Order

```python
# app/api/v1/endpoints/purchase_orders.py

@router.post("", response_model=PurchaseOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(
    body: PurchaseOrderCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission(PURCHASE_ORDER_CREATE)),
    db: Session = Depends(get_db),
):
    svc = PurchaseOrderService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)

    if data.get("purchase_order_no"):
        current_number = extract_number_from_document_no(data["purchase_order_no"])
        if current_number is not None:
            auth_header = request.headers.get("Authorization", "")
            try:
                await organization_client.update_naming_series(
                    organization_id=current_user.organization_id,
                    document_type="purchase_order",
                    current_number=current_number,
                    auth_token=auth_header.replace("Bearer ", ""),
                )
            except Exception as e:
                logger.error(f"Failed to update naming series: {e}")

    return PurchaseOrderResponse.model_validate(data)
```

## Checklist

Before implementing, verify:

- [ ] Document number field name (e.g., `quotation_no`, `sales_order_no`)
- [ ] Document type for naming series (e.g., `quotation`, `sales_order`)
- [ ] Document prefix is in the prefix_map (e.g., `QT`, `SO`, `INV`)
- [ ] Endpoint is async (uses `async def`)
- [ ] Request parameter is added to function signature
- [ ] Imports are added at the top of the file
- [ ] Error handling is in place (try/except)
- [ ] Logger is configured

## Testing

After implementation, test with:

```bash
# 1. Create a document
curl -X POST http://localhost:8001/api/v1/your-endpoint \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{ ... }'

# 2. Check the response for document number
# Response: { "your_document_no": "PREFIX-0035", ... }

# 3. Verify naming series was updated
curl http://localhost:8000/api/v1/identity/organizations/{org_id} \
  -H "Authorization: Bearer {token}"

# 4. Check logs for any errors
docker compose logs core-service | grep "naming series"
```

## Common Issues

### Issue: `Request` parameter not found

**Solution:** Add import: `from fastapi import Request`

### Issue: Endpoint is not async

**Solution:** Change `def` to `async def`

### Issue: Document number not extracted

**Solution:** Check the field name matches your response (e.g., `sales_order_no` not `order_no`)

### Issue: Wrong document type

**Solution:** Verify the document_type matches the naming_series key in organization settings

## Document Type Reference

| Document         | Prefix | Document Type      | Field Name          |
| ---------------- | ------ | ------------------ | ------------------- |
| Quotation        | QT     | `quotation`        | `quotation_no`      |
| Sales Order      | SO     | `sales_order`      | `sales_order_no`    |
| Invoice          | INV    | `invoice`          | `invoice_no`        |
| Purchase Order   | PO     | `purchase_order`   | `purchase_order_no` |
| Delivery Note    | DN     | `delivery_note`    | `delivery_note_no`  |
| Purchase Receipt | PR     | `purchase_receipt` | `receipt_no`        |
| Payment          | PAY    | `payment`          | `payment_no`        |
| Pick List        | PL     | `pick_list`        | `pick_list_no`      |
| Material Request | MR     | `material_request` | `request_no`        |
| RFQ              | RFQ    | `rfq`              | `rfq_no`            |

## Need Help?

See the full documentation: `NAMING_SERIES_AUTO_UPDATE.md`
