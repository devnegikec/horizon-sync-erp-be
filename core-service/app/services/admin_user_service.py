"""Service layer for admin user management.

Orchestrates repository calls, enforces business rules (duplicate email,
role validation), and handles password hashing for new user creation.
"""

import math
from uuid import UUID

import bcrypt
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.admin_user_repository import AdminUserRepository
from app.schemas.admin_user import (
    AdminUserCreate,
    AdminUserDetailResponse,
    AdminUserListItem,
    AdminUserListResponse,
    AdminUserUpdate,
)
from app.schemas.admin_organization import PaginationMeta


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pwd_bytes, salt).decode("utf-8")


class AdminUserService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AdminUserRepository(db)
        # TODO (task 11.3): integrate AdminAuditService

    # ── Create ───────────────────────────────────────────────────────

    def create_user(self, data: AdminUserCreate) -> AdminUserDetailResponse:
        """Create a new user. Raises 409 if email is taken."""
        if self.repo.email_exists(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        user_dict = {
            "email": data.email,
            "password_hash": _hash_password(data.password),
            "first_name": data.first_name,
            "last_name": data.last_name,
            "phone": data.phone,
            "user_type": data.user_type,
            "organization_id": data.organization_id,
            "roles": [r.value for r in data.roles],
        }
        created = self.repo.create_user(user_dict)
        self.db.commit()
        return AdminUserDetailResponse(**created)

    # ── List ─────────────────────────────────────────────────────────

    def list_users(
        self,
        organization_id: UUID | None = None,
        search: str | None = None,
        is_active: bool | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> AdminUserListResponse:
        users, total = self.repo.list_users(
            organization_id=organization_id,
            search=search,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )
        total_pages = max(1, math.ceil(total / page_size))
        return AdminUserListResponse(
            users=[AdminUserListItem(**u) for u in users],
            pagination=PaginationMeta(
                page=page,
                page_size=page_size,
                total_items=total,
                total_pages=total_pages,
                has_next=page < total_pages,
                has_prev=page > 1,
            ),
        )

    # ── Detail ───────────────────────────────────────────────────────

    def get_user(self, user_id: UUID) -> AdminUserDetailResponse:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return AdminUserDetailResponse(**user)

    # ── Update ───────────────────────────────────────────────────────

    def update_user(
        self,
        user_id: UUID,
        data: AdminUserUpdate,
    ) -> AdminUserDetailResponse:
        existing = self.repo.get_by_id(user_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        update_dict = data.model_dump(exclude_unset=True)

        # Convert role enums to strings
        if "roles" in update_dict and update_dict["roles"] is not None:
            update_dict["roles"] = [
                r.value if hasattr(r, "value") else r for r in update_dict["roles"]
            ]

        updated = self.repo.update_user(user_id, update_dict)
        self.db.commit()

        # TODO (task 11.3): audit log for role changes and activation/deactivation

        return AdminUserDetailResponse(**updated)  # type: ignore
