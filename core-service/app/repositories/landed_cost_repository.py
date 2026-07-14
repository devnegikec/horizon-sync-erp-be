"""Landed cost voucher repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.base import DocumentStatus
from app.models.landed_cost import LandedCostVoucher


class LandedCostRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> LandedCostVoucher:
        lc = LandedCostVoucher(**data)
        self.db.add(lc)
        self.db.commit()
        self.db.refresh(lc)
        return lc

    def get_by_id(
        self, voucher_id: UUID, organization_id: UUID
    ) -> LandedCostVoucher | None:
        return (
            self.db.query(LandedCostVoucher)
            .filter(
                LandedCostVoucher.id == voucher_id,
                LandedCostVoucher.organization_id == organization_id,
            )
            .first()
        )

    def get_by_no(
        self, voucher_no: str, organization_id: UUID
    ) -> LandedCostVoucher | None:
        return (
            self.db.query(LandedCostVoucher)
            .filter(
                LandedCostVoucher.voucher_no == voucher_no,
                LandedCostVoucher.organization_id == organization_id,
            )
            .first()
        )

    def list_vouchers(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[LandedCostVoucher], int]:
        q = self.db.query(LandedCostVoucher).filter(
            LandedCostVoucher.organization_id == organization_id
        )
        if status is not None:
            q = q.filter(LandedCostVoucher.status == DocumentStatus(status))
        total = q.count()
        col = getattr(LandedCostVoucher, sort_by, LandedCostVoucher.created_at)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, lc: LandedCostVoucher, data: dict) -> LandedCostVoucher:
        for k, v in data.items():
            if hasattr(lc, k):
                setattr(lc, k, v)
        self.db.commit()
        self.db.refresh(lc)
        return lc

    def delete(self, lc: LandedCostVoucher) -> None:
        self.db.delete(lc)
        self.db.commit()
