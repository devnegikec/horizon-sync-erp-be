"""System Admin Role CRUD Endpoints

Endpoints for managing system admin roles and listing available permissions.
All endpoints are guarded by `system_admin.master` (Super Admin only).
Queries the identity database directly via SQLAlchemy (same pattern as billing.py).
"""

import logging
import uuid
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

from app.config import settings
from app.core.authorization import SYSTEM_ADMIN_MASTER
from app.dependencies import CurrentUser, require_permission

logger = logging.getLogger(__name__)

router = APIRouter()


# ── Request / Response Models ───────────────────────────────────────


class PermissionOut(BaseModel):
    id: str
    code: str
    name: str
    description: Optional[str] = None


class RoleOut(BaseModel):
    id: str
    name: str
    code: str
    description: Optional[str] = None
    is_system: bool = True
    permissions: List[PermissionOut] = []


class RoleCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    permission_ids: List[str] = Field(default_factory=list)


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    permission_ids: Optional[List[str]] = None


# ── Helpers ─────────────────────────────────────────────────────────


def _get_identity_engine():
    """Create a short-lived engine for the identity database."""
    if not settings.identity_database_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Identity database not configured",
        )
    return create_engine(settings.identity_database_url, pool_size=2, max_overflow=0)


def _get_master_org_id(conn) -> str:
    """Return the master organization ID from the identity database."""
    row = conn.execute(
        text("SELECT id FROM organizations WHERE organization_type = 'master' LIMIT 1")
    ).fetchone()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Master organization not found",
        )
    return str(row[0])


# ── Endpoints ───────────────────────────────────────────────────────


@router.get(
    "",
    response_model=List[RoleOut],
    summary="List system admin roles",
    description="List all system admin roles with their associated permissions.",
)
async def list_roles(
    _current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_MASTER)),
):
    """List roles scoped to the master organization with permissions."""
    try:
        engine = _get_identity_engine()
        with engine.connect() as conn:
            master_org_id = _get_master_org_id(conn)

            # Fetch only roles belonging to the master organization
            roles_rows = conn.execute(
                text(
                    "SELECT r.id, r.name, r.code, r.description, r.is_system "
                    "FROM roles r "
                    "WHERE r.organization_id = :org_id "
                    "ORDER BY r.hierarchy_level DESC, r.created_at"
                ),
                {"org_id": master_org_id},
            ).fetchall()

            results: list[dict] = []
            for r in roles_rows:
                role_id = str(r[0])
                # Fetch permissions linked to this role
                perm_rows = conn.execute(
                    text(
                        "SELECT p.id, p.code, p.name, p.description "
                        "FROM permissions p "
                        "JOIN role_permissions rp ON rp.permission_id = p.id "
                        "WHERE rp.role_id = :role_id "
                        "ORDER BY p.code"
                    ),
                    {"role_id": role_id},
                ).fetchall()

                permissions = [
                    {
                        "id": str(p[0]),
                        "code": p[1],
                        "name": p[2],
                        "description": p[3],
                    }
                    for p in perm_rows
                ]

                results.append(
                    {
                        "id": role_id,
                        "name": r[1],
                        "code": r[2],
                        "description": r[3],
                        "is_system": r[4],
                        "permissions": permissions,
                    }
                )

        return results

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list system admin roles: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list roles: {str(e)}",
        )


@router.post(
    "",
    response_model=RoleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a system admin role",
    description="Create a new system admin role with permission links.",
)
async def create_role(
    request: RoleCreateRequest,
    _current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_MASTER)),
):
    """Create a system admin role with is_system=true, scoped to master org."""
    try:
        engine = _get_identity_engine()
        with engine.connect() as conn:
            master_org_id = _get_master_org_id(conn)
            role_id = str(uuid.uuid4())

            # Insert the role
            conn.execute(
                text(
                    "INSERT INTO roles (id, organization_id, name, code, description, is_system, is_active, created_at, updated_at) "
                    "VALUES (:id, :org_id, :name, :code, :description, true, true, NOW(), NOW())"
                ),
                {
                    "id": role_id,
                    "org_id": master_org_id,
                    "name": request.name,
                    "code": request.code,
                    "description": request.description,
                },
            )

            # Link permissions
            permissions = []
            for perm_id in request.permission_ids:
                rp_id = str(uuid.uuid4())
                conn.execute(
                    text(
                        "INSERT INTO role_permissions (id, role_id, permission_id) "
                        "VALUES (:id, :role_id, :perm_id)"
                    ),
                    {"id": rp_id, "role_id": role_id, "perm_id": perm_id},
                )

            conn.commit()

            # Fetch the linked permissions for the response
            perm_rows = conn.execute(
                text(
                    "SELECT p.id, p.code, p.name, p.description "
                    "FROM permissions p "
                    "JOIN role_permissions rp ON rp.permission_id = p.id "
                    "WHERE rp.role_id = :role_id "
                    "ORDER BY p.code"
                ),
                {"role_id": role_id},
            ).fetchall()

            permissions = [
                {"id": str(p[0]), "code": p[1], "name": p[2], "description": p[3]}
                for p in perm_rows
            ]

        return {
            "id": role_id,
            "name": request.name,
            "code": request.code,
            "description": request.description,
            "is_system": True,
            "permissions": permissions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create system admin role: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create role: {str(e)}",
        )


