# Frontend WMS (Warehouse Management System) Module - Implementation Guide

## Overview

Build a complete Warehouse Management System module that enables:

1. **Layout Management** — Define warehouse hierarchy (Zone → Aisle → Bay → Level → Bin) with capacity rollup
2. **Bin Stock Tracking** — Track stock at the bin level with real-time capacity updates
3. **Inbound Receiving** — QR scan sessions at the dock, receiving slip generation and review
4. **Put-Away** — Optimized put-away lists grouped by zone/aisle with worker assignment
5. **Outbound Picking** — SAP invoice-triggered pick lists with FIFO bin resolution and QR scanning
6. **Gate Verification** — Security scan verification before vehicle dispatch
7. **Dispatch Records** — End-to-end traceability for outbound shipments
8. **Worker Tasks** — Task assignment and time tracking via QR location scans
9. **Location Allocations** — Assign bins/levels/bays to item groups (fast/slow movers)

## Workflow Diagrams

### Inbound Flow

```
Dock Worker starts session → Scans box QR codes → Ends session
    → Receiving Slip (PENDING_REVIEW) → Manager approves
    → Put-Away List generated (grouped by zone/aisle)
    → Worker scans at bins (start/finish QR) → Stock updated → PUTAWAY_COMPLETE
```

### Outbound Flow

```
SAP Invoice received → Pick List created (OPEN) → Bins resolved (FIFO)
    → Picker scans items (IN_PROGRESS) → All picked (COMPLETED)
    → Gate Security starts session → Scans items → VERIFIED
    → Dispatch Record created → Stock decremented
```

## API Endpoints Reference

### Base URL

```
http://localhost:8001/api/v1
```

### Authentication

All requests require Bearer token:

```
Authorization: Bearer {token}
```

### Endpoint Groups

| Group                | Base Path                 | Permission Prefix |
| -------------------- | ------------------------- | ----------------- |
| Layout & Capacity    | `/warehouse-locations`    | `warehouse.*`     |
| Bin Stock            | `/bin-stock`              | `warehouse.*`     |
| Location Allocations | `/location-allocations`   | `warehouse.*`     |
| Inbound              | `/inbound`                | `warehouse.*`     |
| Put-Away             | `/put-away-lists`         | `warehouse.*`     |
| Outbound Pick Lists  | `/outbound`               | `pick_list.*`     |
| Gate Verification    | `/outbound/gate-sessions` | `pick_list.*`     |
| Dispatches           | `/outbound/dispatches`    | `pick_list.*`     |
| Worker Tasks         | `/worker-tasks`           | `warehouse.*`     |
| Location Scans       | `/location-scans`         | `warehouse.*`     |
| Scan Events          | `/scan-events`            | `warehouse.*`     |

---

## Module Structure

```
src/
├── features/
│   └── wms/
│       ├── components/
│       │   ├── layout/
│       │   │   ├── LocationTree.tsx              # Hierarchical tree view
│       │   │   ├── LocationForm.tsx              # Create/edit location
│       │   │   ├── LocationDetail.tsx            # Location detail + summary
│       │   │   ├── LocationList.tsx              # Filtered list view
│       │   │   ├── LocationSearch.tsx            # Search by code/name
│       │   │   ├── CapacityBar.tsx               # Visual capacity indicator
│       │   │   └── LocationTypeBadge.tsx         # zone/aisle/bay/level/bin badge
│       │   ├── bin-stock/
│       │   │   ├── BinStockView.tsx              # Stock levels for a bin
│       │   │   ├── ItemBinsView.tsx              # All bins containing an item
│       │   │   ├── AddStockForm.tsx              # Add stock to bin
│       │   │   └── RemoveStockForm.tsx           # Remove stock from bin
│       │   ├── inbound/
│       │   │   ├── ScanSessionPanel.tsx          # Active scan session UI
│       │   │   ├── ScanSessionSummary.tsx        # Session summary view
│       │   │   ├── ReceivingSlipList.tsx         # List of receiving slips
│       │   │   ├── ReceivingSlipDetail.tsx       # Slip detail + review actions
│       │   │   ├── ReceivingSlipReview.tsx       # Approve/reject/flag UI
│       │   │   └── QRScanInput.tsx               # QR scan input component
│       │   ├── put-away/
│       │   │   ├── PutAwayList.tsx               # Put-away list view
│       │   │   ├── PutAwayDetail.tsx             # Put-away items with route
│       │   │   ├── PutAwayItemRow.tsx            # Individual item row
│       │   │   └── PutAwayProgress.tsx           # Progress indicator
│       │   ├── outbound/
│       │   │   ├── PickListList.tsx              # List of pick lists
│       │   │   ├── PickListDetail.tsx            # Pick list with progress
│       │   │   ├── PickScanPanel.tsx             # QR scan for picking
│       │   │   ├── PickListProgress.tsx          # Visual progress bar
│       │   │   └── CreateFromInvoice.tsx         # Create pick list from SAP
│       │   ├── gate/
│       │   │   ├── GateSessionPanel.tsx          # Gate verification session
│       │   │   ├── GateSessionProgress.tsx       # Scanned vs expected
│       │   │   └── GateScanResult.tsx            # Verified/unauthorized badge
│       │   ├── dispatch/
│       │   │   ├── DispatchList.tsx              # List of dispatch records
│       │   │   └── DispatchDetail.tsx            # Dispatch record detail
│       │   ├── tasks/
│       │   │   ├── WorkerTaskList.tsx            # Worker's task list
│       │   │   ├── WorkerTaskDetail.tsx          # Task detail + actions
│       │   │   └── TaskStatusBadge.tsx           # Status indicator
│       │   ├── time-tracking/
│       │   │   ├── LocationScanForm.tsx          # Record start/finish scan
│       │   │   └── TimeSummaryView.tsx           # Time tracking summary
│       │   └── shared/
│       │       ├── StatusBadge.tsx               # Generic status badge
│       │       ├── QRScanner.tsx                 # Camera-based QR scanner
│       │       └── ProgressBar.tsx               # Reusable progress bar
│       ├── hooks/
│       │   ├── useWarehouseLocations.ts
│       │   ├── useLocationTree.ts
│       │   ├── useBinStock.ts
│       │   ├── useLocationAllocations.ts
│       │   ├── useInboundSession.ts
│       │   ├── useReceivingSlips.ts
│       │   ├── usePutAwayLists.ts
│       │   ├── usePickLists.ts
│       │   ├── useGateVerification.ts
│       │   ├── useDispatches.ts
│       │   ├── useWorkerTasks.ts
│       │   └── useLocationScans.ts
│       ├── services/
│       │   ├── layoutService.ts
│       │   ├── binStockService.ts
│       │   ├── allocationService.ts
│       │   ├── inboundService.ts
│       │   ├── putAwayService.ts
│       │   ├── outboundService.ts
│       │   ├── gateVerificationService.ts
│       │   ├── dispatchService.ts
│       │   ├── workerTaskService.ts
│       │   └── locationScanService.ts
│       ├── types/
│       │   └── wms.types.ts
│       └── utils/
│           ├── statusHelpers.ts
│           ├── capacityHelpers.ts
│           └── qrPayloadParser.ts
```

