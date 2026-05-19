"""Schemas for public/marketing endpoints"""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

# ── Contact Us ──────────────────────────────────────────────────────────────


class ContactUsRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    mobile: str | None = Field(None, max_length=20)
    company: str | None = Field(None, max_length=255)
    message: str = Field(..., min_length=10)


# ── Career Application ───────────────────────────────────────────────────────


class CareerApplicationRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    mobile: str | None = Field(None, max_length=20)
    position: str = Field(..., max_length=255)
    cover_letter: str | None = None
    resume_url: str | None = Field(None, max_length=500)


# ── Schedule Demo ────────────────────────────────────────────────────────────


class ScheduleDemoRequest(BaseModel):
    name: str = Field(..., max_length=255)
    email: EmailStr
    mobile: str | None = Field(None, max_length=20)
    company: str | None = Field(None, max_length=255)
    preferred_date: str | None = Field(
        None, description="ISO date string e.g. 2026-04-01"
    )
    notes: str | None = None


# ── Newsletter Subscribe ─────────────────────────────────────────────────────


class NewsletterSubscribeRequest(BaseModel):
    email: EmailStr
    name: str | None = Field(None, max_length=255)


# ── Request Callback ─────────────────────────────────────────────────────────


class RequestCallbackRequest(BaseModel):
    name: str = Field(..., max_length=255)
    mobile: str = Field(..., max_length=20)
    email: EmailStr | None = None
    preferred_time: str | None = Field(
        None, max_length=100, description="e.g. 'Morning', '10am-12pm'"
    )
    notes: str | None = None


# ── Shared Response ──────────────────────────────────────────────────────────


class PublicSubmissionResponse(BaseModel):
    id: str
    submission_type: str
    name: str | None
    email: str | None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
