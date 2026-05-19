"""Service for bulk item import operations"""

import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.bulk_operations import (
    BulkImportValidator,
    FileParser,
)
from app.models.bulk_import_job import BulkImportJob, BulkImportJobStatus
from app.models.item import Item
from app.models.item_group import ItemGroup
from app.repositories.bulk_import_repository import BulkImportRepository
from app.schemas.bulk_operations import ImportErrorDetail
from app.services.document_numbering_service import DocumentNumberingService

logger = logging.getLogger(__name__)


class BulkImportService:
    """Service for bulk import operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repository = BulkImportRepository(db)

    async def create_import_job(
        self, organization_id: UUID, created_by_id: UUID, file_name: str, mime_type: str
    ) -> BulkImportJob:
        """
        Create a new bulk import job.

        Args:
            organization_id: Organization UUID
            created_by_id: User UUID
            file_name: Name of the file
            mime_type: MIME type of the file

        Returns:
            Created BulkImportJob
        """
        return self.repository.create_job(
            organization_id=organization_id,
            created_by_id=created_by_id,
            file_name=file_name,
            mime_type=mime_type,
        )

    async def get_job_status(self, job_id: UUID) -> BulkImportJob | None:
        """
        Get import job status.

        Args:
            job_id: Job UUID

        Returns:
            BulkImportJob or None
        """
        return self.repository.get_job_by_id(job_id)

    async def list_jobs(
        self, organization_id: UUID, page: int = 1, page_size: int = 20
    ) -> tuple[list[BulkImportJob], int]:
        """
        List import jobs for organization.

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

    async def process_import(
        self,
        job_id: UUID,
        organization_id: UUID,
        file_content: bytes,
        file_format: str,
    ) -> dict:
        """
        Process bulk import file.

        Args:
            job_id: Job UUID
            organization_id: Organization UUID
            file_content: File content as bytes
            file_format: File format (csv, xlsx, json)

        Returns:
            Processing result dictionary
        """
        try:
            # Get job to retrieve created_by_id
            job = self.repository.get_job_by_id(job_id)
            if not job:
                return {"success": False, "error": "Job not found"}

            user_id = job.created_by_id

            # Update job status to PROCESSING
            self.repository.update_job_status(job_id, BulkImportJobStatus.PROCESSING)

            # Parse file
            try:
                rows = FileParser.parse_file(file_content, file_format)
            except ValueError as e:
                error_msg = f"File parsing failed: {str(e)}"
                logger.error(error_msg)
                self.repository.update_job_status(
                    job_id, BulkImportJobStatus.FAILED, error_msg
                )
                return {
                    "success": False,
                    "error": error_msg,
                }

            if not rows:
                error_msg = "No data found in file"
                self.repository.update_job_status(
                    job_id, BulkImportJobStatus.FAILED, error_msg
                )
                return {
                    "success": False,
                    "error": error_msg,
                }

            # Check row limit
            if len(rows) > BulkImportValidator.MAX_ROWS:
                error_msg = f"File contains {len(rows)} rows. Maximum allowed is {BulkImportValidator.MAX_ROWS}"
                self.repository.update_job_status(
                    job_id, BulkImportJobStatus.FAILED, error_msg
                )
                return {
                    "success": False,
                    "error": error_msg,
                }

            # Validate columns
            if rows:
                is_valid_cols, col_errors = BulkImportValidator.validate_columns(
                    list(rows[0].keys())
                )
                if not is_valid_cols:
                    error_msg = col_errors[0]
                    self.repository.update_job_status(
                        job_id, BulkImportJobStatus.FAILED, error_msg
                    )
                    return {
                        "success": False,
                        "error": error_msg,
                    }

            # Validate and import rows
            successful_rows = 0
            failed_rows = 0
            error_details = []

            # Cache for item groups to avoid redundant DB lookups
            item_groups_cache = {}

            for row_number, row in enumerate(rows, start=1):
                # Validate row
                is_valid, errors = BulkImportValidator.validate_row(row, row_number)

                if not is_valid:
                    failed_rows += 1
                    error_details.append(
                        {
                            "row_number": row_number,
                            "errors": errors,
                            "data": row,
                        }
                    )
                    continue

                # Handle Item Group auto-creation
                item_group_id = row.get("item_group_id")
                item_group_name = row.get("item_group_name")

                if not item_group_id and item_group_name:
                    item_group_name = item_group_name.strip()
                    if item_group_name in item_groups_cache:
                        item_group_id = item_groups_cache[item_group_name]
                    else:
                        # Check if group exists by name
                        existing_group = (
                            self.db.query(ItemGroup)
                            .filter(
                                ItemGroup.organization_id == organization_id,
                                ItemGroup.name == item_group_name,
                            )
                            .first()
                        )
                        if existing_group:
                            item_group_id = existing_group.id
                        else:
                            # Create new item group
                            try:
                                new_group = ItemGroup(
                                    organization_id=organization_id,
                                    name=item_group_name,
                                    code=item_group_name.upper().replace(" ", "_")[:50],
                                    is_active=True,
                                    created_by=user_id,
                                    updated_by=user_id,
                                )
                                self.db.add(new_group)
                                self.db.commit()
                                self.db.refresh(new_group)
                                item_group_id = new_group.id
                            except Exception as e:
                                self.db.rollback()
                                logger.error(
                                    f"Failed to create item group '{item_group_name}': {str(e)}"
                                )
                                # Continue with None item_group_id or fail the row?
                                # Let's fail the row if group creation was explicitly requested but failed.
                                failed_rows += 1
                                error_details.append(
                                    {
                                        "row_number": row_number,
                                        "errors": [
                                            f"Failed to create item group '{item_group_name}'"
                                        ],
                                        "data": row,
                                    }
                                )
                                continue

                        item_groups_cache[item_group_name] = item_group_id

                # Auto-generate item_code (ignore any item_code from CSV)
                auto_item_code = DocumentNumberingService(self.db).get_next_number(
                    organization_id, "item"
                )

                # Check if item with same name already exists — update instead of create
                existing_item = (
                    self.db.query(Item)
                    .filter(
                        Item.organization_id == organization_id,
                        Item.item_name == row["item_name"].strip(),
                    )
                    .first()
                )

                # Create or update item
                try:
                    # Map standard fields
                    item_data = {
                        "item_name": row["item_name"].strip(),
                        "item_group_id": item_group_id
                        or row.get("item_group_id")
                        or None,
                        "updated_by": user_id,
                    }

                    # Map other valid columns if present in row
                    for col in BulkImportValidator.VALID_COLUMNS:
                        if (
                            col in row
                            and col
                            not in [
                                "item_code",
                                "item_name",
                                "item_group_id",
                                "item_group_name",
                            ]
                            and row[col] is not None
                        ):
                            # Handle numeric conversions
                            if col in [
                                "standard_rate",
                                "valuation_rate",
                                "weight_per_unit",
                            ]:
                                try:
                                    item_data[col] = float(row[col])
                                except (ValueError, TypeError):
                                    continue
                            # Handle boolean conversions
                            elif col in [
                                "maintain_stock",
                                "allow_negative_stock",
                                "has_variants",
                                "has_batch_no",
                                "has_serial_no",
                                "enable_auto_reorder",
                                "inspection_required_before_purchase",
                                "inspection_required_before_delivery",
                            ]:
                                if isinstance(row[col], str):
                                    item_data[col] = row[col].lower() in [
                                        "true",
                                        "1",
                                        "yes",
                                        "t",
                                    ]
                                else:
                                    item_data[col] = bool(row[col])
                            # Handle integer conversions
                            elif col in [
                                "reorder_level",
                                "reorder_qty",
                                "min_order_qty",
                                "max_order_qty",
                            ]:
                                try:
                                    item_data[col] = int(row[col])
                                except (ValueError, TypeError):
                                    continue
                            # Default for strings/JSON
                            else:
                                val = row[col]
                                if isinstance(val, str):
                                    val = val.strip()
                                item_data[col] = val or None

                    if existing_item:
                        # UPDATE existing item with CSV data
                        for key, value in item_data.items():
                            if value is not None:
                                setattr(existing_item, key, value)
                        self.db.commit()
                    else:
                        # CREATE new item
                        item_data["organization_id"] = organization_id
                        item_data["item_code"] = auto_item_code
                        item_data["created_by"] = user_id
                        item = Item(**item_data)
                        self.db.add(item)
                        self.db.commit()

                    successful_rows += 1

                except Exception as e:
                    self.db.rollback()
                    failed_rows += 1
                    error_details.append(
                        {
                            "row_number": row_number,
                            "errors": [f"Database error: {str(e)}"],
                            "data": row,
                        }
                    )
                    logger.error(f"Row {row_number} import failed: {str(e)}")

            # Update job with statistics
            total_rows = successful_rows + failed_rows
            summary = (
                f"Import completed: {successful_rows}/{total_rows} rows successful"
            )

            self.repository.update_job_statistics(
                job_id,
                total_rows=total_rows,
                successful_rows=successful_rows,
                failed_rows=failed_rows,
                error_details={"errors": error_details} if error_details else None,
            )

            self.repository.update_job_status(
                job_id,
                BulkImportJobStatus.COMPLETED,
                summary,
            )

            return {
                "success": True,
                "job_id": str(job_id),
                "total_rows": total_rows,
                "successful_rows": successful_rows,
                "failed_rows": failed_rows,
                "has_errors": len(error_details) > 0,
            }

        except Exception as e:
            error_msg = f"Import processing error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.repository.update_job_status(
                job_id, BulkImportJobStatus.FAILED, error_msg
            )
            return {
                "success": False,
                "error": error_msg,
            }

    async def get_job_errors(self, job_id: UUID) -> list[ImportErrorDetail] | None:
        """
        Get detailed errors for a job.

        Args:
            job_id: Job UUID

        Returns:
            List of ImportErrorDetail or None
        """
        job = self.repository.get_job_by_id(job_id)
        if not job or not job.error_details:
            return None

        error_list = job.error_details.get("errors", [])
        return [ImportErrorDetail(**error) for error in error_list]
