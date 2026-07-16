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
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found"
            )
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
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    def update_campaign(
        self,
        campaign_id: UUID,
        data: CampaignUpdate,
        organization_id: UUID,
        user_id: UUID,
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
        self, campaign_id: UUID, data: PrizeCreate, organization_id: UUID
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

    def list_prizes(
        self, campaign_id: UUID, organization_id: UUID
    ) -> list[Play2WinPrize]:
        self.get_campaign(campaign_id, organization_id)
        return (
            self.db.query(Play2WinPrize)
            .filter(
                Play2WinPrize.campaign_id == campaign_id,
                Play2WinPrize.is_active.is_(True),
            )
            .all()
        )

    def update_prize(
        self, campaign_id: UUID, prize_id: UUID, data, organization_id: UUID
    ) -> Play2WinPrize:
        self.get_campaign(campaign_id, organization_id)
        prize = (
            self.db.query(Play2WinPrize)
            .filter(
                Play2WinPrize.id == prize_id, Play2WinPrize.campaign_id == campaign_id
            )
            .first()
        )
        if not prize:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Prize not found"
            )
        update_dict = data.model_dump()
        for k, v in update_dict.items():
            setattr(prize, k, v)
        self.db.commit()
        self.db.refresh(prize)
        return prize

    def delete_prize(
        self, campaign_id: UUID, prize_id: UUID, organization_id: UUID
    ) -> None:
        self.get_campaign(campaign_id, organization_id)
        prize = (
            self.db.query(Play2WinPrize)
            .filter(
                Play2WinPrize.id == prize_id, Play2WinPrize.campaign_id == campaign_id
            )
            .first()
        )
        if not prize:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Prize not found"
            )
        self.db.delete(prize)
        self.db.commit()

    # ── Leads / CRM ───────────────────────────────────────────────────────────

    def create_lead(self, data: LeadCreate, organization_id: UUID) -> CampaignLead:
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
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    # ── Coupon Verification ───────────────────────────────────────────────────

    def verify_coupon(self, organization_id: UUID, req: CouponVerifyRequest) -> dict:
        coupon = self.coupon_repo.get_by_code(req.coupon_code, organization_id)
        if not coupon:
            return {
                "is_valid": False,
                "is_used": False,
                "is_expired": False,
                "coupon_id": None,
                "value": None,
                "units": None,
                "expiry": None,
                "message": "Coupon not found",
            }

        now = datetime.now(UTC)
        is_expired = bool(coupon.expiry and coupon.expiry < now)
        is_used = coupon.used is not None and coupon.used != ""

        # Mobile check if provided
        if req.mobilenumber and coupon.mobilenumber:
            if coupon.mobilenumber != req.mobilenumber:
                return {
                    "is_valid": False,
                    "is_used": is_used,
                    "is_expired": is_expired,
                    "coupon_id": coupon.id,
                    "value": coupon.value,
                    "units": coupon.units,
                    "expiry": coupon.expiry,
                    "message": "Coupon not registered to this mobile number",
                }

        if is_expired:
            return {
                "is_valid": False,
                "is_used": is_used,
                "is_expired": True,
                "coupon_id": coupon.id,
                "value": coupon.value,
                "units": coupon.units,
                "expiry": coupon.expiry,
                "message": "Coupon has expired",
            }
        if is_used:
            return {
                "is_valid": False,
                "is_used": True,
                "is_expired": False,
                "coupon_id": coupon.id,
                "value": coupon.value,
                "units": coupon.units,
                "expiry": coupon.expiry,
                "message": "Coupon has already been used",
            }

        return {
            "is_valid": True,
            "is_used": False,
            "is_expired": False,
            "coupon_id": coupon.id,
            "value": coupon.value,
            "units": coupon.units,
            "expiry": coupon.expiry,
            "message": "Coupon is valid",
        }

    # ── Coupon Redeem ─────────────────────────────────────────────────────────

    def redeem_coupon(self, organization_id: UUID, req: CouponRedeemRequest) -> dict:
        coupon = self.coupon_repo.get_by_code(req.coupon_code, organization_id)
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found"
            )

        now = datetime.now(UTC)
        if coupon.expiry and coupon.expiry < now:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Coupon has expired"
            )
        if coupon.used:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Coupon has already been used",
            )

        update = {
            "used": "yes",
            "used_timestamp": now,
            "location": req.location,
            "rating": req.rating,
            "comment": req.comment,
            "custom_answer": req.custom_answer,
            "final_billed_amount": req.final_billed_amount,
        }
        self.coupon_repo.update(
            coupon, {k: v for k, v in update.items() if v is not None}
        )

        logger.info("Coupon redeemed: code=%s org=%s", req.coupon_code, organization_id)
        return {
            "success": True,
            "coupon_id": coupon.id,
            "message": "Coupon redeemed successfully",
        }

    # ── Coupon Unlock ─────────────────────────────────────────────────────────

    def unlock_coupon(self, organization_id: UUID, req: CouponUnlockRequest) -> dict:
        coupon = self.coupon_repo.get_by_code(req.coupon_code, organization_id)
        if not coupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Coupon not found"
            )

        self.coupon_repo.update(
            coupon,
            {
                "is_unlocked": True,
                "unlock_count": (coupon.unlock_count or 0) + 1,
            },
        )
        self.coupon_repo.add_unlock_log(
            coupon_id=coupon.id,
            organization_id=organization_id,
            action="unlock",
            notes=req.notes,
            location=req.location,
            user_reference=req.user_reference,
        )

        logger.info(
            "Coupon unlocked: code=%s org=%s count=%d",
            req.coupon_code,
            organization_id,
            coupon.unlock_count,
        )
        return {
            "success": True,
            "coupon_id": coupon.id,
            "unlock_count": coupon.unlock_count,
            "message": "Coupon unlocked successfully",
        }

    # ── Feedback ──────────────────────────────────────────────────────────────

    def submit_feedback(self, organization_id: UUID, data: FeedbackSubmit) -> dict:
        """
        Attach feedback to an existing coupon (matched by mobile + campaign),
        or create a new coupon record if none exists.
        """
        self.get_campaign(data.campaign_id, organization_id)

        coupon = None
        if data.coupon_code:
            coupon = self.coupon_repo.get_by_code(data.coupon_code, organization_id)

        if coupon:
            update = {
                k: v
                for k, v in {
                    "rating": data.rating,
                    "product_rating": data.product_rating,
                    "color_rating": data.color_rating,
                    "price_rating": data.price_rating,
                    "comment": data.comment,
                    "custom_question": data.custom_question,
                    "custom_answer": data.custom_answer,
                }.items()
                if v is not None
            }
            self.coupon_repo.update(coupon, update)
        else:
            # Create a new coupon record to store the feedback
            coupon = self.coupon_repo.create(
                {
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
                }
            )

        return {
            "success": True,
            "coupon_id": coupon.id,
            "message": "Feedback submitted",
        }

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
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    # ── Phase 1: Campaign Clone & Status ──────────────────────────────────────

    def clone_campaign(
        self, campaign_id: UUID, new_name: str, organization_id: UUID, user_id: UUID
    ) -> Campaign:
        """Clone a campaign with all its prizes."""
        original = self.get_campaign(campaign_id, organization_id)
        clone_data = {
            k: v
            for k, v in original.__dict__.items()
            if k
            not in (
                "id",
                "_sa_instance_state",
                "created_at",
                "updated_at",
                "created_by",
                "updated_by",
                "deleted_at",
                "scans",
                "campaign_status",
                "prizes",
                "leads",
                "coupons",
            )
        }
        clone_data["name"] = new_name
        clone_data["organization_id"] = organization_id
        clone_data["created_by"] = user_id
        clone_data["updated_by"] = user_id
        clone_data["campaign_status"] = "A"
        clone_data["scans"] = 0

        cloned = self.campaign_repo.create(clone_data)

        # Clone prizes
        for prize in original.prizes:
            self.db.add(
                Play2WinPrize(
                    organization_id=organization_id,
                    campaign_id=cloned.id,
                    name=prize.name,
                    prize_type=prize.prize_type,
                    value=prize.value,
                    weight=prize.weight,
                    max_quantity=prize.max_quantity,
                    slot_color=prize.slot_color,
                    is_active=prize.is_active,
                )
            )
        self.db.commit()
        self.db.refresh(cloned)
        return cloned

    def update_campaign_status(
        self, campaign_id: UUID, new_status: str, organization_id: UUID, user_id: UUID
    ) -> Campaign:
        """Update campaign status (A=active, P=paused, E=ended)."""
        campaign = self.get_campaign(campaign_id, organization_id)
        valid = {"A", "P", "E"}
        if new_status not in valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status '{new_status}'. Must be one of: {valid}",
            )
        return self.campaign_repo.update(
            campaign, {"campaign_status": new_status, "updated_by": user_id}
        )

    # ── Phase 1: Lead Detail / Update / Delete / Archive ─────────────────────

    def get_lead(self, lead_id: UUID, organization_id: UUID) -> CampaignLead:
        lead = self.lead_repo.get_by_id(lead_id, organization_id)
        if not lead:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found"
            )
        return lead

    def update_lead(self, lead_id: UUID, data, organization_id: UUID) -> CampaignLead:
        lead = self.get_lead(lead_id, organization_id)
        update_dict = data.model_dump(exclude_unset=True)
        return self.lead_repo.update(lead, update_dict)

    def delete_lead(self, lead_id: UUID, organization_id: UUID) -> None:
        lead = self.get_lead(lead_id, organization_id)
        self.db.delete(lead)
        self.db.commit()

    def bulk_delete_leads(self, lead_ids: list[UUID], organization_id: UUID) -> int:
        result = (
            self.db.query(CampaignLead)
            .filter(
                CampaignLead.id.in_(lead_ids),
                CampaignLead.organization_id == organization_id,
            )
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return result

    def archive_lead(self, lead_id: UUID, organization_id: UUID) -> CampaignLead:
        lead = self.get_lead(lead_id, organization_id)
        return self.lead_repo.update(lead, {"is_archived": True})

    def unarchive_lead(self, lead_id: UUID, organization_id: UUID) -> CampaignLead:
        lead = self.get_lead(lead_id, organization_id)
        return self.lead_repo.update(lead, {"is_archived": False})

    def blocklist_lead(self, lead_id: UUID, organization_id: UUID) -> CampaignLead:
        lead = self.get_lead(lead_id, organization_id)
        return self.lead_repo.update(lead, {"is_blocklisted": True})

    def unblocklist_lead(self, lead_id: UUID, organization_id: UUID) -> CampaignLead:
        lead = self.get_lead(lead_id, organization_id)
        return self.lead_repo.update(lead, {"is_blocklisted": False})

    # ── Phase 1: Lead Notes ──────────────────────────────────────────────────

    def add_lead_note(
        self, lead_id: UUID, content: str, organization_id: UUID, user_id: UUID
    ) -> "LeadNote":
        from app.models.coupon import LeadNote

        self.get_lead(lead_id, organization_id)
        note = LeadNote(
            organization_id=organization_id,
            lead_id=lead_id,
            content=content,
            created_by=user_id,
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def list_lead_notes(self, lead_id: UUID, organization_id: UUID) -> list["LeadNote"]:
        from app.models.coupon import LeadNote

        self.get_lead(lead_id, organization_id)
        return (
            self.db.query(LeadNote)
            .filter(
                LeadNote.lead_id == lead_id, LeadNote.organization_id == organization_id
            )
            .order_by(LeadNote.created_at.desc())
            .all()
        )

    def update_lead_note(
        self, lead_id: UUID, note_id: UUID, content: str, organization_id: UUID
    ) -> "LeadNote":
        from app.models.coupon import LeadNote

        self.get_lead(lead_id, organization_id)
        note = (
            self.db.query(LeadNote)
            .filter(
                LeadNote.id == note_id,
                LeadNote.lead_id == lead_id,
                LeadNote.organization_id == organization_id,
            )
            .first()
        )
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
            )
        note.content = content
        self.db.commit()
        self.db.refresh(note)
        return note

    def delete_lead_note(
        self, lead_id: UUID, note_id: UUID, organization_id: UUID
    ) -> None:
        from app.models.coupon import LeadNote

        self.get_lead(lead_id, organization_id)
        result = (
            self.db.query(LeadNote)
            .filter(
                LeadNote.id == note_id,
                LeadNote.lead_id == lead_id,
                LeadNote.organization_id == organization_id,
            )
            .delete()
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Note not found"
            )
        self.db.commit()

    # ── Phase 1: Tag CRUD ────────────────────────────────────────────────────

    def create_tag(self, data, organization_id: UUID) -> CampaignTag:
        from app.models.coupon import CampaignTag

        tag = CampaignTag(
            organization_id=organization_id,
            **data.model_dump(),
        )
        self.db.add(tag)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def list_tags(self, organization_id: UUID) -> list[CampaignTag]:
        from app.models.coupon import CampaignTag

        return (
            self.db.query(CampaignTag)
            .filter(CampaignTag.organization_id == organization_id)
            .order_by(CampaignTag.created_at.desc())
            .all()
        )

    def get_tag(self, tag_id: UUID, organization_id: UUID) -> CampaignTag:
        from app.models.coupon import CampaignTag

        tag = (
            self.db.query(CampaignTag)
            .filter(
                CampaignTag.id == tag_id, CampaignTag.organization_id == organization_id
            )
            .first()
        )
        if not tag:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found"
            )
        return tag

    def update_tag(self, tag_id: UUID, data, organization_id: UUID) -> CampaignTag:
        tag = self.get_tag(tag_id, organization_id)
        update_dict = data.model_dump(exclude_unset=True)
        for k, v in update_dict.items():
            setattr(tag, k, v)
        self.db.commit()
        self.db.refresh(tag)
        return tag

    def delete_tag(self, tag_id: UUID, organization_id: UUID) -> None:
        from app.models.coupon import lead_tags

        tag = self.get_tag(tag_id, organization_id)
        # Remove all lead-tag associations first
        self.db.execute(lead_tags.delete().where(lead_tags.c.tag_id == tag_id))
        self.db.delete(tag)
        self.db.commit()

    def assign_tags(
        self, tag_ids: list[UUID], lead_ids: list[UUID], organization_id: UUID
    ) -> dict:
        """Assign tags to leads. Returns count of assignments made."""
        from app.models.coupon import CampaignLead, CampaignTag, lead_tags

        # Validate tags belong to org
        valid_tags = (
            self.db.query(CampaignTag.id)
            .filter(
                CampaignTag.id.in_(tag_ids),
                CampaignTag.organization_id == organization_id,
            )
            .all()
        )
        valid_tag_ids = {t[0] for t in valid_tags}
        # Validate leads belong to org
        valid_leads = (
            self.db.query(CampaignLead.id)
            .filter(
                CampaignLead.id.in_(lead_ids),
                CampaignLead.organization_id == organization_id,
            )
            .all()
        )
        valid_lead_ids = {l[0] for l in valid_leads}

        assigned = 0
        for tag_id in valid_tag_ids:
            for lead_id in valid_lead_ids:
                existing = self.db.execute(
                    lead_tags.select().where(
                        lead_tags.c.tag_id == tag_id,
                        lead_tags.c.lead_id == lead_id,
                    )
                ).first()
                if not existing:
                    self.db.execute(
                        lead_tags.insert().values(tag_id=tag_id, lead_id=lead_id)
                    )
                    assigned += 1

        self.db.commit()
        return {
            "assigned": assigned,
            "tag_ids": list(valid_tag_ids),
            "lead_ids": list(valid_lead_ids),
        }

    def unassign_tags(
        self, tag_ids: list[UUID], lead_ids: list[UUID], organization_id: UUID
    ) -> dict:
        """Unassign tags from leads. Returns count of removals."""
        from app.models.coupon import lead_tags

        result = self.db.execute(
            lead_tags.delete().where(
                lead_tags.c.tag_id.in_(tag_ids),
                lead_tags.c.lead_id.in_(lead_ids),
            )
        )
        self.db.commit()
        return {"removed": result.rowcount}

    def clear_tag_from_leads(self, tag_id: UUID, organization_id: UUID) -> dict:
        """Remove a tag from all leads in the organization."""
        from app.models.coupon import lead_tags

        self.get_tag(tag_id, organization_id)
        result = self.db.execute(lead_tags.delete().where(lead_tags.c.tag_id == tag_id))
        self.db.commit()
        return {"removed": result.rowcount}
