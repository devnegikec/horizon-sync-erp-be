---
inclusion: manual
---

# Frontend QR Product Settings Module - Integration Guide

Complete API reference for building the QR Product Settings UI. This module lets each organization define allowed lookup values for Serial Prefix, Channel, Destination, and Shelf Life — used as dropdown options during QR product and block creation.

## Base URL & Auth

```
Base: http://localhost:8001/api/v1
Auth: Authorization: Bearer {token}
```

All endpoints require a valid Bearer token. Token is stored in `localStorage.getItem("token")`.

---

## Architecture

A single `qr_product_settings` table stores all four setting types, discriminated by `setting_type`:

| setting_type    | Purpose                                 | Example value | Example label |
| --------------- | --------------------------------------- | ------------- | ------------- |
| `serial_prefix` | Allowed serial prefixes for QR blocks   | `PH`          | `Pharma (PH)` |
| `channel`       | Distribution channels                   | `retail`      | `Retail`      |
| `destination`   | Target markets for product distribution | `IN`          | `India`       |
| `shelf_life`    | Shelf life options (value = months)     | `12`          | `12 Months`   |

Each setting is scoped per organization. The `value` field is the stored key, `label` is the display name shown in dropdowns.

---

## 1. QR Product Settings API

### Create Setting

```
POST /qr-product-settings
```

```json
{
  "setting_type": "serial_prefix",
  "value": "PH",
  "label": "Pharma (PH)",
  "description": "Pharmaceutical products",
  "sort_order": 1,
  "is_active": true,
  "extra_data": null
}
```

Required fields: `setting_type`, `value`, `label`

`setting_type` must be one of: `serial_prefix` | `channel` | `destination` | `shelf_life`

Response: `QRProductSettingResponse` (201)

```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "setting_type": "serial_prefix",
  "value": "PH",
  "label": "Pharma (PH)",
  "description": "Pharmaceutical products",
  "sort_order": 1,
  "is_active": true,
  "extra_data": null,
  "created_at": "2026-03-21T10:00:00Z",
  "updated_at": "2026-03-21T10:00:00Z"
}
```

### List Settings

```
GET /qr-product-settings?setting_type=serial_prefix&is_active=true&search=pharma&page=1&page_size=50
```

All query params are optional. Use `setting_type` to fetch options for a specific dropdown.

Response:

```json
{
  "settings": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "setting_type": "serial_prefix",
      "value": "PH",
      "label": "Pharma (PH)",
      "description": "Pharmaceutical products",
      "sort_order": 1,
      "is_active": true,
      "extra_data": null,
      "created_at": "2026-03-21T10:00:00Z",
      "updated_at": "2026-03-21T10:00:00Z"
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 50,
    "total_items": 5,
    "total_pages": 1,
    "has_next": false,
    "has_prev": false
  }
}
```

Results are ordered by `setting_type` then `sort_order`.

### Get Setting

```
GET /qr-product-settings/{setting_id}
```

Response: `QRProductSettingResponse` (200)

### Update Setting

```
PATCH /qr-product-settings/{setting_id}
```

```json
{
  "label": "Pharma Prefix (PH)",
  "sort_order": 2,
  "is_active": false
}
```

All fields optional. Note: `setting_type` cannot be changed after creation.

Response: `QRProductSettingResponse` (200)

### Delete Setting (soft delete)

```
DELETE /qr-product-settings/{setting_id}
```

Returns 204. Record is soft-deleted (not permanently removed).

### Error Codes

| Scenario                      | Status | Detail                                                                                 |
| ----------------------------- | ------ | -------------------------------------------------------------------------------------- |
| Duplicate value for same type | 409    | `"Setting 'serial_prefix' with value 'PH' already exists for this organization."`      |
| Duplicate value on update     | 409    | `"Setting 'serial_prefix' with value 'PH' already exists."`                            |
| Not found / wrong org         | 404    | `"QR product setting not found."`                                                      |
| Invalid setting_type          | 422    | Pydantic validation error (must be serial_prefix, channel, destination, or shelf_life) |
| value exceeds 100 chars       | 422    | Pydantic validation error                                                              |
| label exceeds 150 chars       | 422    | Pydantic validation error                                                              |

