---
inclusion: manual
---

# Frontend Admin Auth Module - Integration Guide

Complete API reference for building the Admin Portal authentication layer. This module handles admin identity verification, profile fetching, and route protection — ensuring only `system_admin` users can access admin portal pages.

## Base URLs & Auth

```
Identity Service: http://localhost:8000/api/v1
Core Service:     http://localhost:8001/api/v1
Auth:             Authorization: Bearer {token}
```

All admin endpoints require a valid Bearer token with `user_type = "system_admin"`. Token is stored in `localStorage.getItem("token")`.

---

## Architecture

Admin authentication spans two services:

| Service          | Responsibility                                  | Base URL                          |
| ---------------- | ----------------------------------------------- | --------------------------------- |
| Identity Service | Admin profile (`/identity/admin/me`)             | `http://localhost:8000/api/v1`    |
| Core Service     | All admin data endpoints (`/admin/*`)            | `http://localhost:8001/api/v1`    |

Both services enforce the `require_admin` gate independently:

- **Identity Service**: Validates `user_type == UserType.SYSTEM_ADMIN` via database lookup.
- **Core Service**: Validates `user_type == "system_admin"` from the JWT token payload.

Non-admin users receive a `403` response with `"Admin access required"` from either service.

---

## 1. Admin Auth API

### Get Admin Profile

```
GET /api/v1/identity/admin/me
Host: localhost:8000
Authorization: Bearer {token}
```

Returns the authenticated admin's profile. This is the authoritative source for admin identity.

Response (200):

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "admin@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "display_name": "John Doe",
  "user_type": "system_admin",
  "organization_id": "660e8400-e29b-41d4-a716-446655440000",
  "permissions": ["item.read", "item.create", "warehouse.*"]
}
```

### Core Service Admin Gate

All core-service admin endpoints live under `/api/v1/admin/`. Every request is validated by the `require_admin` dependency before reaching the handler.

```
GET /api/v1/admin/dashboard/overview
Host: localhost:8001
Authorization: Bearer {token}
```

### Error Responses

| Scenario                        | Status | Detail                                  | Service          |
| ------------------------------- | ------ | --------------------------------------- | ---------------- |
| Missing or invalid Bearer token | 401    | `"Invalid authentication credentials"`  | Both             |
| Invalid token type              | 401    | `"Invalid token type"`                  | Both             |
| User not found                  | 401    | `"User not found"`                      | Identity Service |
| Inactive user                   | 403    | `"Inactive user"`                       | Identity Service |
| Non-admin user (`user_type != system_admin`) | 403 | `"Admin access required"` | Both             |
| Identity service unavailable    | 503    | `"Identity service unavailable"`        | Core Service     |

### Permissions

The `/identity/admin/me` endpoint uses the `require_admin` gate — no additional RBAC permission is needed. All core-service `/admin/*` endpoints also use `require_admin` (bypasses `require_permission` checks).

---

## 2. TypeScript Types

```typescript
// types/adminAuth.types.ts

export interface AdminProfile {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  display_name: string | null;
  user_type: "system_admin";
  organization_id: string | null;
  permissions: string[];
}

export interface AdminAuthState {
  profile: AdminProfile | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface ApiError {
  detail: string;
}
```

---

## 3. Frontend Service Layer

```typescript
// services/adminAuthService.ts

import apiClient from "./apiClient";
import type { AdminProfile } from "../types/adminAuth.types";

const IDENTITY_BASE = "http://localhost:8000/api/v1";

/**
 * Admin auth service.
 *
 * Uses the identity-service for profile fetching (authoritative source).
 * The core-service admin gate is handled automatically by apiClient
 * when calling /admin/* endpoints — no extra service method needed.
 */
export const adminAuthService = {
  /**
   * Fetch the current admin profile from identity-service.
   * Returns 403 if the user is not a system_admin.
   */
  getAdminProfile: () =>
    apiClient.get<AdminProfile>(`${IDENTITY_BASE}/identity/admin/me`),

  /**
   * Check if the current token belongs to an admin user.
   * Returns true if the profile fetch succeeds, false otherwise.
   */
  checkAdminAccess: async (): Promise<boolean> => {
    try {
      await apiClient.get<AdminProfile>(`${IDENTITY_BASE}/identity/admin/me`);
      return true;
    } catch {
      return false;
    }
  },
};
```

---

## 4. React Hooks

### useAdminProfile — Fetch and cache admin profile

```typescript
// hooks/useAdminProfile.ts

