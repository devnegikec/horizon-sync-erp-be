# Material Request API Enhancements

## Overview

The Material Request module has been enhanced to provide a more robust sourcing workflow, matching the completeness of the Revenue module. These enhancements address the missing pieces identified in the sourcing flow.

## What's New

### Header Level (material_requests table)

#### 1. Request Number (`request_no`)

- **Type**: `string` (max 50 characters)
- **Purpose**: Human-readable reference number for UI/UX and printing
- **Format**: `MR-YYYY-NNNN` (e.g., `MR-2024-0001`)
- **Auto-generation**: If not provided, automatically generated based on year and count
- **Example**: `MR-2026-0042`

#### 2. Request Type (`type`)

- **Type**: `enum` (purchase, transfer, issue)
- **Purpose**: Indicates why materials are being requested
- **Values**:
  - `purchase`: Buy from vendor (default)
  - `transfer`: Move from Warehouse A to Warehouse B
  - `issue`: Give to a department
- **Default**: `purchase`

#### 3. Priority (`priority`)

- **Type**: `enum` (low, medium, high, urgent)
- **Purpose**: Helps procurement officers prioritize which RFQs to create first
- **Values**:
  - `low`: Can wait
  - `medium`: Normal priority (default)
  - `high`: Important, needs attention soon
  - `urgent`: Emergency, handle immediately
- **Default**: `medium`

#### 4. Target Warehouse (`target_warehouse_id`)

- **Type**: `UUID` (nullable)
- **Purpose**: Indicates where goods should eventually land
- **Note**: Foreign key constraint will be added when warehouses table is created

#### 5. Requested By (`requested_by`)

- **Type**: `UUID` (nullable)
- **Purpose**: User ID of the person who requested the materials
- **Default**: Set to current user if not provided

#### 6. Department (`department`)

- **Type**: `string` (max 100 characters, nullable)
- **Purpose**: Department requesting the materials
- **Example**: "Production", "Maintenance", "R&D"

### Line Level (material_request_lines table)

#### 1. Unit of Measure (`uom`)

- **Type**: `string` (max 50 characters, nullable)
- **Purpose**: Specifies the unit for quantity (critical for vendor communication)
- **Examples**: "Kgs", "Boxes", "Pallets", "Pieces", "Liters", "Meters"
- **Why Important**: Vendors might sell in different units than you consume

#### 2. Estimated Unit Cost (`estimated_unit_cost`)

- **Type**: `decimal(15,4)` (nullable)
- **Purpose**: Helps in approval workflow
- **Use Case**: "Requests over $5,000 need Manager approval"
- **Note**: This is an estimate, not the final PO price

#### 3. Requested For (`requested_for`)

- **Type**: `string` (max 255 characters, nullable)
- **Purpose**: Employee name or ID who is the "internal customer"
- **Example**: "John Doe", "EMP-12345"

#### 4. Requested For Department (`requested_for_department`)

- **Type**: `string` (max 100 characters, nullable)
- **Purpose**: Department of the internal customer
- **Example**: "Assembly Line 2", "Quality Control"

## API Changes

### Create Material Request

**Endpoint**: `POST /api/v1/material-requests`

**Request Body**:

```json
{
  "request_no": "MR-2026-0042", // Optional, auto-generated if not provided
  "type": "purchase", // Optional, default: "purchase"
  "priority": "high", // Optional, default: "medium"
  "target_warehouse_id": "uuid", // Optional
  "requested_by": "uuid", // Optional, defaults to current user
  "department": "Production", // Optional
  "notes": "Urgent materials needed for Project X",
  "line_items": [
    {
      "item_id": "uuid",
      "quantity": 100,
      "uom": "Kgs", // NEW
      "required_date": "2026-03-01",
      "description": "High-grade steel",
      "estimated_unit_cost": 25.5, // NEW
      "requested_for": "John Doe", // NEW
      "requested_for_department": "Assembly" // NEW
    }
  ]
}
```

