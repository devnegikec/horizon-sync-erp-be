---
title: Frontend Smart Picking Module - Implementation Guide
description: Complete guide for building the Smart Picking module for warehouse allocation and delivery workflow
tags:
  [
    frontend,
    smart-picking,
    warehouse,
    allocation,
    pick-list,
    delivery,
    stock,
    api-integration,
  ]
---

# Frontend Smart Picking Module - Implementation Guide

## Overview

Build a Smart Picking module that enables users to:

1. View suggested warehouse allocations for a confirmed Sales Order
2. Review and adjust allocation suggestions before committing
3. Create a Pick List that reserves stock across warehouses
4. Convert a completed Pick List into a Delivery Note with full audit trail
5. Track stock movements and delivery status

## Workflow Diagram

```
Sales Order (confirmed) → Suggest Allocation → Review/Edit Suggestions
       → Create Pick List (reserves stock) → Create Delivery Note (deducts stock, creates audit trail)
```

**Status Transitions:**

- Pick List: `DRAFT` → `COMPLETED` (on delivery note creation)
- Sales Order: `CONFIRMED` → `PARTIALLY_DELIVERED` → `DELIVERED`

## API Endpoints Reference

### Base URL

```
http://localhost:8001/api/v1/smart-picking
```

### Authentication

All requests require Bearer token in Authorization header:

```
Authorization: Bearer {token}
```

### Available Endpoints

1. **Suggest Allocation** - `GET /smart-picking/suggest-allocation/{sales_order_id}`
2. **Create Pick List** - `POST /smart-picking/create`
3. **Create Delivery Note from Pick List** - `POST /smart-picking/delivery-from-pick-list`

---

### 1. Suggest Allocation

**Endpoint**: `GET /api/v1/smart-picking/suggest-allocation/{sales_order_id}`

**Permission Required**: `pick_list.read`

**Description**: For each SO line item, queries `stock_levels` ordered by `quantity_available DESC` and splits the required qty across warehouses when a single warehouse can't fulfil the full amount. Only considers items with remaining undelivered quantity (`qty - delivered_qty`).

**Path Parameters**:

- `sales_order_id` (UUID) — The confirmed sales order to allocate

**Response** (`200 OK`):

```json
{
  "sales_order_id": "uuid",
  "sales_order_no": "SO-2025-0001",
  "customer_id": "uuid",
  "suggestions": [
    {
      "item_id": "uuid",
      "item_code": "ITEM-001",
      "item_name": "Widget A",
      "warehouse_id": "uuid",
      "warehouse_code": "WH-MAIN",
      "warehouse_name": "Main Warehouse",
      "suggested_qty": 50,
      "current_available": 120,
      "uom": "Pieces"
    },
    {
      "item_id": "uuid",
      "item_code": "ITEM-001",
      "item_name": "Widget A",
      "warehouse_id": "uuid-2",
      "warehouse_code": "WH-SEC",
      "warehouse_name": "Secondary Warehouse",
      "suggested_qty": 10,
      "current_available": 30,
      "uom": "Pieces"
    }
  ],
  "unallocated": [
    {
      "item_id": "uuid",
      "item_code": "ITEM-002",
      "item_name": "Widget B",
      "short_qty": 5,
      "uom": "Boxes"
    }
  ]
}
```

**Error Responses**:

- `404` — Sales order not found
- `409` — Sales order not in `confirmed` or `partially_delivered` status

---

### 2. Create Pick List

**Endpoint**: `POST /api/v1/smart-picking/create`

**Permission Required**: `pick_list.create`

**Description**: Creates a pick list from confirmed allocations and reserves stock. For each allocation line, increments `quantity_reserved` and decrements `quantity_available` in `stock_levels`. Uses `SELECT ... FOR UPDATE` row locks. All operations run inside a single DB transaction.

**Request Body**:

```json
{
  "sales_order_id": "uuid",
  "allocations": [
    {
      "item_id": "uuid",
      "warehouse_id": "uuid",
      "qty": 50,
      "uom": "Pieces"
    },
    {
      "item_id": "uuid",
      "warehouse_id": "uuid-2",
      "qty": 10,
      "uom": "Pieces"
    }
  ],
  "remarks": "Optional notes"
}
```

**Validation Rules**:

