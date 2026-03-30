---
inclusion: manual
---

# Frontend Admin Dashboard Module - Integration Guide

Complete API reference for building the Admin Portal dashboard page. This module provides aggregated platform metrics (organizations, users, revenue) and recent activity — giving system admins a quick pulse on the entire system.

## Base URL & Auth

```
Core Service: http://localhost:8001/api/v1
Auth:         Authorization: Bearer {token}
```

All dashboard endpoints require a valid Bearer token with `user_type = "system_admin"`. Non-admin users receive `403 Admin access required`.

---

## 1. Dashboard API

### Get Dashboard Overview

```
GET /api/v1/admin/dashboard/overview
Host: localhost:8001
Authorization: Bearer {token}
```

Query Parameters (all optional):

| Parameter   | Type       | Description                          |
| ----------- | ---------- | ------------------------------------ |
| `date_from` | `datetime` | Start of date range (ISO 8601)       |
| `date_to`   | `datetime` | End of date range (ISO 8601)         |

Date range filters apply to revenue metrics and recent activity only. Organization and user counts are always unfiltered totals.

Response (200):

```json
{
  "organizations": {
    "total": 42,
    "active": 35,
    "on_trial": 7
  },
  "users": {
    "total": 320,
    "active": 285
  },
  "revenue": {
    "total_invoiced": "125000.00",
    "total_outstanding": "18500.50",
    "total_received": "106500.00"
  },
  "recent_activity": [
    {
      "id": "a1b2c3d4-...",
      "user_id": "u1u2u3u4-...",
      "organization_id": "o1o2o3o4-...",
      "action": "login",
      "resource_type": null,
      "resource_id": null,
      "ip_address": "192.168.1.1",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Error Responses

| Status | Detail                                 | Cause                        |
| ------ | -------------------------------------- | ---------------------------- |
| 401    | `"Invalid authentication credentials"` | Missing or invalid token     |
| 403    | `"Admin access required"`              | Non-admin user               |
| 503    | `"Identity service unavailable"`       | Identity service unreachable |

---

## 2. TypeScript Types

```typescript
// types/adminDashboard.types.ts

export interface OrgMetrics {
  total: number;
  active: number;
  on_trial: number;
}

export interface UserMetrics {
  total: number;
  active: number;
}

export interface RevenueMetrics {
  total_invoiced: string; // Decimal as string
  total_outstanding: string;
  total_received: string;
}

export interface ActivityLogItem {
  id: string;
  user_id: string;
  organization_id: string;
  action: string;
  resource_type: string | null;
  resource_id: string | null;
  ip_address: string | null;
  created_at: string; // ISO 8601
}

export interface DashboardOverview {
  organizations: OrgMetrics;
  users: UserMetrics;
  revenue: RevenueMetrics;
  recent_activity: ActivityLogItem[];
}

export interface DashboardFilters {
  date_from?: string; // ISO 8601
  date_to?: string;
}
```

---

## 3. Frontend Service Layer

```typescript
// services/adminDashboardService.ts

import apiClient from "./apiClient";
import type {
  DashboardOverview,
  DashboardFilters,
} from "../types/adminDashboard.types";

const BASE = "http://localhost:8001/api/v1";

export const adminDashboardService = {
  /**
   * Fetch the dashboard overview metrics.
   * Optional date range filters apply to revenue and activity only.
   */
  getOverview: (filters?: DashboardFilters) => {
    const params = new URLSearchParams();
    if (filters?.date_from) params.set("date_from", filters.date_from);
    if (filters?.date_to) params.set("date_to", filters.date_to);
    const qs = params.toString();
    return apiClient.get<DashboardOverview>(
      `${BASE}/admin/dashboard/overview${qs ? `?${qs}` : ""}`
    );
  },
};
```

---

## 4. React Hooks

### useDashboardOverview — Fetch and cache dashboard data

```typescript
// hooks/useDashboardOverview.ts

import { useState, useEffect, useCallback } from "react";
import { adminDashboardService } from "../services/adminDashboardService";
import type {
  DashboardOverview,
  DashboardFilters,
} from "../types/adminDashboard.types";

interface DashboardState {
  data: DashboardOverview | null;
  isLoading: boolean;
  error: string | null;
}

