"""Repository for QR Product Settings"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.qr_product_setting import QRProductSetting


class QRProductSettingRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> QRProductSetting:
        setting = QRProductSetting(**data)
        self.db.add(setting)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def get_by_id(self, setting_id: UUID, organization_id: UUID) -> QRProductSetting | None:
        return (
            self.db.query(QRProductSetting)
            .filter(
                QRProductSetting.id == setting_id,
                QRProductSetting.organization_id == organization_id,
                QRProductSetting.deleted_at.is_(None),
            )
            .first()
        )

    def value_exists(
        self,
        setting_type: str,
        value: str,
        organization_id: UUID,
        exclude_id: UUID | None = None,
    ) -> bool:
        q = self.db.query(QRProductSetting.id).filter(
            QRProductSetting.setting_type == setting_type,
            QRProductSetting.value == value,
            QRProductSetting.organization_id == organization_id,
            QRProductSetting.deleted_at.is_(None),
        )
        if exclude_id:
            q = q.filter(QRProductSetting.id != exclude_id)
        return q.first() is not None

    def list(
        self,
        organization_id: UUID,
        setting_type: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[QRProductSetting], int]:
        q = self.db.query(QRProductSetting).filter(
            QRProductSetting.organization_id == organization_id,
            QRProductSetting.deleted_at.is_(None),
        )
        if setting_type:
            q = q.filter(QRProductSetting.setting_type == setting_type)
        if is_active is not None:
            q = q.filter(QRProductSetting.is_active == is_active)
        if search:
            q = q.filter(
                QRProductSetting.label.ilike(f"%{search}%")
                | QRProductSetting.value.ilike(f"%{search}%")
            )
        total = q.count()
        items = (
            q.order_by(QRProductSetting.setting_type, QRProductSetting.sort_order)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def update(self, setting: QRProductSetting, data: dict) -> QRProductSetting:
        for k, v in data.items():
            setattr(setting, k, v)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def soft_delete(self, setting: QRProductSetting, user_id: UUID) -> None:
        setting.deleted_at = datetime.now(UTC)
        setting.updated_by = user_id
        self.db.commit()
