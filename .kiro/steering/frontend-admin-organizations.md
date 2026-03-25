---
inclusion: manual
---

# Frontend Admin Organizations Module - Integration Guide

Complete API reference for building the Admin Organization Management UI. This module lets system admins create, list, view, update, and suspend organizations across the entire platform.

## Base URL & Auth

```
Core Service: http://localhost:8001/api/v1
Auth:         Authorization: Bearer {token}
```

All organization admin endpoints require a valid Bearer token with `user_type = "system_admin"`. Non-admin users receive `403 Admin access required`.

---

## 1. Organization API

### Create Organization

```
POST /api/v1/admin/organizations
Host: localhost:8001
Authorization: Bearer {token}
Content-Type: application/json
```

Request body:

```json
{
  "name": "Acme Corp",
  "slug": "acme-corp",
  "display_name": "Acme Corporation",
  "description": "Enterprise client",
  "email": "admin@acme.com",
  "phone": "+1-555-0100",
  "website": "https://acme.com",
  "organization_type": "enterprise",
  "industry": "Manufacturing",
  "base_currency": "USD",
  "status": "active",
  "country": "US"
}
```

Required fields: `name`, `slug`

`slug` must match `^[a-z0-9-]+$` (lowercase alphanumeric + hyphens).

`organization_type` must be one of: `enterprise` | `business` | `startup` | `individual`

`status` must be one of: `active` | `inactive` | `suspended` | `trial`

Response (201): `AdminOrgDetailResponse`

```json
{
  "id": "uuid",
  "name": "Acme Corp",
  "slug": "acme-corp",
  "display_name": "Acme Corporation",
  "description": "Enterprise client",
  "email": "admin@acme.com",
  "phone": "+1-555-0100",
  "website": "https://acme.com",
  "address_line1": null,
  "address_line2": null,
  "city": null,
  "state": null,
  "postal_code": null,
  "country": "US",
  "organization_type": "enterprise",
  "industry": "Manufacturing",
  "base_currency": "USD",
  "logo_url": null,
  "status": "active",
  "is_active": true,
  "owner_id": null,
  "settings": null,
  "extra_data": null,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": null,
  "user_count": 0,
  "invoice_count": 0,
  "payment_total": "0"
}
```

### List Organizations

```
GET /api/v1/admin/organizations?search=acme&status=active&page=1&page_size=20
Host: localhost:8001
Authorization: Bearer {token}
```

Query Parameters (all optional):

| Parameter   | Type     | Default | Description                                |
| ----------- | -------- | ------- | ------------------------------------------ |
| `search`    | `string` | —       | Filter by name or slug (case-insensitive)  |
| `status`    | `string` | —       | Filter by status value                     |
| `page`      | `int`    | 1       | Page number (≥ 1)                          |
| `page_size` | `int`    | 20      | Items per page (1–100)                     |

Response (200):

```json
{
  "organizations": [
    {
      "id": "uuid",
      "name": "Acme Corp",
      "slug": "acme-corp",
      "display_name": "Acme Corporation",
      "status": "active",
      "organization_type": "enterprise",
      "is_active": true,
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 42,
    "total_pages": 3,
    "has_next": true,
    "has_prev": false
  }
}
```

### Get Organization Detail

```
GET /api/v1/admin/organizations/{id}
Host: localhost:8001
Authorization: Bearer {token}
```

Response (200): `AdminOrgDetailResponse` — same shape as create response, with populated `user_count`, `invoice_count`, and `payment_total`.

### Update Organization (Partial)

```
PATCH /api/v1/admin/organizations/{id}
Host: localhost:8001
Authorization: Bearer {token}
Content-Type: application/json
```

Request body (all fields optional):

```json
{
  "name": "Acme Corp Updated",
  "status": "suspended",
  "industry": "Technology"
}
```

Setting `status` to `"suspended"` triggers a cascade: all users in the organization are set to `is_active = false`.

Response (200): `AdminOrgDetailResponse`

### Error Responses

| Status | Detail                                              | Cause                          |
| ------ | --------------------------------------------------- | ------------------------------ |
| 401    | `"Invalid authentication credentials"`              | Missing or invalid token       |
| 403    | `"Admin access required"`                           | Non-admin user                 |
| 404    | `"Organization not found"`                          | Invalid org ID                 |
| 409    | `"Organization with this slug already exists"`      | Duplicate slug on create       |
| 422    | Pydantic validation error                           | Invalid field values           |

