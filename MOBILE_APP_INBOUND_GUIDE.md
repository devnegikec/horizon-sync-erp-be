# Mobile App — Inbound (Receiving + Put-Away) Integration Guide

> **Version**: 1.0
> **Date**: 2026-06-20
> **Audience**: Mobile App Developers (React Native / Flutter)
> **Base URL**: `http://<host>:9000/api/v1`

---

## 1. Inbound Flow Overview

```
Worker opens mobile app
  → Starts scan session
  → Scans item QR codes (box labels)
  → Ends session → System generates Receiving Slip
  → Admin approves slip → System generates Put-Away List
  → Worker scans bin QR → Confirms put-away → Stock updated
```

---

## 2. API Reference — Inbound Endpoints

### 2.1 Start Scan Session

```
POST /inbound/sessions
Authorization: Bearer <token>

Body:
{
  "warehouse_id": "0cbc00c4-7315-44e5-8fb3-687affa1e0ea",
  "dock_location": "DOCK-A"
}

Response 201:
{
  "id": "session-uuid",
  "warehouse_id": "...",
  "worker_id": "...",
  "status": "open",
  "dock_location": "DOCK-A",
  "created_at": "2026-06-20T10:00:00Z"
}
```

**Required permission**: `receiving_slip.create`

---

### 2.2 Record QR Scan

```
POST /inbound/sessions/{session_id}/scan
Authorization: Bearer <token>

Body:
{
  "qr_data": "{\"id\":\"RB7FJE\",\"sku\":\"ITEM-001\",\"qty\":50,\"batch\":\"BATCH-2025-01\"}"
}

Response 201:
{
  "id": "scan-uuid",
  "sku": "ITEM-001",
  "batch": "BATCH-2025-01",
  "quantity": 50,
  "is_duplicate": false
}
```

**QR Payload Format** (what the QR code must contain):

```json
{
  "id": "RB7FJE",
  "sku": "ITEM-001",
  "qty": 50,
  "batch": "BATCH-2025-01"
}
```

**Required permission**: `receiving_slip.create`

---

### 2.3 End Scan Session → Generate Receiving Slip

```
POST /inbound/sessions/{session_id}/end
Authorization: Bearer <token>

Response 200:
{
  "id": "slip-uuid",
  "slip_no": "RS-2025-0001",
  "status": "pending_putaway",
  "items": [
    {
      "id": "item-uuid",
      "sku": "ITEM-001",
      "batch_number": "BATCH-2025-01",
      "quantity": 150,
      "box_count": 3,
      "put_away_status": "pending"
    }
  ]
}
```

**Required permission**: `receiving_slip.create`

---

### 2.4 Assign Bin (NEW — Two-Step Inbound)

Worker scans bin QR → assigns bin to slip item → stock added to bin.

```
POST /inbound/receiving-slips/{slip_id}/items/{item_id}/assign-bin
Authorization: Bearer <token>

Body:
{
  "bin_location_id": "<scanned-bin-uuid>",
  "quantity": 50
}

Response 200:
{
  "slip_item_id": "...",
  "sku": "SVACHH-SS-POP-2L",
  "batch_number": "BATCH-2025-01",
  "quantity": 50,
  "bin_location_id": "...",
  "bin_full_path": "Z01-A01-B01-L01-BN001",
  "put_away_status": "completed",
  "put_away_at": "2026-06-22T10:00:00Z"
}
```

- If `quantity` is omitted, the full slip item quantity is used
- When ALL items on a slip are `put_away_status=completed`, slip status becomes `putaway_complete`

**Required permission**: `receiving_slip.create`

---

### 2.5 FIFO Bin Suggestions (NEW)

See which bins already have this SKU, sorted by stock age (oldest first).

```
GET /inbound/receiving-slips/{slip_id}/items/{item_id}/fifo-bins
Authorization: Bearer <token>

Response 200:
{
  "sku": "SVACHH-SS-POP-2L",
  "bins": [
    {
      "bin_id": "...",
      "bin_path": "Z01-A01-B01-L01-BN001",
      "batch_number": "BATCH-2025-01",
      "quantity_on_hand": 30,
      "stock_age_days": 172
    },
    {
      "bin_id": "...",
      "bin_path": "Z01-A01-B01-L01-BN005",
      "batch_number": "BATCH-2025-02",
      "quantity_on_hand": 20,
      "stock_age_days": 90
    }
  ]
}
```

