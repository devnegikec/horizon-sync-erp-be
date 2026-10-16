# WMS Reports — Frontend Integration Notes

Backend-only implementation of the WMS reports MVP. This document tells the
frontend team how to call the four report endpoints and what the responses look
like.

---

## 1. Base facts

| Item | Value |
|---|---|
| Base URL | `${API_BASE_URL}/api/v1` |
| Auth | `Authorization: Bearer <JWT>` (identity-service access token) |
| Required permission | `warehouse.read` |
| Pagination | `page` (1-based), `page_size` (max 100) |
| Export | append `?format=csv` to download the full report as CSV |

All four endpoints are read-only `GET`, scoped to the caller's assigned
warehouses (system/organization admins and primary-warehouse users see every
warehouse; other users see only their assigned warehouses).

---

## 2. Endpoints

```
GET /api/v1/wms/reports/stock-movements
GET /api/v1/wms/reports/inventory-aging
GET /api/v1/wms/reports/receiving-variance
GET /api/v1/wms/reports/bin-capacity
```

Every endpoint accepts a shared `format` query param:

| Param | Values |
|---|---|
| `format` | `json` (default) or `csv` — `csv` returns `text/csv` with a `Content-Disposition` attachment |

### 2.1 Stock movement report

```
GET /api/v1/wms/reports/stock-movements
    ?warehouse_id=&item_id=&movement_type=&date_from=&date_to=&page=&page_size=&format=
```

| Param | Notes |
|---|---|
| `movement_type` | `in` \| `out` \| `transfer` \| `adjustment` |
| `date_from` / `date_to` | ISO-8601 datetime range on `performed_at` |

Response:

```json
{
  "summary": {
    "total_in_qty": 65.0,
    "total_in_value": 0.0,
    "total_out_qty": 50.0,
    "total_out_value": 0.0,
    "total_transfer_qty": 0.0,
    "total_adjustment_qty": 0.0
  },
  "rows": [
    {
      "id": "…",
      "performed_at": "2026-09-15T08:36:13.840087Z",
      "movement_type": "in",
      "quantity": 1.0,
      "unit_cost": null,
      "line_value": 0.0,
      "reference_type": "stock_entry",
      "reference_id": "…",
      "notes": null,
      "warehouse_id": "…",
      "warehouse_name": "Mother Warehouse",
      "item_id": "…",
      "item_code": "ITM-2026-00034",
      "item_name": "…",
      "sku": "…"
    }
  ],
  "pagination": { "page": 1, "page_size": 20, "total_items": 37, "total_pages": 2, "has_next": true, "has_prev": false }
}
```

### 2.2 Inventory aging report

```
GET /api/v1/wms/reports/inventory-aging
    ?warehouse_id=&item_id=&days_idle=30&page=&page_size=&format=
```

- `days_idle` (default `30`): items whose last movement is older than this (or
  never moved) are reported.

Response:

```json
{
  "summary": {
    "idle_item_count": 16,
    "total_idle_qty": 448.0,
    "total_idle_value": 0.0,
    "days_idle": 30
  },
  "rows": [
    {
      "item_id": "…",
      "item_code": "ITM-2026-00015",
      "item_name": "…",
      "sku": "…",
      "warehouse_id": "…",
      "warehouse_name": "…",
      "quantity_on_hand": 3.0,
      "quantity_reserved": 0.0,
      "quantity_available": 3.0,
      "last_moved_at": null,
      "last_unit_cost": null,
      "est_value": 0.0,
      "days_idle": null
    }
  ],
  "pagination": { /* … */ }
}
```

> `est_value = quantity_on_hand × last_unit_cost`. It is `0` when no unit cost
> is recorded in stock movements (common in test data).

### 2.3 Receiving vs ASN variance report

```
GET /api/v1/wms/reports/receiving-variance
    ?warehouse_id=&date_from=&date_to=&page=&page_size=&format=
```

- `date_from` / `date_to` filter on the ASN `order_date`.
- `received` is sourced from `receiving_slip_items` (the actual receiving
  flow), joined to the ASN by `asn_order_id` + item `sku`.

Response:

```json
{
  "summary": {
    "total_expected_qty": 1855.0,
    "total_received_qty": 1176.0,
    "total_variance_qty": 679.0,
    "line_count": 184,
    "short_line_count": 84,
    "excess_line_count": 3
  },
  "rows": [
    {
      "asn_order_id": "…",
      "asn_order_no": "ASN-2026-00117",
      "order_date": "2026-09-20T17:25:56.485905Z",
      "asn_status": "delivered",
      "warehouse_id": "…",
      "warehouse_name": "…",
      "item_id": "…",
      "item_code": "ITM-2026-00033",
      "item_name": "…",
      "sku": "…",
      "expected_qty": 12.0,
      "received_qty": 12.0,
      "variance_qty": 0.0
    }
  ],
  "pagination": { /* … */ }
}
```

- `variance_qty = expected_qty − received_qty` (positive = short, negative =
  over-received).

### 2.4 Bin capacity utilization report

```
GET /api/v1/wms/reports/bin-capacity
    ?warehouse_id=&page=&page_size=&format=
```

Response:

