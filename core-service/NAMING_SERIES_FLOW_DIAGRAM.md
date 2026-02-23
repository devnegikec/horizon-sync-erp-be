# Naming Series Auto-Update Flow Diagram

## Complete Flow Visualization

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND APPLICATION                         │
│                                                                      │
│  1. User clicks "Create Quotation"                                  │
│  2. Shows next number: QT-0036 (from org settings)                  │
│  3. Submits form                                                     │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   │ POST /api/v1/quotations
                                   │ Authorization: Bearer {token}
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CORE SERVICE (Port 8001)                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ quotations.py: create_quotation()                          │    │
│  │                                                             │    │
│  │ 1. Validate request                                        │    │
│  │ 2. Call QuotationService.create()                          │    │
│  │    ├─ Generate quotation_no: "QT-0035"                     │    │
│  │    ├─ Save to database                                     │    │
│  │    └─ Return quotation data                                │    │
│  │                                                             │    │
│  │ 3. Extract number from quotation_no                        │    │
│  │    extract_number_from_document_no("QT-0035") → 35         │    │
│  │                                                             │    │
│  │ 4. Update naming series (async)                            │    │
│  │    ┌─────────────────────────────────────────────┐        │    │
│  │    │ organization_client.update_naming_series()  │        │    │
│  │    │                                              │        │    │
│  │    │ - organization_id: UUID                     │        │    │
│  │    │ - document_type: "quotation"                │        │    │
│  │    │ - current_number: 35                        │        │    │
│  │    │ - auth_token: {token}                       │        │    │
│  │    └─────────────────────────────────────────────┘        │    │
│  │                                                             │    │
│  │ 5. Return quotation response                               │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                   │                                 │
└───────────────────────────────────┼─────────────────────────────────┘
                                    │
                                    │ PATCH /api/v1/identity/organizations/{id}
                                    │ Authorization: Bearer {token}
                                    │ {
                                    │   "naming_series": {
                                    │     "quotation": {
                                    │       "current_number": 35
                                    │     }
                                    │   }
                                    │ }
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   IDENTITY SERVICE (Port 8000)                       │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ organizations.py: update_organization()                    │    │
│  │                                                             │    │
│  │ 1. Validate auth token                                     │    │
│  │ 2. Validate organization_id                                │    │
│  │ 3. Update organization.settings.naming_series              │    │
│  │    {                                                        │    │
│  │      "quotation": {                                         │    │
│  │        "prefix": "QT-",                                     │    │
│  │        "padding": 4,                                        │    │
│  │        "separator": "-",                                    │    │
│  │        "current_number": 35  ← UPDATED!                    │    │
│  │      }                                                       │    │
│  │    }                                                        │    │
│  │ 4. Save to database                                        │    │
│  │ 5. Return 200 OK                                           │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                   │                                 │
└───────────────────────────────────┼─────────────────────────────────┘
                                    │
                                    │ 200 OK
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    CORE SERVICE (Port 8001)                          │
│                                                                      │
│  ✅ Naming series update successful                                 │
│  ✅ Return quotation response to frontend                           │
│                                                                      │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   │ 201 Created
                                   │ {
                                   │   "id": "uuid",
                                   │   "quotation_no": "QT-0035",
                                   │   ...
                                   │ }
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND APPLICATION                         │
│                                                                      │
│  ✅ Quotation created: QT-0035                                      │
│  ✅ Next quotation will be: QT-0036                                 │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CORE SERVICE (Port 8001)                          │
│                                                                      │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │ quotations.py: create_quotation()                          │    │
│  │                                                             │    │
│  │ 1. Create quotation: QT-0035 ✅                            │    │
│  │                                                             │    │
│  │ 2. Try to update naming series                             │    │
│  │    ┌─────────────────────────────────────────────┐        │    │
│  │    │ organization_client.update_naming_series()  │        │    │
│  │    │                                              │        │    │
│  │    │ ❌ Error: Identity Service unavailable      │        │    │
│  │    │ ❌ Error: Timeout (>10 seconds)             │        │    │
│  │    │ ❌ Error: Invalid auth token                │        │    │
│  │    └─────────────────────────────────────────────┘        │    │
│  │                                                             │    │
│  │ 3. Log error (non-blocking)                                │    │
│  │    logger.error("Failed to update naming series")          │    │
│  │                                                             │    │
│  │ 4. ✅ Still return quotation response                      │    │
│  │    (Document creation succeeded!)                          │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘

