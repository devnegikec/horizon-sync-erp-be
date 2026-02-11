"""API endpoints for bulk item import operations"""

import logging
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.core.bulk_operations import (
    BulkImportValidator,
    FileFormat,
    ImportTemplate,
)
from app.dependencies import get_db, get_current_user
from app.schemas.bulk_operations import (
    BulkImportJobCreate,
    BulkImportJobDetailResponse,
    BulkImportJobResponse,
    ImportErrorDetail,
    PaginatedBulkImportResponse,
    ImportTemplateDownloadResponse,
)
from app.services.bulk_import_service import BulkImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bulk-import", tags=["Bulk Operations"])


@router.post(
    "/upload",
    response_model=BulkImportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload file for bulk import",
)
async def upload_import_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> BulkImportJobResponse:
    """
    Upload a file for bulk item import.

    Supported formats: CSV, XLSX, JSON
    Maximum file size: 50MB
    Maximum rows: 10,000

    Returns:
        Job information with status PENDING
    """
    try:
        # Get organization from current user
        organization_id = current_user.organization_id
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an organization",
            )

        user_id = current_user.id

        # Validate file
        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File name is required",
            )

        # Get file size
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size
        is_valid, error_msg = BulkImportValidator.validate_file_size(file_size)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=error_msg,
            )

        # Determine file format from extension
        file_ext = file.filename.split(".")[-1].lower()
        if file_ext == "csv":
            file_format = FileFormat.CSV
        elif file_ext in ("xlsx", "xls"):
            file_format = FileFormat.XLSX
        elif file_ext == "json":
            file_format = FileFormat.JSON
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported file format: {file_ext}. Supported: csv, xlsx, json",
            )

        # Validate file format
        is_valid, error_msg = BulkImportValidator.validate_file_format(
            file.content_type or "application/octet-stream", file_format
        )
        if not is_valid:
            logger.warning(f"File format validation failed: {error_msg}")
            # Don't fail on MIME type validation, continue anyway

        # Create import job
        service = BulkImportService(db)
        job = await service.create_import_job(
            organization_id=organization_id,
            created_by_id=user_id,
            file_name=file.filename,
            mime_type=file.content_type or "application/octet-stream",
        )

        # Process import asynchronously (in production, use Celery)
        # For now, we'll process synchronously
        try:
            result = await service.process_import(
                job_id=job.id,
                organization_id=organization_id,
                file_content=file_content,
                file_format=file_format,
            )
            logger.info(f"Import job {job.id} completed: {result}")
        except Exception as e:
            logger.error(f"Failed to process import job {job.id}: {str(e)}")
            # Job status will be updated with error in the service

        # Refresh job to get updated status
        updated_job = await service.get_job_status(job.id)

        return BulkImportJobResponse.model_validate(updated_job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload import file error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process upload",
        )


@router.get(
    "/{job_id}/status",
    response_model=BulkImportJobDetailResponse,
    summary="Get import job status",
)
async def get_import_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> BulkImportJobDetailResponse:
    """
    Get the status of a bulk import job.

    Returns:
        Job details with current status
    """
    try:
        service = BulkImportService(db)
        job = await service.get_job_status(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Import job not found",
            )

        # Verify user has access to this job
        if str(job.organization_id) != str(current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return BulkImportJobDetailResponse.model_validate(job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get import job status error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job status",
        )


@router.get(
    "/{job_id}/errors",
    response_model=list[ImportErrorDetail],
    summary="Get import job errors",
)
async def get_import_job_errors(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> list[ImportErrorDetail]:
    """
    Get detailed error information for a failed import job.

    Returns:
        List of errors with row numbers and details
    """
    try:
        service = BulkImportService(db)
        job = await service.get_job_status(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Import job not found",
            )

        # Verify user has access
        if str(job.organization_id) != str(current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        errors = await service.get_job_errors(job_id)
        return errors or []

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get import job errors error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job errors",
        )


@router.get(
    "",
    response_model=PaginatedBulkImportResponse,
    summary="List import jobs",
)
async def list_import_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PaginatedBulkImportResponse:
    """
    List bulk import jobs for the current organization.

    Returns:
        Paginated list of import jobs
    """
    try:
        if page < 1 or page_size < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="page and page_size must be >= 1",
            )

        organization_id = current_user.organization_id
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an organization",
            )

        service = BulkImportService(db)
        jobs, total = await service.list_jobs(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
        )

        return PaginatedBulkImportResponse(
            items=[BulkImportJobResponse.model_validate(job) for job in jobs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List import jobs error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list jobs",
        )


@router.get(
    "/template/csv",
    summary="Download CSV import template",
)
async def download_csv_template() -> ImportTemplateDownloadResponse:
    """
    Download a CSV import template with sample data.

    Returns:
        File for download
    """
    try:
        return {
            "download_url": "/api/v1/bulk-import/template/csv/download",
            "file_format": "csv",
            "file_name": "items_import_template.csv",
        }
    except Exception as e:
        logger.error(f"Download CSV template error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate template",
        )


@router.get(
    "/template/xlsx",
    summary="Download XLSX import template",
)
async def download_xlsx_template() -> ImportTemplateDownloadResponse:
    """
    Download an XLSX import template with sample data.

    Returns:
        File for download
    """
    try:
        return {
            "download_url": "/api/v1/bulk-import/template/xlsx/download",
            "file_format": "xlsx",
            "file_name": "items_import_template.xlsx",
        }
    except Exception as e:
        logger.error(f"Download XLSX template error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate template",
        )
