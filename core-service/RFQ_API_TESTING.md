# RFQ API - Postman Testing Guide

This guide will help you test the RFQ (Request for Quotation) API using the provided Postman collection.

## Files Included

1. **RFQ_API.postman_collection.json** - Complete API collection with 15 test requests
2. **RFQ_API_TESTING.md** - This guide

## Prerequisites

1. **Postman** installed (Desktop or Web version)
2. **Core Service** running on `http://localhost:8001`
3. **Valid JWT token** from the identity service
4. **Material Request created** (use Material Request API first)
5. **Suppliers created** in the database (or update the supplier IDs in the environment)

## Setup Instructions

### Step 1: Import Collection

1. Open Postman
2. Click **Import** button
3. Import the file: `RFQ_API.postman_collection.json`

### Step 2: Configure Environment Variables

1. Select or create an environment in Postman
2. Add/update the following variables:

#### Required Variables:
- **access_token**: Your JWT token from identity service
  ```
  Get this by logging in through the identity service
  ```

- **material_request_id**: ID of a submitted Material Request
  ```
  Create a Material Request first using the Material Request API
  Then submit it before creating an RFQ
  ```

#### Supplier IDs (Update with Real IDs from Your Database):

Run this SQL query to get real supplier IDs from your database:

```sql
SELECT id, supplier_name, supplier_code 
FROM suppliers 
WHERE organization_id = 'YOUR_ORG_ID' 
AND status = 'active'
LIMIT 3;
```

Then update these environment variables with real UUIDs:
- **supplier_id_1**: First supplier ID
- **supplier_id_2**: Second supplier ID
- **supplier_id_3**: Third supplier ID

#### Optional Variables:
- **base_url**: Default is `http://localhost:8001` (change if needed)

### Step 3: Create Sample Suppliers (if needed)

You can use this SQL script to create sample suppliers if needed:

```sql
-- Insert sample suppliers for testing
INSERT INTO suppliers (id, organization_id, supplier_name, supplier_code, status, created_at, updated_at)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'YOUR_ORG_ID', 'ABC Manufacturing Co.', 'SUP-001', 'active', NOW(), NOW()),
  ('22222222-2222-2222-2222-222222222222', 'YOUR_ORG_ID', 'XYZ Industrial Supplies', 'SUP-002', 'active', NOW(), NOW()),
  ('33333333-3333-3333-3333-333333333333', 'YOUR_ORG_ID', 'Global Parts Distributor', 'SUP-003', 'active', NOW(), NOW());
```

## Test Scenarios Included

### 1. Basic CRUD Operations

#### Request 1: Create RFQ from Material Request
- Creates an RFQ from an existing Material Request
- Copies all line items from the Material Request
- Associates multiple suppliers
- Saves the RFQ ID and line IDs to environment
- **Expected**: 201 Created

#### Request 2: Get RFQ by ID
- Retrieves the created RFQ
- Shows all line items, suppliers, and quotes
- **Expected**: 200 OK with full details

#### Request 3: List All RFQs
- Paginated list with sorting
- **Expected**: 200 OK with array of RFQs

#### Request 4: Filter by Status (DRAFT)
- Lists only DRAFT RFQs
- **Expected**: 200 OK with filtered results

#### Request 5: Update RFQ (DRAFT only)
- Updates closing date
- **Expected**: 200 OK (only works for DRAFT status)

#### Request 13: Delete RFQ (DRAFT only)
- Deletes an RFQ
- **Expected**: 204 No Content (only works for DRAFT status)

### 2. Status Transitions

#### Request 6: Send RFQ to Suppliers
- Changes status from DRAFT to SENT
- **Expected**: 200 OK with status = "sent"

#### Request 12: Close RFQ
- Changes status to CLOSED
- **Expected**: 200 OK with status = "closed"

### 3. Supplier Quote Recording

#### Request 7: Record Supplier Quote - Supplier 1, Line 1
- Records first supplier's quote
- **Expected**: 200 OK with quote added

