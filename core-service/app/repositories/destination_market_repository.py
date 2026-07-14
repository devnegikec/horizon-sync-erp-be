"""Repository for Destinations module"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.destination_market import DestinationMarket


class DestinationMarketRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> DestinationMarket:
        market = DestinationMarket(**data)
        self.db.add(market)
        self.db.commit()
        self.db.refresh(market)
        return market

    def get_by_id(self, market_id: UUID, organization_id: UUID) -> DestinationMarket | None:
        return (
            self.db.query(DestinationMarket)
            .filter(
                DestinationMarket.id == market_id,
                DestinationMarket.organization_id == organization_id,
                DestinationMarket.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_code(self, code: str, organization_id: UUID) -> DestinationMarket | None:
        return (
            self.db.query(DestinationMarket)
            .filter(
                DestinationMarket.code == code,
                DestinationMarket.organization_id == organization_id,
                DestinationMarket.deleted_at.is_(None),
            )
            .first()
        )

    def code_exists(self, code: str, organization_id: UUID, exclude_id: UUID | None = None) -> bool:
        q = self.db.query(DestinationMarket.id).filter(
            DestinationMarket.code == code,
            DestinationMarket.organization_id == organization_id,
            DestinationMarket.deleted_at.is_(None),
        )
        if exclude_id:
            q = q.filter(DestinationMarket.id != exclude_id)
        return q.first() is not None

    def list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        is_active: bool | None = None,
        country: str | None = None,
        search: str | None = None,
    ) -> tuple[list[DestinationMarket], int]:
        q = self.db.query(DestinationMarket).filter(
            DestinationMarket.organization_id == organization_id,
            DestinationMarket.deleted_at.is_(None),
        )
        if is_active is not None:
            q = q.filter(DestinationMarket.is_active == is_active)
        if country:
            q = q.filter(DestinationMarket.country.ilike(f"%{country}%"))
        if search:
            q = q.filter(
                DestinationMarket.name.ilike(f"%{search}%")
                | DestinationMarket.code.ilike(f"%{search}%")
            )
        total = q.count()
        items = (
            q.order_by(DestinationMarket.name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update(self, market: DestinationMarket, data: dict) -> DestinationMarket:
        for k, v in data.items():
            setattr(market, k, v)
        self.db.commit()
        self.db.refresh(market)
        return market

    def soft_delete(self, market: DestinationMarket, user_id: UUID) -> None:
        market.deleted_at = datetime.now(UTC)
        market.updated_by = user_id
        self.db.commit()
