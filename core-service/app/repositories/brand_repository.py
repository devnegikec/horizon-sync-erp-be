"""Repository for Brand database operations"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.brand import Brand


class BrandRepository:
    """Repository for brand database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Brand:
        """Create a new brand.

        Args:
            data: Dictionary containing brand data including organization_id,
                  name, short_code, public_key, private_key_encrypted, etc.

        Returns:
            Created Brand object.
        """
        brand = Brand(**data)
        self.db.add(brand)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def get_by_id(self, brand_id: UUID, organization_id: UUID) -> Brand | None:
        """Get brand by ID within an organization.

        Args:
            brand_id: Brand UUID.
            organization_id: Organization UUID for tenant isolation.

        Returns:
            Brand object or None if not found.
        """
        return (
            self.db.query(Brand)
            .filter(
                Brand.id == brand_id,
                Brand.organization_id == organization_id,
                Brand.deleted_at.is_(None),
            )
            .first()
        )

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[Brand], int]:
        """List brands with pagination and optional search.

        Args:
            organization_id: Organization UUID for tenant isolation.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            search: Optional search term for name or short_code.

        Returns:
            Tuple of (list of brands, total count).
        """
        query = self.db.query(Brand).filter(
            Brand.organization_id == organization_id,
            Brand.deleted_at.is_(None),
        )

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Brand.name.ilike(search_term),
                    Brand.short_code.ilike(search_term),
                )
            )

        total = query.count()
        items = (
            query.order_by(Brand.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update(self, brand: Brand, data: dict) -> Brand:
        """Update brand fields.

        Args:
            brand: Brand object to update.
            data: Dictionary of fields to update.

        Returns:
            Updated Brand object.
        """
        for key, value in data.items():
            setattr(brand, key, value)
        self.db.commit()
        self.db.refresh(brand)
        return brand

    def soft_delete(self, brand: Brand, user_id: UUID) -> None:
        """Soft-delete a brand.

        Args:
            brand: Brand object to delete.
            user_id: UUID of the user performing the deletion.
        """
        brand.deleted_at = datetime.now(UTC)
        brand.updated_by = user_id
        self.db.commit()
