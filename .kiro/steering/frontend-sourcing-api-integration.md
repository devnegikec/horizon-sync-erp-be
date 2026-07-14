---
inclusion: manual
---

# Frontend Sourcing API Integration Guide

Complete API reference for integrating the Procure-to-Pay sourcing workflow into the frontend.

## Base URL & Auth

```
Base: http://localhost:8001/api/v1
Auth: Authorization: Bearer {token}
```

All endpoints require a valid Bearer token. Token is stored in `localStorage.getItem("token")`.

## Complete Workflow

```
Material Request → RFQ → Purchase Order → Receipt → Invoice → Payment
   (create)     (convert)  (convert)     (create)   (create)   (create)
```

Each step links to the previous via `reference_type` + `reference_id`.

---

## 1. Material Requests API

### Statuses: `draft` → `submitted` → `partially_quoted` → `fully_quoted` | `cancelled`

### Create Material Request

```
POST /material-requests
```

```json
{
  "type": "purchase",
  "priority": "medium",
  "department": "Production",
  "target_warehouse_id": "uuid | null",
  "requested_by": "uuid | null",
  "notes": "string | null",
  "request_no": "string | null (auto-generated as MR-YYYY-NNNN if omitted)",
  "line_items": [
    {
      "item_id": "uuid (required)",
      "quantity": 10,
      "uom": "Kgs | Boxes | Pieces | null",
      "required_date": "2026-03-15",
      "description": "string | null",
      "estimated_unit_cost": 125.5,
      "requested_for": "Employee Name | null",
      "requested_for_department": "Department | null"
    }
  ]
}
```

Response: `MaterialRequestResponse` (201)

### List Material Requests

```
GET /material-requests?page=1&page_size=20&status=submitted&sort_by=created_at&sort_order=desc&search=keyword
```

Response:

