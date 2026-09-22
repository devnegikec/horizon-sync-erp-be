"""QSeal endpoints — hierarchical parent-child QSeal management"""

from datetime import datetime
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Query, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.constants import ANALYTICS_MODULE_ENABLED
from app.database import get_db
from app.dependencies import CurrentUser, get_current_user, require_feature_flag, require_permission
from app.models.product_item import ProductItem
from app.schemas.qseal import (
    QSealAggregationGroupedResponse,
    QSealAggregationResponse,
    QSealAutoLinkRequest,
    QSealAutoLinkResponse,
    QSealAnalyticsSummaryResponse,
    QSealChildCreate,
    QSealChildListResponse,
    QSealDeviceAnalyticsResponse,
    QSealGeographyAnalyticsResponse,
    QSealHistoryItem,
    QSealHistoryResponse,
    QSealLabelDownloadResponse,
    QSealMapRequest,
    QSealMapResponse,
    QSealParentCreate,
    QSealParentDetailResponse,
    QSealParentListResponse,
    QSealParentResponse,
    QSealProductAnalyticsResponse,
    QSealScanRequest,
    QSealScanResponse,
    QSealScanTrendResponse,
    QSealSuspiciousReviewRequest,
    QSealSuspiciousScanResponse,
)
from app.schemas.qseal_activation import (
    ActivationScanRequest,
    ActivationScanResponse,
    ActivationSettingsHistoryResponse,
    ActivationSettingsInput,
    ActivationSettingsResponse,
    ActivationSettingsSaveResponse,
    ActivationSummaryResponse,
    MobileActivationRequest,
    MobileCurrencyRequest,
    MobileCurrencyResponse,
    MobileExpiryRequest,
    MobileExpiryResponse,
    MobileScanRequest,
    MobileScanResponse,
    MobileSettingsRequest,
    SerialActivationRequest,
    SerialActivationResponse,
)
from app.services.qseal_activation_service import QSealActivationService
from app.services.qseal_service import QSealService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> QSealService:
    return QSealService(db)


def get_activation_service(db: Session = Depends(get_db)) -> QSealActivationService:
    return QSealActivationService(db)


# ── QSeal Activation (separate from the legacy /qr-activation API) ──────────

@router.get(
    "/products/{product_id}/activation/summary",
    response_model=ActivationSummaryResponse,
    summary="Get QSeal activation summary",
)
def activation_summary(
    product_id: UUID,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
):
    return service.summary(product_id, current_user.organization_id)


@router.get(
    "/products/{product_id}/activation/settings",
    response_model=ActivationSettingsResponse,
    summary="Get current QSeal activation settings",
)
def current_activation_settings(
    product_id: UUID,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
):
    service.product(product_id, current_user.organization_id)
    row = service.current_settings(product_id, current_user.organization_id)
    if not row:
        from app.services.qseal_activation_service import activation_error
        activation_error(404, "QR_SETTINGS_NOT_CONFIGURED", "Product activation settings are not configured.")
    return row


@router.post(
    "/products/{product_id}/activation/settings",
    response_model=ActivationSettingsSaveResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or update QSeal activation settings",
)
def save_activation_settings(
    product_id: UUID,
    data: ActivationSettingsInput,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.create")),
):
    row = service.save_settings(product_id, data, current_user.organization_id, current_user.id)
    return {"message": "Activation settings saved successfully", "settings_id": row.id,
            "expiry_date": row.expiry_date, "currency": row.currency}


@router.get(
    "/products/{product_id}/activation/settings/history",
    response_model=ActivationSettingsHistoryResponse,
    summary="List QSeal activation settings history",
)
def activation_settings_history(
    product_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
):
    rows, total = service.history(product_id, current_user.organization_id, page, page_size)
    return {"items": rows, "page": page, "page_size": page_size, "total": total}


@router.post(
    "/activation/scan/validate",
    response_model=ActivationScanResponse,
    summary="Validate a QSeal serial for mobile activation",
)
def validate_activation_scan(
    data: ActivationScanRequest,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
):
    return service.validate_scan(data.serial_number or data.url, data.product_id, current_user.organization_id)


