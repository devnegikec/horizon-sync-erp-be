"""Customer-facing subscription, credit and billing endpoints (``/account``)."""

import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.models.invoice import Invoice
from app.schemas.subscription import (
    AccountInvoiceListResponse,
    CreditBatchListResponse,
    CreditLedgerListResponse,
    CreditsResponse,
    ExpirationsResponse,
    SubscriptionResponse,
    TopupOrderRequest,
    TopupOrderResponse,
    TopupQuoteRequest,
    TopupQuoteResponse,
)
from app.services.credit_engine_service import CreditEngineService
from app.services.subscription_service import SubscriptionService

router = APIRouter()

ACCOUNT_INVOICE_TYPES = ("subscription", "setup_fee", "overage", "addon")


def _org(current_user: CurrentUser) -> UUID:
    # ``get_current_user`` guarantees an organization for non-system users.
    return current_user.organization_id


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Current plan, renewal and payment status",
)
def get_account_subscription(
    current_user: CurrentUser = Depends(
        require_permission("subscription.read", "qr_product.read")
    ),
    db: Session = Depends(get_db),
):
    return SubscriptionService(db).get_snapshot(_org(current_user))


@router.get(
    "/credits",
    response_model=CreditsResponse,
    summary="Available, reserved and expiring credits",
)
def get_account_credits(
    current_user: CurrentUser = Depends(
        require_permission("subscription.read", "qr_product.read")
    ),
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).credits_summary(_org(current_user))


@router.get(
    "/credits/batches",
    response_model=CreditBatchListResponse,
    summary="Credit batch history",
)
def list_account_credit_batches(
    status_filter: str | None = Query(None, alias="status"),
    expiring_before: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(
        require_permission("subscription.read", "qr_product.read")
    ),
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).list_batches(
        _org(current_user),
        batch_status=status_filter,
        expiring_before=expiring_before,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/credits/ledger",
    response_model=CreditLedgerListResponse,
    summary="Credit ledger entries",
)
def list_account_credit_ledger(
    entry_type: str | None = Query(None, alias="type"),
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    operation_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(
        require_permission("subscription.read", "qr_product.read")
    ),
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).list_ledger(
        _org(current_user),
        entry_type=entry_type,
        from_date=from_date,
        to_date=to_date,
        operation_id=operation_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/credits/expirations",
    response_model=ExpirationsResponse,
    summary="Credits expiring in the next 30 / 60 / 90 days",
)
def get_account_credit_expirations(
    current_user: CurrentUser = Depends(
        require_permission("subscription.read", "qr_product.read")
    ),
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).expirations(_org(current_user))


@router.get(
    "/invoices",
    response_model=AccountInvoiceListResponse,
    summary="Subscription invoice history",
)
def list_account_invoices(
    status_filter: str | None = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(
        require_permission("subscription.read", "qr_product.read")
    ),
    db: Session = Depends(get_db),
):
    query = db.query(Invoice).filter(
        Invoice.organization_id == _org(current_user),
        Invoice.invoice_type.in_(ACCOUNT_INVOICE_TYPES),
    )
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    total = query.count()
    invoices = (
        query.order_by(Invoice.posting_date.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "items": [
            {
                "id": invoice.id,
                "invoice_no": invoice.invoice_no,
                "invoice_type": invoice.invoice_type,
                "posting_date": invoice.posting_date,
                "due_date": invoice.due_date,
                "status": invoice.status,
                "subtotal": invoice.net_total or 0,
                "tax_total": invoice.total_tax or 0,
                "grand_total": invoice.grand_total or 0,
                "outstanding_amount": invoice.outstanding_amount or 0,
                "currency": invoice.currency,
                "download_url": None,
            }
            for invoice in invoices
        ],
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": max(1, (total + page_size - 1) // page_size),
        },
    }


@router.post(
    "/topups/quotes",
    response_model=TopupQuoteResponse,
    summary="Quote a credit top-up (price, tax, credits, expiry)",
)
def create_topup_quote(
    payload: TopupQuoteRequest,
    current_user: CurrentUser = Depends(
        require_permission("billing.topup", "billing.manage", "qr_product.manage")
    ),
    db: Session = Depends(get_db),
):
    quote, _subscription = CreditEngineService(db).create_topup_quote(
        _org(current_user), payload.credits
    )
    return {
        "quote_id": quote.id,
        "credits": quote.credits,
        "subtotal": quote.subtotal,
        "tax_amount": quote.tax_amount,
        "total": quote.amount,
        "currency": quote.currency,
        "expires_at": quote.expires_at,
        "credit_expires_at": quote.credit_expires_at,
    }


@router.post(
    "/topups/orders",
    response_model=TopupOrderResponse,
    status_code=201,
    summary="Create an idempotent top-up checkout order",
)
def create_topup_order(
    payload: TopupOrderRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(
        require_permission("billing.topup", "billing.manage", "qr_product.manage")
    ),
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).create_topup_order(
        _org(current_user),
        payload.quote_id,
        idempotency_key,
        payload.provider,
    )


@router.get(
    "/topups/orders/{order_id}",
    response_model=TopupOrderResponse,
    summary="Poll a top-up order status",
)
def get_topup_order(
    order_id: UUID,
    current_user: CurrentUser = Depends(
        require_permission("billing.topup", "billing.manage", "qr_product.manage")
    ),
    db: Session = Depends(get_db),
):
    service = CreditEngineService(db)
    order = service.credit_repo.get_order(_org(current_user), order_id)
    if order is None:
        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "ORDER_NOT_FOUND", "message": "Top-up order not found"},
        )
    return service._order_dict(order)


@router.get(
    "/reports/credits.csv",
    summary="Export the credit ledger as CSV",
)
def export_credit_report(
    from_date: datetime | None = Query(None),
    to_date: datetime | None = Query(None),
    current_user: CurrentUser = Depends(
        require_permission("subscription.read", "qr_product.read")
    ),
    db: Session = Depends(get_db),
):
    org_id = _org(current_user)
    service = CreditEngineService(db)

    def rows():
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(
            [
                "entry_id",
                "batch_id",
                "type",
                "quantity",
                "balance_after",
                "operation_id",
                "reference_type",
                "reference_id",
                "reason",
                "occurred_at",
            ]
        )
        yield buffer.getvalue()
        buffer.seek(0)
        buffer.truncate(0)
        # Stream every matching row; never silently cap the export.
        for entry in service.credit_repo.iter_ledger(
            org_id, from_date=from_date, to_date=to_date
        ):
            writer.writerow(
                [
                    entry.id,
                    entry.batch_id,
                    entry.type,
                    entry.qty,
                    entry.balance_after,
                    entry.operation_id,
                    entry.reference_type,
                    entry.reference_id,
                    entry.reason,
                    entry.occurred_at.isoformat(),
                ]
            )
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

    return StreamingResponse(
        rows(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="credit-ledger.csv"'},
    )
