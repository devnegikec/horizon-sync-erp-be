# Naming Series Implementation Checklist

Use this checklist when implementing automatic naming series updates for any document type.

## Pre-Implementation

- [ ] Identify the document type (e.g., sales_order, invoice, purchase_order)
- [ ] Identify the document number field name (e.g., sales_order_no, invoice_no)
- [ ] Identify the document prefix (e.g., SO, INV, PO)
- [ ] Verify the prefix is in `app/utils/naming_series.py` prefix_map
- [ ] Confirm the endpoint is async (uses `async def`)

## Code Changes

### 1. Add Imports

- [ ] Add `import logging` (if not present)
- [ ] Add `from fastapi import Request` (if not present)
- [ ] Add `from app.services.organization_client import organization_client`
- [ ] Add `from app.utils.naming_series import extract_number_from_document_no`
- [ ] Add `logger = logging.getLogger(__name__)` (if not present)

### 2. Update Function Signature

- [ ] Add `request: Request` parameter to the create endpoint
- [ ] Ensure function is `async def` (not just `def`)

### 3. Add Naming Series Update Logic

- [ ] Copy the naming series update block after document creation
- [ ] Update the document number field name (e.g., `sales_order_no`)
- [ ] Update the document type (e.g., `sales_order`)
- [ ] Update the error log message with correct document type

### 4. Code Template

```python
# After document creation
if data.get("your_document_no_field"):
    current_number = extract_number_from_document_no(data["your_document_no_field"])

    if current_number is not None:
        auth_header = request.headers.get("Authorization", "")

        try:
            await organization_client.update_naming_series(
                organization_id=current_user.organization_id,
                document_type="your_document_type",
                current_number=current_number,
                auth_token=auth_header.replace("Bearer ", ""),
            )
        except Exception as e:
            logger.error(
                f"Failed to update naming series for {data['your_document_no_field']}: {e}"
            )
```

## Testing

### Unit Tests

- [ ] Run standalone test: `python3 test_naming_series_standalone.py`
- [ ] Verify all tests pass

### Integration Tests

- [ ] Start services: `docker compose up -d`
- [ ] Create a test document via API
- [ ] Verify document is created successfully
- [ ] Check document number in response
- [ ] Verify naming series updated in Identity Service
- [ ] Check logs for any errors

### Test Commands

```bash
# 1. Create document
curl -X POST http://localhost:8001/api/v1/your-endpoint \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{ ... }'

# 2. Verify naming series
curl http://localhost:8000/api/v1/identity/organizations/{org_id} \
  -H "Authorization: Bearer {token}" | jq '.naming_series.your_document_type'

# 3. Check logs
docker compose logs core-service | grep "naming series"
```

## Verification

### Code Review

- [ ] Imports are at the top of the file
- [ ] Function signature includes `request: Request`
- [ ] Function is `async def`
- [ ] Document number field name is correct
- [ ] Document type matches naming_series key
- [ ] Error handling is in place (try/except)
- [ ] Logger is configured
- [ ] Code follows existing patterns

### Functionality

- [ ] Document creation succeeds
- [ ] Document number is generated correctly
- [ ] Naming series is updated in Identity Service
- [ ] Frontend shows correct next number
- [ ] Errors are logged but don't fail creation

### Error Scenarios

- [ ] Test with Identity Service down (document should still be created)
- [ ] Test with invalid auth token (document should still be created)
- [ ] Test with network timeout (document should still be created)
- [ ] Verify all errors are logged

## Documentation

- [ ] Update API documentation if needed
- [ ] Add comments explaining the naming series update
- [ ] Update README if this is a new feature
- [ ] Document any special cases or edge cases

## Deployment

- [ ] Code reviewed and approved
- [ ] Tests passing
- [ ] No breaking changes
- [ ] Environment variables configured
- [ ] Identity Service is running and accessible
- [ ] Monitoring/logging configured

## Post-Deployment

- [ ] Monitor logs for errors
- [ ] Verify naming series updates are working
- [ ] Check frontend displays correct numbers
- [ ] Monitor performance impact
- [ ] Gather user feedback

## Rollback Plan

If issues occur:

1. [ ] Identify the issue (check logs)
2. [ ] Determine if rollback is needed
3. [ ] If needed, revert the endpoint changes
4. [ ] Redeploy previous version
5. [ ] Verify document creation still works
6. [ ] Investigate and fix the issue
7. [ ] Re-deploy with fix

## Common Issues & Solutions

### Issue: Request parameter not found

**Solution:** Add `from fastapi import Request` import

### Issue: Function not async

**Solution:** Change `def` to `async def`

### Issue: Document number not extracted

**Solution:** Verify field name matches response (e.g., `sales_order_no` not `order_no`)

### Issue: Wrong document type

**Solution:** Check document_type matches naming_series key in organization settings

### Issue: Prefix not recognized

**Solution:** Add prefix to `app/utils/naming_series.py` prefix_map

### Issue: Identity Service unavailable

**Solution:** Verify IDENTITY_SERVICE_URL in .env and service is running

### Issue: Auth token invalid

**Solution:** Verify token is being passed correctly from request headers

## Reference

| Document         | Prefix | Document Type    | Field Name        | Endpoint           |
| ---------------- | ------ | ---------------- | ----------------- | ------------------ |
| Quotation        | QT     | quotation        | quotation_no      | /quotations        |
| Sales Order      | SO     | sales_order      | sales_order_no    | /sales-orders      |
| Invoice          | INV    | invoice          | invoice_no        | /invoices          |
| Purchase Order   | PO     | purchase_order   | purchase_order_no | /purchase-orders   |
| Delivery Note    | DN     | delivery_note    | delivery_note_no  | /delivery-notes    |
| Purchase Receipt | PR     | purchase_receipt | receipt_no        | /purchase-receipts |
| Payment          | PAY    | payment          | payment_no        | /payments          |
| Pick List        | PL     | pick_list        | pick_list_no      | /pick-lists        |
| Material Request | MR     | material_request | request_no        | /material-requests |
| RFQ              | RFQ    | rfq              | rfq_no            | /rfqs              |

## Resources

- **Full Documentation**: `NAMING_SERIES_AUTO_UPDATE.md`
- **Implementation Guide**: `NAMING_SERIES_IMPLEMENTATION_GUIDE.md`
- **Flow Diagram**: `NAMING_SERIES_FLOW_DIAGRAM.md`
- **Summary**: `../NAMING_SERIES_UPDATE_SUMMARY.md`

## Sign-off

- [ ] Developer: Implementation complete
- [ ] Reviewer: Code reviewed and approved
- [ ] QA: Tests passing
- [ ] DevOps: Deployed successfully
- [ ] Product: Feature verified

---

**Date Implemented**: **\*\***\_**\*\***

**Implemented By**: **\*\***\_**\*\***

**Reviewed By**: **\*\***\_**\*\***

**Document Type**: **\*\***\_**\*\***
