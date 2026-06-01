# Frontend WMS — Multi-UOM Packaging Units Module

## Overview

This steering file documents all **breaking changes and new capabilities** introduced by the WMS Multi-UOM Packaging Units backend feature. The frontend must be updated to:

1. **Manage Packaging Units** — New CRUD UI for defining packaging units per item (Each, Box of 12, Pallet of 144) with physical dimensions and a QR identifier
2. **Update QR Scan Payload** — The inbound scan QR payload now accepts an optional `packaging_unit_qr_id` field
3. **Handle Renamed Field** — `ScanResult.quantity` is now `ScanResult.raw_quantity` (breaking rename)
4. **Display Converted Quantities** — Receiving slip quantities are now in Eaches (converted at approval time); the scan session summary still shows raw scanned quantities
5. **Warehouse Location Capacity** — Bin locations now have optional `max_volume_cc` and `max_weight_grams` fields for volumetric capacity management
6. **Item SKU Field** — Items now have an optional `sku` field separate from `item_code`

---

## Breaking Changes (Must Fix)

### 1. `ScanResult.quantity` → `ScanResult.raw_quantity`

The scan result response from `POST /inbound/sessions/{id}/scan` has renamed `quantity` to `raw_quantity`.

**Before:**

```typescript
interface ScanResult {
  scan_item_id: string;
  session_id: string;
  qr_identifier: string;
  sku: string;
  quantity: number; // ← OLD
  batch_number: string;
  scanned_at: string | null;
  total_boxes_scanned: number;
}
```

**After:**

```typescript
interface ScanResult {
  scan_item_id: string;
  session_id: string;
  qr_identifier: string;
  sku: string;
  raw_quantity: number; // ← RENAMED
  batch_number: string;
  packaging_unit_id: string | null; // ← NEW
  scanned_at: string | null;
  total_boxes_scanned: number;
}
```

**Action:** Find every place in the frontend that reads `result.quantity` from a scan result and rename it to `result.raw_quantity`. Also update the `ScanResult` TypeScript type.

---

### 2. QR Payload Format — new optional field

The QR payload JSON that dock workers scan now supports an optional `packaging_unit_qr_id` field. The `qrPayloadParser.ts` utility and any QR generation logic must be updated.

**Before:**

```typescript
export interface QRPayload {
  id: string;
  sku: string;
  qty: number;
  batch: string;
}
```

**After:**

```typescript
export interface QRPayload {
  id: string;
  sku: string;
  qty: number;
  batch: string;
  packaging_unit_qr_id?: string; // ← NEW (optional)
}
```

**Action:** Update `parseQRPayload` / `isValidQRPayload` utilities to pass through `packaging_unit_qr_id` when present. The field is optional — existing QR codes without it continue to work.

---

### 3. `WarehouseLocation` type — two new fields

```typescript
interface WarehouseLocation {
  // ... existing fields ...
  max_volume_cc: number | null; // ← NEW — max storage volume in cc
  max_weight_grams: number | null; // ← NEW — max storage weight in grams
}
```

**Action:** Update the `WarehouseLocation` TypeScript interface. These fields are nullable — a null value means the bin has no capacity limit for that dimension.

---

### 4. `Item` type — new `sku` field

```typescript
interface Item {
  // ... existing fields ...
  sku: string | null; // ← NEW — warehouse-facing SKU, distinct from item_code
}
```

**Action:** Update the `Item` TypeScript interface. Display `sku` in item detail views and item picker components. `item_code` remains the ERP-internal reference; `sku` is the warehouse-facing identifier used in scanning.

---

## New API Endpoints

### Base URL

```
http://localhost:8001/api/v1
```

### Packaging Units CRUD

| Method   | Path                                    | Description                            |
| -------- | --------------------------------------- | -------------------------------------- |
| `GET`    | `/items/{item_id}/packaging-units`      | List packaging units for an item       |
| `POST`   | `/items/{item_id}/packaging-units`      | Create a packaging unit                |
| `PATCH`  | `/items/{item_id}/packaging-units/{id}` | Partial update                         |
| `DELETE` | `/items/{item_id}/packaging-units/{id}` | Soft-delete (sets `is_active = false`) |

