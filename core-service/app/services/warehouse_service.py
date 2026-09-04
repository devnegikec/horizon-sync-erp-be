"""Warehouse service with business logic"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import (
    CircularReferenceException,
    DuplicateWarehouseCodeException,
    WarehouseNotFoundException,
)
from app.models.base import WarehouseType
from app.models.warehouse import Warehouse
from app.models.warehouse_location import LocationType, WarehouseLocation
from app.repositories.warehouse_repository import WarehouseRepository
from app.schemas.warehouse import WarehouseCreate, WarehouseTreeNode, WarehouseUpdate
from app.services.document_numbering_service import DocumentNumberingService


class WarehouseService:
    """Service for warehouse operations"""

    def __init__(self, db: Session):
        self.db = db
        self.warehouse_repo = WarehouseRepository(db)

    def create_warehouse(
        self,
        warehouse_data: WarehouseCreate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Warehouse:
        """
        Create a new warehouse.

        Args:
            warehouse_data: Warehouse creation data
            organization_id: Organization UUID
            user_id: User UUID creating the warehouse

        Returns:
            Created Warehouse object

        Raises:
            DuplicateWarehouseCodeException: If warehouse code already exists
            WarehouseNotFoundException: If parent warehouse not found
        """
        # Auto-generate code if not provided
        code = warehouse_data.code
        if not code:
            code = DocumentNumberingService(self.db).get_next_number(
                organization_id, "warehouse"
            )

        # Check if warehouse code already exists
        if self.warehouse_repo.warehouse_code_exists(code, organization_id):
            raise DuplicateWarehouseCodeException(
                f"Warehouse with code '{code}' already exists"
            )

        # Validate parent warehouse if provided
        if warehouse_data.parent_warehouse_id:
            parent = self.warehouse_repo.get_warehouse_by_id(
                warehouse_data.parent_warehouse_id, organization_id
            )
            if not parent:
                raise WarehouseNotFoundException(
                    f"Parent warehouse with ID {warehouse_data.parent_warehouse_id} not found"
                )

        # Convert to dict and add organization/user info
        warehouse_dict = warehouse_data.model_dump()
        warehouse_dict["code"] = code
        warehouse_dict["organization_id"] = organization_id
        warehouse_dict["created_by"] = user_id
        warehouse_dict["updated_by"] = user_id

        # Convert warehouse_type string to enum
        if warehouse_dict.get("warehouse_type"):
            try:
                wh_type_str = str(warehouse_dict["warehouse_type"]).lower()
                warehouse_dict["warehouse_type"] = WarehouseType(wh_type_str)
            except (ValueError, KeyError):
                warehouse_dict["warehouse_type"] = WarehouseType.WAREHOUSE

        warehouse = self.warehouse_repo.create_warehouse(warehouse_dict)

        # If this is set as default, update others
        if warehouse.is_default:
            self.warehouse_repo.set_default_warehouse(warehouse.id, organization_id)

        return warehouse

    def get_warehouse_by_id(
        self,
        warehouse_id: UUID,
        organization_id: UUID,
        include_parent: bool = True,
    ) -> Warehouse:
        """
        Get warehouse by ID.

        Args:
            warehouse_id: Warehouse UUID
            organization_id: Organization UUID
            include_parent: Whether to include parent relationship

        Returns:
            Warehouse object

        Raises:
            WarehouseNotFoundException: If warehouse not found
        """
        warehouse = self.warehouse_repo.get_warehouse_by_id(
            warehouse_id, organization_id, include_parent=include_parent
        )
        if not warehouse:
            raise WarehouseNotFoundException(
                f"Warehouse with ID {warehouse_id} not found"
            )
        self._apply_derived_capacity([warehouse])
        return warehouse

    def update_warehouse(
        self,
        warehouse_id: UUID,
        warehouse_data: WarehouseUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> Warehouse:
        """
        Update a warehouse.

        Args:
            warehouse_id: Warehouse UUID
            warehouse_data: Warehouse update data
            organization_id: Organization UUID
            user_id: User UUID updating the warehouse

        Returns:
            Updated Warehouse object

        Raises:
            WarehouseNotFoundException: If warehouse not found
            CircularReferenceException: If parent would create circular reference
        """
        warehouse = self.warehouse_repo.get_warehouse_by_id(
            warehouse_id, organization_id
        )
        if not warehouse:
            raise WarehouseNotFoundException(
                f"Warehouse with ID {warehouse_id} not found"
            )

        # Validate parent warehouse if being changed
        update_dict = warehouse_data.model_dump(exclude_unset=True)

        if "parent_warehouse_id" in update_dict and update_dict["parent_warehouse_id"]:
            parent_id = update_dict["parent_warehouse_id"]

            # Cannot be its own parent
            if parent_id == warehouse_id:
                raise CircularReferenceException("Warehouse cannot be its own parent")

            # Check parent exists
            parent = self.warehouse_repo.get_warehouse_by_id(parent_id, organization_id)
            if not parent:
                raise WarehouseNotFoundException(
                    f"Parent warehouse with ID {parent_id} not found"
                )

            # Check for circular reference
            if self._would_create_circular_reference(
                warehouse_id, parent_id, organization_id
            ):
                raise CircularReferenceException(
                    "This parent assignment would create a circular reference"
                )

        update_dict["updated_by"] = user_id

        # Convert warehouse_type string to enum
        if "warehouse_type" in update_dict and update_dict["warehouse_type"]:
            try:
                wh_type_str = str(update_dict["warehouse_type"]).lower()
                update_dict["warehouse_type"] = WarehouseType(wh_type_str)
            except (ValueError, KeyError):
                del update_dict["warehouse_type"]

        warehouse = self.warehouse_repo.update_warehouse(warehouse, update_dict)

        # If this is set as default, update others
        if warehouse.is_default:
            self.warehouse_repo.set_default_warehouse(warehouse.id, organization_id)

        return warehouse

    def delete_warehouse(
        self,
        warehouse_id: UUID,
        organization_id: UUID,
        user_id: UUID,
    ) -> Warehouse:
        """
        Soft delete a warehouse.

        Args:
            warehouse_id: Warehouse UUID
            organization_id: Organization UUID
            user_id: User UUID deleting the warehouse

        Returns:
            Deleted Warehouse object

        Raises:
            WarehouseNotFoundException: If warehouse not found
        """
        warehouse = self.warehouse_repo.get_warehouse_by_id(
            warehouse_id, organization_id
        )
        if not warehouse:
            raise WarehouseNotFoundException(
                f"Warehouse with ID {warehouse_id} not found"
            )

        warehouse.updated_by = user_id
        return self.warehouse_repo.soft_delete_warehouse(warehouse)

    def get_warehouses(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        warehouse_type: str | None = None,
        parent_warehouse_id: UUID | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        warehouse_ids: list[UUID] | None = None,
    ) -> tuple[list[Warehouse], dict, dict, dict]:
        """
        Get paginated list of warehouses with filters.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page
            is_active: Filter by active status
            warehouse_type: Filter by warehouse type
            parent_warehouse_id: Filter by parent warehouse
            search: Search term
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            warehouse_ids: Optional list of warehouse IDs to restrict to

        Returns:
            Tuple of (list of warehouses, pagination metadata, status counts, type counts)
        """
        # Convert warehouse_type string to enum
        warehouse_type_enum = None
        if warehouse_type:
            try:
                wh_type_str = str(warehouse_type).lower()
                warehouse_type_enum = WarehouseType(wh_type_str)
            except (ValueError, KeyError):
                pass

        # Ensure page_size doesn't exceed maximum
        page_size = min(page_size, 100)

        # Get warehouses from repository
        warehouses, total_count = self.warehouse_repo.list_warehouses(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            is_active=is_active,
            warehouse_type=warehouse_type_enum,
            parent_warehouse_id=parent_warehouse_id,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            warehouse_ids=warehouse_ids,
        )

        # Get status and type counts (scoped to warehouse_ids if provided)
        status_counts = self.warehouse_repo.get_warehouse_status_counts(organization_id, warehouse_ids=warehouse_ids)
        type_counts = self.warehouse_repo.get_warehouse_type_counts(organization_id, warehouse_ids=warehouse_ids)

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

        self._apply_derived_capacity(warehouses)

        return warehouses, pagination, status_counts, type_counts

    def _apply_derived_capacity(self, warehouses: list[Warehouse]) -> None:
        """Populate each warehouse's total capacity and UOM from its active bins.

        Warehouse capacity is modelled as a roll-up of the active bin locations
        (the layout is the source of truth). Only warehouses with bins get a
        derived value; warehouses without a layout keep their stored value.
        """
        if not warehouses:
            return

        ids = [w.id for w in warehouses]
        rows = (
            self.db.query(
                WarehouseLocation.warehouse_id,
                func.sum(WarehouseLocation.capacity),
                func.max(WarehouseLocation.capacity_uom),
            )
            .filter(
                WarehouseLocation.warehouse_id.in_(ids),
                WarehouseLocation.location_type == LocationType.BIN.value,
                WarehouseLocation.is_active.is_(True),
            )
            .group_by(WarehouseLocation.warehouse_id)
            .all()
        )

        capacity_map: dict[UUID, tuple[Decimal | None, str | None]] = {
            row[0]: (row[1], row[2]) for row in rows
        }

        for warehouse in warehouses:
            row = capacity_map.get(warehouse.id)
            if row is None:
                continue
            total, uom = row
            if total is not None:
                warehouse.total_capacity = int(total)
            if warehouse.capacity_uom is None and uom:
                warehouse.capacity_uom = uom

    def get_warehouse_tree(self, organization_id: UUID) -> list[WarehouseTreeNode]:
        """
        Get warehouses as a tree structure.

        Args:
            organization_id: Organization UUID

        Returns:
            List of root-level warehouse tree nodes
        """
        all_warehouses = self.warehouse_repo.get_all_warehouses(organization_id)

        # Build tree
        root_nodes = []
        children_map: dict[UUID, list] = {}

        for warehouse in all_warehouses:
            if warehouse.parent_warehouse_id:
                if warehouse.parent_warehouse_id not in children_map:
                    children_map[warehouse.parent_warehouse_id] = []
                children_map[warehouse.parent_warehouse_id].append(warehouse)
            else:
                root_nodes.append(warehouse)

        def build_tree_node(warehouse: Warehouse) -> WarehouseTreeNode:
            children = children_map.get(warehouse.id, [])
            return WarehouseTreeNode(
                id=warehouse.id,
                name=warehouse.name,
                code=warehouse.code,
                warehouse_type=str(warehouse.warehouse_type.value)
                if warehouse.warehouse_type
                else "warehouse",
                is_active=warehouse.is_active,
                is_default=warehouse.is_default,
                children=[build_tree_node(c) for c in children],
            )

        return [build_tree_node(w) for w in root_nodes]

    def _would_create_circular_reference(
        self, warehouse_id: UUID, new_parent_id: UUID, organization_id: UUID
    ) -> bool:
        """
        Check if setting new_parent_id as parent would create circular reference.

        Args:
            warehouse_id: Warehouse being updated
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
            if current_id == warehouse_id:
                return True

            visited.add(current_id)

            parent = self.warehouse_repo.get_warehouse_by_id(
                current_id, organization_id
            )
            if not parent:
                break

            current_id = parent.parent_warehouse_id

        return False
