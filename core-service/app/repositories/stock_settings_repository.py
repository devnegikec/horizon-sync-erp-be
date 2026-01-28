"""Stock settings repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.stock_settings import StockSettings


class StockSettingsRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_organization(self, organization_id: UUID) -> StockSettings | None:
        return (
            self.db.query(StockSettings)
            .filter(StockSettings.organization_id == organization_id)
            .first()
        )

    def create(self, data: dict) -> StockSettings:
        s = StockSettings(**data)
        self.db.add(s)
        self.db.commit()
        self.db.refresh(s)
        return s

    def update(self, s: StockSettings, data: dict) -> StockSettings:
        for k, v in data.items():
            if hasattr(s, k):
                setattr(s, k, v)
        self.db.commit()
        self.db.refresh(s)
        return s