```json
{
  "material_requests": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "request_no": "MR-2026-0001",
      "type": "purchase | transfer | issue",
      "priority": "low | medium | high | urgent",
      "status": "draft | submitted | partially_quoted | fully_quoted | cancelled",
      "department": "string | null",
      "created_at": "datetime",
      "created_by": "uuid | null",
      "line_items_count": 3
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 45,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

### Get Material Request

```
GET /material-requests/{id}
```

Response includes full `line_items` array with all fields.

### Update Material Request (DRAFT only)

```
PUT /material-requests/{id}
```

Same body as create, all fields optional. Returns 400 if status is not `draft`.

### Submit Material Request

```
POST /material-requests/{id}/submit
```

No body. Changes status `draft` → `submitted`. Returns updated MR.

### Cancel Material Request

```
POST /material-requests/{id}/cancel
```

No body. Returns updated MR.

### Delete Material Request (DRAFT only)

```
DELETE /material-requests/{id}
```

Returns 204.

### Get Workflow Status (NEW)

```
GET /material-requests/{id}/workflow
```

Traces the entire sourcing chain from this MR through to payments.

Response:

```json
{
  "material_request": { "...full MR response..." },
  "rfqs": [
    {
      "id": "uuid",
      "status": "draft | sent | partially_responded | fully_responded | closed",
      "closing_date": "2026-03-30",
      "created_at": "datetime"
    }
  ],
  "purchase_orders": [
    {
      "id": "uuid",
      "status": "draft | submitted | partially_received | fully_received | closed | cancelled",
      "party_id": "uuid (supplier)",
      "grand_total": 5000.00,
      "created_at": "datetime"
    }
  ],
  "receipts": [
    {
      "id": "uuid",
      "purchase_receipt_no": "PR-001",
      "receipt_date": "datetime",
      "status": "string"
    }
  ],
  "invoices": [
    {
      "id": "uuid",
      "invoice_no": "INV-001",
      "status": "string",
      "grand_total": 5000.00
    }
  ],
  "payments": [
    {
      "id": "uuid",
      "payment_no": "PAY-001",
      "amount": 5000.00,
      "status": "string",
      "posting_date": "datetime"
    }
  ]
}
```

Use this endpoint to power the `WorkflowTimeline` component.

---

## 2. RFQ (Request for Quotation) API

### Statuses: `draft` → `sent` → `partially_responded` → `fully_responded` → `closed`

### Create RFQ from Material Request (Conversion)

```
POST /rfqs
```

```json
{
  "material_request_id": "uuid (required for conversion)",
  "closing_date": "2026-03-30",
  "supplier_ids": ["supplier-uuid-1", "supplier-uuid-2"]
}
```

When `material_request_id` is provided:

- Line items are auto-copied from the Material Request
- `reference_type` is set to `MATERIAL_REQUEST`
- MR status updates to `partially_quoted`
- No need to send `line_items` in the body

Response: `RFQResponse` (201) with `line_items`, `suppliers` arrays.

### List RFQs (with Material Request filter)

```
GET /rfqs?page=1&page_size=20&status=sent&material_request_id={uuid}&sort_by=created_at&sort_order=desc
```

The `material_request_id` query param filters RFQs linked to a specific MR. Use this to show "RFQs created from this Material Request" on the MR detail page.

Response:

```json
{
  "rfqs": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "material_request_id": "uuid | null",
      "status": "string",
      "closing_date": "2026-03-30",
      "created_at": "datetime",
      "created_by": "uuid | null",
      "line_items_count": 3,
      "suppliers_count": 2
    }
  ],
  "pagination": { "..." }
}
```

### Get RFQ Detail

```
GET /rfqs/{id}
```

Response includes nested `line_items[].quotes[]` and `suppliers[]`.

```json
{
  "id": "uuid",
  "material_request_id": "uuid | null",
  "reference_type": "MATERIAL_REQUEST | null",
  "reference_id": "uuid | null",
  "status": "sent",
  "closing_date": "2026-03-30",
  "line_items": [
    {
      "id": "uuid",
      "item_id": "uuid",
      "quantity": 10,
      "required_date": "2026-03-15",
      "description": "string | null",
      "quotes": [
        {
          "id": "uuid",
          "rfq_line_id": "uuid",
          "supplier_id": "uuid",
          "quoted_price": 125.5,
          "quoted_delivery_date": "2026-03-20",
          "supplier_notes": "string | null",
          "created_at": "datetime"
        }
      ]
    }
  ],
  "suppliers": [
    {
      "id": "uuid",
      "supplier_id": "uuid",
      "rfq_id": "uuid",
      "created_at": "datetime"
    }
  ]
}
```

### Send RFQ to Suppliers

```
POST /rfqs/{id}/send
```

No body. Changes status `draft` → `sent`. Validates line items and suppliers exist.

### Record Supplier Quote (NEW)

```
POST /rfqs/{id}/quotes
```

```json
{
  "rfq_line_id": "uuid",
  "supplier_id": "uuid",
  "quoted_price": 125.5,
  "quoted_delivery_date": "2026-03-20",
  "supplier_notes": "Bulk discount available"
}
```

Backend auto-updates RFQ status:

- If all lines have at least one quote from all suppliers → `fully_responded`
- If some lines have quotes → `partially_responded`
- Also updates the parent MR status (`partially_quoted` / `fully_quoted`)

Returns full `RFQResponse` with updated quotes.

### Update RFQ (DRAFT only)

```
PUT /rfqs/{id}
```

```json
{
  "closing_date": "2026-04-15",
  "line_items": [
    { "item_id": "uuid", "quantity": 5, "required_date": "2026-04-01" }
  ],
  "supplier_ids": ["uuid-1", "uuid-2"]
}
```

### Close RFQ

```
POST /rfqs/{id}/close
```

No body. Changes status to `closed`.

### Delete RFQ (DRAFT only)

```
DELETE /rfqs/{id}
```

Returns 204.

---

## 3. Purchase Orders API

### Statuses: `draft` → `submitted` → `partially_received` → `fully_received` → `closed` | `cancelled`

### Create Purchase Order from RFQ (Conversion)

```
POST /purchase-orders
```

```json
{
  "rfq_id": "uuid (triggers from-RFQ flow)",
  "party_id": "uuid (supplier_id - required)",
  "tax_rate": 0.18,
  "discount_amount": 100.0,
  "line_items": [
    {
      "item_id": "uuid",
      "quantity": 10,
      "unit_price": 125.5
    }
  ]
}
```

When `rfq_id` is provided:

- `reference_type` is set to `RFQ`
- Totals are calculated by the Transaction Engine (subtotal, tax_amount, grand_total)
- The linked RFQ status is auto-set to `closed`
- `line_items` must include the quoted prices from the selected supplier

Note: `tax_rate` is a decimal between 0 and 1 (e.g., 0.18 = 18%).

### Create Standalone Purchase Order

Same endpoint, omit `rfq_id`:

```json
{
  "party_id": "uuid (supplier_id)",
  "tax_rate": 0.18,
  "discount_amount": 0,
  "line_items": [{ "item_id": "uuid", "quantity": 10, "unit_price": 125.5 }]
}
```

### List Purchase Orders (with RFQ filter)

```
GET /purchase-orders?page=1&page_size=20&status=submitted&rfq_id={uuid}&sort_by=created_at&sort_order=desc
```

The `rfq_id` query param filters POs linked to a specific RFQ. Use this to show "Purchase Orders created from this RFQ" on the RFQ detail page.

Response:

```json
{
  "purchase_orders": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "rfq_id": "uuid | null",
      "party_id": "uuid",
      "status": "string",
      "grand_total": 5000.00,
      "created_at": "datetime",
      "created_by": "uuid | null",
      "line_items_count": 3
    }
  ],
  "pagination": { "..." }
}
```

### Get Purchase Order Detail

```
GET /purchase-orders/{id}
```

Response:

```json
{
  "id": "uuid",
  "rfq_id": "uuid | null",
  "reference_type": "RFQ | null",
  "reference_id": "uuid | null",
  "party_type": "SUPPLIER",
  "party_id": "uuid",
  "status": "draft",
  "subtotal": 1255.0,
  "tax_amount": 225.9,
  "tax_rate": 0.18,
  "discount_amount": 100.0,
  "grand_total": 1380.9,
  "line_items": [
    {
      "id": "uuid",
      "item_id": "uuid",
      "quantity": 10,
      "unit_price": 125.5,
      "line_total": 1255.0,
      "received_quantity": 0
    }
  ]
}
```

### Submit Purchase Order

```
POST /purchase-orders/{id}/submit
```

No body. `draft` → `submitted`. Locked after this.

### Cancel Purchase Order

```
POST /purchase-orders/{id}/cancel
```

No body. Works from `draft` or `submitted`.

### Close Purchase Order

```
POST /purchase-orders/{id}/close
```

No body. Only from `fully_received`.

### Delete Purchase Order (DRAFT only)

```
DELETE /purchase-orders/{id}
```

Returns 204.

---

## 4. Supporting APIs (for dropdowns)

### List Suppliers

```
GET /suppliers?page=1&page_size=100
```

Use for supplier selection in RFQ creation and PO creation.

### List Items

```
GET /items?page=1&page_size=100
```

Use for item selection in Material Request line items.

### Items Picker (search-optimized)

```
GET /items/picker?search=keyword&page_size=20
```

Use for autocomplete/search inputs when selecting items.

---

## 5. Frontend Service Layer

### Axios Instance Setup

```typescript
import axios from "axios";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

