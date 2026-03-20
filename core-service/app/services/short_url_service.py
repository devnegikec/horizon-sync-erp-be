"""Service layer for URL Management module"""

import random
import string
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.short_url_repository import ShortURLRepository
from app.schemas.short_url import ShortURLCreate, ShortURLUpdate

BASE_URL = "https://qsl.ink"  # configurable short domain
SLUG_LENGTH = 8


def _generate_slug(length: int = SLUG_LENGTH) -> str:
    chars = string.ascii_letters + string.digits
    return "".join(random.choices(chars, k=length))


class ShortURLService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = ShortURLRepository(db)

    def _build_response(self, url) -> dict:
        d = {c.name: getattr(url, c.name) for c in url.__table__.columns}
        d["short_url"] = f"{BASE_URL}/{url.slug}"
        return d

    def _paginate(self, total, page, page_size) -> dict:
        total_pages = max(1, (total + page_size - 1) // page_size)
        return {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    # ── Generate ──────────────────────────────────────────────────────────────

    def generate(self, data: ShortURLCreate, organization_id: UUID, user_id: UUID):
        # Resolve slug
        if data.slug:
            if self.repo.slug_exists(data.slug):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Slug '{data.slug}' is already taken.",
                )
            slug = data.slug
        else:
            # Auto-generate a unique slug
            for _ in range(10):
                candidate = _generate_slug()
                if not self.repo.slug_exists(candidate):
                    slug = candidate
                    break
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Could not generate a unique slug. Try again.",
                )

        payload = data.model_dump(exclude={"slug"})
        payload["slug"] = slug
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id

        url = self.repo.create(payload)
        return self._build_response(url)

    # ── Resolve ───────────────────────────────────────────────────────────────

    def resolve(self, slug: str) -> dict:
        """Public — look up a slug and increment click counter."""
        url = self.repo.get_by_slug(slug)
        if not url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Short URL '{slug}' not found.")

        if not url.is_active:
            raise HTTPException(status_code=status.HTTP_410_GONE,
                                detail="This short URL has been deactivated.")

        if url.expires_at and url.expires_at < datetime.now(UTC):
            raise HTTPException(status_code=status.HTTP_410_GONE,
                                detail="This short URL has expired.")

        self.repo.increment_clicks(url)

        return {
            "slug": url.slug,
            "original_url": url.original_url,
            "click_count": url.click_count,
            "is_active": url.is_active,
            "expires_at": url.expires_at,
        }

    # ── List ──────────────────────────────────────────────────────────────────

    def list_urls(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        search: str | None = None,
    ):
        items, total = self.repo.list(organization_id, page, page_size, is_active, search)
        return {
            "urls": [self._build_response(u) for u in items],
            "pagination": self._paginate(total, page, page_size),
        }

    # ── Get ───────────────────────────────────────────────────────────────────

    def get_url(self, url_id: UUID, organization_id: UUID):
        url = self.repo.get_by_id(url_id, organization_id)
        if not url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Short URL not found.")
        return self._build_response(url)

    # ── Update ────────────────────────────────────────────────────────────────

    def update_url(self, url_id: UUID, data: ShortURLUpdate, organization_id: UUID):
        url = self.repo.get_by_id(url_id, organization_id)
        if not url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Short URL not found.")
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        url = self.repo.update(url, payload)
        return self._build_response(url)

    # ── Delete ────────────────────────────────────────────────────────────────

    def delete_url(self, url_id: UUID, organization_id: UUID) -> None:
        url = self.repo.get_by_id(url_id, organization_id)
        if not url:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Short URL not found.")
        self.repo.delete(url)