All endpoints require `Authorization: Bearer {token}`.

---

## TypeScript Types

```typescript
// types/wms.types.ts — add these

export interface ItemPackagingUnit {
  id: string;
  organization_id: string;
  item_id: string;
  unit_name: string; // e.g. "Box of 12", "Pallet of 144"
  qr_identifier: string | null; // unique QR code printed on the packaging
  conversion_factor: number; // how many Eaches this unit contains (must be > 0)
  length_mm: number | null; // physical dimension in mm
  width_mm: number | null;
  height_mm: number | null;
  weight_grams: number | null; // weight of one unit in grams
  is_base_unit: boolean; // true = this is the Each (base unit)
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface ItemPackagingUnitCreate {
  unit_name: string; // required, max 100 chars
  qr_identifier?: string | null; // optional, max 255 chars, must be unique
  conversion_factor: number; // required, must be > 0
  length_mm?: number | null;
  width_mm?: number | null;
  height_mm?: number | null;
  weight_grams?: number | null;
  is_base_unit?: boolean; // default false
  is_active?: boolean; // default true
}

export interface ItemPackagingUnitUpdate {
  unit_name?: string;
  qr_identifier?: string | null;
  conversion_factor?: number; // must be > 0 if provided
  length_mm?: number | null;
  width_mm?: number | null;
  height_mm?: number | null;
  weight_grams?: number | null;
  is_base_unit?: boolean;
  is_active?: boolean;
}

export interface ItemPackagingUnitListResponse {
  packaging_units: ItemPackagingUnit[];
  pagination: Pagination;
}
```

---

## API Service

```typescript
// services/itemPackagingUnitService.ts

import axios from "axios";
import type {
  ItemPackagingUnit,
  ItemPackagingUnitCreate,
  ItemPackagingUnitUpdate,
  ItemPackagingUnitListResponse,
} from "../types/wms.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class ItemPackagingUnitService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async list(
    itemId: string,
    params?: { page?: number; page_size?: number; is_active?: boolean },
  ): Promise<ItemPackagingUnitListResponse> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/items/${itemId}/packaging-units`,
      { headers: this.getHeaders(), params },
    );
    return res.data;
  }

  async create(
    itemId: string,
    data: ItemPackagingUnitCreate,
  ): Promise<ItemPackagingUnit> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/items/${itemId}/packaging-units`,
      data,
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async update(
    itemId: string,
    unitId: string,
    data: ItemPackagingUnitUpdate,
  ): Promise<ItemPackagingUnit> {
    const res = await axios.patch(
      `${API_BASE_URL}/api/v1/items/${itemId}/packaging-units/${unitId}`,
      data,
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async softDelete(itemId: string, unitId: string): Promise<ItemPackagingUnit> {
    const res = await axios.delete(
      `${API_BASE_URL}/api/v1/items/${itemId}/packaging-units/${unitId}`,
      { headers: this.getHeaders() },
    );
    return res.data; // returns the unit with is_active: false
  }
}

export const itemPackagingUnitService = new ItemPackagingUnitService();
```

---

## React Hooks

```typescript
// hooks/useItemPackagingUnits.ts

import { useState, useEffect } from "react";
import { itemPackagingUnitService } from "../services/itemPackagingUnitService";
import type {
  ItemPackagingUnit,
  ItemPackagingUnitCreate,
  ItemPackagingUnitUpdate,
} from "../types/wms.types";

export const useItemPackagingUnits = (itemId: string | null) => {
  const [units, setUnits] = useState<ItemPackagingUnit[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchUnits = async () => {
    if (!itemId) return;
    setLoading(true);
    setError(null);
    try {
      const res = await itemPackagingUnitService.list(itemId, {
        is_active: true,
      });
      setUnits(res.packaging_units);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load packaging units");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUnits();
  }, [itemId]);

  const create = async (data: ItemPackagingUnitCreate) => {
    if (!itemId) throw new Error("No item selected");
    const unit = await itemPackagingUnitService.create(itemId, data);
    setUnits((prev) => [...prev, unit]);
    return unit;
  };

  const update = async (unitId: string, data: ItemPackagingUnitUpdate) => {
    if (!itemId) throw new Error("No item selected");
    const updated = await itemPackagingUnitService.update(itemId, unitId, data);
    setUnits((prev) => prev.map((u) => (u.id === unitId ? updated : u)));
    return updated;
  };

  const softDelete = async (unitId: string) => {
    if (!itemId) throw new Error("No item selected");
    const deleted = await itemPackagingUnitService.softDelete(itemId, unitId);
    setUnits((prev) => prev.filter((u) => u.id !== unitId));
    return deleted;
  };

  return {
    units,
    loading,
    error,
    refetch: fetchUnits,
    create,
    update,
    softDelete,
  };
};
```