import { useState, useEffect, useCallback } from "react";
import { adminAuthService } from "../services/adminAuthService";
import type {
  AdminProfile,
  AdminAuthState,
} from "../types/adminAuth.types";

export const useAdminProfile = () => {
  const [state, setState] = useState<AdminAuthState>({
    profile: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
  });

  const fetchProfile = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminAuthService.getAdminProfile();
      setState({
        profile: result.data,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
    } catch (err: any) {
      const status = err.response?.status;
      let errorMessage = "Failed to fetch admin profile";

      if (status === 401) {
        errorMessage = "Authentication required. Please log in.";
      } else if (status === 403) {
        errorMessage = "Admin access required. You do not have permission.";
      } else if (status === 503) {
        errorMessage = "Identity service unavailable. Please try again later.";
      }

      setState({
        profile: null,
        isAuthenticated: false,
        isLoading: false,
        error: errorMessage,
      });
    }
  }, []);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  return { ...state, refetch: fetchProfile };
};
```

### useAdminGuard — Protect admin routes

```typescript
// hooks/useAdminGuard.ts

import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAdminProfile } from "./useAdminProfile";

/**
 * Hook that redirects non-admin users away from admin pages.
 * Use at the top of any admin page component or in a route guard.
 *
 * @param redirectTo - Path to redirect non-admin users (default: "/")
 */
export const useAdminGuard = (redirectTo: string = "/") => {
  const { profile, isAuthenticated, isLoading, error } = useAdminProfile();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      navigate(redirectTo, { replace: true });
    }
  }, [isLoading, isAuthenticated, navigate, redirectTo]);

  return { profile, isLoading, isAuthenticated, error };
};
```

---

## 5. Module Structure

```
src/
├── features/
│   └── admin/
│       ├── components/
│       │   ├── AdminLayout.tsx            # Layout wrapper with admin nav
│       │   ├── AdminGuard.tsx             # Route guard component
│       │   └── AdminProfileBadge.tsx      # Profile display in header
│       ├── hooks/
│       │   ├── useAdminProfile.ts
│       │   └── useAdminGuard.ts
│       ├── services/
│       │   └── adminAuthService.ts
│       └── types/
│           └── adminAuth.types.ts
```

---

## 6. Component Examples

### Admin Route Guard

```typescript
// components/AdminGuard.tsx

import React from "react";
import { useAdminGuard } from "../hooks/useAdminGuard";

interface AdminGuardProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const AdminGuard: React.FC<AdminGuardProps> = ({
  children,
  fallback = <div>Loading...</div>,
}) => {
  const { isLoading, isAuthenticated, error } = useAdminGuard();

  if (isLoading) return <>{fallback}</>;

  if (!isAuthenticated) {
    return (
      <div className="admin-access-denied">
        <h2>Access Denied</h2>
        <p>{error || "You do not have admin access."}</p>
      </div>
    );
  }

  return <>{children}</>;
};
```

### Admin Layout with Profile Badge

```typescript
// components/AdminLayout.tsx

import React from "react";
import { Outlet } from "react-router-dom";
import { AdminGuard } from "./AdminGuard";
import { AdminProfileBadge } from "./AdminProfileBadge";

export const AdminLayout: React.FC = () => {
  return (
    <AdminGuard>
      <div className="admin-layout">
        <header className="admin-header">
          <h1>Admin Portal</h1>
          <AdminProfileBadge />
        </header>
        <nav className="admin-nav">
          <a href="/admin/dashboard">Dashboard</a>
          <a href="/admin/organizations">Organizations</a>
          <a href="/admin/users">Users</a>
          <a href="/admin/invoices">Invoices</a>
          <a href="/admin/activity-logs">Activity</a>
          <a href="/admin/audit-logs">Audit Trail</a>
          <a href="/admin/notifications">Notifications</a>
        </nav>
        <main className="admin-content">
          <Outlet />
        </main>
      </div>
    </AdminGuard>
  );
};
```

### Admin Profile Badge

```typescript
// components/AdminProfileBadge.tsx

import React from "react";
import { useAdminProfile } from "../hooks/useAdminProfile";

export const AdminProfileBadge: React.FC = () => {
  const { profile, isLoading } = useAdminProfile();

  if (isLoading || !profile) return null;

  const displayName =
    profile.display_name || `${profile.first_name} ${profile.last_name}`;

  return (
    <div className="admin-profile-badge">
      <span className="admin-badge">Admin</span>
      <span className="admin-name">{displayName}</span>
      <span className="admin-email">{profile.email}</span>
    </div>
  );
};
```

---

## 7. Navigation & Routing

Wrap all admin routes with the `AdminLayout` component:

```typescript
// In your router config:
import { AdminLayout } from "./features/admin/components/AdminLayout";

