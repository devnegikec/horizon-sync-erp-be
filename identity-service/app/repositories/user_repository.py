"""User repository for database operations"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.base import UserStatus, UserType
from app.models.user import User

logger = logging.getLogger(__name__)


class UserRepository:
    """Repository for user database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_user(self, user_data: dict) -> User:
        """
        Create a new user.

        Args:
            user_data: Dictionary containing user data

        Returns:
            Created User object
        """
        user = User(**user_data)
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def get_user_by_id(self, user_id: UUID) -> User | None:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User object or None if not found
        """
        return (
            self.db.query(User)
            .filter(User.id == user_id, User.deleted_at.is_(None))
            .first()
        )

    def get_user_by_email(self, email: str) -> User | None:
        """
        Get user by email address.

        Args:
            email: User email address

        Returns:
            User object or None if not found
        """
        return (
            self.db.query(User)
            .filter(User.email == email, User.deleted_at.is_(None))
            .first()
        )

    def update_user(self, user: User, update_data: dict) -> User:
        """
        Update user fields.

        Args:
            user: User object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated User object
        """
        for key, value in update_data.items():
            if hasattr(user, key):
                setattr(user, key, value)

        self.db.commit()
        self.db.refresh(user)
        return user

    def list_users(
        self,
        page: int = 1,
        page_size: int = 20,
        status: UserStatus | None = None,
        user_type: UserType | None = None,
        email_verified: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        organization_ids: list[UUID] | None = None,
    ) -> tuple[list[User], int]:
        """
        List users with pagination and filters.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by user status
            user_type: Filter by user type
            email_verified: Filter by email verification status
            search: Search term for email, first_name, last_name
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)
            organization_ids: If set, only users that belong to these organizations

        Returns:
            Tuple of (list of users, total count)
        """
        query = self.db.query(User).filter(User.deleted_at.is_(None))

        if organization_ids is not None:
            from app.models.role import UserOrganizationRole

            query = (
                query.join(
                    UserOrganizationRole,
                    UserOrganizationRole.user_id == User.id
                )
                .filter(
                    UserOrganizationRole.organization_id.in_(organization_ids),
                    UserOrganizationRole.is_active,
                )
                .distinct()
            )

        # Apply filters
        if status:
            query = query.filter(User.status == status)

        if user_type:
            query = query.filter(User.user_type == user_type)

        if email_verified is not None:
            query = query.filter(User.email_verified == email_verified)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    User.email.ilike(search_term),
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                )
            )

        # Get total count before pagination
        total_count = query.count()

        # Apply sorting
        sort_column = getattr(User, sort_by, User.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        users = query.offset(offset).limit(page_size).all()

        return users, total_count

    def get_user_status_counts(
        self,
        organization_ids: list[UUID] | None = None,
        user_type: UserType | None = None,
        email_verified: bool | None = None,
        search: str | None = None,
    ) -> dict[str, int]:
        """
        Get counts of users by status and mfa_enabled for the same scope as list_users.

        Uses the same filters (organization_ids, user_type, email_verified, search)
        but does not filter by status. Returns counts for active, inactive, suspended,
        pending, and mfa_enabled (count of users with MFA enabled).

        Returns:
            Dict with keys: active, inactive, suspended, pending, mfa_enabled
        """
        from sqlalchemy import distinct, func

        def apply_filters(q):
            if organization_ids is not None:
                from app.models.role import UserOrganizationRole

                q = (
                    q.join(
                        UserOrganizationRole,
                        UserOrganizationRole.user_id == User.id
                    )
                    .filter(
                        UserOrganizationRole.organization_id.in_(organization_ids),
                        UserOrganizationRole.is_active,
                    )
                    .distinct()
                )
            if user_type is not None:
                q = q.filter(User.user_type == user_type)
            if email_verified is not None:
                q = q.filter(User.email_verified == email_verified)
            if search:
                search_term = f"%{search}%"
                q = q.filter(
                    or_(
                        User.email.ilike(search_term),
                        User.first_name.ilike(search_term),
                        User.last_name.ilike(search_term),
                    )
                )
            return q

        count_expr = (
            func.count(distinct(User.id))
            if organization_ids is not None
            else func.count(User.id)
        )
        status_counts_query = self.db.query(User.status, count_expr).filter(
            User.deleted_at.is_(None)
        )
        status_counts_query = apply_filters(status_counts_query)
        status_counts = status_counts_query.group_by(User.status).all()

        result = {
            UserStatus.ACTIVE.value: 0,
            UserStatus.INACTIVE.value: 0,
            UserStatus.SUSPENDED.value: 0,
            UserStatus.PENDING.value: 0,
            "mfa_enabled": 0,
        }
        for status_val, count in status_counts:
            # Handle enum values safely
            if status_val is None:
                continue
            try:
                if hasattr(status_val, "value"):
                    key = status_val.value
                elif isinstance(status_val, str):
                    key = status_val
                else:
                    # Try to convert to string
                    key = str(status_val)
                if key in result:
                    result[key] = int(count) if count is not None else 0
            except (AttributeError, ValueError, TypeError) as e:
                # Log but don't fail - skip invalid status values
                logger.warning(f"Error processing status value {status_val}: {e}")
                continue

        mfa_count_expr = (
            func.count(distinct(User.id))
            if organization_ids is not None
            else func.count(User.id)
        )
        mfa_query = self.db.query(mfa_count_expr).filter(
            User.deleted_at.is_(None), User.mfa_enabled.is_(True)
        )
        mfa_query = apply_filters(mfa_query)
        result["mfa_enabled"] = mfa_query.scalar() or 0

        return result

    def email_exists(self, email: str) -> bool:
        """
        Check if email already exists.

        Args:
            email: Email address to check

        Returns:
            True if email exists, False otherwise
        """
        return (
            self.db.query(User)
            .filter(User.email == email, User.deleted_at.is_(None))
            .count()
            > 0
        )

    def soft_delete(self, user: User) -> User:
        """
        Soft delete user by setting deleted_at.

        Args:
            user: User object to soft delete

        Returns:
            Updated User object
        """
        user.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(user)
        return user