---

## Component Examples

### PackagingUnitsPanel — embed in Item detail page

```typescript
// components/items/PackagingUnitsPanel.tsx

import React, { useState } from 'react';
import { useItemPackagingUnits } from '../../hooks/useItemPackagingUnits';
import type { ItemPackagingUnitCreate } from '../../types/wms.types';

interface Props {
  itemId: string;
}

export const PackagingUnitsPanel: React.FC<Props> = ({ itemId }) => {
  const { units, loading, error, create, softDelete } = useItemPackagingUnits(itemId);
  const [showForm, setShowForm] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleCreate = async (data: ItemPackagingUnitCreate) => {
    setFormError(null);
    try {
      await create(data);
      setShowForm(false);
    } catch (err: any) {
      const status = err.response?.status;
      if (status === 409) {
        setFormError(`A packaging unit named "${data.unit_name}" already exists for this item.`);
      } else if (status === 422) {
        setFormError('Conversion factor must be greater than 0.');
      } else {
        setFormError(err.response?.data?.detail || 'Failed to create packaging unit.');
      }
    }
  };

  if (loading) return <div>Loading packaging units...</div>;
  if (error) return <div className="text-red-500">{error}</div>;

  return (
    <div className="packaging-units-panel">
      <div className="flex justify-between items-center mb-3">
        <h3 className="font-semibold">Packaging Units</h3>
        <button onClick={() => setShowForm(true)} className="btn-primary text-sm">
          + Add Unit
        </button>
      </div>

      {units.length === 0 && !showForm && (
        <p className="text-gray-400 text-sm">No packaging units defined. Add one to enable multi-UOM scanning.</p>
      )}

      <table className="w-full text-sm">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left px-3 py-2">Unit Name</th>
            <th className="text-left px-3 py-2">QR Identifier</th>
            <th className="text-right px-3 py-2">Conversion Factor</th>
            <th className="text-right px-3 py-2">L × W × H (mm)</th>
            <th className="text-right px-3 py-2">Weight (g)</th>
            <th className="text-left px-3 py-2">Status</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {units.map(unit => (
            <tr key={unit.id} className="border-t">
              <td className="px-3 py-2 font-medium">
                {unit.unit_name}
                {unit.is_base_unit && (
                  <span className="ml-2 text-xs bg-blue-100 text-blue-700 px-1 rounded">Base</span>
                )}
              </td>
              <td className="px-3 py-2 font-mono text-xs">{unit.qr_identifier || '—'}</td>
              <td className="px-3 py-2 text-right">{unit.conversion_factor}</td>
              <td className="px-3 py-2 text-right text-xs text-gray-500">
                {unit.length_mm && unit.width_mm && unit.height_mm
                  ? `${unit.length_mm} × ${unit.width_mm} × ${unit.height_mm}`
                  : '—'}
              </td>
              <td className="px-3 py-2 text-right">{unit.weight_grams ?? '—'}</td>
              <td className="px-3 py-2">
                <span className={`text-xs px-2 py-0.5 rounded-full ${unit.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                  {unit.is_active ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td className="px-3 py-2">
                <button
                  onClick={() => softDelete(unit.id)}
                  className="text-red-500 text-xs hover:underline"
                >
                  Remove
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showForm && (
        <PackagingUnitForm
          onSubmit={handleCreate}
          onCancel={() => { setShowForm(false); setFormError(null); }}
          error={formError}
        />
      )}
    </div>
  );
};
```

### PackagingUnitForm

```typescript
// components/items/PackagingUnitForm.tsx

