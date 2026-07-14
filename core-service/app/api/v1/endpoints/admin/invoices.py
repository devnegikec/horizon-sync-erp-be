"""Admin invoice management endpoints.

GET    /admin/invoices          — cross-org paginated list with org_id, status, date range filters
GET    /admin/invoices/{id}     — detail with line items + payment history
POST   /admin/invoices          — create invoice in specified org
POST   /admin/invoices/{id}/send — send invoice via email
POST   /admin/invoices/{id}/mark-paid — mark invoice as paid
POST   /admin/invoices/{id}/create-payment — create payment entry
"""

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.authorization import SYSTEM_ADMIN_BILLING_CREATE, SYSTEM_ADMIN_BILLING_READ
from app.dependencies import CurrentUser, require_permission
from app.schemas.admin_invoice import AdminInvoiceListResponse
from app.schemas.invoice import InvoiceCreate, InvoiceResponse
from app.schemas.invoice_payment import InvoicePaymentRequest, MarkInvoicePaidRequest
from app.services.admin_invoice_service import AdminInvoiceService

router = APIRouter()
security = HTTPBearer()
logger = logging.getLogger(__name__)


@router.get("", response_model=AdminInvoiceListResponse)
async def list_invoices(
    organization_id: UUID | None = Query(None, description="Filter by organization"),
    status: str | None = Query(None, description="Filter by invoice status"),
    date_from: datetime | None = Query(None, description="Filter invoices from this date"),
    date_to: datetime | None = Query(None, description="Filter invoices up to this date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_READ)),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> AdminInvoiceListResponse:
    """Return a paginated list of invoices from customer organizations linked to the master organization."""
    service = AdminInvoiceService(db, token=credentials.credentials)
    return await service.list_invoices(
        organization_id=organization_id,
        status_filter=status,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
        current_user_org=current_user.organization_id,
    )


@router.get("/{invoice_id}")
async def get_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_READ)),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Return full invoice detail with line items and payment history."""
    service = AdminInvoiceService(db, token=credentials.credentials)
    return service.get_invoice(invoice_id)


@router.post("", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    body: InvoiceCreate,
    organization_id: UUID = Query(..., description="Organization to create the invoice in"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_CREATE)),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> InvoiceResponse:
    """Create an invoice in the specified organization."""
    service = AdminInvoiceService(db, token=credentials.credentials)
    data = service.create_invoice(
        data=body.model_dump(),
        organization_id=organization_id,
        user_id=current_user.id,
    )
    return InvoiceResponse.model_validate(data)


@router.post("/{invoice_id}/send")
async def send_invoice(
    invoice_id: UUID,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_CREATE)),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Send an invoice to the party's email and update status to pending."""
    service = AdminInvoiceService(db, token=credentials.credentials)
    return await service.send_invoice(invoice_id, current_user.id)


@router.post("/{invoice_id}/mark-paid")
async def mark_invoice_paid(
    invoice_id: UUID,
    payment_data: MarkInvoicePaidRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_CREATE)),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Mark an invoice as paid by updating its status and outstanding amount."""
    service = AdminInvoiceService(db, token=credentials.credentials)
    return await service.mark_invoice_paid(invoice_id, payment_data.model_dump(), current_user.id)


@router.post("/{invoice_id}/create-payment")
async def create_payment_from_invoice(
    invoice_id: UUID,
    payment_data: InvoicePaymentRequest,
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_CREATE)),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Create a payment entry from an invoice."""
    try:
        logger.info(f"=== Payment endpoint called ===")
        logger.info(f"Invoice ID: {invoice_id}")
        logger.info(f"Raw payment data: {payment_data}")
        logger.info(f"Payment data model dump: {payment_data.model_dump()}")
        logger.info(f"Current user: {current_user}")
        
        service = AdminInvoiceService(db, token=credentials.credentials)
        result = await service.create_payment_from_invoice(invoice_id, payment_data.model_dump(), current_user.id)
        
        logger.info(f"Payment creation successful: {result}")
        return result
        
    except HTTPException as he:
        logger.error(f"HTTP Exception in payment endpoint: {he.status_code} - {he.detail}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in payment endpoint: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.post("/{invoice_id}/capture-payment-intent") 
async def capture_payment_intent(
    invoice_id: UUID,
    capture_data: dict,  # TODO: Create proper schema for payment intent capture
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_CREATE)),
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Capture payment through payment gateway (FUTURE IMPLEMENTATION).
    
    This would integrate with Stripe/PayPal/etc. to capture authorized payments.
    Currently returns not implemented error.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Payment gateway integration not implemented yet. Use manual payment capture via /create-payment endpoint."
    )


@router.post("/debug-payment-data")
async def debug_payment_data(
    request_data: dict,
) -> dict:
    """Debug endpoint to see raw payment data format."""
    logger.info(f"=== Debug endpoint called ===")
    logger.info(f"Raw request data: {request_data}")
    logger.info(f"Data type: {type(request_data)}")
    logger.info(f"Data keys: {list(request_data.keys()) if isinstance(request_data, dict) else 'Not a dict'}")
    
    try:
        # Try to validate with our schema
        payment_request = InvoicePaymentRequest(**request_data)
        return {
            "success": True,
            "parsed_data": payment_request.model_dump(),
            "message": "Data validation successful"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "raw_data": request_data,
            "message": "Data validation failed"
        }
