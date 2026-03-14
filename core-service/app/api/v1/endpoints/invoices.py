"""Invoices API endpoints (Phase 7)"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import INVOICE_CREATE, INVOICE_READ, INVOICE_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.invoice import (
    InvoiceCreate,
    InvoiceListItem,
    InvoiceListResponse,
    InvoiceResponse,
    InvoiceUpdate,
)
from app.services.invoice_service import InvoiceService

router = APIRouter()


@router.post("", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
async def create_invoice(
    body: InvoiceCreate,
    current_user: CurrentUser = Depends(require_permission(INVOICE_CREATE)),
    db: Session = Depends(get_db),
):
    """Create invoice. Requires invoice.create."""
    svc = InvoiceService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)
    return InvoiceResponse.model_validate(data)


@router.get("", response_model=InvoiceListResponse)
async def list_invoices(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    party_id: UUID | None = None,
    status: str | None = Query(
        None, pattern="^(draft|pending|paid|partial|overdue|cancelled)$"
    ),
    invoice_type: str | None = Query(None, pattern="^(sales|purchase)$"),
    sort_by: str = Query("posting_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(INVOICE_READ)),
    db: Session = Depends(get_db),
):
    """List invoices. Requires invoice.read."""
    svc = InvoiceService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        party_id=party_id,
        status=status,
        invoice_type=invoice_type,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return InvoiceListResponse(
        invoices=[InvoiceListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: UUID,
    current_user: CurrentUser = Depends(require_permission(INVOICE_READ)),
    db: Session = Depends(get_db),
):
    """Get invoice by ID. Requires invoice.read."""
    svc = InvoiceService(db)
    data = svc.get_by_id(invoice_id, current_user.organization_id)
    return InvoiceResponse.model_validate(data)


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: UUID,
    body: InvoiceUpdate,
    current_user: CurrentUser = Depends(require_permission(INVOICE_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update invoice. Requires invoice.update."""
    svc = InvoiceService(db)
    data = svc.update(
        invoice_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return InvoiceResponse.model_validate(data)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: UUID,
    current_user: CurrentUser = Depends(require_permission(INVOICE_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete invoice. Requires invoice.update."""
    svc = InvoiceService(db)
    svc.delete(invoice_id, current_user.organization_id)
    return None


# @router.post("/{invoice_id}/confirm", response_model=InvoiceResponse)
# async def confirm_invoice(
#     invoice_id: UUID,
#     current_user: CurrentUser = Depends(require_permission(INVOICE_UPDATE)),
#     db: Session = Depends(get_db),
# ):
#     """
#     Confirm/submit an invoice.
    
#     Changes the invoice status from "draft" to "pending" and creates journal entries
#     for accounts receivable/payable and revenue/expense recognition.
    
#     **Requires:** invoice.update permission
    
#     **Path Parameters:**
#     - **invoice_id**: UUID of the invoice to confirm
    
#     **Behavior:**
#     - Updates invoice status to "pending" (submitted/confirmed, awaiting payment)
#     - Sets submitted_at timestamp to current datetime
#     - Sets outstanding_amount to grand_total
#     - Creates journal entry:
#       - Sales Invoice: Debit AR, Credit Revenue
#       - Purchase Invoice: Debit Expense, Credit AP
    
#     **Validation:**
#     - Invoice must be in "draft" status
#     - Invoice type must be "Sales" or "Purchase"
#     - Grand total must be greater than zero
#     - Required default accounts must be configured:
#       - Sales: accounts_receivable, sales_revenue
#       - Purchase: purchase_expense, accounts_payable
    
#     **Error Responses:**
#     - 400: Invoice not in draft status, missing default accounts, or invalid data
#     - 404: Invoice not found
#     - 403: Insufficient permissions
    
#     **Transaction Behavior:**
#     - Operation is atomic: invoice update and journal entry creation succeed together or fail together
#     - If journal entry creation fails, invoice status change is rolled back
    
#     **Returns:** Updated invoice with submitted_at and outstanding_amount set
#     """
#     svc = InvoiceService(db)
#     data = svc.confirm_invoice(invoice_id, current_user.organization_id, current_user.id)
#     return InvoiceResponse.model_validate(data)