Result:
✅ Quotation created successfully
❌ Naming series not updated (logged for debugging)
⚠️  Frontend may show stale number temporarily
```

## Sequence Diagram

```
Frontend          Core Service       Identity Service
   │                   │                     │
   │  POST /quotations │                     │
   ├──────────────────>│                     │
   │                   │                     │
   │                   │ Create quotation    │
   │                   │ (QT-0035)           │
   │                   │                     │
   │                   │ Extract number (35) │
   │                   │                     │
   │                   │ PATCH /organizations│
   │                   ├────────────────────>│
   │                   │                     │
   │                   │                     │ Update naming_series
   │                   │                     │ current_number = 35
   │                   │                     │
   │                   │      200 OK         │
   │                   │<────────────────────┤
   │                   │                     │
   │  201 Created      │                     │
   │  (QT-0035)        │                     │
   │<──────────────────┤                     │
   │                   │                     │
   │  GET /organizations                     │
   ├────────────────────────────────────────>│
   │                                         │
   │  200 OK (current_number: 35)            │
   │<────────────────────────────────────────┤
   │                                         │
   │  Display: Next = QT-0036                │
   │                                         │
```

## Component Interaction

```
┌──────────────────────────────────────────────────────────────┐
│                     Core Service                              │
│                                                               │
│  ┌─────────────────┐         ┌──────────────────────┐       │
│  │   Quotation     │         │  Organization        │       │
│  │   Endpoint      │────────>│  Client              │       │
│  │                 │         │  (HTTP Client)       │       │
│  └─────────────────┘         └──────────────────────┘       │
│          │                              │                    │
│          │                              │                    │
│          ▼                              │                    │
│  ┌─────────────────┐                   │                    │
│  │   Naming        │                   │                    │
│  │   Series Utils  │                   │                    │
│  │                 │                   │                    │
│  │ - extract_number│                   │                    │
│  │ - get_doc_type  │                   │                    │
│  └─────────────────┘                   │                    │
│                                         │                    │
└─────────────────────────────────────────┼────────────────────┘
                                          │
                                          │ HTTP PATCH
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────┐
│                   Identity Service                            │
│                                                               │
│  ┌─────────────────┐         ┌──────────────────────┐       │
│  │  Organization   │         │   Organization       │       │
│  │  Endpoint       │────────>│   Repository         │       │
│  │                 │         │                      │       │
│  └─────────────────┘         └──────────────────────┘       │
│                                         │                    │
│                                         ▼                    │
│                              ┌──────────────────────┐       │
│                              │   PostgreSQL         │       │
│                              │   (identity_db)      │       │
│                              │                      │       │
│                              │ organizations table  │       │
│                              │ - settings (JSONB)   │       │
│                              └──────────────────────┘       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

## Data Flow

```
Input: Create Quotation Request
│
├─> Core Service
│   │
│   ├─> QuotationService.create()
│   │   │
│   │   ├─> Generate quotation_no: "QT-0035"
│   │   │
│   │   └─> Save to core_db.quotations
│   │
│   ├─> extract_number_from_document_no("QT-0035")
│   │   │
│   │   └─> Returns: 35
│   │
│   └─> organization_client.update_naming_series()
│       │
│       └─> HTTP PATCH to Identity Service
│
├─> Identity Service
│   │
│   ├─> Validate auth & organization_id
│   │
│   ├─> Update identity_db.organizations
│   │   │
│   │   └─> settings.naming_series.quotation.current_number = 35
│   │
│   └─> Return 200 OK
│
└─> Output: Quotation Response + Updated Naming Series
```

## Key Points

1. **Non-blocking**: Naming series update happens asynchronously
2. **Error-tolerant**: Document creation succeeds even if update fails
3. **Secure**: Uses same JWT token for authentication
4. **Fast**: 10-second timeout prevents hanging
5. **Logged**: All errors are logged for debugging

## Timing

```
Total Request Time: ~100-200ms

├─ Quotation Creation: 50-100ms
│  └─ Database insert + validation
│
└─ Naming Series Update: 50-100ms (async)
   ├─ HTTP request to Identity Service: 20-50ms
   ├─ Database update: 20-30ms
   └─ Response: 10-20ms
```

## Success Criteria

✅ Quotation created in core_db
✅ Naming series updated in identity_db
✅ Frontend receives quotation response
✅ Next quotation shows correct number