## TypeScript Types

```typescript
// types/wms.types.ts

// ============================================
// WAREHOUSE LOCATION TYPES
// ============================================

export type LocationType = "zone" | "aisle" | "bay" | "level" | "bin";

export interface CreateLocationRequest {
  warehouse_id: string;
  parent_location_id: string | null;
  location_type: LocationType;
  code: string;
  name?: string | null;
  capacity?: number;
  capacity_uom?: string | null;
  position_x?: number;
  position_y?: number;
}

export interface UpdateLocationRequest {
  name?: string | null;
  capacity?: number;
  capacity_uom?: string | null;
  position_x?: number;
  position_y?: number;
}

export interface WarehouseLocation {
  id: string;
  organization_id: string;
  warehouse_id: string;
  parent_location_id: string | null;
  location_type: LocationType;
  code: string;
  full_path: string | null;
  name: string | null;
  capacity: number;
  total_capacity: number;
  available_capacity: number;
  capacity_uom: string | null;
  position_x: number;
  position_y: number;
  is_active: boolean;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface LocationTree
  extends Omit<
    WarehouseLocation,
    "organization_id" | "version" | "created_at" | "updated_at"
  > {
  children: LocationTree[];
}

export interface LocationSummary {
  total_bins: number;
  occupied_bins: number;
  total_capacity: number;
  used_capacity: number;
  available_capacity: number;
  item_count: number;
}

export interface PaginatedLocations {
  locations: WarehouseLocation[];
  pagination: Pagination;
}

// ============================================
// BIN STOCK TYPES
// ============================================

export interface AddStockRequest {
  bin_id: string;
  item_id: string;
  quantity: number;
  batch_number?: string | null;
}

export interface RemoveStockRequest {
  bin_id: string;
  item_id: string;
  quantity: number;
  batch_number?: string | null;
}

export interface BinStockLevel {
  id: string;
  organization_id: string;
  bin_location_id: string;
  item_id: string;
  quantity_on_hand: number;
  batch_number: string | null;
  created_at: string;
  updated_at: string;
}

export interface BinStockInfo {
  bin_location_id: string;
  bin_code: string | null;
  bin_name: string | null;
  warehouse_id: string;
  item_id: string;
  quantity_on_hand: number;
  batch_number: string | null;
  bin_capacity: number;
  available_capacity: number;
  is_active: boolean;
  created_at: string;
}

// ============================================
// LOCATION ALLOCATION TYPES
// ============================================

export type AllocationType = "exclusive" | "preferred";

export interface CreateAllocationRequest {
  location_id: string;
  item_group_id: string;
  allocation_type?: AllocationType;
  priority?: number;
}

export interface UpdateAllocationRequest {
  allocation_type?: AllocationType;
  priority?: number;
}

export interface LocationAllocation {
  id: string;
  organization_id: string;
  location_id: string;
  item_group_id: string;
  priority: number;
  allocation_type: AllocationType;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface PaginatedAllocations {
  allocations: LocationAllocation[];
  pagination: Pagination;
}

// ============================================
// INBOUND TYPES
// ============================================

export interface StartSessionRequest {
  warehouse_id: string;
  dock_location?: string | null;
}

export interface RecordScanRequest {
  qr_data: string;
  device_type?: string | null;
  os?: string | null;
}

export interface ScanSession {
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

export interface ScanResult {
  scan_item_id: string;
  session_id: string;
  qr_identifier: string;
  sku: string;
  quantity: number;
  batch_number: string;
  scanned_at: string | null;
  total_boxes_scanned: number;
}

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

export type ReceivingSlipStatus =
  | "pending_review"
  | "pending_putaway"
  | "putaway_complete"
  | "rejected";

export interface ReceivingSlipItem {
  id: string;
  sku: string;
  batch_number: string | null;
  quantity: number;
  box_count: number;
  flag: string;
  notes: string | null;
}

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

// ============================================
// OUTBOUND / PICK LIST TYPES
// ============================================

export type PickListStatus =
  | "draft"
  | "in_progress"
  | "completed"
  | "cancelled";

export interface SAPInvoiceItem {
  item_id: string;
  sku: string;
  quantity: number;
  uom: string;
}

export interface SAPInvoicePayload {
  invoice_reference: string;
  warehouse_id: string;
  items: SAPInvoiceItem[];
}

export interface PickListProgress {
  total_items: number;
  picked_items: number;
  remaining_items: number;
  total_qty: number;
  picked_qty: number;
  remaining_qty: number;
  completion_percentage: number;
}

export interface PickListItem {
  id: string;
  item_id: string;
  warehouse_id: string;
  qty: number;
  picked_qty: number;
  uom: string;
  batch_no: string | null;
  bin_location_id: string | null;
  sort_order: number;
}

export interface PickList {
  id: string;
  organization_id: string;
  pick_list_no: string;
  warehouse_id: string;
  status: PickListStatus;
  pick_date: string | null;
  reference_type: string | null;
  invoice_reference: string | null;
  completed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
  items: PickListItem[];
  progress: PickListProgress | null;
}

export interface PickScanResult {
  pick_list_id: string;
  pick_list_status: string;
  pick_list_item_id: string;
  item_id: string;
  sku: string;
  scanned_qty: number;
  picked_qty: number;
  required_qty: number;
  remaining_qty: number;
  batch: string | null;
}

// ============================================
// GATE VERIFICATION TYPES
// ============================================

export type GateSessionStatus = "open" | "verified" | "cancelled";

export interface GateSessionRequest {
  pick_list_id: string;
  vehicle_number?: string | null;
  driver_name?: string | null;
  driver_contact?: string | null;
}

export interface GateVerificationItem {
  id: string;
  qr_identifier: string;
  sku: string;
  quantity: number;
  status: "verified" | "unauthorized";
  scanned_at: string | null;
}

export interface DispatchInfo {
  id: string;
  organization_id: string;
  dispatch_number: string;
  pick_list_id: string;
  gate_session_id: string;
  invoice_reference: string | null;
  vehicle_number: string | null;
  driver_name: string | null;
  dispatched_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface GateSession {
  id: string;
  organization_id: string;
  pick_list_id: string;
  warehouse_id: string;
  worker_id: string;
  vehicle_number: string | null;
  driver_name: string | null;
  driver_contact: string | null;
  status: GateSessionStatus;
  verified_at: string | null;
  items: GateVerificationItem[];
  dispatch: DispatchInfo | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface GateScanResult {
  gate_item_id: string;
  session_id: string;
  qr_identifier: string;
  sku: string;
  quantity: number;
  batch: string | null;
  status: "verified" | "unauthorized";
  scanned_at: string | null;
}

export interface GateSessionProgress {
  session_id: string;
  status: string;
  pick_list_id: string;
  vehicle_number: string | null;
  driver_name: string | null;
  total_scanned: number;
  verified_count: number;
  unauthorized_count: number;
  verified_qty: number;
  expected_total_qty: number;
  all_verified: boolean;
  items: GateVerificationItem[];
}

// ============================================
// DISPATCH TYPES
// ============================================

export interface DispatchRecord {
  id: string;
  organization_id: string;
  dispatch_number: string;
  pick_list_id: string;
  gate_session_id: string;
  invoice_reference: string | null;
  vehicle_number: string | null;
  driver_name: string | null;
  dispatched_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface DispatchListResponse {
  dispatches: DispatchRecord[];
  pagination: Pagination;
}

// ============================================
// WORKER TASK TYPES
// ============================================

export type TaskType = "put_away" | "pick";
export type TaskStatus = "assigned" | "in_progress" | "completed" | "cancelled";

export interface WorkerTaskCreate {
  task_type: TaskType;
  worker_id: string;
  reference_id: string;
}

export interface WorkerTask {
  id: string;
  organization_id: string;
  task_type: TaskType;
  worker_id: string;
  reference_id: string;
  status: TaskStatus;
  assigned_at: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface WorkerTaskListResponse {
  tasks: WorkerTask[];
  pagination: Pagination;
}

// ============================================
// LOCATION SCAN (TIME TRACKING) TYPES
// ============================================

export type ScanType = "start" | "finish";

export interface LocationScanRequest {
  worker_id: string;
  task_id: string;
  location_code: string;
  scan_type: ScanType;
  scanned_at?: string | null;
}

export interface LocationScan {
  id: string;
  organization_id: string;
  worker_task_id: string;
  location_code: string;
  scan_type: ScanType;
  scanned_at: string | null;
  elapsed_seconds: number | null;
  created_at: string | null;
}

export interface LocationTimeSummaryItem {
  location_code: string;
  total_elapsed_seconds: number;
  scan_count: number;
  avg_elapsed_seconds: number;
}

export interface TimeSummary {
  total_elapsed_seconds: number;
  total_scans: number;
  avg_elapsed_seconds: number;
  by_location: LocationTimeSummaryItem[];
  records: LocationScan[];
}

// ============================================
// SHARED TYPES
// ============================================

export interface Pagination {
  page: number;
  page_size: number;
  total_items: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}
```

