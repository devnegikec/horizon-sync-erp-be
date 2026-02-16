# Sourcing Flow API Documentation

## Overview

The Sourcing Flow API implements a complete procure-to-pay workflow, covering the entire procurement lifecycle from internal demand identification through supplier payment. This document provides comprehensive API reference for all endpoints, including request/response examples, error responses, and workflow sequences.

## Table of Contents

1. [Authentication](#authentication)
2. [Common Patterns](#common-patterns)
3. [Material Request API](#material-request-api)
4. [RFQ API](#rfq-api)
5. [Purchase Order API](#purchase-order-api)
6. [Receipt Note API](#receipt-note-api)
7. [Purchase Invoice API](#purchase-invoice-api)
8. [Payment Made API](#payment-made-api)
9. [Error Responses](#error-responses)
10. [Workflow Sequences](#workflow-sequences)

## Authentication

All API endpoints require authentication using JWT tokens.

**Header:**
```
Authorization: Bearer <access_token>
```

**Getting a Token:**
Obtain an access token from the identity service by logging in with valid credentials.

## Common Patterns

### Standard Response Fields

All document responses include these standard fields:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Unique identifier |
| `organization_id` | UUID | Organization identifier |
| `status` | string | Current document status |
| `created_at` | timestamp | Creation timestamp |
| `updated_at` | timestamp | Last update timestamp |
| `created_by` | UUID | User who created the document |
| `updated_by` | UUID | User who last updated the document |

### Pagination

List endpoints support pagination with the following query parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-indexed) |
| `page_size` | integer | 20 | Items per page (max 100) |
| `sort_by` | string | created_at | Field to sort by |
| `sort_order` | string | desc | Sort order (asc/desc) |


**Pagination Response Format:**
```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "total_pages": 8
}
```

### Status Filtering

List endpoints support filtering by status:

```
GET /api/v1/material-requests?status=draft
GET /api/v1/rfqs?status=sent
GET /api/v1/purchase-orders?status=submitted
```

---

## Material Request API

Material Requests signal internal demand for materials and initiate the procurement process.

### Status Flow

```
DRAFT → SUBMITTED → PARTIALLY_QUOTED → FULLY_QUOTED
  ↓
CANCELLED
```

### Endpoints

#### Create Material Request

Creates a new Material Request in DRAFT status.

**Endpoint:** `POST /api/v1/material-requests`

**Request Body:**
```json
{
  "notes": "Office supplies needed for Q1 2024",
  "line_items": [
    {
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 50,
      "required_date": "2024-03-15",
      "description": "Ergonomic office chairs"
    },
    {
      "item_id": "22222222-2222-2222-2222-222222222222",
      "quantity": 25,
      "required_date": "2024-03-20",
      "description": "Standing desks"
    }
  ]
}
```

**Success Response (201 Created):**
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
    },
    {
      "id": "line-item-uuid-2",
      "organization_id": "org-uuid-here",
      "material_request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "item_id": "22222222-2222-2222-2222-222222222222",
      "quantity": 25,
      "required_date": "2024-03-20",
      "description": "Standing desks",
      "created_at": "2024-02-14T10:30:00Z",
      "updated_at": "2024-02-14T10:30:00Z"
    }
  ]
}
```


**Error Responses:**

*Validation Error (400):*
```json
{
  "detail": {
    "message": "Validation failed",
    "status_code": 400,
    "code": "VALIDATION_ERROR",
    "errors": [
      {
        "field": "line_items[0].quantity",
        "reason": "Quantity must be greater than zero"
      }
    ]
  }
}
```

*Item Not Found (404):*
```json
{
  "detail": {
    "message": "Item not found",
    "status_code": 404,
    "code": "ITEM_NOT_FOUND",
    "entity_type": "ITEM",
    "entity_id": "11111111-1111-1111-1111-111111111111"
  }
}
```

---

#### Get Material Request by ID

Retrieves a specific Material Request with all line items.

**Endpoint:** `GET /api/v1/material-requests/{id}`

**Success Response (200 OK):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "organization_id": "org-uuid-here",
  "status": "submitted",
  "notes": "Office supplies needed for Q1 2024",
  "created_by": "user-uuid-here",
  "updated_by": null,
  "created_at": "2024-02-14T10:30:00Z",
  "updated_at": "2024-02-14T11:00:00Z",
  "line_items": [...]
}
```

**Error Response (404):**
```json
{
  "detail": {
    "message": "Material Request not found",
    "status_code": 404,
    "code": "MATERIAL_REQUEST_NOT_FOUND",
    "entity_type": "MATERIAL_REQUEST",
    "entity_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

---

#### List Material Requests

Retrieves a paginated list of Material Requests with optional filtering.

**Endpoint:** `GET /api/v1/material-requests`

**Query Parameters:**
- `page` (integer, default: 1)
- `page_size` (integer, default: 20, max: 100)
- `sort_by` (string, default: created_at)
- `sort_order` (string, default: desc)
- `status` (string, optional): Filter by status (draft, submitted, etc.)

**Example Request:**
```
GET /api/v1/material-requests?page=1&page_size=20&status=draft&sort_by=created_at&sort_order=desc
```

**Success Response (200 OK):**
```json
{
  "items": [
    {
      "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "organization_id": "org-uuid-here",
      "status": "draft",
      "notes": "Office supplies needed for Q1 2024",
      "created_by": "user-uuid-here",
      "created_at": "2024-02-14T10:30:00Z",
      "updated_at": "2024-02-14T10:30:00Z",
      "line_items": [...]
    }
  ],
  "total": 45,
  "page": 1,
  "page_size": 20,
  "total_pages": 3
}
```


---

#### Update Material Request

Updates a Material Request. Only allowed in DRAFT status.

**Endpoint:** `PUT /api/v1/material-requests/{id}`

**Request Body:**
```json
{
  "notes": "Updated notes - Office supplies for Q1 2024",
  "line_items": [
    {
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 60,
      "required_date": "2024-03-15",
      "description": "Ergonomic office chairs - increased quantity"
    }
  ]
}
```

**Success Response (200 OK):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "organization_id": "org-uuid-here",
  "status": "draft",
  "notes": "Updated notes - Office supplies for Q1 2024",
  "updated_at": "2024-02-14T11:15:00Z",
  "line_items": [...]
}
```

**Error Response - State Conflict (409):**
```json
{
  "detail": {
    "message": "Cannot update Material Request in SUBMITTED status",
    "status_code": 409,
    "code": "STATE_CONFLICT",
    "current_state": "submitted",
    "allowed_states": ["draft"]
  }
}
```

---

#### Submit Material Request

Changes status from DRAFT to SUBMITTED. After submission, the Material Request cannot be modified.

**Endpoint:** `POST /api/v1/material-requests/{id}/submit`

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "organization_id": "org-uuid-here",
  "status": "submitted",
  "notes": "Office supplies needed for Q1 2024",
  "created_at": "2024-02-14T10:30:00Z",
  "updated_at": "2024-02-14T11:30:00Z",
  "line_items": [...]
}
```

**Error Response - Invalid Transition (409):**
```json
{
  "detail": {
    "message": "Invalid status transition from CANCELLED to SUBMITTED",
    "status_code": 409,
    "code": "INVALID_TRANSITION",
    "current_state": "cancelled",
    "requested_state": "submitted"
  }
}
```

---

#### Cancel Material Request

Changes status to CANCELLED. Can be done from DRAFT or SUBMITTED status.

**Endpoint:** `POST /api/v1/material-requests/{id}/cancel`

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "cancelled",
  "updated_at": "2024-02-14T12:00:00Z"
}
```

---

#### Delete Material Request

Deletes a Material Request. Only allowed in DRAFT status.

**Endpoint:** `DELETE /api/v1/material-requests/{id}`

**Success Response (204 No Content):** Empty response body

**Error Response - State Conflict (409):**
```json
{
  "detail": {
    "message": "Cannot delete Material Request in SUBMITTED status",
    "status_code": 409,
    "code": "STATE_CONFLICT",
    "current_state": "submitted",
    "allowed_states": ["draft"]
  }
}
```


---

## RFQ API

Request for Quotation (RFQ) documents are sent to multiple suppliers to gather competitive pricing and terms.

### Status Flow

```
DRAFT → SENT → PARTIALLY_RESPONDED → FULLY_RESPONDED → CLOSED
  ↓
CLOSED (can close from any status)
```

### Endpoints

#### Create RFQ from Material Request

Creates a new RFQ from an existing Material Request. Copies all line items from the source Material Request.

**Endpoint:** `POST /api/v1/rfqs`

**Request Body:**
```json
{
  "material_request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "closing_date": "2024-03-30",
  "supplier_ids": [
    "supplier-uuid-1",
    "supplier-uuid-2",
    "supplier-uuid-3"
  ]
}
```

**Success Response (201 Created):**
```json
{
  "id": "rfq-uuid-here",
  "organization_id": "org-uuid-here",
  "material_request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "reference_type": "MATERIAL_REQUEST",
  "reference_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "draft",
  "closing_date": "2024-03-30",
  "created_by": "user-uuid-here",
  "updated_by": null,
  "created_at": "2024-02-15T10:30:00Z",
  "updated_at": "2024-02-15T10:30:00Z",
  "line_items": [
    {
      "id": "rfq-line-uuid-1",
      "organization_id": "org-uuid-here",
      "rfq_id": "rfq-uuid-here",
      "item_id": "11111111-1111-1111-1111-111111111111",
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
      "rfq_id": "rfq-uuid-here",
      "supplier_id": "supplier-uuid-1",
      "created_at": "2024-02-15T10:30:00Z"
    },
    {
      "id": "rfq-supplier-uuid-2",
      "organization_id": "org-uuid-here",
      "rfq_id": "rfq-uuid-here",
      "supplier_id": "supplier-uuid-2",
      "created_at": "2024-02-15T10:30:00Z"
    },
    {
      "id": "rfq-supplier-uuid-3",
      "organization_id": "org-uuid-here",
      "rfq_id": "rfq-uuid-here",
      "supplier_id": "supplier-uuid-3",
      "created_at": "2024-02-15T10:30:00Z"
    }
  ]
}
```

**Error Responses:**

*Material Request Not Found (404):*
```json
{
  "detail": {
    "message": "Material Request not found",
    "status_code": 404,
    "code": "MATERIAL_REQUEST_NOT_FOUND",
    "entity_type": "MATERIAL_REQUEST",
    "entity_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

*Material Request Not Submitted (409):*
```json
{
  "detail": {
    "message": "Material Request must be in SUBMITTED status",
    "status_code": 409,
    "code": "INVALID_STATE",
    "current_state": "draft",
    "required_state": "submitted"
  }
}
```

*Supplier Not Found (404):*
```json
{
  "detail": {
    "message": "Supplier not found",
    "status_code": 404,
    "code": "SUPPLIER_NOT_FOUND",
    "entity_type": "SUPPLIER",
    "entity_id": "supplier-uuid-1"
  }
}
```


---

#### Get RFQ by ID

Retrieves a specific RFQ with all line items, suppliers, and quotes.

**Endpoint:** `GET /api/v1/rfqs/{id}`

**Success Response (200 OK):**
```json
{
  "id": "rfq-uuid-here",
  "organization_id": "org-uuid-here",
  "material_request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "reference_type": "MATERIAL_REQUEST",
  "reference_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "sent",
  "closing_date": "2024-03-30",
  "created_at": "2024-02-15T10:30:00Z",
  "updated_at": "2024-02-15T11:00:00Z",
  "line_items": [
    {
      "id": "rfq-line-uuid-1",
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 50,
      "required_date": "2024-03-15",
      "description": "Ergonomic office chairs",
      "quotes": [
        {
          "id": "quote-uuid-1",
          "rfq_line_id": "rfq-line-uuid-1",
          "supplier_id": "supplier-uuid-1",
          "quoted_price": 125.50,
          "quoted_delivery_date": "2024-03-20",
          "supplier_notes": "Best quality materials, bulk discount available",
          "created_at": "2024-02-16T09:00:00Z"
        },
        {
          "id": "quote-uuid-2",
          "rfq_line_id": "rfq-line-uuid-1",
          "supplier_id": "supplier-uuid-2",
          "quoted_price": 118.75,
          "quoted_delivery_date": "2024-03-25",
          "supplier_notes": "Competitive pricing, standard delivery",
          "created_at": "2024-02-16T10:30:00Z"
        }
      ]
    }
  ],
  "suppliers": [...]
}
```

---

#### List RFQs

Retrieves a paginated list of RFQs with optional filtering.

**Endpoint:** `GET /api/v1/rfqs`

**Query Parameters:**
- `page` (integer, default: 1)
- `page_size` (integer, default: 20, max: 100)
- `sort_by` (string, default: created_at)
- `sort_order` (string, default: desc)
- `status` (string, optional): Filter by status

**Example Request:**
```
GET /api/v1/rfqs?page=1&page_size=20&status=sent&sort_by=closing_date&sort_order=asc
```

**Success Response (200 OK):**
```json
{
  "items": [
    {
      "id": "rfq-uuid-here",
      "material_request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "status": "sent",
      "closing_date": "2024-03-30",
      "created_at": "2024-02-15T10:30:00Z",
      "line_items": [...],
      "suppliers": [...]
    }
  ],
  "total": 12,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

#### Update RFQ

Updates an RFQ. Only allowed in DRAFT status.

**Endpoint:** `PUT /api/v1/rfqs/{id}`

**Request Body:**
```json
{
  "closing_date": "2024-04-15"
}
```

**Success Response (200 OK):**
```json
{
  "id": "rfq-uuid-here",
  "status": "draft",
  "closing_date": "2024-04-15",
  "updated_at": "2024-02-15T11:30:00Z"
}
```

**Error Response - State Conflict (409):**
```json
{
  "detail": {
    "message": "Cannot update RFQ in SENT status",
    "status_code": 409,
    "code": "STATE_CONFLICT",
    "current_state": "sent",
    "allowed_states": ["draft"]
  }
}
```


---

#### Send RFQ to Suppliers

Changes status from DRAFT to SENT. After sending, the RFQ cannot be modified.

**Endpoint:** `POST /api/v1/rfqs/{id}/send`

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "id": "rfq-uuid-here",
  "status": "sent",
  "updated_at": "2024-02-15T12:00:00Z"
}
```

---

#### Record Supplier Quote

Records a quote from a supplier for a specific RFQ line item.

**Endpoint:** `POST /api/v1/rfqs/{id}/quotes`

**Request Body:**
```json
{
  "rfq_line_id": "rfq-line-uuid-1",
  "supplier_id": "supplier-uuid-1",
  "quoted_price": 125.50,
  "quoted_delivery_date": "2024-03-20",
  "supplier_notes": "Best quality materials, bulk discount available"
}
```

**Success Response (200 OK):**
```json
{
  "id": "quote-uuid-1",
  "organization_id": "org-uuid-here",
  "rfq_line_id": "rfq-line-uuid-1",
  "supplier_id": "supplier-uuid-1",
  "quoted_price": 125.50,
  "quoted_delivery_date": "2024-03-20",
  "supplier_notes": "Best quality materials, bulk discount available",
  "created_at": "2024-02-16T09:00:00Z"
}
```

**Error Responses:**

*RFQ Not in Valid State (409):*
```json
{
  "detail": {
    "message": "Cannot record quote for RFQ in DRAFT status",
    "status_code": 409,
    "code": "INVALID_STATE",
    "current_state": "draft",
    "required_states": ["sent", "partially_responded"]
  }
}
```

*Supplier Not Associated with RFQ (400):*
```json
{
  "detail": {
    "message": "Supplier is not associated with this RFQ",
    "status_code": 400,
    "code": "INVALID_SUPPLIER",
    "supplier_id": "supplier-uuid-1",
    "rfq_id": "rfq-uuid-here"
  }
}
```

---

#### Close RFQ

Changes status to CLOSED. Can be done from any status.

**Endpoint:** `POST /api/v1/rfqs/{id}/close`

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "id": "rfq-uuid-here",
  "status": "closed",
  "updated_at": "2024-02-20T15:00:00Z"
}
```

---

#### Delete RFQ

Deletes an RFQ. Only allowed in DRAFT status.

**Endpoint:** `DELETE /api/v1/rfqs/{id}`

**Success Response (204 No Content):** Empty response body

**Error Response - State Conflict (409):**
```json
{
  "detail": {
    "message": "Cannot delete RFQ in SENT status",
    "status_code": 409,
    "code": "STATE_CONFLICT",
    "current_state": "sent",
    "allowed_states": ["draft"]
  }
}
```


---

## Purchase Order API

Purchase Orders are legally binding contracts issued to suppliers for procurement.

### Status Flow

```
DRAFT → SUBMITTED → PARTIALLY_RECEIVED → FULLY_RECEIVED → CLOSED
  ↓
CANCELLED
```

### Endpoints

#### Create Purchase Order from RFQ

Creates a new Purchase Order from selected RFQ quotes. Automatically calculates totals using the Transaction Engine.

**Endpoint:** `POST /api/v1/purchase-orders`

**Request Body:**
```json
{
  "rfq_id": "rfq-uuid-here",
  "supplier_id": "supplier-uuid-1",
  "tax_rate": 0.10,
  "discount_amount": 0,
  "line_items": [
    {
      "rfq_line_id": "rfq-line-uuid-1",
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 50,
      "unit_price": 125.50
    },
    {
      "rfq_line_id": "rfq-line-uuid-2",
      "item_id": "22222222-2222-2222-2222-222222222222",
      "quantity": 25,
      "unit_price": 450.00
    }
  ]
}
```

**Success Response (201 Created):**
```json
{
  "id": "po-uuid-here",
  "organization_id": "org-uuid-here",
  "rfq_id": "rfq-uuid-here",
  "reference_type": "RFQ",
  "reference_id": "rfq-uuid-here",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-1",
  "status": "draft",
  "subtotal": 17525.00,
  "tax_amount": 1752.50,
  "tax_rate": 0.10,
  "discount_amount": 0,
  "grand_total": 19277.50,
  "created_by": "user-uuid-here",
  "updated_by": null,
  "created_at": "2024-02-17T10:00:00Z",
  "updated_at": "2024-02-17T10:00:00Z",
  "line_items": [
    {
      "id": "po-line-uuid-1",
      "organization_id": "org-uuid-here",
      "purchase_order_id": "po-uuid-here",
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 50,
      "unit_price": 125.50,
      "line_total": 6275.00,
      "received_quantity": 0,
      "created_at": "2024-02-17T10:00:00Z",
      "updated_at": "2024-02-17T10:00:00Z"
    },
    {
      "id": "po-line-uuid-2",
      "organization_id": "org-uuid-here",
      "purchase_order_id": "po-uuid-here",
      "item_id": "22222222-2222-2222-2222-222222222222",
      "quantity": 25,
      "unit_price": 450.00,
      "line_total": 11250.00,
      "received_quantity": 0,
      "created_at": "2024-02-17T10:00:00Z",
      "updated_at": "2024-02-17T10:00:00Z"
    }
  ]
}
```

**Calculation Details:**
- Line 1 Total: 50 × 125.50 = 6,275.00
- Line 2 Total: 25 × 450.00 = 11,250.00
- Subtotal: 6,275.00 + 11,250.00 = 17,525.00
- Tax (10%): 17,525.00 × 0.10 = 1,752.50
- Grand Total: 17,525.00 + 1,752.50 - 0 = 19,277.50

**Error Responses:**

*RFQ Not Found (404):*
```json
{
  "detail": {
    "message": "RFQ not found",
    "status_code": 404,
    "code": "RFQ_NOT_FOUND",
    "entity_type": "RFQ",
    "entity_id": "rfq-uuid-here"
  }
}
```

*Supplier Not Found (404):*
```json
{
  "detail": {
    "message": "Supplier not found",
    "status_code": 404,
    "code": "SUPPLIER_NOT_FOUND",
    "entity_type": "SUPPLIER",
    "entity_id": "supplier-uuid-1"
  }
}
```

*No Quotes Available (409):*
```json
{
  "detail": {
    "message": "RFQ has no supplier quotes",
    "status_code": 409,
    "code": "NO_QUOTES_AVAILABLE",
    "rfq_id": "rfq-uuid-here"
  }
}
```


---

#### Get Purchase Order by ID

Retrieves a specific Purchase Order with all line items and calculated totals.

**Endpoint:** `GET /api/v1/purchase-orders/{id}`

**Success Response (200 OK):**
```json
{
  "id": "po-uuid-here",
  "organization_id": "org-uuid-here",
  "rfq_id": "rfq-uuid-here",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-1",
  "status": "submitted",
  "subtotal": 17525.00,
  "tax_amount": 1752.50,
  "tax_rate": 0.10,
  "discount_amount": 0,
  "grand_total": 19277.50,
  "created_at": "2024-02-17T10:00:00Z",
  "updated_at": "2024-02-17T11:00:00Z",
  "line_items": [...]
}
```

---

#### List Purchase Orders

Retrieves a paginated list of Purchase Orders with optional filtering.

**Endpoint:** `GET /api/v1/purchase-orders`

**Query Parameters:**
- `page` (integer, default: 1)
- `page_size` (integer, default: 20, max: 100)
- `sort_by` (string, default: created_at)
- `sort_order` (string, default: desc)
- `status` (string, optional): Filter by status
- `supplier_id` (UUID, optional): Filter by supplier

**Example Request:**
```
GET /api/v1/purchase-orders?page=1&page_size=20&status=submitted&supplier_id=supplier-uuid-1
```

**Success Response (200 OK):**
```json
{
  "items": [
    {
      "id": "po-uuid-here",
      "rfq_id": "rfq-uuid-here",
      "party_id": "supplier-uuid-1",
      "status": "submitted",
      "grand_total": 19277.50,
      "created_at": "2024-02-17T10:00:00Z",
      "line_items": [...]
    }
  ],
  "total": 8,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

#### Update Purchase Order

Updates a Purchase Order. Only allowed in DRAFT status.

**Endpoint:** `PUT /api/v1/purchase-orders/{id}`

**Request Body:**
```json
{
  "tax_rate": 0.12,
  "discount_amount": 500.00,
  "line_items": [
    {
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 60,
      "unit_price": 125.50
    }
  ]
}
```

**Success Response (200 OK):**
```json
{
  "id": "po-uuid-here",
  "status": "draft",
  "subtotal": 7530.00,
  "tax_amount": 903.60,
  "tax_rate": 0.12,
  "discount_amount": 500.00,
  "grand_total": 7933.60,
  "updated_at": "2024-02-17T11:30:00Z",
  "line_items": [...]
}
```

**Error Response - State Conflict (409):**
```json
{
  "detail": {
    "message": "Cannot update Purchase Order in SUBMITTED status",
    "status_code": 409,
    "code": "STATE_CONFLICT",
    "current_state": "submitted",
    "allowed_states": ["draft"]
  }
}
```

---

#### Submit Purchase Order

Changes status from DRAFT to SUBMITTED. After submission, the Purchase Order cannot be modified.

**Endpoint:** `POST /api/v1/purchase-orders/{id}/submit`

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "id": "po-uuid-here",
  "status": "submitted",
  "updated_at": "2024-02-17T12:00:00Z"
}
```


---

#### Cancel Purchase Order

Changes status to CANCELLED. Can be done from DRAFT or SUBMITTED status.

**Endpoint:** `POST /api/v1/purchase-orders/{id}/cancel`

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "id": "po-uuid-here",
  "status": "cancelled",
  "updated_at": "2024-02-17T13:00:00Z"
}
```

**Error Response - Invalid State (409):**
```json
{
  "detail": {
    "message": "Cannot cancel Purchase Order in FULLY_RECEIVED status",
    "status_code": 409,
    "code": "INVALID_TRANSITION",
    "current_state": "fully_received",
    "requested_state": "cancelled"
  }
}
```

---

#### Close Purchase Order

Changes status to CLOSED. Only allowed when status is FULLY_RECEIVED.

**Endpoint:** `POST /api/v1/purchase-orders/{id}/close`

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "id": "po-uuid-here",
  "status": "closed",
  "updated_at": "2024-02-25T10:00:00Z"
}
```

**Error Response - Invalid State (409):**
```json
{
  "detail": {
    "message": "Cannot close Purchase Order. Must be FULLY_RECEIVED",
    "status_code": 409,
    "code": "INVALID_STATE",
    "current_state": "partially_received",
    "required_state": "fully_received"
  }
}
```

---

#### Delete Purchase Order

Deletes a Purchase Order. Only allowed in DRAFT status.

**Endpoint:** `DELETE /api/v1/purchase-orders/{id}`

**Success Response (204 No Content):** Empty response body

**Error Response - State Conflict (409):**
```json
{
  "detail": {
    "message": "Cannot delete Purchase Order in SUBMITTED status",
    "status_code": 409,
    "code": "STATE_CONFLICT",
    "current_state": "submitted",
    "allowed_states": ["draft"]
  }
}
```

---

## Receipt Note API

Receipt Notes record the physical arrival of goods at the warehouse. They use the existing Purchase Receipt API with specific reference configuration.

### Endpoints

#### Create Receipt Note

Creates a Receipt Note for a Purchase Order. Automatically updates Purchase Order status and increments stock levels.

**Endpoint:** `POST /api/v1/purchase-receipts`

**Request Body:**
```json
{
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "po-uuid-here",
  "received_date": "2024-02-20",
  "line_items": [
    {
      "purchase_order_line_id": "po-line-uuid-1",
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 30
    }
  ]
}
```

**Success Response (201 Created):**
```json
{
  "id": "receipt-uuid-here",
  "organization_id": "org-uuid-here",
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "po-uuid-here",
  "received_date": "2024-02-20",
  "status": "completed",
  "created_by": "user-uuid-here",
  "created_at": "2024-02-20T14:30:00Z",
  "updated_at": "2024-02-20T14:30:00Z",
  "line_items": [
    {
      "id": "receipt-line-uuid-1",
      "purchase_receipt_id": "receipt-uuid-here",
      "purchase_order_line_id": "po-line-uuid-1",
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 30,
      "created_at": "2024-02-20T14:30:00Z"
    }
  ]
}
```

**Side Effects:**
1. Purchase Order line `received_quantity` updated: 0 → 30
2. Purchase Order status updated: SUBMITTED → PARTIALLY_RECEIVED
3. Stock level incremented by 30 for item `11111111-1111-1111-1111-111111111111`


**Error Responses:**

*Purchase Order Not Found (404):*
```json
{
  "detail": {
    "message": "Purchase Order not found",
    "status_code": 404,
    "code": "PURCHASE_ORDER_NOT_FOUND",
    "entity_type": "PURCHASE_ORDER",
    "entity_id": "po-uuid-here"
  }
}
```

*Invalid Purchase Order State (409):*
```json
{
  "detail": {
    "message": "Cannot create receipt for Purchase Order in DRAFT status",
    "status_code": 409,
    "code": "INVALID_STATE",
    "current_state": "draft",
    "required_states": ["submitted", "partially_received"]
  }
}
```

*Quantity Exceeds Ordered (400):*
```json
{
  "detail": {
    "message": "Received quantity exceeds ordered quantity",
    "status_code": 400,
    "code": "QUANTITY_EXCEEDED",
    "ordered_quantity": 50,
    "already_received": 30,
    "attempting_to_receive": 30,
    "remaining_quantity": 20
  }
}
```

---

#### Get Receipt Note by ID

Retrieves a specific Receipt Note.

**Endpoint:** `GET /api/v1/purchase-receipts/{id}`

**Success Response (200 OK):**
```json
{
  "id": "receipt-uuid-here",
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "po-uuid-here",
  "received_date": "2024-02-20",
  "status": "completed",
  "created_at": "2024-02-20T14:30:00Z",
  "line_items": [...]
}
```

---

#### List Receipt Notes

Retrieves a paginated list of Receipt Notes.

**Endpoint:** `GET /api/v1/purchase-receipts`

**Query Parameters:**
- `page` (integer, default: 1)
- `page_size` (integer, default: 20, max: 100)
- `reference_type` (string, optional): Filter by reference type (PURCHASE_ORDER)
- `reference_id` (UUID, optional): Filter by Purchase Order ID

**Example Request:**
```
GET /api/v1/purchase-receipts?reference_type=PURCHASE_ORDER&reference_id=po-uuid-here
```

**Success Response (200 OK):**
```json
{
  "items": [
    {
      "id": "receipt-uuid-here",
      "reference_type": "PURCHASE_ORDER",
      "reference_id": "po-uuid-here",
      "received_date": "2024-02-20",
      "status": "completed",
      "line_items": [...]
    }
  ],
  "total": 2,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

## Purchase Invoice API

Purchase Invoices record supplier bills as accounts payable. They use the existing Invoice API with PURCHASE type.

### Endpoints

#### Create Purchase Invoice

Creates a Purchase Invoice for a Purchase Order. Automatically calculates totals using the Transaction Engine.

**Endpoint:** `POST /api/v1/invoices`

**Request Body:**
```json
{
  "invoice_type": "PURCHASE",
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "po-uuid-here",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-1",
  "invoice_date": "2024-02-21",
  "due_date": "2024-03-21",
  "line_items": [
    {
      "purchase_order_line_id": "po-line-uuid-1",
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 30,
      "unit_price": 125.50
    }
  ]
}
```

**Success Response (201 Created):**
```json
{
  "id": "invoice-uuid-here",
  "organization_id": "org-uuid-here",
  "invoice_type": "PURCHASE",
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "po-uuid-here",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-1",
  "invoice_date": "2024-02-21",
  "due_date": "2024-03-21",
  "status": "draft",
  "subtotal": 3765.00,
  "tax_amount": 376.50,
  "discount_amount": 0,
  "grand_total": 4141.50,
  "outstanding_balance": 4141.50,
  "created_by": "user-uuid-here",
  "created_at": "2024-02-21T10:00:00Z",
  "updated_at": "2024-02-21T10:00:00Z",
  "line_items": [
    {
      "id": "invoice-line-uuid-1",
      "invoice_id": "invoice-uuid-here",
      "purchase_order_line_id": "po-line-uuid-1",
      "item_id": "11111111-1111-1111-1111-111111111111",
      "quantity": 30,
      "unit_price": 125.50,
      "line_total": 3765.00,
      "created_at": "2024-02-21T10:00:00Z"
    }
  ]
}
```


**Error Responses:**

*Purchase Order Not Found (404):*
```json
{
  "detail": {
    "message": "Purchase Order not found",
    "status_code": 404,
    "code": "PURCHASE_ORDER_NOT_FOUND",
    "entity_type": "PURCHASE_ORDER",
    "entity_id": "po-uuid-here"
  }
}
```

*Invalid Purchase Order State (409):*
```json
{
  "detail": {
    "message": "Cannot create invoice for Purchase Order in DRAFT status",
    "status_code": 409,
    "code": "INVALID_STATE",
    "current_state": "draft",
    "required_states": ["submitted", "partially_received", "fully_received"]
  }
}
```

*Three-Way Matching Failed (400):*
```json
{
  "detail": {
    "message": "Invoiced quantity exceeds received quantity",
    "status_code": 400,
    "code": "THREE_WAY_MATCHING_FAILED",
    "item_id": "11111111-1111-1111-1111-111111111111",
    "invoiced_quantity": 50,
    "received_quantity": 30
  }
}
```

---

#### Get Purchase Invoice by ID

Retrieves a specific Purchase Invoice.

**Endpoint:** `GET /api/v1/invoices/{id}`

**Success Response (200 OK):**
```json
{
  "id": "invoice-uuid-here",
  "invoice_type": "PURCHASE",
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "po-uuid-here",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-1",
  "status": "submitted",
  "grand_total": 4141.50,
  "outstanding_balance": 4141.50,
  "created_at": "2024-02-21T10:00:00Z",
  "line_items": [...]
}
```

---

#### List Purchase Invoices

Retrieves a paginated list of Purchase Invoices.

**Endpoint:** `GET /api/v1/invoices`

**Query Parameters:**
- `page` (integer, default: 1)
- `page_size` (integer, default: 20, max: 100)
- `invoice_type` (string, optional): Filter by type (PURCHASE)
- `party_id` (UUID, optional): Filter by supplier
- `status` (string, optional): Filter by status

**Example Request:**
```
GET /api/v1/invoices?invoice_type=PURCHASE&party_id=supplier-uuid-1&status=submitted
```

**Success Response (200 OK):**
```json
{
  "items": [
    {
      "id": "invoice-uuid-here",
      "invoice_type": "PURCHASE",
      "party_id": "supplier-uuid-1",
      "status": "submitted",
      "grand_total": 4141.50,
      "outstanding_balance": 4141.50,
      "created_at": "2024-02-21T10:00:00Z"
    }
  ],
  "total": 5,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

#### Submit Purchase Invoice

Changes invoice status from DRAFT to SUBMITTED.

**Endpoint:** `POST /api/v1/invoices/{id}/submit`

**Request Body:** None

**Success Response (200 OK):**
```json
{
  "id": "invoice-uuid-here",
  "status": "submitted",
  "updated_at": "2024-02-21T11:00:00Z"
}
```

---

## Payment Made API

Payment Made records outbound payments to suppliers. Uses the existing Payment API with PAY type.

### Endpoints

#### Create Payment Made

Creates a payment to a supplier for a Purchase Invoice. Automatically reduces the invoice outstanding balance.

**Endpoint:** `POST /api/v1/payments`

**Request Body:**
```json
{
  "payment_type": "PAY",
  "reference_type": "PURCHASE_INVOICE",
  "reference_id": "invoice-uuid-here",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-1",
  "amount": 4141.50,
  "payment_date": "2024-02-25",
  "payment_method": "BANK_TRANSFER",
  "notes": "Payment for PO-2024-001"
}
```


**Success Response (201 Created):**
```json
{
  "id": "payment-uuid-here",
  "organization_id": "org-uuid-here",
  "payment_type": "PAY",
  "reference_type": "PURCHASE_INVOICE",
  "reference_id": "invoice-uuid-here",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-1",
  "amount": 4141.50,
  "payment_date": "2024-02-25",
  "payment_method": "BANK_TRANSFER",
  "status": "completed",
  "notes": "Payment for PO-2024-001",
  "created_by": "user-uuid-here",
  "created_at": "2024-02-25T09:00:00Z",
  "updated_at": "2024-02-25T09:00:00Z"
}
```

**Side Effects:**
1. Invoice outstanding balance updated: 4141.50 → 0.00
2. Invoice status updated: SUBMITTED → PAID

**Error Responses:**

*Purchase Invoice Not Found (404):*
```json
{
  "detail": {
    "message": "Purchase Invoice not found",
    "status_code": 404,
    "code": "INVOICE_NOT_FOUND",
    "entity_type": "INVOICE",
    "entity_id": "invoice-uuid-here"
  }
}
```

*No Outstanding Balance (409):*
```json
{
  "detail": {
    "message": "Invoice has no outstanding balance",
    "status_code": 409,
    "code": "NO_OUTSTANDING_BALANCE",
    "invoice_id": "invoice-uuid-here",
    "outstanding_balance": 0.00
  }
}
```

*Payment Exceeds Balance (400):*
```json
{
  "detail": {
    "message": "Payment amount exceeds outstanding balance",
    "status_code": 400,
    "code": "PAYMENT_EXCEEDS_BALANCE",
    "payment_amount": 5000.00,
    "outstanding_balance": 4141.50
  }
}
```

---

#### Get Payment by ID

Retrieves a specific Payment.

**Endpoint:** `GET /api/v1/payments/{id}`

**Success Response (200 OK):**
```json
{
  "id": "payment-uuid-here",
  "payment_type": "PAY",
  "reference_type": "PURCHASE_INVOICE",
  "reference_id": "invoice-uuid-here",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-1",
  "amount": 4141.50,
  "payment_date": "2024-02-25",
  "payment_method": "BANK_TRANSFER",
  "status": "completed",
  "created_at": "2024-02-25T09:00:00Z"
}
```

---

#### List Payments

Retrieves a paginated list of Payments.

**Endpoint:** `GET /api/v1/payments`

**Query Parameters:**
- `page` (integer, default: 1)
- `page_size` (integer, default: 20, max: 100)
- `payment_type` (string, optional): Filter by type (PAY)
- `party_id` (UUID, optional): Filter by supplier
- `status` (string, optional): Filter by status

**Example Request:**
```
GET /api/v1/payments?payment_type=PAY&party_id=supplier-uuid-1
```

**Success Response (200 OK):**
```json
{
  "items": [
    {
      "id": "payment-uuid-here",
      "payment_type": "PAY",
      "party_id": "supplier-uuid-1",
      "amount": 4141.50,
      "payment_date": "2024-02-25",
      "status": "completed",
      "created_at": "2024-02-25T09:00:00Z"
    }
  ],
  "total": 3,
  "page": 1,
  "page_size": 20,
  "total_pages": 1
}
```

---

## Error Responses

All API endpoints follow consistent error response patterns.

### Error Response Structure

```json
{
  "detail": {
    "message": "Human-readable error message",
    "status_code": 400,
    "code": "ERROR_CODE",
    "additional_field": "Additional context"
  }
}
```

### HTTP Status Codes

| Status Code | Description | When Used |
|-------------|-------------|-----------|
| 200 | OK | Successful GET, PUT, POST (status transitions) |
| 201 | Created | Successful POST (resource creation) |
| 204 | No Content | Successful DELETE |
| 400 | Bad Request | Validation errors, invalid input |
| 401 | Unauthorized | Missing or invalid authentication token |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | State conflicts, invalid transitions |
| 422 | Unprocessable Entity | Business rule violations |
| 500 | Internal Server Error | Unexpected server errors |
| 502 | Bad Gateway | External API integration failures |
| 503 | Service Unavailable | Service temporarily unavailable |


### Common Error Types

#### Validation Error (400)

Returned when input data fails validation rules.

```json
{
  "detail": {
    "message": "Validation failed",
    "status_code": 400,
    "code": "VALIDATION_ERROR",
    "errors": [
      {
        "field": "line_items[0].quantity",
        "reason": "Quantity must be greater than zero"
      },
      {
        "field": "required_date",
        "reason": "Required date cannot be in the past"
      }
    ]
  }
}
```

**Common Validation Errors:**
- Negative or zero quantities
- Missing required fields
- Invalid date formats
- Invalid UUID formats
- Empty line items array

---

#### Not Found Error (404)

Returned when a referenced entity doesn't exist.

```json
{
  "detail": {
    "message": "Material Request not found",
    "status_code": 404,
    "code": "MATERIAL_REQUEST_NOT_FOUND",
    "entity_type": "MATERIAL_REQUEST",
    "entity_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

**Common Not Found Errors:**
- `MATERIAL_REQUEST_NOT_FOUND`
- `RFQ_NOT_FOUND`
- `PURCHASE_ORDER_NOT_FOUND`
- `SUPPLIER_NOT_FOUND`
- `ITEM_NOT_FOUND`
- `INVOICE_NOT_FOUND`

---

#### State Conflict Error (409)

Returned when an operation conflicts with the current document state.

```json
{
  "detail": {
    "message": "Cannot update Material Request in SUBMITTED status",
    "status_code": 409,
    "code": "STATE_CONFLICT",
    "current_state": "submitted",
    "allowed_states": ["draft"]
  }
}
```

**Common State Conflicts:**
- Attempting to modify a submitted document
- Invalid status transitions
- Deleting a non-draft document
- Creating receipt for cancelled Purchase Order

---

#### Invalid Transition Error (409)

Returned when a status transition is not allowed by the state machine.

```json
{
  "detail": {
    "message": "Invalid status transition from CANCELLED to SUBMITTED",
    "status_code": 409,
    "code": "INVALID_TRANSITION",
    "current_state": "cancelled",
    "requested_state": "submitted",
    "allowed_transitions": []
  }
}
```

---

#### Integration Error (502/503)

Returned when external API calls fail.

```json
{
  "detail": {
    "message": "Failed to validate supplier",
    "status_code": 502,
    "code": "INTEGRATION_ERROR",
    "service": "Suppliers API",
    "details": "Connection timeout after 30 seconds"
  }
}
```

**Common Integration Errors:**
- Suppliers API unavailable
- Purchase Receipt API timeout
- Invoice API returns error
- Payment API connection refused

---

#### Authentication Error (401)

Returned when authentication token is missing or invalid.

```json
{
  "detail": {
    "message": "Authentication required",
    "status_code": 401,
    "code": "UNAUTHORIZED"
  }
}
```

---

#### Permission Error (403)

Returned when user lacks required permissions.

```json
{
  "detail": {
    "message": "Insufficient permissions",
    "status_code": 403,
    "code": "FORBIDDEN",
    "required_permission": "material_request.create"
  }
}
```

**Required Permissions:**
- `material_request.create`, `material_request.read`, `material_request.update`, `material_request.delete`
- `rfq.create`, `rfq.read`, `rfq.update`, `rfq.delete`
- `purchase_order.create`, `purchase_order.read`, `purchase_order.update`, `purchase_order.delete`
- `purchase_receipt.create`, `purchase_receipt.read`
- `invoice.create`, `invoice.read`, `invoice.update`
- `payment.create`, `payment.read`


---

## Workflow Sequences

This section documents the complete workflow sequences for common procurement scenarios.

### Complete Procure-to-Pay Workflow

This is the full workflow from internal demand identification through supplier payment.

```
Material Request → RFQ → Purchase Order → Receipt Note → Purchase Invoice → Payment Made
```

#### Step 1: Create and Submit Material Request

**Action:** Warehouse manager creates a Material Request for needed items.

```bash
# Create Material Request
POST /api/v1/material-requests
{
  "notes": "Office supplies for Q1 2024",
  "line_items": [
    {
      "item_id": "item-uuid-1",
      "quantity": 50,
      "required_date": "2024-03-15",
      "description": "Ergonomic office chairs"
    }
  ]
}

# Response: Material Request created with status "draft"
# Save material_request_id for next step

# Submit Material Request
POST /api/v1/material-requests/{material_request_id}/submit

# Response: Status changed to "submitted"
```

---

#### Step 2: Create RFQ and Send to Suppliers

**Action:** Procurement officer creates RFQ from Material Request and sends to multiple suppliers.

```bash
# Create RFQ from Material Request
POST /api/v1/rfqs
{
  "material_request_id": "{material_request_id}",
  "closing_date": "2024-03-30",
  "supplier_ids": [
    "supplier-uuid-1",
    "supplier-uuid-2",
    "supplier-uuid-3"
  ]
}

# Response: RFQ created with status "draft", line items copied from Material Request
# Save rfq_id and rfq_line_id for next steps

# Send RFQ to suppliers
POST /api/v1/rfqs/{rfq_id}/send

# Response: Status changed to "sent"
```

---

#### Step 3: Record Supplier Quotes

**Action:** Suppliers respond with quotes. Procurement officer records each quote.

```bash
# Record quote from Supplier 1
POST /api/v1/rfqs/{rfq_id}/quotes
{
  "rfq_line_id": "{rfq_line_id}",
  "supplier_id": "supplier-uuid-1",
  "quoted_price": 125.50,
  "quoted_delivery_date": "2024-03-20",
  "supplier_notes": "Best quality materials"
}

# Record quote from Supplier 2
POST /api/v1/rfqs/{rfq_id}/quotes
{
  "rfq_line_id": "{rfq_line_id}",
  "supplier_id": "supplier-uuid-2",
  "quoted_price": 118.75,
  "quoted_delivery_date": "2024-03-25",
  "supplier_notes": "Competitive pricing"
}

# Record quote from Supplier 3
POST /api/v1/rfqs/{rfq_id}/quotes
{
  "rfq_line_id": "{rfq_line_id}",
  "supplier_id": "supplier-uuid-3",
  "quoted_price": 130.00,
  "quoted_delivery_date": "2024-03-18",
  "supplier_notes": "Fastest delivery"
}

# Response: RFQ status automatically updated to "fully_responded"
```

---

#### Step 4: Create and Submit Purchase Order

**Action:** Procurement officer selects best quote and creates Purchase Order.

```bash
# Create Purchase Order from selected RFQ quote
POST /api/v1/purchase-orders
{
  "rfq_id": "{rfq_id}",
  "supplier_id": "supplier-uuid-2",
  "tax_rate": 0.10,
  "discount_amount": 0,
  "line_items": [
    {
      "rfq_line_id": "{rfq_line_id}",
      "item_id": "item-uuid-1",
      "quantity": 50,
      "unit_price": 118.75
    }
  ]
}

# Response: Purchase Order created with calculated totals
# - Subtotal: 5,937.50
# - Tax (10%): 593.75
# - Grand Total: 6,531.25
# Save purchase_order_id and purchase_order_line_id

# Submit Purchase Order
POST /api/v1/purchase-orders/{purchase_order_id}/submit

# Response: Status changed to "submitted"
```

---

#### Step 5: Record Goods Receipt

**Action:** Warehouse operator receives goods and creates Receipt Note.

```bash
# Create Receipt Note (partial receipt - 30 out of 50)
POST /api/v1/purchase-receipts
{
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "{purchase_order_id}",
  "received_date": "2024-03-20",
  "line_items": [
    {
      "purchase_order_line_id": "{purchase_order_line_id}",
      "item_id": "item-uuid-1",
      "quantity": 30
    }
  ]
}

# Response: Receipt Note created
# Side effects:
# - Purchase Order status: "submitted" → "partially_received"
# - Purchase Order line received_quantity: 0 → 30
# - Stock incremented by 30 for item-uuid-1

# Create second Receipt Note (remaining 20)
POST /api/v1/purchase-receipts
{
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "{purchase_order_id}",
  "received_date": "2024-03-22",
  "line_items": [
    {
      "purchase_order_line_id": "{purchase_order_line_id}",
      "item_id": "item-uuid-1",
      "quantity": 20
    }
  ]
}

# Response: Receipt Note created
# Side effects:
# - Purchase Order status: "partially_received" → "fully_received"
# - Purchase Order line received_quantity: 30 → 50
# - Stock incremented by 20 for item-uuid-1
```


---

#### Step 6: Record Purchase Invoice

**Action:** Accounts payable clerk receives supplier invoice and records it.

```bash
# Create Purchase Invoice
POST /api/v1/invoices
{
  "invoice_type": "PURCHASE",
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "{purchase_order_id}",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-2",
  "invoice_date": "2024-03-23",
  "due_date": "2024-04-23",
  "line_items": [
    {
      "purchase_order_line_id": "{purchase_order_line_id}",
      "item_id": "item-uuid-1",
      "quantity": 50,
      "unit_price": 118.75
    }
  ]
}

# Response: Purchase Invoice created with calculated totals
# - Subtotal: 5,937.50
# - Tax: 593.75
# - Grand Total: 6,531.25
# - Outstanding Balance: 6,531.25
# Save invoice_id

# Submit Purchase Invoice
POST /api/v1/invoices/{invoice_id}/submit

# Response: Status changed to "submitted"
```

---

#### Step 7: Make Payment to Supplier

**Action:** Accounts payable clerk processes payment to supplier.

```bash
# Create Payment Made
POST /api/v1/payments
{
  "payment_type": "PAY",
  "reference_type": "PURCHASE_INVOICE",
  "reference_id": "{invoice_id}",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-2",
  "amount": 6531.25,
  "payment_date": "2024-04-15",
  "payment_method": "BANK_TRANSFER",
  "notes": "Payment for PO-2024-001"
}

# Response: Payment created
# Side effects:
# - Invoice outstanding_balance: 6,531.25 → 0.00
# - Invoice status: "submitted" → "paid"
```

---

#### Step 8: Close Purchase Order

**Action:** Procurement officer closes the completed Purchase Order.

```bash
# Close Purchase Order
POST /api/v1/purchase-orders/{purchase_order_id}/close

# Response: Status changed to "closed"
```

**Workflow Complete!** The procurement cycle is now finished.

---

### Partial Payment Workflow

This workflow demonstrates handling partial payments for an invoice.

```bash
# Step 1: Create and submit Purchase Invoice (as shown above)
# Invoice grand_total: 6,531.25
# Invoice outstanding_balance: 6,531.25

# Step 2: Make first partial payment
POST /api/v1/payments
{
  "payment_type": "PAY",
  "reference_type": "PURCHASE_INVOICE",
  "reference_id": "{invoice_id}",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-2",
  "amount": 3000.00,
  "payment_date": "2024-04-01",
  "payment_method": "BANK_TRANSFER",
  "notes": "Partial payment 1 of 2"
}

# Response: Payment created
# Side effects:
# - Invoice outstanding_balance: 6,531.25 → 3,531.25
# - Invoice status remains "submitted" (not fully paid)

# Step 3: Make second partial payment
POST /api/v1/payments
{
  "payment_type": "PAY",
  "reference_type": "PURCHASE_INVOICE",
  "reference_id": "{invoice_id}",
  "party_type": "SUPPLIER",
  "party_id": "supplier-uuid-2",
  "amount": 3531.25,
  "payment_date": "2024-04-15",
  "payment_method": "BANK_TRANSFER",
  "notes": "Final payment"
}

# Response: Payment created
# Side effects:
# - Invoice outstanding_balance: 3,531.25 → 0.00
# - Invoice status: "submitted" → "paid"
```

---

### Emergency Cancellation Workflow

This workflow demonstrates cancelling a Purchase Order before receipt.

```bash
# Step 1: Purchase Order is submitted
# Status: "submitted"

# Step 2: Need to cancel due to supplier issue
POST /api/v1/purchase-orders/{purchase_order_id}/cancel

# Response: Status changed to "cancelled"

# Note: Cannot cancel if any goods have been received
# If status is "partially_received" or "fully_received", cancellation will fail
```

---

### Quote Comparison Workflow

This workflow demonstrates comparing quotes from multiple suppliers.

```bash
# Step 1: Create and send RFQ to 3 suppliers (as shown above)

# Step 2: Record all quotes
# (Record quotes from all 3 suppliers as shown above)

# Step 3: Retrieve RFQ with all quotes for comparison
GET /api/v1/rfqs/{rfq_id}

# Response includes all quotes:
# Supplier 1: $125.50, delivery 2024-03-20
# Supplier 2: $118.75, delivery 2024-03-25 (BEST PRICE)
# Supplier 3: $130.00, delivery 2024-03-18 (FASTEST)

# Step 4: Decision matrix
# - Lowest price: Supplier 2 ($118.75)
# - Fastest delivery: Supplier 3 (2024-03-18)
# - Best value: Supplier 2 (good price, reasonable delivery)

# Step 5: Create Purchase Order with selected supplier
# (Create PO with Supplier 2 as shown above)
```


---

### Three-Way Matching Workflow

This workflow demonstrates the three-way matching validation between Purchase Order, Receipt Note, and Purchase Invoice.

```bash
# Step 1: Purchase Order created for 100 units
POST /api/v1/purchase-orders
{
  "line_items": [
    {
      "item_id": "item-uuid-1",
      "quantity": 100,
      "unit_price": 50.00
    }
  ]
}
# PO Line: quantity = 100

# Step 2: Partial receipt of 60 units
POST /api/v1/purchase-receipts
{
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "{purchase_order_id}",
  "line_items": [
    {
      "purchase_order_line_id": "{po_line_id}",
      "item_id": "item-uuid-1",
      "quantity": 60
    }
  ]
}
# PO Line: received_quantity = 60

# Step 3: Attempt to invoice for 100 units (WILL FAIL)
POST /api/v1/invoices
{
  "invoice_type": "PURCHASE",
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "{purchase_order_id}",
  "line_items": [
    {
      "purchase_order_line_id": "{po_line_id}",
      "item_id": "item-uuid-1",
      "quantity": 100,
      "unit_price": 50.00
    }
  ]
}

# Response: 400 Bad Request
# {
#   "detail": {
#     "message": "Invoiced quantity exceeds received quantity",
#     "code": "THREE_WAY_MATCHING_FAILED",
#     "invoiced_quantity": 100,
#     "received_quantity": 60
#   }
# }

# Step 4: Invoice for received quantity only (WILL SUCCEED)
POST /api/v1/invoices
{
  "invoice_type": "PURCHASE",
  "reference_type": "PURCHASE_ORDER",
  "reference_id": "{purchase_order_id}",
  "line_items": [
    {
      "purchase_order_line_id": "{po_line_id}",
      "item_id": "item-uuid-1",
      "quantity": 60,
      "unit_price": 50.00
    }
  ]
}

# Response: 201 Created
# Invoice created for 60 units (matching received quantity)
```

---

### Status Transition Logging

All status transitions are automatically logged for audit purposes.

**Logged Information:**
- Entity type (MATERIAL_REQUEST, RFQ, PURCHASE_ORDER)
- Entity ID
- Previous status
- New status
- User ID who made the change
- Timestamp

**Example Status Transition Log:**

```json
{
  "id": "transition-uuid-here",
  "entity_type": "PURCHASE_ORDER",
  "entity_id": "po-uuid-here",
  "previous_status": "draft",
  "new_status": "submitted",
  "user_id": "user-uuid-here",
  "transitioned_at": "2024-02-17T12:00:00Z"
}
```

**Querying Status Transitions:**

```bash
# Get all transitions for a specific Purchase Order
GET /api/v1/status-transitions?entity_type=PURCHASE_ORDER&entity_id={po_id}

# Response: Array of all status transitions for that Purchase Order
```

---

## Best Practices

### 1. Always Submit Before Proceeding

Documents must be submitted before they can be used in the next workflow step:
- Submit Material Request before creating RFQ
- Send RFQ before recording quotes
- Submit Purchase Order before creating Receipt Note

### 2. Handle Partial Receipts

Goods may arrive in multiple shipments:
- Create separate Receipt Notes for each shipment
- Purchase Order status automatically updates to PARTIALLY_RECEIVED
- When all items received, status updates to FULLY_RECEIVED

### 3. Respect Three-Way Matching

Always ensure invoiced quantities don't exceed received quantities:
- Check received_quantity on Purchase Order lines
- Invoice only for what has been received
- Create additional invoices after receiving remaining goods

### 4. Use Pagination for Large Lists

When retrieving lists of documents:
- Use reasonable page_size (20-50 items)
- Implement pagination in your UI
- Use filtering to narrow results

### 5. Handle Errors Gracefully

API errors provide detailed information:
- Check the `code` field for programmatic error handling
- Display the `message` field to users
- Use `errors` array for field-level validation feedback

### 6. Validate Before Submission

Before submitting documents:
- Ensure all required fields are filled
- Validate quantities are positive
- Check dates are in the future
- Verify referenced entities exist

### 7. Monitor Status Transitions

Track document progress through the workflow:
- Query status transition logs for audit trails
- Display status history to users
- Alert on unexpected status changes

### 8. Use Filters Effectively

Narrow down results using filters:
- Filter by status to find documents needing action
- Filter by supplier to track supplier-specific orders
- Filter by date ranges for reporting

---

## API Versioning

The API uses URL-based versioning:

**Current Version:** `v1`

**Base URL:** `http://localhost:8001/api/v1`

Future versions will be introduced as `/api/v2`, `/api/v3`, etc., with backward compatibility maintained for at least one major version.

---

## Rate Limiting

API requests are rate-limited to ensure fair usage:

**Limits:**
- 1000 requests per hour per user
- 100 requests per minute per user

**Rate Limit Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1708531200
```

When rate limit is exceeded:
```json
{
  "detail": {
    "message": "Rate limit exceeded",
    "status_code": 429,
    "code": "RATE_LIMIT_EXCEEDED",
    "retry_after": 3600
  }
}
```

---

## Support and Resources

**Documentation:**
- Design Document: `.kiro/specs/sourcing-flow/design.md`
- Requirements: `.kiro/specs/sourcing-flow/requirements.md`
- Tasks: `.kiro/specs/sourcing-flow/tasks.md`

**Postman Collections:**
- Material Request API: `Material_Request_API.postman_collection.json`
- RFQ API: `RFQ_API.postman_collection.json`
- Receipt Note API: `Receipt_Note_API.postman_collection.json`

**Testing Guides:**
- Material Request: `MATERIAL_REQUEST_API_TESTING.md`
- RFQ: `RFQ_API_TESTING.md`
- Receipt Note: `RECEIPT_NOTE_API_TESTING.md`

**Contact:**
For issues, questions, or feature requests, please contact the development team or create an issue in the project repository.

---

## Changelog

### Version 1.0.0 (2024-02-14)
- Initial release of Sourcing Flow API
- Material Request API
- RFQ API
- Purchase Order API
- Integration with existing Receipt Note, Invoice, and Payment APIs
- Complete procure-to-pay workflow
- Transaction Engine for automatic calculations
- State machine-driven status transitions
- Three-way matching validation
- Status transition logging

---

**End of Documentation**

