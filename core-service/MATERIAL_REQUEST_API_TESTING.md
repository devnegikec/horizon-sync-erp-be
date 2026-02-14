# Material Request API - Postman Testing Guide

This guide will help you test the Material Request API using the provided Postman collection.

## Files Included

1. **Material_Request_API.postman_collection.json** - Complete API collection with 14 test requests
2. **Material_Request_API.postman_environment.json** - Environment variables and sample data
3. **MATERIAL_REQUEST_API_TESTING.md** - This guide

## Prerequisites

1. **Postman** installed (Desktop or Web version)
2. **Core Service** running on `http://localhost:8001`
3. **Valid JWT token** from the identity service
4. **Items created** in the database (or update the item IDs in the environment)

## Setup Instructions

### Step 1: Import Collection and Environment

1. Open Postman
2. Click **Import** button
3. Import both files:
   - `Material_Request_API.postman_collection.json`
   - `Material_Request_API.postman_environment.json`

### Step 2: Configure Environment Variables

1. Select the **Material Request API - Environment** from the environment dropdown
2. Click the eye icon to view/edit environment variables
3. Update the following variables:

#### Required Variables:
- **access_token**: Your JWT token from identity service
  ```
  Get this by logging in through the identity service
  ```

#### Item IDs (Update with Real IDs from Your Database):

Run this SQL query to get real item IDs from your database:

```sql
SELECT id, item_code, item_name 
FROM items 
WHERE organization_id = 'YOUR_ORG_ID' 
LIMIT 12;
```

Then update these environment variables with real UUIDs:
- **item_id_1** through **item_id_12**: Replace with actual item IDs from your database

#### Optional Variables:
- **base_url**: Default is `http://localhost:8001` (change if needed)

### Step 3: Get Real Item IDs from Database

You can use this SQL script to create sample items if needed:

```sql
-- Insert sample items for testing
INSERT INTO items (id, organization_id, item_code, item_name, item_group_id, uom, is_active, created_at, updated_at)
VALUES 
  ('11111111-1111-1111-1111-111111111111', 'YOUR_ORG_ID', 'CHAIR-001', 'Ergonomic Office Chair', NULL, 'Unit', true, NOW(), NOW()),
  ('22222222-2222-2222-2222-222222222222', 'YOUR_ORG_ID', 'DESK-001', 'Standing Desk Adjustable', NULL, 'Unit', true, NOW(), NOW()),
  ('33333333-3333-3333-3333-333333333333', 'YOUR_ORG_ID', 'KB-MOUSE-001', 'Wireless Keyboard Mouse Combo', NULL, 'Set', true, NOW(), NOW()),
  ('44444444-4444-4444-4444-444444444444', 'YOUR_ORG_ID', 'STEEL-001', 'Cold Rolled Steel Sheet 2mm', NULL, 'Sheet', true, NOW(), NOW()),
  ('55555555-5555-5555-5555-555555555555', 'YOUR_ORG_ID', 'BOLT-001', 'Stainless Steel Bolt M8x20mm', NULL, 'Piece', true, NOW(), NOW()),
  ('66666666-6666-6666-6666-666666666666', 'YOUR_ORG_ID', 'ADHESIVE-001', 'Industrial Adhesive 5L', NULL, 'Container', true, NOW(), NOW()),
  ('77777777-7777-7777-7777-777777777777', 'YOUR_ORG_ID', 'GASKET-001', 'Rubber Gasket 50mm', NULL, 'Piece', true, NOW(), NOW()),
  ('88888888-8888-8888-8888-888888888888', 'YOUR_ORG_ID', 'MONITOR-ARM-001', 'Dual Monitor Arm', NULL, 'Unit', true, NOW(), NOW()),
  ('99999999-9999-9999-9999-999999999999', 'YOUR_ORG_ID', 'LAPTOP-001', 'Dell Latitude 5540 16GB', NULL, 'Unit', true, NOW(), NOW()),
  ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'YOUR_ORG_ID', 'MONITOR-001', '27-inch 4K Monitor', NULL, 'Unit', true, NOW(), NOW()),
  ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'YOUR_ORG_ID', 'DOCK-001', 'USB-C Docking Station', NULL, 'Unit', true, NOW(), NOW()),
  ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'YOUR_ORG_ID', 'HEADSET-001', 'Noise Cancelling Headset', NULL, 'Unit', true, NOW(), NOW());
```

## Test Scenarios Included

### 1. Basic CRUD Operations

#### Request 1: Create Material Request - Office Supplies
- Creates a Material Request with 3 line items
- Saves the Material Request ID to environment
- **Expected**: 201 Created

#### Request 3: Get Material Request by ID
- Retrieves the created Material Request
- **Expected**: 200 OK with full details

#### Request 6: Update Material Request (DRAFT only)
- Updates notes and line items
- Adds a new line item
- **Expected**: 200 OK (only works for DRAFT status)

#### Request 10: Delete Material Request (DRAFT only)
- Deletes a Material Request
- **Expected**: 204 No Content (only works for DRAFT status)

### 2. Status Transitions

#### Request 7: Submit Material Request
- Changes status from DRAFT to SUBMITTED
- **Expected**: 200 OK with status = "submitted"

#### Request 9: Cancel Material Request
- Changes status to CANCELLED
- **Expected**: 200 OK with status = "cancelled"

