"""Service layer for admin user management.

Proxies requests to identity-service which owns the users table.
"""

import logging
import math
from uuid import UUID

import httpx
from fastapi import HTTPException, status
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


class AdminUserService:
    def __init__(self, db: Session, token: str | None = None):
        self.db = db
        self.token = token

    def _headers(self) -> dict[str, str]:
        h: dict[str, str] = {}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _map_user_list_item(self, u: dict) -> AdminUserListItem:
        """Map identity-service user response to admin list item."""
        user_type = u.get("user_type", "user")
        if hasattr(user_type, "value"):
            user_type = user_type.value
        return AdminUserListItem(
            id=u["id"],
            email=u["email"],
            first_name=u.get("first_name", ""),
            last_name=u.get("last_name", ""),
            phone=u.get("phone"),
            roles=u.get("roles", []),
            user_type=user_type,
            is_active=u.get("is_active", True),
            organization_id=u.get("organization_id"),
            organization_name=u.get("organization_name"),
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

        return AdminUserDetailResponse(
            id=u["id"], email=u["email"],
            first_name=u.get("first_name", ""),
            last_name=u.get("last_name", ""),
            display_name=u.get("display_name"),
            phone=u.get("phone"),
            roles=u.get("roles", []),
            user_type=user_type,
            is_active=u.get("is_active", True),
            organization_id=u.get("organization_id"),
            organization_name=u.get("organization_name"),
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
            organization_id=data.organization_id,
            organization_name=None,
            created_at=u.get("created_at", ""),
            updated_at=u.get("updated_at"),
        )

    # ── Update ───────────────────────────────────────────────────────

    async def update_user(self, user_id: UUID, data: AdminUserUpdate) -> AdminUserDetailResponse:
        payload = data.model_dump(exclude_unset=True, mode="json")
        if "roles" in payload and payload["roles"] is not None:
            payload["roles"] = [r.value if hasattr(r, "value") else r for r in payload["roles"]]

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
            organization_id=u.get("organization_id"),
            organization_name=u.get("organization_name"),
            created_at=u.get("created_at", ""),
            updated_at=u.get("updated_at"),
        )

        return await self.get_user(user_id)
