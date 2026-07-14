---
inclusion: manual
---

# Frontend Admin Invoices & Payments Module - Integration Guide

Complete API reference for building the Admin Invoice & Payment Tracking UI. This module lets system admins list, view, create, and send invoices across all organizations, and track payments platform-wide.

## Base URL & Auth

```
Core Service: http://localhost:8001/api/v1
Auth:         Authorization: Bearer {token}
```

All invoice and payment admin endpoints require a valid Bearer token with `user_type = "system_admin"`. Non-admin users receive `403 Admin access required`.

---

## 1. Invoice & Payment API

### List Invoices

```
GET /api/v1/admin/invoices?organization_id=uuid&status=pending&date_from=2024-01-01T00:00:00&date_to=2024-12-31T23:59:59&page=1&page_size=20
Host: localhost:8001
Authorization: Bearer {token}
```

Query Parameters (all optional):

| Parameter         | Type       | Default | Description                                      |
| ----------------- | ---------- | ------- | ------------------------------------------------ |
| `organization_id` | `UUID`     | —       | Filter by organization                           |
| `status`          | `string`   | —       | Filter by invoice status                         |
| `date_from`       | `datetime` | —       | Filter invoices from this posting date           |
| `date_to`         | `datetime` | —       | Filter invoices up to this posting date          |
| `page`            | `int`      | 1       | Page number (≥ 1)                                |
| `page_size`       | `int`      | 20      | Items per page (1–100)                           |

Response (200):

```json
{
  "invoices": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "organization_name": "Acme Corp",
      "invoice_no": "INV-2024-001",
      "invoice_type": "sales",
      "party_id": "uuid",
      "party_name": "Customer Inc",
      "party_code": "CUST-001",
      "status": "pending",
      "posting_date": "2024-06-15T00:00:00Z",
      "due_date": "2024-07-15T00:00:00Z",
      "grand_total": "15000.00",
      "outstanding_amount": "15000.00",
      "created_at": "2024-06-15T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 350,
    "total_pages": 18,
    "has_next": true,
    "has_prev": false
  }
}
```

### Get Invoice Detail

```
GET /api/v1/admin/invoices/{id}
Host: localhost:8001
Authorization: Bearer {token}
```