### 3. List and Filter Operations

#### Request 4: List All Material Requests
- Paginated list with sorting
- **Expected**: 200 OK with array of Material Requests

#### Request 5: Filter by Status (DRAFT)
- Lists only DRAFT Material Requests
- **Expected**: 200 OK with filtered results

#### Request 8: Filter by Status (SUBMITTED)
- Lists only SUBMITTED Material Requests
- **Expected**: 200 OK with filtered results

### 4. Multiple Scenarios

#### Request 2: Manufacturing Raw Materials
- Creates Material Request with 4 line items
- Different item types and quantities
- **Expected**: 201 Created

#### Request 11: IT Equipment
- Creates Material Request for IT equipment
- 4 line items with laptops, monitors, etc.
- **Expected**: 201 Created

### 5. Error Handling Tests

#### Request 12: Invalid Data - Negative Quantity
- Tests validation for negative quantity
- **Expected**: 400 Bad Request

#### Request 13: Invalid Data - No Line Items
- Tests validation for empty line items
- **Expected**: 400 Bad Request

#### Request 14: Update Submitted Material Request
- Tests business rule: cannot update submitted requests
- **Expected**: 409 Conflict

## Recommended Testing Flow

### Flow 1: Happy Path
1. **Create** Material Request (Request 1)
2. **Get** Material Request by ID (Request 3)
3. **Update** Material Request (Request 6)
4. **Submit** Material Request (Request 7)
5. **List** Submitted requests (Request 8)

### Flow 2: Create and Cancel
1. **Create** Material Request (Request 2)
2. **Get** Material Request by ID (Request 3)
3. **Cancel** Material Request (Request 9)

### Flow 3: Error Testing
1. **Test** negative quantity (Request 12)
2. **Test** no line items (Request 13)
3. **Create** and **Submit** a request
4. **Try to Update** submitted request (Request 14) - should fail

### Flow 4: List and Filter
1. **Create** multiple Material Requests (Requests 1, 2, 11)
2. **List** all requests (Request 4)
3. **Filter** by DRAFT status (Request 5)
4. **Submit** one request (Request 7)
5. **Filter** by SUBMITTED status (Request 8)

## Response Examples

### Successful Creation (201 Created)
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "organization_id": "org-uuid-here",
  "status": "draft",
  "notes": "Office supplies needed for Q1 2024",
  "created_by": "user-uuid-here",
  "updated_by": null,
  "created_at": "2024-02-14T10:30:00Z",
  "updated_at": "2024-02-14T10:30:00Z",
  "line_items": [
    {
      "id": "line-item-uuid-1",
      "organization_id": "org-uuid-here",
      "material_request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 50,
      "required_date": "2024-03-15",
      "description": "Ergonomic office chairs",
      "created_at": "2024-02-14T10:30:00Z",
      "updated_at": "2024-02-14T10:30:00Z"
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
    "message": "Cannot update Material Request in SUBMITTED status",
    "status_code": 409,
    "code": "STATE_CONFLICT"
  }
}
```

## Troubleshooting

### Issue: 401 Unauthorized
**Solution**: Update the `access_token` in the environment with a valid JWT token

### Issue: 404 Not Found (Item not found)
**Solution**: Update the `item_id_X` variables with real item IDs from your database

### Issue: 403 Forbidden
**Solution**: Ensure your user has the required permissions:
- `material_request.create`
- `material_request.read`
- `material_request.update`

### Issue: 409 Conflict (Cannot update)
**Solution**: You can only update Material Requests in DRAFT status. Once submitted, they cannot be modified.

### Issue: Connection Refused
**Solution**: Ensure the core-service is running on `http://localhost:8001`

## API Endpoints Summary

| Method | Endpoint | Description | Status Requirement |
|--------|----------|-------------|-------------------|
| POST | `/api/v1/material-requests` | Create Material Request | - |
| GET | `/api/v1/material-requests` | List Material Requests | - |
| GET | `/api/v1/material-requests/{id}` | Get Material Request | - |
| PUT | `/api/v1/material-requests/{id}` | Update Material Request | DRAFT only |
| DELETE | `/api/v1/material-requests/{id}` | Delete Material Request | DRAFT only |
| POST | `/api/v1/material-requests/{id}/submit` | Submit Material Request | DRAFT → SUBMITTED |
| POST | `/api/v1/material-requests/{id}/cancel` | Cancel Material Request | Any → CANCELLED |

## Status Flow

```
DRAFT → SUBMITTED → PARTIALLY_QUOTED → FULLY_QUOTED
  ↓
CANCELLED
```

- **DRAFT**: Initial state, can be edited/deleted
- **SUBMITTED**: Submitted for procurement, cannot be edited
- **PARTIALLY_QUOTED**: Some items have RFQ quotes
- **FULLY_QUOTED**: All items have RFQ quotes
- **CANCELLED**: Request cancelled

## Next Steps

After testing Material Requests, you can:
1. Create RFQs from submitted Material Requests
2. Add suppliers to RFQs
3. Record supplier quotes
4. Create Purchase Orders from RFQs

## Support

For issues or questions:
1. Check the API logs in the core-service
2. Verify database connectivity
3. Ensure all migrations are applied
4. Check the design document: `.kiro/specs/sourcing-flow/design.md`
