---
inclusion: manual
---

# Frontend Admin Activity Logs Module - Integration Guide

Complete API reference for building the Admin User Activity Monitoring UI. This module lets system admins view user activity logs across all organizations and inspect login history for individual users.

## Base URL & Auth

```
Core Service: http://localhost:8001/api/v1
Auth:         Authorization: Bearer {token}
```

All activity log admin endpoints require a valid Bearer token with `user_type = "system_admin"`. Non-admin users receive `403 Admin access required`.

---

## 1. Activity Log API

### List Activity Logs

```
GET /api/v1/admin/activity-logs?user_id=uuid&organization_id=uuid&action=login&date_from=2024-01-01T00:00:00&date_to=2024-12-31T23:59:59&page=1&page_size=20
Host: localhost:8001
Authorization: Bearer {token}
```

Query Parameters (all optional):

| Parameter         | Type       | Default | Description                              |
| ----------------- | ---------- | ------- | ---------------------------------------- |
| `user_id`         | `UUID`     | —       | Filter by user                           |
| `organization_id` | `UUID`     | —       | Filter by organization                   |
| `action`          | `string`   | —       | Filter by action type                    |
| `date_from`       | `datetime` | —       | Filter logs from this date               |
| `date_to`         | `datetime` | —       | Filter logs up to this date              |
| `page`            | `int`      | 1       | Page number (≥ 1)                        |
| `page_size`       | `int`      | 20      | Items per page (1–100)                   |

Valid `action` values: `login`, `logout`, `login_failed`, `page_view`, `data_create`, `data_update`, `data_delete`

Response (200):

```json
{
  "activity_logs": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "organization_id": "uuid",
      "action": "login",
      "resource_type": null,
      "resource_id": null,
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 ...",
      "metadata": null,
      "created_at": "2024-06-15T10:00:00Z",
      "user_email": "user@example.com",
      "organization_name": "Acme Corp"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 500,
    "total_pages": 25,
    "has_next": true,
    "has_prev": false
  }
}
```

### Get Login History

```
GET /api/v1/admin/activity-logs/users/{user_id}/login-history?page=1&page_size=20
Host: localhost:8001
Authorization: Bearer {token}
```

Path Parameters:

| Parameter | Type   | Description                    |
| --------- | ------ | ------------------------------ |
| `user_id` | `UUID` | User to get login history for  |

Query Parameters (optional):

| Parameter   | Type  | Default | Description            |
| ----------- | ----- | ------- | ---------------------- |
| `page`      | `int` | 1       | Page number (≥ 1)      |
| `page_size` | `int` | 20      | Items per page (1–100) |

Response (200):

```json
{
  "user_id": "uuid",
  "login_history": [
    {
      "id": "uuid",
      "user_id": "uuid",
      "organization_id": "uuid",
      "action": "login",
      "resource_type": null,
      "resource_id": null,
      "ip_address": "192.168.1.100",
      "user_agent": "Mozilla/5.0 ...",
      "metadata": null,
      "created_at": "2024-06-15T10:00:00Z",
      "user_email": "user@example.com",
      "organization_name": "Acme Corp"
    },
    {
      "id": "uuid",
      "user_id": "uuid",
      "organization_id": "uuid",
      "action": "login_failed",
      "resource_type": null,
      "resource_id": null,
      "ip_address": "10.0.0.50",
      "user_agent": "Mozilla/5.0 ...",
      "metadata": {"reason": "invalid_password"},
      "created_at": "2024-06-14T08:30:00Z",
      "user_email": "user@example.com",
      "organization_name": "Acme Corp"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 45,
    "total_pages": 3,
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
| 422    | Pydantic validation error                 | Invalid field values     |

---

## 2. TypeScript Types

```typescript
// types/adminActivityLog.types.ts

export type ActivityAction =
  | "login"
  | "logout"
  | "login_failed"
  | "page_view"
  | "data_create"
  | "data_update"
  | "data_delete";