const adminRoutes = {
  path: "/admin",
  element: <AdminLayout />,
  children: [
    { path: "dashboard", element: <AdminDashboardPage /> },
    { path: "organizations", element: <AdminOrganizationsPage /> },
    { path: "users", element: <AdminUsersPage /> },
    { path: "invoices", element: <AdminInvoicesPage /> },
    { path: "payments", element: <AdminPaymentsPage /> },
    { path: "activity-logs", element: <AdminActivityLogsPage /> },
    { path: "subscriptions", element: <AdminSubscriptionsPage /> },
    { path: "audit-logs", element: <AdminAuditLogsPage /> },
    { path: "notifications", element: <AdminNotificationsPage /> },
    { path: "export", element: <AdminExportPage /> },
  ],
};
```

---

## 8. Error Handling

All errors return:

```json
{ "detail": "Human-readable error message" }
```

Extract error message:

```typescript
catch (err: any) {
  const message = err.response?.data?.detail || "An error occurred";
  const status = err.response?.status;

  if (status === 401) {
    // Token expired or invalid — redirect to login
    localStorage.removeItem("token");
    window.location.href = "/login";
  } else if (status === 403) {
    // Not an admin — show access denied
    setError("Admin access required");
  } else if (status === 503) {
    // Service unavailable — show retry
    setError("Service temporarily unavailable. Please try again.");
  }
}
```

Common status codes: `401` (unauthenticated), `403` (not admin), `503` (service unavailable).

---

## 9. UI Behavior Notes

- The admin profile should be fetched once on app load and cached for the session
- If the `/identity/admin/me` call returns 403, redirect the user to the main app (not the admin portal)
- If the token expires (401), clear `localStorage` and redirect to login
- The `permissions` array from the admin profile can be used for fine-grained UI visibility (e.g., hiding export buttons if the admin lacks specific permissions), though `system_admin` users bypass RBAC checks on the backend
- `organization_id` may be `null` if the admin is not assigned to any organization — handle gracefully in the UI
- `display_name` may be `null` — fall back to `first_name + last_name`

---

## 10. Testing Checklist

### Unit Tests

- [ ] `adminAuthService.getAdminProfile` calls correct URL (`/api/v1/identity/admin/me`)
- [ ] `adminAuthService.checkAdminAccess` returns `true` on 200, `false` on 403/401
- [ ] `useAdminProfile` sets `isAuthenticated = true` and populates `profile` on success
- [ ] `useAdminProfile` sets `isAuthenticated = false` and `error` message on 401
- [ ] `useAdminProfile` sets `isAuthenticated = false` and `error` message on 403
- [ ] `useAdminProfile` handles 503 (service unavailable) gracefully
- [ ] `useAdminGuard` redirects to `redirectTo` path when not authenticated
- [ ] `useAdminGuard` does not redirect while `isLoading` is true
- [ ] `AdminGuard` renders children when authenticated
- [ ] `AdminGuard` renders access denied message when not authenticated
- [ ] `AdminProfileBadge` displays `display_name` when available
- [ ] `AdminProfileBadge` falls back to `first_name + last_name` when `display_name` is null

### Integration Tests

- [ ] Full flow: login → fetch admin profile → render admin layout
- [ ] Non-admin user is redirected away from `/admin/*` routes
- [ ] Expired token triggers redirect to login page
- [ ] Network error on profile fetch shows appropriate error state

### Error Scenario Tests

- [ ] 401 response clears token and redirects to login
- [ ] 403 response shows "Admin access required" message
- [ ] 503 response shows "Service unavailable" with retry option
- [ ] Missing `display_name` field renders fallback name correctly
- [ ] Missing `organization_id` (null) does not break profile display

---

## 11. Backend Files Reference

- Identity Service — Admin Auth Endpoint: `identity-service/app/api/v1/endpoints/admin/auth.py`
- Identity Service — Admin Schema: `identity-service/app/schemas/admin.py`
- Identity Service — `require_admin` Dependency: `identity-service/app/dependencies.py`
- Identity Service — Router Mount: `identity-service/app/api/v1/router.py` (prefix: `/identity/admin`)
- Core Service — `require_admin` Dependency: `core-service/app/dependencies.py`
- Core Service — Admin Router: `core-service/app/api/v1/endpoints/admin/__init__.py`
- Swagger UI (Identity): http://localhost:8000/docs (tag: Admin Auth)
- Swagger UI (Core): http://localhost:8001/docs (tag: Admin - *)
