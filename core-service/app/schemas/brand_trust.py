"""Pydantic schemas for Brand Trust Assessment module"""

from datetime import datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# ── Industries ────────────────────────────────────────────────────────────────

class BrandIndustryResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool

    model_config = {"from_attributes": True}


# ── Questions ─────────────────────────────────────────────────────────────────

class BrandTrustQuestionResponse(BaseModel):
    id: UUID
    industry_id: UUID | None
    section: str
    question_text: str
    question_type: str
    options: list[str] | None
    weight: Decimal
    order_index: int

    model_config = {"from_attributes": True}


# ── Assessment ────────────────────────────────────────────────────────────────

class StartAssessmentRequest(BaseModel):
    industry_id: UUID | None = None
    notes: str | None = None


class AssessmentResponse(BaseModel):
    id: UUID
    organization_id: UUID
    industry_id: UUID | None
    status: str
    overall_score: Decimal | None
    score_breakdown: dict[str, Any] | None
    report_url: str | None
    notes: str | None
    submitted_at: datetime | None
    created_at: datetime
    questions: list[BrandTrustQuestionResponse] = []

    model_config = {"from_attributes": True}


class AssessmentListResponse(BaseModel):
    assessments: list[AssessmentResponse]
    pagination: dict[str, Any]


# ── Submit ────────────────────────────────────────────────────────────────────

class AnswerItem(BaseModel):
    question_id: UUID
    answer_value: str = Field(..., description="Rating 1-5, 'yes'/'no', free text, or option")


class SubmitAssessmentRequest(BaseModel):
    answers: list[AnswerItem] = Field(..., min_length=1)


# ── Report ────────────────────────────────────────────────────────────────────

class SectionScore(BaseModel):
    section: str
    score: Decimal
    max_score: Decimal
    percentage: Decimal


class AssessmentReportResponse(BaseModel):
    assessment_id: UUID
    organization_id: UUID
    industry_name: str | None
    overall_score: Decimal
    grade: str                          # A / B / C / D / F
    section_scores: list[SectionScore]
    submitted_at: datetime | None
    answers: list[dict[str, Any]]


# ── Email ─────────────────────────────────────────────────────────────────────

class SendReportEmailRequest(BaseModel):
    to: str = Field(..., description="Recipient email address")
    cc: list[str] | None = None
    message: str | None = None
