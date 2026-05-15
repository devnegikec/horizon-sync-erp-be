"""API endpoints for bulk customer import/export operations"""

import csv
import io
import logging

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.bulk_operations import FileFormat
from app.database import get_db
from app.dependencies import get_current_user
from app.models.customer import Customer
from app.services.bulk_customer_import_service import BulkCustomerImportService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers/bulk", tags=["Customer Bulk Operations"])


@router.post(
    "/import",
    status_code=status.HTTP_200_OK,
    summary="Bulk import customers from CSV/XLSX/JSON",
)
async def bulk_import_customers(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Upload a file for bulk customer import.

    Supported formats: CSV, XLSX, JSON
    Maximum rows: 10,000

    Required columns: customer_name
    Optional columns: customer_code, email, phone, address, address_line1,
    address_line2, city, state, postal_code, country, tax_number, status, credit_limit

    If a customer with the same name already exists, it will be updated.
    If customer_code is not provided, it will be auto-generated.
    """
    try:
        organization_id = current_user.organization_id
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an organization",
            )

        user_id = current_user.id

        if not file.filename:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="File name is required",
            )

        # Read file content
        file_content = await file.read()
        file_size = len(file_content)

        # Validate file size (50MB max)
        if file_size > 50 * 1024 * 1024:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File size exceeds 50MB limit",
            )

        # Determine file format
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

        # Process import
        service = BulkCustomerImportService(db)
        result = await service.process_import(
            organization_id=organization_id,
            user_id=user_id,
            file_content=file_content,
            file_format=file_format,
        )

        if not result.get("success") and result.get("error"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"],
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer bulk import error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process customer import",
        )


@router.get(
    "/export",
    summary="Export customers as CSV",
)
async def bulk_export_customers(
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    search: str | None = Query(None, description="Search filter"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """
    Export all customers as a CSV file.

    Optional filters:
    - status: active, inactive, blocked
    - search: search in name, code, email
    """
    try:
        organization_id = current_user.organization_id
        if not organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User must belong to an organization",
            )

        # Query customers
        query = db.query(Customer).filter(
            Customer.organization_id == organization_id,
            Customer.deleted_at.is_(None),
        )

        if status_filter:
            query = query.filter(Customer.status == status_filter)

        if search:
            search_term = f"%{search}%"
            query = query.filter(
                (Customer.customer_name.ilike(search_term))
                | (Customer.customer_code.ilike(search_term))
                | (Customer.email.ilike(search_term))
            )

        customers = query.order_by(Customer.created_at.desc()).all()

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header row
        headers = [
            "customer_code", "customer_name", "email", "phone",
            "address_line1", "address_line2", "city", "state",
            "postal_code", "country", "tax_number", "status", "credit_limit",
        ]
        writer.writerow(headers)

        # Data rows
        for c in customers:
            writer.writerow([
                c.customer_code or "",
                c.customer_name or "",
                c.email or "",
                c.phone or "",
                c.address_line1 or "",
                c.address_line2 or "",
                c.city or "",
                c.state or "",
                c.postal_code or "",
                c.country or "",
                c.tax_number or "",
                c.status.value if c.status else "active",
                str(c.credit_limit or 0),
            ])

        output.seek(0)

        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=customers_export.csv"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Customer bulk export error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export customers",
        )


@router.get(
    "/template",
    summary="Download customer import template CSV",
)
async def download_customer_template():
    """Download a sample CSV template for customer import."""
    output = io.StringIO()
    writer = csv.writer(output)

    # Header
    writer.writerow([
        "customer_name", "customer_code", "email", "phone",
        "address_line1", "address_line2", "city", "state",
        "postal_code", "country", "tax_number", "status", "credit_limit",
    ])

    # Sample rows
    writer.writerow([
        "Acme Corporation", "", "contact@acme.com", "+1-555-0100",
        "123 Business Ave", "Suite 400", "New York", "NY",
        "10001", "USA", "US-TAX-12345", "active", "50000",
    ])
    writer.writerow([
        "Global Supplies Ltd", "", "info@globalsupplies.com", "+44-20-7946-0958",
        "45 Commerce Street", "", "London", "",
        "EC1A 1BB", "UK", "GB-VAT-67890", "active", "25000",
    ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=customers-import-template.csv"},
    )
