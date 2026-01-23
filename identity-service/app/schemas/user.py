"""User related Pydantic schemas"""

from typing import Optional
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserBase(BaseModel):
    """Base user schema with common fields"""
    email: EmailStr
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    phone: Optional[str] = Field(None, max_length=20)


class UserCreate(UserBase):
    """Schema for creating a new user"""
    password: str = Field(..., min_length=8)


class UserResponse(UserBase):
    """Schema for user response"""
    id: UUID
    display_name: Optional[str] = None
    user_type: str
    status: str
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserListItem(BaseModel):
    """Schema for user in list response"""
    id: UUID
    email: EmailStr
    first_name: str
    last_name: str
    display_name: Optional[str] = None
    user_type: str
    status: str
    email_verified: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class PaginationMeta(BaseModel):
    """Pagination metadata"""
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_prev: bool


class UserListResponse(BaseModel):
    """Schema for paginated user list response"""
    users: list[UserListItem]
    pagination: PaginationMeta
