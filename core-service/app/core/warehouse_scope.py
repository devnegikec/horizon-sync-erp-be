"""Warehouse scoping helper shared by WMS dashboard and reports.

Resolves the list of warehouse IDs a user may see based on their role and
warehouse-user assignments. Centralized here so the dashboard and the reports
endpoints apply identical scoping rules.
"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.warehouse_user import WarehouseUser


def get_user_warehouse_ids(
    db: Session,
    user_id: UUID,
    organization_id: UUID,
    user_type: str,
    permissions: list[str],
) -> list[UUID] | None:
    """Return the list of warehouse IDs assigned to this user.

    Returns None if the user has global/admin access (meaning no filter should
    be applied and all warehouses are visible).
    """
    if user_type in ("system_admin", "organization_admin") or "*.*" in permissions:
        return None  # global access — no warehouse filter

    # Check for primary (mother-warehouse) assignment → global access
    has_primary = (
        db.query(WarehouseUser)
        .filter(
            WarehouseUser.organization_id == organization_id,
            WarehouseUser.user_id == user_id,
            WarehouseUser.is_primary == True,
            WarehouseUser.is_active == True,
        )
        .first()
    )
    if has_primary:
        return None  # global access

    rows = (
        db.query(WarehouseUser.warehouse_id)
        .filter(
            WarehouseUser.organization_id == organization_id,
            WarehouseUser.user_id == user_id,
            WarehouseUser.is_active == True,
        )
        .all()
    )
    return [r.warehouse_id for r in rows]
