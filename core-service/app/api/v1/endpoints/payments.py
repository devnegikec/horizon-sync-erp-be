"""Payment Entry management API endpoints"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from sqlalchemy.exc import IntegrityError as SQLIntegrityError

from app.core.exceptions import NotFoundError, ValidationError
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.payment_entry import (
    CancelPaymentRequest,
    PaymentEntryCreate,
    PaymentEntryListResponse,
    PaymentEntryResponse,
    PaymentEntryUpdate,
    PaymentFilters,
)
from app.schemas.payment_reference import (
    PaymentReferenceCreate,
    PaymentReferenceResponse,
)
from app.services.allocation_service import AllocationService
from app.services.payment_entry_service import PaymentEntryService
from app.services.payment_export_service import PaymentExportService
from app.services.receipt_service import ReceiptService
from app.services.reconciliation_report_service import ReconciliationReportService

router = APIRouter()


# Placeholder endpoints - will be implemented in subsequent tasks
@router.post(
    "",
    response_model=PaymentEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create payment entry",
    description="Create a new payment entry in Draft status",
)
async def create_payment_entry(
    data: PaymentEntryCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new payment entry.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Request Body:**
    - **payment_type**: Customer_Payment or Supplier_Payment (required)
    - **party_id**: Customer or Supplier UUID (required)
    - **amount**: Payment amount (must be > 0) (required)
    - **currency_code**: ISO 4217 currency code (default: USD)
    - **payment_date**: Date of payment (required)
    - **payment_mode**: Cash, Check, or Bank_Transfer (required)
    - **reference_no**: Check number or bank UTR (required for Check and Bank_Transfer)
    - **bank_account_id**: Bank account UUID (optional, only for Bank_Transfer)

    **Returns:** Created payment entry details
    """
    try:
        # Validate bank_account_id if provided
        if data.bank_account_id:
            # Validate payment_mode is Bank_Transfer
            if data.payment_mode != "Bank_Transfer":
                raise ValidationError(
                    "bank_account_id can only be provided for Bank_Transfer payment mode"
                )
            
            # Validate bank account exists and belongs to organization
            from app.models.bank_account import BankAccount
            bank_account = db.query(BankAccount).filter(
                BankAccount.id == data.bank_account_id
            ).first()
            
            if not bank_account:
                raise NotFoundError(f"Bank account with ID {data.bank_account_id} not found")
            
            if bank_account.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bank account does not belong to your organization"
                )
            
            if not bank_account.is_active:
                raise ValidationError(
                    f"Bank account '{bank_account.bank_name}' is not active"
                )
        
        service = PaymentEntryService(db)
        payment = service.create_payment_entry(
            data=data,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
        return PaymentEntryResponse.model_validate(payment)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error creating payment entry: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating payment entry",
        )


@router.get(
    "",
    response_model=PaymentEntryListResponse,
    summary="List payment entries",
    description="Get paginated list of payment entries with optional filters",
)
async def list_payment_entries(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=1000, description="Items per page (max 1000)"),
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status: Draft, Confirmed, or Cancelled",
    ),
    payment_mode: str | None = Query(
        None, description="Filter by payment mode: Cash, Check, or Bank_Transfer"
    ),
    payment_type: str | None = Query(
        None, description="Filter by payment type: Customer_Payment or Supplier_Payment"
    ),
    party_id: UUID | None = Query(
        None, description="Filter by customer or supplier ID"
    ),
    date_from: datetime | None = Query(
        None, description="Filter payments from this date (inclusive)"
    ),
    date_to: datetime | None = Query(
        None, description="Filter payments to this date (inclusive)"
    ),
    search: str | None = Query(
        None, description="Search by reference_no or receipt_number"
    ),
    has_unallocated: bool | None = Query(
        None, description="Filter payments with unallocated_amount > 0"
    ),
    sort_by: str = Query("payment_date", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List payment entries with pagination and filters.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 1000)
    - **status**: Filter by status
    - **payment_mode**: Filter by payment mode
    - **payment_type**: Filter by payment type
    - **party_id**: Filter by customer or supplier
    - **date_from**, **date_to**: Date range filter
    - **search**: Search term for reference_no or receipt_number
    - **has_unallocated**: Filter payments with unallocated amounts
    - **sort_by**: Field to sort by (default: payment_date)
    - **sort_order**: Sort order - asc or desc (default: desc)

    **Returns:** Paginated list of payment entries
    """
    try:
        filters = PaymentFilters(
            status=status_filter,
            payment_mode=payment_mode,
            party_id=party_id,
            date_from=date_from,
            date_to=date_to,
            search=search,
            has_unallocated=has_unallocated,
        )
        service = PaymentEntryService(db)
        return service.list_payment_entries(
            filters=filters,
            organization_id=current_user.organization_id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error listing payment entries: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while listing payment entries",
        )


@router.get(
    "/{payment_id}",
    response_model=PaymentEntryResponse,
    summary="Get payment entry",
    description="Get payment entry details by ID",
)
async def get_payment_entry(
    payment_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get payment entry details by ID.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Path Parameters:**
    - **payment_id**: Payment entry UUID

    **Returns:** Payment entry details including allocations
    """
    try:
        service = PaymentEntryService(db)
        payment = service.get_payment_entry(
            payment_id=payment_id,
            organization_id=current_user.organization_id,
        )
        return PaymentEntryResponse.model_validate(payment)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting payment entry: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while getting payment entry",
        )