---

## 2. TypeScript Types

```typescript
// types/adminOrganization.types.ts

export type OrgStatus = "active" | "inactive" | "suspended" | "trial";
export type OrgType = "enterprise" | "business" | "startup" | "individual";

export interface AdminOrgCreate {
  name: string;
  slug: string;
  display_name?: string | null;
  description?: string | null;
  email?: string | null;
  phone?: string | null;
  website?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  organization_type?: OrgType;
  industry?: string | null;
  base_currency?: string;
  status?: OrgStatus;
}

export interface AdminOrgUpdate {
  name?: string;
  display_name?: string | null;
  description?: string | null;
  email?: string | null;
  phone?: string | null;
  website?: string | null;
  address_line1?: string | null;
  address_line2?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  country?: string | null;
  organization_type?: OrgType;
  industry?: string | null;
  base_currency?: string;
  status?: OrgStatus;
  is_active?: boolean;
  settings?: Record<string, any> | null;
  extra_data?: Record<string, any> | null;
}

export interface AdminOrgListItem {
  id: string;
  name: string;
  slug: string;
  display_name: string | null;
  status: OrgStatus;
  organization_type: OrgType;
  is_active: boolean;
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

export interface AdminOrgListResponse {
  organizations: AdminOrgListItem[];
  pagination: PaginationMeta;
}

export interface AdminOrgDetailResponse {
  id: string;
  name: string;
  slug: string;
  display_name: string | null;
  description: string | null;
  email: string | null;
  phone: string | null;
  website: string | null;
  address_line1: string | null;
  address_line2: string | null;
  city: string | null;
  state: string | null;
  postal_code: string | null;
  country: string | null;
  organization_type: OrgType;
  industry: string | null;
  base_currency: string | null;
  logo_url: string | null;
  status: OrgStatus;
  is_active: boolean;
  owner_id: string | null;
  settings: Record<string, any> | null;
  extra_data: Record<string, any> | null;
  created_at: string;
  updated_at: string | null;
  user_count: number;
  invoice_count: number;
  payment_total: string; // Decimal as string
}

export interface AdminOrgFilters {
  search?: string;
  status?: OrgStatus;
  page?: number;
  page_size?: number;
}
```

---

## 3. Frontend Service Layer

```typescript
// services/adminOrganizationService.ts

import apiClient from "./apiClient";
import type {
  AdminOrgCreate,
  AdminOrgUpdate,
  AdminOrgDetailResponse,
  AdminOrgListResponse,
  AdminOrgFilters,
} from "../types/adminOrganization.types";

const BASE = "http://localhost:8001/api/v1";

export const adminOrganizationService = {
  create: (data: AdminOrgCreate) =>
    apiClient.post<AdminOrgDetailResponse>(`${BASE}/admin/organizations`, data),

  list: (filters?: AdminOrgFilters) => {
    const params = new URLSearchParams();
    if (filters?.search) params.set("search", filters.search);
    if (filters?.status) params.set("status", filters.status);
    if (filters?.page) params.set("page", String(filters.page));
    if (filters?.page_size) params.set("page_size", String(filters.page_size));
    const qs = params.toString();
    return apiClient.get<AdminOrgListResponse>(
      `${BASE}/admin/organizations${qs ? `?${qs}` : ""}`
    );
  },

  getById: (id: string) =>
    apiClient.get<AdminOrgDetailResponse>(`${BASE}/admin/organizations/${id}`),

  update: (id: string, data: AdminOrgUpdate) =>
    apiClient.patch<AdminOrgDetailResponse>(
      `${BASE}/admin/organizations/${id}`,
      data
    ),
};
```


---

## 4. React Hooks

### useAdminOrganizations — Fetch paginated list

```typescript
// hooks/useAdminOrganizations.ts

import { useState, useEffect, useCallback } from "react";
import { adminOrganizationService } from "../services/adminOrganizationService";
import type {
  AdminOrgListResponse,
  AdminOrgFilters,
} from "../types/adminOrganization.types";

interface OrgListState {
  data: AdminOrgListResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const useAdminOrganizations = (filters?: AdminOrgFilters) => {
  const [state, setState] = useState<OrgListState>({
    data: null,
    isLoading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminOrganizationService.list(filters);
      setState({ data: result.data, isLoading: false, error: null });
    } catch (err: any) {
      const message =
        err.response?.data?.detail || "Failed to load organizations";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [filters?.search, filters?.status, filters?.page, filters?.page_size]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { ...state, refetch: fetchData };
};
```

