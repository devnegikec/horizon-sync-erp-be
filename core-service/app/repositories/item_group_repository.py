"""Item Group repository for database operations"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.models.item_group import ItemGroup


class ItemGroupRepository:
    """Repository for item group database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_item_group(self, item_group_data: dict) -> ItemGroup:
        """
        Create a new item group.

        Args:
            item_group_data: Dictionary containing item group data

        Returns:
            Created ItemGroup object
        """
        item_group = ItemGroup(**item_group_data)
        self.db.add(item_group)
        self.db.commit()
        self.db.refresh(item_group)
        return item_group

    def get_item_group_by_id(
        self, item_group_id: UUID, organization_id: UUID, include_parent: bool = False
    ) -> ItemGroup | None:
        """
        Get item group by ID within an organization.

        Args:
            item_group_id: Item Group UUID
            organization_id: Organization UUID
            include_parent: Whether to include parent relationship

        Returns:
            ItemGroup object or None if not found
        """
        query = self.db.query(ItemGroup).filter(
            ItemGroup.id == item_group_id,
            ItemGroup.organization_id == organization_id,
            ItemGroup.deleted_at.is_(None),
        )

        if include_parent:
            query = query.options(joinedload(ItemGroup.parent))

        return query.first()

    def get_item_group_by_code(
        self, code: str, organization_id: UUID
    ) -> ItemGroup | None:
        """
        Get item group by code within an organization.

        Args:
            code: Item group code
            organization_id: Organization UUID

        Returns:
            ItemGroup object or None if not found
        """
        return (
            self.db.query(ItemGroup)
            .filter(
                ItemGroup.code == code,
                ItemGroup.organization_id == organization_id,
                ItemGroup.deleted_at.is_(None),
            )
            .first()
        )

    def update_item_group(self, item_group: ItemGroup, update_data: dict) -> ItemGroup:
        """
        Update item group fields.

        Args:
            item_group: ItemGroup object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated ItemGroup object
        """
        for key, value in update_data.items():
            if hasattr(item_group, key) and value is not None:
                setattr(item_group, key, value)

        self.db.commit()
        self.db.refresh(item_group)
        return item_group

    def soft_delete_item_group(self, item_group: ItemGroup) -> ItemGroup:
        """
        Soft delete an item group.

        Args:
            item_group: ItemGroup object to delete

        Returns:
            Deleted ItemGroup object
        """
        from datetime import UTC, datetime

        item_group.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(item_group)
        return item_group

    def list_item_groups(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        parent_id: UUID | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ItemGroup], int]:
        """
        List item groups with pagination and filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            is_active: Filter by active status
            parent_id: Filter by parent group
            search: Search term for name, code
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of item groups, total count)
        """
        from app.models.tax_template import TaxTemplate

        query = self.db.query(ItemGroup).filter(
            ItemGroup.organization_id == organization_id,
            ItemGroup.deleted_at.is_(None),
        )

        # Apply filters
        if is_active is not None:
            query = query.filter(ItemGroup.is_active == is_active)

        if parent_id:
            query = query.filter(ItemGroup.parent_id == parent_id)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    ItemGroup.name.ilike(search_term),
                    ItemGroup.code.ilike(search_term),
                )
            )

        # Get total count before pagination
        total_count = query.count()

        # Eager-load parent and tax templates with their rules
        query = query.options(
            joinedload(ItemGroup.parent),
            joinedload(ItemGroup.sales_tax_template).joinedload(TaxTemplate.tax_rules),
            joinedload(ItemGroup.purchase_tax_template).joinedload(
                TaxTemplate.tax_rules
            ),
        )

        # Apply sorting
        sort_column = getattr(ItemGroup, sort_by, ItemGroup.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        item_groups = query.offset(offset).limit(page_size).all()

        return item_groups, total_count

    def item_group_code_exists(self, code: str, organization_id: UUID) -> bool:
        """
        Check if item group code already exists in the organization.

        Args:
            code: Item group code to check
            organization_id: Organization UUID

        Returns:
            True if code exists, False otherwise
        """
        return (
            self.db.query(ItemGroup)
            .filter(
                ItemGroup.code == code,
                ItemGroup.organization_id == organization_id,
                ItemGroup.deleted_at.is_(None),
            )
            .count()
            > 0
        )

    def get_all_item_groups(self, organization_id: UUID) -> list[ItemGroup]:
        """
        Get all item groups for an organization (for tree building).

        Args:
            organization_id: Organization UUID

        Returns:
            List of all item groups
        """
        return (
            self.db.query(ItemGroup)
            .filter(
                ItemGroup.organization_id == organization_id,
                ItemGroup.deleted_at.is_(None),
            )
            .order_by(ItemGroup.name)
            .all()
        )

    def get_active_item_groups(self, organization_id: UUID) -> list[ItemGroup]:
        """
        Get all active item groups for an organization.

        Args:
            organization_id: Organization UUID

        Returns:
            List of active item groups
        """
        return (
            self.db.query(ItemGroup)
            .filter(
                ItemGroup.organization_id == organization_id,
                ItemGroup.is_active.is_(True),
                ItemGroup.deleted_at.is_(None),
            )
            .order_by(ItemGroup.name)
            .all()
        )

    def has_children(self, item_group_id: UUID, organization_id: UUID) -> bool:
        """
        Check if item group has child groups.

        Args:
            item_group_id: Item Group UUID
            organization_id: Organization UUID

        Returns:
            True if has children, False otherwise
        """
        return (
            self.db.query(ItemGroup)
            .filter(
                ItemGroup.parent_id == item_group_id,
                ItemGroup.organization_id == organization_id,
                ItemGroup.deleted_at.is_(None),
            )
            .count()
            > 0
        )

    def has_items(self, item_group_id: UUID, organization_id: UUID) -> bool:
        """
        Check if item group has items associated.

        Args:
            item_group_id: Item Group UUID
            organization_id: Organization UUID

        Returns:
            True if has items, False otherwise
        """
        from app.models.item import Item

        return (
            self.db.query(Item)
            .filter(
                Item.item_group_id == item_group_id,
                Item.organization_id == organization_id,
                Item.deleted_at.is_(None),
            )
            .count()
            > 0
        )

    def get_root_groups(self, organization_id: UUID) -> list[ItemGroup]:
        """
        Get all root-level item groups (no parent).

        Args:
            organization_id: Organization UUID

        Returns:
            List of root item groups
        """
        return (
            self.db.query(ItemGroup)
            .filter(
                ItemGroup.organization_id == organization_id,
                ItemGroup.parent_id.is_(None),
                ItemGroup.deleted_at.is_(None),
            )
            .order_by(ItemGroup.name)
            .all()
        )