```json
{
  "summary": {
    "total_bins": 424,
    "bins_with_volume_capacity": 424,
    "bins_with_weight_capacity": 0,
    "total_capacity_cc": 424000000.0,
    "total_occupied_cc": 758640.0,
    "volume_utilization_pct": 0.178,
    "total_capacity_grams": 0.0,
    "total_occupied_grams": 0.0,
    "weight_utilization_pct": null,
    "over_utilized_bins": 0,
    "full_bins": 0
  },
  "rows": [
    {
      "bin_id": "…",
      "code": "HOLD",
      "full_path": "HOLD",
      "location_type": "bin",
      "is_pickable": false,
      "unit_count": 0.0,
      "master_pack_count": 0.0,
      "occupied_cc": 0.0,
      "capacity_cc": 1000000.0,
      "volume_utilization_pct": 0.0,
      "occupied_grams": 0.0,
      "capacity_grams": null,
      "weight_utilization_pct": null
    }
  ],
  "pagination": { /* … */ }
}
```

- Volume figures are in cubic centimetres (`cc`), weight in grams.
- `volume_utilization_pct` / `weight_utilization_pct` are percentages.
- `over_utilized_bins` = bins above 100% utilization; `full_bins` = bins at or
  above 90% (either metric).

---

## 3. TypeScript types

```ts
export interface PaginationMeta {
  page: number;
  page_size: number;
  total_items: number | null;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface StockMovementSummary {
  total_in_qty: number;
  total_in_value: number;
  total_out_qty: number;
  total_out_value: number;
  total_transfer_qty: number;
  total_adjustment_qty: number;
}

export interface StockMovementRow {
  id: string;
  performed_at: string | null;
  movement_type: "in" | "out" | "transfer" | "adjustment";
  quantity: number;
  unit_cost: number | null;
  line_value: number;
  reference_type: string | null;
  reference_id: string | null;
  notes: string | null;
  warehouse_id: string | null;
  warehouse_name: string | null;
  item_id: string | null;
  item_code: string | null;
  item_name: string | null;
  sku: string | null;
}

export interface InventoryAgingRow {
  item_id: string;
  item_code: string | null;
  item_name: string | null;
  sku: string | null;
  warehouse_id: string | null;
  warehouse_name: string | null;
  quantity_on_hand: number;
  quantity_reserved: number;
  quantity_available: number;
  last_moved_at: string | null;
  last_unit_cost: number | null;
  est_value: number;
  days_idle: number | null;
}

export interface ReceivingVarianceRow {
  asn_order_id: string;
  asn_order_no: string | null;
  order_date: string | null;
  asn_status: string | null;
  warehouse_id: string | null;
  warehouse_name: string | null;
  item_id: string;
  item_code: string | null;
  item_name: string | null;
  sku: string | null;
  expected_qty: number;
  received_qty: number;
  variance_qty: number;
}

export interface BinCapacityRow {
  bin_id: string;
  code: string | null;
  full_path: string | null;
  location_type: string | null;
  is_pickable: boolean;
  unit_count: number;
  master_pack_count: number;
  occupied_cc: number;
  capacity_cc: number | null;
  volume_utilization_pct: number | null;
  occupied_grams: number;
  capacity_grams: number | null;
  weight_utilization_pct: number | null;
}
```

Each report response is `{ summary, rows, pagination }` with its own summary and
row types.

---

## 4. API client example (project `apiRequest` pattern)

```ts
import { apiRequest } from "@/api/core";

export const wmsReportService = {
  stockMovements(token: string, params: Record<string, unknown>) {
    return apiRequest("/wms/reports/stock-movements", token, { params });
  },
  inventoryAging(token: string, params: Record<string, unknown>) {
    return apiRequest("/wms/reports/inventory-aging", token, { params });
  },
  receivingVariance(token: string, params: Record<string, unknown>) {
    return apiRequest("/wms/reports/receiving-variance", token, { params });
  },
  binCapacity(token: string, params: Record<string, unknown>) {
    return apiRequest("/wms/reports/bin-capacity", token, { params });
  },
};
```

### CSV download

CSV is returned as a raw file, so download it via a plain link / `window.open`
rather than the JSON client:

```ts
const url = `${API_BASE_URL}/api/v1/wms/reports/stock-movements?format=csv&date_from=${from}&date_to=${to}`;
// with Authorization: Bearer <token> header, or a signed/session-cookie variant
```

If the request needs the `Authorization` header, fetch it as a blob instead:

```ts
const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
const blob = await res.blob();
const href = URL.createObjectURL(blob);
// trigger a download of the blob with the Content-Disposition filename
```

---

## 5. UI wiring recommendations

1. **Report selector** — a tab or dropdown for the four reports.
2. **Filter bar** — warehouse (optional, already role-scoped), date range,
   and report-specific filters (`movement_type`, `item_id`, `days_idle`).
3. **Summary cards** — render the `summary` object as KPI cards above the table.
4. **Table** — column set per report (see row types); show variance as a
   color-coded badge (short = amber, excess = green, matched = default).
5. **Pagination** — use `pagination.total_pages`, `has_next`, `has_prev`.
6. **Export button** — calls the same endpoint with `format=csv`.

---

## 6. Notes / caveats

- **Warehouse scoping** is applied server-side; the `warehouse_id` filter only
  narrows an already-scoped view. Non-admin users without a primary warehouse
  see only their assigned warehouses.
- **`movement_type`** validation returns `400` for unknown values.
- **Inventory-aging value** is `0` when items have no recorded unit cost.
- **Receiving variance** uses `receiving_slip_items` as the source of truth for
  received qty (the ASN line's `received_qty` column is not reliably populated).
- CSV export is capped at 100,000 rows.
