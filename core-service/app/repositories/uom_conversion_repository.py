"""UOM Conversion repository for database operations"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.uom_conversion import UOMConversion


class UOMConversionRepository:
    """Repository for UOM Conversion database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, conversion_data: dict) -> UOMConversion:
        """
        Create a new UOM Conversion record.

        Args:
            conversion_data: Dictionary containing UOM Conversion data

        Returns:
            Created UOMConversion object
        """
        conversion = UOMConversion(**conversion_data)
        self.db.add(conversion)
        self.db.commit()
        self.db.refresh(conversion)
        return conversion

    def get_by_id(
        self, conversion_id: UUID, organization_id: UUID
    ) -> UOMConversion | None:
        """
        Get UOM Conversion by ID within an organization, excluding soft-deleted.

        Args:
            conversion_id: UOMConversion UUID
            organization_id: Organization UUID

        Returns:
            UOMConversion object or None if not found
        """
        return (
            self.db.query(UOMConversion)
            .filter(
                UOMConversion.id == conversion_id,
                UOMConversion.organization_id == organization_id,
                UOMConversion.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_item_and_pair(
        self,
        item_id: UUID,
        from_uom: str,
        to_uom: str,
        organization_id: UUID,
    ) -> UOMConversion | None:
        """
        Get UOM Conversion by item and UOM pair for uniqueness checks and convert_quantity lookups.

        Args:
            item_id: Item UUID
            from_uom: Source UOM name
            to_uom: Target UOM name
            organization_id: Organization UUID

        Returns:
            UOMConversion object or None if not found
        """
        return (
            self.db.query(UOMConversion)
            .filter(
                UOMConversion.item_id == item_id,
                UOMConversion.from_uom == from_uom,
                UOMConversion.to_uom == to_uom,
                UOMConversion.organization_id == organization_id,
                UOMConversion.deleted_at.is_(None),
            )
            .first()
        )

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        item_id: UUID | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[UOMConversion], int]:
        """
        List UOM Conversions with pagination, org-scoped, excluding soft-deleted.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            item_id: Optional filter by item ID
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of UOMConversions, total count)
        """
        query = self.db.query(UOMConversion).filter(
            UOMConversion.organization_id == organization_id,
            UOMConversion.deleted_at.is_(None),
        )

        if item_id is not None:
            query = query.filter(UOMConversion.item_id == item_id)

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(UOMConversion, sort_by, UOMConversion.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        conversions = query.offset(offset).limit(page_size).all()

        return conversions, total_count

    def update(self, conversion: UOMConversion, update_data: dict) -> UOMConversion:
        """
        Update UOM Conversion fields.

        Args:
            conversion: UOMConversion object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated UOMConversion object
        """
        for key, value in update_data.items():
            if hasattr(conversion, key) and value is not None:
                setattr(conversion, key, value)

        self.db.commit()
        self.db.refresh(conversion)
        return conversion

    def soft_delete(self, conversion: UOMConversion) -> UOMConversion:
        """
        Soft delete a UOM Conversion by setting deleted_at.

        Args:
            conversion: UOMConversion object to delete

        Returns:
            Soft-deleted UOMConversion object
        """
        from datetime import UTC, datetime

        conversion.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(conversion)
        return conversion
