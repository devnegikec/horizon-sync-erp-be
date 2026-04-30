"""Landing / Public API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.qr_activation import (
    CurrencyByMarketRequest,
    CurrencyByMarketResponse,
    DestinationMarketListResponse,
    DestinationMarketResponse,
    ProductActivationRequest,
    ProductActivationResponse,
    ProductExpiryRequest,
    ProductExpiryResponse,
    QRScanRequest,
    QRScanResponse,
    QRSettingsCreateRequest,
    QRSettingsResponse,
)
from app.services.qr_activation_service import QRActivationService

router = APIRouter()


# ── Destination Market ────────────────────────────────────────────────────────

@router.get(
    "/destination-markets",
    response_model=DestinationMarketListResponse,
    summary="List destination markets",
)
async def list_destination_markets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
    db: Session = Depends(get_db),
):
    svc = QRActivationService(db)
    markets, pagination = svc.list_destination_markets(
        current_user.organization_id, page, page_size, search
    )
    return DestinationMarketListResponse(
        markets=[DestinationMarketResponse.model_validate(m) for m in markets],
        pagination=pagination,
    )


@router.post(
    "/destination-markets/currency",
    response_model=CurrencyByMarketResponse,
    summary="Get currency for a destination market",
)
async def get_currency(
    req: CurrencyByMarketRequest,
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
    db: Session = Depends(get_db),
):
    svc = QRActivationService(db)
    currency = svc.get_currency_by_market(req.name, current_user.organization_id)
    return CurrencyByMarketResponse(currency=currency)


# ── Product Expiry ────────────────────────────────────────────────────────────

@router.post(
    "/products/expiry",
    response_model=ProductExpiryResponse,
    summary="Calculate product expiry date",
)
async def calculate_expiry(
    req: ProductExpiryRequest,
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
    db: Session = Depends(get_db),
):
    svc = QRActivationService(db)
    expiry_date = svc.calculate_expiry(
        req.product_id, current_user.organization_id, req.manufacturing_date
    )
    return ProductExpiryResponse(expiry_date=expiry_date)


# ── QR Scan ───────────────────────────────────────────────────────────────────

@router.post(
    "/qr/scan",
    response_model=QRScanResponse,
    summary="Scan QR and check activation status",
)
async def scan_qr(
    req: QRScanRequest,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
    db: Session = Depends(get_db),
):
    svc = QRActivationService(db)
    tenant_schema = request.headers.get("X-Tenant-Schema", "public")
    result = svc.scan_qr(req, current_user.organization_id, tenant_schema)
    return QRScanResponse(**result)


# ── Product Activation ────────────────────────────────────────────────────────

@router.post(
    "/qr/activate",
    response_model=ProductActivationResponse,
    summary="Activate product items by serial numbers",
)
async def activate_products(
    req: ProductActivationRequest,
    current_user: CurrentUser = Depends(require_permission("qr_activation.create")),
    db: Session = Depends(get_db),
):
    svc = QRActivationService(db)
    svc.activate_products(req.srnumber, current_user.organization_id)
    return ProductActivationResponse(message="Activated")


# ── QR Settings ──────────────────────────────────────────────────────────────

@router.post(
    "/qr/settings",
    summary="Create or update QR activation settings",
)
async def create_or_update_qr_settings(
    req: QRSettingsCreateRequest,
    current_user: CurrentUser = Depends(require_permission("qr_activation.create")),
    db: Session = Depends(get_db),
):
    svc = QRActivationService(db)
    svc.create_or_update_qr_settings(req, current_user.organization_id)
    return {"message": "QR activation settings saved successfully"}
   


@router.get(
    "/qr/settings/{product_id}",
    response_model=QRSettingsResponse,
    summary="Get QR activation settings for a product",
)
async def get_qr_settings(
    product_id: UUID,
    current_user: CurrentUser = Depends(require_permission("qr_activation.read")),
    db: Session = Depends(get_db),
):
    svc = QRActivationService(db)
    return svc.get_qr_settings(product_id, current_user.organization_id)







# @router.get(
#     "/products",
#     response_model=LandingProductListResponse,
#     summary="List all products",
# )
# async def list_products(
#     page: int = Query(1, ge=1),
#     page_size: int = Query(20, ge=1, le=100),
#     search: str | None = Query(None),
#     is_active: bool | None = Query(None),
#     current_user: CurrentUser = Depends(require_permission("landing.read")),
#     db: Session = Depends(get_db),
# ):
#     svc = QRActivationService(db)
#     products, pagination = svc.list_products(
#         current_user.organization_id, page, page_size, search, is_active
#     )
#     return LandingProductListResponse(
#         products=[LandingProductResponse.model_validate(p) for p in products],
#         pagination=pagination,
#     )


# @router.get(
#     "/products/{product_id}",
#     response_model=LandingProductResponse,
#     summary="Get product detail",
# )
# async def get_product(
#     product_id: UUID,
#     current_user: CurrentUser = Depends(require_permission("landing.read")),
#     db: Session = Depends(get_db),
# ):
#     svc = QRActivationService(db)
#     product = svc.get_product(product_id, current_user.organization_id)
#     return LandingProductResponse.model_validate(product)