const apiClient = axios.create({
  baseURL: `${API_BASE_URL}/api/v1`,
  headers: { "Content-Type": "application/json" },
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

export default apiClient;
```

### Material Request Service

```typescript
import apiClient from "./apiClient";

export const materialRequestService = {
  create: (data: any) => apiClient.post("/material-requests", data),
  list: (params?: any) => apiClient.get("/material-requests", { params }),
  getById: (id: string) => apiClient.get(`/material-requests/${id}`),
  update: (id: string, data: any) =>
    apiClient.put(`/material-requests/${id}`, data),
  submit: (id: string) => apiClient.post(`/material-requests/${id}/submit`),
  cancel: (id: string) => apiClient.post(`/material-requests/${id}/cancel`),
  delete: (id: string) => apiClient.delete(`/material-requests/${id}`),
  getWorkflow: (id: string) =>
    apiClient.get(`/material-requests/${id}/workflow`),
};
```

### RFQ Service

```typescript
export const rfqService = {
  createFromMR: (data: {
    material_request_id: string;
    closing_date: string;
    supplier_ids: string[];
  }) => apiClient.post("/rfqs", data),

  list: (params?: any) => apiClient.get("/rfqs", { params }),
  getById: (id: string) => apiClient.get(`/rfqs/${id}`),
  update: (id: string, data: any) => apiClient.put(`/rfqs/${id}`, data),
  send: (id: string) => apiClient.post(`/rfqs/${id}/send`),
  delete: (id: string) => apiClient.delete(`/rfqs/${id}`),
  close: (id: string) => apiClient.post(`/rfqs/${id}/close`),

  recordQuote: (
    rfqId: string,
    data: {
      rfq_line_id: string;
      supplier_id: string;
      quoted_price: number;
      quoted_delivery_date: string;
      supplier_notes?: string;
    },
  ) => apiClient.post(`/rfqs/${rfqId}/quotes`, data),

  listByMaterialRequest: (mrId: string, params?: any) =>
    apiClient.get("/rfqs", {
      params: { material_request_id: mrId, ...params },
    }),
};
```

### Purchase Order Service

```typescript
export const purchaseOrderService = {
  createFromRFQ: (data: {
    rfq_id: string;
    party_id: string;
    line_items: { item_id: string; quantity: number; unit_price: number }[];
    tax_rate?: number;
    discount_amount?: number;
  }) => apiClient.post("/purchase-orders", data),

  createStandalone: (data: {
    party_id: string;
    line_items: { item_id: string; quantity: number; unit_price: number }[];
    tax_rate?: number;
    discount_amount?: number;
  }) => apiClient.post("/purchase-orders", data),

  list: (params?: any) => apiClient.get("/purchase-orders", { params }),
  getById: (id: string) => apiClient.get(`/purchase-orders/${id}`),
  update: (id: string, data: any) =>
    apiClient.put(`/purchase-orders/${id}`, data),
  submit: (id: string) => apiClient.post(`/purchase-orders/${id}/submit`),
  cancel: (id: string) => apiClient.post(`/purchase-orders/${id}/cancel`),
  close: (id: string) => apiClient.post(`/purchase-orders/${id}/close`),
  delete: (id: string) => apiClient.delete(`/purchase-orders/${id}`),

  listByRFQ: (rfqId: string, params?: any) =>
    apiClient.get("/purchase-orders", { params: { rfq_id: rfqId, ...params } }),
};
```

---

## 6. Conversion Flow Logic

### Material Request → RFQ

When user clicks "Convert to RFQ" on a submitted MR:

1. Fetch suppliers list: `GET /suppliers?page_size=100`
2. Show dialog: select suppliers + closing date
3. Call: `POST /rfqs` with `{ material_request_id, supplier_ids, closing_date }`
4. Line items are auto-copied. No need to send them.
5. MR status auto-updates to `partially_quoted`
6. Navigate to the new RFQ detail page

Only show the button when `materialRequest.status === "submitted"`.

### RFQ → Purchase Order

When user clicks "Convert to PO" on an RFQ with quotes:

1. Get RFQ detail: `GET /rfqs/{id}` (includes `line_items[].quotes[]`)
2. Show dialog: select supplier, review their quoted prices
3. Build `line_items` from the selected supplier's quotes:
   ```typescript
   const lineItems = rfq.line_items
     .map((line) => {
       const quote = line.quotes.find(
         (q) => q.supplier_id === selectedSupplierId,
       );
       return quote
         ? {
             item_id: line.item_id,
             quantity: line.quantity,
             unit_price: quote.quoted_price,
           }
         : null;
     })
     .filter(Boolean);
   ```
4. Call: `POST /purchase-orders` with `{ rfq_id, party_id: selectedSupplierId, line_items, tax_rate, discount_amount }`
5. RFQ status auto-updates to `closed`
6. Navigate to the new PO detail page

Only show the button when `rfq.status === "partially_responded" || rfq.status === "fully_responded"`.

---

## 7. Status-Based UI Rules

### Material Request

| Status           | Can Edit | Can Submit | Can Cancel | Can Convert to RFQ |
| ---------------- | -------- | ---------- | ---------- | ------------------ |
| draft            | Yes      | Yes        | No         | No                 |
| submitted        | No       | No         | Yes        | Yes                |
| partially_quoted | No       | No         | Yes        | No                 |
| fully_quoted     | No       | No         | Yes        | No                 |
| cancelled        | No       | No         | No         | No                 |

### RFQ

| Status              | Can Edit | Can Send | Can Record Quote | Can Convert to PO | Can Close |
| ------------------- | -------- | -------- | ---------------- | ----------------- | --------- |
| draft               | Yes      | Yes      | No               | No                | No        |
| sent                | No       | No       | Yes              | No                | Yes       |
| partially_responded | No       | No       | Yes              | Yes               | Yes       |
| fully_responded     | No       | No       | Yes              | Yes               | Yes       |
| closed              | No       | No       | No               | No                | No        |

### Purchase Order

| Status             | Can Edit | Can Submit | Can Cancel | Can Close |
| ------------------ | -------- | ---------- | ---------- | --------- |
| draft              | Yes      | Yes        | Yes        | No        |
| submitted          | No       | No         | Yes        | No        |
| partially_received | No       | No         | No         | No        |
| fully_received     | No       | No         | No         | Yes       |
| closed             | No       | No         | No         | No        |
| cancelled          | No       | No         | No         | No        |

---

## 8. Error Handling

All errors return:

```json
{
  "detail": "Human-readable error message"
}
```

Common status codes:

- `400` - Validation error (wrong status for action, missing fields)
- `401` - Unauthorized (invalid/missing token)
- `403` - Forbidden (insufficient permissions)
- `404` - Resource not found
- `422` - Request body validation error

Extract error message:

```typescript
catch (err: any) {
  const message = err.response?.data?.detail || "An error occurred";
}
```

---

## 9. Workflow Timeline Component Data

Use `GET /material-requests/{id}/workflow` to build the timeline:

```typescript
const { data } = await materialRequestService.getWorkflow(mrId);

const steps = [
  {
    name: "Material Request",
    completed: true,
    status: data.material_request.status,
  },
  {
    name: "RFQ",
    completed: data.rfqs.length > 0,
    status: data.rfqs[0]?.status,
  },
  {
    name: "Purchase Order",
    completed: data.purchase_orders.length > 0,
    status: data.purchase_orders[0]?.status,
  },
  {
    name: "Receipt",
    completed: data.receipts.length > 0,
    status: data.receipts[0]?.status,
  },
  {
    name: "Invoice",
    completed: data.invoices.length > 0,
    status: data.invoices[0]?.status,
  },
  {
    name: "Payment",
    completed: data.payments.length > 0,
    status: data.payments[0]?.status,
  },
];
```

---

## 10. Key Implementation Notes

- `request_no` is auto-generated as `MR-YYYY-NNNN` if not provided on create
- `tax_rate` on PO is a decimal 0-1 (not percentage). Send 0.18 for 18%
- PO `grand_total` is calculated server-side by the Transaction Engine. Do not calculate on frontend
- When creating PO from RFQ, you must send `line_items` with the quoted `unit_price` values
- RFQ quote recording auto-cascades status updates to both the RFQ and the parent MR
- Closing an RFQ happens automatically when a PO is created from it
- `received_quantity` on PO line items is updated by the Purchase Receipt flow (separate API)
- All list endpoints support pagination with `page`, `page_size`, `has_next`, `has_prev`
- Swagger UI available at: http://localhost:8001/docs
