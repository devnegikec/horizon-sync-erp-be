"""Public / Marketing endpoints — no authentication required"""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.public_marketing import (
    ContactUsRequest,
    CareerApplicationRequest,
    ScheduleDemoRequest,
    NewsletterSubscribeRequest,
    RequestCallbackRequest,
    PublicSubmissionResponse,
)
from app.services.public_marketing_service import PublicMarketingService

router = APIRouter()


def _get_ip(request: Request) -> str | None:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ── Contact Us ───────────────────────────────────────────────────────────────

@router.post(
    "/contact-us",
    response_model=PublicSubmissionResponse,
    status_code=201,
    summary="Submit a contact-us enquiry",
)
async def contact_us(
    data: ContactUsRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    svc = PublicMarketingService(db)
    record = await svc.contact_us(data, _get_ip(request))
    return record


# ── Career Application ────────────────────────────────────────────────────────

@router.post(
    "/career",
    response_model=PublicSubmissionResponse,
    status_code=201,
    summary="Submit a career / job application",
)
async def career_application(
    data: CareerApplicationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    svc = PublicMarketingService(db)
    record = await svc.career_application(data, _get_ip(request))
    return record


# ── Schedule Demo ─────────────────────────────────────────────────────────────

@router.post(
    "/schedule-demo",
    response_model=PublicSubmissionResponse,
    status_code=201,
    summary="Request a product demo",
)
async def schedule_demo(
    data: ScheduleDemoRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    svc = PublicMarketingService(db)
    record = await svc.schedule_demo(data, _get_ip(request))
    return record


# ── Newsletter Subscribe ──────────────────────────────────────────────────────

@router.post(
    "/newsletter/subscribe",
    response_model=PublicSubmissionResponse,
    status_code=201,
    summary="Subscribe to the newsletter",
)
async def newsletter_subscribe(
    data: NewsletterSubscribeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    svc = PublicMarketingService(db)
    record = await svc.newsletter_subscribe(data, _get_ip(request))
    return record


# ── Request Callback ──────────────────────────────────────────────────────────

@router.post(
    "/request-callback",
    response_model=PublicSubmissionResponse,
    status_code=201,
    summary="Request a sales callback",
)
async def request_callback(
    data: RequestCallbackRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    svc = PublicMarketingService(db)
    record = await svc.request_callback(data, _get_ip(request))
    return record
