"""QR Credits API endpoints — balance and usage queries."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.qr_credit import QRCreditBalanceResponse
from app.services.credit_service import CreditService

router = APIRouter()


@router.get(
    "/balance",
    response_model=QRCreditBalanceResponse,
    summary="Get QR credit balance for current organization",
)
def get_credit_balance(
    current_user: CurrentUser = Depends(require_permission("qr_product.read")),
    db: Session = Depends(get_db),
):
    """Returns total, used, and remaining QR generation credits."""
    svc = CreditService(db)
    balance = svc.repo.get_balance(current_user.organization_id)

    if balance is None:
        return QRCreditBalanceResponse(
            total_credits=0,
            used_credits=0,
            balance_credits=0,
        )

    return QRCreditBalanceResponse.model_validate(balance)