### useAdminOrganization — Fetch single org detail

```typescript
// hooks/useAdminOrganization.ts

import { useState, useEffect, useCallback } from "react";
import { adminOrganizationService } from "../services/adminOrganizationService";
import type { AdminOrgDetailResponse } from "../types/adminOrganization.types";

interface OrgDetailState {
  data: AdminOrgDetailResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const useAdminOrganization = (orgId: string) => {
  const [state, setState] = useState<OrgDetailState>({
    data: null,
    isLoading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminOrganizationService.getById(orgId);
      setState({ data: result.data, isLoading: false, error: null });
    } catch (err: any) {
      const message =
        err.response?.data?.detail || "Failed to load organization";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [orgId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { ...state, refetch: fetchData };
};
```

### useCreateOrganization — Create a new org

```typescript
// hooks/useCreateOrganization.ts

import { useState } from "react";
import { adminOrganizationService } from "../services/adminOrganizationService";
import type {
  AdminOrgCreate,
  AdminOrgDetailResponse,
} from "../types/adminOrganization.types";

export const useCreateOrganization = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createOrg = async (
    data: AdminOrgCreate
  ): Promise<AdminOrgDetailResponse> => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminOrganizationService.create(data);
      return result.data;
    } catch (err: any) {
      const message =
        err.response?.data?.detail || "Failed to create organization";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createOrg, loading, error };
};
```

### useUpdateOrganization — Update an existing org

```typescript
// hooks/useUpdateOrganization.ts

import { useState } from "react";
import { adminOrganizationService } from "../services/adminOrganizationService";
import type {
  AdminOrgUpdate,
  AdminOrgDetailResponse,
} from "../types/adminOrganization.types";

export const useUpdateOrganization = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateOrg = async (
    id: string,
    data: AdminOrgUpdate
  ): Promise<AdminOrgDetailResponse> => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminOrganizationService.update(id, data);
      return result.data;
    } catch (err: any) {
      const message =
        err.response?.data?.detail || "Failed to update organization";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { updateOrg, loading, error };
};
```

---

## 5. Module Structure

```
src/
├── features/
│   └── admin/
│       ├── components/
│       │   ├── OrganizationsPage.tsx        # List page with search + filters
│       │   ├── OrganizationDetailPage.tsx   # Single org detail view
│       │   ├── OrganizationForm.tsx         # Create / edit form
│       │   ├── OrganizationTable.tsx        # Table of orgs with pagination
│       │   └── SuspendConfirmDialog.tsx     # Confirmation for suspension cascade
│       ├── hooks/
│       │   ├── useAdminOrganizations.ts
│       │   ├── useAdminOrganization.ts
│       │   ├── useCreateOrganization.ts
│       │   └── useUpdateOrganization.ts
│       ├── services/
│       │   └── adminOrganizationService.ts
│       └── types/
│           └── adminOrganization.types.ts
```

---

## 6. Component Examples

### Organizations List Page

```typescript
// components/OrganizationsPage.tsx

import React, { useState } from "react";
import { useAdminOrganizations } from "../hooks/useAdminOrganizations";
import { OrganizationTable } from "./OrganizationTable";
import type { AdminOrgFilters, OrgStatus } from "../types/adminOrganization.types";

export const OrganizationsPage: React.FC = () => {
  const [filters, setFilters] = useState<AdminOrgFilters>({ page: 1, page_size: 20 });
  const { data, isLoading, error, refetch } = useAdminOrganizations(filters);

  return (
    <div className="admin-organizations">
      <h1>Organizations</h1>

      <div className="filters-bar">
        <input
          type="text"
          placeholder="Search by name or slug..."
          value={filters.search || ""}
          onChange={(e) => setFilters({ ...filters, search: e.target.value, page: 1 })}
        />
        <select
          value={filters.status || ""}
          onChange={(e) =>
            setFilters({ ...filters, status: (e.target.value || undefined) as OrgStatus | undefined, page: 1 })
          }
        >
          <option value="">All Statuses</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
          <option value="suspended">Suspended</option>
          <option value="trial">Trial</option>
        </select>
      </div>

      {isLoading && <div>Loading...</div>}
      {error && <div className="error">{error}</div>}
      {data && (
        <OrganizationTable
          organizations={data.organizations}
          pagination={data.pagination}
          onPageChange={(page) => setFilters({ ...filters, page })}
        />
      )}
    </div>
  );
};
```

