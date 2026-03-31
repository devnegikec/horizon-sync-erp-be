"""Service layer for admin user management.

Proxies requests to identity-service which owns the users table.
Resolves organization names by querying the identity database directly
(read-only access via identity_database_url).
"""

import logging
import math
from typing import List
from uuid import UUID

import httpx
from fastapi import HTTPException, status
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.config import settings
from app.schemas.admin_organization import PaginationMeta
from app.schemas.admin_user import (
    AdminUserCreate,
    AdminUserDetailResponse,
    AdminUserListItem,
    AdminUserListResponse,
    AdminUserUpdate,
)

logger = logging.getLogger(__name__)

IDENTITY_API = f"{settings.identity_service_url}/api/v1/identity"

# Read-only engine for identity DB (org lookups)
_identity_engine = None
def _get_identity_engine():
    global _identity_engine
    if _identity_engine is None and settings.identity_database_url:
        _identity_engine = create_engine(settings.identity_database_url, pool_size=2, max_overflow=0)
    return _identity_engine


class AdminUserService:
    def __init__(self, db: Session, token: str | None = None):
        self.db = db
        self.token = token
        self._org_cache: dict[str, tuple[str | None, str | None]] = {}  # user_id -> (org_id, org_name)

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _resolve_user_orgs(self, user_ids: list[str]) -> None:
        """Batch-resolve organization_id and organization_name for users via identity DB."""
        engine = _get_identity_engine()
        if not engine or not user_ids:
            return
        missing = [uid for uid in user_ids if uid not in self._org_cache]
        if not missing:
            return
        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text("""
                        SELECT DISTINCT ON (uor.user_id)
                            uor.user_id::text,
                            uor.organization_id::text,
                            o.name as organization_name
                        FROM user_organization_roles uor
                        JOIN organizations o ON o.id = uor.organization_id
                        WHERE uor.user_id::text = ANY(:user_ids)
                        ORDER BY uor.user_id, uor.is_primary DESC, uor.created_at ASC
                    """),
                    {"user_ids": missing},
                )
                for row in result:
                    self._org_cache[row[0]] = (row[1], row[2])
        except Exception as e:
            logger.warning(f"Failed to resolve org names from identity DB: {e}")

    def _get_user_org(self, user_id: str | None) -> tuple[str | None, str | None]:
        """Return (organization_id, organization_name) for a user."""
        if not user_id:
            return (None, None)
        return self._org_cache.get(user_id, (None, None))

    def _map_user_list_item(self, u: dict) -> AdminUserListItem:
        """Map identity-service user response to admin list item."""
        user_type = u.get("user_type", "user")
        if hasattr(user_type, "value"):
            user_type = user_type.value
        uid = str(u["id"])
        org_id_from_api = u.get("organization_id")
        org_name_from_api = u.get("organization_name")
        # Use API data if available, otherwise use identity DB lookup
        if org_id_from_api and org_name_from_api:
            org_id, org_name = str(org_id_from_api), org_name_from_api
        else:
            org_id, org_name = self._get_user_org(uid)
        return AdminUserListItem(
            id=u["id"],
            email=u["email"],
            first_name=u.get("first_name", ""),
            last_name=u.get("last_name", ""),
            phone=u.get("phone"),
            roles=u.get("roles", []),
            user_type=user_type,
            is_active=u.get("is_active", True),
            organization_id=org_id,
            organization_name=org_name,
            created_at=u["created_at"],
        )

    # ── List ─────────────────────────────────────────────────────────

    async def list_users(
        self,
        organization_id: UUID | None = None,
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminUserListResponse:
        params: dict = {"page": page, "page_size": page_size, "sort_by": "created_at", "sort_order": "desc"}
        if organization_id:
            params["organization_id"] = str(organization_id)
        if search:
            params["search"] = search
        if is_active is not None:
            params["status"] = "active" if is_active else "inactive"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{IDENTITY_API}/users",
                params=params,
                headers=self._headers(),
            )

        if resp.status_code != 200:
            logger.error(f"Identity-service /users returned {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch users")

        data = resp.json()
        users_raw = data.get("users", [])
        pagination_raw = data.get("pagination", {})

        # Batch-resolve organization names from identity DB
        user_ids = [str(u["id"]) for u in users_raw]
        self._resolve_user_orgs(user_ids)

        users = [self._map_user_list_item(u) for u in users_raw]

        return AdminUserListResponse(
            users=users,
            pagination=PaginationMeta(
                page=pagination_raw.get("page", page),
                page_size=pagination_raw.get("page_size", page_size),
                total_items=pagination_raw.get("total_items", 0),
                total_pages=pagination_raw.get("total_pages", 0),
                has_next=pagination_raw.get("has_next", False),
                has_prev=pagination_raw.get("has_prev", False),
            ),
        )

    # ── Detail ───────────────────────────────────────────────────────

    async def get_user(self, user_id: UUID) -> AdminUserDetailResponse:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{IDENTITY_API}/users/{user_id}",
                headers=self._headers(),
            )

        if resp.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if resp.status_code != 200:
            logger.error(f"Identity-service /users/{user_id} returned {resp.status_code}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to fetch user")

        u = resp.json()
        user_type = u.get("user_type", "user")
        if hasattr(user_type, "value"):
            user_type = user_type.value

        uid = str(u["id"])
        org_id_from_api = u.get("organization_id")
        org_name_from_api = u.get("organization_name")
        if org_id_from_api and org_name_from_api:
            org_id, org_name = str(org_id_from_api), org_name_from_api
        else:
            self._resolve_user_orgs([uid])
            org_id, org_name = self._get_user_org(uid)

        return AdminUserDetailResponse(
            id=u["id"], email=u["email"],
            first_name=u.get("first_name", ""),
            last_name=u.get("last_name", ""),
            display_name=u.get("display_name"),
            phone=u.get("phone"),
            roles=u.get("roles", []),
            user_type=user_type,
            is_active=u.get("is_active", True),
            organization_id=org_id,
            organization_name=org_name,
            created_at=u["created_at"],
            updated_at=u.get("updated_at"),
        )

    # ── Create ───────────────────────────────────────────────────────

    async def create_user(self, data: AdminUserCreate) -> AdminUserDetailResponse:
        payload = data.model_dump(mode="json")
        payload["roles"] = [r.value if hasattr(r, "value") else r for r in data.roles]

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{IDENTITY_API}/users",
                json=payload,
                headers=self._headers(),
            )

        if resp.status_code == 409:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists")
        if resp.status_code not in (200, 201):
            logger.error(f"Identity-service POST /users returned {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to create user")

        u = resp.json()
        user_type = u.get("user_type", "user")
        if hasattr(user_type, "value"):
            user_type = user_type.value

        return AdminUserDetailResponse(
            id=u["id"],
            email=u["email"],
            first_name=u.get("first_name", ""),
            last_name=u.get("last_name", ""),
            display_name=u.get("display_name"),
            phone=u.get("phone"),
            roles=payload.get("roles", []),
            user_type=user_type,
            is_active=u.get("is_active", True),
            organization_id=str(data.organization_id),
            organization_name=None,  # Will be resolved on next fetch after org membership is created
            created_at=u.get("created_at", ""),
            updated_at=u.get("updated_at"),
        )

    # ── Update ───────────────────────────────────────────────────────

    async def update_user(self, user_id: UUID, data: AdminUserUpdate) -> AdminUserDetailResponse:
        payload = data.model_dump(exclude_unset=True, mode="json")
        if "roles" in payload and payload["roles"] is not None:
            payload["roles"] = [r.value if hasattr(r, "value") else r for r in payload["roles"]]

        # Convert is_active boolean to status string for identity service
        if "is_active" in payload:
            is_active = payload.pop("is_active")
            payload["status"] = "active" if is_active else "inactive"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(
                f"{IDENTITY_API}/users/{user_id}",
                json=payload,
                headers=self._headers(),
            )

        if resp.status_code == 404:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if resp.status_code != 200:
            logger.error(f"Identity-service PATCH /users/{user_id} returned {resp.status_code}: {resp.text}")
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Failed to update user")

        u = resp.json()
        user_type = u.get("user_type", "user")
        if hasattr(user_type, "value"):
            user_type = user_type.value

        uid = str(u["id"])
        org_id_from_api = u.get("organization_id")
        org_name_from_api = u.get("organization_name")
        if org_id_from_api and org_name_from_api:
            org_id, org_name = str(org_id_from_api), org_name_from_api
        else:
            self._resolve_user_orgs([uid])
            org_id, org_name = self._get_user_org(uid)

        return AdminUserDetailResponse(
            id=u["id"],
            email=u["email"],
            first_name=u.get("first_name", ""),
            last_name=u.get("last_name", ""),
            display_name=u.get("display_name"),
            phone=u.get("phone"),
            roles=u.get("roles", []),
            user_type=user_type,
            is_active=u.get("is_active", True),
            organization_id=org_id,
            organization_name=org_name,
            created_at=u.get("created_at", ""),
            updated_at=u.get("updated_at"),
        )

    # ── System Administration Methods ──────────────────────────────────

    async def get_system_admin_users(self) -> List[dict]:
        """Get all users with system admin roles in the master organization"""
        try:
            # Call identity service to get system admin users
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{IDENTITY_API}/organization-management/system-admin-users",
                    headers=self._headers(),
                    timeout=30.0,
                )
                
                if response.status_code == 404:
                    return []
                    
                response.raise_for_status()
                data = response.json()
                
                # Map to expected format
                admin_users = []
                for user in data.get("admin_users", []):
                    admin_users.append({
                        "user_id": user["user_id"],
                        "email": user["email"],
                        "first_name": user.get("first_name"),
                        "last_name": user.get("last_name"),
                        "roles": user.get("permissions", []),  # Map permissions to roles
                        "is_active": user.get("is_active", True),
                        "created_at": user.get("created_at", ""),
                        "last_login": user.get("last_login")
                    })
                
                return admin_users
                
        except httpx.RequestError as e:
            logger.error(f"Network error getting system admin users: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting system admin users: {e}")
            return []

    async def create_system_admin_user(self, user_data: dict) -> dict:
        """Create a new system admin user"""
        try:
            # Create user via identity service
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{IDENTITY_API}/admin/users",
                    headers=self._headers(),
                    json=user_data,
                    timeout=30.0,
                )
                
                response.raise_for_status()
                user_resp = response.json()
                
                # Map to expected format
                return {
                    "user_id": user_resp["id"],
                    "email": user_resp["email"],
                    "first_name": user_resp.get("first_name"),
                    "last_name": user_resp.get("last_name"),
                    "roles": user_data.get("roles", []),
                    "is_active": user_resp.get("is_active", True),
                    "created_at": user_resp.get("created_at", ""),
                    "last_login": None
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating system admin user: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to create system admin user")
        except Exception as e:
            logger.error(f"Error creating system admin user: {e}")
            raise HTTPException(status_code=500, detail="Failed to create system admin user")

    async def update_system_admin_user(self, user_id: UUID, updates: dict) -> dict:
        """Update system admin user"""
        try:
            # Update user via identity service
            async with httpx.AsyncClient() as client:
                response = await client.patch(
                    f"{IDENTITY_API}/users/{user_id}",
                    headers=self._headers(),
                    json=updates,
                    timeout=30.0,
                )
                
                response.raise_for_status()
                user_resp = response.json()
                
                # Map to expected format
                return {
                    "user_id": user_resp["id"],
                    "email": user_resp["email"],
                    "first_name": user_resp.get("first_name"),
                    "last_name": user_resp.get("last_name"),
                    "roles": user_resp.get("roles", []),
                    "is_active": user_resp.get("is_active", True),
                    "created_at": user_resp.get("created_at", ""),
                    "last_login": user_resp.get("last_login")
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating system admin user: {e}")
            raise HTTPException(status_code=e.response.status_code, detail="Failed to update system admin user")
        except Exception as e:
            logger.error(f"Error updating system admin user: {e}")
            raise HTTPException(status_code=500, detail="Failed to update system admin user")

    async def remove_system_admin_user(self, user_id: UUID) -> None:
        """Remove (deactivate) system admin user"""
        try:
            # Deactivate user via identity service
            await self.update_system_admin_user(user_id, {"is_active": False})
            
        except Exception as e:
            logger.error(f"Error removing system admin user: {e}")
            raise HTTPException(status_code=500, detail="Failed to remove system admin user")
