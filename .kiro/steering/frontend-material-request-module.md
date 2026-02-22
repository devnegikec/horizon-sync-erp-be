---
title: Frontend Material Request Module - Implementation Guide
description: Complete guide for building the Material Request module for sourcing workflow
tags: [frontend, material-request, sourcing, procurement, api-integration]
---

# Frontend Material Request Module - Implementation Guide

## Overview

Build a comprehensive Material Request module that enables users to:

1. Create material requests with type (purchase/transfer/issue) and priority
2. Add line items with UOM, estimated costs, and internal customer details
3. Submit requests for procurement processing
4. Track request status through the sourcing workflow
5. View and manage material request history
6. Auto-generate human-readable request numbers

## API Endpoints Reference

### Base URL

```
http://localhost:8001/api/v1/material-requests
```

### Authentication

All requests require Bearer token in Authorization header:

```
Authorization: Bearer {token}
```

### Available Endpoints

1. **Create Material Request** - `POST /material-requests`
2. **List Material Requests** - `GET /material-requests`
3. **Get Material Request** - `GET /material-requests/{id}`
4. **Update Material Request** - `PATCH /material-requests/{id}` (DRAFT only)
5. **Delete Material Request** - `DELETE /material-requests/{id}` (DRAFT only)
6. **Submit Material Request** - `POST /material-requests/{id}/submit`
7. **Cancel Material Request** - `POST /material-requests/{id}/cancel`

## Module Structure

```
src/
├── features/
│   └── material-requests/
│       ├── components/
│       │   ├── MaterialRequestForm.tsx        # Main form for create/edit
│       │   ├── MaterialRequestList.tsx        # List view with filters
│       │   ├── MaterialRequestDetail.tsx      # Single request view
│       │   ├── LineItemsTable.tsx             # Line items management
│       │   ├── LineItemForm.tsx               # Add/edit line item
│       │   ├── RequestTypeSelector.tsx        # Purchase/Transfer/Issue
│       │   ├── PriorityBadge.tsx              # Priority indicator
│       │   ├── StatusBadge.tsx                # Status indicator
│       │   └── RequestFilters.tsx             # Filter by type, priority, status
│       ├── hooks/
│       │   ├── useMaterialRequests.ts         # Fetch requests list
│       │   ├── useMaterialRequest.ts          # Fetch single request
│       │   ├── useCreateMaterialRequest.ts    # Create request
│       │   ├── useUpdateMaterialRequest.ts    # Update request
│       │   ├── useSubmitMaterialRequest.ts    # Submit request
│       │   └── useCancelMaterialRequest.ts    # Cancel request
│       ├── services/
│       │   └── materialRequestService.ts      # API service layer
│       ├── types/
│       │   └── materialRequest.types.ts       # TypeScript types
│       └── utils/
│           ├── requestNumberGenerator.ts      # Generate MR-YYYY-NNNN
│           └── costCalculations.ts            # Calculate total costs
```

## TypeScript Types

```typescript
// materialRequest.types.ts

export type MaterialRequestType = "purchase" | "transfer" | "issue";

export type MaterialRequestPriority = "low" | "medium" | "high" | "urgent";

export type MaterialRequestStatus =
  | "draft"
  | "submitted"
  | "partially_quoted"
  | "fully_quoted"
  | "cancelled";

export interface MaterialRequestLine {
  id?: string;
  item_id: string;
  quantity: number;
  uom: string | null;
  required_date: string; // ISO date format
  description: string | null;
  estimated_unit_cost: number | null;
  requested_for: string | null;
  requested_for_department: string | null;
}

export interface MaterialRequestLineResponse extends MaterialRequestLine {
  id: string;
  organization_id: string;
  material_request_id: string;
  created_at: string;
  updated_at: string;
}

export interface MaterialRequestCreate {
  request_no?: string; // Optional, auto-generated if not provided
  type: MaterialRequestType;
  priority: MaterialRequestPriority;
  target_warehouse_id?: string | null;
  requested_by?: string | null;
  department?: string | null;
  notes?: string | null;
  line_items: MaterialRequestLine[];
}

export interface MaterialRequestUpdate {
  request_no?: string;
  type?: MaterialRequestType;
  priority?: MaterialRequestPriority;
  target_warehouse_id?: string | null;
  requested_by?: string | null;
  department?: string | null;
  notes?: string | null;
  line_items?: MaterialRequestLine[];
}

export interface MaterialRequest {
  id: string;
  organization_id: string;
  request_no: string;
  type: MaterialRequestType;
  priority: MaterialRequestPriority;
  status: MaterialRequestStatus;
  target_warehouse_id: string | null;
  requested_by: string | null;
  department: string | null;
  notes: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  line_items: MaterialRequestLineResponse[];
}

export interface MaterialRequestListItem {
  id: string;
  organization_id: string;
  request_no: string;
  type: MaterialRequestType;
  priority: MaterialRequestPriority;
  status: MaterialRequestStatus;
  department: string | null;
  created_at: string;
  created_by: string | null;
  line_items_count: number;
}

export interface MaterialRequestListResponse {
  material_requests: MaterialRequestListItem[];
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

## API Service Implementation

```typescript
// services/materialRequestService.ts

