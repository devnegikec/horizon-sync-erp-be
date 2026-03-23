---
inclusion: manual
---

# Frontend Admin Users Module - Integration Guide

Complete API reference for building the Admin User Management UI. This module lets system admins create, list, view, and update users across all organizations.

## Base URL & Auth

```
Core Service: http://localhost:8001/api/v1
Auth:         Authorization: Bearer {token}
```

All user admin endpoints require a valid Bearer token with `user_type = "system_admin"`. Non-admin users receive `403 Admin access required`.

---

## 1. User API

### Create User

```
POST /api/v1/admin/users
Host: localhost:8001
Authorization: Bearer {token}
Content-Type: application/json
```

Request body:

```json
{
  "email": "user@example.com",
  "password": "SecurePass1!",
  "first_name": "Jane",
  "last_name": "Doe",
  "organization_id": "uuid",
  "roles": ["user"],
  "phone": "+1-555-0100",
  "user_type": "user"
}
```

Required fields: `email`, `password`, `first_name`, `last_name`, `organization_id`

`roles` must contain values from: `system_admin` | `org_admin` | `user`

`user_type` must be one of: `system_admin` | `organization_admin` | `user` | `guest`

Response (201): `AdminUserDetailResponse`

```json
{
  "id": "uuid",
  "email": "user@example.com",
  "first_name": "Jane",
  "last_name": "Doe",
  "display_name": "Jane Doe",
  "phone": "+1-555-0100",
  "roles": ["user"],
  "user_type": "user",
  "is_active": true,
  "organization_id": "uuid",
  "organization_name": "Acme Corp",
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### List Users

```
GET /api/v1/admin/users?organization_id=uuid&search=jane&is_active=true&page=1&page_size=20
Host: localhost:8001
Authorization: Bearer {token}
```

Query Parameters (all optional):

| Parameter         | Type      | Default | Description                                      |
| ----------------- | --------- | ------- | ------------------------------------------------ |
| `organization_id` | `UUID`    | —       | Filter by organization                           |
| `search`          | `string`  | —       | Search by email, phone, or name (case-insensitive) |
| `is_active`       | `boolean` | —       | Filter by active status                          |
| `page`            | `int`     | 1       | Page number (≥ 1)                                |
| `page_size`       | `int`     | 20      | Items per page (1–100)                           |

Response (200):

```json
{
  "users": [
    {
      "id": "uuid",
      "email": "user@example.com",
      "first_name": "Jane",
      "last_name": "Doe",
      "phone": "+1-555-0100",
      "roles": ["user"],
      "user_type": "user",
      "is_active": true,
      "organization_id": "uuid",
      "organization_name": "Acme Corp",
      "created_at": "2024-01-15T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```

### Get User Detail

```
GET /api/v1/admin/users/{id}
Host: localhost:8001
Authorization: Bearer {token}
```

Response (200): `AdminUserDetailResponse` — same shape as create response.

### Update User (Partial)

```
PATCH /api/v1/admin/users/{id}
Host: localhost:8001
Authorization: Bearer {token}
Content-Type: application/json
```

Request body (all fields optional):

```json
{
  "roles": ["org_admin"],
  "is_active": false,
  "first_name": "Janet",
  "phone": "+1-555-0200"
}
```

Updating `roles` replaces the entire roles array (not append). Changing `is_active` deactivates/reactivates the user.

Response (200): `AdminUserDetailResponse`

### Error Responses

| Status | Detail                                    | Cause                    |
| ------ | ----------------------------------------- | ------------------------ |
| 401    | `"Invalid authentication credentials"`    | Missing or invalid token |
| 403    | `"Admin access required"`                 | Non-admin user           |
| 404    | `"User not found"`                        | Invalid user ID          |
| 409    | `"User with this email already exists"`   | Duplicate email          |
| 422    | Pydantic validation error                 | Invalid field values     |

---

## 2. TypeScript Types

```typescript
// types/adminUser.types.ts

export type AllowedRole = "system_admin" | "org_admin" | "user";
export type UserType = "system_admin" | "organization_admin" | "user" | "guest";

export interface AdminUserCreate {
  email: string;
  password: string;
  first_name: string;
  last_name: string;
  organization_id: string;
  roles?: AllowedRole[];
  phone?: string | null;
  user_type?: UserType;
}

export interface AdminUserUpdate {
  roles?: AllowedRole[];
  is_active?: boolean;
  first_name?: string;
  last_name?: string;
  phone?: string | null;
  user_type?: UserType;
}

export interface AdminUserListItem {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  phone: string | null;
  roles: string[];
  user_type: string;
  is_active: boolean;
  organization_id: string | null;
  organization_name: string | null;
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

export interface AdminUserListResponse {
  users: AdminUserListItem[];
  pagination: PaginationMeta;
}

export interface AdminUserDetailResponse {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string | null;
  phone: string | null;
  roles: string[];
  user_type: string;
  is_active: boolean;
  organization_id: string | null;
  organization_name: string | null;
  created_at: string;
  updated_at: string | null;
}

export interface AdminUserFilters {
  organization_id?: string;
  search?: string;
  is_active?: boolean;
  page?: number;
  page_size?: number;
}
```

---

## 3. Frontend Service Layer

```typescript
// services/adminUserService.ts

import apiClient from "./apiClient";
import type {
  AdminUserCreate,
  AdminUserUpdate,
  AdminUserDetailResponse,
  AdminUserListResponse,
  AdminUserFilters,
} from "../types/adminUser.types";

const BASE = "http://localhost:8001/api/v1";

export const adminUserService = {
  create: (data: AdminUserCreate) =>
    apiClient.post<AdminUserDetailResponse>(`${BASE}/admin/users`, data),

  list: (filters?: AdminUserFilters) => {
    const params = new URLSearchParams();
    if (filters?.organization_id) params.set("organization_id", filters.organization_id);
    if (filters?.search) params.set("search", filters.search);
    if (filters?.is_active !== undefined) params.set("is_active", String(filters.is_active));
    if (filters?.page) params.set("page", String(filters.page));
    if (filters?.page_size) params.set("page_size", String(filters.page_size));
    const qs = params.toString();
    return apiClient.get<AdminUserListResponse>(
      `${BASE}/admin/users${qs ? `?${qs}` : ""}`
    );
  },

  getById: (id: string) =>
    apiClient.get<AdminUserDetailResponse>(`${BASE}/admin/users/${id}`),

  update: (id: string, data: AdminUserUpdate) =>
    apiClient.patch<AdminUserDetailResponse>(`${BASE}/admin/users/${id}`, data),
};
```


---

## 4. React Hooks

### useAdminUsers — Fetch paginated list

```typescript
// hooks/useAdminUsers.ts

import { useState, useEffect, useCallback } from "react";
import { adminUserService } from "../services/adminUserService";
import type { AdminUserListResponse, AdminUserFilters } from "../types/adminUser.types";

interface UserListState {
  data: AdminUserListResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const useAdminUsers = (filters?: AdminUserFilters) => {
  const [state, setState] = useState<UserListState>({
    data: null, isLoading: true, error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminUserService.list(filters);
      setState({ data: result.data, isLoading: false, error: null });
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to load users";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [filters?.organization_id, filters?.search, filters?.is_active, filters?.page, filters?.page_size]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { ...state, refetch: fetchData };
};
```

### useAdminUser — Fetch single user detail

```typescript
// hooks/useAdminUser.ts

import { useState, useEffect, useCallback } from "react";
import { adminUserService } from "../services/adminUserService";
import type { AdminUserDetailResponse } from "../types/adminUser.types";

interface UserDetailState {
  data: AdminUserDetailResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const useAdminUser = (userId: string) => {
  const [state, setState] = useState<UserDetailState>({
    data: null, isLoading: true, error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminUserService.getById(userId);
      setState({ data: result.data, isLoading: false, error: null });
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to load user";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [userId]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { ...state, refetch: fetchData };
};
```

### useCreateUser — Create a new user

```typescript
// hooks/useCreateUser.ts

import { useState } from "react";
import { adminUserService } from "../services/adminUserService";
import type { AdminUserCreate, AdminUserDetailResponse } from "../types/adminUser.types";

export const useCreateUser = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createUser = async (data: AdminUserCreate): Promise<AdminUserDetailResponse> => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminUserService.create(data);
      return result.data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to create user";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createUser, loading, error };
};
```

### useUpdateUser — Update an existing user

```typescript
// hooks/useUpdateUser.ts

import { useState } from "react";
import { adminUserService } from "../services/adminUserService";
import type { AdminUserUpdate, AdminUserDetailResponse } from "../types/adminUser.types";

export const useUpdateUser = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateUser = async (id: string, data: AdminUserUpdate): Promise<AdminUserDetailResponse> => {
    setLoading(true);
    setError(null);
    try {
      const result = await adminUserService.update(id, data);
      return result.data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to update user";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { updateUser, loading, error };
};
```

---

## 5. Module Structure

```
src/
├── features/
│   └── admin/
│       ├── components/
│       │   ├── UsersPage.tsx              # List page with search + filters
│       │   ├── UserDetailPage.tsx         # Single user detail view
│       │   ├── UserForm.tsx               # Create / edit form
│       │   ├── UserTable.tsx              # Table of users with pagination
│       │   └── DeactivateConfirmDialog.tsx # Confirmation for deactivation
│       ├── hooks/
│       │   ├── useAdminUsers.ts
│       │   ├── useAdminUser.ts
│       │   ├── useCreateUser.ts
│       │   └── useUpdateUser.ts
│       ├── services/
│       │   └── adminUserService.ts
│       └── types/
│           └── adminUser.types.ts
```

---

## 6. Component Examples

### Users List Page

```typescript
// components/UsersPage.tsx

import React, { useState } from "react";
import { useAdminUsers } from "../hooks/useAdminUsers";
import { UserTable } from "./UserTable";
import type { AdminUserFilters } from "../types/adminUser.types";

export const UsersPage: React.FC = () => {
  const [filters, setFilters] = useState<AdminUserFilters>({ page: 1, page_size: 20 });
  const { data, isLoading, error } = useAdminUsers(filters);

  return (
    <div className="admin-users">
      <h1>Users</h1>

      <div className="filters-bar">
        <input
          type="text"
          placeholder="Search by email, phone, or name..."
          value={filters.search || ""}
          onChange={(e) => setFilters({ ...filters, search: e.target.value, page: 1 })}
        />
        <select
          value={filters.is_active === undefined ? "" : String(filters.is_active)}
          onChange={(e) =>
            setFilters({
              ...filters,
              is_active: e.target.value === "" ? undefined : e.target.value === "true",
              page: 1,
            })
          }
        >
          <option value="">All Users</option>
          <option value="true">Active</option>
          <option value="false">Inactive</option>
        </select>
      </div>

      {isLoading && <div>Loading...</div>}
      {error && <div className="error">{error}</div>}
      {data && (
        <UserTable
          users={data.users}
          pagination={data.pagination}
          onPageChange={(page) => setFilters({ ...filters, page })}
        />
      )}
    </div>
  );
};
```

### User Detail Page

```typescript
// components/UserDetailPage.tsx

import React from "react";
import { useParams } from "react-router-dom";
import { useAdminUser } from "../hooks/useAdminUser";

export const UserDetailPage: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const { data: user, isLoading, error } = useAdminUser(id!);

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!user) return null;

  return (
    <div className="user-detail">
      <h1>{user.display_name || `${user.first_name} ${user.last_name}`}</h1>
      <span className={`badge badge-${user.is_active ? "active" : "inactive"}`}>
        {user.is_active ? "Active" : "Inactive"}
      </span>

      <div className="user-info">
        <p>Email: {user.email}</p>
        <p>Phone: {user.phone || "—"}</p>
        <p>User Type: {user.user_type}</p>
        <p>Roles: {user.roles.join(", ") || "—"}</p>
        <p>Organization: {user.organization_name || "—"}</p>
        <p>Created: {new Date(user.created_at).toLocaleDateString()}</p>
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
    setError("User not found");
  } else if (status === 409) {
    setError(message); // "User with this email already exists"
  }
}
```

---

## 8. UI Behavior Notes

- `email` is set on creation and should be treated as immutable in the UI (not included in update form)
- Updating `roles` replaces the entire array — the UI should show all current roles and let the admin select new ones
- Deactivating a user (`is_active = false`) should show a confirmation dialog
- Search is case-insensitive and matches against `email`, `phone`, `first_name`, and `last_name`
- The `organization_id` filter can be combined with search and `is_active` filters
- Pagination: `page` starts at 1, `page_size` max is 100
- Allowed roles: `system_admin`, `org_admin`, `user`

---

## 9. Testing Checklist

### Unit Tests

- [ ] `adminUserService.list` calls correct URL with query params
- [ ] `adminUserService.create` sends POST with correct body
- [ ] `adminUserService.getById` calls correct URL
- [ ] `adminUserService.update` sends PATCH with correct body
- [ ] `useAdminUsers` sets `isLoading` correctly during fetch
- [ ] `useAdminUsers` populates `data` on success
- [ ] `useAdminUsers` sets `error` on failure
- [ ] `useAdminUsers` refetches when filters change
- [ ] `useCreateUser` returns created user on success
- [ ] `useCreateUser` sets error on 409 (duplicate email)
- [ ] `useUpdateUser` returns updated user on success
- [ ] `UserTable` renders all user rows
- [ ] `UserTable` handles empty list gracefully
- [ ] `UserDetailPage` renders user info and roles

### Integration Tests

- [ ] Full flow: list users → click user → view detail
- [ ] Create user → appears in list
- [ ] Update user roles → roles updated in detail view
- [ ] Deactivate user → confirmation dialog → success
- [ ] Search filter updates list results
- [ ] Organization filter updates list results
- [ ] Active/inactive filter works correctly
- [ ] Pagination navigation works correctly

### Error Scenario Tests

- [ ] 401 response clears token and redirects to login
- [ ] 403 response shows "Admin access required"
- [ ] 404 response shows "User not found"
- [ ] 409 response shows duplicate email error on create form
- [ ] Network error shows appropriate error state

---

## 10. Backend Files Reference

- Schema: `core-service/app/schemas/admin_user.py`
- Repository: `core-service/app/repositories/admin_user_repository.py`
- Service: `core-service/app/services/admin_user_service.py`
- Endpoint: `core-service/app/api/v1/endpoints/admin/users.py`
- Router Registration: `core-service/app/api/v1/endpoints/admin/__init__.py`
- Swagger UI: http://localhost:8001/docs (tag: Admin - Users)