## API Service Implementations

### Layout Service

```typescript
// services/layoutService.ts

import axios from "axios";
import type {
  CreateLocationRequest,
  UpdateLocationRequest,
  WarehouseLocation,
  LocationTree,
  LocationSummary,
  PaginatedLocations,
} from "../types/wms.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class LayoutService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async createLocation(
    data: CreateLocationRequest,
  ): Promise<WarehouseLocation> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/warehouse-locations`,
      data,
      {
        headers: this.getHeaders(),
      },
    );
    return res.data;
  }

  async getTree(warehouseId: string): Promise<LocationTree[]> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/warehouse-locations/tree/${warehouseId}`,
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async listLocations(params: {
    warehouse_id: string;
    location_type?: string;
    parent_location_id?: string;
    is_active?: boolean;
    has_stock?: boolean;
    page?: number;
    page_size?: number;
  }): Promise<PaginatedLocations> {
    const res = await axios.get(`${API_BASE_URL}/api/v1/warehouse-locations`, {
      headers: this.getHeaders(),
      params,
    });
    return res.data;
  }

  async getLocation(locationId: string): Promise<WarehouseLocation> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/warehouse-locations/${locationId}`,
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async updateLocation(
    locationId: string,
    data: UpdateLocationRequest,
  ): Promise<WarehouseLocation> {
    const res = await axios.patch(
      `${API_BASE_URL}/api/v1/warehouse-locations/${locationId}`,
      data,
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async deactivateLocation(locationId: string): Promise<WarehouseLocation> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/warehouse-locations/${locationId}/deactivate`,
      {},
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async getLocationSummary(locationId: string): Promise<LocationSummary> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/warehouse-locations/${locationId}/summary`,
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async searchLocations(
    warehouseId: string,
    query: string,
    limit = 20,
  ): Promise<WarehouseLocation[]> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/warehouse-locations/search`,
      {
        headers: this.getHeaders(),
        params: { warehouse_id: warehouseId, q: query, limit },
      },
    );
    return res.data;
  }
}

export const layoutService = new LayoutService();
```

### Inbound Service

```typescript
// services/inboundService.ts

import axios from "axios";
import type {
  StartSessionRequest,
  RecordScanRequest,
  ScanSession,
  ScanResult,
  SessionSummary,
  ReceivingSlip,
} from "../types/wms.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class InboundService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async startSession(data: StartSessionRequest): Promise<ScanSession> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/inbound/sessions`,
      data,
      {
        headers: this.getHeaders(),
      },
    );
    return res.data;
  }

  async recordScan(
    sessionId: string,
    data: RecordScanRequest,
  ): Promise<ScanResult> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/inbound/sessions/${sessionId}/scan`,
      data,
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async endSession(sessionId: string): Promise<ReceivingSlip> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/inbound/sessions/${sessionId}/end`,
      {},
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async getSessionSummary(sessionId: string): Promise<SessionSummary> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/inbound/sessions/${sessionId}/summary`,
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async getReceivingSlip(slipId: string): Promise<ReceivingSlip> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/inbound/receiving-slips/${slipId}`,
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async approveSlip(slipId: string, workerId?: string): Promise<ReceivingSlip> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/inbound/receiving-slips/${slipId}/approve`,
      workerId ? { worker_id: workerId } : {},
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async rejectSlip(slipId: string, reason: string): Promise<ReceivingSlip> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/inbound/receiving-slips/${slipId}/reject`,
      { reason },
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async flagLineItem(
    slipId: string,
    itemId: string,
    flag: "short" | "damaged",
    notes?: string,
  ): Promise<any> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/inbound/receiving-slips/${slipId}/items/${itemId}/flag`,
      { flag, notes },
      { headers: this.getHeaders() },
    );
    return res.data;
  }
}

export const inboundService = new InboundService();
```

### Outbound Service

