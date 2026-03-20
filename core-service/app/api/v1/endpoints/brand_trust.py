"""Brand Trust Assessment endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.schemas.brand_trust import (
    AssessmentListResponse,
    AssessmentReportResponse,
    AssessmentResponse,
    BrandIndustryResponse,
    BrandTrustQuestionResponse,
    SendReportEmailRequest,
    StartAssessmentRequest,
    SubmitAssessmentRequest,
)
from app.services.brand_trust_service import BrandTrustService

router = APIRouter()


def get_service(db: Session = Depends(get_db)) -> BrandTrustService:
    return BrandTrustService(db)


# ── Industries ────────────────────────────────────────────────────────────────

@router.get(
    "/industries",
    response_model=list[BrandIndustryResponse],
    summary="List brand industries",
)
def list_industries(service: BrandTrustService = Depends(get_service)):
    """Public — no auth required. Used to populate the industry selector."""
    return service.list_industries()


# ── Questions ─────────────────────────────────────────────────────────────────

@router.get(
    "/questions",
    response_model=list[BrandTrustQuestionResponse],
    summary="Get assessment questions",
)
def get_questions(
    industry_id: UUID | None = Query(None, description="Filter questions by industry"),
    service: BrandTrustService = Depends(get_service),
):
    """Public — returns questions for the given industry + universal questions."""
    return service.get_questions(industry_id)


# ── Assessments ───────────────────────────────────────────────────────────────

@router.post(
    "/start",
    response_model=AssessmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new brand trust assessment",
)
def start_assessment(
    data: StartAssessmentRequest,
    service: BrandTrustService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    return service.start_assessment(data, org_id, user_id)


@router.get(
    "",
    response_model=AssessmentListResponse,
    summary="List assessments for the organization",
)
def list_assessments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="in_progress | submitted | scored"),
    service: BrandTrustService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.list_assessments(org_id, page, page_size, status)


@router.post(
    "/{assessment_id}/submit",
    response_model=AssessmentResponse,
    summary="Submit answers and score the assessment",
)
def submit_assessment(
    assessment_id: UUID,
    data: SubmitAssessmentRequest,
    service: BrandTrustService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.submit_assessment(assessment_id, data, org_id)


# ── Report ────────────────────────────────────────────────────────────────────

@router.get(
    "/{assessment_id}/report",
    response_model=AssessmentReportResponse,
    summary="Get the assessment report with scores and answers",
)
def get_report(
    assessment_id: UUID,
    service: BrandTrustService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.get_report(assessment_id, org_id)


# ── PDF ───────────────────────────────────────────────────────────────────────

@router.get(
    "/{assessment_id}/pdf",
    summary="Get PDF report URL (stub — returns placeholder URL)",
)
def get_pdf(
    assessment_id: UUID,
    service: BrandTrustService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    return service.get_pdf_url(assessment_id, org_id)


# ── Email ─────────────────────────────────────────────────────────────────────

@router.post(
    "/{assessment_id}/send-email",
    summary="Email the brand trust report to a recipient",
)
async def send_report_email(
    assessment_id: UUID,
    req: SendReportEmailRequest,
    service: BrandTrustService = Depends(get_service),
    current_user: dict = Depends(get_current_user),
):
    org_id = UUID(current_user["organization_id"])
    user_id = UUID(current_user["user_id"])
    return await service.send_report_email(assessment_id, req, org_id, user_id)