export const useDashboardOverview = (filters?: DashboardFilters) => {
  const [state, setState] = useState<DashboardState>({
    data: null,
    isLoading: true,
    error: null,
  });

  const fetchData = useCallback(async () => {
    setState((prev) => ({ ...prev, isLoading: true, error: null }));
    try {
      const result = await adminDashboardService.getOverview(filters);
      setState({ data: result.data, isLoading: false, error: null });
    } catch (err: any) {
      const message =
        err.response?.data?.detail || "Failed to load dashboard data";
      setState({ data: null, isLoading: false, error: message });
    }
  }, [filters?.date_from, filters?.date_to]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

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
│       │   ├── DashboardPage.tsx
│       │   ├── MetricCard.tsx
│       │   ├── RevenueCard.tsx
│       │   ├── RecentActivityTable.tsx
│       │   └── DateRangeFilter.tsx
│       ├── hooks/
│       │   └── useDashboardOverview.ts
│       ├── services/
│       │   └── adminDashboardService.ts
│       └── types/
│           └── adminDashboard.types.ts
```

---

## 6. Component Examples

### Dashboard Page

```typescript
// components/DashboardPage.tsx

import React, { useState } from "react";
import { useDashboardOverview } from "../hooks/useDashboardOverview";
import { MetricCard } from "./MetricCard";
import { RevenueCard } from "./RevenueCard";
import { RecentActivityTable } from "./RecentActivityTable";
import type { DashboardFilters } from "../types/adminDashboard.types";

export const DashboardPage: React.FC = () => {
  const [filters, setFilters] = useState<DashboardFilters>({});
  const { data, isLoading, error, refetch } = useDashboardOverview(filters);

  if (isLoading) return <div>Loading dashboard...</div>;
  if (error) return <div className="error">{error}</div>;
  if (!data) return null;

  return (
    <div className="admin-dashboard">
      <h1>Dashboard</h1>

      <div className="metrics-grid">
        <MetricCard
          title="Organizations"
          total={data.organizations.total}
          details={[
            { label: "Active", value: data.organizations.active },
            { label: "On Trial", value: data.organizations.on_trial },
          ]}
        />
        <MetricCard
          title="Users"
          total={data.users.total}
          details={[{ label: "Active", value: data.users.active }]}
        />
        <RevenueCard revenue={data.revenue} />
      </div>

      <RecentActivityTable activities={data.recent_activity} />
    </div>
  );
};
```

### Metric Card

```typescript
// components/MetricCard.tsx

import React from "react";

interface MetricCardProps {
  title: string;
  total: number;
  details: { label: string; value: number }[];
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  total,
  details,
}) => (
  <div className="metric-card">
    <h3>{title}</h3>
    <div className="metric-total">{total.toLocaleString()}</div>
    <div className="metric-details">
      {details.map((d) => (
        <span key={d.label}>
          {d.label}: {d.value.toLocaleString()}
        </span>
      ))}
    </div>
  </div>
);
```

### Recent Activity Table

```typescript
// components/RecentActivityTable.tsx

import React from "react";
import type { ActivityLogItem } from "../types/adminDashboard.types";

interface Props {
  activities: ActivityLogItem[];
}

export const RecentActivityTable: React.FC<Props> = ({ activities }) => (
  <div className="recent-activity">
    <h3>Recent Activity</h3>
    <table>
      <thead>
        <tr>
          <th>Action</th>
          <th>Resource</th>
          <th>IP Address</th>
          <th>Time</th>
        </tr>
      </thead>
      <tbody>
        {activities.map((a) => (
          <tr key={a.id}>
            <td>{a.action}</td>
            <td>{a.resource_type || "—"}</td>
            <td>{a.ip_address || "—"}</td>
            <td>{new Date(a.created_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
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

- Dashboard is the admin portal landing page — fetch data on mount
- Revenue values are returned as decimal strings — parse with `parseFloat()` for display and formatting
- `recent_activity` returns at most 10 entries sorted by most recent first
- Date range filters only affect revenue and activity sections; org/user counts are always global totals
- Consider auto-refreshing dashboard data every 60 seconds for live monitoring
- `resource_type` and `resource_id` may be null for login/logout events — display "—" or hide the column

---

## 9. Testing Checklist

### Unit Tests

- [ ] `adminDashboardService.getOverview` calls correct URL (`/api/v1/admin/dashboard/overview`)
- [ ] `adminDashboardService.getOverview` appends `date_from` and `date_to` query params when provided
- [ ] `useDashboardOverview` sets `isLoading = true` initially, then `false` after fetch
- [ ] `useDashboardOverview` populates `data` on successful response
- [ ] `useDashboardOverview` sets `error` message on 401/403/500
- [ ] `useDashboardOverview` refetches when filters change
- [ ] `MetricCard` renders title, total, and detail labels correctly
- [ ] `RecentActivityTable` renders all activity rows
- [ ] `RecentActivityTable` handles null `resource_type` and `ip_address` gracefully

### Integration Tests

- [ ] Full flow: load dashboard page → fetch overview → render metrics and activity
- [ ] Date range filter updates revenue and activity sections
- [ ] Non-admin user is redirected (403 handling)
- [ ] Network error shows appropriate error state

### Error Scenario Tests

- [ ] 401 response clears token and redirects to login
- [ ] 403 response shows "Admin access required"
- [ ] Empty activity list renders empty state (no crash)
- [ ] Zero revenue values display correctly

---

## 10. Backend Files Reference

- Schema: `core-service/app/schemas/admin_dashboard.py`
- Repository: `core-service/app/repositories/admin_dashboard_repository.py`
- Service: `core-service/app/services/admin_dashboard_service.py`
- Endpoint: `core-service/app/api/v1/endpoints/admin/dashboard.py`
- Router Registration: `core-service/app/api/v1/endpoints/admin/__init__.py`
- Swagger UI: http://localhost:8001/docs (tag: Admin - Dashboard)
