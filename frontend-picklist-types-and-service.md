# Pick List API Integration - Customer and Warehouse Details

## Updated TypeScript Types

```typescript
// types/pickList.types.ts

export interface CustomerDetails {
  id: string;
  name: string;
  code: string;
}

export interface WarehouseDetails {
  id: string;
  name: string;
  code: string;
}

export interface PickListItem {
  id: string;
  item_id: string;
  item_code?: string;
  item_name?: string;
  warehouse_id: string;
  warehouse?: WarehouseDetails;
  qty: number;
  picked_qty: number;
  uom: string;
}

export interface PickList {
  id: string;
  pick_list_no: string;
  status: "draft" | "in_progress" | "completed" | "cancelled";
  sales_order_id: string;
  sales_order_no: string;
  customer_id: string;
  customer: CustomerDetails;
  items: PickListItem[];
  remarks: string | null;
  created_at: string;
  updated_at: string;
  created_by: string | null;
}

export interface PickListListItem {
  id: string;
  pick_list_no: string;
  status: string;
  sales_order_no: string;
  customer: CustomerDetails;
  items_count: number;
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

      {/* Customer Details */}
      <div className="info-section">
        <h3>Customer Information</h3>
        <div className="info-grid">
          <div className="info-item">
            <label>Customer Code:</label>
            <span>{pickList.customer.code}</span>
          </div>
          <div className="info-item">
            <label>Customer Name:</label>
            <span>{pickList.customer.name}</span>
          </div>
          <div className="info-item">
            <label>Customer ID:</label>
            <span>{pickList.customer.id}</span>
          </div>
        </div>
      </div>

      {/* Sales Order Reference */}
      <div className="info-section">
        <h3>Sales Order</h3>
        <div className="info-item">
          <label>Sales Order No:</label>
          <a href={`/sales-orders/${pickList.sales_order_id}`}>
            {pickList.sales_order_no}
          </a>
        </div>
      </div>

      {/* Pick List Items with Warehouse Details */}
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
                <td>{item.item_code || item.item_id}</td>
                <td>{item.item_name || "-"}</td>
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

When calling `GET /api/v1/pick-lists/{id}`, the response should include:

```json
{
  "id": "uuid",
  "pick_list_no": "PL-2025-0001",
  "status": "draft",
  "sales_order_id": "uuid",
  "sales_order_no": "SO-2025-0001",
  "customer_id": "08d25496-002c-4edb-b033-a76a9acfa674",
  "customer": {
    "id": "08d25496-002c-4edb-b033-a76a9acfa674",
    "name": "Huge Rock",
    "code": "HRU-01"
  },
  "items": [
    {
      "id": "uuid",
      "item_id": "uuid",
      "item_code": "ITEM-001",
      "item_name": "Widget A",
      "warehouse_id": "uuid",
      "warehouse": {
        "id": "uuid",
        "name": "Main Warehouse",
        "code": "WH-MAIN"
      },
      "qty": 50,
      "picked_qty": 0,
      "uom": "Pieces"
    }
  ],
  "remarks": null,
  "created_at": "2025-06-15T10:30:00Z",
  "updated_at": "2025-06-15T10:30:00Z",
  "created_by": "user@example.com"
}
```

## Key Points

1. **Customer Details**: Always included in the format `{ id, name, code }`
2. **Warehouse Details**: Included for each item in the format `{ id, name, code }`
3. **Nested Structure**: Customer and warehouse are nested objects, not just IDs
4. **Type Safety**: TypeScript types ensure proper structure throughout the app
5. **Display**: Components can directly access `pickList.customer.name` and `item.warehouse.code`

## Backend Requirements

The backend API endpoint `/api/v1/pick-lists/{id}` must:

1. Join with `customers` table to get customer details
2. Join with `warehouses` table for each pick list item
3. Return nested objects (not just IDs) for customer and warehouse
4. Include code, name, and id for both customer and warehouse entities
