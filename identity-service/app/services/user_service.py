"""User service with business logic"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateEmailException, UserNotFoundException
from app.core.security import hash_password
from app.models.base import OrganizationType, UserStatus, UserType
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.organization_service import OrganizationService


class UserService:
    """Service for user operations"""

    def __init__(self, db: Session):
        self.db = db
        self.user_repo = UserRepository(db)

    def create_user(self, data: dict) -> User:
        """
        Create a new user. Hashes password. Raises DuplicateEmailException if email exists.
        """
        email = (data.get("email") or "").strip().lower()
        if self.user_repo.email_exists(email):
            raise DuplicateEmailException(f"User with email '{email}' already exists")
        payload = dict(data)
        if "password" in payload:
            payload["password_hash"] = hash_password(payload.pop("password"))
        if "user_type" in payload and payload["user_type"]:
            payload["user_type"] = UserType(payload["user_type"])
        if "status" in payload and payload["status"]:
            payload["status"] = UserStatus(payload["status"])
        return self.user_repo.create_user(payload)

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
        organization_ids: list[UUID] | None = None,
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
            organization_ids: If set, only users in these organizations

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
            organization_ids=organization_ids,
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

    def get_user_status_counts(
        self,
        organization_ids: list[UUID] | None = None,
        user_type: str | None = None,
        email_verified: bool | None = None,
        search: str | None = None,
    ) -> dict[str, int]:
        """
        Get counts by status and mfa_enabled for the same scope as get_users.
        Returns dict with keys: active, inactive, suspended, pending, mfa_enabled.
        """
        user_type_enum = None
        if user_type:
            try:
                user_type_enum = UserType(user_type)
            except ValueError:
                pass
        return self.user_repo.get_user_status_counts(
            organization_ids=organization_ids,
            user_type=user_type_enum,
            email_verified=email_verified,
            search=search,
        )

    def update_user(self, user_id: UUID, data: dict) -> User:
        """
        Update user by ID. Partial update; enum fields converted.
        Raises UserNotFoundException if not found.
        """
        user = self.get_user_by_id(user_id)
        payload = {k: v for k, v in data.items() if v is not None}
        if "user_type" in payload:
            payload["user_type"] = UserType(payload["user_type"])
        if "status" in payload:
            payload["status"] = UserStatus(payload["status"])
        if "password" in payload:
            payload["password_hash"] = hash_password(payload.pop("password"))
        return self.user_repo.update_user(user, payload)

    def delete_user(self, user_id: UUID) -> None:
        """Soft delete user by ID. Raises UserNotFoundException if not found."""
        user = self.get_user_by_id(user_id)
        self.user_repo.soft_delete(user)

    # System Admin Role Assignment Methods (Task 1C-2)
    
    def validate_system_admin_user(self, user: User, organization_id: UUID) -> bool:
        """
        Validate that system admin user belongs to master organization.
        
        Task 1C-2: System admin users must belong to the master organization
        to have cross-org permissions.
        
        Args:
            user: User object to validate
            organization_id: Organization ID the user is being assigned to
            
        Returns:
            True if validation passes
            
        Raises:
            ValueError: If system admin user is not in master organization
        """
        if user.user_type == UserType.SYSTEM_ADMIN:
            org_service = OrganizationService(self.db)
            master_org = org_service.get_master_organization()
            
            if not master_org:
                raise ValueError("Master organization not found - cannot assign system admin role")
                
            if organization_id != master_org.id:
                raise ValueError(
                    "System admin users must belong to the master organization. "
                    f"Expected organization ID: {master_org.id}, got: {organization_id}"
                )
        
        return True
    
    def create_system_admin_user(
        self, 
        data: dict, 
        organization_id: UUID, 
        created_by_user_type: UserType = None
    ) -> User:
        """
        Create system admin user with validation.
        
        Task 1C-2: Only system admins can create other system admin users,
        and they must be assigned to the master organization.
        
        Args:
            data: User data dictionary
            organization_id: Organization to assign user to
            created_by_user_type: User type of the user creating this admin
            
        Returns:
            Created user object
            
        Raises:
            ValueError: If validation fails
        """
        user_type = data.get("user_type")
        
        # Check if creating system admin user
        if user_type == UserType.SYSTEM_ADMIN or user_type == "system_admin":
            # Only system admins can create system admin users
            if created_by_user_type != UserType.SYSTEM_ADMIN:
                raise ValueError("Only system administrators can create system admin users")
            
            # Ensure it's being assigned to master organization
            org_service = OrganizationService(self.db)
            master_org = org_service.get_master_organization()
            
            if not master_org:
                raise ValueError("Master organization not found - cannot create system admin")
                
            if organization_id != master_org.id:
                raise ValueError("System admin users must be assigned to the master organization")
        
        # Create the user
        return self.create_user(data)
        
    def update_user_with_admin_validation(
        self, 
        user_id: UUID, 
        data: dict, 
        updated_by_user_type: UserType = None
    ) -> User:
        """
        Update user with system admin validation.
        
        Task 1C-2: Prevent unauthorized changes to system admin users.
        
        Args:
            user_id: User ID to update
            data: Update data
            updated_by_user_type: User type of user making the update
            
        Returns:
            Updated user object
            
        Raises:
            ValueError: If validation fails
        """
        user = self.get_user_by_id(user_id)
        new_user_type = data.get("user_type")
        
        # Check if trying to make user system admin
        if new_user_type and (new_user_type == UserType.SYSTEM_ADMIN or new_user_type == "system_admin"):
            if updated_by_user_type != UserType.SYSTEM_ADMIN:
                raise ValueError("Only system administrators can grant system admin privileges")
                
        # Check if trying to modify existing system admin
        if user.user_type == UserType.SYSTEM_ADMIN:
            if updated_by_user_type != UserType.SYSTEM_ADMIN:
                raise ValueError("Only system administrators can modify system admin users")
        
        return self.update_user(user_id, data)
    
    def can_access_cross_org_operations(self, user: User) -> bool:
        """
        Check if user can perform cross-organization operations.
        
        Task 1C-2: System admin users from master org can access cross-org operations.
        
        Args:
            user: User to check
            
        Returns:
            True if user can access cross-org operations
        """
        if user.user_type != UserType.SYSTEM_ADMIN:
            return False
            
        # Get user's organization and check if it's master org
        from app.models.role import UserOrganizationRole
        user_orgs = (
            self.db.query(UserOrganizationRole)
            .filter(
                UserOrganizationRole.user_id == user.id,
                UserOrganizationRole.is_active == True
            )
            .all()
        )
        
        org_service = OrganizationService(self.db)
        master_org = org_service.get_master_organization()
        
        if not master_org:
            return False
            
        # Check if user belongs to master organization
        return any(role.organization_id == master_org.id for role in user_orgs)
