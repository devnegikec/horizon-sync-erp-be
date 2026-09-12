# Put-away List Generation — Frontend Integration Guide

This document describes how the frontend integrates with the **put-away list generation** feature: generating a put-away list from a receiving slip, choosing between **automatic** (server-assigned bins) and **manual** (worker-assigned bins) modes, and configuring the organization's default behaviour.

All paths are relative to the Core Service base URL, e.g. `https://core-service-…/api/v1`.

---

## 1. Overview

When goods are received, the flow is:

1. A **receiving slip** is created from a scan session.
2. The slip is **approved**, moving it to `pending_putaway`.
3. A **put-away list** is generated from the slip. This can be:
   - **`auto`** — the server assigns bins (respecting location allocations, capacity, volumetric fit) and sorts items by the optimal walking/traversal route so workers put away faster.
   - **`manual`** — the list is created with items grouped by SKU/batch but **without bin assignment**; workers pick each bin themselves.
4. Workers **complete** each put-away item (optionally choosing a bin).

The organisation can choose a **default mode** in settings (`putaway_mode`).

---

## 2. Organisation default setting (`putaway_mode`)

The default generation mode is stored in the tenant-scoped settings store (same table/API as Pick Settings).

| Key | Type | Default | Allowed |
|-----|------|---------|---------|
| `putaway_mode` | enum | `auto` | `auto`, `manual` |

### Settings endpoints

```http
# Catalog (powers the settings editor UI — now includes putaway_mode)
GET /api/v1/pick-settings/catalog
# Permission: organization.update

# Effective settings for the current org (defaults merged with overrides)
GET /api/v1/pick-settings
# Permission: organization.update

# Upsert an override
PUT /api/v1/pick-settings
Content-Type: application/json
{ "settings": { "putaway_mode": "manual" } }
# Permission: organization.update

# Reset all overrides to defaults
POST /api/v1/pick-settings/reset
# Permission: organization.update
```

### Resolution order for a generation request

1. Explicit `mode` in the request body wins.
2. Otherwise → org `putaway_mode` override.
3. Otherwise → code default `auto`.

> **Recommendation:** ship a settings screen (admin) with a dropdown "Put-away generation mode" bound to `putaway_mode`. It appears automatically in `/pick-settings/catalog` (key `putaway_mode`, type `enum`, allowed `["auto","manual"]`).

---

## 3. API endpoints

| Method | Path | Permission | Purpose |
|--------|------|-----------|---------|
| `POST` | `/put-away/generate-from-slip/{slip_id}` | `warehouse.create` | Generate a put-away list (auto or manual) |
| `GET`  | `/put-away` | `warehouse.read` | List put-away lists (paginated, filterable) |
| `GET`  | `/put-away/{put_away_list_id}` | `warehouse.read` | Get list detail with items |
| `POST` | `/put-away/{put_away_list_id}/items/{item_id}/complete` | `warehouse.update` | Complete an item (optionally choose bin) |
| `POST` | `/put-away/{put_away_list_id}/items/{item_id}/skip` | `warehouse.update` | Skip an item with a reason |

---

## 4. Generate a put-away list

```
POST /api/v1/put-away/generate-from-slip/{slip_id}
```

**Request body (all fields optional):**

```json
{
  "worker_id": "6b1f...",   // optional: assign this worker
  "mode": "auto"            // "auto" | "manual" — omit to use org default
}
```

**Constraints:**

- The receiving slip must be in `pending_putaway` status (approve it first).
- Only **one** list can be generated per slip. A second call returns `422`:
  > `Put-away list '…' already exists for receiving slip '…'`
- `damaged`, `rejected`, `hold`, `quarantine`, and `excess` slip lines are **skipped** automatically (they stay segregated until manager disposition). Skipped items are reported in the response `warnings`.

**Response `201`** — `PutAwayListResponse` (see §6).

### Frontend example