Response (200): Full invoice record including line items and payment history.

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "invoice_no": "INV-2024-001",
  "invoice_type": "sales",
  "party_id": "uuid",
  "party_type": "customer",
  "posting_date": "2024-06-15T00:00:00Z",
  "due_date": "2024-07-15T00:00:00Z",
  "status": "pending",
  "grand_total": "15000.00",
  "outstanding_amount": "15000.00",
  "currency": "INR",
  "discount_type": "percentage",
  "discount_value": "0",
  "remarks": null,
  "submitted_at": null,
  "created_by": "uuid",
  "updated_by": null,
  "created_at": "2024-06-15T10:00:00Z",
  "updated_at": "2024-06-15T10:00:00Z",
  "reference_no": "SO-2024-001",
  "customer": {
    "customer_name": "Customer Inc",
    "customer_code": "CUST-001",
    "email": "billing@customer.com",
    "phone": "+1-555-0100",
    "address": null,
    "tax_number": null
  },
  "items": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "invoice_id": "uuid",
      "item_id": "uuid",
      "item_code": "ITEM-001",
      "item_name": "Widget A",
      "description": "Standard widget",
      "qty": "10",
      "uom": "pcs",
      "rate": "1500.00",
      "amount": "15000.00",
      "sort_order": 1,
      "tax_template_id": null,
      "tax_rate": null,
      "tax_amount": null,
      "discount_type": null,
      "discount_value": null,
      "discount_amount": null,
      "total_amount": "15000.00",
      "created_at": "2024-06-15T10:00:00Z",
      "updated_at": "2024-06-15T10:00:00Z"
    }
  ]
}
```

### Create Invoice

```
POST /api/v1/admin/invoices?organization_id=uuid
Host: localhost:8001
Authorization: Bearer {token}
Content-Type: application/json
```

Query Parameters:

| Parameter         | Type   | Required | Description                              |
| ----------------- | ------ | -------- | ---------------------------------------- |
| `organization_id` | `UUID` | Yes      | Organization to create the invoice in    |

Request body:

```json
{
  "invoice_type": "sales",
  "party_id": "uuid",
  "party_type": "customer",
  "posting_date": "2024-06-15T00:00:00Z",
  "due_date": "2024-07-15T00:00:00Z",
  "status": "draft",
  "grand_total": 15000.00,
  "outstanding_amount": 15000.00,
  "currency": "INR",
  "discount_type": "percentage",
  "discount_value": 0,
  "remarks": null
}
```

Required fields: `invoice_type`, `party_id`, `party_type`, `posting_date`

`invoice_type` must be one of: `sales` | `purchase`

`status` must be one of: `draft` | `submitted` | `pending` | `paid` | `partial` | `overdue` | `cancelled`

Response (201): `InvoiceResponse` — full invoice record with items, customer/supplier details.

### Send Invoice

```
POST /api/v1/admin/invoices/{id}/send
Host: localhost:8001
Authorization: Bearer {token}
```

Sends the invoice to the party's email via the communication log system and updates the invoice status to "pending".

Response (200):

```json
{
  "message": "Invoice sent successfully",
  "invoice_id": "uuid",
  "status": "pending"
}
```

### List Payments

```
GET /api/v1/admin/payments?organization_id=uuid&status=completed&page=1&page_size=20
Host: localhost:8001
Authorization: Bearer {token}
```

Query Parameters (all optional):

| Parameter         | Type     | Default | Description                    |
| ----------------- | -------- | ------- | ------------------------------ |
| `organization_id` | `UUID`   | —       | Filter by organization         |
| `status`          | `string` | —       | Filter by payment status       |
| `page`            | `int`    | 1       | Page number (≥ 1)              |
| `page_size`       | `int`    | 20      | Items per page (1–100)         |

Response (200):

```json
{
  "payment_entries": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "organization_name": "Acme Corp",
      "payment_type": "receive",
      "party_id": "uuid",
      "amount": "5000.00",
      "currency_code": "INR",
      "payment_date": "2024-06-20T00:00:00Z",
      "payment_mode": "bank_transfer",
      "reference_no": "TXN-12345",
      "status": "completed",
      "source": "manual",
      "receipt_number": "REC-001",
      "unallocated_amount": "0.00",
      "created_at": "2024-06-20T10:00:00Z",
      "party_name": "Customer Inc",
      "party_code": "CUST-001",
      "party_email": "billing@customer.com",
      "party_phone": "+1-555-0100"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 120,
    "total_pages": 6,
    "has_next": true,
    "has_prev": false
  }
}
```

### Error Responses

| Status | Detail                                    | Cause                    |
| ------ | ----------------------------------------- | ------------------------ |
| 401    | `"Invalid authentication credentials"`    | Missing or invalid token |
| 403    | `"Admin access required"`                 | Non-admin user           |
| 404    | `"Invoice not found"`                     | Invalid invoice ID       |
| 422    | Pydantic validation error                 | Invalid field values     |

---

## 2. TypeScript Types

```typescript
// types/adminInvoice.types.ts

export type InvoiceStatus = "draft" | "submitted" | "pending" | "paid" | "partial" | "overdue" | "cancelled";
export type InvoiceType = "sales" | "purchase";
export type DiscountType = "flat" | "percentage";