### Permissions

All endpoints use `qr_product.*` permissions:

| Action | Permission Required |
| ------ | ------------------- |
| Create | `qr_product.create` |
| List   | `qr_product.read`   |
| Get    | `qr_product.read`   |
| Update | `qr_product.update` |
| Delete | `qr_product.delete` |

---

## 2. TypeScript Types

```typescript
// qrProductSettings.types.ts

export type SettingType =
  | "serial_prefix"
  | "channel"
  | "destination"
  | "shelf_life";

export interface QRProductSetting {
  id: string;
  organization_id: string;
  setting_type: SettingType;
  value: string;
  label: string;
  description: string | null;
  sort_order: number;
  is_active: boolean;
  extra_data: Record<string, any> | null;
  created_at: string;
  updated_at: string;
}

export interface QRProductSettingCreate {
  setting_type: SettingType;
  value: string;
  label: string;
  description?: string | null;
  sort_order?: number;
  is_active?: boolean;
  extra_data?: Record<string, any> | null;
}

export interface QRProductSettingUpdate {
  value?: string;
  label?: string;
  description?: string | null;
  sort_order?: number;
  is_active?: boolean;
  extra_data?: Record<string, any> | null;
}

export interface QRProductSettingListResponse {
  settings: QRProductSetting[];
  pagination: PaginationMeta;
}

export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

// Helper type for dropdown options built from settings
export interface SettingOption {
  value: string;
  label: string;
  description?: string | null;
}
```

---

## 3. Frontend Service Layer

```typescript
// services/qrProductSettingService.ts

import apiClient from "./apiClient";
import type {
  QRProductSetting,
  QRProductSettingCreate,
  QRProductSettingUpdate,
  QRProductSettingListResponse,
  SettingType,
} from "../types/qrProductSettings.types";

export const qrProductSettingService = {
  create: (data: QRProductSettingCreate) =>
    apiClient.post<QRProductSetting>("/qr-product-settings", data),

  list: (params?: {
    setting_type?: SettingType;
    is_active?: boolean;
    search?: string;
    page?: number;
    page_size?: number;
  }) =>
    apiClient.get<QRProductSettingListResponse>("/qr-product-settings", {
      params,
    }),

  getById: (id: string) =>
    apiClient.get<QRProductSetting>(`/qr-product-settings/${id}`),

  update: (id: string, data: QRProductSettingUpdate) =>
    apiClient.patch<QRProductSetting>(`/qr-product-settings/${id}`, data),

  delete: (id: string) => apiClient.delete(`/qr-product-settings/${id}`),
};
```

---

## 4. React Hooks

### useQRProductSettings — Fetch settings by type

```typescript
// hooks/useQRProductSettings.ts

import { useState, useEffect, useCallback } from "react";
import { qrProductSettingService } from "../services/qrProductSettingService";
import type {
  QRProductSettingListResponse,
  SettingType,
} from "../types/qrProductSettings.types";

export const useQRProductSettings = (settingType?: SettingType) => {
  const [data, setData] = useState<QRProductSettingListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = useCallback(
    async (page = 1) => {
      setLoading(true);
      setError(null);
      try {
        const result = await qrProductSettingService.list({
          setting_type: settingType,
          is_active: true,
          page,
          page_size: 100,
        });
        setData(result.data);
      } catch (err: any) {
        setError(
          err.response?.data?.detail || "Failed to fetch product settings",
        );
      } finally {
        setLoading(false);
      }
    },
    [settingType],
  );

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  return { data, loading, error, refetch: fetchSettings };
};
```

### useCreateQRProductSetting — Create a new setting

