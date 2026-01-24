"""User service with business logic"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import UserNotFoundException
from app.models.base import UserStatus, UserType
from app.models.user import User
from app.repositories.user_repository import UserRepository


class UserService:
    """Service for user operations"""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def get_user_by_id(self, user_id: UUID) -> User:
        """
        Get user by ID.

        Args:
            user_id: User UUID

        Returns:
            User object

        Raises:
            UserNotFoundException: If user not found
        """
        user = self.user_repo.get_user_by_id(user_id)
        if not user:
            raise UserNotFoundException(f"User with ID {user_id} not found")
        return user

    def get_users(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        user_type: str | None = None,
        email_verified: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[User], dict]:
        """
        Get paginated list of users with filters.

        Args:
            page: Page number (1-indexed)
            page_size: Number of items per page
            status: Filter by user status
            user_type: Filter by user type
            email_verified: Filter by email verification status
            search: Search term for email, first_name, last_name
            sort_by: Field to sort by
            sort_order: Sort order (asc or desc)

        Returns:
            Tuple of (list of users, pagination metadata)
        """
        # Validate and convert enum values
        status_enum = None
        if status:
            try:
                status_enum = UserStatus(status)
            except ValueError:
                pass

        user_type_enum = None
        if user_type:
            try:
                user_type_enum = UserType(user_type)
            except ValueError:
                pass

        # Ensure page_size doesn't exceed maximum
        page_size = min(page_size, 100)

        # Get users from repository
        users, total_count = self.user_repo.list_users(
            page=page,
            page_size=page_size,
            status=status_enum,
            user_type=user_type_enum,
            email_verified=email_verified,
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

        return users, pagination
