"""Communication service"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import (
    CommunicationChannel,
    CommunicationDocType,
    CommunicationStatus,
    RecipientType,
)
from app.repositories.communication_repository import CommunicationRepository


class CommunicationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CommunicationRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        """
        Create a communication log entry.

        Args:
            data: Communication data
            organization_id: Organization ID
            user_id: User ID who initiated the communication

        Returns:
            Created communication as dict
        """
        payload = dict(data)
        payload["organization_id"] = organization_id
        payload["sender_id"] = user_id

        # Convert string enums to enum types
        if payload.get("doc_type"):
            payload["doc_type"] = CommunicationDocType(payload["doc_type"])
        if payload.get("channel"):
            payload["channel"] = CommunicationChannel(payload["channel"])
        if payload.get("recipient_type"):
            payload["recipient_type"] = RecipientType(payload["recipient_type"])
        if payload.get("status"):
            payload["status"] = CommunicationStatus(payload["status"])

        # Set sent_at if status is sent
        if payload.get("status") == CommunicationStatus.SENT:
            payload["sent_at"] = datetime.now(UTC)

        comm = self.repo.create(payload)
        return self._to_response(comm)

    def get_by_id(self, communication_id: UUID, organization_id: UUID) -> dict:
        """Get communication by ID."""
        comm = self.repo.get_by_id(communication_id, organization_id)
        if not comm:
            raise ResourceNotFoundException(
                f"Communication {communication_id} not found"
            )
        return self._to_response(comm)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        doc_type: str | None = None,
        doc_id: UUID | None = None,
        channel: str | None = None,
        status: str | None = None,
        recipient_type: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        """List communications with filters."""
        items, total = self.repo.list_communications(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            doc_type=doc_type,
            doc_id=doc_id,
            channel=channel,
            status=status,
            recipient_type=recipient_type,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return [self._to_list_item(x) for x in items], pagination

    def update_status(
        self,
        communication_id: UUID,
        status: str,
        organization_id: UUID,
        error_message: str | None = None,
    ) -> dict:
        """
        Update communication status.

        Args:
            communication_id: Communication ID
            status: New status
            organization_id: Organization ID
            error_message: Error message if status is failed

        Returns:
            Updated communication as dict
        """
        comm = self.repo.get_by_id(communication_id, organization_id)
        if not comm:
            raise ResourceNotFoundException(
                f"Communication {communication_id} not found"
            )

        status_enum = CommunicationStatus(status)
        payload = {"status": status_enum}

        # Set timestamps based on status
        if status_enum == CommunicationStatus.SENT and comm.sent_at is None:
            payload["sent_at"] = datetime.now(UTC)
        elif status_enum == CommunicationStatus.DELIVERED:
            payload["delivered_at"] = datetime.now(UTC)
        elif status_enum == CommunicationStatus.FAILED:
            payload["failed_at"] = datetime.now(UTC)
            if error_message:
                payload["error_message"] = error_message

        self.repo.update(comm, payload)
        return self._to_response(comm)

    def delete(self, communication_id: UUID, organization_id: UUID) -> None:
        """Delete communication log."""
        comm = self.repo.get_by_id(communication_id, organization_id)
        if not comm:
            raise ResourceNotFoundException(
                f"Communication {communication_id} not found"
            )
        self.repo.delete(comm)

    @staticmethod
    def _to_response(comm) -> dict:
        """Convert communication model to response dict."""
        return {
            "id": comm.id,
            "organization_id": comm.organization_id,
            "doc_type": comm.doc_type.value if comm.doc_type else None,
            "doc_id": comm.doc_id,
            "doc_no": comm.doc_no,
            "version": comm.version,
            "channel": comm.channel.value if comm.channel else None,
            "recipient_type": (
                comm.recipient_type.value if comm.recipient_type else None
            ),
            "recipient": comm.recipient,
            "recipient_name": comm.recipient_name,
            "sender_id": comm.sender_id,
            "sender_name": comm.sender_name,
            "sender_email": comm.sender_email,
            "subject": comm.subject,
            "message": comm.message,
            "status": comm.status.value if comm.status else None,
            "sent_at": comm.sent_at,
            "delivered_at": comm.delivered_at,
            "failed_at": comm.failed_at,
            "error_message": comm.error_message,
            "metadata": comm.metadata,
            "created_at": comm.created_at,
            "updated_at": comm.updated_at,
        }

    @staticmethod
    def _to_list_item(comm) -> dict:
        """Convert communication model to list item dict."""
        return {
            "id": comm.id,
            "organization_id": comm.organization_id,
            "doc_type": comm.doc_type.value if comm.doc_type else None,
            "doc_id": comm.doc_id,
            "doc_no": comm.doc_no,
            "version": comm.version,
            "channel": comm.channel.value if comm.channel else None,
            "recipient_type": (
                comm.recipient_type.value if comm.recipient_type else None
            ),
            "recipient": comm.recipient,
            "recipient_name": comm.recipient_name,
            "status": comm.status.value if comm.status else None,
            "sent_at": comm.sent_at,
            "created_at": comm.created_at,
        }
