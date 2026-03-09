"""Schemas for bulk import and export operations"""

from datetime import datetime
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
    error_details: dict | None = None
    summary: str | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None

    class Config:
        from_attributes = True


class BulkImportJobDetailResponse(BulkImportJobResponse):
    """Detailed schema for bulk import job response"""

    file_path: str | None = None


class BulkItemImport(BaseModel):
    """Schema for individual item import"""

    item_code: str = Field(..., max_length=100, description="Unique item code")
    item_name: str = Field(..., max_length=255, description="Item name")
    description: str | None = Field(None, max_length=500)
    item_group_id: UUID | None = None
    item_type: str | None = Field(None, description="Stock, Service, etc.")
    status: str | None = Field(None, description="Active, Inactive")
    uom: str | None = Field("Nos")
    standard_rate: float | None = Field(None, ge=0)


class ImportErrorDetail(BaseModel):
    """Schema for import error details"""

    row_number: int
    errors: list[str]
    data: dict | None = None


class ImportResult(BaseModel):
    """Schema for import result"""

    job_id: UUID
    total_rows: int
    successful_rows: int
    failed_rows: int
    errors: list[ImportErrorDetail] | None = None
    status: str


# ==================== BULK EXPORT SCHEMAS ====================


class ExportFilter(BaseModel):
    """Schema for export filters"""

    item_type: str | None = None
    status: str | None = None
    item_group_id: UUID | None = None
    search: str | None = None


class BulkExportRequest(BaseModel):
    """Schema for export request"""

    file_format: str = Field(..., description="csv, xlsx, json, or pdf")
    filters: ExportFilter | None = None
    selected_columns: list[str] | None = None
    file_name: str | None = Field(
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
    filters: dict | None = None
    selected_columns: list | None = None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    expires_at: datetime | None = None

    class Config:
        from_attributes = True


class BulkExportJobDetailResponse(BulkExportJobResponse):
    """Detailed schema for bulk export job response"""

    file_path: str | None = None
    error_message: str | None = None


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
