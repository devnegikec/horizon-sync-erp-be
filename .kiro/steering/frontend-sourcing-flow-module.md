---
title: Frontend Sourcing Flow Module - Complete Procure-to-Pay Implementation
description: Complete guide for building the Sourcing Flow (Material Request → RFQ → Purchase Order → Receipt → Invoice → Payment)
tags: [frontend, sourcing, procurement, rfq, purchase-order, procure-to-pay]
---

# Frontend Sourcing Flow Module - Implementation Guide

## Overview

Build a complete Procure-to-Pay workflow that enables users to:

1. Create Material Requests for items needed
2. Convert Material Requests to RFQs (Request for Quotation)
3. Send RFQs to suppliers and collect quotes
4. Convert RFQs to Purchase Orders
5. Create Receipt Notes from Purchase Orders
6. Generate Purchase Invoices from Purchase Orders
7. Make Payments against Purchase Invoices
8. Track the complete workflow with status updates

## Workflow Diagram

```
Material Request → RFQ → Purchase Order → Receipt Note → Purchase Invoice → Payment Made
     (new)        (new)      (new)         (existing)      (existing)        (existing)
```

## API Endpoints Reference

### Base URLs

```
Material Requests: http://localhost:8001/api/v1/material-requests
RFQs: http://localhost:8001/api/v1/rfqs
Purchase Orders: http://localhost:8001/api/v1/purchase-orders
Suppliers: http://localhost:8001/api/v1/suppliers
Purchase Receipts: http://localhost:8001/api/v1/purchase-receipts
Invoices: http://localhost:8001/api/v1/invoices
Payments: http://localhost:8001/api/v1/payments
```

### Authentication

All requests require Bearer token:

```
Authorization: Bearer {token}
```

## Module Structure

```
src/
├── features/
│   └── sourcing/
│       ├── components/
│       │   ├── material-requests/
│       │   │   ├── MaterialRequestForm.tsx
│       │   │   ├── MaterialRequestList.tsx
│       │   │   ├── MaterialRequestDetail.tsx
│       │   │   └── ConvertToRFQButton.tsx
│       │   ├── rfqs/
│       │   │   ├── RFQForm.tsx
│       │   │   ├── RFQList.tsx
│       │   │   ├── RFQDetail.tsx
│       │   │   ├── SupplierQuoteForm.tsx
│       │   │   ├── QuoteComparison.tsx
│       │   │   └── ConvertToPOButton.tsx
│       │   ├── purchase-orders/
│       │   │   ├── PurchaseOrderForm.tsx
│       │   │   ├── PurchaseOrderList.tsx
│       │   │   ├── PurchaseOrderDetail.tsx
│       │   │   ├── CreateReceiptButton.tsx
│       │   │   └── CreateInvoiceButton.tsx
│       │   ├── shared/
│       │   │   ├── LineItemsTable.tsx
│       │   │   ├── StatusBadge.tsx
│       │   │   ├── WorkflowTimeline.tsx
│       │   │   └── DocumentReference.tsx
│       ├── hooks/
│       │   ├── useMaterialRequests.ts
│       │   ├── useRFQs.ts
│       │   ├── usePurchaseOrders.ts
│       │   ├── useConvertToRFQ.ts
│       │   ├── useConvertToPO.ts
│       │   └── useWorkflowStatus.ts
│       ├── services/
│       │   ├── materialRequestService.ts
│       │   ├── rfqService.ts
│       │   ├── purchaseOrderService.ts
│       │   └── workflowService.ts
│       ├── types/
│       │   └── sourcing.types.ts
│       └── utils/
│           ├── statusHelpers.ts
│           └── conversionHelpers.ts
```

## TypeScript Types

