# Frontend Integration: Inbound Receiving & Put-Away Workflow

## Overview

This document covers the complete Inbound Receiving → Put-Away workflow for frontend integration. The flow goes:

```
Start Scan Session → Scan QR Boxes → End Session (generates Receiving Slip)
    → Review/Flag Items → Approve Slip → Generate Put-Away List
    → Execute Put-Away (complete/skip items) → Done
```

---

## Complete Workflow Diagram

```
[Dock Worker App]
    │
    ├─ POST /inbound/sessions                          → Start scan session
    ├─ POST /inbound/sessions/{id}/scan  (× N boxes)   → Scan QR codes
    ├─ GET  /inbound/sessions/{id}/summary             → Review scanned items
    └─ POST /inbound/sessions/{id}/end                 → Generate receiving slip

[Supervisor App]
    │
    ├─ GET  /inbound/receiving-slips                   → List slips (filter pending_review)
    ├─ GET  /inbound/receiving-slips/{id}              → Review slip details
    ├─ POST /inbound/receiving-slips/{id}/items/{i}/flag → Flag damaged/short items
    └─ POST /inbound/receiving-slips/{id}/approve       → Approve + auto-generate put-away
         │
         │  OR (decoupled approach — NEW)
         │
         ├─ POST /put-away/generate-from-slip/{id}      → Generate put-away list standalone

[Warehouse Worker App]
    │
    ├─ GET  /put-away                                  → List put-away lists
    ├─ GET  /put-away/{id}                             → View put-away with bin locations
    ├─ POST /put-away/{id}/items/{itemId}/complete     → Complete an item
    └─ POST /put-away/{id}/items/{itemId}/skip         → Skip an item
```

---

## TypeScript Types

Create `types/inbound.types.ts`:

```typescript
// ===========================================
// SCAN SESSION
// ===========================================

export interface StartSessionRequest {
  warehouse_id: string;
  dock_location?: string;
}

export interface SessionResponse {
  id: string;
  organization_id: string;
  session_type: string;
  worker_id: string;
  warehouse_id: string;
  dock_location: string | null;
  status: "open" | "closed";
  total_boxes_scanned: number;
  started_at: string | null;
  ended_at: string | null;
  created_at: string | null;
}

// ===========================================
// QR SCAN
// ===========================================

export interface RecordScanRequest {
  qr_data: string;
  device_type?: string;
  os?: string;
}

export interface ScanResult {
  scan_item_id: string;
  session_id: string;
  qr_identifier: string;
  sku: string;
  raw_quantity: number;
  batch_number: string;
  packaging_unit_id: string | null;
  scanned_at: string | null;
  total_boxes_scanned: number;
}

// ===========================================
// SESSION SUMMARY
// ===========================================

export interface BatchBreakdown {
  batch_number: string;
  quantity: number;
  box_count: number;
}

export interface SKUBreakdown {
  sku: string;
  total_quantity: number;
  total_boxes: number;
  batches: BatchBreakdown[];
}

export interface SessionSummary {
  session_id: string;
  status: string;
  session_type: string;
  warehouse_id: string;
  worker_id: string;
  dock_location: string | null;
  started_at: string | null;
  ended_at: string | null;
  total_boxes: number;
  total_quantity: number;
  items: SKUBreakdown[];
}

// ===========================================
// RECEIVING SLIP
// ===========================================

export interface ReceivingSlipItem {
  id: string;
  sku: string;
  batch_number: string | null;
  quantity: number;
  box_count: number;
  flag: "ok" | "short" | "damaged";
  notes: string | null;
}

export type ReceivingSlipStatus =
  | "pending_review"
  | "pending_putaway"
  | "putaway_complete"
  | "rejected";

export interface ReceivingSlip {
  id: string;
  organization_id: string;
  slip_number: string;
  session_id: string;
  warehouse_id: string;
  status: ReceivingSlipStatus;
  total_boxes: number;
  total_items: number;
  rejection_reason: string | null;
  notes: string | null;
  items: ReceivingSlipItem[];
  created_at: string | null;
  updated_at: string | null;
}

export interface ReceivingSlipPagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface ReceivingSlipListResponse {
  receiving_slips: ReceivingSlip[];
  pagination: ReceivingSlipPagination;
}

// ===========================================
// SLIP ACTIONS
// ===========================================

export interface ApproveSlipRequest {
  worker_id?: string;
}

export interface RejectSlipRequest {
  reason: string;
}

export interface FlagLineItemRequest {
  flag: "short" | "damaged";
  notes?: string;
}

export interface FlaggedItemResponse {
  id: string;
  slip_id: string;
  sku: string;
  batch_number: string | null;
  quantity: number;
  box_count: number;
  flag: string;
  notes: string | null;
}
```