```typescript
// services/outboundService.ts

import axios from "axios";
import type {
  SAPInvoicePayload,
  PickList,
  PickScanResult,
  GateSessionRequest,
  GateSession,
  GateScanResult,
  GateSessionProgress,
  DispatchRecord,
  DispatchListResponse,
} from "../types/wms.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class OutboundService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  // --- Pick Lists ---

  async createFromInvoice(data: SAPInvoicePayload): Promise<PickList> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/outbound/from-invoice`,
      data,
      {
        headers: this.getHeaders(),
      },
    );
    return res.data;
  }

  async listPickLists(params?: {
    status?: string;
    warehouse_id?: string;
    invoice_reference?: string;
    sort_by?: string;
    sort_order?: string;
    page?: number;
    page_size?: number;
  }): Promise<{ pick_lists: any[]; pagination: any }> {
    const res = await axios.get(`${API_BASE_URL}/api/v1/outbound`, {
      headers: this.getHeaders(),
      params,
    });
    return res.data;
  }

  async getPickList(pickListId: string): Promise<PickList> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/outbound/${pickListId}`,
      {
        headers: this.getHeaders(),
      },
    );
    return res.data;
  }

  async recordPickScan(
    pickListId: string,
    qrData: string,
  ): Promise<PickScanResult> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/outbound/${pickListId}/scan`,
      { qr_data: qrData },
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async completePickList(pickListId: string): Promise<PickList> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/outbound/${pickListId}/complete`,
      {},
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async cancelPickList(pickListId: string): Promise<PickList> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/outbound/${pickListId}/cancel`,
      {},
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  // --- Gate Verification ---

  async startGateSession(data: GateSessionRequest): Promise<GateSession> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/outbound/gate-sessions`,
      data,
      {
        headers: this.getHeaders(),
      },
    );
    return res.data;
  }

  async recordGateScan(
    sessionId: string,
    qrData: string,
    deviceType?: string,
    os?: string,
  ): Promise<GateScanResult> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/outbound/gate-sessions/${sessionId}/scan`,
      { qr_data: qrData, device_type: deviceType, os },
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async getGateSessionProgress(
    sessionId: string,
  ): Promise<GateSessionProgress> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/outbound/gate-sessions/${sessionId}/progress`,
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async verifyGateSession(sessionId: string): Promise<GateSession> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/outbound/gate-sessions/${sessionId}/verify`,
      {},
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  // --- Dispatches ---

  async createDispatch(gateSessionId: string): Promise<DispatchRecord> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/outbound/dispatches`,
      { gate_session_id: gateSessionId },
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async listDispatches(params?: {
    date_from?: string;
    date_to?: string;
    vehicle_number?: string;
    invoice_reference?: string;
    page?: number;
    page_size?: number;
  }): Promise<DispatchListResponse> {
    const res = await axios.get(`${API_BASE_URL}/api/v1/outbound/dispatches`, {
      headers: this.getHeaders(),
      params,
    });
    return res.data;
  }

  async getDispatch(dispatchId: string): Promise<DispatchRecord> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/outbound/dispatches/${dispatchId}`,
      { headers: this.getHeaders() },
    );
    return res.data;
  }
}

export const outboundService = new OutboundService();
```

### Worker Task Service

```typescript
// services/workerTaskService.ts

import axios from "axios";
import type {
  WorkerTaskCreate,
  WorkerTask,
  WorkerTaskListResponse,
} from "../types/wms.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class WorkerTaskService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async createTask(data: WorkerTaskCreate): Promise<WorkerTask> {
    const res = await axios.post(`${API_BASE_URL}/api/v1/worker-tasks`, data, {
      headers: this.getHeaders(),
    });
    return res.data;
  }

  async listTasks(params: {
    worker_id: string;
    status?: string;
    date_from?: string;
    date_to?: string;
    page?: number;
    page_size?: number;
  }): Promise<WorkerTaskListResponse> {
    const res = await axios.get(`${API_BASE_URL}/api/v1/worker-tasks`, {
      headers: this.getHeaders(),
      params,
    });
    return res.data;
  }

  async getTask(taskId: string): Promise<WorkerTask> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/worker-tasks/${taskId}`,
      {
        headers: this.getHeaders(),
      },
    );
    return res.data;
  }

  async startTask(taskId: string): Promise<WorkerTask> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/worker-tasks/${taskId}/start`,
      {},
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async completeTask(taskId: string): Promise<WorkerTask> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/worker-tasks/${taskId}/complete`,
      {},
      { headers: this.getHeaders() },
    );
    return res.data;
  }

  async cancelTask(taskId: string): Promise<WorkerTask> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/worker-tasks/${taskId}/cancel`,
      {},
      { headers: this.getHeaders() },
    );
    return res.data;
  }
}

export const workerTaskService = new WorkerTaskService();
```

### Location Scan Service

```typescript
// services/locationScanService.ts

import axios from "axios";
import type {
  LocationScanRequest,
  LocationScan,
  TimeSummary,
} from "../types/wms.types";

const API_BASE_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

class LocationScanService {
  private getHeaders() {
    const token = localStorage.getItem("token");
    return {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };
  }

  async recordScan(data: LocationScanRequest): Promise<LocationScan> {
    const res = await axios.post(
      `${API_BASE_URL}/api/v1/location-scans`,
      data,
      {
        headers: this.getHeaders(),
      },
    );
    return res.data;
  }

  async getTimeSummary(params?: {
    worker_id?: string;
    task_id?: string;
    location_code?: string;
    date_from?: string;
    date_to?: string;
  }): Promise<TimeSummary> {
    const res = await axios.get(
      `${API_BASE_URL}/api/v1/location-scans/summary`,
      {
        headers: this.getHeaders(),
        params,
      },
    );
    return res.data;
  }
}

export const locationScanService = new LocationScanService();
```

## React Hooks

### Inbound Session Hook

```typescript
// hooks/useInboundSession.ts

import { useState } from "react";
import { inboundService } from "../services/inboundService";
import type {
  ScanSession,
  ScanResult,
  SessionSummary,
  ReceivingSlip,
} from "../types/wms.types";

