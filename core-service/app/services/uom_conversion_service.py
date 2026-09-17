"""UOM Conversion service with business logic"""

import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateUOMConversionException,
    ItemNotFoundException,
    UOMConversionNotFoundException,
    ValidationError,
)
from app.models.item import Item
from app.models.uom_conversion import UOMConversion
from app.repositories.uom_conversion_repository import UOMConversionRepository
from app.schemas.uom_conversion import (
    UOMConversionBulkItem,
    UOMConversionCreate,
    UOMConversionUpdate,
)

logger = logging.getLogger(__name__)


class UOMConversionService:
    """Service for UOM Conversion operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = UOMConversionRepository(db)

    def _validate_item_exists(self, item_id: UUID, organization_id: UUID) -> None:
        """Validate that the referenced item exists in the organization."""
        item = (
            self.db.query(Item)
            .filter(
                Item.id == item_id,
                Item.organization_id == organization_id,
            )
            .first()
        )
        if not item:
            raise ItemNotFoundException(
                f"Item '{item_id}' not found in this organization"
            )

    def _find_existing_conversion(
        self,
        item_id: UUID | None,
        from_uom: str,
        to_uom: str,
        from_uom_id: UUID | None,
        to_uom_id: UUID | None,
        organization_id: UUID,
    ) -> UOMConversion | None:
        """Find an existing conversion, preferring FK ids, then name caches."""
        if from_uom_id and to_uom_id:
            found = self.repo.get_by_item_and_ids(
                item_id, from_uom_id, to_uom_id, organization_id
            )
            if found is not None:
                return found
        return self.repo.get_by_item_and_pair(
            item_id, from_uom, to_uom, organization_id
        )

    def create_conversion(
        self,
        conversion_data: UOMConversionCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> UOMConversion:
        """
        Create a new UOM Conversion.

        Args:
            conversion_data: UOM Conversion creation data
            organization_id: Organization UUID
            user_id: User UUID creating the conversion

        Returns:
            Created UOMConversion object

        Raises:
            ItemNotFoundException: If item does not exist in org
            DuplicateUOMConversionException: If (item_id, from_uom, to_uom) already exists
        """
        # Validate item exists in org
        self._validate_item_exists(conversion_data.item_id, organization_id)

        # Check duplicate (item_id, from_uom, to_uom) within org
        existing = self._find_existing_conversion(
            conversion_data.item_id,
            conversion_data.from_uom,
            conversion_data.to_uom,
            conversion_data.from_uom_id,
            conversion_data.to_uom_id,
            organization_id,
        )
        if existing:
            raise DuplicateUOMConversionException(
                f"UOM conversion for item '{conversion_data.item_id}' "
                f"from '{conversion_data.from_uom}' to '{conversion_data.to_uom}' already exists"
            )

        # Prepare data and delegate to repository
        conversion_dict = conversion_data.model_dump()
        conversion_dict["organization_id"] = organization_id
        conversion_dict["created_by"] = user_id
        conversion_dict["updated_by"] = user_id

        return self.repo.create(conversion_dict)

    def bulk_upsert_conversions(
        self,
        organization_id: UUID,
        user_id: UUID,
        conversions: list[UOMConversionBulkItem],
    ) -> tuple[int, int, int, list[dict]]:
        """
        Bulk process UOM conversions (create by default; supports create /
        modify / delete actions). Each row is committed independently so
        partial success is reported via the returned error list.

        Returns:
            Tuple of (created, updated, deleted, errors).
        """
        created = 0
        updated = 0
        deleted = 0
        errors: list[dict] = []

        for index, conv in enumerate(conversions):
            try:
                action = (conv.action or "").strip().lower() or "create"
                if conv.item_id is not None:
                    self._validate_item_exists(conv.item_id, organization_id)

                existing = self._find_existing_conversion(
                    conv.item_id,
                    conv.from_uom,
                    conv.to_uom,
                    conv.from_uom_id,
                    conv.to_uom_id,
                    organization_id,
                )

                if action == "delete":
                    if existing is not None:
                        existing.updated_by = user_id
                        self.repo.soft_delete(existing)
                        deleted += 1
                    continue  # missing → silently ignored

                if action == "create" and existing is not None:
                    continue  # already exists → nothing happens

                if action == "modify" and existing is None:
                    continue  # nothing to modify → silently ignored

                if conv.conversion_factor is None:
                    errors.append(
                        {"row": index, "error": "conversion_factor is required"}
                    )
                    continue

                if existing is not None:
                    self.repo.update(
                        existing,
                        {
                            "conversion_factor": conv.conversion_factor,
                            "from_uom_id": conv.from_uom_id,
                            "to_uom_id": conv.to_uom_id,
                            "updated_by": user_id,
                        },
                    )
                    updated += 1
                else:
                    data = conv.model_dump(exclude={"action"})
                    data["organization_id"] = organization_id
                    data["created_by"] = user_id
                    data["updated_by"] = user_id
                    self.repo.create(data)
                    created += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning(
                    "Bulk UOM conversion row %d failed: %s", index, exc
                )
                errors.append({"row": index, "error": str(exc)})

        return created, updated, deleted, errors

    def get_conversion(
        self,
        conversion_id: UUID,
        organization_id: UUID,
    ) -> UOMConversion:
        """
        Get UOM Conversion by ID.

        Args:
            conversion_id: UOMConversion UUID
            organization_id: Organization UUID

        Returns:
            UOMConversion object

        Raises:
            UOMConversionNotFoundException: If conversion not found or belongs to different org
        """
        conversion = self.repo.get_by_id(conversion_id, organization_id)
        if not conversion:
            raise UOMConversionNotFoundException(
                f"UOM Conversion with ID {conversion_id} not found"
            )
        return conversion

    def list_conversions(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        item_id: UUID | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[UOMConversion], dict]:
        """
        Get paginated list of UOM Conversions.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            item_id: Optional filter by item ID
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of UOMConversions, pagination metadata dict)
        """
        page_size = min(page_size, 100)

        conversions, total_count = self.repo.list(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            item_id=item_id,
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

        return conversions, pagination

    def update_conversion(
        self,
        conversion_id: UUID,
        conversion_data: UOMConversionUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> UOMConversion:
        """
        Update a UOM Conversion.

        Args:
            conversion_id: UOMConversion UUID
            conversion_data: UOM Conversion update data
            organization_id: Organization UUID
            user_id: User UUID updating the conversion

        Returns:
            Updated UOMConversion object

        Raises:
            UOMConversionNotFoundException: If conversion not found
            DuplicateUOMConversionException: If updated triple already exists
        """
        conversion = self.repo.get_by_id(conversion_id, organization_id)
        if not conversion:
            raise UOMConversionNotFoundException(
                f"UOM Conversion with ID {conversion_id} not found"
            )

        update_dict = conversion_data.model_dump(exclude_unset=True)

        # Check for duplicate if from_uom or to_uom is changing
        new_from_uom = update_dict.get("from_uom", conversion.from_uom)
        new_to_uom = update_dict.get("to_uom", conversion.to_uom)

        if new_from_uom != conversion.from_uom or new_to_uom != conversion.to_uom:
            existing = self.repo.get_by_item_and_pair(
                conversion.item_id,
                new_from_uom,
                new_to_uom,
                organization_id,
            )
            if existing and existing.id != conversion.id:
                raise DuplicateUOMConversionException(
                    f"UOM conversion for item '{conversion.item_id}' "
                    f"from '{new_from_uom}' to '{new_to_uom}' already exists"
                )

        update_dict["updated_by"] = user_id

        return self.repo.update(conversion, update_dict)

    def delete_conversion(
        self,
        conversion_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> UOMConversion:
        """
        Soft delete a UOM Conversion.

        Args:
            conversion_id: UOMConversion UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the conversion

        Returns:
            Soft-deleted UOMConversion object

        Raises:
            UOMConversionNotFoundException: If conversion not found
        """
        conversion = self.repo.get_by_id(conversion_id, organization_id)
        if not conversion:
            raise UOMConversionNotFoundException(
                f"UOM Conversion with ID {conversion_id} not found"
            )

        conversion.updated_by = user_id
        return self.repo.soft_delete(conversion)

    def convert_quantity(
        self,
        item_id: UUID,
        from_uom: str,
        to_uom: str,
        quantity: Decimal,
        organization_id: UUID,
    ) -> Decimal:
        """
        Convert quantity from one UOM to another for a given item.

        1. If from_uom == to_uom, return quantity as-is (no DB lookup).
        2. Forward lookup: get_by_item_and_pair(item_id, from_uom, to_uom) → result = quantity × factor.
        3. Reverse lookup: get_by_item_and_pair(item_id, to_uom, from_uom) → result = quantity / factor.
        4. If neither found, raise ValidationError.

        Args:
            item_id: Item UUID
            from_uom: Source UOM name
            to_uom: Target UOM name
            quantity: Quantity to convert
            organization_id: Organization UUID

        Returns:
            Converted quantity as Decimal

        Raises:
            ValidationError: If no conversion found (neither forward nor reverse)
        """
        # Identity check — no DB lookup needed
        if from_uom == to_uom:
            return quantity

        # Forward lookup
        forward = self.repo.get_by_item_and_pair(
            item_id, from_uom, to_uom, organization_id
        )
        if forward:
            return quantity * forward.conversion_factor

        # Reverse lookup (item-specific)
        reverse = self.repo.get_by_item_and_pair(
            item_id, to_uom, from_uom, organization_id
        )
        if reverse:
            return quantity / reverse.conversion_factor

        # Global fallback (item_id IS NULL) — org-wide standard conversions
        global_forward = self.repo.get_by_item_and_pair(
            None, from_uom, to_uom, organization_id
        )
        if global_forward:
            return quantity * global_forward.conversion_factor

        global_reverse = self.repo.get_by_item_and_pair(
            None, to_uom, from_uom, organization_id
        )
        if global_reverse:
            return quantity / global_reverse.conversion_factor

        raise ValidationError(
            f"No UOM conversion found for item {item_id} from '{from_uom}' to '{to_uom}'"
        )
