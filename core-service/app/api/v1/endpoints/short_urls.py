"""URL Management endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.dependencies import get_current_user
from app.database import get_db
from app.schemas.short_url import (
    ResolveURLResponse,
    ShortURLCreate,
    ShortURLListResponse,
    ShortURLResponse,
    ShortURLUpdate,
)
from app.services.short_url_service import ShortURLService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> ShortURLService:
    return ShortURLService(db)


# ── Generate ──────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ShortURLResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a short URL",
)
def generate_short_url(
    data: ShortURLCreate,
    service: ShortURLService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    return service.generate(data, org_id, user_id)


# ── Resolve (public) ──────────────────────────────────────────────────────────

@router.get(
    "/resolve/{slug}",
    response_model=ResolveURLResponse,
    summary="Resolve a short URL slug (public — increments click count)",
)
def resolve_short_url(
    slug: str,
    service: ShortURLService = Depends(get_service),
):
    """No auth required — called when a short link is clicked."""
    return service.resolve(slug)


# ── List ──────────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=ShortURLListResponse,
    summary="List short URLs for the organization",
)
def list_short_urls(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    is_active: bool | None = Query(None),
    search: str | None = Query(None, description="Search by slug or title"),
    service: ShortURLService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.list_urls(org_id, page, page_size, is_active, search)


# ── Get ───────────────────────────────────────────────────────────────────────

@router.get(
    "/{url_id}",
    response_model=ShortURLResponse,
    summary="Get a short URL by ID",
)
def get_short_url(
    url_id: UUID,
    service: ShortURLService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.get_url(url_id, org_id)


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch(
    "/{url_id}",
    response_model=ShortURLResponse,
    summary="Update a short URL",
)
def update_short_url(
    url_id: UUID,
    data: ShortURLUpdate,
    service: ShortURLService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.update_url(url_id, data, org_id)


# ── Delete ────────────────────────────────────────────────────────────────────

@router.delete(
    "/{url_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a short URL",
)
def delete_short_url(
    url_id: UUID,
    service: ShortURLService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    service.delete_url(url_id, org_id)