export interface ActivityLogItem {
  id: string;
  user_id: string;
  organization_id: string;
  action: ActivityAction;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  user_agent: string | null;
  metadata: Record<string, any> | null;
  created_at: string;
  user_email: string | null;
  organization_name: string | null;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ActivityLogListResponse {
  activity_logs: ActivityLogItem[];
  pagination: PaginationMeta;
}

export interface LoginHistoryResponse {
  user_id: string;
  login_history: ActivityLogItem[];
  pagination: PaginationMeta;
}

export interface ActivityLogFilters {
  user_id?: string;
  organization_id?: string;
  action?: ActivityAction;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface LoginHistoryFilters {
  page?: number;
  page_size?: number;
}
```

---

## 3. Frontend Service Layer

```typescript
// services/adminActivityLogService.ts

import apiClient from "./apiClient";
import type {
  ActivityLogListResponse,
  ActivityLogFilters,
  LoginHistoryResponse,
  LoginHistoryFilters,
} from "../types/adminActivityLog.types";

const BASE = "http://localhost:8001/api/v1";

export const adminActivityLogService = {
  list: (filters?: ActivityLogFilters) => {
    const params = new URLSearchParams();
    if (filters?.user_id) params.set("user_id", filters.user_id);
    if (filters?.organization_id) params.set("organization_id", filters.organization_id);
    if (filters?.action) params.set("action", filters.action);
    if (filters?.date_from) params.set("date_from", filters.date_from);
    if (filters?.date_to) params.set("date_to", filters.date_to);
    if (filters?.page) params.set("page", String(filters.page));
    if (filters?.page_size) params.set("page_size", String(filters.page_size));
    const qs = params.toString();
    return apiClient.get<ActivityLogListResponse>(
      `${BASE}/admin/activity-logs${qs ? `?${qs}` : ""}`
    );
  },

  getLoginHistory: (userId: string, filters?: LoginHistoryFilters) => {
    const params = new URLSearchParams();
    if (filters?.page) params.set("page", String(filters.page));
    if (filters?.page_size) params.set("page_size", String(filters.page_size));
    const qs = params.toString();
    return apiClient.get<LoginHistoryResponse>(
      `${BASE}/admin/activity-logs/users/${userId}/login-history${qs ? `?${qs}` : ""}`
    );
  },
};
```

---

## 4. React Hooks

### useAdminActivityLogs — Fetch paginated activity log list

```typescript
// hooks/useAdminActivityLogs.ts

import { useState, useEffect, useCallback } from "react";
import { adminActivityLogService } from "../services/adminActivityLogService";
import type { ActivityLogListResponse, ActivityLogFilters } from "../types/adminActivityLog.types";

interface ActivityLogListState {
  data: ActivityLogListResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const useAdminActivityLogs = (filters?: ActivityLogFilters) => {
  const [state, setState] = useState<ActivityLogListState>({
    data: null, isLoading: true, error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminActivityLogService.list(filters);
      setState({ data: result.data, isLoading: false, error: null });
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to load activity logs";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [
    filters?.user_id, filters?.organization_id, filters?.action,
    filters?.date_from, filters?.date_to, filters?.page, filters?.page_size,
  ]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return { ...state, refetch: fetchData };
};
```

### useLoginHistory — Fetch login history for a user

```typescript
// hooks/useLoginHistory.ts

import { useState, useEffect, useCallback } from "react";
import { adminActivityLogService } from "../services/adminActivityLogService";
import type { LoginHistoryResponse, LoginHistoryFilters } from "../types/adminActivityLog.types";

interface LoginHistoryState {
  data: LoginHistoryResponse | null;
  isLoading: boolean;
  error: string | null;
}

export const useLoginHistory = (userId: string, filters?: LoginHistoryFilters) => {
  const [state, setState] = useState<LoginHistoryState>({
    data: null, isLoading: true, error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminActivityLogService.getLoginHistory(userId, filters);
      setState({ data: result.data, isLoading: false, error: null });
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to load login history";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [userId, filters?.page, filters?.page_size]);

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
│       │   ├── ActivityLogsPage.tsx         # Activity log list page with filters
│       │   ├── ActivityLogTable.tsx         # Table of activity logs with pagination
│       │   └── LoginHistoryPage.tsx         # Login history for a specific user
│       ├── hooks/
│       │   ├── useAdminActivityLogs.ts
│       │   └── useLoginHistory.ts
│       ├── services/
│       │   └── adminActivityLogService.ts
│       └── types/
│           └── adminActivityLog.types.ts
```

---

## 6. Component Examples

### Activity Logs List Page

```typescript
// components/ActivityLogsPage.tsx

import React, { useState } from "react";
import { useAdminActivityLogs } from "../hooks/useAdminActivityLogs";
import { ActivityLogTable } from "./ActivityLogTable";
import type { ActivityLogFilters, ActivityAction } from "../types/adminActivityLog.types";

const ACTION_OPTIONS: ActivityAction[] = [
  "login", "logout", "login_failed", "page_view",
  "data_create", "data_update", "data_delete",
];

export const ActivityLogsPage: React.FC = () => {
  const [filters, setFilters] = useState<ActivityLogFilters>({ page: 1, page_size: 20 });
  const { data, isLoading, error } = useAdminActivityLogs(filters);

  return (
    <div className="admin-activity-logs">
      <h1>User Activity Logs</h1>

      <div className="filters-bar">
        <select
          value={filters.action || ""}
          onChange={(e) =>
            setFilters({ ...filters, action: (e.target.value || undefined) as ActivityAction | undefined, page: 1 })
          }
          aria-label="Filter by action"
        >
          <option value="">All Actions</option>
          {ACTION_OPTIONS.map((a) => (
            <option key={a} value={a}>{a.replace("_", " ")}</option>
          ))}
        </select>

        <input
          type="date"
          aria-label="Date from"
          value={filters.date_from?.split("T")[0] || ""}
          onChange={(e) =>
            setFilters({ ...filters, date_from: e.target.value ? `${e.target.value}T00:00:00` : undefined, page: 1 })
          }
        />
        <input
          type="date"
          aria-label="Date to"
          value={filters.date_to?.split("T")[0] || ""}
          onChange={(e) =>
            setFilters({ ...filters, date_to: e.target.value ? `${e.target.value}T23:59:59` : undefined, page: 1 })
          }
        />
      </div>

      {isLoading && <div>Loading...</div>}
      {error && <div className="error" role="alert">{error}</div>}
      {data && (
        <ActivityLogTable
          logs={data.activity_logs}
          pagination={data.pagination}
          onPageChange={(page) => setFilters({ ...filters, page })}
        />
      )}
    </div>
  );
};
```

### Login History Page

```typescript
// components/LoginHistoryPage.tsx

import React, { useState } from "react";
import { useParams } from "react-router-dom";
import { useLoginHistory } from "../hooks/useLoginHistory";
import type { LoginHistoryFilters } from "../types/adminActivityLog.types";

export const LoginHistoryPage: React.FC = () => {
  const { userId } = useParams<{ userId: string }>();
  const [filters, setFilters] = useState<LoginHistoryFilters>({ page: 1, page_size: 20 });
  const { data, isLoading, error } = useLoginHistory(userId!, filters);

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div className="error" role="alert">{error}</div>;
  if (!data) return null;

  return (
    <div className="login-history">
      <h1>Login History</h1>
      <p>User: {data.user_id}</p>

      <table>
        <thead>
          <tr>
            <th>Action</th>
            <th>IP Address</th>
            <th>User Agent</th>
            <th>Date</th>
          </tr>
        </thead>
        <tbody>
          {data.login_history.map((entry) => (
            <tr key={entry.id}>
              <td>
                <span className={entry.action === "login" ? "badge-success" : "badge-danger"}>
                  {entry.action}
                </span>
              </td>
              <td>{entry.ip_address || "—"}</td>
              <td title={entry.user_agent || ""}>{entry.user_agent?.substring(0, 50) || "—"}</td>
              <td>{new Date(entry.created_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="pagination">
        <button
          disabled={!data.pagination.has_prev}
          onClick={() => setFilters({ ...filters, page: (filters.page || 1) - 1 })}
        >
          Previous
        </button>
        <span>Page {data.pagination.page} of {data.pagination.total_pages}</span>
        <button
          disabled={!data.pagination.has_next}
          onClick={() => setFilters({ ...filters, page: (filters.page || 1) + 1 })}
        >
          Next
        </button>
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
  }
}
```

---

## 8. UI Behavior Notes

- Activity logs are sorted by `created_at` descending (most recent first)
- The `metadata` field is a JSONB object — display as expandable JSON or key-value pairs
- `user_email` and `organization_name` are joined fields for display context — show as columns in tables
- Login history only returns `login` and `login_failed` actions for the specified user
- `user_agent` strings can be long — truncate in table cells and show full value on hover/tooltip
- `ip_address` supports both IPv4 and IPv6 (max 45 chars)
- Date range filters use `created_at` for filtering
- Pagination: `page` starts at 1, `page_size` max is 100

---

## 9. Testing Checklist

### Unit Tests

- [ ] `adminActivityLogService.list` calls correct URL with query params
- [ ] `adminActivityLogService.getLoginHistory` calls correct URL with user ID
- [ ] `useAdminActivityLogs` sets `isLoading` correctly during fetch
- [ ] `useAdminActivityLogs` populates `data` on success
- [ ] `useAdminActivityLogs` sets `error` on failure
- [ ] `useLoginHistory` sets `isLoading` correctly during fetch
- [ ] `useLoginHistory` populates `data` on success
- [ ] `useLoginHistory` sets `error` on failure

### Integration Tests

- [ ] Activity logs list returns paginated results
- [ ] Activity logs list filters by user_id correctly
- [ ] Activity logs list filters by organization_id correctly
- [ ] Activity logs list filters by action correctly
- [ ] Activity logs list filters by date range correctly
- [ ] Login history returns only login/login_failed entries
- [ ] Login history is scoped to the specified user
- [ ] Non-admin users receive 403

### Accessibility Tests

- [ ] Filter controls have proper labels
- [ ] Table has proper headers and scope attributes
- [ ] Error messages use role="alert"
- [ ] Pagination controls are keyboard accessible
- [ ] Action badges have sufficient color contrast
