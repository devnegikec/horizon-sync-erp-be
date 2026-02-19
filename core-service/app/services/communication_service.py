"""Communication service"""

import base64
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
from app.services.email_service import EmailService


class CommunicationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = CommunicationRepository(db)
        self.email_service = EmailService()

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
            "extra_data": comm.extra_data,
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

    async def send_email(
        self,
        to: str,
        subject: str,
        message: str,
        organization_id: UUID,
        user_id: UUID,
        cc: list[str] | None = None,
        html_message: str | None = None,
        attachments: list[dict] | None = None,
        doc_type: str | None = None,
        doc_id: str | None = None,
        doc_no: str | None = None,
    ) -> dict:
        """
        Send an email and log the communication.

        Args:
            to: Recipient email address
            subject: Email subject
            message: Email body (plain text)
            organization_id: Organization ID
            user_id: User ID sending the email
            cc: List of CC email addresses
            html_message: Optional HTML version of email
            attachments: List of attachment dicts with filename, content (base64), content_type
            doc_type: Optional document type for logging
            doc_id: Optional document ID for logging
            doc_no: Optional document number for logging

        Returns:
            dict with status, message, and communication_id
        """
        # Process attachments - decode base64 content
        processed_attachments = []
        if attachments:
            for att in attachments:
                try:
                    content = att.get("content", "")
                    # If content is string (base64), decode it
                    if isinstance(content, str):
                        content = base64.b64decode(content)

                    processed_attachments.append(
                        {
                            "filename": att.get("filename", "attachment"),
                            "content": content,
                            "content_type": att.get("content_type"),
                        }
                    )
                except Exception as e:
                    raise ValueError(f"Invalid attachment: {str(e)}")

        # Send email
        try:
            result = await self.email_service.send_email(
                subject=subject,
                recipient=to,
                body=message,
                cc=cc,
                attachments=processed_attachments if processed_attachments else None,
                html_body=html_message,
            )

            # Create communication log
            log_data = {
                "organization_id": organization_id,
                "channel": CommunicationChannel.EMAIL,
                "recipient": to,
                "sender_id": user_id,
                "subject": subject,
                "message": message,
                "status": CommunicationStatus.SENT
                if result["status"] == "sent"
                else CommunicationStatus.PENDING,
                "extra_data": {
                    "cc": cc,
                    "has_attachments": len(processed_attachments) > 0
                    if processed_attachments
                    else False,
                    "attachment_count": len(processed_attachments)
                    if processed_attachments
                    else 0,
                    "attachment_names": [a["filename"] for a in processed_attachments]
                    if processed_attachments
                    else [],
                },
            }

            # Add document info if provided
            if doc_type and doc_id:
                log_data["doc_type"] = CommunicationDocType(doc_type)
                log_data["doc_id"] = UUID(doc_id)
                log_data["doc_no"] = doc_no
                log_data["version"] = 1

            # Set sent_at if sent successfully
            if result["status"] == "sent":
                log_data["sent_at"] = datetime.now(UTC)

            comm = self.repo.create(log_data)

            return {
                "status": result["status"],
                "message": result["message"],
                "communication_id": str(comm.id),
            }

        except Exception as e:
            # Log failed attempt
            log_data = {
                "organization_id": organization_id,
                "channel": CommunicationChannel.EMAIL,
                "recipient": to,
                "sender_id": user_id,
                "subject": subject,
                "message": message,
                "status": CommunicationStatus.FAILED,
                "failed_at": datetime.now(UTC),
                "error_message": str(e),
                "extra_data": {
                    "cc": cc,
                    "has_attachments": len(processed_attachments) > 0
                    if processed_attachments
                    else False,
                },
            }

            if doc_type and doc_id:
                log_data["doc_type"] = CommunicationDocType(doc_type)
                log_data["doc_id"] = UUID(doc_id)
                log_data["doc_no"] = doc_no
                log_data["version"] = 1

            comm = self.repo.create(log_data)

            return {
                "status": "failed",
                "message": f"Failed to send email: {str(e)}",
                "communication_id": str(comm.id),
            }