```typescript
// sourcing.types.ts

// ============================================
// MATERIAL REQUEST TYPES
// ============================================

export type MaterialRequestStatus =
  | "draft"
  | "submitted"
  | "partially_quoted"
  | "fully_quoted"
  | "cancelled";

export interface MaterialRequest {
  id: string;
  organization_id: string;
  request_no: string;
  type: "purchase" | "transfer" | "issue";
  priority: "low" | "medium" | "high" | "urgent";
  status: MaterialRequestStatus;
  target_warehouse_id: string | null;
  requested_by: string | null;
  department: string | null;
  notes: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  line_items: MaterialRequestLine[];
}

export interface MaterialRequestLine {
  id: string;
  material_request_id: string;
  item_id: string;
  quantity: number;
  uom: string | null;
  required_date: string;
  description: string | null;
  estimated_unit_cost: number | null;
  requested_for: string | null;
  requested_for_department: string | null;
}

// ============================================
// RFQ TYPES
// ============================================

export type RFQStatus =
  | "draft"
  | "sent"
  | "partially_responded"
  | "fully_responded"
  | "closed";

export interface RFQ {
  id: string;
  organization_id: string;
  material_request_id: string | null;
  reference_type: "material_request" | null;
  reference_id: string | null;
  status: RFQStatus;
  closing_date: string;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  line_items: RFQLine[];
  suppliers: RFQSupplier[];
}

export interface RFQLine {
  id: string;
  rfq_id: string;
  item_id: string;
  quantity: number;
  required_date: string;
  description: string | null;
  quotes: SupplierQuote[];
}

export interface RFQSupplier {
  id: string;
  rfq_id: string;
  supplier_id: string;
  supplier_name?: string;
}

export interface SupplierQuote {
  id: string;
  rfq_line_id: string;
  supplier_id: string;
  supplier_name?: string;
  quoted_price: number;
  quoted_delivery_date: string;
  supplier_notes: string | null;
  created_at: string;
}

// ============================================
// PURCHASE ORDER TYPES
// ============================================

export type PurchaseOrderStatus =
  | "draft"
  | "submitted"
  | "partially_received"
  | "fully_received"
  | "closed"
  | "cancelled";

export interface PurchaseOrder {
  id: string;
  organization_id: string;
  rfq_id: string | null;
  reference_type: "rfq" | null;
  reference_id: string | null;
  party_type: "supplier";
  party_id: string;
  supplier_name?: string;
  status: PurchaseOrderStatus;
  subtotal: number;
  tax_amount: number;
  tax_rate: number | null;
  discount_amount: number;
  grand_total: number;
  created_at: string;
  updated_at: string;
  created_by: string | null;
  line_items: PurchaseOrderLine[];
}

export interface PurchaseOrderLine {
  id: string;
  purchase_order_id: string;
  item_id: string;
  item_name?: string;
  quantity: number;
  unit_price: number;
  line_total: number;
  received_quantity: number;
}

// ============================================
// CONVERSION TYPES
// ============================================

export interface ConvertToRFQRequest {
  material_request_id: string;
  supplier_ids: string[];
  closing_date: string;
  line_item_ids?: string[]; // Optional: select specific line items
}

export interface ConvertToPORequest {
  rfq_id: string;
  supplier_id: string;
  selected_quotes: {
    rfq_line_id: string;
    supplier_quote_id: string;
  }[];
  tax_rate?: number;
  discount_amount?: number;
}

// ============================================
// WORKFLOW TYPES
// ============================================

export interface WorkflowStatus {
  material_request?: {
    id: string;
    request_no: string;
    status: MaterialRequestStatus;
  };
  rfq?: {
    id: string;
    status: RFQStatus;
  };
  purchase_order?: {
    id: string;
    status: PurchaseOrderStatus;
  };
  receipts?: {
    id: string;
    received_date: string;
    status: string;
  }[];
  invoices?: {
    id: string;
    invoice_no: string;
    status: string;
  }[];
  payments?: {
    id: string;
    payment_date: string;
    amount: number;
  }[];
}
```

## API Services Implementation

### Material Request Service

