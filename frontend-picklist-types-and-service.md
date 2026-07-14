# Pick List API Integration - Customer and Warehouse Details

## Updated TypeScript Types

```typescript
// types/pickList.types.ts

export interface NestedReference {
  id: string;
  name: string;
  code: string;
}

export interface ReferenceDetails {
  id: string;
  reference_type: string;
  name: string;
  code: string;
}

export interface PickListItem {
  id: string;
  organization_id: string;
  item: NestedReference | null;
  warehouse: NestedReference | null;
  qty: number;
  picked_qty: number;
  uom: string;
  batch_no: string | null;
  sort_order: number;
  created_at: string;
}

export interface PickList {
  id: string;
  organization_id: string;
  pick_list_no: string;
  warehouse_id: string;
  warehouse: NestedReference | null;
  status: "draft" | "in_progress" | "completed" | "cancelled";
  pick_date: string | null;
  reference_type: string | null;
  reference_id: string | null;
  reference: ReferenceDetails | null;
  remarks: string | null;
  completed_at: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  items: PickListItem[];
}

export interface PickListListItem {
  id: string;
  organization_id: string;
  pick_list_no: string;
  warehouse_id: string;
  status: string;
  pick_date: string | null;
  created_at: string;
}

export interface PickListListResponse {
  pick_lists: PickListListItem[];
  pagination: {
    page: number;
    page_size: number;
    total_items: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}
```

## Updated Service Implementation

```typescript
// services/pickListService.ts

import axios from "axios";
import type { PickList, PickListListResponse } from "../types/pickList.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class PickListService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  /**
   * Get a single pick list by ID with customer and warehouse details
   *
   * Response includes:
   * - customer: { id, name, code }
   * - items[].warehouse: { id, name, code }
   */
  async getPickList(id: string): Promise<PickList> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/pick-lists/${id}`,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  /**
   * List all pick lists with customer details
   */
  async listPickLists(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    sales_order_id?: string;
    customer_id?: string;
  }): Promise<PickListListResponse> {
    const response = await axios.get(`${API_BASE_URL}/api/v1/pick-lists`, {
      headers: this.getHeaders(),
      params,
    });
    return response.data;
  }

  async createPickList(data: any): Promise<PickList> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/pick-lists`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async updatePickList(id: string, data: any): Promise<PickList> {
    const response = await axios.patch(
      `${API_BASE_URL}/api/v1/pick-lists/${id}`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async deletePickList(id: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/api/v1/pick-lists/${id}`, {
      headers: this.getHeaders(),
    });
  }
}

export const pickListService = new PickListService();
```

## Updated React Hook

```typescript
// hooks/usePickList.ts

import { useState, useEffect } from "react";
import { pickListService } from "../services/pickListService";
import type { PickList } from "../types/pickList.types";

export const usePickList = (id: string) => {
  const [data, setData] = useState<PickList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPickList = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await pickListService.getPickList(id);
      setData(result);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch pick list");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) {
      fetchPickList();
    }
  }, [id]);

  return { data, loading, error, refetch: fetchPickList };
};
```

## Updated Component Example

```typescript
// components/PickListDetail.tsx

import React from "react";
import { useParams } from "react-router-dom";
import { usePickList } from "../hooks/usePickList";