```ts
async function generatePutAwayList(slipId: string, mode?: "auto" | "manual", workerId?: string) {
  const res = await fetch(`/api/v1/put-away/generate-from-slip/${slipId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      ...(workerId ? { worker_id: workerId } : {}),
      ...(mode ? { mode } : {}),
    }),
  });
  if (!res.ok) throw new Error((await res.json()).detail ?? res.statusText);
  return res.json(); // PutAwayListResponse
}
```

---

## 5. Manual vs auto behaviour (what the frontend shows)

### `auto` mode (efficient)

- Each list item has `bin_location_id` and `bin_location_code` populated.
- Items are ordered by `sort_order` — the optimal traversal route. **Render the list in `sort_order` order** so the worker walks the shortest path.
- `suggested_bin_code` may also be present (volumetric/optimization suggestion).

### `manual` mode

- Items are grouped by SKU/batch, one item per slip line.
- `bin_location_id` / `bin_location_code` are **`null`** until the worker assigns a bin.
- Worker completes each item and supplies the bin:

```
POST /api/v1/put-away/{put_away_list_id}/items/{item_id}/complete
{ "bin_id": "4f2a..." }
```

> The same `complete` endpoint is used in both modes; in `auto` mode the `bin_id` is an optional override of the pre-assigned bin.

---

## 6. Response schemas

### `PutAwayListResponse`

```json
{
  "id": "…",
  "organization_id": "…",
  "warehouse_id": "…",
  "put_away_list_no": "PA-2026-00042",
  "status": "pending",
  "reference_type": "receiving_slip",
  "reference_id": "…",
  "receiving_slip_id": "…",
  "receiving_slip_no": "RS-2026-00091",
  "remarks": null,
  "warnings": [
    "Skipped 1 held/quarantined/excess item(s): PTK-OMG-D001 (batch: …)"
  ],
  "assigned_to": "6b1f...",        // null if not assigned
  "worker_name": null,
  "total_items": 120,
  "completed_items": 0,
  "pending_items": 120,
  "completed_at": null,
  "created_at": "2026-09-03T…",
  "updated_at": "2026-09-03T…",
  "items": [ /* PutAwayListItemResponse[] */ ]
}
```

### `PutAwayListItemResponse`

```json
{
  "id": "…",
  "item_id": "…",
  "sku": "PTK-OMG-D001",
  "item_name": "PRESTIGE …",
  "batch_number": "BATCH-SEP-02-2",
  "serial_number": "TTK-QYI1AG",
  "manufacturing_date": null,
  "expiry_date": null,
  "quantity": 10,
  "bin_location_id": "…",       // null in manual mode until completed
  "bin_location_code": "Z01-A03-…", // null in manual mode until completed
  "suggested_bin_code": null,
  "sort_order": 0,
  "status": "pending",           // pending | completed | skipped
  "notes": null,
  "completed_at": null,
  "created_at": "…"
}
```

### `PutAwayListListResponse` (list endpoint)

```json
{
  "put_away_lists": [ /* PutAwayListSummaryResponse[] */ ],
  "pagination": {
    "page": 1, "page_size": 20,
    "total_items": 137, "total_pages": 7,
    "has_next": true, "has_prev": false
  }
}
```

List items are summaries (no `items` array); use the detail endpoint to load items.

---

## 7. Suggested UI flows

### 7.1 Generation dialog (on receiving slip detail)

- Button: **"Generate Put-away List"** (enabled only when slip status = `pending_putaway`).
- Dialog fields:
  - **Mode**: `Default (org setting)` / `Automatic` / `Manual` — maps to omitting `mode`, `"auto"`, `"manual"`.
  - **Worker**: optional user picker (maps to `worker_id`).
- On success, show the `warnings` (skipped held/damaged/rejected items) and navigate to the list detail.

### 7.2 Put-away list detail

- Sort items by `sort_order` ascending (critical in `auto` mode for efficient walking).
- Show `bin_location_code` when present.
- In `manual` mode: each unassigned item shows a **"Assign bin"** action (bin scanner/picker), then call `complete` with `bin_id`.
- In `auto` mode: worker scans the assigned bin and confirms; `bin_id` is pre-filled but can be overridden.

### 7.3 Settings screen

- Add a dropdown for **"Put-away generation mode"** bound to the `putaway_mode` key.
- Read from `GET /pick-settings` (value under `settings.putaway_mode`).
- Save via `PUT /pick-settings { "settings": { "putaway_mode": value } }`.

---

## 8. Error handling reference

| Status | Meaning |
|--------|---------|
| `201` | Put-away list generated |
| `404` | Receiving slip / list / item not found |
| `409` | Slip not in `pending_putaway` (approve first) |
| `422` | Duplicate list for slip, invalid `mode`, or invalid settings value |

---

## 9. Notes

- The `mode` field is optional on the generate request; the frontend may simply **omit it** to honour the org default, or send an explicit override.
- `bin_location_id`/`bin_location_code` being `null` is expected in `manual` mode — it is not an error.
- Efficiency (shortest walking route) only applies to `auto` mode, which is the default.
