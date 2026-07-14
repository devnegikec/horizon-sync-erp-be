"""Service layer for Campaigns & Coupons module"""

import logging
import random
import string
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.campaign import Campaign, Play2WinPrize
from app.models.coupon import CampaignLead, Coupon
from app.repositories.campaign_repository import (
    CampaignRepository,
    CouponRepository,
    LeadRepository,
)
from app.schemas.campaign import (
    CampaignCreate,
    CampaignUpdate,
    CouponRedeemRequest,
    CouponUnlockRequest,
    CouponVerifyRequest,
    FeedbackSubmit,
    LeadCreate,
    PrizeCreate,
)

logger = logging.getLogger(__name__)


def _generate_coupon_code(length: int = 10) -> str:
    """Generate a random alphanumeric coupon code"""
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


class CampaignService:
    def __init__(self, db: Session):
        self.db = db
        self.campaign_repo = CampaignRepository(db)
        self.lead_repo = LeadRepository(db)
        self.coupon_repo = CouponRepository(db)

    # ── Campaigns ─────────────────────────────────────────────────────────────

    def create_campaign(
        self, data: CampaignCreate, organization_id: UUID, user_id: UUID
    ) -> Campaign:
        campaign_dict = data.model_dump()
        campaign_dict["organization_id"] = organization_id
        campaign_dict["created_by"] = user_id
        campaign_dict["updated_by"] = user_id
        return self.campaign_repo.create(campaign_dict)

    def get_campaign(self, campaign_id: UUID, organization_id: UUID) -> Campaign:
        campaign = self.campaign_repo.get_by_id(campaign_id, organization_id)
        if not campaign:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Campaign not found")
        return campaign

    def list_campaigns(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        campaign_type: str | None = None,
        campaign_status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Campaign], dict]:
        items, total = self.campaign_repo.list(
            organization_id, page, page_size, campaign_type, campaign_status, search
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return items, {
            "page": page, "page_size": page_size, "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages, "has_prev": page > 1,
        }

    def update_campaign(
        self, campaign_id: UUID, data: CampaignUpdate,
        organization_id: UUID, user_id: UUID
    ) -> Campaign:
        campaign = self.get_campaign(campaign_id, organization_id)
        update_dict = data.model_dump(exclude_unset=True)
        update_dict["updated_by"] = user_id
        return self.campaign_repo.update(campaign, update_dict)

    def delete_campaign(
        self, campaign_id: UUID, organization_id: UUID, user_id: UUID
    ) -> None:
        campaign = self.get_campaign(campaign_id, organization_id)
        self.campaign_repo.soft_delete(campaign, user_id)

    # ── Prizes ────────────────────────────────────────────────────────────────

    def add_prize(
        self, campaign_id: UUID, data: PrizeCreate,
        organization_id: UUID
    ) -> Play2WinPrize:
        self.get_campaign(campaign_id, organization_id)
        prize = Play2WinPrize(
            organization_id=organization_id,
            campaign_id=campaign_id,
            **data.model_dump(),
        )
        self.db.add(prize)
        self.db.commit()
        self.db.refresh(prize)
        return prize

    def list_prizes(self, campaign_id: UUID, organization_id: UUID) -> list[Play2WinPrize]:
        self.get_campaign(campaign_id, organization_id)
        return (
            self.db.query(Play2WinPrize)
            .filter(Play2WinPrize.campaign_id == campaign_id,
                    Play2WinPrize.is_active.is_(True))
            .all()
        )

    # ── Leads / CRM ───────────────────────────────────────────────────────────

    def create_lead(
        self, data: LeadCreate, organization_id: UUID
    ) -> CampaignLead:
        # Validate campaign if provided
        if data.campaign_id:
            self.get_campaign(data.campaign_id, organization_id)

        lead_dict = data.model_dump()
        lead_dict["organization_id"] = organization_id
        lead_dict["timestamp"] = datetime.now(UTC)
        return self.lead_repo.create(lead_dict)

    def list_leads(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        campaign_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[CampaignLead], dict]:
        items, total = self.lead_repo.list(
            organization_id, page, page_size, campaign_id, search
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return items, {
            "page": page, "page_size": page_size, "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages, "has_prev": page > 1,
        }

    # ── Coupon Verification ───────────────────────────────────────────────────

    def verify_coupon(
        self, organization_id: UUID, req: CouponVerifyRequest
    ) -> dict:
        coupon = self.coupon_repo.get_by_code(req.coupon_code, organization_id)
        if not coupon:
            return {
                "is_valid": False, "is_used": False, "is_expired": False,
                "coupon_id": None, "value": None, "units": None, "expiry": None,
                "message": "Coupon not found",
            }

        now = datetime.now(UTC)
        is_expired = bool(coupon.expiry and coupon.expiry < now)
        is_used = coupon.used is not None and coupon.used != ""

        # Mobile check if provided
        if req.mobilenumber and coupon.mobilenumber:
            if coupon.mobilenumber != req.mobilenumber:
                return {
                    "is_valid": False, "is_used": is_used, "is_expired": is_expired,
                    "coupon_id": coupon.id, "value": coupon.value,
                    "units": coupon.units, "expiry": coupon.expiry,
                    "message": "Coupon not registered to this mobile number",
                }

        if is_expired:
            return {
                "is_valid": False, "is_used": is_used, "is_expired": True,
                "coupon_id": coupon.id, "value": coupon.value,
                "units": coupon.units, "expiry": coupon.expiry,
                "message": "Coupon has expired",
            }
        if is_used:
            return {
                "is_valid": False, "is_used": True, "is_expired": False,
                "coupon_id": coupon.id, "value": coupon.value,
                "units": coupon.units, "expiry": coupon.expiry,
                "message": "Coupon has already been used",
            }

        return {
            "is_valid": True, "is_used": False, "is_expired": False,
            "coupon_id": coupon.id, "value": coupon.value,
            "units": coupon.units, "expiry": coupon.expiry,
            "message": "Coupon is valid",
        }

    # ── Coupon Redeem ─────────────────────────────────────────────────────────

    def redeem_coupon(
        self, organization_id: UUID, req: CouponRedeemRequest
    ) -> dict:
        coupon = self.coupon_repo.get_by_code(req.coupon_code, organization_id)
        if not coupon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Coupon not found")

        now = datetime.now(UTC)
        if coupon.expiry and coupon.expiry < now:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Coupon has expired")
        if coupon.used:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail="Coupon has already been used")

        update = {
            "used": "yes",
            "used_timestamp": now,
            "location": req.location,
            "rating": req.rating,
            "comment": req.comment,
            "custom_answer": req.custom_answer,
            "final_billed_amount": req.final_billed_amount,
        }
        self.coupon_repo.update(coupon, {k: v for k, v in update.items() if v is not None})

        logger.info("Coupon redeemed: code=%s org=%s", req.coupon_code, organization_id)
        return {"success": True, "coupon_id": coupon.id, "message": "Coupon redeemed successfully"}

    # ── Coupon Unlock ─────────────────────────────────────────────────────────

    def unlock_coupon(
        self, organization_id: UUID, req: CouponUnlockRequest
    ) -> dict:
        coupon = self.coupon_repo.get_by_code(req.coupon_code, organization_id)
        if not coupon:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail="Coupon not found")

        self.coupon_repo.update(coupon, {
            "is_unlocked": True,
            "unlock_count": (coupon.unlock_count or 0) + 1,
        })
        self.coupon_repo.add_unlock_log(
            coupon_id=coupon.id,
            organization_id=organization_id,
            action="unlock",
            notes=req.notes,
            location=req.location,
            user_reference=req.user_reference,
        )

        logger.info("Coupon unlocked: code=%s org=%s count=%d",
                    req.coupon_code, organization_id, coupon.unlock_count)
        return {
            "success": True,
            "coupon_id": coupon.id,
            "unlock_count": coupon.unlock_count,
            "message": "Coupon unlocked successfully",
        }

    # ── Feedback ──────────────────────────────────────────────────────────────

    def submit_feedback(
        self, organization_id: UUID, data: FeedbackSubmit
    ) -> dict:
        """
        Attach feedback to an existing coupon (matched by mobile + campaign),
        or create a new coupon record if none exists.
        """
        self.get_campaign(data.campaign_id, organization_id)

        coupon = None
        if data.coupon_code:
            coupon = self.coupon_repo.get_by_code(data.coupon_code, organization_id)

        if coupon:
            update = {k: v for k, v in {
                "rating": data.rating,
                "product_rating": data.product_rating,
                "color_rating": data.color_rating,
                "price_rating": data.price_rating,
                "comment": data.comment,
                "custom_question": data.custom_question,
                "custom_answer": data.custom_answer,
            }.items() if v is not None}
            self.coupon_repo.update(coupon, update)
        else:
            # Create a new coupon record to store the feedback
            coupon = self.coupon_repo.create({
                "organization_id": organization_id,
                "campaign_id": data.campaign_id,
                "mobilenumber": data.mobilenumber,
                "coupon_code": data.coupon_code,
                "rating": data.rating,
                "product_rating": data.product_rating,
                "color_rating": data.color_rating,
                "price_rating": data.price_rating,
                "comment": data.comment,
                "custom_question": data.custom_question,
                "custom_answer": data.custom_answer,
            })

        return {"success": True, "coupon_id": coupon.id, "message": "Feedback submitted"}

    # ── Coupon list ───────────────────────────────────────────────────────────

    def list_coupons(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        campaign_id: UUID | None = None,
        mobilenumber: str | None = None,
    ) -> tuple[list[Coupon], dict]:
        items, total = self.coupon_repo.list(
            organization_id, page, page_size, campaign_id, mobilenumber
        )
        total_pages = max(1, (total + page_size - 1) // page_size)
        return items, {
            "page": page, "page_size": page_size, "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages, "has_prev": page > 1,
        }