@router.put(
    "/{payment_id}",
    response_model=PaymentEntryResponse,
    summary="Update payment entry",
    description="Update a draft payment entry",
)
async def update_payment_entry(
    payment_id: UUID,
    data: PaymentEntryUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update a draft payment entry.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Path Parameters:**
    - **payment_id**: Payment entry UUID

    **Request Body:** Fields to update (all optional)
    - **amount**: Payment amount
    - **payment_date**: Date of payment
    - **payment_mode**: Payment mode
    - **reference_no**: Check number or bank UTR
    - **bank_account_id**: Bank account UUID (only for Bank_Transfer)

    **Returns:** Updated payment entry details
    """
    try:
        # Validate bank_account_id if provided
        if data.bank_account_id:
            # If payment_mode is being updated, validate it's Bank_Transfer
            if data.payment_mode and data.payment_mode != "Bank_Transfer":
                raise ValidationError(
                    "bank_account_id can only be provided for Bank_Transfer payment mode"
                )
            
            # If payment_mode is not being updated, we need to check the existing payment
            if not data.payment_mode:
                from app.models.payment_entry import PaymentEntry
                existing_payment = db.query(PaymentEntry).filter(
                    PaymentEntry.id == payment_id,
                    PaymentEntry.organization_id == current_user.organization_id
                ).first()
                
                if existing_payment and existing_payment.payment_mode != "Bank_Transfer":
                    raise ValidationError(
                        "bank_account_id can only be provided for Bank_Transfer payment mode"
                    )
            
            # Validate bank account exists and belongs to organization
            from app.models.bank_account import BankAccount
            bank_account = db.query(BankAccount).filter(
                BankAccount.id == data.bank_account_id
            ).first()
            
            if not bank_account:
                raise NotFoundError(f"Bank account with ID {data.bank_account_id} not found")
            
            if bank_account.organization_id != current_user.organization_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Bank account does not belong to your organization"
                )
            
            if not bank_account.is_active:
                raise ValidationError(
                    f"Bank account '{bank_account.bank_name}' is not active"
                )
        
        service = PaymentEntryService(db)
        payment = service.update_payment_entry(
            payment_id=payment_id,
            data=data,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
        return PaymentEntryResponse.model_validate(payment)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error updating payment entry: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while updating payment entry",
        )


@router.post(
    "/{payment_id}/confirm",
    response_model=PaymentEntryResponse,
    summary="Confirm payment entry",
    description="Confirm payment entry and post to journal",
)
async def confirm_payment(
    payment_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Confirm payment entry and post to journal.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Path Parameters:**
    - **payment_id**: Payment entry UUID

    **Returns:** Confirmed payment entry details
    """
    try:
        service = PaymentEntryService(db)
        payment = service.confirm_payment(
            payment_id=payment_id,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
        return PaymentEntryResponse.model_validate(payment)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error confirming payment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while confirming payment",
        )


@router.post(
    "/{payment_id}/cancel",
    response_model=PaymentEntryResponse,
    summary="Cancel payment entry",
    description="Cancel payment entry and reverse journal entries",
)
async def cancel_payment(
    payment_id: UUID,
    data: CancelPaymentRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Cancel payment entry and reverse journal entries.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Path Parameters:**
    - **payment_id**: Payment entry UUID

    **Request Body:**
    - **cancellation_reason**: Reason for cancelling (minimum 10 characters)

    **Returns:** Cancelled payment entry details
    """
    try:
        service = PaymentEntryService(db)
        payment = service.cancel_payment(
            payment_id=payment_id,
            cancellation_reason=data.cancellation_reason,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
        return PaymentEntryResponse.model_validate(payment)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error cancelling payment: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while cancelling payment",
        )


@router.post(
    "/{payment_id}/allocations",
    response_model=PaymentReferenceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create payment allocation",
    description="Allocate payment amount to an invoice",
)
async def create_allocation(
    payment_id: UUID,
    data: PaymentReferenceCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Allocate payment amount to an invoice.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Path Parameters:**
    - **payment_id**: Payment entry UUID

    **Request Body:**
    - **invoice_id**: Invoice UUID to allocate payment to
    - **allocated_amount**: Amount to allocate to this invoice

    **Returns:** Created payment allocation details
    """
    try:
        service = AllocationService(db)
        allocation = service.create_allocation(
            payment_id=payment_id,
            invoice_id=data.invoice_id,
            allocated_amount=data.allocated_amount,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
        return PaymentReferenceResponse.model_validate(allocation)
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except SQLIntegrityError as e:
        logger.warning(f"Integrity error creating allocation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An allocation for this payment and invoice already exists.",
        )
    except Exception as e:
        logger.error(f"Error creating allocation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while creating allocation: {str(e)}",
        )


@router.get(
    "/{payment_id}/allocations",
    response_model=list[PaymentReferenceResponse],
    summary="Get payment allocations",
    description="Get all allocations for a payment",
)
async def get_payment_allocations(
    payment_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all allocations for a payment.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Path Parameters:**
    - **payment_id**: Payment entry UUID

    **Returns:** List of payment allocations
    """
    try:
        service = AllocationService(db)
        allocations = service.get_payment_allocations(
            payment_id=payment_id,
            organization_id=current_user.organization_id,
        )
        return [PaymentReferenceResponse.model_validate(a) for a in allocations]
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        logger.error(f"Error getting payment allocations: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while getting payment allocations",
        )


@router.delete(
    "/allocations/{allocation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove payment allocation",
    description="Remove a payment allocation",
)
async def remove_allocation(
    allocation_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Remove a payment allocation.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Path Parameters:**
    - **allocation_id**: Payment allocation UUID

    **Returns:** 204 No Content on success
    """
    try:
        service = AllocationService(db)
        service.remove_allocation(
            allocation_id=allocation_id,
            organization_id=current_user.organization_id,
            user_id=current_user.id,
        )
        return None
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception as e:
        logger.error(f"Error removing allocation: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while removing allocation",
        )


@router.get(
    "/{payment_id}/receipt",
    summary="Generate payment receipt",
    description="Generate and download payment receipt PDF",
)
async def generate_receipt(
    payment_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Generate and download payment receipt PDF.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Path Parameters:**
    - **payment_id**: Payment entry UUID

    **Returns:** PDF receipt file
    """
    try:
        service = ReceiptService(db)
        pdf_bytes = service.generate_receipt_pdf(
            payment_id=payment_id,
            organization_id=current_user.organization_id,
        )

        # Return PDF with proper content-type header
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=receipt_{payment_id}.pdf"
            },
        )
    except NotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating receipt: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating receipt",
        )


@router.get(
    "/reports/reconciliation",
    summary="Get reconciliation report",
    description="Generate payment reconciliation report with filters",
)
async def get_reconciliation_report(
    date_from: datetime | None = Query(
        None, description="Start date for payment date range (inclusive)"
    ),
    date_to: datetime | None = Query(
        None, description="End date for payment date range (inclusive)"
    ),
    party_id: UUID | None = Query(
        None, description="Filter by customer or supplier ID"
    ),
    payment_mode: str | None = Query(
        None, description="Filter by payment mode: Cash, Check, or Bank_Transfer"
    ),
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status: Draft, Confirmed, or Cancelled",
    ),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Generate payment reconciliation report.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Query Parameters:**
    - **date_from**: Start date for payment date range (optional)
    - **date_to**: End date for payment date range (optional)
    - **party_id**: Filter by customer or supplier (optional)
    - **payment_mode**: Filter by payment mode (optional)
    - **status**: Filter by payment status (optional)

    **Returns:** Report data as JSON with summary statistics and payment details
    """
    try:
        service = ReconciliationReportService(db)
        report = service.generate_report(
            organization_id=current_user.organization_id,
            date_from=date_from,
            date_to=date_to,
            party_id=party_id,
            payment_mode=payment_mode,
            status=status_filter,
        )
        return report
    except Exception as e:
        logger.error(f"Error generating reconciliation report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while generating reconciliation report",
        )


@router.get(
    "/reports/reconciliation/export",
    summary="Export reconciliation report",
    description="Export payment reconciliation report to Excel or PDF",
)
async def export_reconciliation_report(
    format: str = Query(
        ..., pattern="^(excel|pdf)$", description="Export format: excel or pdf"
    ),
    date_from: datetime | None = Query(
        None, description="Start date for payment date range (inclusive)"
    ),
    date_to: datetime | None = Query(
        None, description="End date for payment date range (inclusive)"
    ),
    party_id: UUID | None = Query(
        None, description="Filter by customer or supplier ID"
    ),
    payment_mode: str | None = Query(
        None, description="Filter by payment mode: Cash, Check, or Bank_Transfer"
    ),
    status_filter: str | None = Query(
        None,
        alias="status",
        description="Filter by status: Draft, Confirmed, or Cancelled",
    ),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Export payment reconciliation report to Excel or PDF.

    Requires authentication. Organization ID is automatically extracted from authenticated user.

    **Query Parameters:**
    - **format**: Export format - excel or pdf (required)
    - **date_from**: Start date for payment date range (optional)
    - **date_to**: End date for payment date range (optional)
    - **party_id**: Filter by customer or supplier (optional)
    - **payment_mode**: Filter by payment mode (optional)
    - **status**: Filter by payment status (optional)

    **Returns:** Excel or PDF file download
    """
    try:
        # Initialize services
        reconciliation_service = ReconciliationReportService(db)
        export_service = PaymentExportService(reconciliation_service)

        # Get organization name (you may want to fetch this from organization service)
        organization_name = (
            "Organization"  # TODO: Fetch from organization service if available
        )

        if format == "excel":
            # Export to Excel
            file_bytes = export_service.export_to_excel(
                organization_id=current_user.organization_id,
                date_from=date_from,
                date_to=date_to,
                party_id=party_id,
                payment_mode=payment_mode,
                status=status_filter,
                organization_name=organization_name,
            )

            # Generate filename with date range
            filename = "reconciliation_report"
            if date_from:
                filename += f"_{date_from.strftime('%Y%m%d')}"
            if date_to:
                filename += f"_to_{date_to.strftime('%Y%m%d')}"
            filename += ".xlsx"

            return Response(
                content=file_bytes,
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
        else:  # format == "pdf"
            # Export to PDF
            file_bytes = export_service.export_to_pdf(
                organization_id=current_user.organization_id,
                date_from=date_from,
                date_to=date_to,
                party_id=party_id,
                payment_mode=payment_mode,
                status=status_filter,
                organization_name=organization_name,
            )

            # Generate filename with date range
            filename = "reconciliation_report"
            if date_from:
                filename += f"_{date_from.strftime('%Y%m%d')}"
            if date_to:
                filename += f"_to_{date_to.strftime('%Y%m%d')}"
            filename += ".pdf"

            return Response(
                content=file_bytes,
                media_type="application/pdf",
                headers={"Content-Disposition": f"attachment; filename={filename}"},
            )
    except Exception as e:
        logger.error(f"Error exporting reconciliation report: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while exporting reconciliation report",
        )
