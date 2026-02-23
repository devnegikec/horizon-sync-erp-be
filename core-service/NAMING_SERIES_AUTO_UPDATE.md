# Naming Series Auto-Update Feature

## Overview

This feature automatically updates the organization's naming series `current_number` in the Identity Service whenever a new document (quotation, sales order, invoice, etc.) is created in the Core Service.

## Problem Statement

When creating documents like quotations, the frontend needs to know the latest document number to display to users. Previously, the naming series counter in the organization settings was not automatically updated when documents were created, leading to:

- Stale document numbers shown in the frontend
- Manual updates required to keep naming series in sync
- Potential confusion about the next available document number

## Solution

Automatically update the organization's `naming_series.{document_type}.current_number` in the Identity Service after successfully creating a document in the Core Service.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Application                      │
│  - Displays next quotation number (QT-0036)                 │
│  - Fetches from organization settings                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Identity Service (Port 8000)              │
│  - Stores organization settings                             │
│  - naming_series.quotation.current_number = 35              │
│  - PATCH /api/v1/identity/organizations/{id}                │
└─────────────────────────────────────────────────────────────┘
                              ▲
                              │ (Update naming series)
                              │
┌─────────────────────────────────────────────────────────────┐
│                    Core Service (Port 8001)                  │
│  1. POST /api/v1/quotations                                 │
│  2. Create quotation (QT-0035)                              │
│  3. Extract number from quotation_no (35)                   │
│  4. Call Identity Service to update current_number          │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Details

### 1. Organization Client (`app/services/organization_client.py`)

A new service client that communicates with the Identity Service to update organization settings.

**Key Methods:**

- `update_naming_series()`: Updates the naming series for a specific document type
- `get_organization_settings()`: Retrieves organization settings (for debugging/verification)

**Features:**

