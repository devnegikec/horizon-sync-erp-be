"""Invitation service with business logic"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.base import UserStatus
from app.core.exceptions import (
    InvitationAlreadyAcceptedException,
    InvitationExpiredException,
    InvitationNotFoundException,
    PermissionDeniedException,
    UserAlreadyExistsException,
)
from app.core.authorization import has_permission, is_system_admin
from app.repositories.invitation_repository import InvitationRepository
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository

logger = logging.getLogger(__name__)

# Invitation expiration time in days
INVITATION_EXPIRY_DAYS = 7


def _generate_invitation_token() -> tuple[str, str]:
    """
    Generate a secure invitation token.

    Returns:
        Tuple of (plain_token, hashed_token)
    """
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    return token, token_hash


def _hash_token(token: str) -> str:
    """Hash a token for lookup."""
    return hashlib.sha256(token.encode()).hexdigest()


class InvitationService:
    """Service for invitation operations"""

    def __init__(self, db: Session):
        self.db = db
        self.invitation_repo = InvitationRepository(db)
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    def create_invitation(
        self,
        invitation_data: dict,
        inviter_id: UUID,
        inviter_permissions: list[str],
    ) -> dict:
        """
        Create a new invitation.

        Args:
            invitation_data: Dictionary containing invitation data
            inviter_id: UUID of the user sending the invitation
            inviter_permissions: List of permission codes the inviter has

        Returns:
            Invitation response dictionary with token

        Raises:
            PermissionDeniedException: If user doesn't have invite permission
            UserAlreadyExistsException: If user already exists in organization
        """
        logger.info(f"Creating invitation for: {invitation_data.get('email')}")

        # Check if user has invite permission
        self._validate_inviter_permissions(inviter_id, inviter_permissions)

        email = invitation_data.get("email")
        organization_id = invitation_data.get("organization_id")

        # Check if user already exists and is in the organization
        self._check_existing_membership(email, organization_id)

        # Check for existing pending invitation
        self._handle_existing_invitation(email, organization_id)

        # Create or reuse a pending user record so the user appears in the
        # user management list and can be edited (e.g. fix a wrong email
        # address and re-send the invitation) even when SMTP is not set up.
        first_name = invitation_data.get("first_name") or ""
        last_name = invitation_data.get("last_name") or ""
        role_id = invitation_data.get("role_id")

        existing_user = self.user_repo.get_user_by_email(email)
        if existing_user:
            user_id = existing_user.id
        else:
            from app.models.user import User
            user = User(
                email=email,
                password_hash="",  # Placeholder — set when invitation accepted
                first_name=first_name,
                last_name=last_name,
                status=UserStatus.PENDING,
            )
            self.db.add(user)
            self.db.flush()
            user_id = user.id
            logger.info(f"Pending user created: {user_id}")

        # Ensure org membership for the pending user
        self._ensure_pending_user_role(user_id, organization_id, role_id)

        # Generate token
        token, token_hash = _generate_invitation_token()

        # Prepare invitation data
        invitation_data = self._prepare_invitation_data(
            invitation_data, inviter_id, token_hash
        )

        invitation = self.invitation_repo.create_invitation(invitation_data)
        logger.info(f"Invitation created: {invitation.id}")

        result = self._invitation_to_dict(invitation)
        result["token"] = token  # Include token for sending in email
        return result

    def _validate_inviter_permissions(
        self, inviter_id: UUID, inviter_permissions: list[str]
    ) -> None:
        """Validate if the inviter has permission to create invitations."""
        if not self._has_invite_permission(inviter_permissions):
            logger.warning(f"User {inviter_id} lacks invite permission")
            raise PermissionDeniedException("You don't have permission to invite users")

    def _check_existing_membership(self, email: str, organization_id: UUID) -> None:
        """Check if user with email is already a member of the organization."""
        existing_user = self.user_repo.get_user_by_email(email)
        if existing_user:
            from app.models.role import UserOrganizationRole

            existing_membership = (
                self.db.query(UserOrganizationRole)
                .filter(
                    UserOrganizationRole.user_id == existing_user.id,
                    UserOrganizationRole.organization_id == organization_id,
                    UserOrganizationRole.is_active == True,  # noqa: E712
                )
                .first()
            )
            if existing_membership:
                raise UserAlreadyExistsException(
                    f"User with email '{email}' is already a member of this organization"
                )

    def _handle_existing_invitation(self, email: str, organization_id: UUID) -> None:
        """Cancel existing pending invitation for the same email and organization."""
        existing_invitation = self.invitation_repo.get_invitation_by_email_and_org(
            email, organization_id
        )
        if existing_invitation:
            # Cancel the old invitation and create a new one
            self.invitation_repo.update_invitation(
                existing_invitation, {"status": "cancelled"}
            )

    def _ensure_pending_user_role(
        self, user_id: UUID, organization_id: UUID, role_id: UUID | None
    ) -> None:
        """Ensure the pending user has an org membership row. Idempotent."""
        import uuid
        from app.models.role import UserOrganizationRole

        existing = (
            self.db.query(UserOrganizationRole)
            .filter(
                UserOrganizationRole.user_id == user_id,
                UserOrganizationRole.organization_id == organization_id,
            )
            .first()
        )
        if not existing:
            membership = UserOrganizationRole(
                id=uuid.uuid4(),
                user_id=user_id,
                organization_id=organization_id,
                role_id=role_id,
                is_active=True,
                is_primary=True,
            )
            self.db.add(membership)
            self.db.flush()
            logger.info(
                f"Org membership created for pending user {user_id} in org {organization_id}"
            )

    def _prepare_invitation_data(
        self, invitation_data: dict, inviter_id: UUID, token_hash: str
    ) -> dict:
        """Prepare invitation data dictionary for repository."""
        from uuid import uuid4

        # Set expiration
        expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)

        # Extract custom_permission_ids and store in extra_data (not a model column)
        custom_permission_ids = invitation_data.pop("custom_permission_ids", None) or []

        # Convert team_ids UUIDs to strings for JSONB storage
        if "team_ids" in invitation_data and invitation_data["team_ids"]:
            invitation_data["team_ids"] = [
                str(team_id) for team_id in invitation_data["team_ids"]
            ]

        # Merge custom_permission_ids into extra_data for persistence
        extra_data = invitation_data.get("extra_data") or {}
        if custom_permission_ids:
            extra_data["custom_permission_ids"] = [
                str(pid) for pid in custom_permission_ids
            ]
        invitation_data["extra_data"] = extra_data

        invitation_data["id"] = uuid4()  # Explicitly generate UUID to avoid blank ID
        invitation_data["token_hash"] = token_hash
        invitation_data["invited_by_id"] = inviter_id
        invitation_data["expires_at"] = expires_at
        invitation_data["status"] = "pending"

        return invitation_data

    def get_invitation_by_id(self, invitation_id: UUID) -> dict:
        """
        Get invitation by ID.

        Args:
            invitation_id: Invitation UUID

        Returns:
            Invitation response dictionary

        Raises:
            InvitationNotFoundException: If invitation not found
        """
        logger.debug(f"Fetching invitation: {invitation_id}")

        invitation = self.invitation_repo.get_invitation_by_id(invitation_id)

        if not invitation:
            logger.warning(f"Invitation not found: {invitation_id}")
            raise InvitationNotFoundException(
                f"Invitation with ID {invitation_id} not found"
            )

        return self._invitation_to_dict(invitation)

    def list_invitations(
        self,
        organization_id: UUID | None = None,
        skip: int = 0,
        limit: int = 10,
        status: str | None = None,
        search: str | None = None,
    ) -> dict:
        """
        List invitations with pagination and filters.

        Args:
            organization_id: Filter by organization
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status
            search: Search term

        Returns:
            Dictionary with invitations list and pagination info
        """
        logger.debug(
            f"Listing invitations - org_id: {organization_id}, "
            f"skip: {skip}, limit: {limit}"
        )

        invitations, total_count = self.invitation_repo.list_invitations(
            organization_id=organization_id,
            skip=skip,
            limit=limit,
            status=status,
            search=search,
        )

        return {
            "data": [self._invitation_to_dict(inv) for inv in invitations],
            "total": total_count,
            "skip": skip,
            "limit": limit,
        }

    def cancel_invitation(
        self,
        invitation_id: UUID,
        user_id: UUID,
        user_permissions: list[str],
    ) -> None:
        """
        Cancel an invitation.

        Args:
            invitation_id: Invitation UUID
            user_id: ID of the user cancelling
            user_permissions: List of permission codes

        Raises:
            InvitationNotFoundException: If invitation not found
            PermissionDeniedException: If user lacks permission
        """
        logger.info(f"Cancelling invitation: {invitation_id}")

        if not self._has_invite_permission(user_permissions):
            raise PermissionDeniedException(
                "You don't have permission to cancel invitations"
            )

        invitation = self.invitation_repo.get_invitation_by_id(invitation_id)

        if not invitation:
            raise InvitationNotFoundException(
                f"Invitation with ID {invitation_id} not found"
            )

        if invitation.status != "pending":
            raise InvitationAlreadyAcceptedException(
                f"Cannot cancel invitation with status '{invitation.status}'"
            )

        self.invitation_repo.update_invitation(invitation, {"status": "cancelled"})
        logger.info(f"Invitation cancelled: {invitation_id}")

    def resend_invitation(
        self,
        invitation_id: UUID,
        user_id: UUID,
        user_permissions: list[str],
    ) -> dict:
        """
        Resend an invitation with a new token.

        Args:
            invitation_id: Invitation UUID
            user_id: ID of the user resending
            user_permissions: List of permission codes

        Returns:
            Updated invitation with new token

        Raises:
            InvitationNotFoundException: If invitation not found
            PermissionDeniedException: If user lacks permission
        """
        logger.info(f"Resending invitation: {invitation_id}")

        if not self._has_invite_permission(user_permissions):
            raise PermissionDeniedException(
                "You don't have permission to resend invitations"
            )

        invitation = self.invitation_repo.get_invitation_by_id(invitation_id)

        if not invitation:
            raise InvitationNotFoundException(
                f"Invitation with ID {invitation_id} not found"
            )

        if invitation.status not in ["pending", "expired"]:
            raise InvitationAlreadyAcceptedException(
                f"Cannot resend invitation with status '{invitation.status}'"
            )

        # Generate new token
        token, token_hash = _generate_invitation_token()
        expires_at = datetime.now(timezone.utc) + timedelta(days=INVITATION_EXPIRY_DAYS)

        self.invitation_repo.update_invitation(
            invitation,
            {
                "token_hash": token_hash,
                "expires_at": expires_at,
                "status": "pending",
            },
        )

        logger.info(f"Invitation resent: {invitation_id}")

        result = self._invitation_to_dict(invitation)
        result["token"] = token
        return result

    def accept_invitation(
        self,
        token: str,
        password: str,
        first_name: str | None = None,
        last_name: str | None = None,
    ) -> dict:
        """
        Accept an invitation and create user account.

        Args:
            token: Invitation token
            password: Password for new account
            first_name: Optional first name override
            last_name: Optional last name override

        Returns:
            Dictionary with user and organization info

        Raises:
            InvitationNotFoundException: If invitation not found
            InvitationExpiredException: If invitation expired
            InvitationAlreadyAcceptedException: If already accepted
        """
        logger.info("Accepting invitation")

        invitation = self._get_validated_invitation(token)
        user = self._get_or_create_user_from_invitation(
            invitation, password, first_name, last_name
        )

        # Add user to organization with role(s)
        self._assign_user_roles_from_invitation(user, invitation)

        # Update invitation status
        self.invitation_repo.update_invitation(
            invitation,
            {
                "status": "accepted",
                "accepted_at": datetime.now(timezone.utc),
                "accepted_user_id": user.id,
            },
        )

        self.db.commit()

        logger.info(f"Invitation accepted by user: {user.id}")

        return {
            "message": "Invitation accepted successfully",
            "user_id": user.id,
            "organization_id": invitation.organization_id,
            "email": user.email,
        }

    def _get_validated_invitation(self, token: str):
        """Get and validate invitation by token."""
        token_hash = _hash_token(token)
        invitation = self.invitation_repo.get_invitation_by_token(token_hash)

        if not invitation:
            raise InvitationNotFoundException("Invalid invitation token")

        if invitation.status == "accepted":
            raise InvitationAlreadyAcceptedException("Invitation already accepted")

        if invitation.status == "cancelled":
            raise InvitationNotFoundException("Invitation has been cancelled")

        if invitation.status == "expired" or invitation.expires_at < datetime.now(timezone.utc):
            self.invitation_repo.update_invitation(invitation, {"status": "expired"})
            raise InvitationExpiredException("Invitation has expired")

        return invitation

    def _get_or_create_user_from_invitation(
        self, invitation, password: str, first_name: str | None, last_name: str | None
    ):
        """Get existing user or create a new one from invitation data."""
        existing_user = self.user_repo.get_user_by_email(invitation.email)

        if existing_user:
            return existing_user

        # Create new user
        from app.core.security import hash_password

        user_data = {
            "email": invitation.email,
            "password_hash": hash_password(password),
            "first_name": first_name or invitation.first_name or "",
            "last_name": last_name or invitation.last_name or "",
            "status": UserStatus.ACTIVE,
            "is_active": True,
            "email_verified": True,
            "email_verified_at": datetime.now(timezone.utc),
        }
        return self.user_repo.create_user(user_data)

    def _assign_user_roles_from_invitation(self, user, invitation) -> None:
        """Assign primary, custom, or default roles to the user based on invitation."""
        from app.models.role import UserOrganizationRole

        # Assign primary role (if provided)
        primary_role_id = invitation.role_id
        if primary_role_id:
            user_org_role = UserOrganizationRole(
                user_id=user.id,
                organization_id=invitation.organization_id,
                role_id=primary_role_id,
                is_active=True,
                is_primary=True,
                status="active",
                joined_at=datetime.now(timezone.utc),
            )
            self.db.add(user_org_role)

        # Apply custom permissions
        custom_permission_ids = []
        if invitation.extra_data and "custom_permission_ids" in invitation.extra_data:
            custom_permission_ids = [
                UUID(pid)
                for pid in invitation.extra_data["custom_permission_ids"]
                if pid
            ]

        if custom_permission_ids:
            self._create_custom_role_with_permissions(
                user, invitation, custom_permission_ids, bool(primary_role_id)
            )

        # If no role at all, ensure user has at least one UserOrganizationRole
        if not primary_role_id and not custom_permission_ids:
            self._assign_default_role(user, invitation.organization_id)

    def _create_custom_role_with_permissions(
        self, user, invitation, custom_permission_ids, has_primary_role: bool
    ) -> None:
        """Create a custom role with specific permissions for the user."""
        from app.models.role import Role, RolePermission, UserOrganizationRole

        # Create a "Custom Permissions" role for this user
        custom_role = Role(
            organization_id=invitation.organization_id,
            name="Custom Permissions",
            code=f"custom_{user.id}",
            description="Custom permissions assigned via invitation",
            is_system=False,
            is_default=False,
            is_active=True,
        )
        self.db.add(custom_role)
        self.db.flush()  # Get custom_role.id

        # Assign permissions to the custom role
        for permission_id in custom_permission_ids:
            role_perm = RolePermission(
                role_id=custom_role.id,
                permission_id=permission_id,
            )
            self.db.add(role_perm)

        # Assign user to the custom role
        custom_user_org_role = UserOrganizationRole(
            user_id=user.id,
            organization_id=invitation.organization_id,
            role_id=custom_role.id,
            is_active=True,
            is_primary=not has_primary_role,  # Primary only if no other role
            status="active",
            joined_at=datetime.now(timezone.utc),
        )
        self.db.add(custom_user_org_role)

    def _assign_default_role(self, user, organization_id: UUID) -> None:
        """Assign the default organization role to the user."""
        from app.models.role import Role, UserOrganizationRole

        default_role = (
            self.db.query(Role)
            .filter(
                Role.organization_id == organization_id,
                Role.is_default == True,  # noqa: E712
                Role.is_active == True,  # noqa: E712
            )
            .first()
        )
        if default_role:
            user_org_role = UserOrganizationRole(
                user_id=user.id,
                organization_id=organization_id,
                role_id=default_role.id,
                is_active=True,
                is_primary=True,
                status="active",
                joined_at=datetime.now(timezone.utc),
            )
            self.db.add(user_org_role)

    def validate_invitation(self, token: str) -> dict:
        """
        Validate an invitation token without accepting it.

        Args:
            token: Invitation token

        Returns:
            Dictionary with invitation details

        Raises:
            InvitationNotFoundException: If token invalid
            InvitationExpiredException: If expired
        """
        token_hash = _hash_token(token)
        invitation = self.invitation_repo.get_invitation_by_token(token_hash)

        if not invitation:
            raise InvitationNotFoundException("Invalid invitation token")

        if invitation.status != "pending":
            if invitation.status == "accepted":
                raise InvitationAlreadyAcceptedException("Invitation already accepted")
            elif invitation.status == "cancelled":
                raise InvitationNotFoundException("Invitation has been cancelled")
            elif invitation.status == "expired":
                raise InvitationExpiredException("Invitation has expired")

        if invitation.expires_at < datetime.now(timezone.utc):
            self.invitation_repo.update_invitation(invitation, {"status": "expired"})
            raise InvitationExpiredException("Invitation has expired")

        # Get organization name
        from app.models.organization import Organization

        org = (
            self.db.query(Organization)
            .filter(Organization.id == invitation.organization_id)
            .first()
        )

        return {
            "email": invitation.email,
            "first_name": invitation.first_name,
            "last_name": invitation.last_name,
            "organization_id": invitation.organization_id,
            "organization_name": org.name if org else None,
            "expires_at": invitation.expires_at,
        }

    def _has_invite_permission(self, permissions: list[str]) -> bool:
        """Check if user has invite permission."""
        if is_system_admin(permissions):
            return True

        # Org owners with *.* should always be able to invite
        if "*.*" in permissions:
            return True

        # user.* wildcard covers all user actions including invite
        if "user.*" in permissions:
            return True

        return any(
            has_permission(permissions, perm)
            for perm in [
                "user.invite",
                "invitation.create",
                "user.manage",
                "invitation.*",
                "user.create",
            ]
        )

    def _invitation_to_dict(self, invitation) -> dict:
        """Convert invitation object to dictionary."""
        # Get role name
        role_name = None
        if invitation.role_id and invitation.role:
            role_name = invitation.role.name

        # Get inviter email
        inviter_email = None
        if invitation.invited_by:
            inviter_email = invitation.invited_by.email

        # Extract custom_permission_ids from extra_data
        custom_permission_ids = []
        if invitation.extra_data and "custom_permission_ids" in invitation.extra_data:
            try:
                custom_permission_ids = [
                    UUID(pid)
                    for pid in invitation.extra_data["custom_permission_ids"]
                    if pid
                ]
            except (ValueError, TypeError):
                pass

        return {
            "id": invitation.id,
            "organization_id": invitation.organization_id,
            "email": invitation.email,
            "first_name": invitation.first_name,
            "last_name": invitation.last_name,
            "role_id": invitation.role_id,
            "role_name": role_name,
            "custom_permission_ids": custom_permission_ids,
            "team_ids": invitation.team_ids,
            "invited_by_id": invitation.invited_by_id,
            "invited_by_email": inviter_email,
            "status": invitation.status,
            "expires_at": invitation.expires_at,
            "accepted_at": invitation.accepted_at,
            "message": invitation.message,
            "extra_data": invitation.extra_data,
            "created_at": invitation.created_at,
        }