@router.patch(
    "/{role_id}",
    response_model=RoleOut,
    summary="Update a system admin role",
    description="Update role name and/or replace permission links.",
)
async def update_role(
    role_id: UUID,
    request: RoleUpdateRequest,
    _current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_MASTER)),
):
    """Update a system admin role's name/description and optionally replace permissions."""
    try:
        engine = _get_identity_engine()
        with engine.connect() as conn:
            role_id_str = str(role_id)

            # Verify role exists and is a system role
            existing = conn.execute(
                text("SELECT id, name, code, description FROM roles WHERE id = :id AND is_system = true"),
                {"id": role_id_str},
            ).fetchone()

            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="System admin role not found",
                )

            # Build update fields
            updates = []
            params: dict = {"id": role_id_str}
            if request.name is not None:
                updates.append("name = :name")
                params["name"] = request.name
            if request.description is not None:
                updates.append("description = :description")
                params["description"] = request.description

            if updates:
                updates.append("updated_at = NOW()")
                conn.execute(
                    text(f"UPDATE roles SET {', '.join(updates)} WHERE id = :id"),
                    params,
                )

            # Replace permission links if provided
            if request.permission_ids is not None:
                conn.execute(
                    text("DELETE FROM role_permissions WHERE role_id = :role_id"),
                    {"role_id": role_id_str},
                )
                for perm_id in request.permission_ids:
                    rp_id = str(uuid.uuid4())
                    conn.execute(
                        text(
                            "INSERT INTO role_permissions (id, role_id, permission_id) "
                            "VALUES (:id, :role_id, :perm_id)"
                        ),
                        {"id": rp_id, "role_id": role_id_str, "perm_id": perm_id},
                    )

            conn.commit()

            # Fetch updated role
            role_row = conn.execute(
                text("SELECT id, name, code, description, is_system FROM roles WHERE id = :id"),
                {"id": role_id_str},
            ).fetchone()

            perm_rows = conn.execute(
                text(
                    "SELECT p.id, p.code, p.name, p.description "
                    "FROM permissions p "
                    "JOIN role_permissions rp ON rp.permission_id = p.id "
                    "WHERE rp.role_id = :role_id "
                    "ORDER BY p.code"
                ),
                {"role_id": role_id_str},
            ).fetchall()

            permissions = [
                {"id": str(p[0]), "code": p[1], "name": p[2], "description": p[3]}
                for p in perm_rows
            ]

        return {
            "id": str(role_row[0]),
            "name": role_row[1],
            "code": role_row[2],
            "description": role_row[3],
            "is_system": role_row[4],
            "permissions": permissions,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update system admin role {role_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update role: {str(e)}",
        )


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a system admin role",
    description="Delete a system admin role and its RolePermission records.",
)
async def delete_role(
    role_id: UUID,
    _current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_MASTER)),
):
    """Delete a system admin role and its associated role_permissions records."""
    try:
        engine = _get_identity_engine()
        with engine.connect() as conn:
            role_id_str = str(role_id)

            # Verify role exists and is a system role
            existing = conn.execute(
                text("SELECT id FROM roles WHERE id = :id AND is_system = true"),
                {"id": role_id_str},
            ).fetchone()

            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="System admin role not found",
                )

            # Delete role_permissions first (cascade should handle this, but be explicit)
            conn.execute(
                text("DELETE FROM role_permissions WHERE role_id = :role_id"),
                {"role_id": role_id_str},
            )

            # Delete the role
            conn.execute(
                text("DELETE FROM roles WHERE id = :id"),
                {"id": role_id_str},
            )

            conn.commit()

        return None

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete system admin role {role_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete role: {str(e)}",
        )


@router.get(
    "/permissions",
    response_model=List[PermissionOut],
    summary="List system admin permissions",
    description="List all available system admin permissions (module = 'system_admin').",
)
async def list_permissions(
    _current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_MASTER)),
):
    """List all permissions (system_admin + org-level) for super admin."""
    try:
        engine = _get_identity_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, code, name, description "
                    "FROM permissions "
                    "WHERE is_active = true "
                    "ORDER BY code"
                )
            ).fetchall()

        return [
            {"id": str(r[0]), "code": r[1], "name": r[2], "description": r[3]}
            for r in rows
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to list system admin permissions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list permissions: {str(e)}",
        )