```typescript
// hooks/useCreateQRProductSetting.ts

import { useState } from "react";
import { qrProductSettingService } from "../services/qrProductSettingService";
import type {
  QRProductSettingCreate,
  QRProductSetting,
} from "../types/qrProductSettings.types";

export const useCreateQRProductSetting = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const createSetting = async (
    data: QRProductSettingCreate,
  ): Promise<QRProductSetting> => {
    setLoading(true);
    setError(null);
    try {
      const result = await qrProductSettingService.create(data);
      return result.data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to create setting";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { createSetting, loading, error };
};
```

### useUpdateQRProductSetting — Update an existing setting

```typescript
// hooks/useUpdateQRProductSetting.ts

import { useState } from "react";
import { qrProductSettingService } from "../services/qrProductSettingService";
import type {
  QRProductSettingUpdate,
  QRProductSetting,
} from "../types/qrProductSettings.types";

export const useUpdateQRProductSetting = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateSetting = async (
    id: string,
    data: QRProductSettingUpdate,
  ): Promise<QRProductSetting> => {
    setLoading(true);
    setError(null);
    try {
      const result = await qrProductSettingService.update(id, data);
      return result.data;
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to update setting";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { updateSetting, loading, error };
};
```

### useDeleteQRProductSetting — Delete a setting

```typescript
// hooks/useDeleteQRProductSetting.ts

import { useState } from "react";
import { qrProductSettingService } from "../services/qrProductSettingService";

export const useDeleteQRProductSetting = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const deleteSetting = async (id: string): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      await qrProductSettingService.delete(id);
    } catch (err: any) {
      const message = err.response?.data?.detail || "Failed to delete setting";
      setError(message);
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return { deleteSetting, loading, error };
};
```

---

## 5. Module Structure

```
src/
├── features/
│   └── qr-product-settings/
│       ├── components/
│       │   ├── QRProductSettingsPage.tsx       # Main settings page with tabs per type
│       │   ├── SettingTypeTab.tsx              # Tab content: list + add for one type
│       │   ├── SettingForm.tsx                 # Create/edit form (modal or inline)
│       │   ├── SettingList.tsx                 # Table of settings for one type
│       │   └── SettingDropdown.tsx             # Reusable dropdown for product forms
│       ├── hooks/
│       │   ├── useQRProductSettings.ts
│       │   ├── useCreateQRProductSetting.ts
│       │   ├── useUpdateQRProductSetting.ts
│       │   └── useDeleteQRProductSetting.ts
│       ├── services/
│       │   └── qrProductSettingService.ts
│       └── types/
│           └── qrProductSettings.types.ts
```

---

## 6. Component Examples

### Settings Page with Tabs

```typescript
// components/QRProductSettingsPage.tsx

import React, { useState } from "react";
import { SettingTypeTab } from "./SettingTypeTab";
import type { SettingType } from "../types/qrProductSettings.types";

const SETTING_TABS: { key: SettingType; label: string }[] = [
  { key: "serial_prefix", label: "Serial Prefixes" },
  { key: "channel", label: "Channels" },
  { key: "destination", label: "Destinations" },
  { key: "shelf_life", label: "Shelf Life" },
];

export const QRProductSettingsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<SettingType>("serial_prefix");

  return (
    <div className="qr-product-settings-page">
      <h2>QR Product Settings</h2>
      <p>
        Configure the allowed options for serial prefixes, channels,
        destinations, and shelf life. These appear as dropdown choices when
        creating QR products and blocks.
      </p>

      <div className="tabs">
        {SETTING_TABS.map((tab) => (
          <button
            key={tab.key}
            className={`tab ${activeTab === tab.key ? "active" : ""}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <SettingTypeTab settingType={activeTab} />
    </div>
  );
};
```

### Setting Type Tab (list + add)

```typescript
// components/SettingTypeTab.tsx

