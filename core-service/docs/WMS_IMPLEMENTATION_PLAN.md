# WMS Implementation Plan — Gap Analysis & Roadmap

> **Date**: 2026-08-04
> **Requirements Source**: `WMS_Client_requriement.md` > **Project**: Horizon Sync WMS (Prestige Warehouse)
> **Backend**: `/Users/devnegi/Documents/www/horizon-sync-be/core-service` > **Frontend**: `/Users/devnegi/Documents/www/common/horizon-sync`

---

## 1. Executive Summary

The WMS codebase already covers **~70%** of the client requirements. The core inbound→putaway→inventory→picking→outbound→dispatch flow is fully implemented in both backend and frontend. The major gaps are: **SAP Integration**, **Cycle Counting**, **Packing Verification**, and **Shipment Staging**.

This document provides a feature-by-feature gap analysis, implementation plan, role-based access control (RBAC) design, and frontend implementation details.

---

## 2. Feature Gap Analysis

### 2.1 INBOUND ASN MANAGEMENT

| Requirement                                                 | Status     | Backend                                                        | Frontend                 |
| ----------------------------------------------------------- | ---------- | -------------------------------------------------------------- | ------------------------ |
| ASN order reception from SAP                                | ⚠️ PARTIAL | ✅ `asn_orders` CRUD exists                                    | ✅ ASN API client exists |
| SAP connector for ASN                                       | ❌ MISSING | Need SAP connector service                                     | —                        |
| CSV upload fallback for pilot                               | ❌ MISSING | Need CSV import endpoint                                       | Need CSV upload UI       |
| Scan-based receiving against ASN                            | ✅ DONE    | ✅ `ScanSession` → `ReceivingSlip`                             | ✅ `InboundScanPanel`    |
| Item classification (matched/short/excess/damaged/rejected) | ✅ DONE    | ✅ Flag items in receiving slips                               | ✅ Status badges exist   |
| Rejection/quarantine location management                    | ⚠️ PARTIAL | Location tree exists, but no dedicated "quarantine zone" logic | Need quarantine view     |
| Receiving record generation                                 | ✅ DONE    | ✅ `ReceivingSlip` with approval flow                          | ✅ `ReceivingSlipList`   |
| Approved quantities → SAP sync                              | ❌ MISSING | Need SAP sync on approval                                      | —                        |

**Gap Action Items**:
| # | Task | Priority | Effort | Story Points |
|---|---|---|---|---|
| I-01 | Build SAP connector service (ASN ingestion + sync) | P0 - Critical | L | 13 |
| I-02 | CSV upload endpoint for ASN (pilot fallback) | P0 - Critical | M | 5 |
| I-03 | Quarantine zone designation in location master | P1 - High | S | 3 |
| I-04 | SAP sync on receiving slip approval | P0 - Critical | M | 8 |
| I-05 | In-transit tracking for dispatched-but-not-received items | P1 - High | M | 8 |

---

### 2.2 INBOUND GOODS RECEIPT

| Requirement                                                    | Status     | Backend                             | Frontend              |
| -------------------------------------------------------------- | ---------- | ----------------------------------- | --------------------- |
| ASN details available before physical receipt                  | ✅ DONE    | ✅ `asn_orders` with item details   | —                     |
| QR scanning per box/package                                    | ✅ DONE    | ✅ `ScanSession` per item QR        | ✅ `InboundScanPanel` |
| Item classification (accepted/damaged/rejected/excess/pending) | ✅ DONE    | ✅ Flag types on receiving items    | ✅ Status badges      |
| Rejected/damaged → quarantine location                         | ⚠️ PARTIAL | Need quarantine movement automation | Need quarantine UI    |
| In-transit/shortage tracking                                   | ❌ MISSING | Need shortage tracking on ASN       | Need shortage view    |
| SAP sync of receipt status                                     | ❌ MISSING | Need SAP sync                       | —                     |

**Gap Action Items**:
| # | Task | Priority | Effort | Story Points |
|---|---|---|---|---|
| I-06 | Auto-move rejected/damaged items to quarantine bin | P1 - High | M | 5 |
| I-07 | Shortage tracking on ASN (dispatched but not received) | P1 - High | M | 8 |
| I-08 | SAP sync for goods receipt confirmation | P0 - Critical | M | 8 |

---

### 2.3 PUTAWAY

