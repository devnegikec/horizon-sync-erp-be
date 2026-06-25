# Admin Guide: Creating QR Codes for Warehouse Workers

> **Audience**: Frontend Developers (Admin Portal)
> **Date**: 2026-06-19
> **Base URL**: `https://<host>/api/v1`

---

## Table of Contents

1. [Overview](#1-overview)
2. [Quick Reference — API Endpoints](#2-quick-reference--api-endpoints)
3. [Recommended Flow — Identity Admin Panel](#3-recommended-flow--identity-admin-panel)
4. [Alternative Flow — WMS Workers UI](#4-alternative-flow--wms-workers-ui)
5. [Downloading the QR Code Image](#5-downloading-the-qr-code-image)
6. [Displaying the QR Code](#6-displaying-the-qr-code)
7. [UI/UX Recommendations](#7-uiux-recommendations)
8. [Permission Model](#8-permission-model)

---

## 1. Overview

Admins can create warehouse workers who log in **only via QR code** (no email/password). Workers are created directly — no invitation or email verification needed. The flow:

```
Admin creates worker + assigns warehouses → System creates user + warehouse links → Admin downloads QR PNG → Prints it → Worker scans → Worker sees assigned warehouses
```

The worker scans the QR with the mobile app, which sends the QR code string to `POST /identity/login/qr-code` to get JWT tokens. `GET /warehouse-users/my-warehouses` returns only the warehouses explicitly assigned during creation.

---

## 2. Quick Reference — API Endpoints

| Method | Path                                   | Auth               | Purpose                                        |
| ------ | -------------------------------------- | ------------------ | ---------------------------------------------- |
| `POST` | `/identity/admin/create-worker`        | Admin Bearer       | Create warehouse worker + assign warehouses    |
| `GET`  | `/identity/workers/{user_id}/qr-image` | `warehouse.manage` | Download QR code PNG image                     |
| `GET`  | `/warehouses`                          | `warehouse.read`   | List warehouses (for the warehouse picker)     |
| `POST` | `/wms-workers`                         | `warehouse.manage` | Create WMS worker (also creates identity User) |
| `GET`  | `/wms-workers`                         | `warehouse.read`   | List WMS workers (includes barcode)            |

---

## 3. Recommended Flow — Identity Admin Panel

This is the cleanest path. Create the worker directly in the Identity Service.

### Step 1: Create the Worker User

```
POST /identity/admin/create-worker
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request**:

```json
{
  "first_name": "Rajesh",
  "last_name": "Kumar",
  "qr_code": "WRK-A1B2C3D4E5F6",
  "organization_id": "660e8400-e29b-41d4-a716-446655440001",
  "warehouse_ids": [
    "880e8400-e29b-41d4-a716-446655440003",
    "990e8400-e29b-41d4-a716-446655440004"
  ],
  "warehouse_role": "operator"
}
```

| Field             | Type   | Required | Notes                                                        |
| ----------------- | ------ | -------- | ------------------------------------------------------------ |
| `first_name`      | string | **Yes**  |                                                              |
| `last_name`       | string | **Yes**  |                                                              |
| `qr_code`         | string | **Yes**  | Unique QR code string. Generate client-side                  |
| `organization_id` | UUID   | **Yes**  | The org the worker belongs to                                |
| `warehouse_ids`   | UUID[] | **Yes**  | Warehouses to assign. Worker will ONLY see these warehouses. |
| `warehouse_role`  | string | No       | `operator` (default), `supervisor`, `manager`, `coordinator` |
| `email`           | string | No       | Auto-generated as `{qr_code}@warehouse.local` if omitted     |
| `phone`           | string | No       |                                                              |

> ⚠️ **Important**: `warehouse_ids` is required. Without it, the worker will have **zero warehouses** and cannot do any work. This is a list — assign all warehouses the worker operates in.

**Response** `201`:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "WRK-A1B2C3D4E5F6@warehouse.local",
  "first_name": "Rajesh",
  "last_name": "Kumar",
  "display_name": "Rajesh Kumar",
  "phone": "+91-9876543210",
  "user_type": "warehouse_worker",
  "status": "active",
  "is_active": true,
  "qr_code": "WRK-A1B2C3D4E5F6",
  "organization_id": "660e8400-e29b-41d4-a716-446655440001",
  "created_at": "2026-06-19T10:00:00Z",
  "warehouse_assignments": [
    "880e8400-e29b-41d4-a716-446655440003",
    "990e8400-e29b-41d4-a716-446655440004"
  ]
}
```

**Important**: Save the `id` field — you'll need it to download the QR image.

### Generating a QR Code String

Generate client-side before calling the endpoint:

```typescript
// Generate a unique QR code string
function generateQRCode(): string {
  const chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
  let result = "WRK-";
  for (let i = 0; i < 12; i++) {
    result += chars.charAt(Math.floor(Math.random() * chars.length));
  }
  return result;
}
```

### Step 2: Download the QR Code Image

See [Section 5](#5-downloading-the-qr-code-image).

---

## 4. Alternative Flow — WMS Workers UI

If you prefer using the existing WMS Workers management UI:

### Step 1: Create WMS Worker

```
POST /wms-workers
Authorization: Bearer <admin_token>
Content-Type: application/json
```

**Request**:

```json
{
  "warehouse_id": "880e8400-e29b-41d4-a716-446655440003",
  "first_name": "Rajesh",
  "last_name": "Kumar",
  "email": "rajesh.kumar@warehouse.com",
  "login_username": "rajesh.kumar",
  "password": "TempPass123!",
  "employee_id": "EMP-042",
  "role": "warehouse_worker"
}
```

**Response** `201`:

```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "warehouse_id": "880e8400-...",
  "first_name": "Rajesh",
  "last_name": "Kumar",
  "email": "rajesh.kumar@warehouse.com",
  "barcode": "WRK-A1B2C3D4E5F6",
  "role": "warehouse_worker",
  "status": "active",
  ...
}
```

**What happens automatically**:

- An Identity Service `User` is created with the same `qr_code` = `barcode`
- The `warehouse_work_user` role is assigned
- The user gets `user_type=warehouse_worker`

### Step 2: Find the Identity User ID

To download the QR image, you need the Identity Service user ID. Since the WMS worker and identity User share the same barcode/qr_code, you can look up the identity User:

```
GET /identity/users?search=<barcode>&user_type=warehouse_worker
Authorization: Bearer <admin_token>
```

Or use the barcode to find the matching identity user from the users list. The identity User will have the same email and `qr_code` matching the WMS worker's `barcode`.

---

## 5. Downloading the QR Code Image

Once you have the Identity Service `user_id`, download the QR PNG:

```
GET /identity/workers/{user_id}/qr-image
Authorization: Bearer <admin_token>
```

**Returns**: `image/png` — a 330×330px (approx) QR code PNG image.

### Fetch Example (Frontend)

```typescript
async function downloadWorkerQR(userId: string): Promise<Blob> {
  const response = await fetch(`/api/v1/identity/workers/${userId}/qr-image`, {
    headers: {
      Authorization: `Bearer ${getAdminToken()}`,
    },
  });

  if (!response.ok) {
    throw new Error("Failed to download QR code");
  }

  return response.blob();
}
```

### Display as Image

```tsx
// React component
function WorkerQRCode({ userId }: { userId: string }) {
  const qrUrl = `/api/v1/identity/workers/${userId}/qr-image`;

  return (
    <div>
      <img
        src={qrUrl}
        alt="Worker QR Code"
        style={{ width: 250, height: 250 }}
        // Include auth header via a service worker or proxy, or:
        // use a pre-signed approach where the token is in the URL
      />
      <button onClick={() => printQR(qrUrl)}>Print QR Code</button>
      <button onClick={() => downloadQR(qrUrl)}>Download PNG</button>
    </div>
  );
}
```

> **Note**: Since the `<img>` tag can't send `Authorization` headers, use one of:
>
> 1. A backend proxy that forwards the request with the token
> 2. Fetch the blob client-side with auth, then create an object URL:
>    ```typescript
>    const blob = await downloadWorkerQR(userId);
>    const url = URL.createObjectURL(blob);
>    setQrSrc(url);
>    ```

### Print-Friendly Format

The QR image is designed for printing. Recommended print size: **5cm × 5cm (≈2in × 2in)** on a label printer or standard A4.

---

## 6. Displaying the QR Code

### Complete React Component Example

```tsx
import { useState, useEffect } from "react";

interface WorkerQRProps {
  userId: string;
  workerName: string;
}

export function WorkerQRCard({ userId, workerName }: WorkerQRProps) {
  const [qrBlobUrl, setQrBlobUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getAdminToken(); // from your auth store
    fetch(`/api/v1/identity/workers/${userId}/qr-image`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load QR");
        return res.blob();
      })
      .then((blob) => {
        setQrBlobUrl(URL.createObjectURL(blob));
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });

    return () => {
      if (qrBlobUrl) URL.revokeObjectURL(qrBlobUrl);
    };
  }, [userId]);

  if (loading) return <Spinner />;
  if (error) return <ErrorBanner message={error} />;

  return (
    <div className="qr-card">
      <img src={qrBlobUrl} alt={`QR for ${workerName}`} />
      <p className="worker-name">{workerName}</p>
      <div className="actions">
        <button onClick={() => window.print()}>🖨 Print</button>
        <button
          onClick={() => downloadBlob(qrBlobUrl!, `${workerName}-qr.png`)}
        >
          ⬇ Download
        </button>
      </div>
    </div>
  );
}
```

---

## 7. UI/UX Recommendations

### Worker Creation Flow

```
┌──────────────────────────────────────────────────────────┐
│  Create Warehouse Worker                                  │
│                                                           │
│  Name:     [ Rajesh       ] [ Kumar         ]             │
│  QR Code:  [ WRK-A1B2C3D4E5F6 ] [ 🔄 Generate ]          │
│  Phone:    [ +91-9876543210 ]               (optional)    │
│  Email:    [                         ]     (optional)     │
│  Org:      [ Default Organization ▼ ]                     │
│                                                           │
│  Warehouses:  ┌──────────────────────────────────┐        │
│               │ ☑ Main Warehouse (WH-001)        │        │
│               │ ☑ North Depot (WH-002)           │        │
│               │ ☐ South Depot (WH-003)           │        │
│               │ ☐ Returns Center (WH-004)        │        │
│               └──────────────────────────────────┘        │
│                                                           │
│  Warehouse Role:  [ operator ▼ ]                          │
│                                                           │
│  ┌──────────────────────────────────────────────────┐    │
│  │  Role: Warehouse Work User                        │    │
│  │  • QR login only (no password needed)             │    │
│  │  • Can scan, receive, pick (limited access)       │    │
│  │  • Will see only selected warehouses above         │    │
│  └──────────────────────────────────────────────────┘    │
│                                                           │
│  [ Cancel ]              [ Create & Generate QR ]         │
└──────────────────────────────────────────────────────────┘
```

> 💡 **Warehouse picker**: Fetch the warehouse list from `GET /warehouses` (requires `warehouse.read` permission). Use a multi-select checkbox list. At least one warehouse must be selected.

### After Creation — QR Code Modal

```
┌──────────────────────────────────────────────────┐
│  ✅ Worker Created                                │
│                                                   │
│     ┌─────────────────┐                           │
│     │                 │                           │
│     │   ██████████    │                           │
│     │   ██ ██ ████    │  ← QR Code PNG           │
│     │   ██████████    │                           │
│     │                 │                           │
│     └─────────────────┘                           │
│                                                   │
│  Rajesh Kumar                                      │
│  QR: WRK-A1B2C3D4E5F6                              │
│  Assigned Warehouses:                              │
│    🏭 Main Warehouse (operator)                    │
│    🏭 North Depot (operator)                       │
│                                                   │
│  [ 🖨 Print ]  [ ⬇ Download ]  [ ✕ Close ]        │
└──────────────────────────────────────────────────┘
```

### Worker List — QR Icon

In the users/workers list, show a QR icon next to `warehouse_worker` type users. Clicking it opens the QR modal:

```
┌────────────────────────────────────────────────────────────────────┐
│  Name          │ QR Code          │ Warehouses      │ QR          │
│────────────────────────────────────────────────────────────────────│
│  Rajesh Kumar  │ WRK-A1B2C3D4E5   │ WH-001, WH-002  │ 📱          │
│  Priya Sharma  │ WRK-F6G7H8I9J0   │ WH-003          │ 📱          │
└────────────────────────────────────────────────────────────────────┘
```

### Error States

| Scenario                   | What to Show                                                                   |
| -------------------------- | ------------------------------------------------------------------------------ |
| QR endpoint fails (404)    | "Worker not found. They may not have a QR code yet."                           |
| QR endpoint fails (403)    | "You don't have permission. Need warehouse.manage."                            |
| QR endpoint fails (5xx)    | "Server error. Try again later."                                               |
| Email already exists       | "A user with this email already exists." (only if email was provided)          |
| QR code already in use     | "This QR code is already assigned. Try generating a new one."                  |
| No warehouses selected     | "Select at least one warehouse. Workers need warehouse access."                |
| Warehouse assignment fails | "Worker created but warehouse assignment failed for: WH-003. Assign manually." |

---

## 8. Permission Model

### Role: `warehouse_work_user`

Assigned automatically on worker creation. Grants 7 permissions:

| Permission              | Allows                                          |
| ----------------------- | ----------------------------------------------- |
| `warehouse.read`        | View warehouse info + call `GET /my-warehouses` |
| `wms.scan`              | QR/barcode scanning (inbound + outbound)        |
| `receiving_slip.create` | Create inbound receiving slips                  |
| `receiving_slip.read`   | View receiving slips                            |
| `receiving_slip.update` | Update receiving slip status/quantities         |
| `pick_list.read`        | View outbound pick lists                        |
| `pick_list.update`      | Update pick list status (start/finish picking)  |

### Warehouse Access (NEW)

When `warehouse_ids` is provided, a `WarehouseUser` record is created in core-service for each warehouse. This controls **which warehouses the worker sees**:

- `GET /warehouse-users/my-warehouses` returns ONLY warehouses in `warehouse_ids`
- The `warehouse_role` field sets the operational role: `operator`, `supervisor`, `manager`, `coordinator`
- Without warehouse assignments, the worker sees an empty list and cannot operate

**Workers CANNOT**:

- Create pick lists
- Delete anything
- Access admin, billing, or reporting
- Manage other workers or devices
- See warehouses they are not assigned to

---

## Summary Checklist for Frontend

- [ ] Add "Create Warehouse Worker" form (email, name, phone, org)
- [ ] Auto-generate QR code string client-side (`WRK-{12 random chars}`)
- [ ] Call `POST /identity/admin/create-worker` (requires admin Bearer token)
- [ ] Store the returned `user.id`
- [ ] Call `GET /identity/workers/{user_id}/qr-image` to fetch QR PNG
- [ ] Display QR in a modal with Print/Download buttons
- [ ] Add QR icon to user/worker list for warehouse_worker users
- [ ] Handle duplicate email (409) and duplicate QR code (409) errors
