"""API endpoints for bulk item export operations"""

import logging
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_current_user
from app.schemas.bulk_operations import (
    BulkExportJobDetailResponse,
    BulkExportJobResponse,
    BulkExportRequest,
    ExportDownloadResponse,
    ExportFilter,
    PaginatedBulkExportResponse,
)
from app.services.bulk_export_service import BulkExportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bulk-export", tags=["Bulk Operations"])


@router.post(
    "",
    response_model=BulkExportJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Create bulk export job",
)
async def create_export_job(
    request: BulkExportRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> BulkExportJobResponse:
    """
    Create a bulk export job for items.

    Supported formats: csv, xlsx, json

    Returns:
        Export job with status PENDING
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

        # Validate format
        if request.file_format not in ["csv", "xlsx", "json", "pdf"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supported formats: csv, xlsx, json, pdf",
            )

        # Generate file name if not provided
        file_name = (
            request.file_name
            or f"items_export_{organization_id.hex[:8]}"
        )

        # Create export job
        service = BulkExportService(db)
        job = await service.create_export_job(
            organization_id=organization_id,
            created_by_id=user_id,
            file_name=file_name,
            file_format=request.file_format,
            filters=request.filters.model_dump() if request.filters else None,
            selected_columns=request.selected_columns,
        )

        # Process export asynchronously (in production, use Celery)
        # For now, we'll process synchronously
        try:
            result = await service.process_export(
                job_id=job.id,
                organization_id=organization_id,
                file_format=request.file_format,
                filters=request.filters.model_dump() if request.filters else None,
                selected_columns=request.selected_columns,
            )
            logger.info(f"Export job {job.id} completed: {result}")
        except Exception as e:
            logger.error(f"Failed to process export job {job.id}: {str(e)}")

        # Refresh job to get updated status
        updated_job = await service.get_job_status(job.id)

        return BulkExportJobResponse.model_validate(updated_job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Create export job error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create export job",
        )


@router.get(
    "/{job_id}/status",
    response_model=BulkExportJobDetailResponse,
    summary="Get export job status",
)
async def get_export_job_status(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> BulkExportJobDetailResponse:
    """
    Get the status of a bulk export job.

    Returns:
        Job details with current status
    """
    try:
        service = BulkExportService(db)
        job = await service.get_job_status(job_id)

        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found",
            )

        # Verify user has access to this job
        if str(job.organization_id) != str(current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        return BulkExportJobDetailResponse.model_validate(job)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get export job status error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get job status",
        )


@router.get(
    "/{job_id}/download",
    summary="Download exported file",
)
async def download_export_file(
    job_id: UUID,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Download an exported file.

    Returns:
        File stream for download
    """
    try:
        service = BulkExportService(db)
        job = await service.get_job_status(job_id)
        organization_id=current_user.organization_id
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found",
            )

        # Verify user has access
        if str(job.organization_id) != str(current_user.organization_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied",
            )

        # Check if export is completed
        if job.status != "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Export job status is {job.status}. Only completed exports can be downloaded.",
            )

        # Check if export has expired
        from datetime import UTC, datetime
        if job.expires_at and job.expires_at < datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Export file has expired",
            )

        # In a real implementation, read the file from storage
        # For now, we'll re-generate it
        result = await service.process_export(
            job_id=job.id,
            organization_id=organization_id,
            file_format=job.file_format,
            filters=job.filters,
            selected_columns=job.selected_columns,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate export file",
            )

        file_content = result["file_content"]
        file_ext = job.file_format

        # Determine media type based on format
        media_types = {
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json",
            "pdf": "application/pdf",
        }
        media_type = media_types.get(file_ext, "application/octet-stream")

        return StreamingResponse(
            iter([file_content]),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={job.file_name}.{file_ext}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download export file error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download export file",
        )


@router.get(
    "",
    response_model=PaginatedBulkExportResponse,
    summary="List export jobs",
)
async def list_export_jobs(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> PaginatedBulkExportResponse:
    """
    List bulk export jobs for the current organization.

    Returns:
        Paginated list of export jobs
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

        service = BulkExportService(db)
        jobs, total = await service.list_jobs(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
        )

        return PaginatedBulkExportResponse(
            items=[BulkExportJobResponse.model_validate(job) for job in jobs],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"List export jobs error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list jobs",
        )


@router.post(
    "/quick",
    summary="Quick export items",
)
async def quick_export_items(
    file_format: str = Query(..., description="csv, xlsx, or json"),
    item_type: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    item_group_id: UUID | None = Query(None),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Quick export items without creating a job.

    Returns:
        Exported file stream
    """
    try:
        if file_format not in ["csv", "xlsx", "json", "pdf"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Supported formats: csv, xlsx, json, pdf",
            )

        organization_id = current_user.organization_id
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an organization",
            )

        # Build filters
        filters = {}
        if item_type:
            filters["item_type"] = item_type
        if status_filter:
            filters["status"] = status_filter
        if item_group_id:
            filters["item_group_id"] = item_group_id
        if search:
            filters["search"] = search

        # Create temporary job for quick export
        service = BulkExportService(db)
        job = await service.create_export_job(
            organization_id=organization_id,
            created_by_id=current_user.id,
            file_name=f"items_export",
            file_format=file_format,
            filters=filters,
        )

        # Process export
        result = await service.process_export(
            job_id=job.id,
            organization_id=organization_id,
            file_format=file_format,
            filters=filters,
        )

        if not result.get("success"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate export",
            )

        file_content = result["file_content"]

        # Determine media type
        media_types = {
            "csv": "text/csv",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "json": "application/json",
        }
        media_type = media_types.get(file_format, "application/octet-stream")

        return StreamingResponse(
            iter([file_content]),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename=items_export.{file_format}"
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Quick export items error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export items",
        )
