"""OTP request/response schemas"""

from pydantic import BaseModel, EmailStr, field_validator


class SendEmailOTPRequest(BaseModel):
    email: EmailStr


class SendMobileOTPRequest(BaseModel):
    mobile: str

    @field_validator("mobile")
    @classmethod
    def validate_mobile(cls, v: str) -> str:
        digits = v.replace("+", "").replace("-", "").replace(" ", "")
        if not digits.isdigit() or not (7 <= len(digits) <= 15):
            raise ValueError("Invalid mobile number")
        return v


class VerifyEmailOTPRequest(BaseModel):
    email: EmailStr
    otp_code: str


class VerifyMobileOTPRequest(BaseModel):
    mobile: str
    otp_code: str


class OTPResponse(BaseModel):
    message: str
    # expires_in_minutes is safe to expose; the actual OTP is never returned
    expires_in_minutes: int = 10


class OTPVerifyResponse(BaseModel):
    message: str
    verified: bool
