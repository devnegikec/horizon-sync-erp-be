"""Invitation repository for database operations"""

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.invitation import Invitation

logger = logging.getLogger(__name__)


class InvitationRepository:
    """Repository for invitation database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_invitation(self, invitation_data: dict) -> Invitation:
        """
        Create a new invitation.

        Args:
            invitation_data: Dictionary containing invitation data

        Returns:
            Created Invitation object
        """
        logger.debug(f"Creating invitation for email: {invitation_data.get('email')}")
        try:
            invitation = Invitation(**invitation_data)
            self.db.add(invitation)
            self.db.flush()  # Flush to ensure ID is generated and constraints checked
            self.db.commit()
            self.db.refresh(invitation)
            logger.info(f"Invitation created successfully: {invitation.id}")
            return invitation
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating invitation: {str(e)}")
            raise

    def get_invitation_by_id(self, invitation_id: UUID) -> Invitation | None:
        """
        Get invitation by ID.

        Args:
            invitation_id: Invitation UUID

        Returns:
            Invitation object or None if not found
        """
        logger.debug(f"Fetching invitation: {invitation_id}")
        return self.db.query(Invitation).filter(Invitation.id == invitation_id).first()

    def get_invitation_by_token(self, token_hash: str) -> Invitation | None:
        """
        Get invitation by token hash.

        Args:
            token_hash: Hashed invitation token

        Returns:
            Invitation object or None if not found
        """
        logger.debug("Fetching invitation by token")
        return (
            self.db.query(Invitation)
            .filter(Invitation.token_hash == token_hash)
            .first()
        )

    def get_invitation_by_email_and_org(
        self, email: str, organization_id: UUID
    ) -> Invitation | None:
        """
        Get pending invitation by email and organization.

        Args:
            email: Email address
            organization_id: Organization UUID

        Returns:
            Invitation object or None if not found
        """
        logger.debug(f"Fetching invitation for email {email} in org {organization_id}")
        return (
            self.db.query(Invitation)
            .filter(
                Invitation.email == email,
                Invitation.organization_id == organization_id,
                Invitation.status == "pending",
            )
            .first()
        )

    def update_invitation(
        self, invitation: Invitation, update_data: dict
    ) -> Invitation:
        """
        Update invitation fields.

        Args:
            invitation: Invitation object to update
            update_data: Dictionary of fields to update

        Returns:
            Updated Invitation object
        """
        logger.debug(f"Updating invitation: {invitation.id}")
        for key, value in update_data.items():
            if hasattr(invitation, key) and value is not None:
                setattr(invitation, key, value)

        self.db.commit()
        self.db.refresh(invitation)
        logger.info(f"Invitation updated successfully: {invitation.id}")
        return invitation

    def delete_invitation(self, invitation: Invitation) -> None:
        """
        Delete an invitation.

        Args:
            invitation: Invitation object to delete
        """
        logger.debug(f"Deleting invitation: {invitation.id}")
        self.db.delete(invitation)
        self.db.commit()
        logger.info(f"Invitation deleted successfully: {invitation.id}")

    def list_invitations(
        self,
        organization_id: UUID | None = None,
        skip: int = 0,
        limit: int = 10,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Invitation], int]:
        """
        List invitations with pagination and filters.

        Args:
            organization_id: Filter by organization
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status
            search: Search term for email

        Returns:
            Tuple of (list of invitations, total count)
        """
        logger.debug(
            f"Listing invitations - org_id: {organization_id}, "
            f"skip: {skip}, limit: {limit}, status: {status}"
        )

        query = self.db.query(Invitation)

        if organization_id:
            query = query.filter(Invitation.organization_id == organization_id)

        if status:
            query = query.filter(Invitation.status == status)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                or_(
                    Invitation.email.ilike(search_term),
                    Invitation.first_name.ilike(search_term),
                    Invitation.last_name.ilike(search_term),
                )
            )

        total_count = query.count()

        invitations = (
            query.order_by(Invitation.created_at.desc()).offset(skip).limit(limit).all()
        )

        logger.debug(f"Found {len(invitations)} invitations out of {total_count} total")

        return invitations, total_count

    def count_pending_invitations_for_email(
        self, email: str, organization_id: UUID
    ) -> int:
        """
        Count pending invitations for an email in an organization.

        Args:
            email: Email address
            organization_id: Organization UUID

        Returns:
            Count of pending invitations
        """
        return (
            self.db.query(Invitation)
            .filter(
                Invitation.email == email,
                Invitation.organization_id == organization_id,
                Invitation.status == "pending",
            )
            .count()
        )

    def expire_old_invitations(self) -> int:
        """
        Mark expired invitations as expired.

        Returns:
            Number of invitations expired
        """
        now = datetime.utcnow()
        result = (
            self.db.query(Invitation)
            .filter(
                Invitation.status == "pending",
                Invitation.expires_at < now,
            )
            .update({"status": "expired"})
        )
        self.db.commit()
        logger.info(f"Expired {result} invitations")
        return result
