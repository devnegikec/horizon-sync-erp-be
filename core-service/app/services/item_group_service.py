"""Item Group service with business logic"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    CannotDeleteException,
    CircularReferenceException,
    DuplicateItemGroupCodeException,
    ItemGroupNotFoundException,
)
from app.models.base import ValuationMethod
from app.models.item_group import ItemGroup
from app.repositories.item_group_repository import ItemGroupRepository
from app.schemas.item_group import (
    ItemGroupCreate,
    ItemGroupTreeNode,
    ItemGroupUpdate,
)


class ItemGroupService:
    """Service for item group operations"""

    def __init__(self, db: Session):
        self.db = db
        self.item_group_repo = ItemGroupRepository(db)

    def create_item_group(
        self,
        item_group_data: ItemGroupCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> ItemGroup:
        """
        Create a new item group.

        Args:
            item_group_data: Item group creation data
            organization_id: Organization UUID
            user_id: User UUID creating the item group

        Returns:
            Created ItemGroup object

        Raises:
            DuplicateItemGroupCodeException: If item group code already exists
            ItemGroupNotFoundException: If parent item group not found
        """
        # Check if item group code already exists
        if self.item_group_repo.item_group_code_exists(
            item_group_data.code, organization_id
        ):
            raise DuplicateItemGroupCodeException(
                f"Item group with code '{item_group_data.code}' already exists"
            )

        # Validate parent item group if provided
        if item_group_data.parent_id:
            parent = self.item_group_repo.get_item_group_by_id(
                item_group_data.parent_id, organization_id
            )
            if not parent:
                raise ItemGroupNotFoundException(
                    f"Parent item group with ID {item_group_data.parent_id} not found"
                )

        # Convert to dict and add organization/user info
        item_group_dict = item_group_data.model_dump()
        item_group_dict["organization_id"] = organization_id
        item_group_dict["created_by"] = user_id
        item_group_dict["updated_by"] = user_id

        # Convert valuation_method string to enum
        if item_group_dict.get("default_valuation_method"):
            try:
                vm_str = str(item_group_dict["default_valuation_method"]).lower()
                item_group_dict["default_valuation_method"] = ValuationMethod(vm_str)
            except (ValueError, KeyError):
                item_group_dict["default_valuation_method"] = None

        return self.item_group_repo.create_item_group(item_group_dict)

    def get_item_group_by_id(
        self,
        item_group_id: UUID,
        organization_id: UUID,
        include_parent: bool = True,
    ) -> ItemGroup:
        """
        Get item group by ID.

        Args:
            item_group_id: Item Group UUID
            organization_id: Organization UUID
            include_parent: Whether to include parent relationship

        Returns:
            ItemGroup object

        Raises:
            ItemGroupNotFoundException: If item group not found
        """
        item_group = self.item_group_repo.get_item_group_by_id(
            item_group_id, organization_id, include_parent=include_parent
        )
        if not item_group:
            raise ItemGroupNotFoundException(
                f"Item group with ID {item_group_id} not found"
            )
        return item_group

    def update_item_group(
        self,
        item_group_id: UUID,
        item_group_data: ItemGroupUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> ItemGroup:
        """
        Update an item group.

        Args:
            item_group_id: Item Group UUID
            item_group_data: Item group update data
            organization_id: Organization UUID
            user_id: User UUID updating the item group

        Returns:
            Updated ItemGroup object

        Raises:
            ItemGroupNotFoundException: If item group not found
            CircularReferenceException: If parent would create circular reference
        """
        item_group = self.item_group_repo.get_item_group_by_id(
            item_group_id, organization_id
        )
        if not item_group:
            raise ItemGroupNotFoundException(
                f"Item group with ID {item_group_id} not found"
            )

        # Validate parent item group if being changed
        update_dict = item_group_data.model_dump(exclude_unset=True)

        if "parent_id" in update_dict and update_dict["parent_id"]:
            parent_id = update_dict["parent_id"]

            # Cannot be its own parent
            if parent_id == item_group_id:
                raise CircularReferenceException("Item group cannot be its own parent")

            # Check parent exists
            parent = self.item_group_repo.get_item_group_by_id(
                parent_id, organization_id
            )
            if not parent:
                raise ItemGroupNotFoundException(
                    f"Parent item group with ID {parent_id} not found"
                )

            # Check for circular reference
            if self._would_create_circular_reference(
                item_group_id, parent_id, organization_id
            ):
                raise CircularReferenceException(
                    "This parent assignment would create a circular reference"
                )

        update_dict["updated_by"] = user_id

        # Convert valuation_method string to enum
        if "default_valuation_method" in update_dict:
            if update_dict["default_valuation_method"]:
                try:
                    vm_str = str(update_dict["default_valuation_method"]).lower()
                    update_dict["default_valuation_method"] = ValuationMethod(vm_str)
                except (ValueError, KeyError):
                    del update_dict["default_valuation_method"]

        return self.item_group_repo.update_item_group(item_group, update_dict)

    def delete_item_group(
        self,
        item_group_id: UUID,
        organization_id: UUID,
        user_id: UUID,
        force: bool = False,
    ) -> ItemGroup:
        """
        Soft delete an item group.

        Args:
            item_group_id: Item Group UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the item group
            force: If True, delete even if has children or items

        Returns:
            Deleted ItemGroup object

        Raises:
            ItemGroupNotFoundException: If item group not found
            CannotDeleteException: If has children or items and force=False
        """
        item_group = self.item_group_repo.get_item_group_by_id(
            item_group_id, organization_id
        )
        if not item_group:
            raise ItemGroupNotFoundException(
                f"Item group with ID {item_group_id} not found"
            )

        if not force:
            # Check for children
            if self.item_group_repo.has_children(item_group_id, organization_id):
                raise CannotDeleteException(
                    "Cannot delete item group with child groups. "
                    "Delete children first or use force=true."
                )

            # Check for items
            if self.item_group_repo.has_items(item_group_id, organization_id):
                raise CannotDeleteException(
                    "Cannot delete item group with associated items. "
                    "Remove items first or use force=true."
                )

        item_group.updated_by = user_id
        return self.item_group_repo.soft_delete_item_group(item_group)

    def get_item_groups(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        parent_id: UUID | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[ItemGroup], dict]:
        """
        Get paginated list of item groups with filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            is_active: Filter by active status
            parent_id: Filter by parent group
            search: Search term
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of item groups, pagination metadata)
        """
        # Ensure page_size doesn't exceed maximum
        page_size = min(page_size, 100)

        # Get item groups from repository
        item_groups, total_count = self.item_group_repo.list_item_groups(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            is_active=is_active,
            parent_id=parent_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        # Calculate pagination metadata
        total_pages = (total_count + page_size - 1) // page_size
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total_count,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

        return item_groups, pagination

    def get_item_group_tree(self, organization_id: UUID) -> list[ItemGroupTreeNode]:
        """
        Get item groups as a tree structure.

        Args:
            organization_id: Organization UUID

        Returns:
            List of root-level item group tree nodes
        """
        all_groups = self.item_group_repo.get_all_item_groups(organization_id)

        # Build lookup dict
        group_dict = {g.id: g for g in all_groups}

        # Build tree
        root_nodes = []
        children_map: dict[UUID, list] = {}

        for group in all_groups:
            if group.parent_id:
                if group.parent_id not in children_map:
                    children_map[group.parent_id] = []
                children_map[group.parent_id].append(group)
            else:
                root_nodes.append(group)

        def build_tree_node(group: ItemGroup) -> ItemGroupTreeNode:
            children = children_map.get(group.id, [])
            return ItemGroupTreeNode(
                id=group.id,
                name=group.name,
                code=group.code,
                default_valuation_method=str(group.default_valuation_method.value)
                if group.default_valuation_method
                else None,
                default_uom=group.default_uom,
                is_active=group.is_active,
                children=[build_tree_node(c) for c in children],
            )

        return [build_tree_node(g) for g in root_nodes]

    def _would_create_circular_reference(
        self, item_group_id: UUID, new_parent_id: UUID, organization_id: UUID
    ) -> bool:
        """
        Check if setting new_parent_id as parent would create circular reference.

        Args:
            item_group_id: Item group being updated
            new_parent_id: Proposed parent ID
            organization_id: Organization UUID

        Returns:
            True if circular reference would be created
        """
        current_id = new_parent_id
        visited = set()

        while current_id:
            if current_id in visited:
                return True
            if current_id == item_group_id:
                return True

            visited.add(current_id)

            parent = self.item_group_repo.get_item_group_by_id(
                current_id, organization_id
            )
            if not parent:
                break

            current_id = parent.parent_id

        return False
