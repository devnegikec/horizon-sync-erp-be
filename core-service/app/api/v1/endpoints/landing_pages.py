"""Landing Page Config API endpoints.

Nested under /api/v1/products/{productId}/landing-page
"""

from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.landing_page import (
    ImageUploadResponse,
    LandingPageConfigCreate,
    LandingPageConfigResponse,
    LandingPageConfigUpdate,
)
from app.services.landing_page_service import LandingPageService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> LandingPageService:
    return LandingPageService(db)


# ─────────────────────────────────────────────────────────────────────────────
# Public router — no auth, for consumer-facing QR landing pages
# ─────────────────────────────────────────────────────────────────────────────

public_router = APIRouter()


@public_router.get(
    "/{product_id}/landing-page",
    response_model=LandingPageConfigResponse,
    summary="[Public] Fetch landing page config for QR verification page",
)
def get_landing_page_public(
    product_id: UUID,
    organization_id: UUID = Query(
        ..., description="Organization that owns the QR product"
    ),
    service: LandingPageService = Depends(get_service),
):
    """Public endpoint — no auth required.

    Called by the consumer-facing QR verification page to render
    the custom landing page for a scanned product.
    """
    config = service.get_config(product_id, organization_id)
    return {"config": config}


# ─────────────────────────────────────────────────────────────────────────────
# Authenticated router — for dashboard/admin management
# ─────────────────────────────────────────────────────────────────────────────


# ── Fetch Config ──────────────────────────────────────────────────────────


@router.get(
    "/{product_id}/landing-page",
    response_model=LandingPageConfigResponse,
    summary="Fetch landing page config",
)
def get_landing_page(
    product_id: UUID,
    service: LandingPageService = Depends(get_service),
    current_user: dict = Depends(CurrentUser),
):
    """Get the landing page configuration for a QR product."""
    org_id = UUID(current_user["organization_id"])
    config = service.get_config(product_id, org_id)
    return {"config": config}


# ── Create Config ─────────────────────────────────────────────────────────


@router.post(
    "/{product_id}/landing-page",
    response_model=LandingPageConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create landing page config",
)
def create_landing_page(
    product_id: UUID,
    data: LandingPageConfigCreate,
    current_user: dict = Depends(require_permission("landing_page.create")),
    service: LandingPageService = Depends(get_service),
):
    """Create a landing page configuration for a QR product.

    Only one config per product is allowed. Returns 409 if one already exists.
    """
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    config = service.create_config(product_id, data, org_id, user_id)
    return {"config": config}


# ── Update Config ─────────────────────────────────────────────────────────


@router.patch(
    "/{product_id}/landing-page",
    response_model=LandingPageConfigResponse,
    summary="Update landing page config",
)
def update_landing_page(
    product_id: UUID,
    data: LandingPageConfigUpdate,
    current_user: dict = Depends(require_permission("landing_page.update")),
    service: LandingPageService = Depends(get_service),
):
    """Partial update. Send only the fields you want to change.

    Nested objects (product_details, feedback, warranty, custom_cta, footer)
    are deep-merged. Array fields (social_links) are replaced entirely.
    """
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    config = service.update_config(product_id, data, org_id, user_id)
    return {"config": config}


# ── Delete Config ─────────────────────────────────────────────────────────


@router.delete(
    "/{product_id}/landing-page",
    summary="Delete landing page config",
)
def delete_landing_page(
    product_id: UUID,
    current_user: dict = Depends(require_permission("landing_page.delete")),
    service: LandingPageService = Depends(get_service),
):
    """Delete the landing page configuration for a QR product."""
    org_id = UUID(current_user["organization_id"])
    service.delete_config(product_id, org_id)
    return {"success": True}


# ── Upload Image ──────────────────────────────────────────────────────────


@router.post(
    "/{product_id}/landing-page/upload-image",
    response_model=ImageUploadResponse,
    summary="Upload logo or banner image",
)
async def upload_landing_page_image(
    product_id: UUID,
    file: UploadFile = File(..., description="PNG or JPEG image, max 5 MB"),
    image_type: str = Form(..., description='"logo" or "banner"'),
    current_user: dict = Depends(require_permission("landing_page.upload_image")),
    service: LandingPageService = Depends(get_service),
):
    """Upload a logo or banner image for the landing page.

    - **logo**: 300×300px recommended (displayed at 80×80px)
    - **banner**: 1200×400px recommended (3:1 aspect ratio)

    Returns the URL you can use in the landing page config.
    """
    org_id = UUID(current_user["organization_id"])

    if image_type not in ("logo", "banner"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='image_type must be "logo" or "banner"',
        )

    return await service.upload_image(product_id, file, image_type, org_id)