export const useInboundSession = () => {
  const [session, setSession] = useState<ScanSession | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startSession = async (warehouseId: string, dockLocation?: string) => {
    setLoading(true);
    setError(null);
    try {
      const result = await inboundService.startSession({
        warehouse_id: warehouseId,
        dock_location: dockLocation,
      });
      setSession(result);
      return result;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to start session");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const recordScan = async (qrData: string): Promise<ScanResult> => {
    if (!session) throw new Error("No active session");
    setError(null);
    try {
      const result = await inboundService.recordScan(session.id, {
        qr_data: qrData,
      });
      setSession((prev) =>
        prev
          ? { ...prev, total_boxes_scanned: result.total_boxes_scanned }
          : prev,
      );
      return result;
    } catch (err: any) {
      const msg = err.response?.data?.detail || "Scan failed";
      setError(msg);
      throw err;
    }
  };

  const endSession = async (): Promise<ReceivingSlip> => {
    if (!session) throw new Error("No active session");
    setLoading(true);
    setError(null);
    try {
      const slip = await inboundService.endSession(session.id);
      setSession((prev) =>
        prev ? { ...prev, status: "closed" as const } : prev,
      );
      return slip;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to end session");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const getSummary = async (): Promise<SessionSummary | null> => {
    if (!session) return null;
    try {
      return await inboundService.getSessionSummary(session.id);
    } catch {
      return null;
    }
  };

  return {
    session,
    loading,
    error,
    startSession,
    recordScan,
    endSession,
    getSummary,
  };
};
```

### Pick List Hook

```typescript
// hooks/usePickLists.ts

import { useState, useEffect } from "react";
import { outboundService } from "../services/outboundService";
import type { PickList, PickScanResult } from "../types/wms.types";

export const usePickList = (pickListId: string | null) => {
  const [pickList, setPickList] = useState<PickList | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPickList = async () => {
    if (!pickListId) return;
    setLoading(true);
    try {
      const data = await outboundService.getPickList(pickListId);
      setPickList(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to fetch pick list");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPickList();
  }, [pickListId]);

  const recordScan = async (qrData: string): Promise<PickScanResult> => {
    if (!pickListId) throw new Error("No pick list selected");
    setError(null);
    try {
      const result = await outboundService.recordPickScan(pickListId, qrData);
      await fetchPickList(); // Refresh progress
      return result;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Pick scan failed");
      throw err;
    }
  };

  const complete = async () => {
    if (!pickListId) throw new Error("No pick list selected");
    setLoading(true);
    setError(null);
    try {
      const result = await outboundService.completePickList(pickListId);
      setPickList(result);
      return result;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to complete pick list");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const cancel = async () => {
    if (!pickListId) throw new Error("No pick list selected");
    setLoading(true);
    try {
      const result = await outboundService.cancelPickList(pickListId);
      setPickList(result);
      return result;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to cancel pick list");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    pickList,
    loading,
    error,
    refetch: fetchPickList,
    recordScan,
    complete,
    cancel,
  };
};
```

### Gate Verification Hook

```typescript
// hooks/useGateVerification.ts

import { useState } from "react";
import { outboundService } from "../services/outboundService";
import type {
  GateSession,
  GateScanResult,
  GateSessionProgress,
} from "../types/wms.types";

export const useGateVerification = () => {
  const [session, setSession] = useState<GateSession | null>(null);
  const [progress, setProgress] = useState<GateSessionProgress | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startSession = async (
    pickListId: string,
    vehicleNumber?: string,
    driverName?: string,
    driverContact?: string,
  ) => {
    setLoading(true);
    setError(null);
    try {
      const result = await outboundService.startGateSession({
        pick_list_id: pickListId,
        vehicle_number: vehicleNumber,
        driver_name: driverName,
        driver_contact: driverContact,
      });
      setSession(result);
      return result;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to start gate session");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  const recordScan = async (qrData: string): Promise<GateScanResult> => {
    if (!session) throw new Error("No active gate session");
    setError(null);
    try {
      const result = await outboundService.recordGateScan(session.id, qrData);
      // Refresh progress
      const prog = await outboundService.getGateSessionProgress(session.id);
      setProgress(prog);
      return result;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Gate scan failed");
      throw err;
    }
  };

  const verify = async (): Promise<GateSession> => {
    if (!session) throw new Error("No active gate session");
    setLoading(true);
    setError(null);
    try {
      const result = await outboundService.verifyGateSession(session.id);
      setSession(result);
      return result;
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to verify gate session");
      throw err;
    } finally {
      setLoading(false);
    }
  };

  return {
    session,
    progress,
    loading,
    error,
    startSession,
    recordScan,
    verify,
  };
};
```

### Location Tree Hook

```typescript
// hooks/useLocationTree.ts

import { useState, useEffect } from "react";
import { layoutService } from "../services/layoutService";
import type { LocationTree } from "../types/wms.types";

export const useLocationTree = (warehouseId: string | null) => {
  const [tree, setTree] = useState<LocationTree[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTree = async () => {
    if (!warehouseId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await layoutService.getTree(warehouseId);
      setTree(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || "Failed to load location tree");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTree();
  }, [warehouseId]);

  return { tree, loading, error, refetch: fetchTree };
};
```

## Component Examples

### Location Tree Component

```typescript
// components/layout/LocationTree.tsx

import React, { useState } from "react";
import { useLocationTree } from "../../hooks/useLocationTree";
import { LocationTypeBadge } from "./LocationTypeBadge";
import { CapacityBar } from "./CapacityBar";
import type { LocationTree as LocationTreeType } from "../../types/wms.types";

interface LocationTreeProps {
  warehouseId: string;
  onSelect?: (location: LocationTreeType) => void;
}

const TreeNode: React.FC<{
  node: LocationTreeType;
  depth: number;
  onSelect?: (location: LocationTreeType) => void;
}> = ({ node, depth, onSelect }) => {
  const [expanded, setExpanded] = useState(depth < 2);
  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className="tree-node" style={{ paddingLeft: `${depth * 20}px` }}>
      <div
        className={`tree-node-row flex items-center gap-2 py-1 px-2 rounded hover:bg-gray-50 cursor-pointer ${!node.is_active ? "opacity-50" : ""}`}
        onClick={() => onSelect?.(node)}
      >
        {hasChildren && (
          <button
            onClick={(e) => { e.stopPropagation(); setExpanded(!expanded); }}
            className="text-gray-400 w-5"
          >
            {expanded ? "▼" : "▶"}
          </button>
        )}
        {!hasChildren && <span className="w-5" />}

        <LocationTypeBadge type={node.location_type} />
        <span className="font-mono text-sm">{node.code}</span>
        {node.name && <span className="text-gray-500 text-sm">— {node.name}</span>}

        {node.location_type === "bin" && (
          <CapacityBar
            total={node.total_capacity}
            available={node.available_capacity}
            className="ml-auto w-24"
          />
        )}
      </div>

      {expanded && hasChildren && (
        <div>
          {node.children.map((child) => (
            <TreeNode key={child.id} node={child} depth={depth + 1} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
};

export const LocationTreeView: React.FC<LocationTreeProps> = ({ warehouseId, onSelect }) => {
  const { tree, loading, error } = useLocationTree(warehouseId);

  if (loading) return <div className="p-4 text-gray-500">Loading warehouse layout...</div>;
  if (error) return <div className="p-4 text-red-500">Error: {error}</div>;
  if (tree.length === 0) return <div className="p-4 text-gray-400">No locations defined yet</div>;

  return (
    <div className="location-tree border rounded-lg p-4 bg-white">
      <h3 className="text-lg font-semibold mb-3">Warehouse Layout</h3>
      {tree.map((node) => (
        <TreeNode key={node.id} node={node} depth={0} onSelect={onSelect} />
      ))}
    </div>
  );
};
```

### Inbound Scan Session Panel

```typescript
// components/inbound/ScanSessionPanel.tsx

import React, { useState } from "react";
import { useInboundSession } from "../../hooks/useInboundSession";
import type { ScanResult } from "../../types/wms.types";

interface ScanSessionPanelProps {
  warehouseId: string;
  onSlipGenerated?: (slipId: string) => void;
}

export const ScanSessionPanel: React.FC<ScanSessionPanelProps> = ({
  warehouseId,
  onSlipGenerated,
}) => {
  const { session, loading, error, startSession, recordScan, endSession } = useInboundSession();
  const [qrInput, setQrInput] = useState("");
  const [scans, setScans] = useState<ScanResult[]>([]);
  const [scanError, setScanError] = useState<string | null>(null);
  const [dockLocation, setDockLocation] = useState("");

  const handleStart = async () => {
    await startSession(warehouseId, dockLocation || undefined);
  };

  const handleScan = async () => {
    if (!qrInput.trim()) return;
    setScanError(null);
    try {
      const result = await recordScan(qrInput);
      setScans((prev) => [result, ...prev]);
      setQrInput("");
    } catch (err: any) {
      setScanError(err.response?.data?.detail || "Scan failed");
    }
  };

  const handleEnd = async () => {
    try {
      const slip = await endSession();
      onSlipGenerated?.(slip.id);
    } catch {}
  };

  // Not started yet
  if (!session) {
    return (
      <div className="p-6 bg-white rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Start Inbound Session</h2>
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-1">Dock Location (optional)</label>
          <input
            type="text"
            value={dockLocation}
            onChange={(e) => setDockLocation(e.target.value)}
            placeholder="e.g., Dock A, Bay 3"
            className="w-full border rounded px-3 py-2"
          />
        </div>
        {error && <div className="text-red-500 text-sm mb-3">{error}</div>}
        <button onClick={handleStart} disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:opacity-50">
          {loading ? "Starting..." : "Start Session"}
        </button>
      </div>
    );
  }

  // Active session
  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Inbound Scanning</h2>
        <div className="flex items-center gap-3">
          <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-medium">
            {session.total_boxes_scanned} boxes scanned
          </span>
          <button
            onClick={handleEnd}
            disabled={loading || session.total_boxes_scanned === 0}
            className="bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700 disabled:opacity-50"
          >
            End Session
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={qrInput}
          onChange={(e) => setQrInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleScan()}
          placeholder="Scan or paste QR code data..."
          className="flex-1 border rounded px-3 py-2 font-mono text-sm"
          autoFocus
        />
        <button onClick={handleScan} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
          Scan
        </button>
      </div>

      {scanError && <div className="text-red-500 text-sm mb-3 bg-red-50 p-2 rounded">{scanError}</div>}
      {error && <div className="text-red-500 text-sm mb-3">{error}</div>}

      {scans.length > 0 && (
        <div className="border rounded overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="text-left px-3 py-2">SKU</th>
                <th className="text-left px-3 py-2">Qty</th>
                <th className="text-left px-3 py-2">Batch</th>
                <th className="text-left px-3 py-2">Time</th>
              </tr>
            </thead>
            <tbody>
              {scans.map((scan) => (
                <tr key={scan.scan_item_id} className="border-t">
                  <td className="px-3 py-2 font-mono">{scan.sku}</td>
                  <td className="px-3 py-2">{scan.quantity}</td>
                  <td className="px-3 py-2">{scan.batch_number}</td>
                  <td className="px-3 py-2 text-gray-500">{scan.scanned_at}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
```

### Pick List Detail with Progress

```typescript
// components/outbound/PickListDetail.tsx

import React from "react";
import { usePickList } from "../../hooks/usePickLists";
import type { PickListItem } from "../../types/wms.types";

interface PickListDetailProps {
  pickListId: string;
  onScanClick?: () => void;
}

export const PickListDetail: React.FC<PickListDetailProps> = ({ pickListId, onScanClick }) => {
  const { pickList, loading, error, complete, cancel } = usePickList(pickListId);

  if (loading) return <div className="p-4">Loading pick list...</div>;
  if (error) return <div className="p-4 text-red-500">{error}</div>;
  if (!pickList) return null;

  const { progress } = pickList;
  const canComplete = pickList.status === "in_progress" && progress?.remaining_items === 0;
  const canScan = pickList.status === "draft" || pickList.status === "in_progress";
  const canCancel = pickList.status !== "completed" && pickList.status !== "cancelled";

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <div className="flex justify-between items-start mb-6">
        <div>
          <h2 className="text-xl font-semibold">{pickList.pick_list_no}</h2>
          {pickList.invoice_reference && (
            <p className="text-gray-500 text-sm">Invoice: {pickList.invoice_reference}</p>
          )}
        </div>
        <span className={`px-3 py-1 rounded-full text-sm font-medium ${
          pickList.status === "completed" ? "bg-green-100 text-green-800" :
          pickList.status === "in_progress" ? "bg-blue-100 text-blue-800" :
          pickList.status === "cancelled" ? "bg-red-100 text-red-800" :
          "bg-gray-100 text-gray-800"
        }`}>
          {pickList.status.replace("_", " ").toUpperCase()}
        </span>
      </div>

      {/* Progress Bar */}
      {progress && (
        <div className="mb-6">
          <div className="flex justify-between text-sm text-gray-600 mb-1">
            <span>{progress.picked_items} of {progress.total_items} items picked</span>
            <span>{progress.completion_percentage}%</span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-3">
            <div
              className="bg-blue-600 h-3 rounded-full transition-all"
              style={{ width: `${progress.completion_percentage}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>Qty: {progress.picked_qty} / {progress.total_qty}</span>
            <span>Remaining: {progress.remaining_qty}</span>
          </div>
        </div>
      )}

      {/* Items Table */}
      <table className="w-full text-sm border rounded overflow-hidden mb-4">
        <thead className="bg-gray-50">
          <tr>
            <th className="text-left px-3 py-2">#</th>
            <th className="text-left px-3 py-2">Item</th>
            <th className="text-left px-3 py-2">Bin</th>
            <th className="text-right px-3 py-2">Required</th>
            <th className="text-right px-3 py-2">Picked</th>
            <th className="text-left px-3 py-2">Status</th>
          </tr>
        </thead>
        <tbody>
          {pickList.items.map((item, idx) => (
            <tr key={item.id} className="border-t">
              <td className="px-3 py-2 text-gray-400">{item.sort_order || idx + 1}</td>
              <td className="px-3 py-2 font-mono">{item.item_id}</td>
              <td className="px-3 py-2 font-mono text-xs">{item.bin_location_id || "—"}</td>
              <td className="px-3 py-2 text-right">{item.qty}</td>
              <td className="px-3 py-2 text-right font-semibold">{item.picked_qty}</td>
              <td className="px-3 py-2">
                {item.picked_qty >= item.qty ? (
                  <span className="text-green-600">✓ Done</span>
                ) : item.picked_qty > 0 ? (
                  <span className="text-blue-600">Partial</span>
                ) : (
                  <span className="text-gray-400">Pending</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Actions */}
      <div className="flex gap-3">
        {canScan && (
          <button onClick={onScanClick} className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
            Start Scanning
          </button>
        )}
        {canComplete && (
          <button onClick={complete} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
            Mark Complete
          </button>
        )}
        {canCancel && (
          <button onClick={cancel} className="border border-red-300 text-red-600 px-4 py-2 rounded hover:bg-red-50">
            Cancel
          </button>
        )}
      </div>
    </div>
  );
};
```

### Gate Verification Panel

```typescript
// components/gate/GateSessionPanel.tsx

import React, { useState } from "react";
import { useGateVerification } from "../../hooks/useGateVerification";

interface GateSessionPanelProps {
  pickListId: string;
  onDispatchCreated?: (dispatchId: string) => void;
}

export const GateSessionPanel: React.FC<GateSessionPanelProps> = ({
  pickListId,
  onDispatchCreated,
}) => {
  const { session, progress, loading, error, startSession, recordScan, verify } = useGateVerification();
  const [qrInput, setQrInput] = useState("");
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [driverName, setDriverName] = useState("");
  const [lastScanStatus, setLastScanStatus] = useState<"verified" | "unauthorized" | null>(null);

  const handleStart = async () => {
    await startSession(pickListId, vehicleNumber || undefined, driverName || undefined);
  };

  const handleScan = async () => {
    if (!qrInput.trim()) return;
    try {
      const result = await recordScan(qrInput);
      setLastScanStatus(result.status);
      setQrInput("");
    } catch {}
  };

  const handleVerify = async () => {
    const result = await verify();
    if (result.dispatch) {
      onDispatchCreated?.(result.dispatch.id);
    }
  };

  if (!session) {
    return (
      <div className="p-6 bg-white rounded-lg shadow">
        <h2 className="text-xl font-semibold mb-4">Start Gate Verification</h2>
        <div className="grid grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-sm font-medium mb-1">Vehicle Number</label>
            <input type="text" value={vehicleNumber} onChange={(e) => setVehicleNumber(e.target.value)} className="w-full border rounded px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Driver Name</label>
            <input type="text" value={driverName} onChange={(e) => setDriverName(e.target.value)} className="w-full border rounded px-3 py-2" />
          </div>
        </div>
        {error && <div className="text-red-500 text-sm mb-3">{error}</div>}
        <button onClick={handleStart} disabled={loading} className="bg-blue-600 text-white px-4 py-2 rounded">
          {loading ? "Starting..." : "Start Verification"}
        </button>
      </div>
    );
  }

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-semibold">Gate Verification</h2>
        {progress && (
          <span className="text-sm text-gray-600">
            {progress.verified_count} / {progress.expected_total_qty} verified
          </span>
        )}
      </div>

      {progress && progress.unauthorized_count > 0 && (
        <div className="bg-red-50 border border-red-200 rounded p-3 mb-4 text-red-700 text-sm">
          ⚠️ {progress.unauthorized_count} unauthorized item(s) detected
        </div>
      )}

      <div className="flex gap-2 mb-4">
        <input
          type="text"
          value={qrInput}
          onChange={(e) => setQrInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleScan()}
          placeholder="Scan item QR code..."
          className="flex-1 border rounded px-3 py-2 font-mono text-sm"
          autoFocus
        />
        <button onClick={handleScan} className="bg-blue-600 text-white px-4 py-2 rounded">Scan</button>
      </div>

      {lastScanStatus && (
        <div className={`mb-4 p-2 rounded text-sm ${lastScanStatus === "verified" ? "bg-green-50 text-green-700" : "bg-red-50 text-red-700"}`}>
          Last scan: {lastScanStatus === "verified" ? "✓ Verified" : "✗ UNAUTHORIZED"}
        </div>
      )}

      {error && <div className="text-red-500 text-sm mb-3">{error}</div>}

      {progress?.all_verified && (
        <button onClick={handleVerify} disabled={loading} className="bg-green-600 text-white px-4 py-2 rounded w-full">
          {loading ? "Verifying..." : "Complete Verification & Create Dispatch"}
        </button>
      )}
    </div>
  );
};
```

## QR Payload Format

The backend expects QR codes to contain a JSON payload:

```json
{
  "id": "unique-qr-identifier",
  "sku": "ITEM-001",
  "qty": 50,
  "batch": "BATCH-2025-01"
}
```

### QR Payload Parser Utility

```typescript
// utils/qrPayloadParser.ts

export interface QRPayload {
  id: string;
  sku: string;
  qty: number;
  batch: string;
}

export const parseQRPayload = (raw: string): QRPayload | null => {
  try {
    const data = JSON.parse(raw);
    if (!data.id || !data.sku || !data.qty || !data.batch) return null;
    if (typeof data.qty !== "number" || data.qty <= 0) return null;
    return { id: data.id, sku: data.sku, qty: data.qty, batch: data.batch };
  } catch {
    return null;
  }
};

export const isValidQRPayload = (raw: string): boolean => {
  return parseQRPayload(raw) !== null;
};
```

## Status Transition Reference

### Receiving Slip

| From            | To               | Trigger                 |
| --------------- | ---------------- | ----------------------- |
| pending_review  | pending_putaway  | Manager approves        |
| pending_review  | rejected         | Manager rejects         |
| pending_putaway | putaway_complete | All put-away items done |

### Pick List

| From        | To          | Trigger                    |
| ----------- | ----------- | -------------------------- |
| draft       | in_progress | First pick scan recorded   |
| draft       | cancelled   | Manual cancel              |
| in_progress | completed   | All items picked + confirm |
| in_progress | cancelled   | Manual cancel              |

### Gate Verification Session

| From | To        | Trigger                     |
| ---- | --------- | --------------------------- |
| open | verified  | All pick list items scanned |
| open | cancelled | Manual cancel               |

### Worker Task

| From        | To          | Trigger            |
| ----------- | ----------- | ------------------ |
| assigned    | in_progress | Worker starts      |
| assigned    | cancelled   | Supervisor cancels |
| in_progress | completed   | All items done     |
| in_progress | cancelled   | Supervisor cancels |

## Error Handling Reference

### Validation Errors (422)

| Scenario                              | Error Detail                                                                             |
| ------------------------------------- | ---------------------------------------------------------------------------------------- |
| QR payload missing SKU                | `"Invalid QR payload: missing SKU identifier"`                                           |
| QR payload invalid quantity           | `"Invalid QR payload: quantity must be a positive integer"`                              |
| Duplicate QR scan in session          | `"QR code already scanned in this session (ID: {qr_identifier})"`                        |
| Pick scan item not on list            | `"Scanned item (SKU: {sku}) is not on this pick list"`                                   |
| Pick scan over-picking                | `"Over-pick: scanned qty ({qty}) would exceed required qty ({required}) for item {sku}"` |
| Gate scan unauthorized item           | `"Unauthorized item: SKU {sku} is not on the associated pick list"`                      |
| Invalid parent type for location      | `"A {type} must have a {expected_parent} as parent, got {actual_parent}"`                |
| Bin capacity exceeded                 | `"Cannot add {qty} to bin {code}: available capacity is {available}"`                    |
| Stock removal exceeds on-hand         | `"Cannot remove {qty} from bin {code}: only {on_hand} on hand"`                          |
| Finish scan without start             | `"Cannot record finish scan: no start scan found for task item {id}"`                    |
| Overlapping exclusive allocation      | `"Location {code} already has an exclusive allocation for item group {group}"`           |
| Deactivated location stock assignment | `"Cannot assign stock to deactivated location {code}"`                                   |

### Not Found Errors (404)

| Scenario                  | Error Detail                                         |
| ------------------------- | ---------------------------------------------------- |
| Location not found        | `"Warehouse location with ID {id} not found"`        |
| Session not found         | `"Scan session with ID {id} not found"`              |
| Receiving slip not found  | `"Receiving slip with ID {id} not found"`            |
| Pick list not found       | `"Pick list with ID {id} not found"`                 |
| Gate session not found    | `"Gate verification session with ID {id} not found"` |
| Dispatch record not found | `"Dispatch record with ID {id} not found"`           |
| Worker task not found     | `"Worker task with ID {id} not found"`               |

### Conflict Errors (409)

| Scenario                            | Error Detail                                                                  |
| ----------------------------------- | ----------------------------------------------------------------------------- |
| Session already closed              | `"Session is already closed"`                                                 |
| Pick list wrong status for scan     | `"Pick list must be OPEN or IN_PROGRESS to accept scans (current: {status})"` |
| Pick list wrong status for complete | `"Pick list must be IN_PROGRESS to be completed (current: {status})"`         |
| Gate session already verified       | `"Gate session is already verified"`                                          |
| Slip already approved/rejected      | `"Receiving slip has already been {status}"`                                  |
| Task already started                | `"Task is already in progress"`                                               |
| Concurrent capacity conflict        | `"Capacity conflict detected, please retry"`                                  |

## Location Hierarchy Rules

The warehouse layout follows a strict parent-child hierarchy:

```
warehouse → zone → aisle → bay → level → bin
```

**Valid parent types:**

| Location Type | Required Parent Type |
| ------------- | -------------------- |
| zone          | warehouse (root)     |
| aisle         | zone                 |
| bay           | aisle                |
| level         | bay                  |
| bin           | level                |

**Location code generation:**

Codes are concatenated from ancestors: `Z01-A03-B02-L04-B01`

**Capacity rollup:**

- Bin capacity is set manually
- Level capacity = sum of all child bin capacities
- Bay capacity = sum of all child level capacities
- Aisle capacity = sum of all child bay capacities
- Zone capacity = sum of all child aisle capacities
- Warehouse capacity = sum of all child zone capacities

## Tailwind CSS Styling Patterns

### Status Badges

```typescript
// utils/statusHelpers.ts

export const getStatusClasses = (status: string): string => {
  const map: Record<string, string> = {
    // Receiving slip
    pending_review: "bg-yellow-100 text-yellow-800",
    pending_putaway: "bg-blue-100 text-blue-800",
    putaway_complete: "bg-green-100 text-green-800",
    rejected: "bg-red-100 text-red-800",
    // Pick list
    draft: "bg-gray-100 text-gray-800",
    in_progress: "bg-blue-100 text-blue-800",
    completed: "bg-green-100 text-green-800",
    cancelled: "bg-red-100 text-red-800",
    // Gate
    open: "bg-yellow-100 text-yellow-800",
    verified: "bg-green-100 text-green-800",
    // Worker task
    assigned: "bg-purple-100 text-purple-800",
    // Scan result
    unauthorized: "bg-red-100 text-red-800",
  };
  return map[status] || "bg-gray-100 text-gray-800";
};

export const getLocationTypeClasses = (type: string): string => {
  const map: Record<string, string> = {
    zone: "bg-indigo-100 text-indigo-800",
    aisle: "bg-cyan-100 text-cyan-800",
    bay: "bg-amber-100 text-amber-800",
    level: "bg-lime-100 text-lime-800",
    bin: "bg-emerald-100 text-emerald-800",
  };
  return map[type] || "bg-gray-100 text-gray-800";
};
```

### Capacity Bar

```typescript
// utils/capacityHelpers.ts

export const getCapacityPercentage = (
  total: number,
  available: number,
): number => {
  if (total === 0) return 0;
  return Math.round(((total - available) / total) * 100);
};

export const getCapacityColor = (percentage: number): string => {
  if (percentage >= 90) return "bg-red-500";
  if (percentage >= 70) return "bg-yellow-500";
  return "bg-green-500";
};
```

## Testing Checklist

### Layout Management

- [ ] Create zone, aisle, bay, level, bin in correct hierarchy
- [ ] Reject invalid parent-child relationships
- [ ] View full location tree
- [ ] Search locations by code or name
- [ ] Filter locations by type, active status, has_stock
- [ ] View location summary (bins, capacity, stock)
- [ ] Deactivate location (cascades to children)
- [ ] Update location capacity (triggers rollup)

### Bin Stock

- [ ] Add stock to a bin
- [ ] Remove stock from a bin
- [ ] View all stock in a bin
- [ ] View all bins containing a specific item
- [ ] Reject stock addition exceeding bin capacity
- [ ] Reject stock addition to deactivated bin

### Inbound Flow

- [ ] Start inbound scan session
- [ ] Scan QR codes (show running count)
- [ ] Reject duplicate QR scans (show warning)
- [ ] End session → generates receiving slip
- [ ] View session summary (per-SKU/batch breakdown)
- [ ] Approve receiving slip → triggers put-away
- [ ] Reject receiving slip with reason
- [ ] Flag line items as SHORT or DAMAGED

### Put-Away

- [ ] View put-away list with optimized route order
- [ ] Mark put-away items as completed
- [ ] Skip items with reason
- [ ] Verify stock updates after completion

### Outbound Picking

- [ ] Create pick list from SAP invoice payload
- [ ] View pick list with progress bar
- [ ] Scan items against pick list
- [ ] Reject scans for items not on list
- [ ] Reject over-picking
- [ ] Complete pick list when all items picked
- [ ] Cancel pick list (releases stock)

### Gate Verification

- [ ] Start gate session with vehicle/driver details
- [ ] Scan items at gate
- [ ] Show verified vs unauthorized status
- [ ] Show progress (scanned vs expected)
- [ ] Verify session when all items scanned
- [ ] Dispatch record created on verification

### Worker Tasks

- [ ] Create and assign tasks
- [ ] Start task (ASSIGNED → IN_PROGRESS)
- [ ] Complete task
- [ ] Cancel task
- [ ] List tasks filtered by worker/status/date

### Time Tracking

- [ ] Record start scan at location
- [ ] Record finish scan (calculates elapsed)
- [ ] Reject finish without preceding start
- [ ] View time summary per worker/task/location

## Best Practices

1. **QR Scanner Integration**: Use a camera-based QR scanner library (e.g., `react-qr-reader` or `html5-qrcode`) for mobile workers. Fall back to manual text input for desktop.
2. **Offline Support**: Cache scan data locally (IndexedDB) and sync when connectivity is restored. The QR payload is self-contained — no server lookup needed to decode.
3. **Real-time Updates**: Use polling or WebSocket for live session progress (scan counts, pick progress).
4. **Optimistic UI**: Show scan results immediately, revert on error.
5. **Sound/Haptic Feedback**: Play success/error sounds on scan to give workers immediate feedback without looking at the screen.
6. **Large Lists**: Use virtual scrolling for location trees and pick lists with many items.
7. **Mobile-First**: The inbound scanning, picking, and gate verification UIs should be designed for tablet/mobile use.
8. **Confirmation Dialogs**: Confirm before ending sessions, completing pick lists, or verifying gate sessions.
9. **Error Recovery**: On duplicate scan, show which box was already scanned. On over-pick, show remaining quantity.
10. **Accessibility**: Ensure all scan inputs are keyboard-navigable and screen-reader friendly.

## Environment Variables

```env
REACT_APP_API_URL=http://localhost:8001
```

## Support & Resources

- Swagger UI: http://localhost:8001/docs
- Backend logs: `docker compose logs core-service`
- Layout endpoints: `core-service/app/api/v1/endpoints/warehouse_locations.py`
- Inbound endpoints: `core-service/app/api/v1/endpoints/inbound.py`
- Outbound endpoints: `core-service/app/api/v1/endpoints/outbound.py`
- Worker task endpoints: `core-service/app/api/v1/endpoints/worker_tasks.py`
- Location scan endpoints: `core-service/app/api/v1/endpoints/location_scans.py`
- Design document: `.kiro/specs/warehouse-qr-inbound-outbound/design.md`
- Requirements: `.kiro/specs/warehouse-qr-inbound-outbound/requirements.md`