import React, { useState } from 'react';
import type { ItemPackagingUnitCreate } from '../../types/wms.types';

interface Props {
  onSubmit: (data: ItemPackagingUnitCreate) => Promise<void>;
  onCancel: () => void;
  error?: string | null;
}

export const PackagingUnitForm: React.FC<Props> = ({ onSubmit, onCancel, error }) => {
  const [unitName, setUnitName] = useState('');
  const [qrIdentifier, setQrIdentifier] = useState('');
  const [conversionFactor, setConversionFactor] = useState<number>(1);
  const [lengthMm, setLengthMm] = useState<string>('');
  const [widthMm, setWidthMm] = useState<string>('');
  const [heightMm, setHeightMm] = useState<string>('');
  const [weightGrams, setWeightGrams] = useState<string>('');
  const [isBaseUnit, setIsBaseUnit] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (conversionFactor <= 0) return;
    setSubmitting(true);
    try {
      await onSubmit({
        unit_name: unitName,
        qr_identifier: qrIdentifier || null,
        conversion_factor: conversionFactor,
        length_mm: lengthMm ? parseFloat(lengthMm) : null,
        width_mm: widthMm ? parseFloat(widthMm) : null,
        height_mm: heightMm ? parseFloat(heightMm) : null,
        weight_grams: weightGrams ? parseFloat(weightGrams) : null,
        is_base_unit: isBaseUnit,
      });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="mt-4 p-4 border rounded bg-gray-50">
      <h4 className="font-medium mb-3">New Packaging Unit</h4>

      <div className="grid grid-cols-2 gap-3 mb-3">
        <div>
          <label className="block text-xs font-medium mb-1">Unit Name *</label>
          <input
            type="text"
            value={unitName}
            onChange={e => setUnitName(e.target.value)}
            placeholder="e.g. Box of 12"
            maxLength={100}
            required
            className="w-full border rounded px-2 py-1 text-sm"
          />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">QR Identifier</label>
          <input
            type="text"
            value={qrIdentifier}
            onChange={e => setQrIdentifier(e.target.value)}
            placeholder="e.g. BOX-12-WIDGET"
            maxLength={255}
            className="w-full border rounded px-2 py-1 text-sm"
          />
          <p className="text-xs text-gray-400 mt-0.5">Printed on the packaging label. Must be unique.</p>
        </div>
      </div>

      <div className="mb-3">
        <label className="block text-xs font-medium mb-1">
          Conversion Factor * <span className="text-gray-400">(how many Eaches in this unit)</span>
        </label>
        <input
          type="number"
          value={conversionFactor}
          onChange={e => setConversionFactor(parseFloat(e.target.value))}
          min={0.000001}
          step="any"
          required
          className="w-32 border rounded px-2 py-1 text-sm"
        />
        {conversionFactor <= 0 && (
          <p className="text-red-500 text-xs mt-0.5">Must be greater than 0</p>
        )}
      </div>

      <div className="grid grid-cols-4 gap-3 mb-3">
        <div>
          <label className="block text-xs font-medium mb-1">Length (mm)</label>
          <input type="number" value={lengthMm} onChange={e => setLengthMm(e.target.value)} min={0} step="any" className="w-full border rounded px-2 py-1 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Width (mm)</label>
          <input type="number" value={widthMm} onChange={e => setWidthMm(e.target.value)} min={0} step="any" className="w-full border rounded px-2 py-1 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Height (mm)</label>
          <input type="number" value={heightMm} onChange={e => setHeightMm(e.target.value)} min={0} step="any" className="w-full border rounded px-2 py-1 text-sm" />
        </div>
        <div>
          <label className="block text-xs font-medium mb-1">Weight (g)</label>
          <input type="number" value={weightGrams} onChange={e => setWeightGrams(e.target.value)} min={0} step="any" className="w-full border rounded px-2 py-1 text-sm" />
        </div>
      </div>

      <div className="mb-3">
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={isBaseUnit} onChange={e => setIsBaseUnit(e.target.checked)} />
          This is the base unit (Each)
        </label>
      </div>

      {error && <div className="text-red-500 text-sm mb-3">{error}</div>}

      <div className="flex gap-2">
        <button type="submit" disabled={submitting || conversionFactor <= 0} className="btn-primary text-sm">
          {submitting ? 'Saving...' : 'Save'}
        </button>
        <button type="button" onClick={onCancel} className="text-sm text-gray-500 hover:underline">
          Cancel
        </button>
      </div>
    </form>
  );
};
```

### Updated ScanSessionPanel — handle `raw_quantity`

The scan result now returns `raw_quantity` instead of `quantity`. Update the scan table display:

```typescript
// In ScanSessionPanel.tsx — update the scan results table column

