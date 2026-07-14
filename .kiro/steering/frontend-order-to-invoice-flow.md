---
inclusion: manual
---

# Frontend Order-to-Invoice Flow Module - Implementation Guide

## Overview

Complete Procure-to-Deliver-to-Invoice workflow for the sales side:

```
Quotation → Sales Order → Pick List → Delivery Note → Invoice
```

This guide covers the two conversion steps that close the loop:

1. Convert a Pick List into a Delivery Note (stock deduction + audit trail)
2. Convert a Delivery Note into a Sales Invoice (bill only delivered items)

The earlier steps (Quotation → SO, SO → Pick List) are already implemented.

## API Endpoints Reference

### Base URLs

```
Smart Picking:   http://localhost:8001/api/v1/smart-picking
Delivery Notes:  http://localhost:8001/api/v1/delivery-notes
Invoices:        http://localhost:8001/api/v1/invoices
Sales Orders:    http://localhost:8001/api/v1/sales-orders
```

### Authentication

All requests require Bearer token:

```
Authorization: Bearer {token}
```

---

## Step 1 — Pick List → Delivery Note

### Endpoint

`POST /api/v1/smart-picking/delivery-from-pick-list`

Permission: `delivery_note.create`

### Request Body

```json
{
  "pick_list_id": "uuid",
  "delivery_date": "2026-03-01T10:30:00Z",
  "remarks": "Optional notes"
}
```

- `delivery_date` is optional (defaults to now)
- `remarks` is optional

### Response (201 Created)

```json
{
  "id": "uuid",
  "delivery_note_no": "DN-2026-00001",
  "customer_id": "uuid",
  "status": "submitted",
  "pick_list_id": "uuid",
  "items": [
    {
      "id": "uuid",
      "item_id": "uuid",
      "warehouse_id": "uuid",
      "qty": 50,
      "uom": "Pieces",
      "rate": 25.0,
      "amount": 1250.0
    }
  ],
  "stock_movements_created": 2,
  "created_at": "2026-03-01T10:30:00Z"
}
```

### What Happens on the Backend

1. Validates pick list is in `draft` or `in_progress` status
2. Resolves the linked sales order to get customer_id and item rates
3. Creates `delivery_note` + `delivery_note_items` (one per pick list item)
4. Deducts stock: `quantity_on_hand -= qty`, `quantity_reserved -= qty`
5. Creates `stock_movement` audit records (type = OUT)
6. Marks pick list as `completed`
7. Updates `delivered_qty` on sales order items
8. Flips SO status to `partially_delivered` or `delivered`

### Error Responses

| Code | Scenario                                  |
| ---- | ----------------------------------------- |
| 404  | Pick list not found                       |
| 409  | Pick list not in draft/in_progress status |
| 422  | Pick list doesn't reference a sales_order |

---

## Step 2 — Delivery Note → Invoice

### Endpoint

`POST /api/v1/delivery-notes/{delivery_note_id}/convert-to-invoice`

Permission: `delivery_note.update`

### Request Body

```json
{
  "items": [
    {
      "item_id": "uuid (delivery_note_item id)",
      "qty_to_bill": 50
    },
    {
      "item_id": "uuid (delivery_note_item id)",
      "qty_to_bill": 10
    }
  ],
  "due_date": "2026-04-01T00:00:00Z",
  "remarks": "Invoice for March delivery"
}
```

- `items` is required, at least 1 item
- `item_id` refers to the **delivery_note_item** UUID (not the product item_id)
- `qty_to_bill` must be > 0 and ≤ the DN item's delivered qty
- `due_date` and `remarks` are optional

### Response (201 Created)

```json
{
  "invoice_id": "uuid",
  "invoice_no": "INV-2026-00001",
  "grand_total": 1500.0,
  "message": "Delivery note successfully converted to invoice"
}
```

### What Happens on the Backend