- `allocations` must have at least 1 item
- `qty` must be > 0
- `uom` must be 1–50 characters
- Each allocation must have a matching `stock_level` row with sufficient `quantity_available`

**Response** (`201 Created`):

```json
{
  "id": "uuid",
  "pick_list_no": "PL-2025-0001",
  "status": "draft",
  "sales_order_id": "uuid",
  "sales_order_no": "SO-2025-0001",
  "items": [
    {
      "id": "uuid",
      "item_id": "uuid",
      "warehouse_id": "uuid",
      "qty": 50,
      "picked_qty": 0,
      "uom": "Pieces"
    }
  ],
  "created_at": "2025-06-15T10:30:00Z"
}
```

**Error Responses**:

- `404` — Sales order not found
- `409` — Sales order not in `confirmed` or `partially_delivered` status
- `422` — Insufficient stock or no stock level found for item/warehouse combo

---

### 3. Create Delivery Note from Pick List

**Endpoint**: `POST /api/v1/smart-picking/delivery-from-pick-list`

**Permission Required**: `delivery_note.create`

**Description**: Converts a pick list into a delivery note. Decrements `quantity_on_hand` and `quantity_reserved` in `stock_levels`, creates `stock_movement` audit records (type=OUT), marks the pick list as `COMPLETED`, and updates `delivered_qty` on the sales order items. Flips SO status to `PARTIALLY_DELIVERED` or `DELIVERED` based on completeness.

**Request Body**:

```json
{
  "pick_list_id": "uuid",
  "delivery_date": "2025-06-15T10:30:00Z",
  "remarks": "Optional notes"
}
```

- `delivery_date` is optional (defaults to now)
- `remarks` is optional

**Response** (`201 Created`):

```json
{
  "id": "uuid",
  "delivery_note_no": "DN-2025-0001",
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
  "created_at": "2025-06-15T10:30:00Z"
}
```

**Error Responses**:

- `404` — Pick list not found, or referenced sales order not found
- `409` — Pick list not in `draft` or `in_progress` status
- `422` — Pick list does not reference a sales_order

---

## Module Structure

```
src/
├── features/
│   └── smart-picking/
│       ├── components/
│       │   ├── AllocationSuggestionView.tsx    # Display suggested allocations
│       │   ├── AllocationEditor.tsx            # Edit allocations before confirming
│       │   ├── ConfirmPickListButton.tsx       # Create pick list from allocations
│       │   ├── CreateDeliveryButton.tsx        # Create delivery note from pick list
│       │   ├── UnallocatedWarning.tsx          # Show items with insufficient stock
│       │   └── PickListStatusBadge.tsx         # Pick list status indicator
│       ├── hooks/
│       │   ├── useSuggestAllocation.ts         # Fetch allocation suggestions
│       │   ├── useCreateSmartPickList.ts       # Create pick list
│       │   └── useDeliveryFromPickList.ts      # Create delivery note
│       ├── services/
│       │   └── smartPickingService.ts          # API service layer
│       ├── types/
│       │   └── smartPicking.types.ts           # TypeScript types
│       └── utils/
│           └── allocationHelpers.ts            # Grouping/totalling helpers
```

## TypeScript Types

```typescript
// smartPicking.types.ts

// ============================================
// SUGGEST ALLOCATION TYPES
// ============================================

export interface AllocationSuggestionItem {
  item_id: string;
  item_code: string;
  item_name: string;
  warehouse_id: string;
  warehouse_code: string;
  warehouse_name: string;
  suggested_qty: number;
  current_available: number;
  uom: string;
}

export interface UnallocatedItem {
  item_id: string;
  item_code: string;
  item_name: string;
  short_qty: number;
  uom: string;
}

export interface AllocationSuggestionResponse {
  sales_order_id: string;
  sales_order_no: string;
  customer_id: string;
  suggestions: AllocationSuggestionItem[];
  unallocated: UnallocatedItem[];
}

// ============================================
// CREATE PICK LIST TYPES
// ============================================

export interface SmartPickAllocation {
  item_id: string;
  warehouse_id: string;
  qty: number;
  uom: string;
}

export interface SmartPickListCreate {
  sales_order_id: string;
  allocations: SmartPickAllocation[];
  remarks?: string | null;
}

export interface SmartPickListItem {
  id: string;
  item_id: string;
  warehouse_id: string;
  qty: number;
  picked_qty: number;
  uom: string;
}

export interface SmartPickListResponse {
  id: string;
  pick_list_no: string;
  status: string;
  sales_order_id: string;
  sales_order_no: string;
  items: SmartPickListItem[];
  created_at: string;
}

// ============================================
// DELIVERY NOTE FROM PICK LIST TYPES
// ============================================

export interface DeliveryNoteFromPickListRequest {
  pick_list_id: string;
  delivery_date?: string | null;
  remarks?: string | null;
}

export interface DeliveryNoteItem {
  id: string;
  item_id: string;
  warehouse_id: string;
  qty: number;
  uom: string;
  rate: number;
  amount: number;
}

export interface DeliveryNoteFromPickListResponse {
  id: string;
  delivery_note_no: string;
  customer_id: string;
  status: string;
  pick_list_id: string;
  items: DeliveryNoteItem[];
  stock_movements_created: number;
  created_at: string;
}
```