| Requirement                                       | Status  | Backend                                   | Frontend                                          |
| ------------------------------------------------- | ------- | ----------------------------------------- | ------------------------------------------------- |
| Directed putaway via Android handheld             | ✅ DONE | ✅ `PutAwayList` + QR scan flow           | ✅ `PutAwayView` + `PutAwayDetailDialog`          |
| Item-to-location QR association                   | ✅ DONE | ✅ Scan item QR + location QR             | ✅ QR scanning                                    |
| Rule-based location recommendations               | ✅ DONE | ✅ `PutAwayRule` + `LocationAllocation`   | ✅ Bin suggestions in 3D view                     |
| Alternate location override                       | ✅ DONE | ✅ Authorized user can pick alternate bin | —                                                 |
| Warehouse layout, location master, capacity rules | ✅ DONE | ✅ `WarehouseLocation` tree + capacity    | ✅ `LocationTreeView` + `WarehouseLayoutDesigner` |

**Status: ✅ FULLY IMPLEMENTED — No gaps.**

---

### 2.4 INVENTORY MANAGEMENT & VISIBILITY

| Requirement                                                                               | Status     | Backend                                                      | Frontend                                  |
| ----------------------------------------------------------------------------------------- | ---------- | ------------------------------------------------------------ | ----------------------------------------- |
| Real-time visibility by warehouse/zone/aisle/rack/bin/SKU                                 | ✅ DONE    | ✅ `BinStockLevel` + `StockLevel` + `StockMovement`          | ✅ Stock components                       |
| Stock statuses (available/allocated/picked/packed/in-transit/rejected/damaged/quarantine) | ⚠️ PARTIAL | Most statuses covered; `in-transit` & `quarantine` need work | Need status filter                        |
| Movement history per unique product                                                       | ✅ DONE    | ✅ `StockMovement` append-only audit                         | ✅ Movement history view                  |
| Dashboard visualization                                                                   | ⚠️ PARTIAL | ✅ `wms-dashboard` endpoints                                 | ✅ `DashboardPanel` but needs enhancement |
| Warehouse layout visualization                                                            | ✅ DONE    | ✅ `Warehouse3DView` + WebSocket                             | ✅ Three.js 3D view                       |
| SAP enterprise stock sync                                                                 | ❌ MISSING | Need SAP sync                                                | —                                         |

**Gap Action Items**:
| # | Task | Priority | Effort | Story Points |
|---|---|---|---|---|
| IV-01 | In-transit & quarantine stock status tracking | P1 - High | M | 5 |
| IV-02 | Enhanced WMS dashboard with warehouse-layout visualization | P1 - High | M | 8 |
| IV-03 | SAP inventory movement sync | P0 - Critical | L | 13 |
| IV-04 | Stock status filter across all inventory views | P2 - Medium | S | 3 |

---

### 2.5 CYCLE COUNTING

| Requirement                | Status     | Backend                              | Frontend                 |
| -------------------------- | ---------- | ------------------------------------ | ------------------------ |
| Scheduled counting         | ❌ MISSING | Need count schedule engine           | Need schedule UI         |
| ABC-based counting         | ❌ MISSING | Need ABC classification engine       | Need ABC config          |
| Location-based counting    | ❌ MISSING | Need location-based count generation | Need location selector   |
| SKU-based counting         | ❌ MISSING | Need SKU-based count generation      | Need SKU selector        |
| Blind counting             | ❌ MISSING | Need blind count mode                | Need blind count UI      |
| Visible counting           | ❌ MISSING | Need visible count mode              | Need visible count UI    |
| Recount support            | ❌ MISSING | Need recount workflow                | Need recount UI          |
| Variance approval workflow | ❌ MISSING | Need variance tolerance + approval   | Need approval UI         |
| SAP adjustment sync        | ❌ MISSING | Need SAP sync                        | —                        |
| QR/handheld scanning       | ✅ DONE    | Existing scan infrastructure         | Existing scan components |