@router.post(
    "/activation",
    response_model=SerialActivationResponse,
    summary="Activate QSeal serial numbers for mobile",
)
def activate_serials(
    data: SerialActivationRequest,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.create")),
):
    return service.activate(
        data.product_id,
        data.serial_numbers,
        data.settings_id,
        current_user.organization_id,
        current_user.id,
        data.idempotency_key,
    )


# ── QSeal mobile compatibility contract ─────────────────────────────────────
# These routes accept the payload names used by the existing Django mobile
# client while delegating all writes and validation to QSealActivationService.

@router.post(
    "/mobile/destination-markets/currency",
    response_model=MobileCurrencyResponse,
    summary="Resolve destination-market currency for mobile activation",
)
def mobile_currency(
    data: MobileCurrencyRequest,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
):
    return {"currency": service.destination_currency(data.name, current_user.organization_id)}


@router.post(
    "/mobile/products/expiry",
    response_model=MobileExpiryResponse,
    summary="Calculate product expiry for mobile activation",
)
def mobile_expiry(
    data: MobileExpiryRequest,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
):
    return {"expiry_date": service.calculate_expiry(data.product_id, data.manufacturing_date, current_user.organization_id)}


@router.post(
    "/mobile/qr/scan",
    response_model=MobileScanResponse,
    summary="Scan a QSeal QR code using the Django mobile contract",
)
def mobile_scan(
    data: MobileScanRequest,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
):
    return service.mobile_scan(data.url, data.serialNumbers, current_user.organization_id)


@router.post(
    "/mobile/qr/activate",
    summary="Activate QSeal serials using the Django mobile contract",
)
def mobile_activate(
    data: MobileActivationRequest,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.create")),
):
    serials = data.serial_numbers or [
        serial.strip() for serial in (data.srnumber or "").split(",") if serial.strip()
    ]
    if not serials:
        from app.services.qseal_activation_service import activation_error
        activation_error(400, "INVALID_REQUEST", "No serial numbers were provided.")
    product_id = data.product_id
    if product_id is None:
        items = service.db.query(ProductItem).filter(
            ProductItem.organization_id == current_user.organization_id,
            ProductItem.serial_number.in_(serials),
            ProductItem.deleted_at.is_(None),
        ).all()
        product_ids = {item.product_id for item in items}
        if len(items) != len(serials) or len(product_ids) != 1:
            from app.services.qseal_activation_service import activation_error
            activation_error(400, "ACTIVATION_VALIDATION_FAILED", "All serials must belong to one valid product.")
        product_id = next(iter(product_ids))
    result = service.activate(
        product_id,
        serials,
        None,
        current_user.organization_id,
        current_user.id,
        data.idempotency_key,
    )
    return {"message": "Activated", **result}


@router.post(
    "/mobile/qr/settings",
    response_model=ActivationSettingsSaveResponse,
    summary="Save QSeal activation settings using the Django mobile contract",
)
def mobile_settings(
    data: MobileSettingsRequest,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.create")),
):
    activation_data = ActivationSettingsInput(
        dispatch_batch=data.dispatch_batch,
        batch_size=data.batch_size,
        manufacturing_date=data.manufacturing_date,
        manufacturing_unit=data.manufacturing_unit,
        destination_market=data.destination_market,
        mrp=data.mrp,
        append_to_existing=data.append_to_existing,
    )
    row = service.save_settings(
        data.product, activation_data, current_user.organization_id, current_user.id
    )
    return {"message": "Success", "settings_id": row.id, "expiry_date": row.expiry_date, "currency": row.currency}


@router.get(
    "/mobile/qr/settings/{product_id}",
    response_model=ActivationSettingsResponse,
    summary="Get QSeal activation settings for mobile",
)
def mobile_settings_get(
    product_id: UUID,
    service: QSealActivationService = Depends(get_activation_service),
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
):
    service.product(product_id, current_user.organization_id)
    row = service.current_settings(product_id, current_user.organization_id)
    if not row:
        from app.services.qseal_activation_service import activation_error
        activation_error(404, "QR_SETTINGS_NOT_CONFIGURED", "Product activation settings are not configured.")
    return row


