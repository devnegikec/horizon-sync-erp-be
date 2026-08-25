"""Feature flag repository"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.feature_flag import FeatureFlag


class FeatureFlagRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> FeatureFlag:
        flag = FeatureFlag(**data)
        self.db.add(flag)
        self.db.commit()
        self.db.refresh(flag)
        return flag

    def get_by_id(self, flag_id: UUID) -> FeatureFlag | None:
        return self.db.query(FeatureFlag).filter(FeatureFlag.id == flag_id).first()

    def get_by_name(self, name: str, scope: str = "GLOBAL") -> FeatureFlag | None:
        return (
            self.db.query(FeatureFlag)
            .filter(FeatureFlag.name == name, FeatureFlag.scope == scope)
            .first()
        )

    def get_by_name_for_tenant(
        self, name: str, organization_id: UUID
    ) -> FeatureFlag | None:
        return (
            self.db.query(FeatureFlag)
            .filter(
                FeatureFlag.name == name,
                FeatureFlag.scope == "TENANT",
                FeatureFlag.tenant_id == organization_id,
            )
            .first()
        )

    def list_all(self) -> list[FeatureFlag]:
        return self.db.query(FeatureFlag).all()

    def list_by_scope(self, scope: str) -> list[FeatureFlag]:
        return (
            self.db.query(FeatureFlag)
            .filter(FeatureFlag.scope == scope)
            .all()
        )

    def list_by_tenant(self, organization_id: UUID) -> list[FeatureFlag]:
        return (
            self.db.query(FeatureFlag)
            .filter(
                FeatureFlag.scope == "TENANT",
                FeatureFlag.tenant_id == organization_id,
            )
            .all()
        )

    def update(self, flag: FeatureFlag, data: dict) -> FeatureFlag:
        for k, v in data.items():
            if hasattr(flag, k):
                setattr(flag, k, v)
        self.db.commit()
        self.db.refresh(flag)
        return flag

    def delete(self, flag: FeatureFlag) -> None:
        self.db.delete(flag)
        self.db.commit()

    def name_exists(self, name: str, exclude_id: UUID | None = None) -> bool:
        q = self.db.query(FeatureFlag).filter(FeatureFlag.name == name)
        if exclude_id is not None:
            q = q.filter(FeatureFlag.id != exclude_id)
        return q.first() is not None