**Gap Action Items** (Entire module to build):
| # | Task | Priority | Effort | Story Points |
|---|---|---|---|---|
| CC-01 | Database models: `CycleCountSchedule`, `CycleCountTask`, `CycleCountItem`, `CycleCountVariance` | P0 - Critical | M | 5 |
| CC-02 | ABC classification engine (velocity × value-based) | P1 - High | M | 8 |
| CC-03 | Count schedule engine (cron-based or event-driven) | P1 - High | L | 8 |
| CC-04 | Count task generation API (by schedule, location, SKU, ad-hoc) | P0 - Critical | L | 13 |
| CC-05 | Blind/visible count execution API | P0 - Critical | M | 8 |
| CC-06 | Variance calculation + tolerance check | P0 - Critical | M | 5 |
| CC-07 | Recount workflow API | P1 - High | M | 5 |
| CC-08 | Variance approval workflow API | P0 - Critical | M | 8 |
| CC-09 | SAP adjustment sync | P0 - Critical | M | 8 |
| CC-10 | Frontend: Count schedule management page | P0 - Critical | L | 13 |
| CC-11 | Frontend: Count execution page (scan-based) | P0 - Critical | L | 13 |
| CC-12 | Frontend: Variance review & approval page | P0 - Critical | M | 8 |
| CC-13 | Frontend: ABC classification config page | P1 - High | M | 5 |

---

### 2.6 OUTBOUND PICKING

| Requirement                   | Status            | Backend                                                           | Frontend                   |
| ----------------------------- | ----------------- | ----------------------------------------------------------------- | -------------------------- |
| Order allocation for picking  | ✅ DONE           | ✅ `smart_picking.py` with allocation                             | ✅ `PickListView`          |
| Wave/zone picking             | ❌ NOT APPLICABLE | Per requirements: "not applicable to Prestige warehouse scenario" | —                          |
| Basic packing verification    | ❌ MISSING        | Need packing verification API                                     | Need packing UI            |
| Scan-based packing validation | ❌ MISSING        | Need scan-picked-items-against-order API                          | Need packing scan UI       |
| Product-carton association    | ❌ MISSING        | Need carton/handling-unit model                                   | Need carton association UI |

**Gap Action Items**:
| # | Task | Priority | Effort | Story Points |
|---|---|---|---|---|
| OP-01 | Packing verification API (scan items → validate against order) | P0 - Critical | M | 8 |
| OP-02 | Carton/Handling Unit model + API | P2 - Medium | M | 8 |
| OP-03 | Product-to-carton association during packing | P2 - Medium | M | 5 |
| OP-04 | Frontend: Packing verification page (scan-based) | P0 - Critical | L | 13 |
| OP-05 | Frontend: Carton management UI | P2 - Medium | M | 8 |
| OP-06 | Label output for packed cartons | P2 - Medium | M | 5 |

---

### 2.7 OUTBOUND SHIPPING

| Requirement             | Status          | Backend                                | Frontend                   |
| ----------------------- | --------------- | -------------------------------------- | -------------------------- |
| Shipment staging        | ❌ MISSING      | Need staging area management           | Need staging UI            |
| Final scan verification | ✅ DONE         | ✅ `GateVerificationSession`           | ✅ `GateVerificationPanel` |
| Dispatch confirmation   | ✅ DONE         | ✅ `DispatchRecord`                    | ✅ `DispatchList`          |
| Shipment status update  | ⚠️ PARTIAL      | Dispatch exists; need status lifecycle | Need status tracking       |
| SAP shipment sync       | ❌ MISSING      | Need SAP sync                          | —                          |
| TMS/carrier integration | ❌ OUT OF SCOPE | Separate assessment required           | —                          |

**Gap Action Items**:
| # | Task | Priority | Effort | Story Points |
|---|---|---|---|---|
| OS-01 | Staging area designation + staging assignment API | P1 - High | M | 8 |
| OS-02 | Shipment status lifecycle (staged → verified → dispatched → delivered) | P1 - High | M | 5 |
| OS-03 | SAP dispatch/shipment sync | P0 - Critical | M | 8 |
| OS-04 | Frontend: Staging management page | P1 - High | M | 8 |
| OS-05 | Frontend: Shipment status tracking page | P1 - High | M | 5 |

---

### 2.8 CROSS-CUTTING: SAP INTEGRATION

| #      | Task                                                               | Priority      | Effort | Story Points |
| ------ | ------------------------------------------------------------------ | ------------- | ------ | ------------ |
| SAP-01 | SAP connector service architecture (message queue / webhook based) | P0 - Critical | XL     | 21           |
| SAP-02 | ASN ingestion from SAP                                             | P0 - Critical | L      | 13           |
| SAP-03 | Stock-transfer/outbound document ingestion                         | P0 - Critical | L      | 13           |
| SAP-04 | Goods receipt sync to SAP                                          | P0 - Critical | M      | 8            |
| SAP-05 | Inventory movement sync to SAP                                     | P0 - Critical | L      | 13           |
| SAP-06 | Cycle count adjustment sync to SAP                                 | P0 - Critical | M      | 8            |
| SAP-07 | Dispatch/shipment confirmation sync to SAP                         | P0 - Critical | M      | 8            |
| SAP-08 | CSV upload fallback for pilot (all document types)                 | P0 - Critical | M      | 8            |

