"""QR Products API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.qr_product import (
    AuthenticateRequest,
    AuthenticateResponse,
    ProductItemListResponse,
    ProductItemResponse,
    QRActivationParamsCreate,
    QRActivationParamsResponse,
    QRBlockCreate,
    QRBlockResponse,
    QRProductCreate,
    QRProductListResponse,
    QRProductResponse,
    QRProductUpdate,
    QRValidateRequest,
    QRValidateResponse,
    ScanAnalyticsResponse,
)
from app.services.qr_product_service import QRProductService

router = APIRouter()


# ── Products ──────────────────────────────────────────────────────────────────


@router.post(
    "",
    response_model=QRProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create QR product",
)
async def create_qr_product(
    data: QRProductCreate,
    current_user: CurrentUser = Depends(require_permission("qr_product.create")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    product = svc.create_product(data, current_user.organization_id, current_user.id)
    return QRProductResponse.model_validate(product)


@router.get(
    "",
    response_model=QRProductListResponse,
    summary="List QR products",
)
async def list_qr_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    is_active: bool | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    products, pagination = svc.list_products(
        current_user.organization_id, page, page_size, search, is_active
    )
    return QRProductListResponse(
        products=[QRProductResponse.model_validate(p) for p in products],
        pagination=pagination,
    )


@router.get(
    "/{product_id}",
    response_model=QRProductResponse,
    summary="Get QR product",
)
async def get_qr_product(
    product_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    return QRProductResponse.model_validate(
        svc.get_product(product_id, current_user.organization_id)
    )


@router.patch(
    "/{product_id}",
    response_model=QRProductResponse,
    summary="Update QR product",
)
async def update_qr_product(
    product_id: UUID,
    data: QRProductUpdate,
    current_user: CurrentUser = Depends(require_permission("qr_product.update")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    product = svc.update_product(
        product_id, data, current_user.organization_id, current_user.id
    )
    return QRProductResponse.model_validate(product)


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete QR product",
)
async def delete_qr_product(
    product_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_product.delete")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    svc.delete_product(product_id, current_user.organization_id, current_user.id)


# ── QR Blocks ─────────────────────────────────────────────────────────────────


@router.post(
    "/{product_id}/blocks",
    response_model=QRBlockResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate QR block",
    description="Generate a batch of QR codes for a product. Checks monthly credit quota.",
)
async def generate_qr_block(
    product_id: UUID,
    data: QRBlockCreate,
    current_user: CurrentUser = Depends(require_permission("qr_product.create")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    block = svc.generate_block(
        product_id, data, current_user.organization_id, current_user.id
    )
    return QRBlockResponse.model_validate(block)


@router.get(
    "/{product_id}/blocks",
    summary="List QR blocks for a product",
)
async def list_qr_blocks(
    product_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    blocks, pagination = svc.list_blocks(
        product_id, current_user.organization_id, page, page_size
    )
    return {
        "blocks": [QRBlockResponse.model_validate(b) for b in blocks],
        "pagination": pagination,
    }


# ── Product Items ─────────────────────────────────────────────────────────────


@router.get(
    "/blocks/{block_id}/items",
    response_model=ProductItemListResponse,
    summary="List product items (serial numbers) in a block",
)
async def list_product_items(
    block_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    items, pagination = svc.list_items(
        block_id, current_user.organization_id, page, page_size
    )
    return ProductItemListResponse(
        items=[ProductItemResponse.model_validate(i) for i in items],
        pagination=pagination,
    )


# ── QR Validate (public — no auth required) ───────────────────────────────────


@router.post(
    "/validate",
    response_model=QRValidateResponse,
    summary="Validate / authenticate a QR code scan",
    description=(
        "Public endpoint called when a consumer scans a QR code. "
        "Records the scan event and returns authenticity status."
    ),
)
async def validate_qr(
    organization_id: UUID,
    req: QRValidateRequest,
    db: Session = Depends(get_db),
):
    """
    No auth required — this is called from the consumer-facing landing page.
    organization_id is passed as a query param (embedded in the QR URL).
    """
    svc = QRProductService(db)
    result = svc.validate_qr(organization_id, req)
    return QRValidateResponse(**result)


# ── QR Authenticate (public — no auth required) ───────────────────────────────


@router.post(
    "/authenticate",
    response_model=AuthenticateResponse,
    summary="Authenticate a QR code via ECDSA signature",
    description="Public endpoint for cryptographic QR verification. No auth required.",
)
async def authenticate_qr(
    organization_id: UUID,
    req: AuthenticateRequest,
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    result = svc.authenticate(organization_id, req)
    return AuthenticateResponse(**result)


# ── Scan Analytics ────────────────────────────────────────────────────────────


@router.get(
    "/{product_id}/analytics",
    response_model=ScanAnalyticsResponse,
    summary="Get scan analytics for a product",
)
async def get_scan_analytics(
    product_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    data = svc.get_scan_analytics(product_id, current_user.organization_id)
    return ScanAnalyticsResponse(**data)


# ── Activation Parameters ─────────────────────────────────────────────────────


@router.post(
    "/activation-params",
    response_model=QRActivationParamsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set QR activation parameters",
)
async def set_activation_params(
    data: QRActivationParamsCreate,
    current_user: CurrentUser = Depends(require_permission("qr_product.create")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    params = svc.set_activation_params(
        data, current_user.organization_id, current_user.id
    )
    return QRActivationParamsResponse.model_validate(params)