import React, { useState } from "react";
import { useQRProductSettings } from "../hooks/useQRProductSettings";
import { useCreateQRProductSetting } from "../hooks/useCreateQRProductSetting";
import { useDeleteQRProductSetting } from "../hooks/useDeleteQRProductSetting";
import { SettingForm } from "./SettingForm";
import type { SettingType } from "../types/qrProductSettings.types";

interface SettingTypeTabProps {
  settingType: SettingType;
}

const TYPE_LABELS: Record<SettingType, { singular: string; valuePlaceholder: string; labelPlaceholder: string }> = {
  serial_prefix: { singular: "Serial Prefix", valuePlaceholder: "e.g. PH", labelPlaceholder: "e.g. Pharma (PH)" },
  channel: { singular: "Channel", valuePlaceholder: "e.g. retail", labelPlaceholder: "e.g. Retail" },
  destination: { singular: "Destination", valuePlaceholder: "e.g. IN", labelPlaceholder: "e.g. India" },
  shelf_life: { singular: "Shelf Life", valuePlaceholder: "e.g. 12", labelPlaceholder: "e.g. 12 Months" },
};

export const SettingTypeTab: React.FC<SettingTypeTabProps> = ({ settingType }) => {
  const { data, loading, error, refetch } = useQRProductSettings(settingType);
  const { createSetting, loading: creating, error: createError } = useCreateQRProductSetting();
  const { deleteSetting, loading: deleting } = useDeleteQRProductSetting();
  const [showForm, setShowForm] = useState(false);

  const meta = TYPE_LABELS[settingType];

  const handleCreate = async (formData: { value: string; label: string; description: string; sort_order: number }) => {
    await createSetting({
      setting_type: settingType,
      ...formData,
    });
    setShowForm(false);
    refetch();
  };

  const handleDelete = async (id: string) => {
    if (!confirm(`Delete this ${meta.singular.toLowerCase()}?`)) return;
    await deleteSetting(id);
    refetch();
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div className="error-message">{error}</div>;

  return (
    <div className="setting-type-tab">
      <div className="tab-header">
        <h3>{meta.singular} Options</h3>
        <button className="btn-primary" onClick={() => setShowForm(true)}>
          + Add {meta.singular}
        </button>
      </div>

      {showForm && (
        <SettingForm
          valuePlaceholder={meta.valuePlaceholder}
          labelPlaceholder={meta.labelPlaceholder}
          onSubmit={handleCreate}
          onCancel={() => setShowForm(false)}
          loading={creating}
          error={createError}
        />
      )}

      <table>
        <thead>
          <tr>
            <th>Value</th>
            <th>Label</th>
            <th>Description</th>
            <th>Order</th>
            <th>Active</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {data?.settings.map((setting) => (
            <tr key={setting.id}>
              <td><code>{setting.value}</code></td>
              <td>{setting.label}</td>
              <td>{setting.description || "—"}</td>
              <td>{setting.sort_order}</td>
              <td>{setting.is_active ? "✓" : "✗"}</td>
              <td>
                <button onClick={() => {/* open edit modal */}}>Edit</button>
                <button
                  onClick={() => handleDelete(setting.id)}
                  disabled={deleting}
                  className="btn-danger"
                >
                  Delete
                </button>
              </td>
            </tr>
          ))}
          {data?.settings.length === 0 && (
            <tr>
              <td colSpan={6} style={{ textAlign: "center" }}>
                No {meta.singular.toLowerCase()} options configured yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
};
```

### Setting Form (create/edit)

```typescript
// components/SettingForm.tsx

import React, { useState } from "react";

interface SettingFormProps {
  valuePlaceholder: string;
  labelPlaceholder: string;
  initialValue?: string;
  initialLabel?: string;
  initialDescription?: string;
  initialSortOrder?: number;
  onSubmit: (data: { value: string; label: string; description: string; sort_order: number }) => Promise<void>;
  onCancel: () => void;
  loading: boolean;
  error: string | null;
}

export const SettingForm: React.FC<SettingFormProps> = ({
  valuePlaceholder,
  labelPlaceholder,
  initialValue = "",
  initialLabel = "",
  initialDescription = "",
  initialSortOrder = 0,
  onSubmit,
  onCancel,
  loading,
  error,
}) => {
  const [value, setValue] = useState(initialValue);
  const [label, setLabel] = useState(initialLabel);
  const [description, setDescription] = useState(initialDescription);
  const [sortOrder, setSortOrder] = useState(initialSortOrder);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    await onSubmit({ value, label, description, sort_order: sortOrder });
  };

  return (
    <form onSubmit={handleSubmit} className="setting-form">
      <div className="form-row">
        <div className="form-group">
          <label>Value *</label>
          <input
            type="text"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            placeholder={valuePlaceholder}
            maxLength={100}
            required
          />
        </div>
        <div className="form-group">
          <label>Label *</label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder={labelPlaceholder}
            maxLength={150}
            required
          />
        </div>
        <div className="form-group">
          <label>Sort Order</label>
          <input
            type="number"
            value={sortOrder}
            onChange={(e) => setSortOrder(Number(e.target.value))}
            min={0}
          />
        </div>
      </div>
      <div className="form-group">
        <label>Description</label>
        <input
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="Optional description"
        />
      </div>
      {error && <div className="error-message">{error}</div>}
      <div className="form-actions">
        <button type="button" onClick={onCancel} disabled={loading}>Cancel</button>
        <button type="submit" disabled={loading} className="btn-primary">
          {loading ? "Saving..." : "Save"}
        </button>
      </div>
    </form>
  );
};
```

### Reusable Dropdown for Product Forms

```typescript
// components/SettingDropdown.tsx

import React from "react";
import { useQRProductSettings } from "../hooks/useQRProductSettings";
import type { SettingType } from "../types/qrProductSettings.types";

interface SettingDropdownProps {
  settingType: SettingType;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
}

export const SettingDropdown: React.FC<SettingDropdownProps> = ({
  settingType,
  value,
  onChange,
  placeholder = "-- Select --",
  required = false,
  disabled = false,
}) => {
  const { data, loading, error } = useQRProductSettings(settingType);

  if (loading) return <select disabled><option>Loading...</option></select>;
  if (error) return <select disabled><option>Error loading options</option></select>;

  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      required={required}
      disabled={disabled}
    >
      <option value="">{placeholder}</option>
      {data?.settings.map((setting) => (
        <option key={setting.id} value={setting.value}>
          {setting.label}
        </option>
      ))}
    </select>
  );
};
```

---

## 7. Integration with QR Product / Block Forms

### Product Creation Form — using setting dropdowns

When creating a QR product, use `SettingDropdown` for the configurable fields:

```typescript
import { SettingDropdown } from "../qr-product-settings/components/SettingDropdown";

// Inside QR Product form:
<div className="form-group">
  <label>Serial Prefix</label>
  <SettingDropdown
    settingType="serial_prefix"
    value={serialPrefix}
    onChange={setSerialPrefix}
    placeholder="-- Select Serial Prefix --"
  />
</div>

<div className="form-group">
  <label>Channel</label>
  <SettingDropdown
    settingType="channel"
    value={channel}
    onChange={setChannel}
    placeholder="-- Select Channel --"
  />
</div>

<div className="form-group">
  <label>Destination</label>
  <SettingDropdown
    settingType="destination"
    value={destination}
    onChange={setDestination}
    placeholder="-- Select Destination --"
  />
</div>

<div className="form-group">
  <label>Shelf Life</label>
  <SettingDropdown
    settingType="shelf_life"
    value={shelfLife}
    onChange={setShelfLife}
    placeholder="-- Select Shelf Life --"
  />
</div>
```

### Storing selected values

The selected `value` from each dropdown can be stored in the product's `extra_data` JSONB field:

```typescript
const productData = {
  name: productName,
  // ... other fields
  extra_data: {
    serial_prefix: serialPrefix, // "PH"
    channel: channel, // "retail"
    destination: destination, // "IN"
    shelf_life_months: shelfLife, // "12"
  },
};
```

Or for QR blocks, `serial_prefix` maps directly to the `serial_prefix` column, and others go into `extra_data`:

```typescript
const blockData = {
  batch: batchName,
  quantity: qty,
  serial_prefix: serialPrefix, // direct column on qr_blocks
  extra_data: {
    channel: channel,
    destination: destination,
    shelf_life_months: shelfLife,
  },
};
```

---

## 8. Shelf Life — Special Handling

For `shelf_life` settings, the `value` stores months as a string (e.g. `"12"`). The `extra_data` field on the setting can store structured data:

```json
{
  "setting_type": "shelf_life",
  "value": "12",
  "label": "12 Months",
  "extra_data": { "months": 12 }
}
```

When a user selects a shelf life, you can compute the expiry date from the manufacture date:

```typescript
const computeExpiryDate = (
  manufactureDate: string,
  shelfLifeMonths: string,
): string => {
  const date = new Date(manufactureDate);
  date.setMonth(date.getMonth() + parseInt(shelfLifeMonths, 10));
  return date.toISOString().split("T")[0];
};

// Usage in block creation:
const expiryDate = computeExpiryDate(manufactureDate, selectedShelfLife);
```

---

## 9. Navigation & Routing

Add a route for the settings page under the QR Products section:

```typescript
// In your router config:
{
  path: "/qr-products/settings",
  element: <QRProductSettingsPage />,
}
```

Add a link from the QR Products list page:

```typescript
<a href="/qr-products/settings">⚙ Product Settings</a>
```

---

## 10. UI Behavior Notes

- `value` max 100 chars, `label` max 150 chars — enforce in form inputs
- `setting_type` is set on creation and cannot be changed — hide it in edit forms
- `sort_order` controls display order in dropdowns — default 0, lower numbers appear first
- `is_active = false` settings are hidden from dropdowns but still visible in the settings management page
- Duplicate `value` within the same `setting_type` and organization is rejected with 409
- Soft delete — deleted settings disappear from lists but data is preserved
- The settings page should show all settings (active + inactive) for management; dropdowns should only show `is_active = true`
- For shelf_life, consider showing the computed expiry date preview next to the dropdown when a manufacture date is also selected

---

## 11. Error Handling

All errors return:

```json
{ "detail": "Human-readable error message" }
```

Extract error message:

```typescript
catch (err: any) {
  const message = err.response?.data?.detail || "An error occurred";
}
```

Common status codes: `404` (not found), `409` (duplicate value), `422` (validation error).

---

## 12. Seed Data Reference

The backend ships with sample seed data for testing. After running the migration and seed script, you'll have:

| Type          | Count | Example values                                 |
| ------------- | ----- | ---------------------------------------------- |
| serial_prefix | 5     | PH, RC, EB, TX, AU                             |
| channel       | 5     | retail, wholesale, online, distributor, export |
| destination   | 5     | IN, UAE, US, EU, SEA                           |
| shelf_life    | 5     | 3, 6, 12, 24, 36 (months)                      |

Seed script: `core-service/scripts/seed_qr_product_settings.sql`

---

## 13. Backend Files Reference

- Model: `core-service/app/models/qr_product_setting.py`
- Schema: `core-service/app/schemas/qr_product_setting.py`
- Repository: `core-service/app/repositories/qr_product_setting_repository.py`
- Service: `core-service/app/services/qr_product_setting_service.py`
- Endpoint: `core-service/app/api/v1/endpoints/qr_product_settings.py`
- Migration: `core-service/alembic/versions/033_add_qr_product_settings.py`
- Swagger UI: http://localhost:8001/docs (tag: QR Product Settings)