### Update Material Request

**Endpoint**: `PATCH /api/v1/material-requests/{id}`

**Request Body** (all fields optional):

```json
{
  "request_no": "MR-2026-0042",
  "type": "transfer",
  "priority": "urgent",
  "target_warehouse_id": "uuid",
  "requested_by": "uuid",
  "department": "Maintenance",
  "notes": "Updated notes",
  "line_items": [
    {
      "item_id": "uuid",
      "quantity": 150,
      "uom": "Boxes",
      "required_date": "2026-03-15",
      "description": "Updated description",
      "estimated_unit_cost": 30.0,
      "requested_for": "Jane Smith",
      "requested_for_department": "Quality Control"
    }
  ]
}
```

### Get Material Request

**Endpoint**: `GET /api/v1/material-requests/{id}`

**Response**:

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "request_no": "MR-2026-0042",
  "type": "purchase",
  "priority": "high",
  "status": "draft",
  "target_warehouse_id": "uuid",
  "requested_by": "uuid",
  "department": "Production",
  "notes": "Urgent materials needed",
  "created_by": "uuid",
  "updated_by": "uuid",
  "created_at": "2026-02-19T10:00:00Z",
  "updated_at": "2026-02-19T10:00:00Z",
  "line_items": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "material_request_id": "uuid",
      "item_id": "uuid",
      "quantity": 100,
      "uom": "Kgs",
      "required_date": "2026-03-01",
      "description": "High-grade steel",
      "estimated_unit_cost": 25.5,
      "requested_for": "John Doe",
      "requested_for_department": "Assembly",
      "created_at": "2026-02-19T10:00:00Z",
      "updated_at": "2026-02-19T10:00:00Z"
    }
  ]
}
```

### List Material Requests

**Endpoint**: `GET /api/v1/material-requests`

**Response**:

```json
{
  "material_requests": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "request_no": "MR-2026-0042",
      "type": "purchase",
      "priority": "high",
      "status": "submitted",
      "department": "Production",
      "created_at": "2026-02-19T10:00:00Z",
      "created_by": "uuid",
      "line_items_count": 3
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 1,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

## Use Cases

### 1. Purchase Request (Buy from Vendor)

```json
{
  "type": "purchase",
  "priority": "high",
  "department": "Production",
  "notes": "Materials for Q1 production run",
  "line_items": [
    {
      "item_id": "uuid",
      "quantity": 500,
      "uom": "Kgs",
      "required_date": "2026-03-15",
      "estimated_unit_cost": 12.5,
      "requested_for": "Production Manager",
      "requested_for_department": "Manufacturing"
    }
  ]
}
```

### 2. Transfer Request (Move Between Warehouses)

```json
{
  "type": "transfer",
  "priority": "medium",
  "target_warehouse_id": "warehouse-b-uuid",
  "department": "Logistics",
  "notes": "Transfer to regional warehouse",
  "line_items": [
    {
      "item_id": "uuid",
      "quantity": 200,
      "uom": "Boxes",
      "required_date": "2026-02-25",
      "requested_for": "Regional Manager",
      "requested_for_department": "Distribution"
    }
  ]
}
```

### 3. Issue Request (Give to Department)

```json
{
  "type": "issue",
  "priority": "urgent",
  "department": "Maintenance",
  "notes": "Emergency repair materials",
  "line_items": [
    {
      "item_id": "uuid",
      "quantity": 10,
      "uom": "Pieces",
      "required_date": "2026-02-20",
      "estimated_unit_cost": 150.0,
      "requested_for": "Maintenance Supervisor",
      "requested_for_department": "Facilities"
    }
  ]
}
```

## Approval Workflow Example

With the new `estimated_unit_cost` field, you can implement approval workflows:

```python
# Calculate total estimated cost
total_cost = sum(
    line.quantity * line.estimated_unit_cost
    for line in material_request.line_items
    if line.estimated_unit_cost
)

# Apply approval rules
if total_cost > 5000:
    # Requires manager approval
    send_approval_request(material_request, "manager")
elif total_cost > 10000:
    # Requires director approval
    send_approval_request(material_request, "director")
```

## Priority-Based Procurement

Procurement officers can now prioritize their work:

1. **Urgent**: Handle immediately (emergency repairs, production stoppage)
2. **High**: Process within 24 hours (important projects)
3. **Medium**: Process within 3-5 days (normal operations)
4. **Low**: Process when time permits (stock replenishment)

## Database Schema

### New Enums

```sql
-- Material Request Type
CREATE TYPE materialrequesttype AS ENUM ('purchase', 'transfer', 'issue');

-- Material Request Priority
CREATE TYPE materialrequestpriority AS ENUM ('low', 'medium', 'high', 'urgent');
```

### Updated Tables

```sql
-- material_requests table additions
ALTER TABLE material_requests ADD COLUMN request_no VARCHAR(50);
ALTER TABLE material_requests ADD COLUMN type materialrequesttype NOT NULL DEFAULT 'purchase';
ALTER TABLE material_requests ADD COLUMN priority materialrequestpriority NOT NULL DEFAULT 'medium';
ALTER TABLE material_requests ADD COLUMN target_warehouse_id UUID;
ALTER TABLE material_requests ADD COLUMN requested_by UUID;
ALTER TABLE material_requests ADD COLUMN department VARCHAR(100);

CREATE INDEX ix_material_requests_request_no ON material_requests(request_no);

-- material_request_lines table additions
ALTER TABLE material_request_lines ADD COLUMN uom VARCHAR(50);
ALTER TABLE material_request_lines ADD COLUMN estimated_unit_cost NUMERIC(15,4);
ALTER TABLE material_request_lines ADD COLUMN requested_for VARCHAR(255);
ALTER TABLE material_request_lines ADD COLUMN requested_for_department VARCHAR(100);
```

## Migration

The migration has been applied automatically. The revision ID is `h8i9j0k1l2m3`.

To verify:

```bash
docker compose exec core-service python -m alembic current
```

## Testing

### Test Create with New Fields

```bash
curl -X POST "http://localhost:8001/api/v1/material-requests" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "purchase",
    "priority": "high",
    "department": "Production",
    "notes": "Test request",
    "line_items": [
      {
        "item_id": "YOUR_ITEM_UUID",
        "quantity": 100,
        "uom": "Kgs",
        "required_date": "2026-03-01",
        "estimated_unit_cost": 25.50,
        "requested_for": "John Doe",
        "requested_for_department": "Assembly"
      }
    ]
  }'
```

### Test List with New Fields

```bash
curl -X GET "http://localhost:8001/api/v1/material-requests" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Benefits

1. **Better Tracking**: Human-readable request numbers (MR-2026-0042)
2. **Clear Purpose**: Know if it's for purchase, transfer, or issue
3. **Prioritization**: Handle urgent requests first
4. **Approval Workflow**: Use estimated costs for approval rules
5. **Accountability**: Track who requested and for which department
6. **Vendor Communication**: Clear UOM prevents confusion
7. **Warehouse Planning**: Know target warehouse in advance
8. **Internal Customer**: Track which employee/department needs the materials

## Next Steps

1. Implement approval workflow based on estimated costs
2. Add warehouse management module
3. Create RFQ from Material Request with priority consideration
4. Add email notifications for urgent requests
5. Generate printable Material Request forms with request_no
6. Add dashboard showing requests by priority and type
7. Implement budget tracking using estimated costs

## Backward Compatibility

All new fields are optional (nullable) or have defaults, ensuring backward compatibility with existing Material Requests. Existing records will have:

- `type`: "purchase" (default)
- `priority`: "medium" (default)
- `request_no`: NULL (can be generated on first update)
- Other new fields: NULL

## Support

For questions or issues, refer to:

- API Documentation: http://localhost:8001/docs
- Material Request API: http://localhost:8001/docs#/Material%20Requests
