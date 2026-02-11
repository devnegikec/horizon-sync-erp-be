"""Bulk Import Job repository for database operations"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.bulk_import_job import BulkImportJob, BulkImportJobStatus


class BulkImportRepository:
    """Repository for bulk import job database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        organization_id: UUID,
        created_by_id: UUID,
        file_name: str,
        mime_type: str,
    ) -> BulkImportJob:
        """
        Create a new bulk import job.

        Args:
            organization_id: Organization UUID
            created_by_id: User UUID who created the job
            file_name: Name of the uploaded file
            mime_type: MIME type of the file

        Returns:
            Created BulkImportJob object
        """
        job = BulkImportJob(
            organization_id=organization_id,
            created_by_id=created_by_id,
            file_name=file_name,
            mime_type=mime_type,
            status=BulkImportJobStatus.PENDING,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job_by_id(self, job_id: UUID) -> BulkImportJob | None:
        """
        Get bulk import job by ID.

        Args:
            job_id: Job UUID

        Returns:
            BulkImportJob object or None if not found
        """
        return self.db.query(BulkImportJob).filter(BulkImportJob.id == job_id).first()

    def get_jobs_by_organization(
        self, organization_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[BulkImportJob], int]:
        """
        Get bulk import jobs for an organization with pagination.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of jobs, total count)
        """
        query = self.db.query(BulkImportJob).filter(
            BulkImportJob.organization_id == organization_id
        )

        total_count = query.count()

        offset = (page - 1) * page_size
        jobs = (
            query.order_by(desc(BulkImportJob.created_at))
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return jobs, total_count

    def update_job_status(
        self, job_id: UUID, status: str, summary: str | None = None
    ) -> BulkImportJob | None:
        """
        Update job status and optionally summary.

        Args:
            job_id: Job UUID
            status: New status
            summary: Optional summary message

        Returns:
            Updated BulkImportJob or None if not found
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return None

        job.status = status
        if summary:
            job.summary = summary

        if status == BulkImportJobStatus.COMPLETED:
            job.completed_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(job)
        return job

    def update_job_statistics(
        self,
        job_id: UUID,
        total_rows: int,
        successful_rows: int,
        failed_rows: int,
        error_details: dict | None = None,
    ) -> BulkImportJob | None:
        """
        Update job statistics and error details.

        Args:
            job_id: Job UUID
            total_rows: Total rows processed
            successful_rows: Number of successful rows
            failed_rows: Number of failed rows
            error_details: Dictionary containing error information

        Returns:
            Updated BulkImportJob or None if not found
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return None

        job.total_rows = total_rows
        job.successful_rows = successful_rows
        job.failed_rows = failed_rows
        if error_details:
            job.error_details = error_details

        self.db.commit()
        self.db.refresh(job)
        return job

    def update_job_file_path(self, job_id: UUID, file_path: str) -> BulkImportJob | None:
        """
        Update job file path.

        Args:
            job_id: Job UUID
            file_path: Path to the uploaded file

        Returns:
            Updated BulkImportJob or None if not found
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return None

        job.file_path = file_path
        self.db.commit()
        self.db.refresh(job)
        return job
