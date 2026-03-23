"""Repository for Campaigns & Coupons module"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.campaign import Campaign, WebCampaign
from app.models.coupon import CampaignLead, CampaignTag, Coupon, CouponUnlockLog


class CampaignRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Campaign:
        campaign = Campaign(**data)
        self.db.add(campaign)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def get_by_id(self, campaign_id: UUID, organization_id: UUID) -> Campaign | None:
        return (
            self.db.query(Campaign)
            .filter(
                Campaign.id == campaign_id,
                Campaign.organization_id == organization_id,
                Campaign.deleted_at.is_(None),
            )
            .first()
        )

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        campaign_type: str | None = None,
        campaign_status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Campaign], int]:
        q = self.db.query(Campaign).filter(
            Campaign.organization_id == organization_id,
            Campaign.deleted_at.is_(None),
        )
        if campaign_type:
            q = q.filter(Campaign.campaign_type == campaign_type)
        if campaign_status:
            q = q.filter(Campaign.campaign_status == campaign_status)
        if search:
            q = q.filter(Campaign.name.ilike(f"%{search}%"))
        total = q.count()
        items = (
            q.order_by(Campaign.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update(self, campaign: Campaign, data: dict) -> Campaign:
        for k, v in data.items():
            setattr(campaign, k, v)
        self.db.commit()
        self.db.refresh(campaign)
        return campaign

    def soft_delete(self, campaign: Campaign, user_id: UUID) -> None:
        campaign.deleted_at = datetime.now(UTC)
        campaign.updated_by = user_id
        self.db.commit()

    def increment_scans(self, campaign_id: UUID) -> None:
        self.db.query(Campaign).filter(Campaign.id == campaign_id).update(
            {Campaign.scans: Campaign.scans + 1}
        )
        self.db.commit()


class LeadRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> CampaignLead:
        lead = CampaignLead(**data)
        self.db.add(lead)
        self.db.commit()
        self.db.refresh(lead)
        return lead

    def get_by_id(self, lead_id: UUID, organization_id: UUID) -> CampaignLead | None:
        return (
            self.db.query(CampaignLead)
            .filter(
                CampaignLead.id == lead_id,
                CampaignLead.organization_id == organization_id,
            )
            .first()
        )

    def get_by_mobile(self, mobile: str, organization_id: UUID,
                      campaign_id: UUID | None = None) -> CampaignLead | None:
        q = self.db.query(CampaignLead).filter(
            CampaignLead.mobilenumber == mobile,
            CampaignLead.organization_id == organization_id,
        )
        if campaign_id:
            q = q.filter(CampaignLead.campaign_id == campaign_id)
        return q.first()

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        campaign_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[list[CampaignLead], int]:
        q = self.db.query(CampaignLead).filter(
            CampaignLead.organization_id == organization_id,
        )
        if campaign_id:
            q = q.filter(CampaignLead.campaign_id == campaign_id)
        if search:
            q = q.filter(
                CampaignLead.name.ilike(f"%{search}%")
                | CampaignLead.mobilenumber.ilike(f"%{search}%")
                | CampaignLead.email.ilike(f"%{search}%")
            )
        total = q.count()
        items = (
            q.order_by(CampaignLead.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total


class CouponRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Coupon:
        coupon = Coupon(**data)
        self.db.add(coupon)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def get_by_code(self, coupon_code: str,
                    organization_id: UUID) -> Coupon | None:
        return (
            self.db.query(Coupon)
            .filter(
                Coupon.coupon_code == coupon_code,
                Coupon.organization_id == organization_id,
            )
            .first()
        )

    def get_by_id(self, coupon_id: UUID, organization_id: UUID) -> Coupon | None:
        return (
            self.db.query(Coupon)
            .filter(
                Coupon.id == coupon_id,
                Coupon.organization_id == organization_id,
            )
            .first()
        )

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        campaign_id: UUID | None = None,
        mobilenumber: str | None = None,
    ) -> tuple[list[Coupon], int]:
        q = self.db.query(Coupon).filter(
            Coupon.organization_id == organization_id,
        )
        if campaign_id:
            q = q.filter(Coupon.campaign_id == campaign_id)
        if mobilenumber:
            q = q.filter(Coupon.mobilenumber == mobilenumber)
        total = q.count()
        items = (
            q.order_by(Coupon.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update(self, coupon: Coupon, data: dict) -> Coupon:
        for k, v in data.items():
            setattr(coupon, k, v)
        self.db.commit()
        self.db.refresh(coupon)
        return coupon

    def add_unlock_log(self, coupon_id: UUID, organization_id: UUID,
                       action: str, **kwargs) -> CouponUnlockLog:
        log = CouponUnlockLog(
            organization_id=organization_id,
            coupon_id=coupon_id,
            action=action,
            **kwargs,
        )
        self.db.add(log)
        self.db.commit()
        return log
