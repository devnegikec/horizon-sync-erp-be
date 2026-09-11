"""Shared expiry calculation helpers for QR activation workflows."""

from decimal import Decimal, InvalidOperation
from uuid import UUID

from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session

from app.models.qr_product_setting import QRProductSetting


def resolve_shelf_life_months(
    db: Session,
    setting_id: UUID | None,
    organization_id: UUID,
) -> int | None:
    """Resolve a product's active organization-scoped shelf-life setting."""
    if setting_id is None:
        return None

    setting = (
        db.query(QRProductSetting)
        .filter(
            QRProductSetting.id == setting_id,
            QRProductSetting.organization_id == organization_id,
            QRProductSetting.setting_type == "shelf_life",
            QRProductSetting.is_active.is_(True),
            QRProductSetting.deleted_at.is_(None),
        )
        .first()
    )
    if not setting:
        return None

    try:
        months = Decimal(str(setting.value).strip())
    except (InvalidOperation, TypeError, ValueError):
        return None

    if months <= 0 or months != months.to_integral_value():
        return None
    return int(months)


def calculate_shelf_life_expiry(manufacturing_date, months: int):
    """Calculate expiry using calendar months, preserving month-end behavior."""
    return manufacturing_date + relativedelta(months=months)