## API Service Implementation

```typescript
// services/smartPickingService.ts

import axios from "axios";
import type {
  AllocationSuggestionResponse,
  SmartPickListCreate,
  SmartPickListResponse,
  DeliveryNoteFromPickListRequest,
  DeliveryNoteFromPickListResponse,
} from "../types/smartPicking.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class SmartPickingService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async suggestAllocation(
    salesOrderId: string,
  ): Promise<AllocationSuggestionResponse> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/smart-picking/suggest-allocation/${salesOrderId}`,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async createPickList(
    data: SmartPickListCreate,
  ): Promise<SmartPickListResponse> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/smart-picking/create`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async createDeliveryFromPickList(
    data: DeliveryNoteFromPickListRequest,
  ): Promise<DeliveryNoteFromPickListResponse> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/smart-picking/delivery-from-pick-list`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }
}

export const smartPickingService = new SmartPickingService();
```

## React Hooks

### Suggest Allocation Hook

```typescript
// hooks/useSuggestAllocation.ts

import { useState } from "react";
import { smartPickingService } from "../services/smartPickingService";
import type { AllocationSuggestionResponse } from "../types/smartPicking.types";

export const useSuggestAllocation = () => {
  const [data, setData] = useState<AllocationSuggestionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSuggestions = async (salesOrderId: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await smartPickingService.suggestAllocation(salesOrderId);
      setData(result);
      return result;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to fetch allocation suggestions";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { data, loading, error, fetchSuggestions };
};
```

### Create Pick List Hook

```typescript
// hooks/useCreateSmartPickList.ts

import { useState } from "react";
import { smartPickingService } from "../services/smartPickingService";
import type {
  SmartPickListCreate,
  SmartPickListResponse,
} from "../types/smartPicking.types";

export const useCreateSmartPickList = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createPickList = async (
    data: SmartPickListCreate,
  ): Promise<SmartPickListResponse> => {
    setLoading(true);
    setError(null);
    try {
      const result = await smartPickingService.createPickList(data);
      return result;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to create pick list";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createPickList, loading, error };
};
```

### Delivery from Pick List Hook

```typescript
// hooks/useDeliveryFromPickList.ts

import { useState } from "react";
import { smartPickingService } from "../services/smartPickingService";
import type {
  DeliveryNoteFromPickListRequest,
  DeliveryNoteFromPickListResponse,
} from "../types/smartPicking.types";

export const useDeliveryFromPickList = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createDelivery = async (
    data: DeliveryNoteFromPickListRequest,
  ): Promise<DeliveryNoteFromPickListResponse> => {
    setLoading(true);
    setError(null);
    try {
      const result = await smartPickingService.createDeliveryFromPickList(data);
      return result;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to create delivery note";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createDelivery, loading, error };
};
```

## Component Examples

### Allocation Suggestion View

```typescript
// components/AllocationSuggestionView.tsx

import React, { useEffect, useState } from "react";
import { useSuggestAllocation } from "../hooks/useSuggestAllocation";
import { useCreateSmartPickList } from "../hooks/useCreateSmartPickList";
import type { SmartPickAllocation } from "../types/smartPicking.types";

interface AllocationSuggestionViewProps {
  salesOrderId: string;
  onPickListCreated?: (pickListId: string) => void;
}

export const AllocationSuggestionView: React.FC<
  AllocationSuggestionViewProps
> = ({ salesOrderId, onPickListCreated }) => {
  const { data, loading, error, fetchSuggestions } = useSuggestAllocation();
  const {
    createPickList,
    loading: creating,
    error: createError,
  } = useCreateSmartPickList();

  const [editedAllocations, setEditedAllocations] = useState<
    SmartPickAllocation[]
  >([]);
  const [remarks, setRemarks] = useState("");

  useEffect(() => {
    fetchSuggestions(salesOrderId);
  }, [salesOrderId]);

  useEffect(() => {
    if (data?.suggestions) {
      setEditedAllocations(
        data.suggestions.map((s) => ({
          item_id: s.item_id,
          warehouse_id: s.warehouse_id,
          qty: s.suggested_qty,
          uom: s.uom,
        }))
      );
    }
  }, [data]);

  const handleQtyChange = (index: number, newQty: number) => {
    const updated = [...editedAllocations];
    updated[index] = { ...updated[index], qty: newQty };
    setEditedAllocations(updated);
  };

  const handleCreatePickList = async () => {
    const validAllocations = editedAllocations.filter((a) => a.qty > 0);
    if (validAllocations.length === 0) {
      alert("Please allocate at least one item");
      return;
    }

    try {
      const result = await createPickList({
        sales_order_id: salesOrderId,
        allocations: validAllocations,
        remarks: remarks || undefined,
      });
      onPickListCreated?.(result.id);
      alert(`Pick List ${result.pick_list_no} created successfully!`);
    } catch (err) {
      // Error handled by hook
    }
  };

  if (loading) return <div>Loading allocation suggestions...</div>;
  if (error) return <div className="error-message">Error: {error}</div>;
  if (!data) return null;

  return (
    <div className="allocation-suggestion-view">
      <div className="suggestion-header">
        <h2>Smart Picking — {data.sales_order_no}</h2>
        <p>Review and adjust warehouse allocations before creating a pick list.</p>
      </div>

      {data.unallocated.length > 0 && (
        <div className="warning-banner">
          <strong>Insufficient Stock:</strong>
          <ul>
            {data.unallocated.map((item) => (
              <li key={item.item_id}>
                {item.item_name} ({item.item_code}) — short by {item.short_qty}{" "}
                {item.uom}
              </li>
            ))}
          </ul>
        </div>
      )}

      <table className="allocation-table">
        <thead>
          <tr>
            <th>Item</th>
            <th>Warehouse</th>
            <th>Available</th>
            <th>Suggested Qty</th>
            <th>Allocate Qty</th>
            <th>UOM</th>
          </tr>
        </thead>
        <tbody>
          {data.suggestions.map((suggestion, index) => (
            <tr key={`${suggestion.item_id}-${suggestion.warehouse_id}`}>
              <td>
                <div>{suggestion.item_name}</div>
                <small>{suggestion.item_code}</small>
              </td>
              <td>
                <div>{suggestion.warehouse_name}</div>
                <small>{suggestion.warehouse_code}</small>
              </td>
              <td>{suggestion.current_available}</td>
              <td>{suggestion.suggested_qty}</td>
              <td>
                <input
                  type="number"
                  value={editedAllocations[index]?.qty ?? suggestion.suggested_qty}
                  onChange={(e) =>
                    handleQtyChange(index, Number(e.target.value))
                  }
                  min={0}
                  max={suggestion.current_available}
                  step={1}
                />
              </td>
              <td>{suggestion.uom}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="form-group" style={{ marginTop: "16px" }}>
        <label>Remarks (optional)</label>
        <textarea
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
          rows={2}
          placeholder="Notes for the pick list"
        />
      </div>

      {createError && <div className="error-message">{createError}</div>}

      <div className="form-actions">
        <button
          onClick={handleCreatePickList}
          disabled={creating || editedAllocations.length === 0}
          className="btn-primary"
        >
          {creating ? "Creating Pick List..." : "Create Pick List"}
        </button>
      </div>
    </div>
  );
};
```

### Create Delivery Button

```typescript
// components/CreateDeliveryButton.tsx

import React, { useState } from "react";
import { useDeliveryFromPickList } from "../hooks/useDeliveryFromPickList";

interface CreateDeliveryButtonProps {
  pickListId: string;
  pickListStatus: string;
  onSuccess?: (deliveryNoteId: string) => void;
}

export const CreateDeliveryButton: React.FC<CreateDeliveryButtonProps> = ({
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

  const handleCreate = async () => {
    try {
      const result = await createDelivery({
        pick_list_id: pickListId,
        delivery_date: deliveryDate || undefined,
        remarks: remarks || undefined,
      });
      setShowDialog(false);
      onSuccess?.(result.id);
      alert(
        `Delivery Note ${result.delivery_note_no} created! ` +
          `${result.stock_movements_created} stock movements recorded.`
      );
    } catch (err) {
      // Error handled by hook
    }
  };

  if (!canCreate) return null;

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

## Error Handling

| Scenario                             | HTTP Code | User Message                                                       |
| ------------------------------------ | --------- | ------------------------------------------------------------------ |
| Sales order not found                | 404       | "Sales order not found"                                            |
| SO not confirmed/partially_delivered | 409       | "Sales order must be in confirmed or partially_delivered status"   |
| Insufficient stock for allocation    | 422       | "Insufficient stock for item {code} in warehouse {name}"           |
| No stock level row found             | 422       | "No stock level found for item {id} in warehouse {id}"             |
| Pick list not found                  | 404       | "Pick list not found"                                              |
| Pick list not draft/in_progress      | 409       | "Pick list must be draft or in_progress"                           |
| Pick list doesn't reference a SO     | 422       | "Pick list must reference a sales_order to create a delivery note" |

All error responses follow the pattern:

```json
{ "detail": "Error message string" }
```

## Testing Checklist

### Suggest Allocation

- [ ] Fetch suggestions for a confirmed sales order
- [ ] Verify multi-warehouse splitting (item split across 2+ warehouses)
- [ ] Verify unallocated items appear when stock is insufficient
- [ ] Handle 404 for non-existent sales order
- [ ] Handle 409 for draft/cancelled sales order

### Create Pick List

- [ ] Create pick list with suggested allocations
- [ ] Create pick list with user-edited quantities
- [ ] Verify stock reservation (quantity_reserved incremented, quantity_available decremented)
- [ ] Handle insufficient stock error (422)
- [ ] Handle concurrent reservation conflicts
- [ ] Verify pick list number auto-generation (PL-YYYY-NNNN)

### Create Delivery Note

- [ ] Create delivery note from draft pick list
- [ ] Verify stock deduction (quantity_on_hand and quantity_reserved decremented)
- [ ] Verify stock movements created (type=OUT)
- [ ] Verify pick list marked as COMPLETED
- [ ] Verify SO delivered_qty updated on line items
- [ ] Verify SO status transitions (CONFIRMED → PARTIALLY_DELIVERED → DELIVERED)
- [ ] Handle 409 for already-completed pick list
- [ ] Handle 422 for pick list without SO reference

### Integration

- [ ] Full flow: Suggest → Edit → Create Pick List → Create Delivery Note
- [ ] Partial delivery flow (deliver some items, SO goes to PARTIALLY_DELIVERED)
- [ ] Navigate from Sales Order detail to Smart Picking view
- [ ] Navigate from Pick List to Delivery Note after creation

## Best Practices

1. **Optimistic UI**: Show loading states during stock reservation and delivery creation
2. **Confirmation Dialogs**: Always confirm before creating pick lists (reserves stock) and delivery notes (irreversible stock deduction)
3. **Real-time Validation**: Validate allocation quantities against `current_available` before submission
4. **Error Recovery**: On pick list creation failure, suggest re-fetching suggestions (stock may have changed)
5. **Accessibility**: Ensure allocation table inputs are keyboard navigable with proper labels
6. **Mobile Responsive**: Allocation table should scroll horizontally on small screens

## Environment Variables

```env
REACT_APP_API_URL=http://localhost:8001
```

## Support & Resources

- Smart Picking Service: `core-service/app/services/smart_picking_service.py`
- Smart Picking Schemas: `core-service/app/schemas/smart_picking.py`
- Smart Picking Endpoints: `core-service/app/api/v1/endpoints/smart_picking.py`
- Swagger UI: http://localhost:8001/docs
- Backend logs: `docker compose logs core-service`
