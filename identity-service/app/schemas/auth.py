"""Authentication related Pydantic schemas"""

from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class DeviceInfo(BaseModel):
    """Device information schema"""

    device_name: str | None = None
    device_type: str | None = None
    os_info: str | None = None
    browser_info: str | None = None


class LoginRequest(BaseModel):
    """Schema for login request"""

    email: EmailStr
    password: str
    device_info: DeviceInfo | None = None


class TokenResponse(BaseModel):
    """Schema for token response"""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    """Schema for refresh token request"""

    refresh_token: str


class RefreshTokenResponse(BaseModel):
    """Schema for refresh token response"""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LogoutRequest(BaseModel):
    """Schema for logout request"""

    refresh_token: str


class LogoutResponse(BaseModel):
    """Schema for logout response"""

    message: str


class RegisterResponse(BaseModel):
    """Schema for registration response"""

    user: UserResponse
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class ForgotPasswordRequest(BaseModel):
    """Schema for forgot password request"""

    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """Schema for forgot password response"""

    message: str


class ResetPasswordRequest(BaseModel):
    """Schema for reset password request"""

    token: str
    new_password: str


class ResetPasswordResponse(BaseModel):
    """Schema for reset password response"""

    message: str