### Organization Detail Page

```typescript
// components/OrganizationDetailPage.tsx

import React from "react";
import { useParams } from "react-router-dom";
import { useAdminOrganization } from "../hooks/useAdminOrganization";

export const OrganizationDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { data: org, isLoading, error } = useAdminOrganization(id!);

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!org) return null;

  return (
    <div className="org-detail">
      <h1>{org.name}</h1>
      <span className={`badge badge-${org.status}`}>{org.status}</span>

      <div className="summary-cards">
        <div className="card">
          <h3>Users</h3>
          <span>{org.user_count}</span>
        </div>
        <div className="card">
          <h3>Invoices</h3>
          <span>{org.invoice_count}</span>
        </div>
        <div className="card">
          <h3>Payment Total</h3>
          <span>${parseFloat(org.payment_total).toLocaleString()}</span>
        </div>
      </div>

      <div className="org-info">
        <p>Slug: <code>{org.slug}</code></p>
        <p>Type: {org.organization_type}</p>
        <p>Industry: {org.industry || "—"}</p>
        <p>Currency: {org.base_currency || "—"}</p>
        <p>Country: {org.country || "—"}</p>
        <p>Email: {org.email || "—"}</p>
        <p>Phone: {org.phone || "—"}</p>
        <p>Created: {new Date(org.created_at).toLocaleDateString()}</p>
      </div>
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
    setError("Organization not found");
  } else if (status === 409) {
    setError(message); // "Organization with this slug already exists"
  }
}
```

---

## 8. UI Behavior Notes

- `slug` is set on creation and should be treated as immutable in the UI (not included in update form)
- `payment_total` is returned as a decimal string — parse with `parseFloat()` for display
- Setting status to `"suspended"` cascades deactivation to all org users — show a confirmation dialog before submitting
- The list endpoint returns organizations sorted by `created_at` descending (newest first)
- Search is case-insensitive and matches against both `name` and `slug`
- Pagination: `page` starts at 1, `page_size` max is 100

---

## 9. Testing Checklist

### Unit Tests

- [ ] `adminOrganizationService.list` calls correct URL with query params
- [ ] `adminOrganizationService.create` sends POST with correct body
- [ ] `adminOrganizationService.getById` calls correct URL
- [ ] `adminOrganizationService.update` sends PATCH with correct body
- [ ] `useAdminOrganizations` sets `isLoading` correctly during fetch
- [ ] `useAdminOrganizations` populates `data` on success
- [ ] `useAdminOrganizations` sets `error` on failure
- [ ] `useAdminOrganizations` refetches when filters change
- [ ] `useCreateOrganization` returns created org on success
- [ ] `useCreateOrganization` sets error on 409 (duplicate slug)
- [ ] `useUpdateOrganization` returns updated org on success
- [ ] `OrganizationTable` renders all org rows
- [ ] `OrganizationTable` handles empty list gracefully
- [ ] `OrganizationDetailPage` renders summary counts

### Integration Tests

- [ ] Full flow: list orgs → click org → view detail with counts
- [ ] Create org → appears in list
- [ ] Update org status to suspended → confirmation dialog → success
- [ ] Search filter updates list results
- [ ] Status filter updates list results
- [ ] Pagination navigation works correctly

### Error Scenario Tests

- [ ] 401 response clears token and redirects to login
- [ ] 403 response shows "Admin access required"
- [ ] 404 response shows "Organization not found"
- [ ] 409 response shows duplicate slug error on create form
- [ ] Network error shows appropriate error state

---

## 10. Backend Files Reference

- Schema: `core-service/app/schemas/admin_organization.py`
- Repository: `core-service/app/repositories/admin_organization_repository.py`
- Service: `core-service/app/services/admin_organization_service.py`
- Endpoint: `core-service/app/api/v1/endpoints/admin/organizations.py`
- Router Registration: `core-service/app/api/v1/endpoints/admin/__init__.py`
- Swagger UI: http://localhost:8001/docs (tag: Admin - Organizations)
