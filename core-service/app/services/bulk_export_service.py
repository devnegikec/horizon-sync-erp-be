"""Service for bulk item export operations"""

import logging
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.bulk_operations import BulkImportValidator, FileGenerator
from app.models.bulk_export_job import BulkExportJob, BulkExportJobStatus
from app.models.item import Item
from app.repositories.bulk_export_repository import BulkExportRepository

logger = logging.getLogger(__name__)


class BulkExportService:
    """Service for bulk export operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = BulkExportRepository(db)

    async def create_export_job(
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
            created_by_id: User UUID
            file_name: Name of the file
            file_format: Format of export (csv, xlsx, json)
            filters: Optional filters dictionary
            selected_columns: Optional list of columns to include

        Returns:
            Created BulkExportJob
        """
        return self.repository.create_job(
            organization_id=organization_id,
            created_by_id=created_by_id,
            file_name=file_name,
            file_format=file_format,
            filters=filters,
            selected_columns=selected_columns,
        )

    async def get_job_status(self, job_id: UUID) -> BulkExportJob | None:
        """
        Get export job status.

        Args:
            job_id: Job UUID

        Returns:
            BulkExportJob or None
        """
        return self.repository.get_job_by_id(job_id)

    async def list_jobs(
        self, organization_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[BulkExportJob], int]:
        """
        List export jobs for organization.

        Args:
            organization_id: Organization UUID
            page: Page number
            page_size: Items per page

        Returns:
            Tuple of (jobs list, total count)
        """
        return self.repository.get_jobs_by_organization(
            organization_id, page, page_size
        )

    async def process_export(
        self,
        job_id: UUID,
        organization_id: UUID,
        file_format: str,
        filters: dict | None = None,
        selected_columns: list | None = None,
    ) -> dict:
        """
        Process bulk export.

        Args:
            job_id: Job UUID
            organization_id: Organization UUID
            file_format: Export format (csv, xlsx, json)
            filters: Optional filters
            selected_columns: Optional column selection

        Returns:
            Processing result dictionary
        """
        try:
            # Update job status to PROCESSING
            self.repository.update_job_status(job_id, BulkExportJobStatus.PROCESSING)

            # Build query
            query = self.db.query(Item).filter(Item.organization_id == organization_id)

            # Apply filters
            if filters:
                if filters.get("item_type"):
                    query = query.filter(Item.item_type == filters["item_type"])

                if filters.get("status"):
                    query = query.filter(Item.status == filters["status"])

                if filters.get("item_group_id"):
                    query = query.filter(Item.item_group_id == filters["item_group_id"])

                if filters.get("search"):
                    search_term = f"%{filters['search']}%"
                    query = query.filter(
                        or_(
                            Item.item_code.ilike(search_term),
                            Item.item_name.ilike(search_term),
                            Item.description.ilike(search_term),
                        )
                    )

            # Execute query
            items = query.all()
            total_rows = len(items)

            if total_rows == 0:
                logger.warning(f"Export job {job_id}: No items found matching filters")

            # Convert items to dictionaries
            export_data = []

            # Use all valid columns from Item model as default
            all_schema_columns = sorted(list(BulkImportValidator.VALID_COLUMNS))
            columns_to_export = selected_columns or all_schema_columns

            for item in items:
                row = {}
                for col in columns_to_export:
                    # Handle special fields first
                    if col == "item_group_name":
                        row[col] = item.item_group.name if item.item_group else None
                    elif hasattr(item, col):
                        value = getattr(item, col)
                        # Convert UUID and Enum to string for serialization
                        if hasattr(value, "hex") or hasattr(value, "value"):
                            value = str(value)
                        row[col] = value
                    else:
                        row[col] = None
                export_data.append(row)

            # Generate file
            try:
                file_content = FileGenerator.generate_file(
                    export_data, file_format, headers=columns_to_export
                )
            except Exception as e:
                error_msg = f"File generation failed: {str(e)}"
                logger.error(error_msg)
                self.repository.update_job_status(
                    job_id, BulkExportJobStatus.FAILED, error_msg
                )
                return {
                    "success": False,
                    "error": error_msg,
                }

            # Update job with file information
            self.repository.update_job_file_path(
                job_id, f"/exports/{job_id}/{job_id}.{file_format}", total_rows
            )

            # Update job status to COMPLETED
            self.repository.update_job_status(job_id, BulkExportJobStatus.COMPLETED)

            return {
                "success": True,
                "job_id": str(job_id),
                "total_rows": total_rows,
                "file_content": file_content,
            }

        except Exception as e:
            error_msg = f"Export processing error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.repository.update_job_status(
                job_id, BulkExportJobStatus.FAILED, error_msg
            )
            return {
                "success": False,
                "error": error_msg,
            }

    async def cleanup_expired_exports(self) -> int:
        """
        Clean up expired export jobs.

        Returns:
            Number of deleted jobs
        """
        return self.repository.cleanup_expired_exports()
