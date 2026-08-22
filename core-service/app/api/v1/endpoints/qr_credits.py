"""Organization QR-credit balance, ledger, and System Admin allocation APIs."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_admin, require_permission
from app.schemas.qr_credit import (
    QRCreditAddRequest,
    QRCreditBalanceResponse,
    QRCreditLedgerItem,
    QRCreditLedgerResponse,
)
from app.services.admin_organization_service import AdminOrganizationService
from app.services.credit_service import CreditService

router = APIRouter()
security = HTTPBearer()


def _balance_response(organization_id: UUID, balance) -> QRCreditBalanceResponse:
    if balance is None:
        return QRCreditBalanceResponse(
            organization_id=organization_id,
            total_credits=0,
            used_credits=0,
            reserved_credits=0,
            balance_credits=0,
            updated_at=None,
        )
    return QRCreditBalanceResponse.model_validate(balance)


def _ledger_response(
    service: CreditService,
    organization_id: UUID,
    page: int,
    page_size: int,
) -> QRCreditLedgerResponse:
    transactions, pagination = service.list_ledger(
        organization_id, page, page_size
    )
    return QRCreditLedgerResponse(
        transactions=[
            QRCreditLedgerItem.model_validate(transaction)
            for transaction in transactions
        ],
        pagination=pagination,
    )


@router.get("/balance", response_model=QRCreditBalanceResponse)
async def get_organization_credit_balance(
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    service = CreditService(db)
    return _balance_response(
        current_user.organization_id,
        service.get_balance(current_user.organization_id),
    )


@router.get("/ledger", response_model=QRCreditLedgerResponse)
async def get_organization_credit_ledger(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    return _ledger_response(
        CreditService(db),
        current_user.organization_id,
        page,
        page_size,
    )


@router.get(
    "/organizations/{organization_id}",
    response_model=QRCreditBalanceResponse,
)
async def get_admin_organization_credit_balance(
    organization_id: UUID,
    _current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = CreditService(db)
    return _balance_response(
        organization_id,
        service.get_balance(organization_id),
    )


@router.get(
    "/organizations/{organization_id}/ledger",
    response_model=QRCreditLedgerResponse,
)
async def get_admin_organization_credit_ledger(
    organization_id: UUID,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    _current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    return _ledger_response(
        CreditService(db),
        organization_id,
        page,
        page_size,
    )


@router.post(
    "/organizations/{organization_id}/add",
    response_model=QRCreditBalanceResponse,
    status_code=status.HTTP_200_OK,
)
async def add_admin_organization_credits(
    organization_id: UUID,
    data: QRCreditAddRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: CurrentUser = Depends(require_admin),
    db: Session = Depends(get_db),
):
    await AdminOrganizationService(
        db, token=credentials.credentials
    ).get_organization(organization_id)
    balance = CreditService(db).add_credits(
        organization_id=organization_id,
        amount=data.amount,
        reason=data.reason,
        reference_id=data.reference_id,
        user_id=current_user.id,
    )
    return _balance_response(organization_id, balance)