---

## 3. Role-Based Access Control (RBAC) Design

### 3.1 Proposed WMS Roles

| Role                     | Description                                                | Inheritance |
| ------------------------ | ---------------------------------------------------------- | ----------- |
| **WMS Super Admin**      | Full system access across all orgs                         | —           |
| **WMS Manager**          | Full warehouse operations access within org                | —           |
| **WMS Supervisor**       | Oversee inbound/outbound, approve exceptions               | —           |
| **WMS Operator**         | Execute daily warehouse tasks (scanning, putaway, picking) | —           |
| **ASN Coordinator**      | Manage ASN intake and reconciliation                       | —           |
| **Inventory Controller** | Stock management, cycle counts, reconciliations            | —           |
| **Quality Inspector**    | QC inspections and approvals                               | —           |
| **Viewer**               | Read-only access to warehouse data                         | —           |

### 3.2 Permission Matrix

| Resource                 | Super Admin | Manager | Supervisor | Operator    | ASN Coord. | Inv. Controller | QC Inspector | Viewer |
| ------------------------ | ----------- | ------- | ---------- | ----------- | ---------- | --------------- | ------------ | ------ |
| **ASN Orders**           | CRUD+M      | CRUD+M  | CRUD       | R           | CRUD+M     | R               | —            | R      |
| **Receiving Slips**      | CRUD+M      | CRUD+M  | CRUD+A     | CRUD        | R          | R               | —            | R      |
| **Putaway**              | CRUD+M      | CRUD+M  | CRUD       | CRUD        | —          | R               | —            | R      |
| **Pick Lists**           | CRUD+M      | CRUD+M  | CRUD       | CRUD        | —          | R               | —            | R      |
| **Packing**              | CRUD+M      | CRUD+M  | CRUD       | CRUD        | —          | —               | —            | R      |
| **Gate/Dispatch**        | CRUD+M      | CRUD+M  | CRUD       | CRUD        | —          | —               | —            | R      |
| **Staging**              | CRUD+M      | CRUD+M  | CRUD       | CRUD        | —          | —               | —            | R      |
| **Warehouse/Locations**  | CRUD+M      | CRUD+M  | R          | R           | R          | R               | —            | R      |
| **Bin Stock**            | CRUD+M      | CRUD+M  | R          | R           | R          | CRUD            | —            | R      |
| **Stock Levels**         | CRUD+M      | CRUD+M  | R          | R           | R          | CRUD+M          | —            | R      |
| **Stock Movements**      | R           | R       | R          | R           | R          | R               | —            | R      |
| **Stock Reconciliation** | CRUD+A      | CRUD+A  | R          | —           | —          | CRUD+A          | —            | R      |
| **Cycle Count**          | CRUD+A      | CRUD+M  | CRUD       | CRUD (exec) | —          | CRUD+A          | —            | R      |
| **Batch/Serial**         | CRUD+M      | CRUD+M  | CRUD       | CRUD        | —          | CRUD            | —            | R      |
| **Quality Inspection**   | CRUD+A      | CRUD+A  | CRUD       | —           | —          | —               | CRUD+A       | R      |
| **Putaway Rules**        | CRUD        | CRUD    | R          | —           | —          | R               | —            | R      |
| **WMS Workers**          | CRUD+M      | CRUD+M  | CRUD       | —           | —          | —               | —            | R      |
| **WMS Devices**          | CRUD+M      | CRUD+M  | CRUD       | —           | —          | —               | —            | R      |
| **WMS Dashboard**        | Full        | Full    | Full       | Limited     | Limited    | Full            | Limited      | R      |
| **3D Warehouse View**    | Full        | Full    | Full       | R           | —          | Full            | —            | R      |
| **Floor Plan**           | CRUD        | CRUD    | R          | —           | —          | R               | —            | R      |
| **Reports**              | Full        | Full    | Full       | —           | Full       | Full            | —            | R      |

**Legend**: C=Create, R=Read, U=Update, D=Delete, M=Manage, A=Approve, exec=Execute Only

### 3.3 Backend Permission Implementation

All permissions will be defined in `core-service/app/core/authorization.py` and seeded in `identity-service/scripts/seed_data.py`.

**New permission codes to add**:

```python
# Cycle Count
CYCLE_COUNT_SCHEDULE = "cycle_count_schedule"
CYCLE_COUNT_TASK = "cycle_count_task"
CYCLE_COUNT_EXECUTE = "cycle_count_execute"

# Packing
PACKING_VERIFICATION = "packing_verification"

# Staging
STAGING_MANAGEMENT = "staging_management"

# SAP Integration (internal)
SAP_SYNC = "sap_sync"

# Quarantine
QUARANTINE_MANAGEMENT = "quarantine_management"
```

### 3.4 Frontend Permission Guard

New permission checks in `apps/platform/src/app/utils/permissions.ts`:

```typescript
cycleCount: {
  view: hasAnyPermission(p, ['*.*', 'cycle_count_schedule.*', 'cycle_count_schedule.read', 'cycle_count_task.*', 'cycle_count_task.read']),
  create: hasAnyPermission(p, ['*.*', 'cycle_count_schedule.create', 'cycle_count_task.create']),
  execute: hasAnyPermission(p, ['*.*', 'cycle_count_execute.*', 'cycle_count_execute']),
  approve: hasAnyPermission(p, ['*.*', 'cycle_count_task.approve']),
},
packing: {
  view: hasAnyPermission(p, ['*.*', 'packing_verification.*', 'packing_verification.read']),
  execute: hasAnyPermission(p, ['*.*', 'packing_verification.*', 'packing_verification.execute']),
},
staging: {
  view: hasAnyPermission(p, ['*.*', 'staging_management.*', 'staging_management.read']),
  manage: hasAnyPermission(p, ['*.*', 'staging_management.*']),
},
```

---

## 4. Frontend Implementation Plan

### 4.1 New Pages to Build

| Page                          | Route                                | Module    | Priority |
| ----------------------------- | ------------------------------------ | --------- | -------- |
| **Cycle Count Dashboard**     | `/wms/cycle-count`                   | inventory | P0       |
| **Cycle Count Schedule**      | `/wms/cycle-count/schedules`         | inventory | P0       |
| **Count Execution**           | `/wms/cycle-count/execute/:taskId`   | inventory | P0       |
| **Variance Review**           | `/wms/cycle-count/variances/:taskId` | inventory | P0       |
| **ABC Classification Config** | `/wms/cycle-count/abc-config`        | inventory | P1       |
| **Packing Verification**      | `/wms/packing`                       | inventory | P0       |
| **Carton Management**         | `/wms/packing/cartons`               | inventory | P2       |
| **Staging Management**        | `/wms/staging`                       | inventory | P1       |
| **Shipment Tracking**         | `/wms/shipments`                     | inventory | P1       |
| **Quarantine View**           | `/wms/quarantine`                    | inventory | P1       |
| **CSV Import (ASN)**          | `/wms/inbound/import`                | inventory | P0       |

### 4.2 Components to Build

```
apps/inventory/src/app/components/wms/
├── cycle-count/
│   ├── CycleCountDashboard.tsx        ← Main CC hub (tabs: schedules, tasks, variances)
│   ├── CycleCountScheduleList.tsx     ← List of count schedules
│   ├── CycleCountScheduleForm.tsx     ← Create/edit schedule (dialog)
│   ├── CycleCountTaskList.tsx         ← Generated count tasks
│   ├── CountExecutionPanel.tsx        ← QR-scan based counting UI
│   ├── CountVarianceReview.tsx        ← Variance review + approve/reject
│   ├── ABCClassificationPanel.tsx     ← ABC rules configuration
│   └── CycleCountStatusBadge.tsx      ← Status badges for CC workflow
├── packing/
│   ├── PackingVerificationPanel.tsx   ← Scan-based packing check
│   ├── CartonManagementPanel.tsx      ← Carton/handling-unit CRUD
│   └── PackingLabelPreview.tsx        ← Label preview (for PDF output)
├── staging/
│   ├── StagingAreaPanel.tsx           ← Staging zone management
│   └── StagingAssignmentPanel.tsx     ← Assign shipments to staging
├── shipments/
│   └── ShipmentTrackingPanel.tsx      ← Shipment status timeline
├── quarantine/
│   └── QuarantineStockPanel.tsx       ← View/manage quarantine stock
└── imports/
    └── CSVImportPanel.tsx             ← Generic CSV upload with mapping
```

### 4.3 API Clients to Add

