# Naming Series Auto-Update Implementation Summary

## What Was Implemented

Automatic synchronization of document numbering between Core Service and Identity Service. When a quotation (or any document) is created, the organization's naming series counter is automatically updated in the Identity Service.

## Problem Solved

**Before:**

- Frontend shows stale document numbers (e.g., "Next: QT-0030")
- Actual created quotation is QT-0035
- Manual updates required to keep naming series in sync

**After:**

- Create quotation → QT-0035
- Naming series automatically updates to 35
- Frontend always shows correct next number (QT-0036)

## Files Created/Modified

### New Files

1. **`core-service/app/services/organization_client.py`**
   - HTTP client for communicating with Identity Service
   - Methods: `update_naming_series()`, `get_organization_settings()`
   - Uses `httpx` for async HTTP requests

2. **`core-service/app/utils/naming_series.py`**
   - Utility functions for parsing document numbers
   - `extract_number_from_document_no()` - Extract number from "QT-0035" → 35
   - `get_document_type_from_prefix()` - Map "QT" → "quotation"
   - `should_update_naming_series()` - Validate document number format

3. **`core-service/app/utils/__init__.py`**
   - Package initialization for utils module

4. **`core-service/tests/test_naming_series.py`**
   - Comprehensive unit tests for naming series utilities
   - Tests for all edge cases and error scenarios

5. **`core-service/test_naming_series_standalone.py`**
   - Standalone test script (no dependencies required)
   - Quick validation of utility functions

6. **`core-service/NAMING_SERIES_AUTO_UPDATE.md`**
   - Complete technical documentation
   - Architecture diagrams, API flows, troubleshooting

7. **`core-service/NAMING_SERIES_IMPLEMENTATION_GUIDE.md`**
   - Quick reference for implementing in other endpoints
   - Copy-paste examples for sales orders, invoices, etc.

### Modified Files

1. **`core-service/app/api/v1/endpoints/quotations.py`**
   - Added naming series update logic to `create_quotation` endpoint
   - Extracts document number and calls Identity Service
   - Non-blocking, error-tolerant implementation

## How It Works

```
1. POST /api/v1/quotations
   ↓
2. Create quotation (QT-0035)
   ↓
3. Extract number: 35
   ↓
4. PATCH /api/v1/identity/organizations/{id}
   {
     "naming_series": {
       "quotation": {
         "current_number": 35
       }
     }
   }
   ↓
5. Return quotation response
```

## Key Features

✅ **Non-blocking**: Document creation succeeds even if update fails
✅ **Async**: Uses async/await for HTTP calls
✅ **Error-tolerant**: Logs errors but doesn't fail the operation
✅ **Secure**: Uses same JWT token as original request
✅ **Multi-tenant**: Organization ID validated on both services
✅ **Tested**: Comprehensive unit tests included

## Usage Example

### Backend (Already Implemented for Quotations)

```python
# POST /api/v1/quotations
{
  "customer_id": "uuid",
  "quotation_date": "2025-02-22",
  "items": [...]
}

# Response
{
  "id": "uuid",
  "quotation_no": "QT-0035",  # ← Created
  ...
}

# Automatically updates Identity Service:
# naming_series.quotation.current_number = 35
```

### Frontend Integration

```typescript
// Fetch next quotation number
const response = await axios.get(`/api/v1/identity/organizations/${orgId}`);

const namingSeries = response.data.naming_series.quotation;
const nextNumber = namingSeries.current_number + 1;

// Display: QT-0036
const nextQuotationNo = `${namingSeries.prefix}${String(nextNumber).padStart(4, "0")}`;
```

## Extending to Other Documents

To add this feature to sales orders, invoices, etc., follow the quick guide in `NAMING_SERIES_IMPLEMENTATION_GUIDE.md`.

**Basic steps:**

1. Add imports to your endpoint file
2. Add `request: Request` parameter
3. Copy the naming series update block
4. Change document type and field name
5. Test!

## Testing

### Run Unit Tests

```bash
cd core-service
python3 test_naming_series_standalone.py
```

### Test Integration

```bash
# 1. Create quotation
curl -X POST http://localhost:8001/api/v1/quotations \
  -H "Authorization: Bearer {token}" \
  -d '{ ... }'

# 2. Verify naming series updated
curl http://localhost:8000/api/v1/identity/organizations/{org_id} \
  -H "Authorization: Bearer {token}"
```

## Configuration

No additional configuration required! Uses existing environment variables:

```env
IDENTITY_SERVICE_URL=http://identity-service:8000
```

## Dependencies

Already included in `requirements.txt`:

- `httpx==0.25.2` - Async HTTP client

## Error Handling

All errors are logged but don't affect document creation:

```python
logger.error(f"Failed to update naming series: {e}")
```

Check logs:

```bash
docker compose logs core-service | grep "naming series"
```

## Performance Impact

- **Minimal**: Async operation doesn't block document creation
- **Fast**: 10-second timeout prevents hanging
- **Resilient**: Failures don't affect core functionality

## Security

- ✅ Uses same authentication as original request
- ✅ Organization ID validated on both services
- ✅ No additional credentials required
- ✅ Follows existing security patterns

## Next Steps

### Immediate

1. ✅ Implemented for quotations
2. ⏳ Implement for sales orders
3. ⏳ Implement for invoices
4. ⏳ Implement for purchase orders

### Future Enhancements

- Batch updates for multiple document types
- Retry logic with exponential backoff
- Event-driven updates using message queue
- Real-time notifications to frontend

## Documentation

- **Technical Details**: `core-service/NAMING_SERIES_AUTO_UPDATE.md`
- **Implementation Guide**: `core-service/NAMING_SERIES_IMPLEMENTATION_GUIDE.md`
- **API Documentation**: http://localhost:8001/docs

## Support

For questions or issues:

1. Check the documentation files
2. Review the test files for examples
3. Check logs for error messages
4. Verify Identity Service is running

## Conclusion

This implementation provides a robust, scalable solution for keeping document numbering synchronized across services. The non-blocking, error-tolerant design ensures that document creation always succeeds, while the automatic updates keep the frontend in sync with the latest document numbers.

**Status**: ✅ Ready for production use
**Tested**: ✅ Unit tests passing
**Documented**: ✅ Comprehensive documentation provided
