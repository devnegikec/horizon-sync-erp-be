"""Canonical WMS dashboard widget catalogue.

The backend owns this list so the frontend never hardcodes widget ids, labels or
ordering. Adding/removing a dashboard widget is a backend-only change: the
Settings → Dashboard Layout tab is rendered from
``GET /api/v1/identity/organizations/{organization_id}/dashboard-layout``.

A widget is only *toggled* by the organization — the definition itself is not
per-org data, which keeps ``organizations.extra_data["dashboard_layout"]`` tiny
(just ``{"id", "enabled", "order"}`` per widget).

Each entry maps to data that already exists in the core service; ``data_source``
is the endpoint the frontend should call to fill the widget, and is informational
only (the dashboard page still decides how to render).
"""

from dataclasses import asdict, dataclass

# Widget groups, in the order the Settings tab should render them.
GROUP_ORDER: tuple[str, ...] = (
    "kpi",
    "flow",
    "inbound",
    "outbound",
    "inventory",
    "capacity",
    "workforce",
    "quality",
    "traceability",
    "activity",
)

GROUP_LABELS: dict[str, str] = {
    "kpi": "Key Metrics",
    "flow": "Stock Flow",
    "inbound": "Inbound & Receiving",
    "outbound": "Outbound & Picking",
    "inventory": "Inventory Health",
    "capacity": "Capacity & Space",
    "workforce": "Workforce",
    "quality": "Quality & Exceptions",
    "traceability": "Product Traceability",
    "activity": "Activity",
}

# Chart types the frontend can be expected to render.
CHART_TYPES: tuple[str, ...] = (
    "kpi",
    "line",
    "bar",
    "donut",
    "funnel",
    "gauge",
    "treemap",
    "heatmap",
    "map",
    "table",
)

READ_PERMISSION = "warehouse.read"


@dataclass(frozen=True)
class DashboardWidget:
    """A single toggleable dashboard widget."""

    id: str
    label: str
    description: str
    group: str
    chart_type: str
    default_enabled: bool
    default_order: int
    permission: str | None = READ_PERMISSION
    data_source: str | None = None
    # When set, the widget only renders if this feature flag is enabled.
    requires_feature_flag: str | None = None
    # Per-widget config knobs the frontend may expose in the layout tab.
    configurable: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


def _w(*args, **kwargs) -> DashboardWidget:  # noqa: ANN002, ANN003
    return DashboardWidget(*args, **kwargs)


