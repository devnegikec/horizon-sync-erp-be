"""Authentication related Pydantic schemas"""

from typing import Optional
from pydantic import BaseModel, EmailStr

from app.schemas.user import UserResponse


class DeviceInfo(BaseModel):
    """Device information schema"""
    device_name: Optional[str] = None
    device_type: Optional[str] = None
    os_info: Optional[str] = None
    browser_info: Optional[str] = None


class LoginRequest(BaseModel):
    """Schema for login request"""
    email: EmailStr
    password: str
    device_info: Optional[DeviceInfo] = None


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