import axios from "axios";
import type {
  MaterialRequestCreate,
  MaterialRequestUpdate,
  MaterialRequest,
  MaterialRequestListResponse,
} from "../types/materialRequest.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class MaterialRequestService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async createMaterialRequest(
    data: MaterialRequestCreate,
  ): Promise<MaterialRequest> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/material-requests`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async getMaterialRequests(params?: {
    page?: number;
    page_size?: number;
    status?: string;
    sort_by?: string;
    sort_order?: string;
    search?: string;
  }): Promise<MaterialRequestListResponse> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/material-requests`,
      {
        headers: this.getHeaders(),
        params,
      },
    );
    return response.data;
  }

  async getMaterialRequest(id: string): Promise<MaterialRequest> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/material-requests/${id}`,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async updateMaterialRequest(
    id: string,
    data: MaterialRequestUpdate,
  ): Promise<MaterialRequest> {
    const response = await axios.patch(
      `${API_BASE_URL}/api/v1/material-requests/${id}`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async deleteMaterialRequest(id: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/api/v1/material-requests/${id}`, {
      headers: this.getHeaders(),
    });
  }

  async submitMaterialRequest(id: string): Promise<MaterialRequest> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/material-requests/${id}/submit`,
      {},
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async cancelMaterialRequest(id: string): Promise<MaterialRequest> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/material-requests/${id}/cancel`,
      {},
      { headers: this.getHeaders() },
    );
    return response.data;
  }
}

export const materialRequestService = new MaterialRequestService();
```

## React Hooks

```typescript
// hooks/useCreateMaterialRequest.ts

import { useState } from "react";
import { materialRequestService } from "../services/materialRequestService";
import type {
  MaterialRequestCreate,
  MaterialRequest,
} from "../types/materialRequest.types";