# NOTE: keep ids stable — they are persisted in organizations.extra_data.
WIDGETS: tuple[DashboardWidget, ...] = (
    # ── KPI cards ──────────────────────────────────────────────────────────
    _w(
        id="kpi_total_stock_items",
        label="Total Stock Items",
        description="Distinct items with stock on hand across the assigned warehouses.",
        group="kpi",
        chart_type="kpi",
        default_enabled=True,
        default_order=10,
        data_source="/api/v1/wms-dashboard/stats",
    ),
    _w(
        id="kpi_low_stock",
        label="Low Stock Items",
        description="Items at or below their reorder level.",
        group="kpi",
        chart_type="kpi",
        default_enabled=True,
        default_order=20,
        data_source="/api/v1/wms-dashboard/stats",
    ),
    _w(
        id="kpi_out_of_stock",
        label="Out of Stock Items",
        description="Items with zero quantity on hand.",
        group="kpi",
        chart_type="kpi",
        default_enabled=True,
        default_order=30,
        data_source="/api/v1/wms-dashboard/stats",
    ),
    _w(
        id="kpi_active_workers",
        label="Active Workers",
        description="Active warehouse workers assigned to the visible warehouses.",
        group="kpi",
        chart_type="kpi",
        default_enabled=True,
        default_order=40,
        data_source="/api/v1/wms-dashboard/stats",
    ),
    _w(
        id="kpi_assigned_warehouses",
        label="Assigned Warehouses",
        description="Number of warehouses in the current scope.",
        group="kpi",
        chart_type="kpi",
        default_enabled=False,
        default_order=50,
        data_source="/api/v1/wms-dashboard/stats",
    ),
    # ── Stock flow ─────────────────────────────────────────────────────────
    _w(
        id="chart_inbound_outbound",
        label="Inbound vs Outbound",
        description="Quantity and value moved in and out over the selected period.",
        group="flow",
        chart_type="line",
        default_enabled=True,
        default_order=110,
        data_source="/api/v1/wms-dashboard/stats",
        configurable=("period",),
    ),
    _w(
        id="chart_stock_movement_mix",
        label="Stock Movement Mix",
        description="Quantity split across in / out / transfer / adjustment movements.",
        group="flow",
        chart_type="bar",
        default_enabled=False,
        default_order=120,
        data_source="/api/v1/wms/reports/stock-movements",
        configurable=("period",),
    ),
    # ── Inbound ────────────────────────────────────────────────────────────
    _w(
        id="chart_receiving_slip_status",
        label="Receiving Slip Pipeline",
        description="Receiving slips by status (pending review → put-away complete).",
        group="inbound",
        chart_type="donut",
        default_enabled=True,
        default_order=210,
        data_source="/api/v1/inbound/receiving-slips",
    ),
    _w(
        id="chart_putaway_backlog",
        label="Put-Away Backlog",
        description="Put-away lists by status and pending items awaiting shelving.",
        group="inbound",
        chart_type="bar",
        default_enabled=True,
        default_order=220,
        data_source="/api/v1/put-away",
    ),
    _w(
        id="chart_asn_pipeline",
        label="ASN Pipeline",
        description="Advance shipping notices by lifecycle status.",
        group="inbound",
        chart_type="funnel",
        default_enabled=False,
        default_order=230,
        data_source="/api/v1/asn-orders",
    ),
    # ── Outbound ───────────────────────────────────────────────────────────
    _w(
        id="chart_outbound_pick_pipeline",
        label="Outbound Pick Pipeline",
        description="Pick lists by status, with ageing / past-due picks highlighted.",
        group="outbound",
        chart_type="bar",
        default_enabled=True,
        default_order=310,
        data_source="/api/v1/outbound/pick-lists",
    ),
    _w(
        id="chart_packing_dispatch",
        label="Packing & Dispatch",
        description="Packing slips by status (draft → loading → dispatched).",
        group="outbound",
        chart_type="donut",
        default_enabled=False,
        default_order=320,
        data_source="/api/v1/outbound/packing-slips",
    ),
    # ── Inventory health ───────────────────────────────────────────────────
    _w(
        id="chart_inventory_aging",
        label="Inventory Aging",
        description="Idle capital by age bucket, with estimated value.",
        group="inventory",
        chart_type="bar",
        default_enabled=True,
        default_order=410,
        data_source="/api/v1/wms/reports/inventory-aging",
        configurable=("days_idle",),
    ),
    _w(
        id="chart_receiving_variance",
        label="Receiving Variance",
        description="Short-received vs excess-received lines against ASN expectations.",
        group="inventory",
        chart_type="bar",
        default_enabled=False,
        default_order=420,
        data_source="/api/v1/wms/reports/receiving-variance",
    ),
    # ── Capacity & space ───────────────────────────────────────────────────
    _w(
        id="chart_bin_capacity_utilization",
        label="Bin Capacity Utilization",
        description="Volume and weight utilization across bins, plus full/over-utilized counts.",
        group="capacity",
        chart_type="gauge",
        default_enabled=True,
        default_order=510,
        data_source="/api/v1/wms/reports/bin-capacity",
    ),
    _w(
        id="chart_bin_state_map",
        label="Bin State Map",
        description="Live bin fill-level heatmap laid out by physical position.",
        group="capacity",
        chart_type="heatmap",
        default_enabled=False,
        default_order=520,
        data_source="/api/v1/capacity/warehouses/{warehouse_id}/bin-states",
    ),
    _w(
        id="chart_location_utilization_tree",
        label="Zone Utilization",
        description="Warehouse → zone → aisle → bin utilization rollup.",
        group="capacity",
        chart_type="treemap",
        default_enabled=False,
        default_order=530,
        data_source="/api/v1/capacity/warehouses/{warehouse_id}/tree",
    ),
    # ── Workforce ──────────────────────────────────────────────────────────
    _w(
        id="chart_worker_time_per_location",
        label="Time per Location",
        description="Scan count and average elapsed time per warehouse location.",
        group="workforce",
        chart_type="bar",
        default_enabled=False,
        default_order=610,
        permission="pick_list.read",
        data_source="/api/v1/location-scans/summary",
        configurable=("period",),
    ),
    # ── Quality & exceptions ───────────────────────────────────────────────
    _w(
        id="chart_short_balances",
        label="Short Receipt Balances",
        description="Open vs resolved vs written-off shortages, and quantity at risk.",
        group="quality",
        chart_type="donut",
        default_enabled=False,
        default_order=710,
        data_source="/api/v1/inbound/short-balances",
    ),
    # ── Traceability ───────────────────────────────────────────────────────
    _w(
        id="chart_qr_scan_confidence",
        label="QR Scan Confidence",
        description="Valid vs invalid vs suspicious QR scans for consumer-facing codes.",
        group="traceability",
        chart_type="donut",
        default_enabled=False,
        default_order=810,
        permission="qr_product.read",
        data_source="/api/v1/qseal/analytics/summary",
        requires_feature_flag="analytics_module_enabled",
        configurable=("period",),
    ),
    _w(
        id="chart_qr_scan_trend",
        label="QR Scan Trend",
        description="Total / valid / invalid / suspicious scans over time.",
        group="traceability",
        chart_type="line",
        default_enabled=False,
        default_order=820,
        permission="qr_product.read",
        data_source="/api/v1/qseal/analytics/trends",
        requires_feature_flag="analytics_module_enabled",
        configurable=("period",),
    ),
    # ── Activity ───────────────────────────────────────────────────────────
    _w(
        id="feed_recent_activity",
        label="Recent Activity",
        description="Live feed of scan sessions, pick lists, put-away, ASN and dispatches.",
        group="activity",
        chart_type="table",
        default_enabled=True,
        default_order=910,
        data_source="/api/v1/wms-dashboard/stats",
        configurable=("page_size",),
    ),
)

WIDGETS_BY_ID: dict[str, DashboardWidget] = {w.id: w for w in WIDGETS}

# Guard against a typo silently breaking lookups at import time.
assert len(WIDGETS_BY_ID) == len(WIDGETS), "duplicate dashboard widget id"

DEFAULT_ENABLED_IDS: tuple[str, ...] = tuple(w.id for w in WIDGETS if w.default_enabled)


def default_layout() -> dict[str, dict]:
    """Return the default layout as ``{widget_id: {"enabled", "order"}}``."""
    return {
        w.id: {"enabled": w.default_enabled, "order": w.default_order} for w in WIDGETS
    }


__all__ = [
    "CHART_TYPES",
    "DEFAULT_ENABLED_IDS",
    "GROUP_LABELS",
    "GROUP_ORDER",
    "READ_PERMISSION",
    "WIDGETS",
    "WIDGETS_BY_ID",
    "DashboardWidget",
    "default_layout",
]