export const PickListDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { data: pickList, loading, error } = usePickList(id!);

  if (loading) return <div>Loading pick list...</div>;
  if (error) return <div className="error-message">Error: {error}</div>;
  if (!pickList) return <div>Pick list not found</div>;

  return (
    <div className="pick-list-detail">
      <div className="detail-header">
        <h1>Pick List {pickList.pick_list_no}</h1>
        <span className={`status-badge status-${pickList.status}`}>
          {pickList.status}
        </span>
      </div>

      {/* Pick List Items with Item and Warehouse Details */}
      <div className="items-section">
        <h3>Items to Pick</h3>
        <table className="pick-list-items-table">
          <thead>
            <tr>
              <th>Item Code</th>
              <th>Item Name</th>
              <th>Warehouse</th>
              <th>Warehouse Code</th>
              <th>Quantity</th>
              <th>Picked</th>
              <th>UOM</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {pickList.items.map((item) => (
              <tr key={item.id}>
                <td>{item.item?.code || item.item_id}</td>
                <td>{item.item?.name || "-"}</td>
                <td>{item.warehouse?.name || "-"}</td>
                <td>{item.warehouse?.code || "-"}</td>
                <td>{item.qty}</td>
                <td>{item.picked_qty}</td>
                <td>{item.uom}</td>
                <td>
                  {item.picked_qty >= item.qty ? (
                    <span className="status-complete">✓ Complete</span>
                  ) : item.picked_qty > 0 ? (
                    <span className="status-partial">Partial</span>
                  ) : (
                    <span className="status-pending">Pending</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Reference Information */}
      {pickList.reference && (
        <div className="info-section">
          <h3>Reference Document</h3>
          <div className="info-grid">
            <div className="info-item">
              <label>Type:</label>
              <span>{pickList.reference.reference_type}</span>
            </div>
            <div className="info-item">
              <label>Document No:</label>
              <a href={`/${pickList.reference.reference_type}s/${pickList.reference.id}`}>
                {pickList.reference.code}
              </a>
            </div>
          </div>
        </div>
      )}

      {/* Warehouse Information */}
      {pickList.warehouse && (
        <div className="info-section">
          <h3>Warehouse</h3>
          <div className="info-grid">
            <div className="info-item">
              <label>Warehouse Code:</label>
              <span>{pickList.warehouse.code}</span>
            </div>
            <div className="info-item">
              <label>Warehouse Name:</label>
              <span>{pickList.warehouse.name}</span>
            </div>
          </div>
        </div>
      )}

      {pickList.remarks && (
        <div className="info-section">
          <h3>Remarks</h3>
          <p>{pickList.remarks}</p>
        </div>
      )}

      <div className="info-section">
        <h3>Metadata</h3>
        <div className="info-grid">
          <div className="info-item">
            <label>Created:</label>
            <span>{new Date(pickList.created_at).toLocaleString()}</span>
          </div>
          <div className="info-item">
            <label>Updated:</label>
            <span>{new Date(pickList.updated_at).toLocaleString()}</span>
          </div>
          {pickList.created_by && (
            <div className="info-item">
              <label>Created By:</label>
              <span>{pickList.created_by}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
```

## Pick List List Component with Customer Details

```typescript
// components/PickListList.tsx

import React from "react";
import { usePickLists } from "../hooks/usePickLists";
import { format } from "date-fns";

export const PickListList: React.FC = () => {
  const { data, loading, error, refetch } = usePickLists();

  if (loading) return <div>Loading pick lists...</div>;
  if (error) return <div className="error-message">Error: {error}</div>;
  if (!data) return null;

  return (
    <div className="pick-list-list">
      <div className="list-header">
        <h2>Pick Lists</h2>
        <button className="btn-primary">+ New Pick List</button>
      </div>

      <table className="pick-lists-table">
        <thead>
          <tr>
            <th>Pick List No</th>
            <th>Customer Code</th>
            <th>Customer Name</th>
            <th>Sales Order</th>
            <th>Status</th>
            <th>Items</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.pick_lists.map((pickList) => (
            <tr key={pickList.id}>
              <td>
                <a href={`/pick-lists/${pickList.id}`}>
                  {pickList.pick_list_no}
                </a>
              </td>
              <td>{pickList.customer.code}</td>
              <td>{pickList.customer.name}</td>
              <td>{pickList.sales_order_no}</td>
              <td>
                <span className={`status-badge status-${pickList.status}`}>
                  {pickList.status}
                </span>
              </td>
              <td>{pickList.items_count}</td>
              <td>{format(new Date(pickList.created_at), "MMM dd, yyyy")}</td>
              <td>
                <button className="btn-sm">View</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {data.pagination.total_pages > 1 && (
        <div className="pagination">
          <button
            disabled={!data.pagination.has_prev}
            onClick={() => refetch(data.pagination.page - 1)}
          >
            Previous
          </button>
          <span>
            Page {data.pagination.page} of {data.pagination.total_pages}
          </span>
          <button
            disabled={!data.pagination.has_next}
            onClick={() => refetch(data.pagination.page + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
};
```

## Example API Response Format

When calling `GET /api/v1/pick-lists/{id}`, the response now includes enriched nested objects:

```json
{
  "id": "77487a86-15c5-4d1a-a7be-a5cc1b1fa0a6",
  "organization_id": "bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150",
  "pick_list_no": "PL-2026-0006",
  "warehouse_id": "cbf290a6-91cb-4c93-b9a6-db408bb3c274",
  "warehouse": {
    "id": "cbf290a6-91cb-4c93-b9a6-db408bb3c274",
    "name": "Main Warehouse",
    "code": "WH-MAIN"
  },
  "status": "completed",
  "pick_date": "2026-03-02T17:33:22.591222Z",
  "reference_type": "sales_order",
  "reference_id": "9f03419b-98cf-44d6-9796-da53d0a1dc44",
  "reference": {
    "id": "9f03419b-98cf-44d6-9796-da53d0a1dc44",
    "reference_type": "sales_order",
    "name": "SO-2026-0001",
    "code": "SO-2026-0001"
  },
  "remarks": null,
  "completed_at": "2026-03-02T17:35:19.771769Z",
  "created_by": "8d509f22-5fe5-4765-9496-3a236cae2af1",
  "updated_by": "8d509f22-5fe5-4765-9496-3a236cae2af1",
  "created_at": "2026-03-02T17:33:22.601133Z",
  "updated_at": "2026-03-02T17:35:19.825475Z",
  "items": [
    {
      "id": "5f88764e-2236-433d-a845-824212d18537",
      "organization_id": "bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150",
      "item": {
        "id": "a17ac10b-58cc-4372-a567-0e02b2c3d010",
        "name": "Widget A",
        "code": "ITEM-001"
      },
      "warehouse": {
        "id": "cbf290a6-91cb-4c93-b9a6-db408bb3c274",
        "name": "Main Warehouse",
        "code": "WH-MAIN"
      },
      "qty": "50.000",
      "picked_qty": "0.000",
      "uom": "REM",
      "batch_no": null,
      "sort_order": 0,
      "created_at": "2026-03-02T17:33:22.611530Z"
    },
    {
      "id": "586256b3-b2af-45cf-bb98-a09fdea4f526",
      "organization_id": "bfe4fc3e-0b7d-45c9-a983-2ea9f9e99150",
      "item": {
        "id": "f47ac10b-58cc-4372-a567-0e02b2c3d478",
        "name": "Widget B",
        "code": "ITEM-002"
      },
      "warehouse": {
        "id": "cbf290a6-91cb-4c93-b9a6-db408bb3c274",
        "name": "Main Warehouse",
        "code": "WH-MAIN"
      },
      "qty": "1.000",
      "picked_qty": "0.000",
      "uom": "UNIT",
      "batch_no": null,
      "sort_order": 1,
      "created_at": "2026-03-02T17:33:22.611538Z"
    }
  ]
}
```

## Key Points

1. **Item Details**: Each item includes nested `item` object with `{ id, name, code }`
2. **Warehouse Details**:
   - Pick list level: `warehouse` object with `{ id, name, code }`
   - Item level: Each item has its own `warehouse` object with `{ id, name, code }`
3. **Reference Details**: Includes nested `reference` object with `{ id, reference_type, name, code }` for sales orders
4. **Nested Structure**: All related entities are nested objects, not just IDs
5. **Type Safety**: TypeScript types ensure proper structure throughout the app
6. **Display**: Components can directly access:
   - `pickList.warehouse.name`
   - `pickList.reference.code`
   - `item.item.name`
   - `item.warehouse.code`

## Backend Requirements

The backend API endpoint `/api/v1/pick-lists/{id}` now:

1. ✅ Joins with `items` table to get item details (item_code, item_name)
2. ✅ Joins with `warehouses_extended` table (Warehouse model) for:
   - Pick list level warehouse details
   - Each item's warehouse details
3. ✅ Joins with `sales_orders` table for reference details
4. ✅ Returns nested objects (not just IDs) for:
   - `warehouse`: `{ id, name, code }`
   - `reference`: `{ id, reference_type, name, code }`
   - `items[].item`: `{ id, name, code }`
   - `items[].warehouse`: `{ id, name, code }`

## Changes Made

### Backend Changes:

1. **Service Layer** (`pick_list_service.py`):

   - Added `_to_response_enriched()` method that performs joins
   - Queries `Item`, `WarehouseExtended`, and `SalesOrder` tables
   - Builds nested objects for all related entities

2. **Schema Layer** (`pick_list.py`):

   - Added `NestedReference` model for item/warehouse details
   - Added `NestedReferenceWithType` model for reference details
   - Updated `PickListItemResponse` to include `item` and `warehouse` nested objects
   - Updated `PickListResponse` to include `warehouse` and `reference` nested objects

3. **API Endpoint** (`pick_lists.py`):
   - No changes needed - uses updated service method automatically

### Frontend Changes:

1. **TypeScript Types**: Updated to match new response structure
2. **Components**: Updated to access nested properties (e.g., `item.item.name`, `item.warehouse.code`)
3. **Service**: No changes needed - automatically handles new response format
