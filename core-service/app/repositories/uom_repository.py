"""UOM repository for database operations"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.uom import UOM


class UOMRepository:
    """Repository for UOM database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, uom_data: dict) -> UOM:
        """
        Create a new UOM record.

        Args:
            uom_data: Dictionary containing UOM data

        Returns:
            Created UOM object
        """
        uom = UOM(**uom_data)
        self.db.add(uom)
        self.db.commit()
        self.db.refresh(uom)
        return uom

    def get_by_id(self, uom_id: UUID, organization_id: UUID) -> UOM | None:
        """
        Get UOM by ID within an organization, excluding soft-deleted.

        Args:
            uom_id: UOM UUID
            organization_id: Organization UUID

        Returns:
            UOM object or None if not found
        """
        return (
            self.db.query(UOM)
            .filter(
                UOM.id == uom_id,
                UOM.organization_id == organization_id,
                UOM.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_name(self, name: str, organization_id: UUID) -> UOM | None:
        """
        Get UOM by name within an organization for uniqueness checks.

        Args:
            name: UOM name
            organization_id: Organization UUID

        Returns:
            UOM object or None if not found
        """
        return (
            self.db.query(UOM)
            .filter(
                UOM.name == name,
                UOM.organization_id == organization_id,
                UOM.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_abbreviation(
        self, abbreviation: str, organization_id: UUID
    ) -> UOM | None:
        """
        Get UOM by abbreviation within an organization for uniqueness checks.

        Args:
            abbreviation: UOM abbreviation
            organization_id: Organization UUID

        Returns:
            UOM object or None if not found
        """
        return (
            self.db.query(UOM)
            .filter(
                UOM.abbreviation == abbreviation,
                UOM.organization_id == organization_id,
                UOM.deleted_at.is_(None),
            )
            .first()
        )

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[UOM], int]:
        """
        List UOMs with pagination, org-scoped, excluding soft-deleted.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            search: Optional search term for name or abbreviation
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of UOMs, total count)
        """
        query = self.db.query(UOM).filter(
            UOM.organization_id == organization_id,
            UOM.deleted_at.is_(None),
        )

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    UOM.name.ilike(search_term),
                    UOM.abbreviation.ilike(search_term),
                )
            )

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(UOM, sort_by, UOM.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        uoms = query.offset(offset).limit(page_size).all()

        return uoms, total_count

    def update(self, uom: UOM, update_data: dict) -> UOM:
        """
        Update UOM fields.

        Args:
            uom: UOM object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated UOM object
        """
        for key, value in update_data.items():
            if hasattr(uom, key) and value is not None:
                setattr(uom, key, value)

        self.db.commit()
        self.db.refresh(uom)
        return uom

    def soft_delete(self, uom: UOM) -> UOM:
        """
        Soft delete a UOM by setting deleted_at.

        Args:
            uom: UOM object to delete

        Returns:
            Soft-deleted UOM object
        """
        from datetime import UTC, datetime

        uom.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(uom)
        return uom