Create `types/putAway.types.ts`:

```typescript
// ===========================================
// PUT-AWAY LIST
// ===========================================

export interface GeneratePutAwayRequest {
  worker_id?: string;
}

export interface PutAwayListItem {
  id: string;
  item_id: string;
  sku: string | null;
  batch_number: string | null;
  quantity: number;
  bin_location_id: string | null;
  bin_location_code: string | null; // Full path or code of the bin
  sort_order: number; // Optimized traversal order
  status: "pending" | "completed" | "skipped";
  notes: string | null;
  completed_at: string | null;
  created_at: string | null;
}

export interface PutAwayList {
  id: string;
  organization_id: string;
  warehouse_id: string;
  put_away_list_no: string;
  status: "pending" | "completed" | "cancelled";
  reference_type: "receiving_slip" | null;
  reference_id: string | null;
  receiving_slip_id: string | null;
  remarks: string | null;
  assigned_to: string | null;
  completed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  items: PutAwayListItem[];
}

export interface PutAwayListSummary {
  id: string;
  organization_id: string;
  warehouse_id: string;
  put_away_list_no: string;
  status: string;
  reference_type: string | null;
  reference_id: string | null;
  receiving_slip_id: string | null;
  remarks: string | null;
  assigned_to: string | null;
  total_items: number;
  completed_items: number;
  pending_items: number;
  completed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface PutAwayListListResponse {
  put_away_lists: PutAwayListSummary[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
    total_pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
}

export interface SkipPutAwayItemRequest {
  reason: string;
}
```

---

## API Service Implementation

Create `services/inboundService.ts`:

```typescript
import type {
  StartSessionRequest,
  SessionResponse,
  RecordScanRequest,
  ScanResult,
  SessionSummary,
  ReceivingSlip,
  ReceivingSlipListResponse,
  ApproveSlipRequest,
  RejectSlipRequest,
  FlagLineItemRequest,
  FlaggedItemResponse,
} from "@/types/inbound.types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

const headers = (token: string) => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${token}`,
});

// ===========================================
// SCAN SESSION
// ===========================================

