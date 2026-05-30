"""Warehouse-user assignment service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.warehouse import Warehouse
from app.models.warehouse_user import WarehouseUser
from app.schemas.common import PaginationMeta


class WarehouseUserService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, organization_id: UUID, created_by: UUID) -> WarehouseUser:
        """Assign a user to a warehouse."""
        payload = dict(data)
        payload["organization_id"] = organization_id

        # Check for existing active assignment
        existing = (
            self.db.query(WarehouseUser)
            .filter(
                WarehouseUser.organization_id == organization_id,
                WarehouseUser.user_id == payload["user_id"],
                WarehouseUser.warehouse_id == payload["warehouse_id"],
                WarehouseUser.is_active == True,
            )
            .first()
        )
        if existing:
            # Update the existing assignment instead of creating a duplicate
            for key, value in payload.items():
                if value is not None and hasattr(existing, key):
                    setattr(existing, key, value)
            self.db.flush()
            self.db.refresh(existing)
            return existing

        assignment = WarehouseUser(**payload)
        self.db.add(assignment)
        self.db.flush()
        self.db.refresh(assignment)
        return assignment

    def get_list(
        self,
        organization_id: UUID,
        warehouse_id: UUID | None = None,
        user_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], PaginationMeta]:
        """List warehouse-user assignments with warehouse names."""
        query = (
            self.db.query(WarehouseUser, Warehouse)
            .join(Warehouse, WarehouseUser.warehouse_id == Warehouse.id)
            .filter(
                WarehouseUser.organization_id == organization_id,
                WarehouseUser.is_active == True,
            )
        )
        if warehouse_id:
            query = query.filter(WarehouseUser.warehouse_id == warehouse_id)
        if user_id:
            query = query.filter(WarehouseUser.user_id == user_id)

        total = query.count()

        results = (
            query.order_by(Warehouse.name)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items = []
        for assignment, warehouse in results:
            data = {
                "id": assignment.id,
                "organization_id": assignment.organization_id,
                "user_id": assignment.user_id,
                "warehouse_id": assignment.warehouse_id,
                "role": assignment.role.value if assignment.role else None,
                "is_primary": assignment.is_primary,
                "is_active": assignment.is_active,
                "warehouse_name": warehouse.name if warehouse else None,
                "warehouse_code": warehouse.code if warehouse else None,
                "extra_data": assignment.extra_data,
                "created_at": assignment.created_at,
                "updated_at": assignment.updated_at,
            }
            items.append(data)

        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
            has_next=page * page_size < total,
            has_prev=page > 1,
        )
        return items, pagination

    def get_user_warehouses(
        self,
        user_id: UUID,
        organization_id: UUID,
    ) -> list[dict]:
        """Get warehouses assigned to a user.

        If no explicit assignments exist, return all active warehouses
        for backward compatibility.
        """
        # Check if user has any explicit assignments
        has_assignments = (
            self.db.query(WarehouseUser)
            .filter(
                WarehouseUser.organization_id == organization_id,
                WarehouseUser.user_id == user_id,
                WarehouseUser.is_active == True,
            )
            .first()
        )

        if not has_assignments:
            # Fallback: return all active warehouses
            warehouses = (
                self.db.query(Warehouse)
                .filter(
                    Warehouse.organization_id == organization_id,
                    Warehouse.is_active == True,
                )
                .order_by(Warehouse.name)
                .all()
            )
            return [
                {
                    "id": w.id,
                    "name": w.name,
                    "code": w.code,
                    "city": w.city,
                    "type": w.warehouse_type.value if w.warehouse_type else None,
                    "is_default": w.is_default,
                }
                for w in warehouses
            ]

        # Return assigned warehouses
        results = (
            self.db.query(WarehouseUser, Warehouse)
            .join(Warehouse, WarehouseUser.warehouse_id == Warehouse.id)
            .filter(
                WarehouseUser.organization_id == organization_id,
                WarehouseUser.user_id == user_id,
                WarehouseUser.is_active == True,
            )
            .order_by(Warehouse.name)
            .all()
        )

        return [
            {
                "id": warehouse.id,
                "name": warehouse.name,
                "code": warehouse.code,
                "city": warehouse.city,
                "type": warehouse.warehouse_type.value if warehouse.warehouse_type else None,
                "is_default": warehouse.is_default,
                "assignment_role": assignment.role.value if assignment.role else None,
                "assignment_id": assignment.id,
            }
            for assignment, warehouse in results
        ]

    def update(
        self,
        assignment_id: UUID,
        data: dict,
        organization_id: UUID,
    ) -> dict:
        """Update a warehouse-user assignment."""
        assignment = (
            self.db.query(WarehouseUser)
            .filter(
                WarehouseUser.id == assignment_id,
                WarehouseUser.organization_id == organization_id,
            )
            .first()
        )
        if not assignment:
            raise ResourceNotFoundException("WarehouseUser", str(assignment_id))

        for key, value in data.items():
            if value is not None and hasattr(assignment, key):
                setattr(assignment, key, value)

        self.db.flush()
        self.db.refresh(assignment)

        warehouse = (
            self.db.query(Warehouse)
            .filter(Warehouse.id == assignment.warehouse_id)
            .first()
        )
        return {
            "id": assignment.id,
            "organization_id": assignment.organization_id,
            "user_id": assignment.user_id,
            "warehouse_id": assignment.warehouse_id,
            "role": assignment.role.value if assignment.role else None,
            "is_primary": assignment.is_primary,
            "is_active": assignment.is_active,
            "warehouse_name": warehouse.name if warehouse else None,
            "warehouse_code": warehouse.code if warehouse else None,
            "extra_data": assignment.extra_data,
            "created_at": assignment.created_at,
            "updated_at": assignment.updated_at,
        }

    def delete(self, assignment_id: UUID, organization_id: UUID) -> None:
        """Soft-delete a warehouse-user assignment."""
        assignment = (
            self.db.query(WarehouseUser)
            .filter(
                WarehouseUser.id == assignment_id,
                WarehouseUser.organization_id == organization_id,
            )
            .first()
        )
        if not assignment:
            raise ResourceNotFoundException("WarehouseUser", str(assignment_id))

        assignment.is_active = False
        self.db.flush()
