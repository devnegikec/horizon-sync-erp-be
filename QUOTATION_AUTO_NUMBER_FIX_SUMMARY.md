# Quotation Auto-Number Generation - Fix Summary

## Issue

Frontend was getting **400 Bad Request** when creating quotations because:

1. The API required `quotation_no` in the request
2. Frontend didn't know what number to use
3. Manual number generation was error-prone

## Solution

Made `quotation_no` **auto-generated** by the system, similar to Material Requests.

## Changes Made

### 1. Schema Update

**File:** `core-service/app/schemas/quotation.py`

- Made `quotation_no` optional in `QuotationCreate` schema
- System auto-generates if not provided
- Can still provide custom number if needed

### 2. Repository Update

**File:** `core-service/app/repositories/quotation_repository.py`

- Added `count_by_year()` method to count quotations per year
- Used for generating sequential numbers

### 3. Service Update

**File:** `core-service/app/services/quotation_service.py`

- Added auto-generation logic in `create()` method
- Format: `QT-YYYY-NNNN` (e.g., `QT-2026-0001`)
- Counter resets each year

### 4. Documentation

**File:** `core-service/QUOTATION_AUTO_NUMBER_GENERATION.md`

- Complete guide for frontend integration
- API usage examples
- Testing instructions

## How It Works Now

### Backend Flow

```
1. Frontend sends request WITHOUT quotation_no
   ↓
2. Backend checks if quotation_no provided
   ↓
3. If not provided:
   - Get current year (2026)
   - Count existing quotations this year (0)
   - Generate: QT-2026-0001
   ↓
4. Create quotation with generated number
   ↓
5. Update naming series in Identity Service
   ↓
6. Return quotation with quotation_no
```

### Frontend Usage

**Before (❌ Error):**

```json
POST /api/v1/quotations
{
  "quotation_no": "???",  // What number to use?
  "customer_id": "uuid",
  "items": [...]
}
```

**After (✅ Works):**

```json
POST /api/v1/quotations
{
  // quotation_no NOT needed - auto-generated!
  "customer_id": "uuid",
  "quotation_date": "2026-02-25T00:00:00.000Z",
  "valid_until": "2026-05-09T00:00:00.000Z",
  "status": "draft",
  "currency": "INR",
  "remarks": "test",
  "items": [
    {
      "item_id": "uuid",
      "qty": 20,
      "uom": "Bottle",
      "rate": 18,
      "amount": 360,
      "sort_order": 1,
      "tax_template_id": "uuid",
      "tax_rate": 5,
      "tax_amount": 18,
      "total_amount": 378
    }
  ]
}
```

**Response:**

```json
{
  "id": "uuid",
  "quotation_no": "QT-2026-0001",  // ← Auto-generated!
  "customer_id": "uuid",
  "status": "draft",
  "grand_total": 378,
  ...
}
```

## Quotation Number Format

**Format:** `QT-YYYY-NNNN`

**Examples:**

- `QT-2026-0001` - First quotation of 2026
- `QT-2026-0042` - 42nd quotation of 2026
- `QT-2027-0001` - First quotation of 2027 (resets each year)

## Frontend Changes Required

### Option 1: Remove quotation_no (Recommended)

```typescript
// Remove quotation_no from your request
const quotationData = {
  // quotation_no: REMOVE THIS LINE
  customer_id: customerId,
  quotation_date: new Date().toISOString(),
  items: [...]
};

await axios.post('/api/v1/quotations', quotationData);
```

### Option 2: Make it Optional

```typescript
// Update your TypeScript interface
interface QuotationCreate {
  quotation_no?: string; // ← Make optional
  customer_id: string;
  quotation_date: string;
  // ...
}
```

## Testing

### Test the Fix

```bash
# 1. Create quotation without quotation_no
curl -X POST http://localhost:8001/api/v1/quotations \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "08d25496-002c-4edb-b033-a76a9acfa674",
    "quotation_date": "2026-02-25T00:00:00.000Z",
    "valid_until": "2026-05-09T00:00:00.000Z",
    "status": "draft",
    "grand_total": 378,
    "currency": "INR",
    "remarks": "test it",
    "items": [
      {
        "item_id": "a17ac10b-58cc-4372-a567-0e02b2c3d008",
        "qty": 20,
        "uom": "Bottle",
        "rate": 18,
        "amount": 360,
        "sort_order": 1,
        "tax_template_id": "896e1d8b-f75b-4e76-952a-2d385ee3bfa7",
        "tax_rate": 5,
        "tax_amount": 18,
        "total_amount": 378
      }
    ]
  }'

# Expected: 201 Created with quotation_no: "QT-2026-0001"
```

### Verify Naming Series Updated

```bash
# Check organization settings
curl http://localhost:8000/api/v1/identity/organizations/{org_id} \
  -H "Authorization: Bearer {token}" \
  | jq '.naming_series.quotation'

# Expected output:
# {
#   "prefix": "QT-",
#   "padding": 4,
#   "separator": "-",
#   "current_number": 1
# }
```

## Benefits

✅ **No More 400 Errors:** Frontend doesn't need to provide quotation_no
✅ **Automatic Numbering:** System generates unique, sequential numbers
✅ **Year-based Reset:** Counter resets each year for better organization
✅ **Consistent Format:** All quotations follow QT-YYYY-NNNN format
✅ **Auto-sync:** Naming series automatically updated in Identity Service
✅ **Backward Compatible:** Can still provide custom numbers if needed

## Files Modified

1. ✅ `core-service/app/schemas/quotation.py` - Made quotation_no optional
2. ✅ `core-service/app/repositories/quotation_repository.py` - Added count_by_year()
3. ✅ `core-service/app/services/quotation_service.py` - Added auto-generation logic
4. ✅ `core-service/QUOTATION_AUTO_NUMBER_GENERATION.md` - Documentation

## Files Already Created (From Previous Implementation)

5. ✅ `core-service/app/services/organization_client.py` - Identity Service client
6. ✅ `core-service/app/utils/naming_series.py` - Number extraction utilities
7. ✅ `core-service/app/api/v1/endpoints/quotations.py` - Naming series update logic

## Deployment Checklist

- [x] Code changes completed
- [x] Compilation successful
- [x] Documentation created
- [ ] Test with Postman/curl
- [ ] Update frontend to remove quotation_no
- [ ] Deploy to staging
- [ ] Test end-to-end
- [ ] Deploy to production

## Rollback Plan

If issues occur:

1. Revert the 3 modified files
2. Frontend must provide quotation_no again
3. Investigate and fix issues
4. Re-deploy

## Next Steps

1. **Test the API** with the provided curl command
2. **Update Frontend** to remove quotation_no from requests
3. **Verify** quotations are created successfully
4. **Check** naming series is updated correctly

## Support

- **Full Documentation:** `core-service/QUOTATION_AUTO_NUMBER_GENERATION.md`
- **Naming Series Guide:** `core-service/NAMING_SERIES_AUTO_UPDATE.md`
- **API Docs:** http://localhost:8001/docs

---

**Status:** ✅ Ready to test
**Impact:** Frontend must remove `quotation_no` from create requests
**Breaking Change:** No (quotation_no is optional, not removed)
