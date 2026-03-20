"""Schemas for public/marketing endpoints"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field


# ── Contact Us ──────────────────────────────────────────────────────────────

class ContactUsRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    mobile: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=255)
    message: str = Field(..., min_length=10)


# ── Career Application ───────────────────────────────────────────────────────

class CareerApplicationRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    mobile: Optional[str] = Field(None, max_length=20)
    position: str = Field(..., max_length=255)
    cover_letter: Optional[str] = None
    resume_url: Optional[str] = Field(None, max_length=500)


# ── Schedule Demo ────────────────────────────────────────────────────────────

class ScheduleDemoRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    mobile: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=255)
    preferred_date: Optional[str] = Field(None, description="ISO date string e.g. 2026-04-01")
    notes: Optional[str] = None


# ── Newsletter Subscribe ─────────────────────────────────────────────────────

class NewsletterSubscribeRequest(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(None, max_length=255)


# ── Request Callback ─────────────────────────────────────────────────────────

class RequestCallbackRequest(BaseModel):
    name: str = Field(..., max_length=255)
    mobile: str = Field(..., max_length=20)
    email: Optional[EmailStr] = None
    preferred_time: Optional[str] = Field(None, max_length=100,
                                           description="e.g. 'Morning', '10am-12pm'")
    notes: Optional[str] = None


# ── Shared Response ──────────────────────────────────────────────────────────

class PublicSubmissionResponse(BaseModel):
    id: str
    submission_type: str
    name: Optional[str]
    email: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