# ── Parent QSeal ──────────────────────────────────────────────────────────────


@router.post(
    "/parents",
    response_model=QSealParentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a parent QSeal node (e.g. pallet, container)",
)
def create_parent(
    data: QSealParentCreate,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.create_parent(data, org_id)


@router.get(
    "/parents",
    response_model=QSealParentListResponse,
    summary="List parent QSeal nodes",
)
def list_parents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    qseal_type: str | None = Query(
        None, description="Filter by type: shipper, pallet, container"
    ),
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.list_parents(org_id, page, page_size, qseal_type)


@router.get(
    "/parents/{node_id}",
    response_model=QSealParentResponse,
    summary="Get a parent QSeal node",
)
def get_parent(
    node_id: UUID,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_parent(node_id, org_id)


# ── Child QSeal ───────────────────────────────────────────────────────────────


@router.post(
    "/parents/{parent_id}/children",
    response_model=QSealParentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create child QSeal nodes under a parent",
)
def create_child(
    parent_id: UUID,
    data: QSealChildCreate,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.create_child(parent_id, data, org_id)


@router.get(
    "/parents/{parent_id}/children",
    response_model=QSealChildListResponse,
    summary="List child QSeal nodes under a parent",
)
def list_children(
    parent_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.list_children(parent_id, org_id, page, page_size)


# ── Map QSeals ────────────────────────────────────────────────────────────────


@router.post(
    "/parents/{parent_id}/map",
    response_model=QSealMapResponse,
    summary="Map existing child QSeal nodes to a parent",
)
def map_children(
    parent_id: UUID,
    req: QSealMapRequest,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.map_children(parent_id, req, org_id)


# ── QSeal Scan ────────────────────────────────────────────────────────────────


@router.post(
    "/scan",
    response_model=QSealScanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a QSeal scan (public — called by QSeal landing page)",
)
def record_scan(
    req: QSealScanRequest,
    request: Request,
    organization_id: UUID = Query(...),
    service: QSealService = Depends(get_service),
):
    """No auth required — called from the consumer-facing QSeal landing page."""
    return service.record_scan(
        req,
        organization_id,
        request_headers=dict(request.headers),
        client_ip=request.client.host if request.client else None,
    )


# ── QSeal History ─────────────────────────────────────────────────────────────


@router.get(
    "/history",
    response_model=QSealHistoryResponse,
    dependencies=[Depends(require_feature_flag(ANALYTICS_MODULE_ENABLED))],
    summary="Get QSeal scan history",
)
def get_scan_history(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    product_id: UUID | None = Query(None),
    block_id: UUID | None = Query(None),
    batch: str | None = Query(None),
    qseal_type: str | None = Query(None),
    risk_filter: str | None = Query(None),
    serial_number: str | None = Query(
        None, description="Filter to a specific node serial"
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: QSealService = Depends(get_service),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
):
    org_id = current_user.organization_id
    return service.get_scan_history(
        org_id,
        serial_number,
        page,
        page_size,
        date_from,
        date_to,
        product_id,
        block_id,
        batch,
        qseal_type,
        risk_filter,
    )


# ── Client-facing QSeal Analytics ────────────────────────────────────────────


def _analytics_filters(
    date_from: datetime | None,
    date_to: datetime | None,
    product_id: UUID | None,
    block_id: UUID | None,
    batch: str | None,
    qseal_type: str | None,
    serial_number: str | None,
    risk_filter: str | None = None,
) -> dict:
    return {
        "date_from": date_from,
        "date_to": date_to,
        "product_id": product_id,
        "block_id": block_id,
        "batch": batch,
        "qseal_type": qseal_type,
        "serial_number": serial_number,
        "risk_filter": risk_filter,
    }


@router.get(
    "/analytics/summary",
    response_model=QSealAnalyticsSummaryResponse,
    dependencies=[Depends(require_feature_flag(ANALYTICS_MODULE_ENABLED))],
    summary="Get client-facing QSeal scan summary",
)
def get_qseal_analytics_summary(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    product_id: UUID | None = Query(None),
    block_id: UUID | None = Query(None),
    batch: str | None = Query(None),
    qseal_type: str | None = Query(None),
    serial_number: str | None = Query(None),
    risk_filter: str | None = Query(None),
    service: QSealService = Depends(get_service),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
):
    return service.get_scan_analytics_summary(
        current_user.organization_id,
        **_analytics_filters(date_from, date_to, product_id, block_id, batch, qseal_type, serial_number, risk_filter),
    )


@router.get(
    "/analytics/suspicious",
    response_model=QSealSuspiciousScanResponse,
    dependencies=[Depends(require_feature_flag(ANALYTICS_MODULE_ENABLED))],
    summary="List suspicious QSeal scan events",
)
def get_qseal_suspicious_analytics(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    product_id: UUID | None = Query(None),
    batch: str | None = Query(None),
    serial_number: str | None = Query(None),
    risk_filter: str | None = Query(None),
    review_status: str | None = Query(None),
    min_risk_score: int | None = Query(None, ge=0, le=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: QSealService = Depends(get_service),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
):
    return service.get_suspicious_scan_analytics(
        current_user.organization_id,
        page=page,
        page_size=page_size,
        review_status=review_status,
        limit_score=min_risk_score,
        **_analytics_filters(
            date_from, date_to, product_id, None, batch, None, serial_number, risk_filter
        ),
    )


@router.patch(
    "/analytics/suspicious/{event_id}",
    response_model=QSealHistoryItem,
    dependencies=[Depends(require_feature_flag(ANALYTICS_MODULE_ENABLED))],
    summary="Review or dismiss a suspicious QSeal scan",
)
def review_qseal_suspicious_scan(
    event_id: UUID,
    data: QSealSuspiciousReviewRequest,
    service: QSealService = Depends(get_service),
    current_user: CurrentUser = Depends(require_permission("qr_product.update")),
):
    return service.review_suspicious_scan(
        event_id, current_user.organization_id, data.review_status
    )


@router.get(
    "/analytics/trends",
    response_model=QSealScanTrendResponse,
    dependencies=[Depends(require_feature_flag(ANALYTICS_MODULE_ENABLED))],
    summary="Get QSeal scan trends over time",
)
def get_qseal_analytics_trends(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    product_id: UUID | None = Query(None),
    block_id: UUID | None = Query(None),
    batch: str | None = Query(None),
    qseal_type: str | None = Query(None),
    serial_number: str | None = Query(None),
    risk_filter: str | None = Query(None),
    service: QSealService = Depends(get_service),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
):
    return service.get_scan_analytics_trends(
        current_user.organization_id,
        **_analytics_filters(date_from, date_to, product_id, block_id, batch, qseal_type, serial_number, risk_filter),
    )


@router.get(
    "/analytics/products",
    response_model=QSealProductAnalyticsResponse,
    dependencies=[Depends(require_feature_flag(ANALYTICS_MODULE_ENABLED))],
    summary="Get product-level QSeal scan analytics",
)
def get_qseal_product_analytics(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    product_id: UUID | None = Query(None),
    block_id: UUID | None = Query(None),
    batch: str | None = Query(None),
    qseal_type: str | None = Query(None),
    serial_number: str | None = Query(None),
    risk_filter: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    service: QSealService = Depends(get_service),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
):
    return service.get_product_scan_analytics(
        current_user.organization_id,
        limit=limit,
        **_analytics_filters(date_from, date_to, product_id, block_id, batch, qseal_type, serial_number, risk_filter),
    )


@router.get(
    "/analytics/geography",
    response_model=QSealGeographyAnalyticsResponse,
    dependencies=[Depends(require_feature_flag(ANALYTICS_MODULE_ENABLED))],
    summary="Get geographic distribution of QSeal scans",
)
def get_qseal_geography_analytics(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    product_id: UUID | None = Query(None),
    block_id: UUID | None = Query(None),
    batch: str | None = Query(None),
    qseal_type: str | None = Query(None),
    serial_number: str | None = Query(None),
    risk_filter: str | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    service: QSealService = Depends(get_service),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
):
    return service.get_geography_scan_analytics(
        current_user.organization_id,
        limit=limit,
        **_analytics_filters(date_from, date_to, product_id, block_id, batch, qseal_type, serial_number, risk_filter),
    )


@router.get(
    "/analytics/devices",
    response_model=QSealDeviceAnalyticsResponse,
    dependencies=[Depends(require_feature_flag(ANALYTICS_MODULE_ENABLED))],
    summary="Get QSeal scans grouped by device type",
)
def get_qseal_device_analytics(
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    product_id: UUID | None = Query(None),
    block_id: UUID | None = Query(None),
    batch: str | None = Query(None),
    qseal_type: str | None = Query(None),
    serial_number: str | None = Query(None),
    risk_filter: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    service: QSealService = Depends(get_service),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
):
    return service.get_device_scan_analytics(
        current_user.organization_id,
        limit=limit,
        **_analytics_filters(date_from, date_to, product_id, block_id, batch, qseal_type, serial_number, risk_filter),
    )


# ── Label Download ────────────────────────────────────────────────────────────


@router.get(
    "/parents/{parent_id}/labels",
    response_model=QSealLabelDownloadResponse,
    summary="Download label data for all children of a parent node",
)
def get_labels(
    parent_id: UUID,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_labels(parent_id, org_id)


# ── Parent with Linked Units (for inbound/receiving) ─────────────────────────


@router.get(
    "/parents/{parent_id}/linked-units",
    response_model=QSealParentDetailResponse,
    summary="Get parent QSeal with all linked child units (for inbound scanning)",
)
def get_parent_linked_units(
    parent_id: UUID,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    """Returns parent node + all QSealParameters children linked to it.

    Mobile app flow: scan parent QR → get serial → resolve node ID →
    call this endpoint → show all linked units → create receiving slip.
    """
    org_id = current_user.organization_id
    return service.get_parent_with_linked_units(parent_id, org_id)


# ── Block-based Parent QSeal ──────────────────────────────────────────────────


@router.get(
    "/blocks/{block_id}/parents",
    summary="List QSeal parent nodes created for a QR block's master packs",
)
def get_block_parents(
    block_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    return service.get_parents_by_block(block_id, org_id, page, page_size)


@router.get(
    "/blocks/{block_id}/parents/download",
    summary="Download Excel file with parent QSeal QR codes for a block",
)
def download_block_parents(
    block_id: UUID,
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = current_user.organization_id
    excel_bytes, filename = service.get_parents_excel(block_id, org_id)
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Auto-link (automatic cascade / aggregation) ─────────────────────────────


@router.post(
    "/blocks/{block_id}/auto-link",
    response_model=QSealAutoLinkResponse,
    summary="Auto-link a completed block's items into master packs (cascade)",
)
def auto_link_block(
    block_id: UUID,
    data: QSealAutoLinkRequest | None = Body(default=None),
    service: QSealService = Depends(get_service),
    current_user: CurrentUser = Depends(require_permission("qr_product.create")),
):
    """Automatically group a block's generated units into master packs.

    Useful for bulk testing where manual linking/cascading via mobile is slow.
    Re-running is idempotent: previous linkage is removed and rebuilt.
    """
    org_id = current_user.organization_id
    return service.auto_link_block(
        block_id,
        org_id,
        current_user.id,
        data.master_pack_size if data else None,
    )


# ── Aggregation log ─────────────────────────────────────────────────────────


@router.get(
    "/aggregation",
    response_model=QSealAggregationResponse | QSealAggregationGroupedResponse,
    summary="List QSeal aggregation (cascading) log",
)
def list_aggregation(
    block_id: UUID | None = Query(
        None, description="Filter the log to a specific QR block/batch"
    ),
    grouped: bool = Query(
        False,
        description="Group child units under their parent (master-pack) box",
    ),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    service: QSealService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    """Return one row per generated unit with its parent link + activation.

    Pass ``grouped=true`` to nest child units under their parent box.
    """
    org_id = current_user.organization_id
    return service.list_aggregation(org_id, block_id, page, page_size, grouped)
