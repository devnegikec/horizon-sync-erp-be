"""Repository for Landing Page Config module."""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.landing_page import LandingPageConfig


class LandingPageRepository:
    """Data access for landing_page_configs table."""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> LandingPageConfig:
        config = LandingPageConfig(**data)
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def get_by_product(
        self, product_id: UUID, organization_id: UUID
    ) -> LandingPageConfig | None:
        return (
            self.db.query(LandingPageConfig)
            .filter(
                LandingPageConfig.product_id == product_id,
                LandingPageConfig.organization_id == organization_id,
            )
            .first()
        )

    def update(self, config: LandingPageConfig, data: dict) -> LandingPageConfig:
        for k, v in data.items():
            setattr(config, k, v)
        self.db.commit()
        self.db.refresh(config)
        return config

    def delete(self, config: LandingPageConfig) -> None:
        self.db.delete(config)
        self.db.commit()
