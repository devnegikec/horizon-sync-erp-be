"""Bulk import API for stock entries — CSV and XLSX upload."""

import logging

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.services.stock_entry_bulk_import_service import (
    BulkImportResult,
    StockEntryBulkImportService,
    generate_csv_template,
    generate_xlsx_template,
)

logger = logging.getLogger(__name__)

router = APIRouter()

STOCK_ENTRY_CREATE = "stock_entry.create"

_MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class RowErrorOut(BaseModel):
    row: int
    field: str
    message: str


class BulkImportResponse(BaseModel):
    total_rows: int
    created: int
    failed: int
    errors: list[RowErrorOut]


def _to_response(result: BulkImportResult) -> BulkImportResponse:
    return BulkImportResponse(
        total_rows=result.total_rows,
        created=result.created,
        failed=result.failed,
        errors=[
            RowErrorOut(row=e.row, field=e.field, message=e.message)
            for e in result.errors
        ],
    )


# ---------------------------------------------------------------------------
# Template downloads
# ---------------------------------------------------------------------------


@router.get(
    "/template/csv",
    summary="Download CSV import template for stock entries",
    response_class=Response,
    responses={200: {"content": {"text/csv": {}}, "description": "CSV template file"}},
)
async def download_csv_template(
    current_user: CurrentUser = Depends(require_permission(STOCK_ENTRY_CREATE)),
):
    """Download a sample CSV template with column headers and example rows."""
    content = generate_csv_template()
    return Response(
        content=content,
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="stock_entries_template.csv"'
        },
    )


@router.get(
    "/template/xlsx",
    summary="Download XLSX import template for stock entries",
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {}
            },
            "description": "XLSX template file",
        }
    },
)
async def download_xlsx_template(
    current_user: CurrentUser = Depends(require_permission(STOCK_ENTRY_CREATE)),
):
    """Download a sample XLSX template with column headers, example rows, and an Instructions sheet."""
    content = generate_xlsx_template()
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": 'attachment; filename="stock_entries_template.xlsx"'
        },
    )


# ---------------------------------------------------------------------------
# Upload endpoint
# ---------------------------------------------------------------------------


@router.post(
    "/upload",
    response_model=BulkImportResponse,
    status_code=status.HTTP_200_OK,
    summary="Bulk import stock entries from CSV or XLSX",
)
async def bulk_import_stock_entries(
    file: UploadFile = File(..., description="CSV or XLSX file. Max 10 MB, 500 rows."),
    current_user: CurrentUser = Depends(require_permission(STOCK_ENTRY_CREATE)),
    db: Session = Depends(get_db),
) -> BulkImportResponse:
    """
    Import multiple stock entries from a CSV or XLSX file.

    - Download the template first via GET /template/csv or /template/xlsx.
    - Each row = one stock entry with one line item (auto-numbered SE-YYYY-NNNN).
    - Use warehouse and item **codes** (not UUIDs) — e.g. `WH-MAIN`, `ITEM-001`.
    - Entries are created as **draft**. Submit them individually via POST /{id}/submit.
    - Returns a summary with per-row errors so you can fix and re-upload.

    Supported formats: `.csv`, `.xlsx`
    Max file size: 10 MB | Max rows: 500
    """
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="File name is required."
        )

    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
    if ext not in ("csv", "xlsx", "xls"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type '.{ext}'. Upload a .csv or .xlsx file.",
        )

    content = await file.read()
    if len(content) > _MAX_FILE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File exceeds the 10 MB limit.",
        )

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty."
        )

    svc = StockEntryBulkImportService(db)
    try:
        if ext == "csv":
            result = svc.import_from_csv(
                content, current_user.organization_id, current_user.id
            )
        else:
            result = svc.import_from_xlsx(
                content, current_user.organization_id, current_user.id
            )
    except Exception as exc:
        logger.exception("Unexpected error during stock entry bulk import")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Import failed: {exc}",
        ) from exc

    return _to_response(result)