#### Request 8: Record Supplier Quote - Supplier 2, Line 1
- Records second supplier's quote
- **Expected**: 200 OK with quote added

#### Request 9: Record Supplier Quote - Supplier 3, Line 1
- Records third supplier's quote
- **Expected**: 200 OK with quote added

#### Request 10: Get RFQ with Quotes
- Retrieves RFQ to see all recorded quotes
- Compare prices and delivery dates
- **Expected**: 200 OK with all quotes visible

### 4. List and Filter Operations

#### Request 11: Filter by Status (SENT)
- Lists only SENT RFQs
- **Expected**: 200 OK with filtered results

### 5. Error Handling Tests

#### Request 14: Invalid Material Request ID
- Tests validation for non-existent Material Request
- **Expected**: 404 Not Found

#### Request 15: Update Sent RFQ
- Tests business rule: cannot update sent RFQs
- **Expected**: 409 Conflict

## Recommended Testing Flow

### Flow 1: Complete RFQ Workflow
1. **Create** Material Request (use Material Request API)
2. **Submit** Material Request (use Material Request API)
3. **Create** RFQ from Material Request (Request 1)
4. **Get** RFQ by ID (Request 2)
5. **Send** RFQ to suppliers (Request 6)
6. **Record** quotes from all suppliers (Requests 7, 8, 9)
7. **Get** RFQ with quotes (Request 10)
8. **Close** RFQ (Request 12)

### Flow 2: Update and Delete
1. **Create** RFQ from Material Request (Request 1)
2. **Update** closing date (Request 5)
3. **Get** RFQ to verify update (Request 2)
4. **Delete** RFQ (Request 13)

### Flow 3: Error Testing
1. **Test** invalid Material Request ID (Request 14)
2. **Create** and **Send** an RFQ
3. **Try to Update** sent RFQ (Request 15) - should fail

### Flow 4: List and Filter
1. **Create** multiple RFQs (Request 1)
2. **List** all RFQs (Request 3)
3. **Filter** by DRAFT status (Request 4)
4. **Send** one RFQ (Request 6)
5. **Filter** by SENT status (Request 11)

## Response Examples

### Successful RFQ Creation (201 Created)
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "organization_id": "org-uuid-here",
  "material_request_id": "mr-uuid-here",
  "reference_type": "MATERIAL_REQUEST",
  "reference_id": "mr-uuid-here",
  "status": "draft",
  "closing_date": "2024-03-30",
  "created_by": "user-uuid-here",
  "updated_by": null,
  "created_at": "2024-02-15T10:30:00Z",
  "updated_at": "2024-02-15T10:30:00Z",
  "line_items": [
    {
      "id": "line-uuid-1",
      "organization_id": "org-uuid-here",
      "rfq_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "item_id": "item-uuid-1",
      "quantity": 50,
      "required_date": "2024-03-15",
      "description": "Ergonomic office chairs",
      "created_at": "2024-02-15T10:30:00Z",
      "updated_at": "2024-02-15T10:30:00Z",
      "quotes": []
    }
  ],
  "suppliers": [
    {
      "id": "rfq-supplier-uuid-1",
      "organization_id": "org-uuid-here",
      "rfq_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "supplier_id": "supplier-uuid-1",
      "created_at": "2024-02-15T10:30:00Z"
    }
  ]
}
```

### RFQ with Quotes (200 OK)
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "sent",
  "line_items": [
    {
      "id": "line-uuid-1",
      "item_id": "item-uuid-1",
      "quantity": 50,
      "quotes": [
        {
          "id": "quote-uuid-1",
          "supplier_id": "supplier-uuid-1",
          "quoted_price": 125.50,
          "quoted_delivery_date": "2024-03-20",
          "supplier_notes": "Best quality materials"
        },
        {
          "id": "quote-uuid-2",
          "supplier_id": "supplier-uuid-2",
          "quoted_price": 118.75,
          "quoted_delivery_date": "2024-03-25",
          "supplier_notes": "Competitive pricing"
        }
      ]
    }
  ]
}
```

