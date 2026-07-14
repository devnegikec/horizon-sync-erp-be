"""Repository for public_submissions table"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.public_submission import PublicSubmission


class PublicSubmissionRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        submission_type: str,
        name: str | None,
        email: str | None,
        mobile: str | None,
        company: str | None,
        message: str | None,
        payload: dict | None,
        ip_address: str | None,
    ) -> PublicSubmission:
        record = PublicSubmission(
            submission_type=submission_type,
            name=name,
            email=email,
            mobile=mobile,
            company=company,
            message=message,
            payload=payload,
            ip_address=ip_address,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record
