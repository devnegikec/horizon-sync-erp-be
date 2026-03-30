"""QR Products API endpoints"""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.qr_product import (
    AuthenticateRequest,
    AuthenticateResponse,
    BlockDownloadResponse,
    OrgBlockListItem,
    OrgBlockListResponse,
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


# ── QR Blocks (literal paths — MUST be before /{product_id} routes) ───────────


@router.get(
    "/blocks",
    response_model=OrgBlockListResponse,
    summary="List all QR blocks for the organization",
    description="Returns all QR blocks across every product in the authenticated user's organization.",
)
async def list_org_qr_blocks(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Literal["pending", "in_progress", "completed", "failed"] | None = Query(None),
    product_id: UUID | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    blocks, pagination = svc.list_blocks_by_org(
        current_user.organization_id, page, page_size, status, product_id
    )
    return OrgBlockListResponse(
        blocks=[OrgBlockListItem(**b) for b in blocks],
        pagination=pagination,
    )


@router.get(
    "/blocks/{block_id}",
    response_model=QRBlockResponse,
    summary="Get QR block detail",
    description="Returns a single QR block with its current generation status. Poll this until status is 'completed' or 'failed'.",
)
async def get_qr_block(
    block_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    block = svc.get_block(block_id, current_user.organization_id)
    return QRBlockResponse.model_validate(block)


@router.get(
    "/blocks/{block_id}/download",
    summary="Download Excel file for a completed QR block",
    description=(
        "Returns a signed GCS URL if available, otherwise streams the Excel file directly. "
        "Returns 409 if the block is not yet completed."
    ),
)
async def get_block_download_url(
    block_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    from io import BytesIO

    from fastapi.responses import RedirectResponse, StreamingResponse

    svc = QRProductService(db)

    # Try signed URL first (GCS path stored on block)
    try:
        signed_url, expires_at = svc.get_block_download_url(
            block_id, current_user.organization_id
        )
        return BlockDownloadResponse(signed_url=signed_url, expires_at=expires_at)
    except Exception as exc:
        # Re-raise anything that isn't "download_url not set"
        from fastapi import HTTPException as FHTTPException
        if isinstance(exc, FHTTPException) and exc.status_code == 409:
            raise  # block not completed — propagate 409
        if isinstance(exc, FHTTPException) and exc.status_code != 404:
            raise

    # Fallback: generate Excel on-demand and stream it
    excel_bytes, filename = svc.get_block_excel_stream(
        block_id, current_user.organization_id
    )
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


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


# ── Per-product routes (/{product_id} — MUST be after all /blocks/... routes) ─


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
