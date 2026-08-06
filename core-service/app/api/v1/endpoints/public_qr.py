"""Public QR verification endpoint. No user authentication is required."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.qr_verification import (
    PublicQRVerifyRequest,
    PublicQRVerifyResponse,
)
from app.services.qr_verification_service import QRVerificationService

router = APIRouter()


@router.post(
    "/verify",
    response_model=PublicQRVerifyResponse,
    summary="Verify a public QSeal QR code",
    description=(
        "Resolves the globally unique serial, verifies its ECDSA signature, "
        "and applies the configured QR-type and activation rules."
    ),
)
async def verify_public_qr(
    data: PublicQRVerifyRequest,
    db: Session = Depends(get_db),
):
    result = QRVerificationService(db).verify(data)
    return PublicQRVerifyResponse(**result)
