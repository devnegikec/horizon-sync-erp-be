"""Campaigns & Coupons API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.campaign import (
    CampaignCloneRequest,
    CampaignCreate,
    CampaignListResponse,
    CampaignResponse,
    CampaignStatusUpdate,
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
    LeadBulkDeleteRequest,
    LeadCreate,
    LeadListResponse,
    LeadNoteCreate,
    LeadNoteResponse,
    LeadNoteUpdate,
    LeadResponse,
    LeadUpdate,
    PrizeCreate,
    PrizeResponse,
    TagAssignmentRequest,
    TagCreate,
    TagResponse,
    TagUpdate,
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
    campaign_type: str | None = Query(
        None, description="Filter by type (QR, WB, etc.)"
    ),
    campaign_status: str | None = Query(None, description="A=active, I=inactive"),
    search: str | None = Query(None),
    current_user: CurrentUser = Depends(require_permission("campaign.read")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    campaigns, pagination = svc.list_campaigns(
        current_user.organization_id,
        page,
        page_size,
        campaign_type,
        campaign_status,
        search,
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


@router.put(
    "/{campaign_id}/prizes/{prize_id}",
    response_model=PrizeResponse,
    summary="Update prize",
)
async def update_prize(
    campaign_id: UUID,
    prize_id: UUID,
    data: PrizeCreate,
    current_user: CurrentUser = Depends(require_permission("prize.update")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    prize = svc.update_prize(campaign_id, prize_id, data, current_user.organization_id)
    return PrizeResponse.model_validate(prize)


@router.delete(
    "/{campaign_id}/prizes/{prize_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete prize",
)
async def delete_prize(
    campaign_id: UUID,
    prize_id: UUID,
    current_user: CurrentUser = Depends(require_permission("prize.delete")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    svc.delete_prize(campaign_id, prize_id, current_user.organization_id)


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


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Campaign Clone & Status
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/{campaign_id}/clone",
    response_model=CampaignResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Clone campaign",
)
async def clone_campaign(
    campaign_id: UUID,
    data: CampaignCloneRequest,
    current_user: CurrentUser = Depends(require_permission("campaign.clone")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    campaign = svc.clone_campaign(
        campaign_id, data.name, current_user.organization_id, current_user.id
    )
    return CampaignResponse.model_validate(campaign)


@router.patch(
    "/{campaign_id}/status",
    response_model=CampaignResponse,
    summary="Update campaign status",
    description="Change campaign status: A=active, P=paused, E=ended.",
)
async def update_campaign_status(
    campaign_id: UUID,
    data: CampaignStatusUpdate,
    current_user: CurrentUser = Depends(require_permission("campaign.manage_status")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    campaign = svc.update_campaign_status(
        campaign_id, data.status, current_user.organization_id, current_user.id
    )
    return CampaignResponse.model_validate(campaign)


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Lead Detail / Update / Delete / Archive / Blocklist
# ═══════════════════════════════════════════════════════════════════════════════


@router.get(
    "/leads/{lead_id}",
    response_model=LeadResponse,
    summary="Get lead detail",
)
async def get_lead(
    lead_id: UUID,
    current_user: CurrentUser = Depends(require_permission("lead.read")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    return LeadResponse.model_validate(
        svc.get_lead(lead_id, current_user.organization_id)
    )


@router.put(
    "/leads/{lead_id}",
    response_model=LeadResponse,
    summary="Update lead",
)
async def update_lead(
    lead_id: UUID,
    data: LeadUpdate,
    current_user: CurrentUser = Depends(require_permission("lead.update")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    lead = svc.update_lead(lead_id, data, current_user.organization_id)
    return LeadResponse.model_validate(lead)


@router.delete(
    "/leads/{lead_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lead",
)
async def delete_lead(
    lead_id: UUID,
    current_user: CurrentUser = Depends(require_permission("lead.delete")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    svc.delete_lead(lead_id, current_user.organization_id)


@router.post(
    "/leads/bulk-delete",
    status_code=status.HTTP_200_OK,
    summary="Bulk delete leads",
)
async def bulk_delete_leads(
    data: LeadBulkDeleteRequest,
    current_user: CurrentUser = Depends(require_permission("lead.delete")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    deleted = svc.bulk_delete_leads(data.lead_ids, current_user.organization_id)
    return {"deleted": deleted}


@router.post(
    "/leads/{lead_id}/archive",
    response_model=LeadResponse,
    summary="Archive lead",
)
async def archive_lead(
    lead_id: UUID,
    current_user: CurrentUser = Depends(require_permission("lead.archive")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    return LeadResponse.model_validate(
        svc.archive_lead(lead_id, current_user.organization_id)
    )


@router.post(
    "/leads/{lead_id}/unarchive",
    response_model=LeadResponse,
    summary="Unarchive lead",
)
async def unarchive_lead(
    lead_id: UUID,
    current_user: CurrentUser = Depends(require_permission("lead.archive")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    return LeadResponse.model_validate(
        svc.unarchive_lead(lead_id, current_user.organization_id)
    )


@router.post(
    "/leads/{lead_id}/blocklist",
    response_model=LeadResponse,
    summary="Blocklist lead",
)
async def blocklist_lead(
    lead_id: UUID,
    current_user: CurrentUser = Depends(require_permission("lead.blocklist")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    return LeadResponse.model_validate(
        svc.blocklist_lead(lead_id, current_user.organization_id)
    )


@router.delete(
    "/leads/{lead_id}/blocklist",
    response_model=LeadResponse,
    summary="Remove from blocklist",
)
async def unblocklist_lead(
    lead_id: UUID,
    current_user: CurrentUser = Depends(require_permission("lead.blocklist")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    return LeadResponse.model_validate(
        svc.unblocklist_lead(lead_id, current_user.organization_id)
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Lead Notes
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/leads/{lead_id}/notes",
    response_model=LeadNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add note to lead",
)
async def add_lead_note(
    lead_id: UUID,
    data: LeadNoteCreate,
    current_user: CurrentUser = Depends(require_permission("lead.note")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    note = svc.add_lead_note(
        lead_id, data.content, current_user.organization_id, current_user.id
    )
    return LeadNoteResponse.model_validate(note)


@router.get(
    "/leads/{lead_id}/notes",
    response_model=list[LeadNoteResponse],
    summary="List lead notes",
)
async def list_lead_notes(
    lead_id: UUID,
    current_user: CurrentUser = Depends(require_permission("lead.read")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    notes = svc.list_lead_notes(lead_id, current_user.organization_id)
    return [LeadNoteResponse.model_validate(n) for n in notes]


@router.put(
    "/leads/{lead_id}/notes/{note_id}",
    response_model=LeadNoteResponse,
    summary="Update lead note",
)
async def update_lead_note(
    lead_id: UUID,
    note_id: UUID,
    data: LeadNoteUpdate,
    current_user: CurrentUser = Depends(require_permission("lead.note")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    note = svc.update_lead_note(
        lead_id, note_id, data.content, current_user.organization_id
    )
    return LeadNoteResponse.model_validate(note)


@router.delete(
    "/leads/{lead_id}/notes/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete lead note",
)
async def delete_lead_note(
    lead_id: UUID,
    note_id: UUID,
    current_user: CurrentUser = Depends(require_permission("lead.note")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    svc.delete_lead_note(lead_id, note_id, current_user.organization_id)


# ═══════════════════════════════════════════════════════════════════════════════
# Phase 1: Tag CRUD + Assignment
# ═══════════════════════════════════════════════════════════════════════════════


@router.post(
    "/tags",
    response_model=TagResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create tag",
)
async def create_tag(
    data: TagCreate,
    current_user: CurrentUser = Depends(require_permission("tag.create")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    tag = svc.create_tag(data, current_user.organization_id)
    return TagResponse.model_validate(tag)


@router.get(
    "/tags",
    response_model=list[TagResponse],
    summary="List tags",
)
async def list_tags(
    current_user: CurrentUser = Depends(require_permission("tag.read")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    tags = svc.list_tags(current_user.organization_id)
    return [TagResponse.model_validate(t) for t in tags]


@router.get(
    "/tags/{tag_id}",
    response_model=TagResponse,
    summary="Get tag detail",
)
async def get_tag(
    tag_id: UUID,
    current_user: CurrentUser = Depends(require_permission("tag.read")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    return TagResponse.model_validate(svc.get_tag(tag_id, current_user.organization_id))


@router.put(
    "/tags/{tag_id}",
    response_model=TagResponse,
    summary="Update tag",
)
async def update_tag(
    tag_id: UUID,
    data: TagUpdate,
    current_user: CurrentUser = Depends(require_permission("tag.update")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    tag = svc.update_tag(tag_id, data, current_user.organization_id)
    return TagResponse.model_validate(tag)


@router.delete(
    "/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tag",
)
async def delete_tag(
    tag_id: UUID,
    current_user: CurrentUser = Depends(require_permission("tag.delete")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    svc.delete_tag(tag_id, current_user.organization_id)


@router.post(
    "/tags/assign",
    summary="Assign tags to leads",
)
async def assign_tags(
    data: TagAssignmentRequest,
    current_user: CurrentUser = Depends(require_permission("tag.assign")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    return svc.assign_tags(data.tag_ids, data.lead_ids, current_user.organization_id)


@router.post(
    "/tags/unassign",
    summary="Unassign tags from leads",
)
async def unassign_tags(
    data: TagAssignmentRequest,
    current_user: CurrentUser = Depends(require_permission("tag.unassign")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    return svc.unassign_tags(data.tag_ids, data.lead_ids, current_user.organization_id)


@router.post(
    "/tags/{tag_id}/clear",
    summary="Clear tag from all leads",
)
async def clear_tag(
    tag_id: UUID,
    current_user: CurrentUser = Depends(require_permission("tag.unassign")),
    db: Session = Depends(get_db),
):
    svc = CampaignService(db)
    return svc.clear_tag_from_leads(tag_id, current_user.organization_id)