```typescript
// services/materialRequestService.ts

import axios from "axios";
import type {
  MaterialRequest,
  MaterialRequestStatus,
} from "../types/sourcing.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class MaterialRequestService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async create(data: any): Promise<MaterialRequest> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/material-requests`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async getById(id: string): Promise<MaterialRequest> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/material-requests/${id}`,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async list(params?: any): Promise<any> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/material-requests`,
      {
        headers: this.getHeaders(),
        params,
      },
    );
    return response.data;
  }

  async update(id: string, data: any): Promise<MaterialRequest> {
    const response = await axios.patch(
      `${API_BASE_URL}/api/v1/material-requests/${id}`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async submit(id: string): Promise<MaterialRequest> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/material-requests/${id}/submit`,
      {},
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async cancel(id: string): Promise<MaterialRequest> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/material-requests/${id}/cancel`,
      {},
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async delete(id: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/api/v1/material-requests/${id}`, {
      headers: this.getHeaders(),
    });
  }
}

export const materialRequestService = new MaterialRequestService();
```

### RFQ Service

```typescript
// services/rfqService.ts

import axios from "axios";
import type {
  RFQ,
  ConvertToRFQRequest,
  SupplierQuote,
} from "../types/sourcing.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class RFQService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async create(data: any): Promise<RFQ> {
    const response = await axios.post(`${API_BASE_URL}/api/v1/rfqs`, data, {
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async createFromMaterialRequest(data: ConvertToRFQRequest): Promise<RFQ> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/rfqs/from-material-request`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async getById(id: string): Promise<RFQ> {
    const response = await axios.get(`${API_BASE_URL}/api/v1/rfqs/${id}`, {
      headers: this.getHeaders(),
    });
    return response.data;
  }

  async list(params?: any): Promise<any> {
    const response = await axios.get(`${API_BASE_URL}/api/v1/rfqs`, {
      headers: this.getHeaders(),
      params,
    });
    return response.data;
  }

  async update(id: string, data: any): Promise<RFQ> {
    const response = await axios.patch(
      `${API_BASE_URL}/api/v1/rfqs/${id}`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async send(id: string): Promise<RFQ> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/rfqs/${id}/send`,
      {},
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async addQuote(id: string, quoteData: any): Promise<SupplierQuote> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/rfqs/${id}/quotes`,
      quoteData,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async close(id: string): Promise<RFQ> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/rfqs/${id}/close`,
      {},
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async delete(id: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/api/v1/rfqs/${id}`, {
      headers: this.getHeaders(),
    });
  }
}

export const rfqService = new RFQService();
```

### Purchase Order Service

```typescript
// services/purchaseOrderService.ts

import axios from "axios";
import type {
  PurchaseOrder,
  ConvertToPORequest,
} from "../types/sourcing.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class PurchaseOrderService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async create(data: any): Promise<PurchaseOrder> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/purchase-orders`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async createFromRFQ(data: ConvertToPORequest): Promise<PurchaseOrder> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/purchase-orders/from-rfq`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async getById(id: string): Promise<PurchaseOrder> {
    const response = await axios.get(
      `${API_BASE_URL}/api/v1/purchase-orders/${id}`,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async list(params?: any): Promise<any> {
    const response = await axios.get(`${API_BASE_URL}/api/v1/purchase-orders`, {
      headers: this.getHeaders(),
      params,
    });
    return response.data;
  }

  async update(id: string, data: any): Promise<PurchaseOrder> {
    const response = await axios.patch(
      `${API_BASE_URL}/api/v1/purchase-orders/${id}`,
      data,
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async submit(id: string): Promise<PurchaseOrder> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/purchase-orders/${id}/submit`,
      {},
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async cancel(id: string): Promise<PurchaseOrder> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/purchase-orders/${id}/cancel`,
      {},
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async close(id: string): Promise<PurchaseOrder> {
    const response = await axios.post(
      `${API_BASE_URL}/api/v1/purchase-orders/${id}/close`,
      {},
      { headers: this.getHeaders() },
    );
    return response.data;
  }

  async delete(id: string): Promise<void> {
    await axios.delete(`${API_BASE_URL}/api/v1/purchase-orders/${id}`, {
      headers: this.getHeaders(),
    });
  }
}

export const purchaseOrderService = new PurchaseOrderService();
```

## React Hooks

### Convert to RFQ Hook

```typescript
// hooks/useConvertToRFQ.ts

import { useState } from "react";
import { rfqService } from "../services/rfqService";
import type { ConvertToRFQRequest, RFQ } from "../types/sourcing.types";

export const useConvertToRFQ = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const convertToRFQ = async (data: ConvertToRFQRequest): Promise<RFQ> => {
    setLoading(true);
    setError(null);

    try {
      const result = await rfqService.createFromMaterialRequest(data);
      return result;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to convert to RFQ";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { convertToRFQ, loading, error };
};
```

### Convert to Purchase Order Hook

```typescript
// hooks/useConvertToPO.ts

import { useState } from "react";
import { purchaseOrderService } from "../services/purchaseOrderService";
import type {
  ConvertToPORequest,
  PurchaseOrder,
} from "../types/sourcing.types";

export const useConvertToPO = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const convertToPO = async (
    data: ConvertToPORequest,
  ): Promise<PurchaseOrder> => {
    setLoading(true);
    setError(null);

    try {
      const result = await purchaseOrderService.createFromRFQ(data);
      return result;
    } catch (err: any) {
      const errorMessage =
        err.response?.data?.detail || "Failed to convert to Purchase Order";
      setError(errorMessage);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { convertToPO, loading, error };
};
```

### Workflow Status Hook

```typescript
// hooks/useWorkflowStatus.ts

import { useState, useEffect } from "react";
import { materialRequestService } from "../services/materialRequestService";
import { rfqService } from "../services/rfqService";
import { purchaseOrderService } from "../services/purchaseOrderService";
import type { WorkflowStatus } from "../types/sourcing.types";

export const useWorkflowStatus = (materialRequestId: string) => {
  const [status, setStatus] = useState<WorkflowStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchWorkflowStatus = async () => {
    setLoading(true);
    try {
      // Fetch Material Request
      const mr = await materialRequestService.getById(materialRequestId);

      const workflowStatus: WorkflowStatus = {
        material_request: {
          id: mr.id,
          request_no: mr.request_no,
          status: mr.status,
        },
      };

      // Fetch related RFQs
      const rfqsResponse = await rfqService.list({
        material_request_id: materialRequestId,
      });
      if (rfqsResponse.rfqs && rfqsResponse.rfqs.length > 0) {
        workflowStatus.rfq = {
          id: rfqsResponse.rfqs[0].id,
          status: rfqsResponse.rfqs[0].status,
        };

        // Fetch related Purchase Orders
        const posResponse = await purchaseOrderService.list({
          rfq_id: rfqsResponse.rfqs[0].id,
        });
        if (
          posResponse.purchase_orders &&
          posResponse.purchase_orders.length > 0
        ) {
          workflowStatus.purchase_order = {
            id: posResponse.purchase_orders[0].id,
            status: posResponse.purchase_orders[0].status,
          };
        }
      }

      setStatus(workflowStatus);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch workflow status");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWorkflowStatus();
  }, [materialRequestId]);

  return { status, loading, error, refetch: fetchWorkflowStatus };
};
```

## Component Examples

### Convert to RFQ Button Component

```typescript
// components/material-requests/ConvertToRFQButton.tsx

import React, { useState } from "react";
import { useConvertToRFQ } from "../../hooks/useConvertToRFQ";
import type { MaterialRequest } from "../../types/sourcing.types";

interface ConvertToRFQButtonProps {
  materialRequest: MaterialRequest;
  onSuccess?: (rfqId: string) => void;
}

export const ConvertToRFQButton: React.FC<ConvertToRFQButtonProps> = ({
  materialRequest,
  onSuccess,
}) => {
  const { convertToRFQ, loading, error } = useConvertToRFQ();
  const [showDialog, setShowDialog] = useState(false);
  const [selectedSuppliers, setSelectedSuppliers] = useState<string[]>([]);
  const [closingDate, setClosingDate] = useState("");

  const canConvert = materialRequest.status === "submitted";

  const handleConvert = async () => {
    if (selectedSuppliers.length === 0) {
      alert("Please select at least one supplier");
      return;
    }

    if (!closingDate) {
      alert("Please select a closing date");
      return;
    }

    try {
      const rfq = await convertToRFQ({
        material_request_id: materialRequest.id,
        supplier_ids: selectedSuppliers,
        closing_date: closingDate,
      });

      setShowDialog(false);
      onSuccess?.(rfq.id);
      alert(`RFQ created successfully! ID: ${rfq.id}`);
    } catch (err) {
      // Error handled by hook
    }
  };

  if (!canConvert) {
    return null;
  }

  return (
    <>
      <button
        onClick={() => setShowDialog(true)}
        className="btn-primary"
        disabled={loading}
      >
        Convert to RFQ
      </button>

      {showDialog && (
        <div className="modal-overlay">
          <div className="modal-content">
            <h2>Convert to RFQ</h2>
            <p>
              Material Request: {materialRequest.request_no}
            </p>

            <div className="form-group">
              <label>Select Suppliers *</label>
              <select
                multiple
                value={selectedSuppliers}
                onChange={(e) =>
                  setSelectedSuppliers(
                    Array.from(e.target.selectedOptions, (option) => option.value)
                  )
                }
                size={5}
              >
                {/* Fetch suppliers from API and populate */}
                <option value="supplier-1">Supplier 1</option>
                <option value="supplier-2">Supplier 2</option>
                <option value="supplier-3">Supplier 3</option>
              </select>
              <small>Hold Ctrl/Cmd to select multiple suppliers</small>
            </div>

            <div className="form-group">
              <label>Closing Date *</label>
              <input
                type="date"
                value={closingDate}
                onChange={(e) => setClosingDate(e.target.value)}
                min={new Date().toISOString().split("T")[0]}
                required
              />
            </div>

            {error && <div className="error-message">{error}</div>}

            <div className="modal-actions">
              <button
                onClick={() => setShowDialog(false)}
                disabled={loading}
              >
                Cancel
              </button>
              <button
                onClick={handleConvert}
                disabled={loading}
                className="btn-primary"
              >
                {loading ? "Converting..." : "Create RFQ"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
```

### Convert to Purchase Order Button Component

```typescript
// components/rfqs/ConvertToPOButton.tsx

import React, { useState } from "react";
import { useConvertToPO } from "../../hooks/useConvertToPO";
import type { RFQ, SupplierQuote } from "../../types/sourcing.types";

interface ConvertToPOButtonProps {
  rfq: RFQ;
  onSuccess?: (poId: string) => void;
}

export const ConvertToPOButton: React.FC<ConvertToPOButtonProps> = ({
  rfq,
  onSuccess,
}) => {
  const { convertToPO, loading, error } = useConvertToPO();
  const [showDialog, setShowDialog] = useState(false);
  const [selectedSupplierId, setSelectedSupplierId] = useState("");
  const [selectedQuotes, setSelectedQuotes] = useState<Map<string, string>>(
    new Map()
  );
  const [taxRate, setTaxRate] = useState<number>(0);
  const [discountAmount, setDiscountAmount] = useState<number>(0);

  const canConvert =
    rfq.status === "fully_responded" || rfq.status === "partially_responded";

  // Get unique suppliers who have provided quotes
  const suppliersWithQuotes = Array.from(
    new Set(
      rfq.line_items.flatMap((line) =>
        line.quotes.map((q) => q.supplier_id)
      )
    )
  );

  const handleSupplierChange = (supplierId: string) => {
    setSelectedSupplierId(supplierId);
    // Auto-select quotes from this supplier
    const newSelectedQuotes = new Map<string, string>();
    rfq.line_items.forEach((line) => {
      const supplierQuote = line.quotes.find(
        (q) => q.supplier_id === supplierId
      );
      if (supplierQuote) {
        newSelectedQuotes.set(line.id, supplierQuote.id);
      }
    });
    setSelectedQuotes(newSelectedQuotes);
  };

  const handleConvert = async () => {
    if (!selectedSupplierId) {
      alert("Please select a supplier");
      return;
    }

    if (selectedQuotes.size === 0) {
      alert("Please select at least one quote");
      return;
    }

    try {
      const selected_quotes = Array.from(selectedQuotes.entries()).map(
        ([rfq_line_id, supplier_quote_id]) => ({
          rfq_line_id,
          supplier_quote_id,
        })
      );

      const po = await convertToPO({
        rfq_id: rfq.id,
        supplier_id: selectedSupplierId,
        selected_quotes,
        tax_rate: taxRate > 0 ? taxRate / 100 : undefined,
        discount_amount: discountAmount > 0 ? discountAmount : undefined,
      });

      setShowDialog(false);
      onSuccess?.(po.id);
      alert(`Purchase Order created successfully! ID: ${po.id}`);
    } catch (err) {
      // Error handled by hook
    }
  };

  if (!canConvert) {
    return null;
  }

  return (
    <>
      <button
        onClick={() => setShowDialog(true)}
        className="btn-primary"
        disabled={loading}
      >
        Convert to Purchase Order
      </button>

      {showDialog && (
        <div className="modal-overlay">
          <div className="modal-content modal-large">
            <h2>Convert to Purchase Order</h2>
            <p>RFQ ID: {rfq.id}</p>

            <div className="form-group">
              <label>Select Supplier *</label>
              <select
                value={selectedSupplierId}
                onChange={(e) => handleSupplierChange(e.target.value)}
                required
              >
                <option value="">-- Select Supplier --</option>
                {suppliersWithQuotes.map((supplierId) => {
                  const supplierName =
                    rfq.line_items[0]?.quotes.find(
                      (q) => q.supplier_id === supplierId
                    )?.supplier_name || supplierId;
                  return (
                    <option key={supplierId} value={supplierId}>
                      {supplierName}
                    </option>
                  );
                })}
              </select>
            </div>

            {selectedSupplierId && (
              <div className="quote-selection">
                <h3>Selected Quotes</h3>
                <table>
                  <thead>
                    <tr>
                      <th>Item</th>
                      <th>Quantity</th>
                      <th>Quoted Price</th>
                      <th>Delivery Date</th>
                      <th>Total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rfq.line_items.map((line) => {
                      const quote = line.quotes.find(
                        (q) => q.supplier_id === selectedSupplierId
                      );
                      if (!quote) return null;

                      return (
                        <tr key={line.id}>
                          <td>{line.item_id}</td>
                          <td>{line.quantity}</td>
                          <td>${quote.quoted_price.toFixed(2)}</td>
                          <td>{quote.quoted_delivery_date}</td>
                          <td>
                            ${(line.quantity * quote.quoted_price).toFixed(2)}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            <div className="form-row">
              <div className="form-group">
                <label>Tax Rate (%)</label>
                <input
                  type="number"
                  value={taxRate}
                  onChange={(e) => setTaxRate(Number(e.target.value))}
                  min="0"
                  max="100"
                  step="0.01"
                />
              </div>

              <div className="form-group">
                <label>Discount Amount</label>
                <input
                  type="number"
                  value={discountAmount}
                  onChange={(e) => setDiscountAmount(Number(e.target.value))}
                  min="0"
                  step="0.01"
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
                disabled={loading || !selectedSupplierId}
                className="btn-primary"
              >
                {loading ? "Converting..." : "Create Purchase Order"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
```

### Workflow Timeline Component

```typescript
// components/shared/WorkflowTimeline.tsx

import React from "react";
import { useWorkflowStatus } from "../../hooks/useWorkflowStatus";
import { StatusBadge } from "./StatusBadge";

interface WorkflowTimelineProps {
  materialRequestId: string;
}

export const WorkflowTimeline: React.FC<WorkflowTimelineProps> = ({
  materialRequestId,
}) => {
  const { status, loading, error } = useWorkflowStatus(materialRequestId);

  if (loading) return <div>Loading workflow status...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!status) return null;

  const steps = [
    {
      name: "Material Request",
      status: status.material_request?.status,
      id: status.material_request?.id,
      completed: status.material_request !== undefined,
    },
    {
      name: "RFQ",
      status: status.rfq?.status,
      id: status.rfq?.id,
      completed: status.rfq !== undefined,
    },
    {
      name: "Purchase Order",
      status: status.purchase_order?.status,
      id: status.purchase_order?.id,
      completed: status.purchase_order !== undefined,
    },
    {
      name: "Receipt",
      status: status.receipts?.[0]?.status,
      id: status.receipts?.[0]?.id,
      completed: status.receipts && status.receipts.length > 0,
    },
    {
      name: "Invoice",
      status: status.invoices?.[0]?.status,
      id: status.invoices?.[0]?.id,
      completed: status.invoices && status.invoices.length > 0,
    },
    {
      name: "Payment",
      status: "completed",
      id: status.payments?.[0]?.id,
      completed: status.payments && status.payments.length > 0,
    },
  ];

  return (
    <div className="workflow-timeline">
      <h3>Workflow Progress</h3>
      <div className="timeline">
        {steps.map((step, index) => (
          <div
            key={step.name}
            className={`timeline-step ${step.completed ? "completed" : "pending"}`}
          >
            <div className="step-marker">
              {step.completed ? "✓" : index + 1}
            </div>
            <div className="step-content">
              <div className="step-name">{step.name}</div>
              {step.status && (
                <StatusBadge status={step.status} type={step.name.toLowerCase()} />
              )}
              {step.id && (
                <a href={`/${step.name.toLowerCase().replace(" ", "-")}/${step.id}`}>
                  View Details
                </a>
              )}
            </div>
            {index < steps.length - 1 && (
              <div className={`step-connector ${step.completed ? "completed" : ""}`} />
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
```

### Quote Comparison Component

```typescript
// components/rfqs/QuoteComparison.tsx

import React, { useState } from "react";
import type { RFQ } from "../../types/sourcing.types";

interface QuoteComparisonProps {
  rfq: RFQ;
}

export const QuoteComparison: React.FC<QuoteComparisonProps> = ({ rfq }) => {
  const [sortBy, setSortBy] = useState<"price" | "delivery">("price");

  // Get all unique suppliers
  const suppliers = Array.from(
    new Set(rfq.line_items.flatMap((line) => line.quotes.map((q) => q.supplier_id)))
  );

  const calculateTotalForSupplier = (supplierId: string): number => {
    return rfq.line_items.reduce((total, line) => {
      const quote = line.quotes.find((q) => q.supplier_id === supplierId);
      if (quote) {
        return total + line.quantity * quote.quoted_price;
      }
      return total;
    }, 0);
  };

  const sortedSuppliers = [...suppliers].sort((a, b) => {
    if (sortBy === "price") {
      return calculateTotalForSupplier(a) - calculateTotalForSupplier(b);
    }
    // Sort by earliest delivery date
    const aDate = Math.min(
      ...rfq.line_items
        .flatMap((line) => line.quotes.filter((q) => q.supplier_id === a))
        .map((q) => new Date(q.quoted_delivery_date).getTime())
    );
    const bDate = Math.min(
      ...rfq.line_items
        .flatMap((line) => line.quotes.filter((q) => q.supplier_id === b))
        .map((q) => new Date(q.quoted_delivery_date).getTime())
    );
    return aDate - bDate;
  });

  return (
    <div className="quote-comparison">
      <div className="comparison-header">
        <h3>Quote Comparison</h3>
        <div className="sort-controls">
          <label>Sort by:</label>
          <select value={sortBy} onChange={(e) => setSortBy(e.target.value as any)}>
            <option value="price">Best Price</option>
            <option value="delivery">Fastest Delivery</option>
          </select>
        </div>
      </div>

      <div className="comparison-table-wrapper">
        <table className="comparison-table">
          <thead>
            <tr>
              <th>Item</th>
              <th>Quantity</th>
              {sortedSuppliers.map((supplierId) => {
                const supplierName =
                  rfq.line_items[0]?.quotes.find((q) => q.supplier_id === supplierId)
                    ?.supplier_name || supplierId;
                return <th key={supplierId}>{supplierName}</th>;
              })}
            </tr>
          </thead>
          <tbody>
            {rfq.line_items.map((line) => (
              <tr key={line.id}>
                <td>{line.item_id}</td>
                <td>{line.quantity}</td>
                {sortedSuppliers.map((supplierId) => {
                  const quote = line.quotes.find((q) => q.supplier_id === supplierId);
                  if (!quote) {
                    return <td key={supplierId}>-</td>;
                  }
                  return (
                    <td key={supplierId}>
                      <div className="quote-cell">
                        <div className="price">${quote.quoted_price.toFixed(2)}</div>
                        <div className="delivery">
                          Delivery: {quote.quoted_delivery_date}
                        </div>
                        {quote.supplier_notes && (
                          <div className="notes">{quote.supplier_notes}</div>
                        )}
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={2}>
                <strong>Total</strong>
              </td>
              {sortedSuppliers.map((supplierId) => {
                const total = calculateTotalForSupplier(supplierId);
                const isLowest =
                  total ===
                  Math.min(...suppliers.map((s) => calculateTotalForSupplier(s)));
                return (
                  <td key={supplierId}>
                    <strong className={isLowest ? "best-price" : ""}>
                      ${total.toFixed(2)}
                      {isLowest && " 🏆"}
                    </strong>
                  </td>
                );
              })}
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
};
```

## Missing API Endpoints & Data

Based on the design document, here are the **missing API endpoints** that need to be implemented in the backend:

### 1. Convert Material Request to RFQ

**Endpoint**: `POST /api/v1/rfqs/from-material-request`

**Request Body**:

```json
{
  "material_request_id": "uuid",
  "supplier_ids": ["uuid1", "uuid2"],
  "closing_date": "2024-12-31",
  "line_item_ids": ["uuid1", "uuid2"] // Optional: select specific items
}
```

**Response**: RFQ object with copied line items

**Backend Logic**:

- Validate Material Request exists and status is "submitted"
- Copy line items from Material Request to RFQ
- Set reference_type = "material_request" and reference_id = material_request_id
- Create RFQ with status "draft"
- Create rfq_suppliers entries for each supplier_id
- Update Material Request status to "partially_quoted"

### 2. Convert RFQ to Purchase Order

**Endpoint**: `POST /api/v1/purchase-orders/from-rfq`

**Request Body**:

```json
{
  "rfq_id": "uuid",
  "supplier_id": "uuid",
  "selected_quotes": [
    {
      "rfq_line_id": "uuid",
      "supplier_quote_id": "uuid"
    }
  ],
  "tax_rate": 0.18,
  "discount_amount": 100.0
}
```

**Response**: Purchase Order object with calculated totals

**Backend Logic**:

- Validate RFQ exists and has quotes
- Validate all selected quotes belong to the same supplier
- Copy selected line items with quoted prices to Purchase Order
- Use Transaction Engine to calculate totals
- Set reference_type = "rfq" and reference_id = rfq_id
- Set party_type = "supplier" and party_id = supplier_id
- Create Purchase Order with status "draft"
- Update RFQ status to "closed"

### 3. List RFQs by Material Request

**Endpoint**: `GET /api/v1/rfqs?material_request_id={uuid}`

**Query Parameters**:

- `material_request_id`: UUID (filter by Material Request)
- `status`: string (filter by status)
- `page`, `page_size`: pagination

**Response**: Paginated list of RFQs

### 4. List Purchase Orders by RFQ

**Endpoint**: `GET /api/v1/purchase-orders?rfq_id={uuid}`

**Query Parameters**:

- `rfq_id`: UUID (filter by RFQ)
- `status`: string (filter by status)
- `page`, `page_size`: pagination

**Response**: Paginated list of Purchase Orders

### 5. Add Supplier Quote to RFQ

**Endpoint**: `POST /api/v1/rfqs/{id}/quotes`

**Request Body**:

```json
{
  "rfq_line_id": "uuid",
  "supplier_id": "uuid",
  "quoted_price": 125.5,
  "quoted_delivery_date": "2024-12-31",
  "supplier_notes": "Bulk discount available"
}
```

**Response**: SupplierQuote object

**Backend Logic**:

- Validate RFQ exists and status is "sent"
- Validate supplier_id is in rfq_suppliers
- Create supplier_quote entry
- Update RFQ status based on quote completeness:
  - If all line items have at least one quote: "fully_responded"
  - Otherwise: "partially_responded"

### 6. Get Workflow Status

**Endpoint**: `GET /api/v1/material-requests/{id}/workflow`

**Response**:

```json
{
  "material_request": {
    "id": "uuid",
    "request_no": "MR-2024-001",
    "status": "fully_quoted"
  },
  "rfqs": [
    {
      "id": "uuid",
      "status": "closed",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "purchase_orders": [
    {
      "id": "uuid",
      "status": "submitted",
      "supplier_name": "Supplier A",
      "grand_total": 5000.0
    }
  ],
  "receipts": [
    {
      "id": "uuid",
      "received_date": "2024-01-20",
      "status": "completed"
    }
  ],
  "invoices": [
    {
      "id": "uuid",
      "invoice_no": "INV-2024-001",
      "status": "paid"
    }
  ],
  "payments": [
    {
      "id": "uuid",
      "payment_date": "2024-01-25",
      "amount": 5000.0
    }
  ]
}
```

## Styling Recommendations

```css
/* sourcing-flow.css */

/* Workflow Timeline */
.workflow-timeline {
  padding: 20px;
  background: white;
  border-radius: 8px;
  margin-bottom: 20px;
}

.timeline {
  display: flex;
  align-items: flex-start;
  padding: 20px 0;
}

.timeline-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.step-marker {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #e0e0e0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  margin-bottom: 10px;
  z-index: 2;
}

.timeline-step.completed .step-marker {
  background: #4caf50;
  color: white;
}

.step-connector {
  position: absolute;
  top: 20px;
  left: 50%;
  width: 100%;
  height: 2px;
  background: #e0e0e0;
  z-index: 1;
}

.step-connector.completed {
  background: #4caf50;
}

.step-content {
  text-align: center;
}

.step-name {
  font-weight: 500;
  margin-bottom: 5px;
}

/* Quote Comparison */
.quote-comparison {
  background: white;
  border-radius: 8px;
  padding: 20px;
  margin: 20px 0;
}

.comparison-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.comparison-table-wrapper {
  overflow-x: auto;
}

.comparison-table {
  width: 100%;
  border-collapse: collapse;
}

.comparison-table th,
.comparison-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #ddd;
}

.quote-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.quote-cell .price {
  font-size: 16px;
  font-weight: 600;
  color: #2196f3;
}

.quote-cell .delivery {
  font-size: 12px;
  color: #666;
}

.quote-cell .notes {
  font-size: 11px;
  color: #999;
  font-style: italic;
}

.best-price {
  color: #4caf50;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  padding: 24px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-large {
  max-width: 900px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

/* Status Badges */
.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
}

.status-draft {
  background: #f5f5f5;
  color: #666;
}

.status-submitted {
  background: #e3f2fd;
  color: #1976d2;
}

.status-sent {
  background: #fff3e0;
  color: #f57c00;
}

.status-partially_responded,
.status-partially_received,
.status-partially_quoted {
  background: #fff9c4;
  color: #f57f17;
}

.status-fully_responded,
.status-fully_received,
.status-fully_quoted {
  background: #e8f5e9;
  color: #388e3c;
}

.status-closed {
  background: #e0e0e0;
  color: #424242;
}

.status-cancelled {
  background: #ffebee;
  color: #c62828;
}
```

## Integration with Existing APIs

### Purchase Receipt Integration

When creating a Receipt Note from a Purchase Order:

```typescript
// Example: Create Receipt Note from Purchase Order

const createReceiptFromPO = async (purchaseOrder: PurchaseOrder) => {
  const receiptData = {
    reference_type: "purchase_order",
    reference_id: purchaseOrder.id,
    party_type: "supplier",
    party_id: purchaseOrder.party_id,
    received_date: new Date().toISOString().split("T")[0],
    line_items: purchaseOrder.line_items.map((line) => ({
      item_id: line.item_id,
      quantity: line.quantity - line.received_quantity, // Remaining quantity
      purchase_order_line_id: line.id,
    })),
  };

  const response = await axios.post(
    `${API_BASE_URL}/api/v1/purchase-receipts`,
    receiptData,
    { headers: getHeaders() },
  );

  return response.data;
};
```

### Purchase Invoice Integration

When creating a Purchase Invoice from a Purchase Order:

```typescript
// Example: Create Purchase Invoice from Purchase Order

const createInvoiceFromPO = async (purchaseOrder: PurchaseOrder) => {
  const invoiceData = {
    invoice_type: "purchase",
    reference_type: "purchase_order",
    reference_id: purchaseOrder.id,
    party_type: "supplier",
    party_id: purchaseOrder.party_id,
    invoice_date: new Date().toISOString().split("T")[0],
    due_date: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000)
      .toISOString()
      .split("T")[0], // 30 days from now
    line_items: purchaseOrder.line_items.map((line) => ({
      item_id: line.item_id,
      quantity: line.received_quantity, // Only invoice received quantity
      unit_price: line.unit_price,
      line_total: line.received_quantity * line.unit_price,
    })),
    subtotal: purchaseOrder.subtotal,
    tax_amount: purchaseOrder.tax_amount,
    grand_total: purchaseOrder.grand_total,
  };

  const response = await axios.post(
    `${API_BASE_URL}/api/v1/invoices`,
    invoiceData,
    { headers: getHeaders() },
  );

  return response.data;
};
```

### Payment Integration

When making a payment against a Purchase Invoice:

```typescript
// Example: Create Payment for Purchase Invoice

const createPaymentForInvoice = async (invoice: any, amount: number) => {
  const paymentData = {
    payment_type: "pay",
    reference_type: "purchase_invoice",
    reference_id: invoice.id,
    party_type: "supplier",
    party_id: invoice.party_id,
    amount: amount,
    payment_date: new Date().toISOString().split("T")[0],
    payment_method: "bank_transfer",
    notes: `Payment for Invoice ${invoice.invoice_no}`,
  };

  const response = await axios.post(
    `${API_BASE_URL}/api/v1/payments`,
    paymentData,
    { headers: getHeaders() },
  );

  return response.data;
};
```

## Testing Checklist

### Material Request Module

- [ ] Create Material Request with line items
- [ ] Submit Material Request
- [ ] Cancel Material Request
- [ ] Update Material Request (DRAFT only)
- [ ] Delete Material Request (DRAFT only)
- [ ] List Material Requests with filters
- [ ] View Material Request details
- [ ] Convert Material Request to RFQ

### RFQ Module

- [ ] Create RFQ manually
- [ ] Create RFQ from Material Request
- [ ] Add suppliers to RFQ
- [ ] Send RFQ to suppliers
- [ ] Add supplier quotes
- [ ] View quote comparison
- [ ] Convert RFQ to Purchase Order
- [ ] Close RFQ
- [ ] List RFQs with filters

### Purchase Order Module

- [ ] Create Purchase Order manually
- [ ] Create Purchase Order from RFQ
- [ ] Submit Purchase Order
- [ ] Cancel Purchase Order
- [ ] Close Purchase Order
- [ ] Create Receipt Note from Purchase Order
- [ ] Create Purchase Invoice from Purchase Order
- [ ] View Purchase Order details
- [ ] List Purchase Orders with filters

### Workflow Integration

- [ ] View complete workflow timeline
- [ ] Track status updates across documents
- [ ] Navigate between related documents
- [ ] Verify referential integrity
- [ ] Test three-way matching (PO → Receipt → Invoice)

### Error Handling

- [ ] Handle validation errors
- [ ] Handle not found errors
- [ ] Handle state conflict errors
- [ ] Handle integration errors
- [ ] Display user-friendly error messages

## Best Practices

1. **State Management**: Use React Context or Redux for managing sourcing workflow state
2. **Caching**: Cache supplier lists and item catalogs to reduce API calls
3. **Optimistic Updates**: Show immediate feedback while API calls are in progress
4. **Error Recovery**: Provide retry mechanisms for failed operations
5. **Accessibility**: Ensure all forms and modals are keyboard navigable
6. **Mobile Responsive**: Design works well on tablets and mobile devices
7. **Loading States**: Show skeleton loaders for better UX
8. **Confirmation Dialogs**: Confirm destructive actions (delete, cancel)
9. **Audit Trail**: Display who created/updated documents and when
10. **Print Support**: Enable printing of Purchase Orders and RFQs

## Environment Variables

```env
# .env.local

REACT_APP_API_URL=http://localhost:8001
REACT_APP_ENABLE_WORKFLOW_NOTIFICATIONS=true
REACT_APP_DEFAULT_TAX_RATE=0.18
REACT_APP_DEFAULT_PAYMENT_TERMS=30
```

## Performance Optimization

1. **Lazy Loading**: Load RFQ and Purchase Order modules on demand
2. **Pagination**: Always paginate large lists
3. **Debouncing**: Debounce search inputs
4. **Memoization**: Use React.memo for expensive components
5. **Virtual Scrolling**: For large line item tables

## Security Considerations

1. **Permission Checks**: Verify user has required permissions before showing actions
2. **Input Validation**: Validate all inputs on frontend before API calls
3. **XSS Prevention**: Sanitize user inputs displayed in UI
4. **CSRF Protection**: Include CSRF tokens in state-changing requests
5. **Secure Storage**: Store tokens securely (httpOnly cookies preferred)

## Support & Resources

- Material Request API: `core-service/MATERIAL_REQUEST_ENHANCEMENTS.md`
- Design Document: `.kiro/specs/sourcing-flow/design.md`
- Swagger UI: http://localhost:8001/docs
- Backend logs: `docker compose logs core-service`

## Next Steps

1. Implement missing backend endpoints (listed above)
2. Build Material Request UI components
3. Build RFQ UI components with quote comparison
4. Build Purchase Order UI components
5. Integrate with existing Receipt, Invoice, and Payment modules
6. Add workflow timeline visualization
7. Implement email notifications for RFQ sending
8. Add PDF generation for Purchase Orders
9. Implement approval workflows for high-value POs
10. Add analytics dashboard for sourcing metrics

## Common Pitfalls to Avoid

1. **Don't skip validation**: Always validate before conversion
2. **Don't allow conversion from wrong status**: Check status before showing convert buttons
3. **Don't forget to update parent status**: When creating RFQ, update Material Request status
4. **Don't allow editing after submission**: Lock documents after they're submitted
5. **Don't forget referential integrity**: Always set reference_type and reference_id
6. **Don't skip Transaction Engine**: Use it for all financial calculations
7. **Don't allow partial receipts without tracking**: Update received_quantity on PO lines
8. **Don't create invoices for unreceived items**: Only invoice received quantities
9. **Don't allow overpayment**: Validate payment amount against outstanding balance
10. **Don't forget audit logging**: Log all status transitions

## FAQ

**Q: Can I convert a Material Request directly to a Purchase Order?**
A: No, the workflow requires going through RFQ to collect quotes from suppliers first.

**Q: Can I create multiple RFQs from one Material Request?**
A: Yes, you can create multiple RFQs for different line items or send to different supplier groups.

**Q: What happens if I cancel a Material Request that has an RFQ?**
A: The RFQ should be closed automatically, and any draft Purchase Orders should be cancelled.

**Q: Can I edit a Purchase Order after submission?**
A: No, once submitted, Purchase Orders are locked. You need to cancel and create a new one.

**Q: How do I handle partial receipts?**
A: Create multiple Receipt Notes, each updating the received_quantity on Purchase Order lines.

**Q: Can I create an invoice before receiving goods?**
A: Technically yes, but best practice is to only invoice received quantities (three-way matching).

**Q: What if a supplier doesn't respond to an RFQ?**
A: You can still convert to PO with quotes from other suppliers. The RFQ status will be "partially_responded".

**Q: How do I track which items are urgent?**
A: Use the priority field on Material Requests (low, medium, high, urgent).

**Q: Can I apply discounts at the line item level?**
A: Currently, discounts are applied at the document level. Line-level discounts would require backend changes.

**Q: How do I handle currency conversions?**
A: This is not currently supported. All transactions are in the organization's base currency.