/** Start a new inbound scan session */
export async function startScanSession(
  data: StartSessionRequest,
  token: string
): Promise<SessionResponse> {
  const res = await fetch(`${BASE_URL}/api/v1/inbound/sessions`, {
    method: "POST",
    headers: headers(token),
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Failed to start session: ${res.statusText}`);
  return res.json();
}

/** Record a QR scan within an open session */
export async function recordScan(
  sessionId: string,
  data: RecordScanRequest,
  token: string
): Promise<ScanResult> {
  const res = await fetch(
    `${BASE_URL}/api/v1/inbound/sessions/${sessionId}/scan`,
    {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    if (res.status === 422) {
      const err = await res.json();
      throw new Error(err.detail || "Duplicate scan detected");
    }
    throw new Error(`Failed to record scan: ${res.statusText}`);
  }
  return res.json();
}

/** Get session summary with per-SKU/batch aggregation */
export async function getSessionSummary(
  sessionId: string,
  token: string
): Promise<SessionSummary> {
  const res = await fetch(
    `${BASE_URL}/api/v1/inbound/sessions/${sessionId}/summary`,
    { headers: headers(token) }
  );
  if (!res.ok) throw new Error(`Failed to get summary: ${res.statusText}`);
  return res.json();
}

/** End a scan session and generate a receiving slip */
export async function endScanSession(
  sessionId: string,
  token: string
): Promise<ReceivingSlip> {
  const res = await fetch(
    `${BASE_URL}/api/v1/inbound/sessions/${sessionId}/end`,
    {
      method: "POST",
      headers: headers(token),
    }
  );
  if (!res.ok) throw new Error(`Failed to end session: ${res.statusText}`);
  return res.json();
}

// ===========================================
// RECEIVING SLIP
// ===========================================

export interface ListSlipsParams {
  warehouse_id?: string;
  session_id?: string;
  status?: string;
  page?: number;
  page_size?: number;
}

/** List receiving slips with optional filters */
export async function listReceivingSlips(
  params: ListSlipsParams,
  token: string
): Promise<ReceivingSlipListResponse> {
  const searchParams = new URLSearchParams();
  if (params.warehouse_id) searchParams.set("warehouse_id", params.warehouse_id);
  if (params.session_id) searchParams.set("session_id", params.session_id);
  if (params.status) searchParams.set("status", params.status);
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));

  const res = await fetch(
    `${BASE_URL}/api/v1/inbound/receiving-slips?${searchParams}`,
    { headers: headers(token) }
  );
  if (!res.ok) throw new Error(`Failed to list slips: ${res.statusText}`);
  return res.json();
}

/** Get a single receiving slip by ID */
export async function getReceivingSlip(
  slipId: string,
  token: string
): Promise<ReceivingSlip> {
  const res = await fetch(
    `${BASE_URL}/api/v1/inbound/receiving-slips/${slipId}`,
    { headers: headers(token) }
  );
  if (!res.ok) throw new Error(`Failed to get slip: ${res.statusText}`);
  return res.json();
}

/** Approve a receiving slip (transitions to pending_putaway + auto-generates put-away list) */
export async function approveReceivingSlip(
  slipId: string,
  data: ApproveSlipRequest,
  token: string
): Promise<ReceivingSlip> {
  const res = await fetch(
    `${BASE_URL}/api/v1/inbound/receiving-slips/${slipId}/approve`,
    {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    if (res.status === 409) {
      throw new Error("Slip is not in pending_review status");
    }
    throw new Error(`Failed to approve slip: ${res.statusText}`);
  }
  return res.json();
}

/** Reject a receiving slip */
export async function rejectReceivingSlip(
  slipId: string,
  data: RejectSlipRequest,
  token: string
): Promise<ReceivingSlip> {
  const res = await fetch(
    `${BASE_URL}/api/v1/inbound/receiving-slips/${slipId}/reject`,
    {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) throw new Error(`Failed to reject slip: ${res.statusText}`);
  return res.json();
}

/** Flag a line item as short or damaged */
export async function flagLineItem(
  slipId: string,
  itemId: string,
  data: FlagLineItemRequest,
  token: string
): Promise<FlaggedItemResponse> {
  const res = await fetch(
    `${BASE_URL}/api/v1/inbound/receiving-slips/${slipId}/items/${itemId}/flag`,
    {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) throw new Error(`Failed to flag item: ${res.statusText}`);
  return res.json();
}
```

Create `services/putAwayService.ts`:

```typescript
import type {
  GeneratePutAwayRequest,
  PutAwayList,
  PutAwayListItem,
  PutAwayListListResponse,
  SkipPutAwayItemRequest,
} from "@/types/putAway.types";

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "";

const headers = (token: string) => ({
  "Content-Type": "application/json",
  Authorization: `Bearer ${token}`,
});

// ===========================================
// PUT-AWAY LIST GENERATION (NEW ENDPOINT)
// ===========================================

/**
 * Generate a put-away list from an approved receiving slip.
 * The slip MUST be in "pending_putaway" status.
 *
 * Use this as a standalone call when:
 * - You want to decouple approval from generation
 * - Previous generation failed and you need to retry
 * - You need to re-generate the put-away list
 */
export async function generatePutAwayFromSlip(
  slipId: string,
  data: GeneratePutAwayRequest,
  token: string
): Promise<PutAwayList> {
  const res = await fetch(
    `${BASE_URL}/api/v1/put-away/generate-from-slip/${slipId}`,
    {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) {
    if (res.status === 409) {
      throw new Error("Slip is not in pending_putaway status");
    }
    throw new Error(`Failed to generate put-away: ${res.statusText}`);
  }
  return res.json();
}

// ===========================================
// PUT-AWAY LIST OPERATIONS
// ===========================================

export interface ListPutAwayParams {
  warehouse_id?: string;
  status?: "pending" | "completed";
  page?: number;
  page_size?: number;
}

/** List put-away lists with optional filters */
export async function listPutAwayLists(
  params: ListPutAwayParams,
  token: string
): Promise<PutAwayListListResponse> {
  const searchParams = new URLSearchParams();
  if (params.warehouse_id) searchParams.set("warehouse_id", params.warehouse_id);
  if (params.status) searchParams.set("status", params.status);
  if (params.page) searchParams.set("page", String(params.page));
  if (params.page_size) searchParams.set("page_size", String(params.page_size));

  const res = await fetch(
    `${BASE_URL}/api/v1/put-away?${searchParams}`,
    { headers: headers(token) }
  );
  if (!res.ok) throw new Error(`Failed to list put-away: ${res.statusText}`);
  return res.json();
}

/** Get a put-away list with all items (including bin location info) */
export async function getPutAwayList(
  putAwayListId: string,
  token: string
): Promise<PutAwayList> {
  const res = await fetch(
    `${BASE_URL}/api/v1/put-away/${putAwayListId}`,
    { headers: headers(token) }
  );
  if (!res.ok) throw new Error(`Failed to get put-away: ${res.statusText}`);
  return res.json();
}

/**
 * Complete a put-away item.
 * Adds stock to the assigned bin and triggers capacity rollup.
 * When ALL items are done, the put-away list and receiving slip
 * are automatically marked complete.
 */
export async function completePutAwayItem(
  putAwayListId: string,
  itemId: string,
  token: string
): Promise<PutAwayListItem> {
  const res = await fetch(
    `${BASE_URL}/api/v1/put-away/${putAwayListId}/items/${itemId}/complete`,
    {
      method: "POST",
      headers: headers(token),
    }
  );
  if (!res.ok) throw new Error(`Failed to complete item: ${res.statusText}`);
  return res.json();
}

/** Skip a put-away item with a reason */
export async function skipPutAwayItem(
  putAwayListId: string,
  itemId: string,
  data: SkipPutAwayItemRequest,
  token: string
): Promise<PutAwayListItem> {
  const res = await fetch(
    `${BASE_URL}/api/v1/put-away/${putAwayListId}/items/${itemId}/skip`,
    {
      method: "POST",
      headers: headers(token),
      body: JSON.stringify(data),
    }
  );
  if (!res.ok) throw new Error(`Failed to skip item: ${res.statusText}`);
  return res.json();
}
```

---

## Complete API Reference

### Inbound Endpoints (prefix: `/api/v1/inbound`)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/sessions` | `WAREHOUSE_CREATE` | Start a new inbound scan session |
| `POST` | `/sessions/{id}/scan` | `WAREHOUSE_CREATE` | Record a QR scan (422 on duplicate) |
| `GET` | `/sessions/{id}/summary` | `WAREHOUSE_READ` | Get aggregated session summary |
| `POST` | `/sessions/{id}/end` | `WAREHOUSE_CREATE` | End session → generates ReceivingSlip |
| `GET` | `/receiving-slips` | `WAREHOUSE_READ` | List slips (filter: warehouse_id, session_id, status) |
| `GET` | `/receiving-slips/{id}` | `WAREHOUSE_READ` | Get slip detail with items |
| `POST` | `/receiving-slips/{id}/approve` | `WAREHOUSE_UPDATE` | Approve slip + auto-generate put-away |
| `POST` | `/receiving-slips/{id}/reject` | `WAREHOUSE_UPDATE` | Reject slip with reason |
| `POST` | `/receiving-slips/{id}/items/{iid}/flag` | `WAREHOUSE_UPDATE` | Flag item as short/damaged |

### Put-Away Endpoints (prefix: `/api/v1/put-away`)

> **⚠️ Important:** The base path is `/api/v1/put-away` — **NOT** `/api/v1/put-away-lists`.
> There is no `-lists` suffix on any put-away endpoint.

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `POST` | `/generate-from-slip/{slipId}` | `WAREHOUSE_CREATE` | **NEW** Generate put-away from slip |
| `GET` | `/` | `WAREHOUSE_READ` | List put-away lists (filter: warehouse_id, status) |
| `GET` | `/{id}` | `WAREHOUSE_READ` | Get put-away detail with items |
| `POST` | `/{id}/items/{itemId}/complete` | `WAREHOUSE_CREATE` | Complete item → updates bin stock |
| `POST` | `/{id}/items/{itemId}/skip` | `WAREHOUSE_CREATE` | Skip item with reason |

---

## Status Flow

### Receiving Slip Statuses
```
pending_review → pending_putaway → putaway_complete
                ↘ rejected
```

### Put-Away List Statuses
```
pending → completed
        ↘ cancelled
```

### Put-Away Item Statuses
```
pending → completed
        → skipped
```

---

## Integration Notes

### 1. Approve vs Standalone Generate

There are **two ways** to generate a put-away list:

| Approach | Endpoint | Behavior |
|----------|----------|----------|
| **Approve (coupled)** | `POST /inbound/.../approve` | Approves slip AND generates put-away in one call |
| **Generate (decoupled)** | `POST /put-away/generate-from-slip/{id}` | Only generates put-away; slip must already be `pending_putaway` |

**Recommendation for frontend:**
- Use the **approve** endpoint for the normal happy path (one click)
- Use the **generate-from-slip** endpoint when you need to retry after a failure, or if your UI separates approval from put-away generation

### 2. Damaged Items

Items flagged as `damaged` on the receiving slip are **automatically skipped** during put-away generation. They will not appear in the put-away list.

### 3. Bin Assignment

Put-away items are assigned to bins respecting warehouse location allocations:
1. **Exclusive** allocations (item group locked to specific bins)
2. **Preferred** allocations (item group prefers these bins)
3. **Unallocated** bins (fallback)

Items are sorted by `sort_order` which is optimized for the most efficient traversal path through the warehouse.

### 4. Auto-Completion

When **all** items in a put-away list are either `completed` or `skipped`:
- The put-away list status changes to `completed`
- The linked receiving slip status changes to `putaway_complete`

### 5. Error Handling

| HTTP Status | Meaning |
|-------------|---------|
| `404` | Entity not found (session, slip, put-away list, item) |
| `409` | State conflict (e.g., approving a non-pending_review slip) |
| `422` | Validation error (duplicate scan, invalid flag, empty reason) |

### 6. Permissions Required

| Role | Permission | Can do |
|------|-----------|--------|
| Dock Worker | `WAREHOUSE_CREATE` | Start/end sessions, scan items |
| Supervisor | `WAREHOUSE_READ` + `WAREHOUSE_UPDATE` | Review slips, flag items, approve/reject |
| Warehouse Worker | `WAREHOUSE_CREATE` + `WAREHOUSE_READ` | View put-away lists, complete/skip items |

---

## Example: Complete Happy-Path Flow (React Hook)

```typescript
// hooks/useInboundWorkflow.ts

import { useState, useCallback } from "react";
import {
  startScanSession,
  recordScan,
  getSessionSummary,
  endScanSession,
} from "@/services/inboundService";
import type { SessionResponse, ScanResult, ReceivingSlip } from "@/types/inbound.types";

export function useInboundWorkflow(token: string) {
  const [session, setSession] = useState<SessionResponse | null>(null);
  const [scanResults, setScanResults] = useState<ScanResult[]>([]);
  const [slip, setSlip] = useState<ReceivingSlip | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startSession = useCallback(
    async (warehouseId: string, dockLocation?: string) => {
      setLoading(true);
      setError(null);
      try {
        const s = await startScanSession(
          { warehouse_id: warehouseId, dock_location: dockLocation },
          token
        );
        setSession(s);
        setScanResults([]);
        return s;
      } catch (e: any) {
        setError(e.message);
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [token]
  );

  const scanBox = useCallback(
    async (qrData: string) => {
      if (!session) throw new Error("No active session");
      setLoading(true);
      setError(null);
      try {
        const result = await recordScan(
          session.id,
          { qr_data: qrData },
          token
        );
        setScanResults((prev) => [...prev, result]);
        return result;
      } catch (e: any) {
        // 422 = duplicate scan — surface as warning, not error
        setError(e.message);
        throw e;
      } finally {
        setLoading(false);
      }
    },
    [session, token]
  );

  const endSession = useCallback(async () => {
    if (!session) throw new Error("No active session");
    setLoading(true);
    setError(null);
    try {
      const generatedSlip = await endScanSession(session.id, token);
      setSlip(generatedSlip);
      setSession(null);
      return generatedSlip;
    } catch (e: any) {
      setError(e.message);
      throw e;
    } finally {
      setLoading(false);
    }
  }, [session, token]);

  return {
    session,
    scanResults,
    slip,
    loading,
    error,
    startSession,
    scanBox,
    endSession,
  };
}
```

---

## Files Changed for This Feature

| File | Change |
|------|--------|
| `core-service/app/schemas/put_away.py` | Added `GeneratePutAwayRequest` schema |
| `core-service/app/api/v1/endpoints/put_away.py` | Added `POST /generate-from-slip/{slip_id}` endpoint |
| `frontend-inbound-putaway-integration.md` | This file (new) |