**Required permission**: `warehouse.read`

---

## 3. Item Lookup (CRITICAL FIX)

### ✅ CORRECT — Use dedicated SKU lookup endpoint

```
GET /items/by-sku/12350301

Response 200:
{
  "id": "item-uuid",
  "item_code": "12350301",
  "item_name": "Widget A",
  "item_type": "stock",
  "uom": "Nos",
  "barcode": "12350301",
  "standard_rate": 150.00,
  "maintain_stock": true
}
```

Searches by `item_code` first, falls back to `barcode`. Returns 404 if not found.

**No special permission required** — any authenticated user can call this.

### 🔄 Alternative: Search endpoint (for partial matches)

```
GET /items?search=12350301&page_size=1
→ Returns paginated list
```

### ❌ WRONG — Do NOT use stock-levels

```
GET /stock-levels?search=12350301&warehouse_id=...
→ Returns empty if no stock exists yet → "No item found"
```

### Item Lookup Helper (TypeScript)

```typescript
// api/items.ts

const BASE = "/api/v1";

interface ItemResult {
  id: string;
  item_code: string;
  item_name: string;
  item_type: string | null;
  uom: string | null;
  barcode: string | null;
  standard_rate: number | null;
  maintain_stock: boolean | null;
}

export async function findItemBySKU(
  sku: string,
  token: string,
): Promise<ItemResult> {
  const url = `${BASE}/items/by-sku/${encodeURIComponent(sku)}`;
  const res = await fetch(url, {
    headers: { Authorization: `Bearer ${token}` },
  });

  if (res.status === 404) {
    throw new Error(`No item found for SKU: ${sku}`);
  }
  if (!res.ok) throw new Error(`Item lookup failed: ${res.status}`);

  return res.json();
}
```

---

## 4. Put-Away Flow (After Receiving Slip is Approved)

### 4.1 List Put-Away Lists (Worker sees assigned tasks)

```
GET /put-away?warehouse_id=<uuid>&status=pending

Response 200:
{
  "items": [
    {
      "id": "putaway-list-uuid",
      "put_away_list_no": "PA-2025-0001",
      "status": "pending",
      "item_count": 5,
      ...
    }
  ],
  "pagination": { ... }
}
```

### 4.2 Get Put-Away List Detail (with bin assignments)

```
GET /put-away/{putaway_list_id}

Response 200:
{
  "id": "...",
  "items": [
    {
      "id": "item-uuid",
      "sku": "ITEM-001",
      "batch_number": "BATCH-2025-01",
      "quantity": 50,
      "bin_location_id": "bin-uuid",
      "bin_location_code": "Z01-A01-B01-L01-BN001",
      "status": "pending"
    }
  ]
}
```

### 4.3 Complete Put-Away Item (Worker confirms put-away into bin)

```
POST /put-away/items/{item_id}/complete
Authorization: Bearer <token>

Body:
{
  "bin_location_id": "scanned-bin-uuid",
  "quantity": 50
}

Response 200:
{
  "id": "item-uuid",
  "status": "completed",
  "bin_location_id": "scanned-bin-uuid",
  "bin_location_code": "Z01-A01-B01-L01-BN001",
  "completed_at": "2026-06-20T10:30:00Z"
}
```

---

## 5. Bin QR Scanning During Put-Away

### 5.1 Scan Bin QR Code

The mobile app scans the bin QR code (generated via `GET /warehouse-locations/{id}/qr-image`):

```json
// QR payload decoded by mobile app:
{
  "type": "location",
  "org_id": "8614e0b8-...",
  "warehouse_id": "0cbc00c4-...",
  "warehouse_code": "WH-001",
  "warehouse_name": "Main Warehouse",
  "location_id": "bin-uuid",
  "full_path": "Z01-A01-B01-L01-BN001",
  "location_type": "bin",
  "location_code": "BN001"
}
```

### 5.2 Confirm Bin Assignment