export const useCreateMaterialRequest = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createMaterialRequest = async (
    data: MaterialRequestCreate,
  ): Promise<MaterialRequest> => {
    setLoading(true);
    setError(null);

    try {
      const result = await materialRequestService.createMaterialRequest(data);
      return result;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to create material request";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createMaterialRequest, loading, error };
};
```

```typescript
// hooks/useMaterialRequests.ts

import { useState, useEffect } from "react";
import { materialRequestService } from "../services/materialRequestService";
import type { MaterialRequestListResponse } from "../types/materialRequest.types";

export const useMaterialRequests = (filters?: {
  status?: string;
  search?: string;
}) => {
  const [data, setData] = useState<MaterialRequestListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchMaterialRequests = async (page = 1) => {
    setLoading(true);
    try {
      const result = await materialRequestService.getMaterialRequests({
        page,
        page_size: 20,
        ...filters,
      });
      setData(result);
    } catch (err: any) {
      setError(
        err.response?.data?.detail || "Failed to fetch material requests",
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMaterialRequests();
  }, [filters?.status, filters?.search]);

  return { data, loading, error, refetch: fetchMaterialRequests };
};
```

```typescript
// hooks/useSubmitMaterialRequest.ts

import { useState } from "react";
import { materialRequestService } from "../services/materialRequestService";
import type { MaterialRequest } from "../types/materialRequest.types";

export const useSubmitMaterialRequest = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submitMaterialRequest = async (
    id: string,
  ): Promise<MaterialRequest> => {
    setLoading(true);
    setError(null);

    try {
      const result = await materialRequestService.submitMaterialRequest(id);
      return result;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to submit material request";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { submitMaterialRequest, loading, error };
};
```

## Component Examples

### Material Request Form Component

```typescript
// components/MaterialRequestForm.tsx

import React, { useState } from "react";
import { useCreateMaterialRequest } from "../hooks/useCreateMaterialRequest";
import { LineItemsTable } from "./LineItemsTable";
import type {
  MaterialRequestCreate,
  MaterialRequestLine,
  MaterialRequestType,
  MaterialRequestPriority,
} from "../types/materialRequest.types";

interface MaterialRequestFormProps {
  onSuccess?: (materialRequest: any) => void;
  onCancel?: () => void;
}

export const MaterialRequestForm: React.FC<MaterialRequestFormProps> = ({
  onSuccess,
  onCancel,
}) => {
  const { createMaterialRequest, loading, error } = useCreateMaterialRequest();

  const [type, setType] = useState<MaterialRequestType>("purchase");
  const [priority, setPriority] = useState<MaterialRequestPriority>("medium");
  const [department, setDepartment] = useState("");
  const [notes, setNotes] = useState("");
  const [lineItems, setLineItems] = useState<MaterialRequestLine[]>([]);

  const handleAddLineItem = (item: MaterialRequestLine) => {
    setLineItems([...lineItems, item]);
  };

  const handleRemoveLineItem = (index: number) => {
    setLineItems(lineItems.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (lineItems.length === 0) {
      alert("Please add at least one line item");
      return;
    }

    try {
      const data: MaterialRequestCreate = {
        type,
        priority,
        department: department || null,
        notes: notes || null,
        line_items: lineItems,
      };

      const result = await createMaterialRequest(data);
      onSuccess?.(result);
    } catch (err) {
      // Error handled by hook
    }
  };

  return (
    <form onSubmit={handleSubmit} className="material-request-form">
      <h2>Create Material Request</h2>

      <div className="form-row">
        <div className="form-group">
          <label>Request Type *</label>
          <select
            value={type}
            onChange={(e) => setType(e.target.value as MaterialRequestType)}
            required
          >
            <option value="purchase">Purchase (Buy from vendor)</option>
            <option value="transfer">Transfer (Move between warehouses)</option>
            <option value="issue">Issue (Give to department)</option>
          </select>
        </div>

        <div className="form-group">
          <label>Priority *</label>
          <select
            value={priority}
            onChange={(e) =>
              setPriority(e.target.value as MaterialRequestPriority)
            }
            required
          >
            <option value="low">Low</option>
            <option value="medium">Medium</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
        </div>
      </div>

      <div className="form-group">
        <label>Department</label>
        <input
          type="text"
          value={department}
          onChange={(e) => setDepartment(e.target.value)}
          placeholder="e.g., Production, Maintenance"
          maxLength={100}
        />
      </div>

      <div className="form-group">
        <label>Notes</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={3}
          placeholder="Additional information about this request"
        />
      </div>

      <div className="line-items-section">
        <h3>Line Items</h3>
        <LineItemsTable
          items={lineItems}
          onAdd={handleAddLineItem}
          onRemove={handleRemoveLineItem}
        />
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="form-actions">
        <button type="button" onClick={onCancel} disabled={loading}>
          Cancel
        </button>
        <button type="submit" disabled={loading || lineItems.length === 0}>
          {loading ? "Creating..." : "Create Material Request"}
        </button>
      </div>
    </form>
  );
};
```

### Line Items Table Component

```typescript
// components/LineItemsTable.tsx

import React, { useState } from "react";
import { LineItemForm } from "./LineItemForm";
import type { MaterialRequestLine } from "../types/materialRequest.types";

interface LineItemsTableProps {
  items: MaterialRequestLine[];
  onAdd: (item: MaterialRequestLine) => void;
  onRemove: (index: number) => void;
  readOnly?: boolean;
}

export const LineItemsTable: React.FC<LineItemsTableProps> = ({
  items,
  onAdd,
  onRemove,
  readOnly = false,
}) => {
  const [showForm, setShowForm] = useState(false);

  const handleAdd = (item: MaterialRequestLine) => {
    onAdd(item);
    setShowForm(false);
  };

  const calculateTotal = () => {
    return items.reduce((sum, item) => {
      const cost = item.estimated_unit_cost || 0;
      return sum + item.quantity * cost;
    }, 0);
  };

  return (
    <div className="line-items-table">
      {items.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>Item</th>
              <th>Quantity</th>
              <th>UOM</th>
              <th>Required Date</th>
              <th>Est. Unit Cost</th>
              <th>Est. Total</th>
              <th>Requested For</th>
              {!readOnly && <th>Actions</th>}
            </tr>
          </thead>
          <tbody>
            {items.map((item, index) => (
              <tr key={index}>
                <td>{item.item_id}</td>
                <td>{item.quantity}</td>
                <td>{item.uom || "-"}</td>
                <td>{item.required_date}</td>
                <td>
                  {item.estimated_unit_cost
                    ? `$${item.estimated_unit_cost.toFixed(2)}`
                    : "-"}
                </td>
                <td>
                  {item.estimated_unit_cost
                    ? `$${(item.quantity * item.estimated_unit_cost).toFixed(2)}`
                    : "-"}
                </td>
                <td>{item.requested_for || "-"}</td>
                {!readOnly && (
                  <td>
                    <button
                      type="button"
                      onClick={() => onRemove(index)}
                      className="btn-remove"
                    >
                      Remove
                    </button>
                  </td>
                )}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={5} style={{ textAlign: "right" }}>
                <strong>Total Estimated Cost:</strong>
              </td>
              <td>
                <strong>${calculateTotal().toFixed(2)}</strong>
              </td>
              <td colSpan={readOnly ? 1 : 2}></td>
            </tr>
          </tfoot>
        </table>
      )}

      {!readOnly && (
        <>
          {showForm ? (
            <LineItemForm
              onSubmit={handleAdd}
              onCancel={() => setShowForm(false)}
            />
          ) : (
            <button
              type="button"
              onClick={() => setShowForm(true)}
              className="btn-add-item"
            >
              + Add Line Item
            </button>
          )}
        </>
      )}

      {items.length === 0 && !showForm && (
        <p className="no-items">No line items added yet</p>
      )}
    </div>
  );
};
```

### Line Item Form Component

```typescript
// components/LineItemForm.tsx

import React, { useState } from "react";
import type { MaterialRequestLine } from "../types/materialRequest.types";

interface LineItemFormProps {
  onSubmit: (item: MaterialRequestLine) => void;
  onCancel: () => void;
}

export const LineItemForm: React.FC<LineItemFormProps> = ({
  onSubmit,
  onCancel,
}) => {
  const [itemId, setItemId] = useState("");
  const [quantity, setQuantity] = useState<number>(1);
  const [uom, setUom] = useState("");
  const [requiredDate, setRequiredDate] = useState("");
  const [description, setDescription] = useState("");
  const [estimatedUnitCost, setEstimatedUnitCost] = useState<number | null>(
    null
  );
  const [requestedFor, setRequestedFor] = useState("");
  const [requestedForDepartment, setRequestedForDepartment] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const item: MaterialRequestLine = {
      item_id: itemId,
      quantity,
      uom: uom || null,
      required_date: requiredDate,
      description: description || null,
      estimated_unit_cost: estimatedUnitCost,
      requested_for: requestedFor || null,
      requested_for_department: requestedForDepartment || null,
    };

    onSubmit(item);

    // Reset form
    setItemId("");
    setQuantity(1);
    setUom("");
    setRequiredDate("");
    setDescription("");
    setEstimatedUnitCost(null);
    setRequestedFor("");
    setRequestedForDepartment("");
  };

  return (
    <div className="line-item-form">
      <h4>Add Line Item</h4>
      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <div className="form-group">
            <label>Item *</label>
            <input
              type="text"
              value={itemId}
              onChange={(e) => setItemId(e.target.value)}
              placeholder="Select or enter item"
              required
            />
          </div>

          <div className="form-group">
            <label>Quantity *</label>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
              min="0.0001"
              step="0.01"
              required
            />
          </div>

          <div className="form-group">
            <label>UOM</label>
            <input
              type="text"
              value={uom}
              onChange={(e) => setUom(e.target.value)}
              placeholder="Kgs, Boxes, Pieces"
              maxLength={50}
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Required Date *</label>
            <input
              type="date"
              value={requiredDate}
              onChange={(e) => setRequiredDate(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label>Estimated Unit Cost</label>
            <input
              type="number"
              value={estimatedUnitCost || ""}
              onChange={(e) =>
                setEstimatedUnitCost(
                  e.target.value ? Number(e.target.value) : null
                )
              }
              min="0"
              step="0.01"
              placeholder="0.00"
            />
          </div>
        </div>

        <div className="form-group">
          <label>Description</label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={2}
            placeholder="Additional details about this item"
          />
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Requested For</label>
            <input
              type="text"
              value={requestedFor}
              onChange={(e) => setRequestedFor(e.target.value)}
              placeholder="Employee name or ID"
              maxLength={255}
            />
          </div>

          <div className="form-group">
            <label>Requested For Department</label>
            <input
              type="text"
              value={requestedForDepartment}
              onChange={(e) => setRequestedForDepartment(e.target.value)}
              placeholder="Department name"
              maxLength={100}
            />
          </div>
        </div>

        <div className="form-actions">
          <button type="button" onClick={onCancel}>
            Cancel
          </button>
          <button type="submit">Add Item</button>
        </div>
      </form>
    </div>
  );
};
```

### Material Request List Component

```typescript
// components/MaterialRequestList.tsx

import React, { useState } from "react";
import { useMaterialRequests } from "../hooks/useMaterialRequests";
import { StatusBadge } from "./StatusBadge";
import { PriorityBadge } from "./PriorityBadge";
import { format } from "date-fns";

export const MaterialRequestList: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState("");

  const { data, loading, error, refetch } = useMaterialRequests({
    status: statusFilter || undefined,
    search: searchQuery || undefined,
  });

  if (loading) return <div>Loading material requests...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data) return null;

  return (
    <div className="material-request-list">
      <div className="list-header">
        <h2>Material Requests</h2>
        <button className="btn-primary">+ New Material Request</button>
      </div>

      <div className="filters">
        <input
          type="text"
          placeholder="Search..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
        />

        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="submitted">Submitted</option>
          <option value="partially_quoted">Partially Quoted</option>
          <option value="fully_quoted">Fully Quoted</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      <table className="material-requests-table">
        <thead>
          <tr>
            <th>Request No</th>
            <th>Type</th>
            <th>Priority</th>
            <th>Status</th>
            <th>Department</th>
            <th>Items</th>
            <th>Created</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {data.material_requests.map((mr) => (
            <tr key={mr.id}>
              <td>
                <a href={`/material-requests/${mr.id}`}>{mr.request_no}</a>
              </td>
              <td>
                <span className={`type-badge type-${mr.type}`}>
                  {mr.type}
                </span>
              </td>
              <td>
                <PriorityBadge priority={mr.priority} />
              </td>
              <td>
                <StatusBadge status={mr.status} />
              </td>
              <td>{mr.department || "-"}</td>
              <td>{mr.line_items_count}</td>
              <td>{format(new Date(mr.created_at), "MMM dd, yyyy")}</td>
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

### Status and Priority Badge Components

```typescript
// components/StatusBadge.tsx

import React from "react";
import type { MaterialRequestStatus } from "../types/materialRequest.types";

interface StatusBadgeProps {
  status: MaterialRequestStatus;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const getStatusColor = () => {
    switch (status) {
      case "draft":
        return "gray";
      case "submitted":
        return "blue";
      case "partially_quoted":
        return "yellow";
      case "fully_quoted":
        return "green";
      case "cancelled":
        return "red";
      default:
        return "gray";
    }
  };

  const getStatusLabel = () => {
    return status
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  return (
    <span className={`status-badge status-${getStatusColor()}`}>
      {getStatusLabel()}
    </span>
  );
};
```

```typescript
// components/PriorityBadge.tsx

import React from "react";
import type { MaterialRequestPriority } from "../types/materialRequest.types";

interface PriorityBadgeProps {
  priority: MaterialRequestPriority;
}

export const PriorityBadge: React.FC<PriorityBadgeProps> = ({ priority }) => {
  const getPriorityIcon = () => {
    switch (priority) {
      case "urgent":
        return "🔴";
      case "high":
        return "🟠";
      case "medium":
        return "🟡";
      case "low":
        return "🟢";
      default:
        return "";
    }
  };

  return (
    <span className={`priority-badge priority-${priority}`}>
      {getPriorityIcon()} {priority.charAt(0).toUpperCase() + priority.slice(1)}
    </span>
  );
};
```

### Material Request Detail Component

```typescript
// components/MaterialRequestDetail.tsx

import React from "react";
import { useParams } from "react-router-dom";
import { useMaterialRequest } from "../hooks/useMaterialRequest";
import { useSubmitMaterialRequest } from "../hooks/useSubmitMaterialRequest";
import { useCancelMaterialRequest } from "../hooks/useCancelMaterialRequest";
import { StatusBadge } from "./StatusBadge";
import { PriorityBadge } from "./PriorityBadge";
import { LineItemsTable } from "./LineItemsTable";
import { format } from "date-fns";

export const MaterialRequestDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { data: mr, loading, error, refetch } = useMaterialRequest(id!);
  const { submitMaterialRequest, loading: submitting } =
    useSubmitMaterialRequest();
  const { cancelMaterialRequest, loading: cancelling } =
    useCancelMaterialRequest();

  const handleSubmit = async () => {
    if (!mr) return;
    try {
      await submitMaterialRequest(mr.id);
      refetch();
      alert("Material request submitted successfully!");
    } catch (err) {
      // Error handled by hook
    }
  };

  const handleCancel = async () => {
    if (!mr) return;
    if (!confirm("Are you sure you want to cancel this material request?"))
      return;

    try {
      await cancelMaterialRequest(mr.id);
      refetch();
      alert("Material request cancelled successfully!");
    } catch (err) {
      // Error handled by hook
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!mr) return <div>Material request not found</div>;

  return (
    <div className="material-request-detail">
      <div className="detail-header">
        <div>
          <h1>Material Request {mr.request_no}</h1>
          <div className="badges">
            <StatusBadge status={mr.status} />
            <PriorityBadge priority={mr.priority} />
            <span className={`type-badge type-${mr.type}`}>{mr.type}</span>
          </div>
        </div>

        <div className="actions">
          {mr.status === "draft" && (
            <>
              <button onClick={() => {/* Navigate to edit */}}>Edit</button>
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="btn-primary"
              >
                {submitting ? "Submitting..." : "Submit"}
              </button>
            </>
          )}
          {mr.status !== "cancelled" && mr.status !== "draft" && (
            <button
              onClick={handleCancel}
              disabled={cancelling}
              className="btn-danger"
            >
              {cancelling ? "Cancelling..." : "Cancel Request"}
            </button>
          )}
        </div>
      </div>

      <div className="detail-info">
        <div className="info-section">
          <h3>Request Information</h3>
          <div className="info-grid">
            <div className="info-item">
              <label>Request Number:</label>
              <span>{mr.request_no}</span>
            </div>
            <div className="info-item">
              <label>Type:</label>
              <span>{mr.type}</span>
            </div>
            <div className="info-item">
              <label>Priority:</label>
              <span>{mr.priority}</span>
            </div>
            <div className="info-item">
              <label>Department:</label>
              <span>{mr.department || "-"}</span>
            </div>
            <div className="info-item">
              <label>Created:</label>
              <span>{format(new Date(mr.created_at), "MMM dd, yyyy HH:mm")}</span>
            </div>
            <div className="info-item">
              <label>Updated:</label>
              <span>{format(new Date(mr.updated_at), "MMM dd, yyyy HH:mm")}</span>
            </div>
          </div>
        </div>

        {mr.notes && (
          <div className="info-section">
            <h3>Notes</h3>
            <p>{mr.notes}</p>
          </div>
        )}
      </div>

      <div className="line-items-section">
        <h3>Line Items ({mr.line_items.length})</h3>
        <LineItemsTable
          items={mr.line_items}
          onAdd={() => {}}
          onRemove={() => {}}
          readOnly={true}
        />
      </div>
    </div>
  );
};
```