- Async HTTP client using `httpx`
- Proper error handling and logging
- Timeout configuration (10 seconds)
- Non-blocking operation (doesn't fail document creation if update fails)

### 2. Naming Series Utilities (`app/utils/naming_series.py`)

Utility functions for parsing and validating document numbers.

**Functions:**

#### `extract_number_from_document_no(document_no: str) -> Optional[int]`

Extracts the numeric sequence from a document number.

Examples:

- `"QT-0035"` → `35`
- `"SO-2025-0042"` → `42`
- `"INV-0123"` → `123`

#### `get_document_type_from_prefix(prefix: str) -> Optional[str]`

Maps document prefix to document type for naming series.

Examples:

- `"QT"` → `"quotation"`
- `"SO"` → `"sales_order"`
- `"INV"` → `"invoice"`

#### `should_update_naming_series(document_no: str) -> bool`

Validates if a document number follows the expected pattern.

Pattern: `PREFIX-[OPTIONAL_YEAR-]NUMBER`

- Valid: `QT-0035`, `SO-2025-0042`, `INV-0123`
- Invalid: `QUOTE`, `qt-0035`, `0035`

### 3. Updated Quotation Endpoint (`app/api/v1/endpoints/quotations.py`)

The `create_quotation` endpoint now:

1. Creates the quotation (existing logic)
2. Extracts the document number from `quotation_no`
3. Calls `organization_client.update_naming_series()` asynchronously
4. Logs errors but doesn't fail if the update fails

**Key Points:**

- Non-blocking: Document creation succeeds even if naming series update fails
- Async operation: Uses `await` for HTTP call to Identity Service
- Error handling: Logs errors for debugging but doesn't raise exceptions
- Auth token: Extracts from request headers and passes to Identity Service

## API Flow

### Creating a Quotation

**Request:**

```http
POST /api/v1/quotations
Authorization: Bearer {token}
Content-Type: application/json

{
  "customer_id": "uuid",
  "quotation_date": "2025-02-22",
  "items": [...]
}
```

**Core Service Processing:**

1. Validates request
2. Creates quotation with auto-generated number (e.g., `QT-0035`)
3. Extracts number: `35`
4. Calls Identity Service:

```http
PATCH /api/v1/identity/organizations/{org_id}
Authorization: Bearer {token}
Content-Type: application/json

{
  "naming_series": {
    "quotation": {
      "current_number": 35
    }
  }
}
```

**Response:**

```json
{
  "id": "uuid",
  "quotation_no": "QT-0035",
  "customer_id": "uuid",
  ...
}
```

## Configuration

### Environment Variables

The Identity Service URL is configured in `.env`:

```env
IDENTITY_SERVICE_URL=http://identity-service:8000
```

For local development:

```env
IDENTITY_SERVICE_URL=http://localhost:8000
```

### Dependencies

The feature requires `httpx` for async HTTP requests:

```txt
httpx==0.25.2
```

Already included in `core-service/requirements.txt`.

## Error Handling

### Scenarios

1. **Identity Service Unavailable**

   - Error logged: "Request error while updating naming series"
   - Quotation creation: ✅ Succeeds
   - Naming series update: ❌ Fails silently

2. **Timeout (>10 seconds)**

   - Error logged: "Timeout while updating naming series"
   - Quotation creation: ✅ Succeeds
   - Naming series update: ❌ Fails silently

3. **Invalid Auth Token**

   - Error logged: "Failed to update naming series: 401"
   - Quotation creation: ✅ Succeeds
   - Naming series update: ❌ Fails silently

4. **Invalid Document Number Format**
   - No update attempted
   - Quotation creation: ✅ Succeeds

### Logging

All errors are logged with context:

```python
logger.error(
    f"Failed to update naming series for quotation {data['quotation_no']}: {e}"
)
```

Check logs:

```bash
docker compose logs core-service | grep "naming series"
```

## Testing

### Unit Tests

Run the standalone test:

```bash
cd core-service
python3 test_naming_series_standalone.py
```

### Integration Testing

1. **Create a quotation:**

```bash
curl -X POST http://localhost:8001/api/v1/quotations \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "uuid",
    "quotation_date": "2025-02-22",
    "items": [...]
  }'
```

2. **Verify naming series updated:**

```bash
curl http://localhost:8000/api/v1/identity/organizations/{org_id} \
  -H "Authorization: Bearer {token}"
```

Expected response:

```json
{
  "id": "uuid",
  "naming_series": {
    "quotation": {
      "prefix": "QT-",
      "padding": 4,
      "separator": "-",
      "current_number": 35 // ← Updated!
    }
  }
}
```

## Extending to Other Document Types

To add auto-update for other document types (sales orders, invoices, etc.):

### 1. Update the endpoint

```python
# app/api/v1/endpoints/sales_orders.py

@router.post("", response_model=SalesOrderResponse)
async def create_sales_order(
    body: SalesOrderCreate,
    request: Request,  # Add this
    current_user: CurrentUser = Depends(require_permission(SALES_ORDER_CREATE)),
    db: Session = Depends(get_db),
):
    svc = SalesOrderService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)

    # Add naming series update
    if data.get("sales_order_no"):
        current_number = extract_number_from_document_no(data["sales_order_no"])

        if current_number is not None:
            auth_header = request.headers.get("Authorization", "")

            try:
                await organization_client.update_naming_series(
                    organization_id=current_user.organization_id,
                    document_type="sales_order",  # ← Change this
                    current_number=current_number,
                    auth_token=auth_header.replace("Bearer ", ""),
                )
            except Exception as e:
                logger.error(f"Failed to update naming series: {e}")

    return SalesOrderResponse.model_validate(data)
```

### 2. Add imports

```python
from app.services.organization_client import organization_client
from app.utils.naming_series import extract_number_from_document_no
```

### 3. Update prefix mapping (if needed)

If the document uses a new prefix, add it to `app/utils/naming_series.py`:

```python
prefix_map = {
    "QT": "quotation",
    "SO": "sales_order",
    "INV": "invoice",
    "NEW": "new_document_type",  # ← Add new prefix
    # ...
}
```

## Frontend Integration

### Fetching Next Document Number

```typescript
// services/organizationService.ts

async getNextQuotationNumber(organizationId: string): Promise<string> {
  const response = await axios.get(
    `${API_BASE_URL}/api/v1/identity/organizations/${organizationId}`,
    { headers: this.getHeaders() }
  );

  const namingSeries = response.data.naming_series.quotation;
  const nextNumber = namingSeries.current_number + 1;

  // Format: QT-0036
  return `${namingSeries.prefix}${String(nextNumber).padStart(namingSeries.padding, '0')}`;
}
```

### Displaying in UI

```typescript
// components/QuotationForm.tsx

const [nextQuotationNo, setNextQuotationNo] = useState("");

useEffect(() => {
  const fetchNextNumber = async () => {
    const number = await organizationService.getNextQuotationNumber(orgId);
    setNextQuotationNo(number);
  };

  fetchNextNumber();
}, [orgId]);

return (
  <div>
    <label>Next Quotation Number:</label>
    <input value={nextQuotationNo} disabled />
  </div>
);
```

## Troubleshooting

### Issue: Naming series not updating

**Check:**

1. Identity Service is running: `curl http://localhost:8000/health`
2. Core Service logs: `docker compose logs core-service | grep "naming series"`
3. Auth token is valid
4. Organization ID is correct

### Issue: Document number format not recognized

**Check:**

1. Document number matches pattern: `PREFIX-[YEAR-]NUMBER`
2. Prefix is uppercase
3. Number is numeric

**Debug:**

```python
from app.utils.naming_series import extract_number_from_document_no

number = extract_number_from_document_no("QT-0035")
print(f"Extracted: {number}")  # Should print: 35
```

### Issue: Frontend shows stale numbers

**Solutions:**

1. Refresh organization settings after creating document
2. Add cache invalidation
3. Use WebSocket/SSE for real-time updates

## Performance Considerations

- **Async Operation**: HTTP call doesn't block document creation
- **Timeout**: 10-second timeout prevents hanging
- **Error Handling**: Failures don't affect document creation
- **Logging**: Minimal overhead, only on errors

## Security

- **Authentication**: Uses same JWT token as the original request
- **Authorization**: Identity Service validates permissions
- **Multi-tenancy**: Organization ID is validated on both services

## Future Enhancements

1. **Batch Updates**: Update multiple document types in one call
2. **Retry Logic**: Retry failed updates with exponential backoff
3. **Event-Driven**: Use message queue (Redis/RabbitMQ) for async updates
4. **Caching**: Cache organization settings to reduce API calls
5. **Webhooks**: Notify frontend of naming series changes

## Related Files

- `core-service/app/services/organization_client.py` - HTTP client for Identity Service
- `core-service/app/utils/naming_series.py` - Utility functions
- `core-service/app/api/v1/endpoints/quotations.py` - Updated endpoint
- `core-service/tests/test_naming_series.py` - Unit tests
- `core-service/test_naming_series_standalone.py` - Standalone tests

## References

- Identity Service API: http://localhost:8000/docs
- Core Service API: http://localhost:8001/docs
- Organization Settings Schema: See `test.json` for example structure
