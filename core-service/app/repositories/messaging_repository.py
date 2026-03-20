"""Repository for Messaging module"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.messaging import (
    BulkMessageJob,
    MessageCredit,
    MessageTemplate,
    RCSReport,
    RCSTemplate,
    ScheduledMessage,
    SMSReport,
    WhatsAppReport,
)


class MessageTemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> MessageTemplate:
        tmpl = MessageTemplate(**data)
        self.db.add(tmpl)
        self.db.commit()
        self.db.refresh(tmpl)
        return tmpl

    def get_by_id(self, tmpl_id: UUID, organization_id: UUID) -> MessageTemplate | None:
        return (
            self.db.query(MessageTemplate)
            .filter(
                MessageTemplate.id == tmpl_id,
                MessageTemplate.organization_id == organization_id,
                MessageTemplate.deleted_at.is_(None),
            )
            .first()
        )

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        channel: str | None = None,
        search: str | None = None,
    ) -> tuple[list[MessageTemplate], int]:
        q = self.db.query(MessageTemplate).filter(
            MessageTemplate.organization_id == organization_id,
            MessageTemplate.deleted_at.is_(None),
        )
        if channel:
            q = q.filter(MessageTemplate.channel == channel)
        if search:
            q = q.filter(MessageTemplate.template_name.ilike(f"%{search}%"))
        total = q.count()
        items = (
            q.order_by(MessageTemplate.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update(self, tmpl: MessageTemplate, data: dict) -> MessageTemplate:
        for k, v in data.items():
            setattr(tmpl, k, v)
        self.db.commit()
        self.db.refresh(tmpl)
        return tmpl

    def soft_delete(self, tmpl: MessageTemplate, user_id: UUID) -> None:
        tmpl.deleted_at = datetime.now(UTC)
        tmpl.updated_by = user_id
        self.db.commit()


class BulkMessageJobRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> BulkMessageJob:
        job = BulkMessageJob(**data)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_by_id(self, job_id: UUID, organization_id: UUID) -> BulkMessageJob | None:
        return (
            self.db.query(BulkMessageJob)
            .filter(
                BulkMessageJob.id == job_id,
                BulkMessageJob.organization_id == organization_id,
            )
            .first()
        )

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        message_type: str | None = None,
    ) -> tuple[list[BulkMessageJob], int]:
        q = self.db.query(BulkMessageJob).filter(
            BulkMessageJob.organization_id == organization_id,
        )
        if message_type:
            q = q.filter(BulkMessageJob.message_type == message_type)
        total = q.count()
        items = (
            q.order_by(BulkMessageJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update_status(self, job_id: UUID, status: str) -> None:
        self.db.query(BulkMessageJob).filter(
            BulkMessageJob.id == job_id
        ).update({"status": status})
        self.db.commit()


class DeliveryReportRepository:
    """Handles SMS, WhatsApp, and RCS delivery reports"""

    def __init__(self, db: Session):
        self.db = db

    def create_sms_report(self, data: dict) -> SMSReport:
        report = SMSReport(**data)
        self.db.add(report)
        self.db.commit()
        return report

    def update_whatsapp_by_guid(self, guid: str, data: dict) -> WhatsAppReport | None:
        report = (
            self.db.query(WhatsAppReport)
            .filter(WhatsAppReport.guid == guid)
            .first()
        )
        if report:
            for k, v in data.items():
                setattr(report, k, v)
            self.db.commit()
        return report

    def create_whatsapp_report(self, data: dict) -> WhatsAppReport:
        report = WhatsAppReport(**data)
        self.db.add(report)
        self.db.commit()
        return report

    def update_rcs_by_guid(self, guid: str, data: dict) -> RCSReport | None:
        report = (
            self.db.query(RCSReport)
            .filter(RCSReport.guid == guid)
            .first()
        )
        if report:
            for k, v in data.items():
                setattr(report, k, v)
            self.db.commit()
        return report

    def create_rcs_report(self, data: dict) -> RCSReport:
        report = RCSReport(**data)
        self.db.add(report)
        self.db.commit()
        return report


class MessageCreditRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_balance(self, organization_id: UUID,
                    credit_type: str) -> int:
        """Get latest balance for a credit type"""
        result = (
            self.db.query(MessageCredit.balance_credit)
            .filter(
                MessageCredit.organization_id == organization_id,
                MessageCredit.credit_type == credit_type,
            )
            .order_by(MessageCredit.transaction_date.desc())
            .first()
        )
        return result[0] if result else 0

    def add_transaction(self, data: dict) -> MessageCredit:
        credit = MessageCredit(**data)
        self.db.add(credit)
        self.db.commit()
        self.db.refresh(credit)
        return credit

    def get_summary(self, organization_id: UUID) -> list[dict]:
        """Latest balance per credit_type"""
        rows = (
            self.db.query(
                MessageCredit.credit_type,
                func.max(MessageCredit.transaction_date).label("latest"),
            )
            .filter(MessageCredit.organization_id == organization_id)
            .group_by(MessageCredit.credit_type)
            .all()
        )
        result = []
        for row in rows:
            balance = self.get_balance(organization_id, row.credit_type)
            result.append({"credit_type": row.credit_type, "balance_credit": balance})
        return result
