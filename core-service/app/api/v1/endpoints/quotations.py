"""Quotations API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.orm import Session

from app.core.authorization import QUOTATION_CREATE, QUOTATION_READ, QUOTATION_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.quotation import (
    ConvertToSalesOrderResponse,
    QuotationCreate,
    QuotationListItem,
    QuotationListResponse,
    QuotationResponse,
    QuotationStatusUpdate,
    QuotationUpdate,
)
from app.services.organization_client import organization_client
from app.services.quotation_service import QuotationService
from app.utils.naming_series import extract_number_from_document_no

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
async def create_quotation(
    body: QuotationCreate,
    request: Request,
    current_user: CurrentUser = Depends(require_permission(QUOTATION_CREATE)),
    db: Session = Depends(get_db),
):
    """Create quotation. Requires quotation.create."""
    svc = QuotationService(db)
    data = svc.create(body.model_dump(), current_user.organization_id, current_user.id)

    # Update naming series in identity service (async, non-blocking)
    # Extract the number from quotation_no (e.g., "QT-0035" -> 35)
    if data.get("quotation_no"):
        current_number = extract_number_from_document_no(data["quotation_no"])

        if current_number is not None:
            # Get the auth token from request headers
            auth_header = request.headers.get("Authorization", "")

            try:
                # Update naming series asynchronously
                await organization_client.update_naming_series(
                    organization_id=current_user.organization_id,
                    document_type="quotation",
                    current_number=current_number,
                    auth_token=auth_header.replace("Bearer ", ""),
                )
            except Exception as e:
                # Log error but don't fail the quotation creation
                logger.error(
                    f"Failed to update naming series for quotation {data['quotation_no']}: {e}"
                )

    return QuotationResponse.model_validate(data)


@router.get("", response_model=QuotationListResponse)
async def list_quotations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    customer_id: UUID | None = None,
    status: str | None = Query(
        None, pattern="^(draft|sent|accepted|rejected|expired)$"
    ),
    sort_by: str = Query("quotation_date"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(require_permission(QUOTATION_READ)),
    db: Session = Depends(get_db),
):
    """List quotations. Requires quotation.read."""
    svc = QuotationService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        customer_id=customer_id,
        status=status,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return QuotationListResponse(
        quotations=[QuotationListItem.model_validate(x) for x in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{quotation_id}", response_model=QuotationResponse)
async def get_quotation(
    quotation_id: UUID,
    current_user: CurrentUser = Depends(require_permission(QUOTATION_READ)),
    db: Session = Depends(get_db),
):
    """Get quotation by ID. Requires quotation.read."""
    svc = QuotationService(db)
    data = svc.get_by_id(quotation_id, current_user.organization_id)
    return QuotationResponse.model_validate(data)


@router.put("/{quotation_id}", response_model=QuotationResponse)
async def update_quotation(
    quotation_id: UUID,
    body: QuotationUpdate,
    current_user: CurrentUser = Depends(require_permission(QUOTATION_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update quotation. Requires quotation.update."""
    svc = QuotationService(db)
    data = svc.update(
        quotation_id,
        body.model_dump(exclude_unset=True),
        current_user.organization_id,
        current_user.id,
    )
    return QuotationResponse.model_validate(data)


@router.delete("/{quotation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quotation(
    quotation_id: UUID,
    current_user: CurrentUser = Depends(require_permission(QUOTATION_UPDATE)),
    db: Session = Depends(get_db),
):
    """Delete quotation. Requires quotation.update."""
    svc = QuotationService(db)
    svc.delete(quotation_id, current_user.organization_id)
    return None


@router.put("/{quotation_id}/status", response_model=QuotationResponse)
async def update_quotation_status(
    quotation_id: UUID,
    body: QuotationStatusUpdate,
    current_user: CurrentUser = Depends(require_permission(QUOTATION_UPDATE)),
    db: Session = Depends(get_db),
):
    """Update quotation status. Requires quotation.update."""
    svc = QuotationService(db)
    data = svc.update_status(
        quotation_id,
        body.status,
        current_user.organization_id,
        current_user.id,
    )
    return QuotationResponse.model_validate(data)


@router.post(
    "/{quotation_id}/convert-to-sales-order",
    response_model=ConvertToSalesOrderResponse,
    status_code=status.HTTP_201_CREATED,
)
async def convert_quotation_to_sales_order(
    quotation_id: UUID,
    current_user: CurrentUser = Depends(require_permission(QUOTATION_UPDATE)),
    db: Session = Depends(get_db),
):
    """Convert quotation to sales order. Requires quotation.update."""
    svc = QuotationService(db)
    sales_order = svc.convert_to_sales_order(
        quotation_id,
        current_user.organization_id,
        current_user.id,
    )
    return ConvertToSalesOrderResponse(
        sales_order_id=sales_order["id"],
        sales_order_no=sales_order["sales_order_no"],
    )
