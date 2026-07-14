"""UOM service with business logic"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateUOMAbbreviationException,
    DuplicateUOMNameException,
    UOMNotFoundException,
)
from app.models.uom import UOM
from app.repositories.uom_repository import UOMRepository
from app.schemas.uom import UOMCreate, UOMUpdate

logger = logging.getLogger(__name__)


class UOMService:
    """Service for UOM operations"""

    def __init__(self, db: Session):
        self.db = db
        self.uom_repo = UOMRepository(db)

    def create_uom(
        self,
        uom_data: UOMCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> UOM:
        """
        Create a new UOM.

        Args:
            uom_data: UOM creation data
            organization_id: Organization UUID
            user_id: User UUID creating the UOM

        Returns:
            Created UOM object

        Raises:
            DuplicateUOMNameException: If UOM name already exists in org
            DuplicateUOMAbbreviationException: If UOM abbreviation already exists in org
        """
        # Check duplicate name within org
        existing_by_name = self.uom_repo.get_by_name(uom_data.name, organization_id)
        if existing_by_name:
            raise DuplicateUOMNameException(
                f"UOM with name '{uom_data.name}' already exists in this organization"
            )

        # Check duplicate abbreviation within org
        existing_by_abbr = self.uom_repo.get_by_abbreviation(
            uom_data.abbreviation, organization_id
        )
        if existing_by_abbr:
            raise DuplicateUOMAbbreviationException(
                f"UOM with abbreviation '{uom_data.abbreviation}' already exists in this organization"
            )

        # Prepare data and delegate to repository
        uom_dict = uom_data.model_dump()
        uom_dict["organization_id"] = organization_id
        uom_dict["created_by"] = user_id
        uom_dict["updated_by"] = user_id

        return self.uom_repo.create(uom_dict)

    def get_uom(
        self,
        uom_id: UUID,
        organization_id: UUID,
    ) -> UOM:
        """
        Get UOM by ID.

        Args:
            uom_id: UOM UUID
            organization_id: Organization UUID

        Returns:
            UOM object

        Raises:
            UOMNotFoundException: If UOM not found or belongs to different org
        """
        uom = self.uom_repo.get_by_id(uom_id, organization_id)
        if not uom:
            raise UOMNotFoundException(f"UOM with ID {uom_id} not found")
        return uom

    def list_uoms(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[UOM], dict]:
        """
        Get paginated list of UOMs.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            search: Optional search term for name or abbreviation
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of UOMs, pagination metadata dict)
        """
        page_size = min(page_size, 100)

        uoms, total_count = self.uom_repo.list(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        total_pages = (total_count + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return uoms, pagination

    def update_uom(
        self,
        uom_id: UUID,
        uom_data: UOMUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> UOM:
        """
        Update a UOM.

        Args:
            uom_id: UOM UUID
            uom_data: UOM update data
            organization_id: Organization UUID
            user_id: User UUID updating the UOM

        Returns:
            Updated UOM object

        Raises:
            UOMNotFoundException: If UOM not found
            DuplicateUOMNameException: If new name already exists in org
            DuplicateUOMAbbreviationException: If new abbreviation already exists in org
        """
        uom = self.uom_repo.get_by_id(uom_id, organization_id)
        if not uom:
            raise UOMNotFoundException(f"UOM with ID {uom_id} not found")

        update_dict = uom_data.model_dump(exclude_unset=True)

        # Check duplicate name only if name is changing
        if "name" in update_dict and update_dict["name"] != uom.name:
            existing_by_name = self.uom_repo.get_by_name(
                update_dict["name"], organization_id
            )
            if existing_by_name:
                raise DuplicateUOMNameException(
                    f"UOM with name '{update_dict['name']}' already exists in this organization"
                )

        # Check duplicate abbreviation only if abbreviation is changing
        if (
            "abbreviation" in update_dict
            and update_dict["abbreviation"] != uom.abbreviation
        ):
            existing_by_abbr = self.uom_repo.get_by_abbreviation(
                update_dict["abbreviation"], organization_id
            )
            if existing_by_abbr:
                raise DuplicateUOMAbbreviationException(
                    f"UOM with abbreviation '{update_dict['abbreviation']}' already exists in this organization"
                )

        update_dict["updated_by"] = user_id

        return self.uom_repo.update(uom, update_dict)

    def delete_uom(
        self,
        uom_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> UOM:
        """
        Soft delete a UOM.

        Args:
            uom_id: UOM UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the UOM

        Returns:
            Soft-deleted UOM object

        Raises:
            UOMNotFoundException: If UOM not found
        """
        uom = self.uom_repo.get_by_id(uom_id, organization_id)
        if not uom:
            raise UOMNotFoundException(f"UOM with ID {uom_id} not found")

        uom.updated_by = user_id
        return self.uom_repo.soft_delete(uom)