// BEFORE:
<td className="px-3 py-2">{scan.quantity}</td>

// AFTER:
<td className="px-3 py-2">
  {scan.raw_quantity}
  {scan.packaging_unit_id && (
    <span className="ml-1 text-xs text-gray-400">(raw)</span>
  )}
</td>
```

Also update the `ScanResult` type import and any state that stores scan results.

### Updated WarehouseLocation form — volumetric capacity fields

Add `max_volume_cc` and `max_weight_grams` inputs to the bin location create/edit form:

```typescript
// In LocationForm.tsx — add these fields when location_type === 'bin'

{locationType === 'bin' && (
  <div className="grid grid-cols-2 gap-4 mt-4">
    <div>
      <label className="block text-sm font-medium mb-1">
        Max Volume (cc) <span className="text-gray-400 font-normal">— optional</span>
      </label>
      <input
        type="number"
        value={maxVolumeCc ?? ''}
        onChange={e => setMaxVolumeCc(e.target.value ? parseFloat(e.target.value) : null)}
        min={0}
        step="any"
        placeholder="Leave blank for unlimited"
        className="w-full border rounded px-3 py-2"
      />
      <p className="text-xs text-gray-400 mt-1">
        Cubic centimetres. Used for automatic bin assignment.
      </p>
    </div>
    <div>
      <label className="block text-sm font-medium mb-1">
        Max Weight (g) <span className="text-gray-400 font-normal">— optional</span>
      </label>
      <input
        type="number"
        value={maxWeightGrams ?? ''}
        onChange={e => setMaxWeightGrams(e.target.value ? parseFloat(e.target.value) : null)}
        min={0}
        step="any"
        placeholder="Leave blank for unlimited"
        className="w-full border rounded px-3 py-2"
      />
      <p className="text-xs text-gray-400 mt-1">
        Grams. Used for automatic bin assignment.
      </p>
    </div>
  </div>
)}
```

---

## Module Structure — New Files

```
src/features/wms/
├── components/
│   └── items/                          # NEW folder
│       ├── PackagingUnitsPanel.tsx     # Embed in item detail page
│       └── PackagingUnitForm.tsx       # Create/edit form
├── hooks/
│   └── useItemPackagingUnits.ts        # NEW hook
├── services/
│   └── itemPackagingUnitService.ts     # NEW service
└── types/
    └── wms.types.ts                    # UPDATE — add new types, update existing
