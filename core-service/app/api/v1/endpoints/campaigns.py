"""Campaigns & Coupons API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user, require_permission
from app.schemas.campaign import (
    CampaignCreate,
    CampaignListResponse,
    CampaignResponse,
    CampaignUpdate,
    CouponListResponse,
    CouponRedeemRequest,
    CouponRedeemResponse,
    CouponResponse,
    CouponUnlockRequest,
    CouponUnlockResponse,
    CouponVerifyRequest,
    CouponVerifyResponse,
    FeedbackResponse,
    FeedbackSubmit,
    LeadCreate,
    LeadListResponse,
    LeadResponse,
    PrizeCreate,
    PrizeResponse,
)
from app.services.campaign_service import CampaignService

router = APIRouter()


# ── Campaigns ─────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create campaign",
)
async def create_campaign(
    data: CampaignCreate,
    current_user: CurrentUser = Depends(require_permission("campaign.create")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    campaign = svc.create_campaign(data, current_user.organization_id, current_user.id)
    return CampaignResponse.model_validate(campaign)


@router.get(
    "",
    response_model=CampaignListResponse,
    summary="List campaigns",
)
async def list_campaigns(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    campaign_type: str | None = Query(None, description="Filter by type (QR, WB, etc.)"),
    campaign_status: str | None = Query(None, description="A=active, I=inactive"),
    search: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("campaign.read")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    campaigns, pagination = svc.list_campaigns(
        current_user.organization_id, page, page_size,
        campaign_type, campaign_status, search,
    )
    return CampaignListResponse(
        campaigns=[CampaignResponse.model_validate(c) for c in campaigns],
        pagination=pagination,
    )


@router.get(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Get campaign",
)
async def get_campaign(
    campaign_id: UUID,
    current_user: CurrentUser = Depends(require_permission("campaign.read")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    return CampaignResponse.model_validate(
        svc.get_campaign(campaign_id, current_user.organization_id)
    )


@router.patch(
    "/{campaign_id}",
    response_model=CampaignResponse,
    summary="Update campaign",
)
async def update_campaign(
    campaign_id: UUID,
    data: CampaignUpdate,
    current_user: CurrentUser = Depends(require_permission("campaign.update")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    campaign = svc.update_campaign(
        campaign_id, data, current_user.organization_id, current_user.id
    )
    return CampaignResponse.model_validate(campaign)


@router.delete(
    "/{campaign_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete campaign",
)
async def delete_campaign(
    campaign_id: UUID,
    current_user: CurrentUser = Depends(require_permission("campaign.delete")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    svc.delete_campaign(campaign_id, current_user.organization_id, current_user.id)


# ── Prizes ────────────────────────────────────────────────────────────────────

@router.post(
    "/{campaign_id}/prizes",
    response_model=PrizeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add prize to campaign",
)
async def add_prize(
    campaign_id: UUID,
    data: PrizeCreate,
    current_user: CurrentUser = Depends(require_permission("campaign.update")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    prize = svc.add_prize(campaign_id, data, current_user.organization_id)
    return PrizeResponse.model_validate(prize)


@router.get(
    "/{campaign_id}/prizes",
    response_model=list[PrizeResponse],
    summary="List prizes for campaign",
)
async def list_prizes(
    campaign_id: UUID,
    current_user: CurrentUser = Depends(require_permission("campaign.read")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    prizes = svc.list_prizes(campaign_id, current_user.organization_id)
    return [PrizeResponse.model_validate(p) for p in prizes]


# ── Leads / CRM ───────────────────────────────────────────────────────────────

@router.post(
    "/leads",
    response_model=LeadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create lead (CRM)",
    description="Create a new lead/customer record, optionally linked to a campaign.",
)
async def create_lead(
    data: LeadCreate,
    current_user: CurrentUser = Depends(require_permission("campaign.create")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    lead = svc.create_lead(data, current_user.organization_id)
    return LeadResponse.model_validate(lead)


@router.get(
    "/leads",
    response_model=LeadListResponse,
    summary="List leads",
)
async def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    campaign_id: UUID | None = Query(None),
    search: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("campaign.read")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    leads, pagination = svc.list_leads(
        current_user.organization_id, page, page_size, campaign_id, search
    )
    return LeadListResponse(
        leads=[LeadResponse.model_validate(l) for l in leads],
        pagination=pagination,
    )


# ── Coupon Operations (public — no auth) ──────────────────────────────────────

@router.post(
    "/coupons/verify",
    response_model=CouponVerifyResponse,
    summary="Verify coupon",
    description="Public endpoint. Check if a coupon code is valid, used, or expired.",
)
async def verify_coupon(
    organization_id: UUID,
    req: CouponVerifyRequest,
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    result = svc.verify_coupon(organization_id, req)
    return CouponVerifyResponse(**result)


@router.post(
    "/coupons/redeem",
    response_model=CouponRedeemResponse,
    summary="Redeem coupon",
    description="Public endpoint. Mark a coupon as used and record redemption details.",
)
async def redeem_coupon(
    organization_id: UUID,
    req: CouponRedeemRequest,
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    result = svc.redeem_coupon(organization_id, req)
    return CouponRedeemResponse(**result)


@router.post(
    "/coupons/unlock",
    response_model=CouponUnlockResponse,
    summary="Unlock coupon",
    description="Public endpoint. Unlock a coupon and log the unlock event.",
)
async def unlock_coupon(
    organization_id: UUID,
    req: CouponUnlockRequest,
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    result = svc.unlock_coupon(organization_id, req)
    return CouponUnlockResponse(**result)


@router.get(
    "/coupons",
    response_model=CouponListResponse,
    summary="List coupons",
)
async def list_coupons(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    campaign_id: UUID | None = Query(None),
    mobilenumber: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("campaign.read")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    coupons, pagination = svc.list_coupons(
        current_user.organization_id, page, page_size, campaign_id, mobilenumber
    )
    return CouponListResponse(
        coupons=[CouponResponse.model_validate(c) for c in coupons],
        pagination=pagination,
    )


# ── Feedback / Survey ─────────────────────────────────────────────────────────

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="Submit feedback",
    description="Public endpoint. Submit product/campaign feedback linked to a coupon.",
)
async def submit_feedback(
    organization_id: UUID,
    data: FeedbackSubmit,
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    result = svc.submit_feedback(organization_id, data)
    return FeedbackResponse(**result)
