"""Item repository for database operations"""

from uuid import UUID

from sqlalchemy import inspect, or_
from sqlalchemy.orm import Session, joinedload

from app.models.base import ItemStatus, ItemType
from app.models.item import Item


class ItemRepository:
    """Repository for item database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_item(self, item_data: dict) -> Item:
        """
        Create a new item.

        Args:
            item_data: Dictionary containing item data

        Returns:
            Created Item object
        """
        item = Item(**item_data)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get_item_by_id(
        self, item_id: UUID, organization_id: UUID, include_group: bool = False
    ) -> Item | None:
        """
        Get item by ID within an organization.

        Args:
            item_id: Item UUID
            organization_id: Organization UUID
            include_group: Whether to include item_group relationship

        Returns:
            Item object or None if not found
        """
        query = self.db.query(Item).filter(
            Item.id == item_id,
            Item.organization_id == organization_id,
            Item.deleted_at.is_(None),
        )

        if include_group:
            query = query.options(joinedload(Item.item_group))

        return query.first()

    def get_item_by_code(self, item_code: str, organization_id: UUID) -> Item | None:
        """
        Get item by code within an organization.

        Args:
            item_code: Item code
            organization_id: Organization UUID

        Returns:
            Item object or None if not found
        """
        return (
            self.db.query(Item)
            .filter(
                Item.item_code == item_code,
                Item.organization_id == organization_id,
                Item.deleted_at.is_(None),
            )
            .first()
        )

    def update_item(self, item: Item, update_data: dict) -> Item:
        """
        Update item fields.

        Args:
            item: Item object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated Item object
        """
        for key, value in update_data.items():
            if hasattr(item, key) and value is not None:
                setattr(item, key, value)

        self.db.commit()
        self.db.refresh(item)
        return item

    def soft_delete_item(self, item: Item) -> Item:
        """
        Soft delete an item.

        Args:
            item: Item object to delete

        Returns:
            Deleted Item object
        """
        from datetime import UTC, datetime

        item.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(item)
        return item

    def list_items(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: ItemStatus | None = None,
        item_type: ItemType | None = None,
        item_group_id: UUID | None = None,
        maintain_stock: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[Item], int]:
        """
        List items with pagination and filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by item status
            item_type: Filter by item type
            item_group_id: Filter by item group
            maintain_stock: Filter by maintain_stock flag
            search: Search term for item_code, item_name, barcode
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of items, total count)
        """
        query = (
            self.db.query(Item)
            .filter(
                Item.organization_id == organization_id,
                Item.deleted_at.is_(None),
            )
            .options(joinedload(Item.item_group))
        )

        # Apply filters
        if status:
            query = query.filter(Item.status == status)

        if item_type:
            query = query.filter(Item.item_type == item_type)

        if item_group_id:
            query = query.filter(Item.item_group_id == item_group_id)

        if maintain_stock is not None:
            query = query.filter(Item.maintain_stock == maintain_stock)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Item.item_code.ilike(search_term),
                    Item.item_name.ilike(search_term),
                    Item.barcode.ilike(search_term),
                )
            )

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting (schema-aware fallback to prevent runtime DB mismatches)
        allowed_sort_fields = {
            "id",
            "item_code",
            "item_name",
            "status",
            "created_at",
            "updated_at",
        }
        requested_sort_field = sort_by if sort_by in allowed_sort_fields else "created_at"

        existing_columns: set[str] = set()
        try:
            table_columns = inspect(self.db.get_bind()).get_columns("items")
            existing_columns = {column["name"] for column in table_columns}
        except Exception:
            existing_columns = set()

        if existing_columns and requested_sort_field not in existing_columns:
            requested_sort_field = "created_at" if "created_at" in existing_columns else "id"

        sort_column = getattr(Item, requested_sort_field, Item.id)
        normalized_order = "desc" if str(sort_order).lower() == "desc" else "asc"
        if normalized_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()

        return items, total_count

    def item_code_exists(self, item_code: str, organization_id: UUID) -> bool:
        """
        Check if item code already exists in the organization.

        Args:
            item_code: Item code to check
            organization_id: Organization UUID

        Returns:
            True if item code exists, False otherwise
        """
        return (
            self.db.query(Item)
            .filter(
                Item.item_code == item_code,
                Item.organization_id == organization_id,
                Item.deleted_at.is_(None),
            )
            .count()
            > 0
        )
