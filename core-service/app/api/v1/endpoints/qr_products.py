"""QR Products API endpoints"""

from datetime import datetime
from typing import Literal
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.config import settings
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
    QRProductImageResponse,
    QRProductListResponse,
    QRProductResponse,
    QRProductUpdate,
    QRValidateRequest,
    QRValidateResponse,
    ScanAnalyticsResponse,
)
from app.services.qr_block_queue import enqueue_qr_block
from app.services.qr_product_service import QRProductService
from app.services.storage_service import (
    PRODUCT_IMAGE_CONTENT_TYPES,
    delete_product_image,
    read_product_image,
    store_product_image,
)

router = APIRouter()


def _stored_image_key(url: str | None) -> str | None:
    marker = "/api/v1/qr-products/image-files/"
    if not url or marker not in url:
        return None
    return url.split(marker, maxsplit=1)[1]


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
    "/image-files/{object_key:path}",
    name="get_qr_product_image_file",
    include_in_schema=False,
)
async def get_qr_product_image_file(object_key: str):
    try:
        data, content_type = read_product_image(object_key)
    except (FileNotFoundError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product image not found",
        ) from exc
    return Response(
        content=data,
        media_type=content_type,
        headers={
            "Cache-Control": "public, max-age=31536000, immutable",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.post(
    "/{product_id}/images/{image_type}",
    response_model=QRProductImageResponse,
    summary="Upload or replace a Product image",
)
async def upload_qr_product_image(
    product_id: UUID,
    image_type: Literal["logo", "banner"],
    request: Request,
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(require_permission("qr_product.update")),
    db: Session = Depends(get_db),
):
    content_type = (file.content_type or "").lower()
    if content_type not in PRODUCT_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PNG, JPEG, and WebP images are supported",
        )

    data = await file.read(settings.product_image_max_bytes + 1)
    if not data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Image file is empty",
        )
    if len(data) > settings.product_image_max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image exceeds the configured maximum size",
        )

    svc = QRProductService(db)
    svc.get_product(product_id, current_user.organization_id)
    try:
        object_key = store_product_image(
            data,
            content_type,
            current_user.organization_id,
            product_id,
            image_type,
        )
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

    image_url = str(request.url_for("get_qr_product_image_file", object_key=object_key))
    try:
        _, previous_url = svc.update_product_image(
            product_id,
            image_type,
            image_url,
            current_user.organization_id,
            current_user.id,
        )
    except Exception:
        delete_product_image(object_key)
        raise

    previous_key = _stored_image_key(previous_url)
    if previous_key:
        delete_product_image(previous_key)
    return QRProductImageResponse(image_type=image_type, url=image_url)


@router.delete(
    "/{product_id}/images/{image_type}",
    response_model=QRProductImageResponse,
    summary="Remove a Product image",
)
async def delete_qr_product_image(
    product_id: UUID,
    image_type: Literal["logo", "banner"],
    current_user: CurrentUser = Depends(require_permission("qr_product.update")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    _, previous_url = svc.update_product_image(
        product_id,
        image_type,
        None,
        current_user.organization_id,
        current_user.id,
    )
    previous_key = _stored_image_key(previous_url)
    if previous_key:
        delete_product_image(previous_key)
    return QRProductImageResponse(image_type=image_type, url=None)


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
    search: str | None = Query(None, min_length=1, max_length=100),
    status: Literal["pending", "in_progress", "completed", "failed"] | None = Query(
        None
    ),
    product_id: UUID | None = Query(None),
    qr_type: Literal["dynamic", "dual", "secure_code", "one_time"] | None = Query(None),
    created_from: datetime | None = Query(None),
    created_to: datetime | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    blocks, pagination = svc.list_blocks_by_org(
        current_user.organization_id,
        page,
        page_size,
        status,
        product_id,
        search,
        qr_type,
        created_from,
        created_to,
    )
    return OrgBlockListResponse(
        blocks=[OrgBlockListItem(**b) for b in blocks],
        pagination=pagination,
    )


@router.get(
    "/blocks/{block_id}",
    response_model=QRBlockResponse,
    summary="Get QR block detail",
    description=(
        "Returns a single QR block with generation status and an "
        "organization-scoped QR activation summary."
    ),
)
async def get_qr_block(
    block_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    block = svc.get_block_detail(block_id, current_user.organization_id)
    return QRBlockResponse.model_validate(block)


@router.post(
    "/blocks/{block_id}/retry",
    response_model=QRBlockResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed QR block generation job",
)
async def retry_qr_block(
    block_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_product.create")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    block = svc.retry_block_job(block_id, current_user.organization_id)
    task_id = str(uuid4())
    block = svc.assign_block_task(block.id, current_user.organization_id, task_id)
    try:
        enqueue_qr_block(block.id, current_user.organization_id, task_id)
    except Exception as exc:
        svc.fail_block_enqueue(block.id, current_user.organization_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QR generation queue is temporarily unavailable",
        ) from exc
    return QRBlockResponse.model_validate(block)


@router.get(
    "/blocks/{block_id}/download",
    summary="Download Excel file for a completed QR block",
    description=(
        "Returns a short-lived signed object-storage URL if available, otherwise "
        "streams the Excel file directly. "
        "Returns 409 if the block is not yet completed."
    ),
)
async def get_block_download_url(
    block_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    from io import BytesIO

    from fastapi.responses import FileResponse, StreamingResponse

    svc = QRProductService(db)

    # Prefer a private S3 artifact, while retaining the legacy stored URL path.
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

    # Fallback: serve from the local volume cache (core-service-volume) if present,
    # otherwise generate on-demand, cache it, and stream it.
    local_path = svc.get_block_local_artifact_path(
        block_id, current_user.organization_id
    )
    if local_path.is_file():
        return FileResponse(
            local_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=f"qr_block_{block_id}.xlsx",
        )

    excel_bytes, filename = svc.get_block_excel_stream(
        block_id, current_user.organization_id
    )
    try:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        local_path.write_bytes(excel_bytes)
        return FileResponse(
            local_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filename,
        )
    except Exception:
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
    deprecated=True,
)
async def validate_qr(
    req: QRValidateRequest,
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    result = svc.validate_qr(req)
    return QRValidateResponse(**result)


# ── QR Authenticate (public — no auth required) ───────────────────────────────


@router.post(
    "/authenticate",
    response_model=AuthenticateResponse,
    summary="Authenticate a QR code via ECDSA signature",
    description="Public endpoint for cryptographic QR verification. No auth required.",
    deprecated=True,
)
async def authenticate_qr(
    req: AuthenticateRequest,
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    result = svc.authenticate(req)
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
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate QR block",
    description=(
        "Validate and queue a QR generation batch. Credits are reserved until "
        "the background job completes or fails."
    ),
)
async def generate_qr_block(
    product_id: UUID,
    data: QRBlockCreate,
    current_user: CurrentUser = Depends(require_permission("qr_product.create")),
    db: Session = Depends(get_db),
):
    svc = QRProductService(db)
    block = svc.create_block_job(
        product_id, data, current_user.organization_id, current_user.id
    )
    task_id = str(uuid4())
    block = svc.assign_block_task(
        block.id,
        current_user.organization_id,
        task_id,
    )
    try:
        enqueue_qr_block(
            block.id,
            current_user.organization_id,
            task_id,
        )
    except Exception as exc:
        svc.fail_block_enqueue(block.id, current_user.organization_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="QR generation queue is temporarily unavailable",
        ) from exc
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
