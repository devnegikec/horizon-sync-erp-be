"""Repository for Warranty module"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.warranty import Warranty, WarrantyPeriod


class WarrantyPeriodRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> WarrantyPeriod:
        # If new period is default, clear existing defaults first
        if data.get("is_default"):
            self.db.query(WarrantyPeriod).filter(
                WarrantyPeriod.organization_id == data["organization_id"],
                WarrantyPeriod.is_default.is_(True),
            ).update({"is_default": False})
        period = WarrantyPeriod(**data)
        self.db.add(period)
        self.db.commit()
        self.db.refresh(period)
        return period

    def list(self, organization_id: UUID) -> list[WarrantyPeriod]:
        return (
            self.db.query(WarrantyPeriod)
            .filter(
                WarrantyPeriod.organization_id == organization_id,
                WarrantyPeriod.is_active.is_(True),
            )
            .order_by(WarrantyPeriod.months)
            .all()
        )

    def get_default(self, organization_id: UUID) -> WarrantyPeriod | None:
        return (
            self.db.query(WarrantyPeriod)
            .filter(
                WarrantyPeriod.organization_id == organization_id,
                WarrantyPeriod.is_default.is_(True),
                WarrantyPeriod.is_active.is_(True),
            )
            .first()
        )


class WarrantyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Warranty:
        warranty = Warranty(**data)
        self.db.add(warranty)
        self.db.commit()
        self.db.refresh(warranty)
        return warranty

    def get_by_serial(self, serial_number: str,
                      organization_id: UUID) -> Warranty | None:
        return (
            self.db.query(Warranty)
            .filter(
                Warranty.serial_number == serial_number,
                Warranty.organization_id == organization_id,
            )
            .order_by(Warranty.created_at.desc())
            .first()
        )

    def get_by_mobile(self, mobile: str,
                      organization_id: UUID) -> list[Warranty]:
        return (
            self.db.query(Warranty)
            .filter(
                Warranty.mobile == mobile,
                Warranty.organization_id == organization_id,
            )
            .order_by(Warranty.created_at.desc())
            .all()
        )

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        search: str | None = None,
    ) -> tuple[list[Warranty], int]:
        q = self.db.query(Warranty).filter(
            Warranty.organization_id == organization_id,
        )
        if search:
            q = q.filter(
                Warranty.serial_number.ilike(f"%{search}%")
                | Warranty.mobile.ilike(f"%{search}%")
                | Warranty.customer_name.ilike(f"%{search}%")
            )
        total = q.count()
        items = (
            q.order_by(Warranty.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total