```
apps/inventory/src/app/utility/api/
├── cycle-count.ts         ← Count schedules, tasks, execution, variances
├── packing.ts             ← Packing verification, cartons
├── staging.ts             ← Staging area management
├── shipments.ts           ← Shipment status tracking
├── quarantine.ts          ← Quarantine stock operations
└── sap-import.ts          ← CSV import endpoints
```

### 4.4 New Routes (AppRoutes.tsx additions)

```typescript
// WMS sub-routes (lazy-loaded from inventory remote)
{ path: '/wms/cycle-count', component: CycleCountDashboard, permissions: ['cycle_count_schedule.read', 'cycle_count_task.read'] },
{ path: '/wms/cycle-count/schedules', component: CycleCountScheduleList, permissions: ['cycle_count_schedule.read'] },
{ path: '/wms/cycle-count/execute/:taskId', component: CountExecutionPanel, permissions: ['cycle_count_execute'] },
{ path: '/wms/cycle-count/variances/:taskId', component: CountVarianceReview, permissions: ['cycle_count_task.approve'] },
{ path: '/wms/cycle-count/abc-config', component: ABCClassificationPanel, permissions: ['cycle_count_schedule.manage'] },
{ path: '/wms/packing', component: PackingVerificationPanel, permissions: ['packing_verification.read'] },
{ path: '/wms/staging', component: StagingAreaPanel, permissions: ['staging_management.read'] },
{ path: '/wms/shipments', component: ShipmentTrackingPanel, permissions: ['dispatch.read'] },
{ path: '/wms/quarantine', component: QuarantineStockPanel, permissions: ['quarantine_management.read'] },
{ path: '/wms/inbound/import', component: CSVImportPanel, permissions: ['asn_order.create'] },
```

### 4.5 Sidebar Updates

Add to `sidebar.tsx` under WMS section (collapsible submenu):

```typescript
{
  title: 'WMS',
  icon: Warehouse,
  featureFlag: 'wms_module_enabled',
  children: [
    { title: 'Dashboard', href: '/wms' },
    { title: 'Cycle Count', href: '/wms/cycle-count', permission: 'cycle_count_schedule.read' },
    { title: 'Packing', href: '/wms/packing', permission: 'packing_verification.read' },
    { title: 'Staging', href: '/wms/staging', permission: 'staging_management.read' },
    { title: 'Quarantine', href: '/wms/quarantine', permission: 'quarantine_management.read' },
  ],
},
```

---

## 5. Backend Implementation Plan

### 5.1 New Services to Build

```
core-service/app/services/
├── cycle_count_service.py           ← Schedule management, task generation, variance calculation
├── cycle_count_execution_service.py ← Count execution (blind/visible), QR scanning
├── packing_verification_service.py  ← Packing validation against orders
├── staging_service.py               ← Staging area assignment & management
├── shipment_tracking_service.py     ← Shipment status lifecycle
├── quarantine_service.py            ← Quarantine stock movement & tracking
├── sap_connector_service.py         ← SAP integration (message queue based)
└── abc_classification_service.py    ← ABC classification engine
```

### 5.2 New Endpoints to Build

```
core-service/app/api/v1/endpoints/
├── cycle_counts.py           ← /cycle-counts (schedules, tasks, execution, variances)
├── packing_verification.py   ← /packing-verification
├── staging.py                ← /staging
├── shipments.py              ← /shipments
├── quarantine.py             ← /quarantine
└── sap_imports.py            ← /sap-imports (CSV fallback)
```

### 5.3 New Database Models

```python
# Cycle Count
class CycleCountSchedule(Base):
    __tablename__ = "cycle_count_schedules"
    id, organization_id, warehouse_id, name, frequency (daily/weekly/monthly/custom)
    count_type (ABC/location/SKU/ad_hoc), abc_class, location_ids, item_ids
    is_blind, is_active, tolerance_percentage, approval_required
    created_by, created_at, updated_at

class CycleCountTask(Base):
    __tablename__ = "cycle_count_tasks"
    id, schedule_id, warehouse_id, status (pending/in_progress/completed/requires_review/approved)
    assigned_to, started_at, completed_at, created_at

class CycleCountTaskItem(Base):
    __tablename__ = "cycle_count_task_items"
    id, task_id, bin_id, item_id, expected_qty, counted_qty, variance_qty
    variance_percentage, status (pending/counted/recounted/approved/rejected)

# Packing
class PackingVerification(Base):
    __tablename__ = "packing_verifications"
    id, pick_list_id, dispatch_id, status, verified_by, verified_at

class PackingCarton(Base):
    __tablename__ = "packing_cartons"
    id, packing_id, carton_label, carton_type, weight, dimensions

class PackingCartonItem(Base):
    __tablename__ = "packing_carton_items"
    id, carton_id, item_id, quantity, scanned_at

# Staging
class StagingArea(Base):
    __tablename__ = "staging_areas"
    id, warehouse_id, location_id, name, capacity, is_active

class StagingAssignment(Base):
    __tablename__ = "staging_assignments"
    id, staging_area_id, dispatch_id, assigned_at, released_at

# Quarantine
class QuarantineMovement(Base):
    __tablename__ = "quarantine_movements"
    id, item_id, from_bin_id, to_bin_id (quarantine), reason, moved_by, moved_at
```