```typescript
async function confirmPutAway(
  putAwayItemId: string,
  scannedBinQR: string,
  quantity: number,
  token: string,
) {
  const binPayload = JSON.parse(scannedBinQR);

  if (binPayload.type !== "location") {
    throw new Error("Scanned QR is not a bin location");
  }

  const res = await fetch(`${BASE}/put-away/items/${putAwayItemId}/complete`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      bin_location_id: binPayload.location_id,
      quantity: quantity,
    }),
  });

  if (!res.ok) throw new Error(`Put-away failed: ${res.status}`);
  return res.json();
}
```

---

## 6. Complete Inbound Flow — Two-Step (NEW)

```typescript
// 1. Start session
const session = await startSession(warehouseId, dockLocation, token);

// 2. Scan item boxes (each box = one QR scan)
for (const qrScan of scannedBoxes) {
  await recordScan(session.id, qrScan.rawData, token);
}

// 3. End session → receiving slip generated with items
const slip = await endSession(session.id, token);
// slip.items = [{ id, sku, batch_number, quantity, put_away_status: "pending" }]

// 4. For each slip item, assign a bin:
for (const item of slip.items) {
  // Show: "Put 50 × ITEM-001 (BATCH-2025-01) → Scan bin"

  // Worker scans bin QR → decodes location_id
  const binQR = await scanBinQR();
  const binPayload = JSON.parse(binQR);

  // Assign bin → stock added to bin
  await assignBin(
    slip.id,
    item.id,
    binPayload.location_id,
    item.quantity,
    token,
  );
  // Item now: put_away_status = "completed"
}

// 5. All items assigned → slip status auto-updates to "putaway_complete"
```

**No admin approval needed** — worker completes the full inbound flow. For FIFO suggestions during put-away, call:

```typescript
const fifo = await getFifoBins(slip.id, item.id, token);
// Shows existing bins with this SKU, oldest first
```

---

## 7. Common Mistakes

| Mistake                                              | Fix                                                     |
| ---------------------------------------------------- | ------------------------------------------------------- |
| Using `GET /stock-levels?search=...` to find items   | Use `GET /items?search=...` — items exist before stock  |
| Using `warehouse.create` permission                  | Workers need `receiving_slip.create`                    |
| Not sending `Authorization` header on image requests | Fetch QR blob with auth header, then use `blob:` URL    |
| QR payload missing `sku` or `batch`                  | Ensure QR encodes JSON with `id`, `sku`, `qty`, `batch` |

---

## 8. Permissions Reference

### `warehouse_work_user` Role (assigned automatically on worker creation)

| Permission              | Enables                                                 |
| ----------------------- | ------------------------------------------------------- |
| `warehouse.read`        | View warehouses, scan bin QR codes, view put-away lists |
| `wms.scan`              | QR/barcode scanning                                     |
| `receiving_slip.create` | Start scan session, record QR scans, end session        |
| `receiving_slip.read`   | View receiving slips                                    |
| `receiving_slip.update` | Update receiving slip details                           |
| `pick_list.read`        | View outbound pick lists                                |
| `pick_list.update`      | Start/finish picking items                              |
| `stock_entry.create`    | Add/remove stock from bins                              |
| `stock_entry.read`      | View bin stock levels                                   |

| Operation                   | Permission Required     |      Worker has?      |
| --------------------------- | ----------------------- | :-------------------: | --- | ----------------------- | ----------------------- | --- |
| Start scan session          | `receiving_slip.create` |          ✅           |
| Record QR scan              | `receiving_slip.create` |          ✅           |
| End session (generate slip) | `receiving_slip.create` |          ✅           |
| Look up item by SKU         | (any authenticated)     |          ✅           |
| List put-away tasks         | `warehouse.read`        |          ✅           |
| Complete put-away item      | `warehouse.read`        |          ✅           |     | Assign bin to slip item | `receiving_slip.create` | ✅  |
| View FIFO bin suggestions   | `warehouse.read`        |          ✅           |     | Add stock to bin        | `stock_entry.create`    | ✅  |
| Remove stock from bin       | `stock_entry.create`    |          ✅           |
| View bin stock              | `stock_entry.read`      |          ✅           |
| Scan bin QR                 | `warehouse.read`        |          ✅           |
| Generate put-away list      | `warehouse.create`      | ❌ Admin/Manager only |