export interface AdminInvoiceListItem {
  id: string;
  organization_id: string;
  organization_name: string | null;
  invoice_no: string;
  invoice_type: InvoiceType;
  party_id: string;
  party_name: string | null;
  party_code: string | null;
  status: InvoiceStatus;
  posting_date: string;
  due_date: string | null;
  grand_total: string; // Decimal as string
  outstanding_amount: string | number | null;
  created_at: string;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface AdminInvoiceListResponse {
  invoices: AdminInvoiceListItem[];
  pagination: PaginationMeta;
}

export interface InvoiceItemResponse {
  id: string;
  organization_id: string;
  invoice_id: string;
  item_id: string | null;
  item_code: string | null;
  item_name: string | null;
  description: string | null;
  qty: string;
  uom: string;
  rate: string | null;
  amount: string | null;
  sort_order: number | null;
  tax_template_id: string | null;
  tax_rate: string | null;
  tax_amount: string | null;
  discount_type: string | null;
  discount_value: string | null;
  discount_amount: string | null;
  total_amount: string | null;
  min_order_qty: number | null;
  max_order_qty: number | null;
  standard_rate: string | null;
  tax_info: Record<string, any> | null;
  extra_data: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface CustomerDetails {
  customer_name: string;
  customer_code: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  tax_number: string | null;
  status: string | null;
}

export interface SupplierDetails {
  supplier_name: string;
  supplier_code: string;
  email: string | null;
  phone: string | null;
  address: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  tax_number: string | null;
  status: string | null;
}

export interface InvoiceDetailResponse {
  id: string;
  organization_id: string;
  invoice_no: string | null;
  invoice_type: InvoiceType;
  party_id: string;
  party_type: string;
  posting_date: string;
  due_date: string | null;
  status: InvoiceStatus;
  grand_total: number;
  outstanding_amount: number;
  currency: string;
  discount_type: DiscountType | null;
  discount_value: number | null;
  reference_type: string | null;
  reference_id: string | null;
  remarks: string | null;
  submitted_at: string | null;
  created_by: string | null;
  updated_by: string | null;
  created_at: string;
  updated_at: string;
  reference_no: string | null;
  customer: CustomerDetails | null;
  supplier: SupplierDetails | null;
  items: InvoiceItemResponse[] | null;
}

export interface InvoiceCreate {
  invoice_no?: string;
  invoice_type: InvoiceType;
  party_id: string;
  party_type: string;
  posting_date: string;
  due_date?: string;
  status?: InvoiceStatus;
  grand_total?: number;
  outstanding_amount?: number;
  currency?: string;
  discount_type?: DiscountType;
  discount_value?: number;
  reference_type?: string;
  reference_id?: string;
  remarks?: string;
}

export interface InvoiceSendResponse {
  message: string;
  invoice_id: string;
  status: string;
}

export interface AdminInvoiceFilters {
  organization_id?: string;
  status?: InvoiceStatus;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

// ── Payment Types ──

export interface AdminPaymentListItem {
  id: string;
  organization_id: string;
  organization_name: string | null;
  payment_type: string;
  party_id: string;
  amount: string; // Decimal as string
  currency_code: string;
  payment_date: string;
  payment_mode: string;
  reference_no: string | null;
  status: string;
  source: string;
  receipt_number: string | null;
  unallocated_amount: string; // Decimal as string
  created_at: string;
  party_name: string | null;
  party_code: string | null;
  party_email: string | null;
  party_phone: string | null;
}

export interface AdminPaymentListResponse {
  payment_entries: AdminPaymentListItem[];
  pagination: PaginationMeta;
}

export interface AdminPaymentFilters {
  organization_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}
```

---

## 3. Frontend Service Layer

```typescript
// services/adminInvoiceService.ts

import apiClient from "./apiClient";
import type {
  InvoiceCreate,
  InvoiceDetailResponse,
  InvoiceSendResponse,
  AdminInvoiceListResponse,
  AdminInvoiceFilters,
  AdminPaymentListResponse,
  AdminPaymentFilters,
} from "../types/adminInvoice.types";

const BASE = "http://localhost:8001/api/v1";

export const adminInvoiceService = {
  list: (filters?: AdminInvoiceFilters) => {
    const params = new URLSearchParams();
    if (filters?.organization_id) params.set("organization_id", filters.organization_id);
    if (filters?.status) params.set("status", filters.status);
    if (filters?.date_from) params.set("date_from", filters.date_from);
    if (filters?.date_to) params.set("date_to", filters.date_to);
    if (filters?.page) params.set("page", String(filters.page));
    if (filters?.page_size) params.set("page_size", String(filters.page_size));
    const qs = params.toString();
    return apiClient.get<AdminInvoiceListResponse>(
      `${BASE}/admin/invoices${qs ? `?${qs}` : ""}`
    );
  },

  getById: (id: string) =>
    apiClient.get<InvoiceDetailResponse>(`${BASE}/admin/invoices/${id}`),

  create: (organizationId: string, data: InvoiceCreate) =>
    apiClient.post<InvoiceDetailResponse>(
      `${BASE}/admin/invoices?organization_id=${organizationId}`,
      data
    ),

  send: (id: string) =>
    apiClient.post<InvoiceSendResponse>(`${BASE}/admin/invoices/${id}/send`),
};

export const adminPaymentService = {
  list: (filters?: AdminPaymentFilters) => {
    const params = new URLSearchParams();
    if (filters?.organization_id) params.set("organization_id", filters.organization_id);
    if (filters?.status) params.set("status", filters.status);
    if (filters?.page) params.set("page", String(filters.page));
    if (filters?.page_size) params.set("page_size", String(filters.page_size));
    const qs = params.toString();
    return apiClient.get<AdminPaymentListResponse>(
      `${BASE}/admin/payments${qs ? `?${qs}` : ""}`
    );
  },
};
```

---

## 4. React Hooks

### useAdminInvoices — Fetch paginated invoice list

```typescript
// hooks/useAdminInvoices.ts

import { useState, useEffect, useCallback } from "react";
import { adminInvoiceService } from "../services/adminInvoiceService";
import type { AdminInvoiceListResponse, AdminInvoiceFilters } from "../types/adminInvoice.types";

interface InvoiceListState {
  data: AdminInvoiceListResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const useAdminInvoices = (filters?: AdminInvoiceFilters) => {
  const [state, setState] = useState<InvoiceListState>({
    data: null, isLoading: true, error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminInvoiceService.list(filters);
      setState({ data: result.data, isLoading: false, error: null });
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to load invoices";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [filters?.organization_id, filters?.status, filters?.date_from, filters?.date_to, filters?.page, filters?.page_size]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { ...state, refetch: fetchData };
};
```

### useAdminInvoice — Fetch single invoice detail

```typescript
// hooks/useAdminInvoice.ts

import { useState, useEffect, useCallback } from "react";
import { adminInvoiceService } from "../services/adminInvoiceService";
import type { InvoiceDetailResponse } from "../types/adminInvoice.types";

interface InvoiceDetailState {
  data: InvoiceDetailResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const useAdminInvoice = (invoiceId: string) => {
  const [state, setState] = useState<InvoiceDetailState>({
    data: null, isLoading: true, error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminInvoiceService.getById(invoiceId);
      setState({ data: result.data, isLoading: false, error: null });
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to load invoice";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [invoiceId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { ...state, refetch: fetchData };
};
```

### useCreateInvoice — Create a new invoice

```typescript
// hooks/useCreateInvoice.ts

import { useState } from "react";
import { adminInvoiceService } from "../services/adminInvoiceService";
import type { InvoiceCreate, InvoiceDetailResponse } from "../types/adminInvoice.types";

export const useCreateInvoice = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createInvoice = async (
    organizationId: string,
    data: InvoiceCreate
  ): Promise<InvoiceDetailResponse> => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminInvoiceService.create(organizationId, data);
      return result.data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to create invoice";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createInvoice, loading, error };
};
```

### useSendInvoice — Send an invoice

```typescript
// hooks/useSendInvoice.ts

import { useState } from "react";
import { adminInvoiceService } from "../services/adminInvoiceService";
import type { InvoiceSendResponse } from "../types/adminInvoice.types";

export const useSendInvoice = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendInvoice = async (invoiceId: string): Promise<InvoiceSendResponse> => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminInvoiceService.send(invoiceId);
      return result.data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to send invoice";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { sendInvoice, loading, error };
};
```

### useAdminPayments — Fetch paginated payment list

```typescript
// hooks/useAdminPayments.ts

import { useState, useEffect, useCallback } from "react";
import { adminPaymentService } from "../services/adminInvoiceService";
import type { AdminPaymentListResponse, AdminPaymentFilters } from "../types/adminInvoice.types";

interface PaymentListState {
  data: AdminPaymentListResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const useAdminPayments = (filters?: AdminPaymentFilters) => {
  const [state, setState] = useState<PaymentListState>({
    data: null, isLoading: true, error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminPaymentService.list(filters);
      setState({ data: result.data, isLoading: false, error: null });
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to load payments";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [filters?.organization_id, filters?.status, filters?.page, filters?.page_size]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { ...state, refetch: fetchData };
};
```

---

## 5. Module Structure

```
src/
├── features/
│   └── admin/
│       ├── components/
│       │   ├── InvoicesPage.tsx            # Invoice list page with filters
│       │   ├── InvoiceDetailPage.tsx       # Single invoice detail with line items
│       │   ├── InvoiceCreateForm.tsx       # Create invoice form
│       │   ├── InvoiceTable.tsx            # Table of invoices with pagination
│       │   ├── SendInvoiceConfirmDialog.tsx # Confirmation for sending invoice
│       │   ├── PaymentsPage.tsx            # Payment list page with filters
│       │   └── PaymentTable.tsx            # Table of payments with pagination
│       ├── hooks/
│       │   ├── useAdminInvoices.ts
│       │   ├── useAdminInvoice.ts
│       │   ├── useCreateInvoice.ts
│       │   ├── useSendInvoice.ts
│       │   └── useAdminPayments.ts
│       ├── services/
│       │   └── adminInvoiceService.ts
│       └── types/
│           └── adminInvoice.types.ts
```

---

## 6. Component Examples

### Invoices List Page

```typescript
// components/InvoicesPage.tsx

import React, { useState } from "react";
import { useAdminInvoices } from "../hooks/useAdminInvoices";
import { InvoiceTable } from "./InvoiceTable";
import type { AdminInvoiceFilters, InvoiceStatus } from "../types/adminInvoice.types";

export const InvoicesPage: React.FC = () => {
  const [filters, setFilters] = useState<AdminInvoiceFilters>({ page: 1, page_size: 20 });
  const { data, isLoading, error } = useAdminInvoices(filters);

  return (
    <div className="admin-invoices">
      <h1>Invoices</h1>

      <div className="filters-bar">
        <select
          value={filters.status || ""}
          onChange={(e) =>
            setFilters({ ...filters, status: (e.target.value || undefined) as InvoiceStatus | undefined, page: 1 })
          }
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="submitted">Submitted</option>
          <option value="pending">Pending</option>
          <option value="paid">Paid</option>
          <option value="partial">Partial</option>
          <option value="overdue">Overdue</option>
          <option value="cancelled">Cancelled</option>
        </select>

        <input
          type="date"
          value={filters.date_from?.split("T")[0] || ""}
          onChange={(e) =>
            setFilters({ ...filters, date_from: e.target.value ? `${e.target.value}T00:00:00` : undefined, page: 1 })
          }
        />
        <input
          type="date"
          value={filters.date_to?.split("T")[0] || ""}
          onChange={(e) =>
            setFilters({ ...filters, date_to: e.target.value ? `${e.target.value}T23:59:59` : undefined, page: 1 })
          }
        />
      </div>

      {isLoading && <div>Loading...</div>}
      {error && <div className="error">{error}</div>}
      {data && (
        <InvoiceTable
          invoices={data.invoices}
          pagination={data.pagination}
          onPageChange={(page) => setFilters({ ...filters, page })}
        />
      )}
    </div>
  );
};
```

### Invoice Detail Page

```typescript
// components/InvoiceDetailPage.tsx

import React from "react";
import { useParams } from "react-router-dom";
import { useAdminInvoice } from "../hooks/useAdminInvoice";
import { useSendInvoice } from "../hooks/useSendInvoice";

export const InvoiceDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { data: invoice, isLoading, error, refetch } = useAdminInvoice(id!);
  const { sendInvoice, loading: sending } = useSendInvoice();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!invoice) return null;

  const handleSend = async () => {
    if (window.confirm("Send this invoice to the customer?")) {
      await sendInvoice(invoice.id);
      refetch();
    }
  };

  return (
    <div className="invoice-detail">
      <h1>{invoice.invoice_no || "New Invoice"}</h1>
      <span className={`badge badge-${invoice.status}`}>{invoice.status}</span>

      {invoice.status === "draft" && (
        <button onClick={handleSend} disabled={sending}>
          {sending ? "Sending..." : "Send Invoice"}
        </button>
      )}

      <div className="invoice-info">
        <p>Type: {invoice.invoice_type}</p>
        <p>Posting Date: {new Date(invoice.posting_date).toLocaleDateString()}</p>
        <p>Due Date: {invoice.due_date ? new Date(invoice.due_date).toLocaleDateString() : "—"}</p>
        <p>Grand Total: {parseFloat(String(invoice.grand_total)).toLocaleString()} {invoice.currency}</p>
        <p>Outstanding: {parseFloat(String(invoice.outstanding_amount)).toLocaleString()} {invoice.currency}</p>
      </div>

      {invoice.customer && (
        <div className="party-info">
          <h3>Customer</h3>
          <p>{invoice.customer.customer_name} ({invoice.customer.customer_code})</p>
          <p>Email: {invoice.customer.email || "—"}</p>
          <p>Phone: {invoice.customer.phone || "—"}</p>
        </div>
      )}

      {invoice.items && invoice.items.length > 0 && (
        <div className="line-items">
          <h3>Line Items</h3>
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>Qty</th>
                <th>Rate</th>
                <th>Amount</th>
              </tr>
            </thead>
            <tbody>
              {invoice.items.map((item) => (
                <tr key={item.id}>
                  <td>{item.item_name || item.item_code || "—"}</td>
                  <td>{item.qty} {item.uom}</td>
                  <td>{item.rate}</td>
                  <td>{item.amount}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
```

### Payments List Page

```typescript
// components/PaymentsPage.tsx

import React, { useState } from "react";
import { useAdminPayments } from "../hooks/useAdminPayments";
import { PaymentTable } from "./PaymentTable";
import type { AdminPaymentFilters } from "../types/adminInvoice.types";

export const PaymentsPage: React.FC = () => {
  const [filters, setFilters] = useState<AdminPaymentFilters>({ page: 1, page_size: 20 });
  const { data, isLoading, error } = useAdminPayments(filters);

  return (
    <div className="admin-payments">
      <h1>Payments</h1>

      <div className="filters-bar">
        <select
          value={filters.status || ""}
          onChange={(e) =>
            setFilters({ ...filters, status: e.target.value || undefined, page: 1 })
          }
        >
          <option value="">All Statuses</option>
          <option value="draft">Draft</option>
          <option value="submitted">Submitted</option>
          <option value="completed">Completed</option>
          <option value="cancelled">Cancelled</option>
        </select>
      </div>

      {isLoading && <div>Loading...</div>}
      {error && <div className="error">{error}</div>}
      {data && (
        <PaymentTable
          payments={data.payment_entries}
          pagination={data.pagination}
          onPageChange={(page) => setFilters({ ...filters, page })}
        />
      )}
    </div>
  );
};
```

---

## 7. Error Handling

```typescript
catch (err: any) {
  const message = err.response?.data?.detail || "An error occurred";
  const status = err.response?.status;

  if (status === 401) {
    localStorage.removeItem("token");
    window.location.href = "/login";
  } else if (status === 403) {
    setError("Admin access required");
  } else if (status === 404) {
    setError("Invoice not found");
  }
}
```

---

## 8. UI Behavior Notes

- `grand_total` and `outstanding_amount` on invoices, and `amount` and `unallocated_amount` on payments are returned as decimal strings — parse with `parseFloat()` for display
- Invoice creation requires `organization_id` as a query parameter, not in the request body — the UI should provide an org selector
- Sending an invoice updates its status to `"pending"` — show a confirmation dialog before sending
- The invoice detail endpoint returns line items and customer/supplier details inline
- The payments list uses `payment_entries` as the array key (not `payments`)
- Cross-org lists include `organization_name` for display context — show it as a column in tables
- Date range filters on invoices use `posting_date` for filtering
- Pagination: `page` starts at 1, `page_size` max is 100

---

## 9. Testing Checklist

### Unit Tests

- [ ] `adminInvoiceService.list` calls correct URL with query params
- [ ] `adminInvoiceService.getById` calls correct URL
- [ ] `adminInvoiceService.create` sends POST with organization_id query param and correct body
- [ ] `adminInvoiceService.send` sends POST to correct URL
- [ ] `adminPaymentService.list` calls correct URL with query params
- [ ] `useAdminInvoices` sets `isLoading` correctly during fetch
- [ ] `useAdminInvoices` populates `data` on success
- [ ] `useAdminInvoices` sets `error` on failure
- [ ] `useAdminInvoices` refetches when filters change
- [ ] `useAdminInvoice` fetches invoice detail on mount
- [ ] `useCreateInvoice` returns created invoice on success
- [ ] `useCreateInvoice` sets error on failure
- [ ] `useSendInvoice` returns send response on success
- [ ] `useSendInvoice` sets error on failure
- [ ] `useAdminPayments` sets `isLoading` correctly during fetch
- [ ] `useAdminPayments` populates `data` on success
- [ ] `useAdminPayments` sets `error` on failure
- [ ] `InvoiceTable` renders all invoice rows
- [ ] `InvoiceTable` handles empty list gracefully
- [ ] `InvoiceDetailPage` renders line items table
- [ ] `PaymentTable` renders all payment rows
- [ ] `PaymentTable` handles empty list gracefully

### Integration Tests

- [ ] Full flow: list invoices → click invoice → view detail with line items
- [ ] Create invoice → appears in list
- [ ] Send invoice → confirmation dialog → status updates to pending
- [ ] Organization filter updates invoice list results
- [ ] Status filter updates invoice list results
- [ ] Date range filter updates invoice list results
- [ ] Pagination navigation works correctly on invoices
- [ ] Full flow: list payments → verify organization_name displayed
- [ ] Organization filter updates payment list results
- [ ] Status filter updates payment list results
- [ ] Pagination navigation works correctly on payments

### Error Scenario Tests

- [ ] 401 response clears token and redirects to login
- [ ] 403 response shows "Admin access required"
- [ ] 404 response shows "Invoice not found" on detail page
- [ ] Network error shows appropriate error state
- [ ] Send invoice failure shows error message

---

## 10. Backend Files Reference

- Schema: `core-service/app/schemas/admin_invoice.py`
- Invoice Service: `core-service/app/services/admin_invoice_service.py`
- Payment Service: `core-service/app/services/admin_payment_service.py`
- Invoice Endpoint: `core-service/app/api/v1/endpoints/admin/invoices.py`
- Payment Endpoint: `core-service/app/api/v1/endpoints/admin/payments.py`
- Router Registration: `core-service/app/api/v1/endpoints/admin/__init__.py`
- Swagger UI: http://localhost:8001/docs (tags: Admin - Invoices, Admin - Payments)