### 5.4 Integration Architecture

```
┌──────────┐     ┌─────────────────┐     ┌──────────────┐
│   SAP    │────▶│  SAP Connector  │────▶│  Horizon WMS  │
│  System  │◀────│     Service     │◀────│  (core-svc)   │
└──────────┘     └─────────────────┘     └──────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │  Redis Queue │  ← Message buffer for SAP events
                 └──────────────┘
                        │
                        ▼
                 ┌──────────────┐
                 │  CSV Upload  │  ← Pilot fallback
                 │   Endpoint   │
                 └──────────────┘
```

---

## 6. Implementation Phases & Timeline

### Phase 1: Foundation (Weeks 1-2) — 26 SP

| #      | Task                                         | SP  |
| ------ | -------------------------------------------- | --- |
| I-02   | CSV upload endpoint for ASN (pilot fallback) | 5   |
| SAP-08 | CSV upload fallback for all document types   | 8   |
| I-03   | Quarantine zone designation                  | 3   |
| I-06   | Auto-move rejected items to quarantine       | 5   |
| IV-01  | In-transit & quarantine stock status         | 5   |

> **Deliverable**: Pilot-ready CSV-based ASN import + quarantine management

### Phase 2: Core Gaps (Weeks 3-5) — 55 SP

| #     | Task                                   | SP  |
| ----- | -------------------------------------- | --- |
| CC-01 | Cycle count database models            | 5   |
| CC-02 | ABC classification engine              | 8   |
| CC-04 | Count task generation API              | 13  |
| CC-05 | Blind/visible count execution API      | 8   |
| CC-06 | Variance calculation + tolerance check | 5   |
| CC-08 | Variance approval workflow API         | 8   |
| CC-03 | Count schedule engine                  | 8   |

> **Deliverable**: Complete cycle count backend

### Phase 3: Outbound Enhancement (Weeks 6-7) — 34 SP

| #     | Task                       | SP          |
| ----- | -------------------------- | ----------- |
| OP-01 | Packing verification API   | 8           |
| OP-02 | Carton/Handling Unit model | 8           |
| OS-01 | Staging area API           | 8           |
| OS-02 | Shipment status lifecycle  | 5           |
| IV-02 | Enhanced WMS dashboard     | 5 (partial) |

> **Deliverable**: Packing verification + staging + shipment tracking backend

### Phase 4: SAP Integration (Weeks 8-10) — 63 SP

| #      | Task                              | SP  |
| ------ | --------------------------------- | --- |
| SAP-01 | SAP connector architecture        | 21  |
| SAP-02 | ASN ingestion from SAP            | 13  |
| SAP-03 | Stock-transfer document ingestion | 13  |
| SAP-04 | Goods receipt sync                | 8   |
| SAP-07 | Dispatch/shipment sync            | 8   |

> **Deliverable**: SAP connector MVP

### Phase 5: Frontend (Weeks 4-12, parallel with backend)

| #             | Task                                 | SP  |
| ------------- | ------------------------------------ | --- |
| CC-10         | Cycle count schedule management page | 13  |
| CC-11         | Count execution page (scan-based)    | 13  |
| CC-12         | Variance review & approval page      | 8   |
| CC-13         | ABC classification config page       | 5   |
| OP-04         | Packing verification page            | 13  |
| OP-05         | Carton management UI                 | 8   |
| OS-04         | Staging management page              | 8   |
| OS-05         | Shipment tracking page               | 5   |
| I-05 frontend | Quarantine view                      | 5   |
| CSV frontend  | CSV import UI                        | 5   |

> **Deliverable**: Complete frontend for all new features

### Phase 6: SAP Sync Completion (Weeks 11-12) — 37 SP