```

---

## Files to Update

| File                                      | Change                                                                                                                                                                                                                                                                                             |
| ----------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `types/wms.types.ts`                      | Add `ItemPackagingUnit`, `ItemPackagingUnitCreate`, `ItemPackagingUnitUpdate`, `ItemPackagingUnitListResponse`; update `ScanResult` (rename `quantity` → `raw_quantity`, add `packaging_unit_id`); update `WarehouseLocation` (add `max_volume_cc`, `max_weight_grams`); update `Item` (add `sku`) |
| `utils/qrPayloadParser.ts`                | Add optional `packaging_unit_qr_id` to `QRPayload` interface and parser                                                                                                                                                                                                                            |
| `components/inbound/ScanSessionPanel.tsx` | Replace `scan.quantity` with `scan.raw_quantity`                                                                                                                                                                                                                                                   |
| `components/layout/LocationForm.tsx`      | Add `max_volume_cc` / `max_weight_grams` inputs for bin type                                                                                                                                                                                                                                       |
| `components/layout/LocationDetail.tsx`    | Display `max_volume_cc` / `max_weight_grams` when set                                                                                                                                                                                                                                              |
| `components/layout/LocationTree.tsx`      | Optionally show volumetric capacity in bin tooltips                                                                                                                                                                                                                                                |
| `hooks/useInboundSession.ts`              | Update `ScanResult` type reference                                                                                                                                                                                                                                                                 |

---

## Error Handling Reference

| HTTP | Scenario                                 | User-Facing Message                                                                                                                                               |
| ---- | ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 404  | Item not found                           | "Item not found"                                                                                                                                                  |
| 404  | Packaging unit not found                 | "Packaging unit not found"                                                                                                                                        |
| 409  | Duplicate unit name for item             | "A packaging unit named '{unit_name}' already exists for this item"                                                                                               |
| 422  | `conversion_factor <= 0`                 | "Conversion factor must be greater than 0"                                                                                                                        |
| 422  | Inactive packaging unit at slip approval | "Packaging unit not found or inactive. Cannot approve slip." — show this as a blocking error on the approve action with a link to the item's packaging units page |

---

## Key UX Rules

1. **Packaging units panel belongs on the Item detail page** — not a standalone page. Embed `PackagingUnitsPanel` as a tab or section within the existing item detail view.
2. **Soft-delete, not hard-delete** — the DELETE endpoint sets `is_active = false`. Show a confirmation dialog: "This will deactivate the packaging unit. Existing scan records will not be affected."
3. **Conversion factor is required and must be > 0** — validate client-side before submitting. Show inline error immediately.
4. **Dimensions are optional but all-or-nothing for volumetric assignment** — if any of `length_mm`, `width_mm`, `height_mm` is missing, the system treats volume as unconstrained. Show a hint: "All three dimensions are needed for automatic bin capacity checking."
5. **`raw_quantity` in scan results is in the packaging unit's own units** — label it clearly in the scan table, e.g. "5 boxes" not "5 Eaches". The Eaches conversion happens at slip approval and is shown on the receiving slip line items.
6. **Receiving slip quantities are always in Eaches** — after approval, `receiving_slip_items.quantity` is already converted. No further conversion needed on the frontend.
7. **Bin capacity fields are optional** — null means unlimited. Don't show "0 cc" for null values; show "—" or "Unlimited".
8. **`sku` vs `item_code`** — display both in item views. `item_code` is the ERP reference; `sku` is the warehouse barcode/scan identifier. Label them clearly to avoid confusion.

---

## API Endpoint Summary

```
Base: http://localhost:8001/api/v1

NEW:
  GET    /items/{item_id}/packaging-units              → ItemPackagingUnitListResponse
  POST   /items/{item_id}/packaging-units              → ItemPackagingUnit (201)
  PATCH  /items/{item_id}/packaging-units/{id}         → ItemPackagingUnit (200)
  DELETE /items/{item_id}/packaging-units/{id}         → ItemPackagingUnit with is_active:false (200)

CHANGED (breaking):
  POST   /inbound/sessions/{id}/scan                   → ScanResult.quantity renamed to raw_quantity
                                                          ScanResult.packaging_unit_id added

UPDATED (additive, non-breaking):
  GET/POST/PATCH  /warehouse-locations                 → WarehouseLocation gains max_volume_cc, max_weight_grams
  GET/POST/PATCH  /items                               → Item gains sku field
```

---

## Support & Resources

- Swagger UI: http://localhost:8001/docs
- Backend spec: `.kiro/specs/wms-multi-uom-packaging-units/design.md`
- Requirements: `.kiro/specs/wms-multi-uom-packaging-units/requirements.md`
- Existing WMS module guide: `.kiro/steering/frontend-wms-module.md`
