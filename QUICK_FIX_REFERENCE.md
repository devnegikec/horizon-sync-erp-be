# Quick Fix Reference - Quotation Auto-Number

## Problem

❌ **400 Bad Request** when creating quotations

## Root Cause

Frontend was required to provide `quotation_no` but didn't know what number to use

## Solution

✅ System now **auto-generates** quotation numbers

## What Changed

### Backend (✅ Done)

- `quotation_no` is now **optional** in create request
- System generates format: `QT-2026-0001`
- Automatically updates naming series in Identity Service

### Frontend (⏳ Action Required)

Remove `quotation_no` from your create quotation request

## Frontend Fix

### Before (❌ Causes 400 Error)

```typescript
const data = {
  quotation_no: "QT-0001",  // ❌ Remove this
  customer_id: "uuid",
  quotation_date: "2026-02-25T00:00:00.000Z",
  items: [...]
};
```

### After (✅ Works)

```typescript
const data = {
  // quotation_no removed - auto-generated!
  customer_id: "uuid",
  quotation_date: "2026-02-25T00:00:00.000Z",
  valid_until: "2026-05-09T00:00:00.000Z",
  status: "draft",
  currency: "INR",
  remarks: "test",
  items: [
    {
      item_id: "uuid",
      qty: 20,
      uom: "Bottle",
      rate: 18,
      amount: 360,
      sort_order: 1,
      tax_template_id: "uuid",
      tax_rate: 5,
      tax_amount: 18,
      total_amount: 378,
    },
  ],
};
```

## Test Command

```bash
curl -X POST http://localhost:8001/api/v1/quotations \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "08d25496-002c-4edb-b033-a76a9acfa674",
    "quotation_date": "2026-02-25T00:00:00.000Z",
    "valid_until": "2026-05-09T00:00:00.000Z",
    "status": "draft",
    "currency": "INR",
    "remarks": "test",
    "items": [{
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
    }]
  }'
```

## Expected Response

```json
{
  "id": "uuid",
  "quotation_no": "QT-2026-0001",  // ← Auto-generated!
  "customer_id": "08d25496-002c-4edb-b033-a76a9acfa674",
  "quotation_date": "2026-02-25T00:00:00.000Z",
  "status": "draft",
  "grand_total": 378,
  "currency": "INR",
  "items": [...]
}
```

## Quotation Number Format

- **Format:** `QT-YYYY-NNNN`
- **Example:** `QT-2026-0001`, `QT-2026-0042`
- **Resets:** Every year (QT-2027-0001)

## Naming Series Update

After creating quotation `QT-2026-0042`:

- System extracts number: `42`
- Updates Identity Service: `naming_series.quotation.current_number = 42`
- Frontend can fetch next number: `43` → Display as `QT-2026-0043`

## Quick Checklist

- [ ] Remove `quotation_no` from frontend create request
- [ ] Test API with curl command above
- [ ] Verify quotation is created with auto-generated number
- [ ] Check naming series is updated in organization settings
- [ ] Update TypeScript interfaces to make `quotation_no` optional

## Documentation

- **Full Guide:** `core-service/QUOTATION_AUTO_NUMBER_GENERATION.md`
- **Fix Summary:** `QUOTATION_AUTO_NUMBER_FIX_SUMMARY.md`
- **Naming Series:** `core-service/NAMING_SERIES_AUTO_UPDATE.md`

## Status

✅ **Backend:** Ready
⏳ **Frontend:** Remove `quotation_no` from request
🧪 **Testing:** Use curl command above
