"""Schemas for bulk import and export operations"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


# ==================== BULK IMPORT SCHEMAS ====================


class BulkImportJobCreate(BaseModel):
    """Schema for creating a bulk import job"""

    file_name: str = Field(..., description="Name of the uploaded file")
    mime_type: str = Field(..., description="MIME type of the file")


class BulkImportJobResponse(BaseModel):
    """Schema for bulk import job response"""

    id: UUID
    organization_id: UUID
    created_by_id: UUID
    file_name: str
    status: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    error_details: Optional[dict] = None
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BulkImportJobDetailResponse(BulkImportJobResponse):
    """Detailed schema for bulk import job response"""

    file_path: Optional[str] = None


class BulkItemImport(BaseModel):
    """Schema for individual item import"""

    item_code: str = Field(..., max_length=100, description="Unique item code")
    item_name: str = Field(..., max_length=255, description="Item name")
    description: Optional[str] = Field(None, max_length=500)
    item_group_id: Optional[UUID] = None
    item_type: Optional[str] = Field(None, description="Stock, Service, etc.")
    status: Optional[str] = Field(None, description="Active, Inactive")
    uom: Optional[str] = Field("Nos")
    standard_rate: Optional[float] = Field(None, ge=0)


class ImportErrorDetail(BaseModel):
    """Schema for import error details"""

    row_number: int
    errors: list[str]
    data: Optional[dict] = None


class ImportResult(BaseModel):
    """Schema for import result"""

    job_id: UUID
    total_rows: int
    successful_rows: int
    failed_rows: int
    errors: Optional[list[ImportErrorDetail]] = None
    status: str


# ==================== BULK EXPORT SCHEMAS ====================


class ExportFilter(BaseModel):
    """Schema for export filters"""

    item_type: Optional[str] = None
    status: Optional[str] = None
    item_group_id: Optional[UUID] = None
    search: Optional[str] = None


class BulkExportRequest(BaseModel):
    """Schema for export request"""

    file_format: str = Field(..., description="csv, xlsx, json, or pdf")
    filters: Optional[ExportFilter] = None
    selected_columns: Optional[list[str]] = None
    file_name: Optional[str] = Field(
        None, description="Custom file name (without extension)"
    )


class BulkExportJobResponse(BaseModel):
    """Schema for bulk export job response"""

    id: UUID
    organization_id: UUID
    created_by_id: UUID
    file_name: str
    file_format: str
    status: str
    total_rows: str
    filters: Optional[dict] = None
    selected_columns: Optional[list] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BulkExportJobDetailResponse(BulkExportJobResponse):
    """Detailed schema for bulk export job response"""

    file_path: Optional[str] = None
    error_message: Optional[str] = None


class ExportDownloadResponse(BaseModel):
    """Schema for export download response"""

    download_url: str
    expires_at: datetime
    file_name: str
    file_format: str


# ==================== PAGINATION SCHEMAS ====================


class PaginatedBulkImportResponse(BaseModel):
    """Schema for paginated bulk import jobs"""

    items: list[BulkImportJobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedBulkExportResponse(BaseModel):
    """Schema for paginated bulk export jobs"""

    items: list[BulkExportJobResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==================== TEMPLATE SCHEMAS ====================


class ImportTemplateDownloadResponse(BaseModel):
    """Schema for import template download response"""

    download_url: str
    file_format: str
    file_name: str
    columns: list[str] = [
        "item_code",
        "item_name",
        "description",
        "item_group_id",
        "item_type",
        "status",
        "uom",
        "standard_rate",
    ]
