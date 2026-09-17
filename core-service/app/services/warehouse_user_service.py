"""Warehouse-user assignment service"""

from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.authorization import WAREHOUSE_MANAGE, has_global_warehouse_access
from app.core.exceptions import ResourceNotFoundException
from app.dependencies import has_permission
from app.models.pending_warehouse_assignment import PendingWarehouseAssignment
from app.models.warehouse import Warehouse
from app.models.warehouse_user import WarehouseUser
from app.schemas.common import PaginationMeta


class WarehouseUserService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self, data: dict, organization_id: UUID, created_by: UUID
    ) -> WarehouseUser:
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

    def create_pending(
        self,
        email: str,
        organization_id: UUID,
        warehouse_id: UUID,
        role: str,
        is_primary: bool,
        created_by: UUID,
    ) -> PendingWarehouseAssignment:
        """Store a pending assignment keyed by email (user hasn't accepted invite yet)."""
        # Delete any existing pending for this email + warehouse to avoid duplicates
        existing = (
            self.db.query(PendingWarehouseAssignment)
            .filter(
                PendingWarehouseAssignment.email == email,
                PendingWarehouseAssignment.organization_id == organization_id,
                PendingWarehouseAssignment.warehouse_id == warehouse_id,
            )
            .first()
        )
        if existing:
            self.db.delete(existing)
            self.db.flush()

        pending = PendingWarehouseAssignment(
            organization_id=organization_id,
            email=email,
            warehouse_id=warehouse_id,
            role=role,
            is_primary=is_primary,
            created_by=created_by,
        )
        self.db.add(pending)
        self.db.flush()
        self.db.refresh(pending)
        return pending

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
        current_user,  # CurrentUser from dependencies (has DB-derived permissions)
        organization_id: UUID | None = None,
    ) -> list[dict]:
        """Get the warehouses a user is allowed to see.

        Resolution order (``current_user`` carries DB-derived permissions):

          1. Pending email-keyed assignments are resolved first, so the
             warehouse selection made at invitation time is honoured on the
             invited user's very first request.
          2. System admins, org admins, and ``*.*`` holders see every warehouse
             (:func:`has_global_warehouse_access`).
          3. A primary (mother-warehouse) assignment sees every warehouse.
          4. Otherwise the user sees only their explicitly assigned warehouses.

        ``warehouse.manage`` deliberately no longer implies global visibility.
        WMS Managers hold it for worker/device CRUD but must stay scoped to their
        ``WarehouseUser`` assignments. As a backwards-compatible fallback, a
        ``warehouse.manage`` holder with *no* assignment at all (for example a
        WMS Admin that was never scoped to specific warehouses) keeps the legacy
        organization-wide view.
        """
        import logging

        logger = logging.getLogger(__name__)
        user_id = current_user.id
        org_id = organization_id or current_user.organization_id
        user_type = current_user.user_type
        user_email = getattr(current_user, "email", None)
        logger.info(
            "[get_user_warehouses] user_id=%s org_id=%s user_type=%s",
            user_id,
            org_id,
            user_type,
        )

        def _all_active_warehouses(reason: str) -> list[dict]:
            """Every active warehouse the caller may see organization-wide.

            System-admin tokens carry no organization, so the tenancy filter is
            omitted for them instead of filtering on ``NULL`` (which would
            silently return nothing).
            """
            query = self.db.query(Warehouse).filter(Warehouse.is_active == True)
            if org_id is not None:
                query = query.filter(Warehouse.organization_id == org_id)
            warehouses = query.order_by(Warehouse.name).all()
            logger.info(
                "[get_user_warehouses] %s path: found %d warehouses for org %s",
                reason,
                len(warehouses),
                org_id,
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

        # 1. Resolve pending assignments before deciding on visibility, so an
        #    invitation-time assignment can never be bypassed.
        self._resolve_pending_assignments(
            user_id=user_id, org_id=org_id, email=user_email, logger=logger
        )

        # 2. Organization-wide access is reserved for admins / wildcard holders.
        if has_global_warehouse_access(user_type, current_user.permissions):
            return _all_active_warehouses("admin/wildcard")

        # 3. Primary (mother-warehouse) assignment grants the organization view.
        has_primary = (
            self.db.query(WarehouseUser)
            .filter(
                WarehouseUser.organization_id == org_id,
                WarehouseUser.user_id == user_id,
                WarehouseUser.is_primary == True,
                WarehouseUser.is_active == True,
            )
            .first()
        )
        if has_primary:
            return _all_active_warehouses("primary")

        # 4. Explicitly assigned warehouses.
        results = (
            self.db.query(WarehouseUser, Warehouse)
            .join(Warehouse, WarehouseUser.warehouse_id == Warehouse.id)
            .filter(
                WarehouseUser.organization_id == org_id,
                WarehouseUser.user_id == user_id,
                WarehouseUser.is_active == True,
            )
            .order_by(Warehouse.name)
            .all()
        )
        logger.info(
            "[get_user_warehouses] assignment path: found %d warehouses", len(results)
        )

        if results:
            return [
                {
                    "id": warehouse.id,
                    "name": warehouse.name,
                    "code": warehouse.code,
                    "city": warehouse.city,
                    "type": warehouse.warehouse_type.value
                    if warehouse.warehouse_type
                    else None,
                    "is_default": warehouse.is_default,
                    "assignment_role": assignment.role.value
                    if assignment.role
                    else None,
                    "assignment_id": assignment.id,
                }
                for assignment, warehouse in results
            ]

        # 5. Backwards-compatible fallback: a warehouse administrator that was
        #    never scoped to specific warehouses keeps the organization-wide view.
        if has_permission(current_user.permissions, WAREHOUSE_MANAGE):
            return _all_active_warehouses("unassigned warehouse.manage")

        return []

    def _resolve_pending_assignments(
        self,
        user_id: UUID,
        org_id: UUID | None,
        email: str | None,
        logger=None,
    ) -> None:
        """Turn pending (email-keyed) assignments into real WarehouseUser rows.

        Members of the warehouse_users table are matched by email
        (case-insensitive) so an invited user's assignments are materialised the
        first time they read their warehouses. Pending rows are only applied for
        warehouses owned by ``org_id``.
        """
        if not email or org_id is None:
            return

        pending = (
            self.db.query(PendingWarehouseAssignment)
            .filter(
                func.lower(PendingWarehouseAssignment.email) == email.lower(),
                PendingWarehouseAssignment.organization_id == org_id,
            )
            .all()
        )
        if not pending:
            return

        # Only materialise pending rows whose warehouse belongs to the caller's
        # organization; a stale or forged row must never leak a foreign
        # warehouse into the user's assigned list.
        warehouse_ids = {p.warehouse_id for p in pending}
        valid_warehouse_ids = {
            wid
            for (wid,) in self.db.query(Warehouse.id)
            .filter(
                Warehouse.id.in_(warehouse_ids),
                Warehouse.organization_id == org_id,
            )
            .all()
        }

        resolved = 0
        for p in pending:
            if p.warehouse_id not in valid_warehouse_ids:
                # Drop the invalid pending row rather than re-processing it on
                # every subsequent read.
                self.db.delete(p)
                continue

            existing = (
                self.db.query(WarehouseUser)
                .filter(
                    WarehouseUser.user_id == user_id,
                    WarehouseUser.warehouse_id == p.warehouse_id,
                    WarehouseUser.organization_id == org_id,
                )
                .first()
            )
            if existing:
                # Respect an administrator's deactivation: a pending invitation
                # must not silently reactivate (and overwrite the role of) a
                # disabled assignment.
                if existing.is_active:
                    existing.role = p.role
                    existing.is_primary = p.is_primary
            else:
                self.db.add(
                    WarehouseUser(
                        organization_id=org_id,
                        user_id=user_id,
                        warehouse_id=p.warehouse_id,
                        role=p.role,
                        is_primary=p.is_primary,
                        is_active=True,
                    )
                )
            self.db.delete(p)
            resolved += 1

        self.db.commit()
        if logger:
            logger.info(
                "[get_user_warehouses] resolved %d pending assignment(s)",
                resolved,
            )

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
