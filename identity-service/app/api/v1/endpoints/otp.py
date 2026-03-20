"""OTP endpoints — send and verify email/mobile OTPs"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_client_ip
from app.schemas.otp import (
    OTPResponse,
    OTPVerifyResponse,
    SendEmailOTPRequest,
    SendMobileOTPRequest,
    VerifyEmailOTPRequest,
    VerifyMobileOTPRequest,
)
from app.services.otp_service import OTPService

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Email OTP
# ---------------------------------------------------------------------------


@router.post(
    "/otp/email/send",
    response_model=OTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Send email OTP",
    description=(
        "Generates a 6-digit OTP and sends it to the given email address. "
        "Any previously active OTP for this email is invalidated. "
        "OTP expires in 10 minutes."
    ),
)
async def send_email_otp(
    body: SendEmailOTPRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)
    otp_service = OTPService(db)
    otp_service.send_email_otp(body.email, ip_address=ip)
    return OTPResponse(message="OTP sent to email address")


@router.post(
    "/otp/email/verify",
    response_model=OTPVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify email OTP",
    description="Verify the 6-digit OTP sent to an email address.",
)
async def verify_email_otp(
    body: VerifyEmailOTPRequest,
    db: Session = Depends(get_db),
):
    otp_service = OTPService(db)
    try:
        otp_service.verify_otp(body.email, "email", body.otp_code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return OTPVerifyResponse(message="Email OTP verified successfully", verified=True)


# ---------------------------------------------------------------------------
# Mobile OTP
# ---------------------------------------------------------------------------


@router.post(
    "/otp/mobile/send",
    response_model=OTPResponse,
    status_code=status.HTTP_200_OK,
    summary="Send mobile OTP",
    description=(
        "Generates a 6-digit OTP and sends it to the given mobile number. "
        "Any previously active OTP for this number is invalidated. "
        "OTP expires in 10 minutes."
    ),
)
async def send_mobile_otp(
    body: SendMobileOTPRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)
    otp_service = OTPService(db)
    otp_service.send_mobile_otp(body.mobile, ip_address=ip)
    return OTPResponse(message="OTP sent to mobile number")


@router.post(
    "/otp/mobile/verify",
    response_model=OTPVerifyResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify mobile OTP",
    description="Verify the 6-digit OTP sent to a mobile number.",
)
async def verify_mobile_otp(
    body: VerifyMobileOTPRequest,
    db: Session = Depends(get_db),
):
    otp_service = OTPService(db)
    try:
        otp_service.verify_otp(body.mobile, "mobile", body.otp_code)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return OTPVerifyResponse(message="Mobile OTP verified successfully", verified=True)
