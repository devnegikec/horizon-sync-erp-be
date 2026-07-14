"""Service layer for Messaging module"""

import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.repositories.messaging_repository import (
    BulkMessageJobRepository,
    DeliveryReportRepository,
    MessageCreditRepository,
    MessageTemplateRepository,
)
from app.schemas.messaging import (
    BulkMessageJobCreate,
    MessageTemplateCreate,
    MessageTemplateUpdate,
    RCSSendRequest,
    RCSSendResponse,
    ScheduledMessageCreate,
    SMSWebhookPayload,
    WhatsAppSendRequest,
    WhatsAppSendResponse,
    WhatsAppWebhookPayload,
)

logger = logging.getLogger(__name__)


class MessagingService:
    def __init__(self, db: Session):
        self.db = db
        self.template_repo = MessageTemplateRepository(db)
        self.job_repo = BulkMessageJobRepository(db)
        self.report_repo = DeliveryReportRepository(db)
        self.credit_repo = MessageCreditRepository(db)

    # ── Message Templates ─────────────────────────────────────────────────────

    def create_template(
        self, data: MessageTemplateCreate, organization_id: UUID, user_id: UUID
    ):
        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["status"] = "Not Approved"
        return self.template_repo.create(payload)

    def list_templates(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        channel: str | None = None,
        search: str | None = None,
    ):
        items, total = self.template_repo.list(
            organization_id, page, page_size, channel, search
        )
        total_pages = (total + page_size - 1) // page_size
        return {
            "templates": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    def get_template(self, template_id: UUID, organization_id: UUID):
        tmpl = self.template_repo.get_by_id(template_id, organization_id)
        if not tmpl:
            return None
        return tmpl

    def update_template(
        self,
        template_id: UUID,
        data: MessageTemplateUpdate,
        organization_id: UUID,
        user_id: UUID,
    ):
        tmpl = self.template_repo.get_by_id(template_id, organization_id)
        if not tmpl:
            return None
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        payload["updated_by"] = user_id
        return self.template_repo.update(tmpl, payload)

    def delete_template(
        self, template_id: UUID, organization_id: UUID, user_id: UUID
    ) -> bool:
        tmpl = self.template_repo.get_by_id(template_id, organization_id)
        if not tmpl:
            return False
        self.template_repo.soft_delete(tmpl, user_id)
        return True

    # ── Bulk Message Jobs ─────────────────────────────────────────────────────

    def create_bulk_job(
        self, data: BulkMessageJobCreate, organization_id: UUID, user_id: UUID
    ):
        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["user_id"] = user_id
        payload["status"] = "queued"
        return self.job_repo.create(payload)

    def list_jobs(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        message_type: str | None = None,
    ):
        items, total = self.job_repo.list(organization_id, page, page_size, message_type)
        total_pages = (total + page_size - 1) // page_size
        return {
            "jobs": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    def get_job(self, job_id: UUID, organization_id: UUID):
        return self.job_repo.get_by_id(job_id, organization_id)

    # ── Scheduled Messages ────────────────────────────────────────────────────

    def create_scheduled_message(
        self, data: ScheduledMessageCreate, organization_id: UUID, user_id: UUID
    ):
        from app.models.messaging import ScheduledMessage

        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["user_id"] = user_id
        payload["status"] = "Pending"
        msg = ScheduledMessage(**payload)
        self.db.add(msg)
        self.db.commit()
        self.db.refresh(msg)
        return msg

    def list_scheduled(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ):
        from app.models.messaging import ScheduledMessage

        q = self.db.query(ScheduledMessage).filter(
            ScheduledMessage.organization_id == organization_id
        )
        total = q.count()
        items = (
            q.order_by(ScheduledMessage.schedule.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        total_pages = (total + page_size - 1) // page_size
        return {
            "scheduled": items,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    # ── WhatsApp ──────────────────────────────────────────────────────────────

    def send_whatsapp(
        self,
        data: WhatsAppSendRequest,
        organization_id: UUID,
        user_id: UUID,
    ) -> WhatsAppSendResponse:
        """Stub: log the request and create a report row. Real provider TBD."""
        guid = str(uuid.uuid4())
        logger.info(
            "[WHATSAPP STUB] org=%s to=%s template=%s guid=%s",
            organization_id,
            data.recipient_number,
            data.template_name,
            guid,
        )

        # Create a job record
        job = self.job_repo.create(
            {
                "organization_id": organization_id,
                "user_id": user_id,
                "message_type": "whatsapp",
                "template_name": data.template_name,
                "template_type": data.template_type,
                "media_type": data.media_type,
                "interactive_type": data.interactive_type,
                "variable": data.variable,
                "media_link": data.media_link,
                "status": "sent",
                "total_lead": "1",
            }
        )

        # Create delivery report row
        self.report_repo.create_whatsapp_report(
            {
                "organization_id": organization_id,
                "job_id": job.id,
                "recipient_number": data.recipient_number,
                "sender_number": data.sender_number,
                "template_id": data.template_name,
                "guid": guid,
                "status": "sent",
                "sent_date": datetime.now(UTC),
            }
        )

        return WhatsAppSendResponse(
            success=True,
            message_id=guid,
            status="sent",
            message="WhatsApp message queued (stub)",
        )

    def handle_whatsapp_webhook(self, payload: WhatsAppWebhookPayload) -> dict:
        if not payload.guid:
            return {"updated": False, "reason": "no guid"}
        update_data: dict = {}
        if payload.status:
            update_data["status"] = payload.status
        if payload.reason_code:
            update_data["reason_code"] = payload.reason_code
        if payload.deliver_date:
            update_data["deliver_date"] = payload.deliver_date
        if payload.whatsapp_msg_id:
            update_data["whatsapp_msg_id"] = payload.whatsapp_msg_id
        report = self.report_repo.update_whatsapp_by_guid(payload.guid, update_data)
        return {"updated": report is not None}

    # ── SMS ───────────────────────────────────────────────────────────────────

    def handle_sms_webhook(self, payload: SMSWebhookPayload) -> dict:
        if not payload.msg_id:
            return {"updated": False, "reason": "no msg_id"}
        from app.models.messaging import SMSReport

        report = (
            self.db.query(SMSReport)
            .filter(SMSReport.msg_id == payload.msg_id)
            .first()
        )
        if report:
            if payload.status:
                report.status = payload.status
            if payload.deliver_date:
                report.deliver_date = payload.deliver_date
            self.db.commit()
        return {"updated": report is not None}

    # ── RCS ───────────────────────────────────────────────────────────────────

    def send_rcs(
        self,
        data: RCSSendRequest,
        organization_id: UUID,
        user_id: UUID,
    ) -> RCSSendResponse:
        """Stub: log and create report row."""
        guid = str(uuid.uuid4())
        logger.info(
            "[RCS STUB] org=%s to=%s template=%s guid=%s",
            organization_id,
            data.recipient_number,
            data.template_id,
            guid,
        )

        job = self.job_repo.create(
            {
                "organization_id": organization_id,
                "user_id": user_id,
                "message_type": "rcs",
                "status": "sent",
                "total_lead": "1",
            }
        )

        self.report_repo.create_rcs_report(
            {
                "organization_id": organization_id,
                "job_id": job.id,
                "recipient_number": data.recipient_number,
                "guid": guid,
                "status": "sent",
                "sent_date": datetime.now(UTC),
            }
        )

        return RCSSendResponse(
            success=True,
            guid=guid,
            status="sent",
            message="RCS message queued (stub)",
        )

    # ── Credits ───────────────────────────────────────────────────────────────

    def get_credit_summary(self, organization_id: UUID):
        return self.credit_repo.get_summary(organization_id)

    def get_credit_balance(self, organization_id: UUID, credit_type: str) -> int:
        return self.credit_repo.get_balance(organization_id, credit_type)