1. Validates delivery note is in `submitted` status
2. Validates each item exists on the DN and qty_to_bill ≤ delivered qty
3. Creates `invoice` (type = sales, status = draft) with reference to the DN
4. Creates `invoice_items` with rate/amount from the DN items
5. If the DN was created from a sales order, updates `billed_qty` on SO items
6. Uses the document numbering service for invoice_no generation

### Error Responses

| Code | Scenario                                                   |
| ---- | ---------------------------------------------------------- |
| 404  | Delivery note not found                                    |
| 409  | Delivery note not in submitted status                      |
| 400  | qty_to_bill exceeds delivered qty, or item not found on DN |

---

## TypeScript Types

```typescript
// types/orderToInvoice.types.ts

// ── Pick List → Delivery Note ──────────────────────────

export interface DeliveryFromPickListRequest {
  pick_list_id: string;
  delivery_date?: string | null;
  remarks?: string | null;
}

export interface DeliveryFromPickListItem {
  id: string;
  item_id: string;
  warehouse_id: string;
  qty: number;
  uom: string;
  rate: number;
  amount: number;
}

export interface DeliveryFromPickListResponse {
  id: string;
  delivery_note_no: string;
  customer_id: string;
  status: string;
  pick_list_id: string;
  items: DeliveryFromPickListItem[];
  stock_movements_created: number;
  created_at: string;
}

// ── Delivery Note → Invoice ────────────────────────────

export interface ConvertToInvoiceItemRequest {
  item_id: string; // delivery_note_item UUID
  qty_to_bill: number;
}

export interface ConvertToInvoiceRequest {
  items: ConvertToInvoiceItemRequest[];
  due_date?: string | null;
  remarks?: string | null;
}

export interface ConvertToInvoiceResponse {
  invoice_id: string;
  invoice_no: string;
  grand_total: number;
  message: string;
}

// ── Delivery Note (for display) ────────────────────────

export interface DeliveryNoteItem {
  id: string;
  item_id: string;
  qty: number;
  uom: string;
  rate: number | null;
  amount: number | null;
  warehouse_id: string | null;
  sort_order: number;
}

export interface DeliveryNote {
  id: string;
  organization_id: string;
  delivery_note_no: string;
  customer_id: string;
  delivery_date: string;
  status: "draft" | "submitted" | "cancelled";
  warehouse_id: string | null;
  pick_list_id: string | null;
  reference_type: string | null;
  reference_id: string | null;
  remarks: string | null;
  items: DeliveryNoteItem[];
  created_at: string;
  updated_at: string;
}
```

## API Service

```typescript
// services/orderToInvoiceService.ts

import axios from "axios";
import type {
  DeliveryFromPickListRequest,
  DeliveryFromPickListResponse,
  ConvertToInvoiceRequest,
  ConvertToInvoiceResponse,
  DeliveryNote,
} from "../types/orderToInvoice.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class OrderToInvoiceService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  /** Pick List → Delivery Note */
  async createDeliveryFromPickList(
    data: DeliveryFromPickListRequest,
  ): Promise<DeliveryFromPickListResponse> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/smart-picking/delivery-from-pick-list`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  /** Delivery Note → Invoice */
  async convertDeliveryNoteToInvoice(
    deliveryNoteId: string,
    data: ConvertToInvoiceRequest,
  ): Promise<ConvertToInvoiceResponse> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/delivery-notes/${deliveryNoteId}/convert-to-invoice`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  /** Fetch a single delivery note */
  async getDeliveryNote(id: string): Promise<DeliveryNote> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/delivery-notes/${id}`,
      { headers: this.getHeaders() },
    );
    return response.data;
  }
}

export const orderToInvoiceService = new OrderToInvoiceService();
```

## React Hooks

### useDeliveryFromPickList

```typescript
// hooks/useDeliveryFromPickList.ts

import { useState } from "react";
import { orderToInvoiceService } from "../services/orderToInvoiceService";
import type {
  DeliveryFromPickListRequest,
  DeliveryFromPickListResponse,
} from "../types/orderToInvoice.types";

