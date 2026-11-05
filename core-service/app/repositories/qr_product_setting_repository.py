"""Repository for QR Product Settings"""

import builtins
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.qr_block import QRBlock
from app.models.qr_product import QRProduct
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

    def get_by_id(
        self, setting_id: UUID, organization_id: UUID
    ) -> QRProductSetting | None:
        setting = (
            self.db.query(QRProductSetting)
            .filter(
                QRProductSetting.id == setting_id,
                QRProductSetting.organization_id == organization_id,
                QRProductSetting.deleted_at.is_(None),
            )
            .first()
        )
        if setting:
            setting.usage_count = self.reference_counts(
                [setting.id], organization_id
            ).get(setting.id, 0)
        return setting

    def value_exists(
        self,
        setting_type: str,
        value: str,
        organization_id: UUID,
        exclude_id: UUID | None = None,
    ) -> bool:
        normalized_value = value.strip()
        q = self.db.query(QRProductSetting.id).filter(
            QRProductSetting.setting_type == setting_type,
            QRProductSetting.organization_id == organization_id,
            QRProductSetting.deleted_at.is_(None),
        )
        q = q.filter(
            func.lower(func.trim(QRProductSetting.value)) == normalized_value.lower()
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
        usage_counts = self.reference_counts(
            [setting.id for setting in items], organization_id
        )
        for setting in items:
            setting.usage_count = usage_counts.get(setting.id, 0)
        return items, total

    def reference_counts(
        self, setting_ids: builtins.list[UUID], organization_id: UUID
    ) -> dict[UUID, int]:
        counts = dict.fromkeys(setting_ids, 0)
        if not setting_ids:
            return counts

        for model, columns in (
            (
                QRProduct,
                (QRProduct.shelf_life_setting_id, QRProduct.serial_prefix_setting_id),
            ),
            (QRBlock, (QRBlock.channel_setting_id, QRBlock.destination_setting_id)),
        ):
            for column in columns:
                rows = (
                    self.db.query(column, func.count(model.id))
                    .filter(
                        column.in_(setting_ids),
                        model.organization_id == organization_id,
                        model.deleted_at.is_(None),
                    )
                    .group_by(column)
                    .all()
                )
                for setting_id, count in rows:
                    counts[setting_id] = counts.get(setting_id, 0) + int(count)
        return counts

    def update(self, setting: QRProductSetting, data: dict) -> QRProductSetting:
        for k, v in data.items():
            setattr(setting, k, v)
        self.db.commit()
        self.db.refresh(setting)
        return setting

    def is_referenced_by_product(self, setting_id: UUID, organization_id: UUID) -> bool:
        product_reference = (
            self.db.query(QRProduct.id)
            .filter(
                or_(
                    QRProduct.shelf_life_setting_id == setting_id,
                    QRProduct.serial_prefix_setting_id == setting_id,
                ),
                QRProduct.organization_id == organization_id,
                QRProduct.deleted_at.is_(None),
            )
            .first()
            is not None
        )
        if product_reference:
            return True
        return (
            self.db.query(QRBlock.id)
            .filter(
                or_(
                    QRBlock.channel_setting_id == setting_id,
                    QRBlock.destination_setting_id == setting_id,
                ),
                QRBlock.organization_id == organization_id,
                QRBlock.deleted_at.is_(None),
            )
            .first()
            is not None
        )

    def soft_delete(self, setting: QRProductSetting, user_id: UUID) -> None:
        setting.deleted_at = datetime.now(UTC)
        setting.updated_by = user_id
        self.db.commit()