### Validation Error (400 Bad Request)
```json
{
  "detail": {
    "message": "Invalid input data",
    "status_code": 400,
    "code": "VALIDATION_ERROR"
  }
}
```

### Not Found Error (404 Not Found)
```json
{
  "detail": {
    "message": "Material Request not found",
    "status_code": 404,
    "code": "MATERIAL_REQUEST_NOT_FOUND"
  }
}
```

### State Conflict Error (409 Conflict)
```json
{
  "detail": {
    "message": "Cannot update RFQ in SENT status",
    "status_code": 409,
    "code": "STATE_CONFLICT"
  }
}
```

## Troubleshooting

### Issue: 401 Unauthorized
**Solution**: Update the `access_token` in the environment with a valid JWT token

### Issue: 404 Not Found (Material Request not found)
**Solution**: 
1. Create a Material Request first using the Material Request API
2. Submit the Material Request (status must be SUBMITTED)
3. Update the `material_request_id` variable with the created ID

### Issue: 404 Not Found (Supplier not found)
**Solution**: Update the `supplier_id_X` variables with real supplier IDs from your database

### Issue: 403 Forbidden
**Solution**: Ensure your user has the required permissions:
- `rfq.create`
- `rfq.read`
- `rfq.update`

### Issue: 409 Conflict (Cannot update)
**Solution**: You can only update RFQs in DRAFT status. Once sent, they cannot be modified.

### Issue: Connection Refused
**Solution**: Ensure the core-service is running on `http://localhost:8001`

## API Endpoints Summary

| Method | Endpoint | Description | Status Requirement |
|--------|----------|-------------|-------------------|
| POST | `/api/v1/rfqs` | Create RFQ from Material Request | Material Request must be SUBMITTED |
| GET | `/api/v1/rfqs` | List RFQs | - |
| GET | `/api/v1/rfqs/{id}` | Get RFQ | - |
| PUT | `/api/v1/rfqs/{id}` | Update RFQ | DRAFT only |
| DELETE | `/api/v1/rfqs/{id}` | Delete RFQ | DRAFT only |
| POST | `/api/v1/rfqs/{id}/send` | Send RFQ to suppliers | DRAFT → SENT |
| POST | `/api/v1/rfqs/{id}/quotes` | Record supplier quote | SENT or PARTIALLY_RESPONDED |
| POST | `/api/v1/rfqs/{id}/close` | Close RFQ | Any → CLOSED |

## Status Flow

```
DRAFT → SENT → PARTIALLY_RESPONDED → FULLY_RESPONDED → CLOSED
  ↓
CLOSED (can close from any status)
```

- **DRAFT**: Initial state, can be edited/deleted
- **SENT**: Sent to suppliers, cannot be edited
- **PARTIALLY_RESPONDED**: Some suppliers have provided quotes
- **FULLY_RESPONDED**: All suppliers have provided quotes for all line items
- **CLOSED**: RFQ closed, no further quotes accepted

## Quote Comparison

After recording quotes from multiple suppliers, you can compare:
- **Quoted Price**: Which supplier offers the best price?
- **Delivery Date**: Which supplier can deliver fastest?
- **Supplier Notes**: Any special terms or conditions?

Use Request 10 to retrieve the RFQ with all quotes and make informed procurement decisions.

## Next Steps

After testing RFQs, you can:
1. Create Purchase Orders from selected RFQ quotes
2. Track Purchase Order status
3. Record goods receipt
4. Process supplier invoices
5. Make payments to suppliers

## Support

For issues or questions:
1. Check the API logs in the core-service
2. Verify database connectivity
3. Ensure all migrations are applied
4. Check the design document: `.kiro/specs/sourcing-flow/design.md`
5. Review the requirements: `.kiro/specs/sourcing-flow/requirements.md`
