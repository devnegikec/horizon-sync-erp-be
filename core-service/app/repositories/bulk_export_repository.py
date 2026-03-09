"""Bulk Export Job repository for database operations"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.bulk_export_job import BulkExportJob, BulkExportJobStatus


class BulkExportRepository:
    """Repository for bulk export job database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_job(
        self,
        organization_id: UUID,
        created_by_id: UUID,
        file_name: str,
        file_format: str,
        filters: dict | None = None,
        selected_columns: list | None = None,
    ) -> BulkExportJob:
        """
        Create a new bulk export job.

        Args:
            organization_id: Organization UUID
            created_by_id: User UUID who created the job
            file_name: Name of the file to export
            file_format: Format of the export (csv, xlsx, json)
            filters: Optional filters dictionary
            selected_columns: Optional list of columns to include

        Returns:
            Created BulkExportJob object
        """
        job = BulkExportJob(
            organization_id=organization_id,
            created_by_id=created_by_id,
            file_name=file_name,
            file_format=file_format,
            filters=filters,
            selected_columns=selected_columns,
            status=BulkExportJobStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def get_job_by_id(self, job_id: UUID) -> BulkExportJob | None:
        """
        Get bulk export job by ID.

        Args:
            job_id: Job UUID

        Returns:
            BulkExportJob object or None if not found
        """
        return self.db.query(BulkExportJob).filter(BulkExportJob.id == job_id).first()

    def get_jobs_by_organization(
        self, organization_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[BulkExportJob], int]:
        """
        Get bulk export jobs for an organization with pagination.

        Args:
            organization_id: Organization UUID
            page: Page number (1-indexed)
            page_size: Number of items per page

        Returns:
            Tuple of (list of jobs, total count)
        """
        query = self.db.query(BulkExportJob).filter(
            BulkExportJob.organization_id == organization_id
        )

        total_count = query.count()

        offset = (page - 1) * page_size
        jobs = (
            query.order_by(desc(BulkExportJob.created_at))
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return jobs, total_count

    def update_job_status(
        self, job_id: UUID, status: str, error_message: str | None = None
    ) -> BulkExportJob | None:
        """
        Update job status.

        Args:
            job_id: Job UUID
            status: New status
            error_message: Optional error message

        Returns:
            Updated BulkExportJob or None if not found
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return None

        job.status = status
        if error_message:
            job.error_message = error_message

        if status == BulkExportJobStatus.COMPLETED:
            job.completed_at = datetime.now(UTC)

        self.db.commit()
        self.db.refresh(job)
        return job

    def update_job_file_path(
        self, job_id: UUID, file_path: str, total_rows: int = 0
    ) -> BulkExportJob | None:
        """
        Update job file path and row count.

        Args:
            job_id: Job UUID
            file_path: Path to the generated file
            total_rows: Number of rows exported

        Returns:
            Updated BulkExportJob or None if not found
        """
        job = self.get_job_by_id(job_id)
        if not job:
            return None

        job.file_path = file_path
        job.total_rows = str(total_rows)
        self.db.commit()
        self.db.refresh(job)
        return job

    def cleanup_expired_exports(self) -> int:
        """
        Delete expired export jobs.

        Returns:
            Number of deleted jobs
        """
        now = datetime.now(UTC)
        deleted = (
            self.db.query(BulkExportJob)
            .filter(BulkExportJob.expires_at <= now)
            .delete()
        )
        self.db.commit()
        return deleted
