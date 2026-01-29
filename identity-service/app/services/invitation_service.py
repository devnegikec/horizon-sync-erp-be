"""Invitation service with business logic"""

import hashlib
import logging
import secrets
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    InvitationAlreadyAcceptedException,
    InvitationExpiredException,
    InvitationNotFoundException,
    PermissionDeniedException,
    UserAlreadyExistsException,
)
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
        if not self._has_invite_permission(inviter_permissions):
            logger.warning(f"User {inviter_id} lacks invite permission")
            raise PermissionDeniedException("You don't have permission to invite users")

        email = invitation_data.get("email")
        organization_id = invitation_data.get("organization_id")

        # Check if user already exists and is in the organization
        existing_user = self.user_repo.get_user_by_email(email)
        if existing_user:
            # Check if user is already in this organization
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

        # Check for existing pending invitation
        existing_invitation = self.invitation_repo.get_invitation_by_email_and_org(
            email, organization_id
        )
        if existing_invitation:
            # Cancel the old invitation and create a new one
            self.invitation_repo.update_invitation(
                existing_invitation, {"status": "cancelled"}
            )

        # Generate token
        token, token_hash = _generate_invitation_token()

        # Set expiration
        expires_at = datetime.utcnow() + timedelta(days=INVITATION_EXPIRY_DAYS)

        # Create invitation
        from uuid import uuid4
        
        # Convert team_ids UUIDs to strings for JSONB storage
        if "team_ids" in invitation_data and invitation_data["team_ids"]:
            invitation_data["team_ids"] = [
                str(team_id) for team_id in invitation_data["team_ids"]
            ]
        
        invitation_data["id"] = uuid4()  # Explicitly generate UUID to avoid blank ID
        invitation_data["token_hash"] = token_hash
        invitation_data["invited_by_id"] = inviter_id
        invitation_data["expires_at"] = expires_at
        invitation_data["status"] = "pending"

        invitation = self.invitation_repo.create_invitation(invitation_data)
        logger.info(f"Invitation created: {invitation.id}")

        # Get role name if role_id is provided
        role_name = None
        if invitation.role_id:
            role = self.role_repo.get_role_by_id(invitation.role_id)
            if role:
                role_name = role.name

        # Get inviter info
        inviter = self.user_repo.get_user_by_id(inviter_id)
        inviter_email = inviter.email if inviter else None

        return {
            "id": invitation.id,
            "organization_id": invitation.organization_id,
            "email": invitation.email,
            "first_name": invitation.first_name,
            "last_name": invitation.last_name,
            "role_id": invitation.role_id,
            "role_name": role_name,
            "team_ids": invitation.team_ids,
            "invited_by_id": invitation.invited_by_id,
            "invited_by_email": inviter_email,
            "status": invitation.status,
            "expires_at": invitation.expires_at,
            "accepted_at": invitation.accepted_at,
            "message": invitation.message,
            "extra_data": invitation.extra_data,
            "created_at": invitation.created_at,
            "token": token,  # Include token for sending in email
        }

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
        expires_at = datetime.utcnow() + timedelta(days=INVITATION_EXPIRY_DAYS)

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

        token_hash = _hash_token(token)
        invitation = self.invitation_repo.get_invitation_by_token(token_hash)

        if not invitation:
            raise InvitationNotFoundException("Invalid invitation token")

        if invitation.status == "accepted":
            raise InvitationAlreadyAcceptedException("Invitation already accepted")

        if invitation.status == "cancelled":
            raise InvitationNotFoundException("Invitation has been cancelled")

        if invitation.status == "expired" or invitation.expires_at < datetime.utcnow():
            self.invitation_repo.update_invitation(invitation, {"status": "expired"})
            raise InvitationExpiredException("Invitation has expired")

        # Check if user already exists
        existing_user = self.user_repo.get_user_by_email(invitation.email)

        if existing_user:
            # Add user to organization with the specified role
            user = existing_user
        else:
            # Create new user
            from app.core.security import hash_password

            user_data = {
                "email": invitation.email,
                "password_hash": hash_password(password),
                "first_name": first_name or invitation.first_name or "",
                "last_name": last_name or invitation.last_name or "",
                "is_active": True,
                "email_verified": True,
                "email_verified_at": datetime.utcnow(),
            }
            user = self.user_repo.create_user(user_data)

        # Add user to organization with role
        from app.models.role import UserOrganizationRole

        user_org_role = UserOrganizationRole(
            user_id=user.id,
            organization_id=invitation.organization_id,
            role_id=invitation.role_id,
            is_active=True,
            is_primary=True,
            status="active",
            joined_at=datetime.utcnow(),
        )
        self.db.add(user_org_role)

        # Update invitation status
        self.invitation_repo.update_invitation(
            invitation,
            {
                "status": "accepted",
                "accepted_at": datetime.utcnow(),
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

        if invitation.expires_at < datetime.utcnow():
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
        invite_permissions = [
            "user.invite",
            "invitation.create",
            "user.manage",
            "all.manage",
        ]
        return any(p in permissions for p in invite_permissions)

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

        return {
            "id": invitation.id,
            "organization_id": invitation.organization_id,
            "email": invitation.email,
            "first_name": invitation.first_name,
            "last_name": invitation.last_name,
            "role_id": invitation.role_id,
            "role_name": role_name,
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