| #      | Task                            | SP  |
| ------ | ------------------------------- | --- |
| SAP-05 | Inventory movement sync         | 13  |
| SAP-06 | Cycle count adjustment sync     | 8   |
| CC-09  | Cycle count SAP adjustment sync | 8   |
| I-04   | Receiving slip SAP sync         | 8   |

> **Deliverable**: End-to-end SAP integration complete

---

## 7. Total Effort Summary

| Phase     | Description                          | Story Points | Timeline     |
| --------- | ------------------------------------ | ------------ | ------------ |
| Phase 1   | Foundation (CSV Import + Quarantine) | 26 SP        | Weeks 1-2    |
| Phase 2   | Cycle Count Backend                  | 55 SP        | Weeks 3-5    |
| Phase 3   | Outbound Enhancement Backend         | 34 SP        | Weeks 6-7    |
| Phase 4   | SAP Integration Core                 | 63 SP        | Weeks 8-10   |
| Phase 5   | Frontend (parallel)                  | 78 SP        | Weeks 4-12   |
| Phase 6   | SAP Sync Completion                  | 37 SP        | Weeks 11-12  |
| **TOTAL** |                                      | **~293 SP**  | **12 Weeks** |

> **Note**: Phases 2-3 & Phase 5 can run in parallel with a team of 2-3 developers.
> With 2 backend + 1 frontend developer: estimated **10-12 weeks**.

---

## 8. Risk Register

| Risk                                      | Impact | Likelihood | Mitigation                                      |
| ----------------------------------------- | ------ | ---------- | ----------------------------------------------- |
| SAP API not available during pilot        | High   | Medium     | CSV upload fallback (Phase 1)                   |
| SAP document format mismatch              | High   | High       | Schema mapping layer in connector               |
| Android handheld device compatibility     | Medium | Low        | Use PWA/WebView; test on Zebra/Honeywell        |
| QR code standard mismatch with SAP        | Medium | Medium     | Agree on QR format during process design        |
| Performance with real-time inventory sync | Medium | Low        | Redis queue for async processing                |
| Cycle count disrupting live operations    | Medium | Low        | Count during off-hours; freeze bin during count |

---

## 9. What's Already Done (✅) — No Work Needed

These features are fully implemented and match the requirements:

- ✅ **ASN Order Management** — CRUD + status lifecycle
- ✅ **Inbound QR Scanning** — `ScanSession` → `ReceivingSlip` with item flagging
- ✅ **Receiving Slip Approval** — Configurable approval workflow
- ✅ **Directed Putaway** — Rule-based bin suggestions + QR scan association
- ✅ **Putaway Rules Engine** — Configurable by item group, zone, capacity
- ✅ **Pick List Management** — Draft → In Progress → Completed → Cancelled
- ✅ **Smart Picking** — Cross-warehouse allocation suggestions
- ✅ **Gate Verification** — QR scanning + vehicle/driver info
- ✅ **Dispatch Records** — Confirmation and recording
- ✅ **Location Hierarchy** — Zone → Aisle → Bay → Level → Bin
- ✅ **Bin Stock Management** — Per-bin quantities, copy, bulk add, import
- ✅ **Stock Levels** — Aggregate per item/warehouse with filters
- ✅ **Stock Movements** — Append-only audit trail
- ✅ **Stock Reconciliation** — CSV template download/upload wizard
- ✅ **Batch Tracking** — Active/expired/consumed lifecycle
- ✅ **Serial Number Tracking** — Per-item serial management
- ✅ **Quality Inspection** — Templates + inspections with readings
- ✅ **WMS Worker Management** — Barcode + credential login
- ✅ **WMS Device Management** — Device tracking
- ✅ **3D Warehouse View** — Three.js with WebSocket real-time updates
- ✅ **Floor Plan Designer** — Layout configuration and bin generation
- ✅ **WMS Dashboard** — Manager/supervisor KPIs
- ✅ **Location Time Tracking** — Worker scan tracking at bins
- ✅ **Document Numbering** — Configurable naming series
- ✅ **Notifications** — WMS/ASN in-app notifications
- ✅ **Items/Products/SKUs** — With groups, prices, packaging units
- ✅ **Suppliers/Vendors** — CRUD
- ✅ **Purchase Orders** — CRUD with RFQ conversion
- ✅ **Sales Orders** — CRUD with delivery note/invoice conversion
- ✅ **Customers** — CRUD with bulk import
- ✅ **Delivery Notes** — CRUD with invoice conversion
- ✅ **Landed Cost** — Voucher management
- ✅ **Purchase Receipts** — CRUD
