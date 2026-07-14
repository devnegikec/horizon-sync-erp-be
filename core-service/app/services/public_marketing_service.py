"""Service layer for public/marketing form submissions"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.public_submission_repository import PublicSubmissionRepository
from app.schemas.public_marketing import (
    ContactUsRequest,
    CareerApplicationRequest,
    ScheduleDemoRequest,
    NewsletterSubscribeRequest,
    RequestCallbackRequest,
)
from app.models.public_submission import PublicSubmission

logger = logging.getLogger(__name__)

NOTIFY_EMAIL = "admin@example.com"  # Override via env / config


class PublicMarketingService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = PublicSubmissionRepository(db)

    # ── helpers ──────────────────────────────────────────────────────────────

    def _log_notification(self, submission_type: str, record: PublicSubmission) -> None:
        """Log notification details (replace with real email when SMTP is configured)."""
        logger.info(
            "[PUBLIC_MARKETING] New %s submission | id=%s | name=%s | email=%s",
            submission_type,
            record.id,
            record.name,
            record.email,
        )

    # ── handlers ─────────────────────────────────────────────────────────────

    async def contact_us(
        self, data: ContactUsRequest, ip_address: str | None
    ) -> PublicSubmission:
        record = await self.repo.create(
            submission_type="contact_us",
            name=data.name,
            email=str(data.email),
            mobile=data.mobile,
            company=data.company,
            message=data.message,
            payload=None,
            ip_address=ip_address,
        )
        await self.db.commit()
        self._log_notification("contact_us", record)
        return record

    async def career_application(
        self, data: CareerApplicationRequest, ip_address: str | None
    ) -> PublicSubmission:
        payload = {
            "position": data.position,
            "cover_letter": data.cover_letter,
            "resume_url": data.resume_url,
        }
        record = await self.repo.create(
            submission_type="career",
            name=data.name,
            email=str(data.email),
            mobile=data.mobile,
            company=None,
            message=data.cover_letter,
            payload=payload,
            ip_address=ip_address,
        )
        await self.db.commit()
        self._log_notification("career", record)
        return record

    async def schedule_demo(
        self, data: ScheduleDemoRequest, ip_address: str | None
    ) -> PublicSubmission:
        payload = {
            "preferred_date": data.preferred_date,
            "notes": data.notes,
        }
        record = await self.repo.create(
            submission_type="schedule_demo",
            name=data.name,
            email=str(data.email),
            mobile=data.mobile,
            company=data.company,
            message=data.notes,
            payload=payload,
            ip_address=ip_address,
        )
        await self.db.commit()
        self._log_notification("schedule_demo", record)
        return record

    async def newsletter_subscribe(
        self, data: NewsletterSubscribeRequest, ip_address: str | None
    ) -> PublicSubmission:
        record = await self.repo.create(
            submission_type="newsletter",
            name=data.name,
            email=str(data.email),
            mobile=None,
            company=None,
            message=None,
            payload=None,
            ip_address=ip_address,
        )
        await self.db.commit()
        self._log_notification("newsletter", record)
        return record

    async def request_callback(
        self, data: RequestCallbackRequest, ip_address: str | None
    ) -> PublicSubmission:
        payload = {
            "preferred_time": data.preferred_time,
            "notes": data.notes,
        }
        record = await self.repo.create(
            submission_type="request_callback",
            name=data.name,
            email=str(data.email) if data.email else None,
            mobile=data.mobile,
            company=None,
            message=data.notes,
            payload=payload,
            ip_address=ip_address,
        )
        await self.db.commit()
        self._log_notification("request_callback", record)
        return record
