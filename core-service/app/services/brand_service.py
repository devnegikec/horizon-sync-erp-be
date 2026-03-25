"""Brand service — orchestrates brand CRUD with automatic key generation on creation.

Requirements: 1.1, 1.5, 1.6, 3.1, 3.2
"""

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models.brand import Brand
from app.repositories.brand_repository import BrandRepository
from app.schemas.brand import BrandCreate, BrandUpdate
from app.services.key_service import KeyService


class BrandService:
    """Service for brand operations with automatic ECDSA key pair generation."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = BrandRepository(db)
        self.key_service = KeyService(settings.brand_key_encryption_secret)

    def create(
        self, data: BrandCreate, organization_id: UUID, user_id: UUID
    ) -> Brand:
        """Create a new brand with an auto-generated ECDSA P-256 key pair.

        Generates the key pair via KeyService and creates the brand record
        in a single transaction.

        Args:
            data: Brand creation payload (name, short_code).
            organization_id: Organization UUID for tenant isolation.
            user_id: UUID of the user creating the brand.

        Returns:
            Created Brand object.
        """
        encrypted_private_key, public_key_hex = self.key_service.generate_key_pair()

        brand_data = data.model_dump()
        brand_data["organization_id"] = organization_id
        brand_data["public_key"] = public_key_hex
        brand_data["private_key_encrypted"] = encrypted_private_key
        brand_data["created_by"] = user_id
        brand_data["updated_by"] = user_id

        return self.repo.create(brand_data)

    def get_by_id(self, brand_id: UUID, organization_id: UUID) -> Brand:
        """Get a brand by ID within an organization.

        Args:
            brand_id: Brand UUID.
            organization_id: Organization UUID for tenant isolation.

        Returns:
            Brand object.

        Raises:
            HTTPException: 404 if brand not found or belongs to another org.
        """
        brand = self.repo.get_by_id(brand_id, organization_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")
        return brand

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[Brand], dict]:
        """List brands with pagination and optional search.

        Args:
            organization_id: Organization UUID for tenant isolation.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            search: Optional search term for name or short_code.

        Returns:
            Tuple of (list of brands, pagination metadata dict).
        """
        page_size = min(page_size, 100)

        brands, total_count = self.repo.list(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            search=search,
        )

        total_pages = (total_count + page_size - 1) // page_size if total_count > 0 else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return brands, pagination

    def update(
        self,
        brand_id: UUID,
        data: BrandUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Brand:
        """Update a brand's metadata (name, short_code only).

        Rejects any attempt to modify public_key or private_key_encrypted.

        Args:
            brand_id: Brand UUID.
            data: Brand update payload.
            organization_id: Organization UUID for tenant isolation.
            user_id: UUID of the user performing the update.

        Returns:
            Updated Brand object.

        Raises:
            HTTPException: 422 if payload contains key fields.
            HTTPException: 404 if brand not found.
        """
        raw = data.model_dump(exclude_unset=True)

        if "public_key" in raw or "private_key_encrypted" in raw:
            raise HTTPException(
                status_code=422,
                detail="Cannot modify public_key or private_key_encrypted",
            )

        brand = self.repo.get_by_id(brand_id, organization_id)
        if not brand:
            raise HTTPException(status_code=404, detail="Brand not found")

        raw["updated_by"] = user_id
        return self.repo.update(brand, raw)