export const useDeliveryFromPickList = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createDelivery = async (
    data: DeliveryFromPickListRequest,
  ): Promise<DeliveryFromPickListResponse> => {
    setLoading(true);
    setError(null);
    try {
      return await orderToInvoiceService.createDeliveryFromPickList(data);
    } catch (err: any) {
      const msg =
        err.response?.data?.detail || "Failed to create delivery note";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createDelivery, loading, error };
};
```

### useConvertToInvoice

```typescript
// hooks/useConvertToInvoice.ts

import { useState } from "react";
import { orderToInvoiceService } from "../services/orderToInvoiceService";
import type {
  ConvertToInvoiceRequest,
  ConvertToInvoiceResponse,
} from "../types/orderToInvoice.types";

export const useConvertToInvoice = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const convertToInvoice = async (
    deliveryNoteId: string,
    data: ConvertToInvoiceRequest,
  ): Promise<ConvertToInvoiceResponse> => {
    setLoading(true);
    setError(null);
    try {
      return await orderToInvoiceService.convertDeliveryNoteToInvoice(
        deliveryNoteId,
        data,
      );
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Failed to convert to invoice";
      setError(msg);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { convertToInvoice, loading, error };
};
```

## Component Examples

### Create Delivery Note from Pick List

```typescript
// components/CreateDeliveryFromPickListButton.tsx

import React, { useState } from "react";
import { useDeliveryFromPickList } from "../hooks/useDeliveryFromPickList";

interface Props {
  pickListId: string;
  pickListStatus: string;
  onSuccess?: (deliveryNoteId: string, deliveryNoteNo: string) => void;
}

export const CreateDeliveryFromPickListButton: React.FC<Props> = ({
  pickListId,
  pickListStatus,
  onSuccess,
}) => {
  const { createDelivery, loading, error } = useDeliveryFromPickList();
  const [showDialog, setShowDialog] = useState(false);
  const [deliveryDate, setDeliveryDate] = useState("");
  const [remarks, setRemarks] = useState("");

  const canCreate =
    pickListStatus === "draft" || pickListStatus === "in_progress";

  if (!canCreate) return null;

  const handleCreate = async () => {
    try {
      const result = await createDelivery({
        pick_list_id: pickListId,
        delivery_date: deliveryDate || undefined,
        remarks: remarks || undefined,
      });
      setShowDialog(false);
      onSuccess?.(result.id, result.delivery_note_no);
    } catch {
      // error handled by hook
    }
  };

  return (
    <>
      <button
        onClick={() => setShowDialog(true)}
        className="btn-primary"
        disabled={loading}
      >
        Create Delivery Note
      </button>

      {showDialog && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2>Create Delivery Note</h2>
            <p>
              This will deduct stock, create audit movements, and mark the pick
              list as completed.
            </p>

            <div className="form-group">
              <label>Delivery Date (optional, defaults to now)</label>
              <input
                type="datetime-local"
                value={deliveryDate}
                onChange={(e) => setDeliveryDate(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label>Remarks (optional)</label>
              <textarea
                value={remarks}
                onChange={(e) => setRemarks(e.target.value)}
                rows={2}
              />
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="modal-actions">
              <button onClick={() => setShowDialog(false)} disabled={loading}>
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={loading}
                className="btn-primary"
              >
                {loading ? "Creating..." : "Confirm & Create"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
```

### Convert Delivery Note to Invoice

```typescript
// components/ConvertToInvoiceButton.tsx

import React, { useState } from "react";
import { useConvertToInvoice } from "../hooks/useConvertToInvoice";
import type { DeliveryNote } from "../types/orderToInvoice.types";

interface Props {
  deliveryNote: DeliveryNote;
  onSuccess?: (invoiceId: string, invoiceNo: string) => void;
}

export const ConvertToInvoiceButton: React.FC<Props> = ({
  deliveryNote,
  onSuccess,
}) => {
  const { convertToInvoice, loading, error } = useConvertToInvoice();
  const [showDialog, setShowDialog] = useState(false);
  const [selectedItems, setSelectedItems] = useState<
    Map<string, number>
  >(new Map());
  const [dueDate, setDueDate] = useState("");
  const [remarks, setRemarks] = useState("");

  const canConvert = deliveryNote.status === "submitted";

  // Initialize all items as selected with full qty
  const openDialog = () => {
    const initial = new Map<string, number>();
    deliveryNote.items.forEach((item) => {
      initial.set(item.id, Number(item.qty));
    });
    setSelectedItems(initial);
    setShowDialog(true);
  };

  const handleQtyChange = (itemId: string, qty: number) => {
    const updated = new Map(selectedItems);
    if (qty <= 0) {
      updated.delete(itemId);
    } else {
      updated.set(itemId, qty);
    }
    setSelectedItems(updated);
  };

  const handleConvert = async () => {
    if (selectedItems.size === 0) {
      alert("Please select at least one item to bill");
      return;
    }

    try {
      const items = Array.from(selectedItems.entries()).map(
        ([item_id, qty_to_bill]) => ({ item_id, qty_to_bill })
      );

      const result = await convertToInvoice(deliveryNote.id, {
        items,
        due_date: dueDate || undefined,
        remarks: remarks || undefined,
      });

      setShowDialog(false);
      onSuccess?.(result.invoice_id, result.invoice_no);
    } catch {
      // error handled by hook
    }
  };

  if (!canConvert) return null;

  return (
    <>
      <button
        onClick={openDialog}
        className="btn-primary"
        disabled={loading}
      >
        Convert to Invoice
      </button>

      {showDialog && (
        <div className="modal-overlay">
          <div className="modal-content modal-large">
            <h2>Convert to Invoice</h2>
            <p>
              Delivery Note: {deliveryNote.delivery_note_no} — Select items and
              quantities to bill.
            </p>

            <table>
              <thead>
                <tr>
                  <th>Item</th>
                  <th>Delivered Qty</th>
                  <th>UOM</th>
                  <th>Rate</th>
                  <th>Qty to Bill</th>
                  <th>Line Total</th>
                </tr>
              </thead>
              <tbody>
                {deliveryNote.items.map((item) => {
                  const qtyToBill = selectedItems.get(item.id) ?? 0;
                  const rate = item.rate ?? 0;
                  return (
                    <tr key={item.id}>
                      <td>{item.item_id}</td>
                      <td>{item.qty}</td>
                      <td>{item.uom}</td>
                      <td>${Number(rate).toFixed(2)}</td>
                      <td>
                        <input
                          type="number"
                          value={qtyToBill}
                          onChange={(e) =>
                            handleQtyChange(item.id, Number(e.target.value))
                          }
                          min={0}
                          max={Number(item.qty)}
                          step={1}
                        />
                      </td>
                      <td>${(qtyToBill * Number(rate)).toFixed(2)}</td>
                    </tr>
                  );
                })}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={5} style={{ textAlign: "right" }}>
                    <strong>Grand Total:</strong>
                  </td>
                  <td>
                    <strong>
                      $
                      {Array.from(selectedItems.entries())
                        .reduce((sum, [itemId, qty]) => {
                          const item = deliveryNote.items.find(
                            (i) => i.id === itemId
                          );
                          return sum + qty * Number(item?.rate ?? 0);
                        }, 0)
                        .toFixed(2)}
                    </strong>
                  </td>
                </tr>
              </tfoot>
            </table>

            <div className="form-row" style={{ marginTop: "16px" }}>
              <div className="form-group">
                <label>Due Date (optional)</label>
                <input
                  type="date"
                  value={dueDate}
                  onChange={(e) => setDueDate(e.target.value)}
                />
              </div>
              <div className="form-group">
                <label>Remarks (optional)</label>
                <textarea
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  rows={2}
                />
              </div>
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="modal-actions">
              <button onClick={() => setShowDialog(false)} disabled={loading}>
                Cancel
              </button>
              <button
                onClick={handleConvert}
                disabled={loading || selectedItems.size === 0}
                className="btn-primary"
              >
                {loading ? "Creating Invoice..." : "Create Invoice"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
```

## Module Structure

```
src/
├── features/
│   └── order-to-invoice/
│       ├── components/
│       │   ├── CreateDeliveryFromPickListButton.tsx
│       │   ├── ConvertToInvoiceButton.tsx
│       │   └── OrderFlowTimeline.tsx
│       ├── hooks/
│       │   ├── useDeliveryFromPickList.ts
│       │   └── useConvertToInvoice.ts
│       ├── services/
│       │   └── orderToInvoiceService.ts
│       └── types/
│           └── orderToInvoice.types.ts
```

## Integration Points

### On Pick List Detail Page

```tsx
import { CreateDeliveryFromPickListButton } from "../features/order-to-invoice/components/CreateDeliveryFromPickListButton";

// Inside PickListDetail component:
<CreateDeliveryFromPickListButton
  pickListId={pickList.id}
  pickListStatus={pickList.status}
  onSuccess={(dnId, dnNo) => {
    navigate(`/delivery-notes/${dnId}`);
  }}
/>;
```

### On Delivery Note Detail Page

```tsx
import { ConvertToInvoiceButton } from "../features/order-to-invoice/components/ConvertToInvoiceButton";

// Inside DeliveryNoteDetail component:
<ConvertToInvoiceButton
  deliveryNote={deliveryNote}
  onSuccess={(invoiceId, invoiceNo) => {
    navigate(`/invoices/${invoiceId}`);
  }}
/>;
```

## Complete Flow Summary

```
1. Quotation (accepted)
   └─→ POST /sales-orders  (reference_type: "quotation")

2. Sales Order (confirmed)
   └─→ GET  /smart-picking/suggest-allocation/{so_id}
   └─→ POST /smart-picking/create  (reserves stock)

3. Pick List (draft)
   └─→ POST /smart-picking/delivery-from-pick-list
       • Deducts stock (on_hand, reserved)
       • Creates stock_movement audit records
       • Marks pick list → completed
       • Updates SO delivered_qty
       • SO status → partially_delivered / delivered

4. Delivery Note (submitted)
   └─→ POST /delivery-notes/{id}/convert-to-invoice
       • Creates invoice (draft) with DN items
       • Updates SO billed_qty (if DN linked to SO)
       • Only bills up to delivered qty

5. Invoice (draft → pending → paid)
   └─→ POST /payments  (standard payment flow)
```

## Testing Checklist

### Pick List → Delivery Note

- [ ] Create delivery note from draft pick list
- [ ] Verify stock deduction (quantity_on_hand and quantity_reserved decremented)
- [ ] Verify stock movements created (type=OUT)
- [ ] Verify pick list marked as completed
- [ ] Verify SO delivered_qty updated
- [ ] Verify SO status transitions (confirmed → partially_delivered → delivered)
- [ ] Handle 409 for already-completed pick list
- [ ] Handle 422 for pick list without SO reference

### Delivery Note → Invoice

- [ ] Convert submitted DN to invoice with all items
- [ ] Convert with partial items (bill only some items)
- [ ] Convert with partial qty (bill less than delivered qty)
- [ ] Verify invoice created with correct grand_total
- [ ] Verify invoice items have correct rate/amount from DN
- [ ] Verify SO billed_qty updated when DN references a SO
- [ ] Handle 409 for draft/cancelled DN
- [ ] Handle 400 for qty_to_bill > delivered qty
- [ ] Handle 400 for item not found on DN

### End-to-End

- [ ] Full flow: SO → Pick List → Delivery Note → Invoice
- [ ] Partial delivery: deliver some items, invoice only delivered items
- [ ] Multiple deliveries from same SO, invoice each separately
- [ ] Navigate between related documents via reference links

## Error Handling

All error responses follow the pattern:

```json
{ "detail": "Error message string" }
```

Handle these in the frontend with the hook's error state and display user-friendly messages.

## Environment Variables

```env
REACT_APP_API_URL=http://localhost:8001
```
