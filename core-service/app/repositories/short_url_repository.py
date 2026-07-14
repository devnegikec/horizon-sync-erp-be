"""Repository for URL Management module"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.short_url import ShortURL


class ShortURLRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> ShortURL:
        url = ShortURL(**data)
        self.db.add(url)
        self.db.commit()
        self.db.refresh(url)
        return url

    def get_by_id(self, url_id: UUID, organization_id: UUID) -> ShortURL | None:
        return (
            self.db.query(ShortURL)
            .filter(ShortURL.id == url_id, ShortURL.organization_id == organization_id)
            .first()
        )

    def get_by_slug(self, slug: str) -> ShortURL | None:
        """Slug lookup is global — slugs are unique across all orgs."""
        return self.db.query(ShortURL).filter(ShortURL.slug == slug).first()

    def slug_exists(self, slug: str) -> bool:
        return self.db.query(ShortURL.id).filter(ShortURL.slug == slug).first() is not None

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[ShortURL], int]:
        q = self.db.query(ShortURL).filter(ShortURL.organization_id == organization_id)
        if is_active is not None:
            q = q.filter(ShortURL.is_active == is_active)
        if search:
            q = q.filter(
                ShortURL.slug.ilike(f"%{search}%") | ShortURL.title.ilike(f"%{search}%")
            )
        total = q.count()
        items = (
            q.order_by(ShortURL.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update(self, url: ShortURL, data: dict) -> ShortURL:
        for k, v in data.items():
            setattr(url, k, v)
        self.db.commit()
        self.db.refresh(url)
        return url

    def increment_clicks(self, url: ShortURL) -> None:
        url.click_count = (url.click_count or 0) + 1
        self.db.commit()

    def delete(self, url: ShortURL) -> None:
        self.db.delete(url)
        self.db.commit()
