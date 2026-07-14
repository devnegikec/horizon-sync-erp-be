"""Stock settings service - one per organization"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import StockSettingsNotFoundException
from app.models.stock_settings import StockSettings
from app.repositories.stock_settings_repository import StockSettingsRepository
from app.schemas.stock_settings import StockSettingsCreate, StockSettingsUpdate


class StockSettingsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = StockSettingsRepository(db)

    def get(self, organization_id: UUID) -> StockSettings:
        s = self.repo.get_by_organization(organization_id)
        if not s:
            raise StockSettingsNotFoundException(
                "Stock settings not found for this organization. Create them first."
            )
        return s

    def get_or_none(self, organization_id: UUID) -> StockSettings | None:
        return self.repo.get_by_organization(organization_id)

    def create(
        self, data: StockSettingsCreate, organization_id: UUID, user_id: UUID
    ) -> StockSettings:
        existing = self.repo.get_by_organization(organization_id)
        if existing:
            d = data.model_dump()
            d["updated_by"] = user_id
            return self.repo.update(existing, d)
        d = data.model_dump()
        d["organization_id"] = organization_id
        d["created_by"] = user_id
        d["updated_by"] = user_id
        return self.repo.create(d)

    def update(
        self, data: StockSettingsUpdate, organization_id: UUID, user_id: UUID
    ) -> StockSettings:
        s = self.get_or_none(organization_id)
        if not s:
            raise StockSettingsNotFoundException(
                "Stock settings not found for this organization. Create them first."
            )
        d = data.model_dump(exclude_unset=True)
        d["updated_by"] = user_id
        return self.repo.update(s, d)

    def upsert(
        self,
        data: StockSettingsCreate | StockSettingsUpdate,
        organization_id: UUID,
        user_id: UUID,
    ) -> StockSettings:
        """Create or update. For update, pass only fields to change."""
        s = self.repo.get_by_organization(organization_id)
        if s:
            d = data.model_dump(exclude_unset=True)
            d["updated_by"] = user_id
            return self.repo.update(s, d)
        d = (
            data.model_dump()
            if isinstance(data, StockSettingsCreate)
            else data.model_dump(exclude_unset=True)
        )
        d["organization_id"] = organization_id
        d["created_by"] = user_id
        d["updated_by"] = user_id
        return self.repo.create(d)
