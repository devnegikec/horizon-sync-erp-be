"""Service layer for QR Product Settings"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.repositories.qr_product_setting_repository import QRProductSettingRepository
from app.schemas.qr_product_setting import (
    QRProductSettingCreate,
    QRProductSettingUpdate,
)


class QRProductSettingService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QRProductSettingRepository(db)

    def _paginate(self, total: int, page: int, page_size: int) -> dict:
        total_pages = max(1, (total + page_size - 1) // page_size)
        return {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }

    # ── CRUD ──────────────────────────────────────────────────────────────────

    @staticmethod
    def _normalize_value(setting_type: str, value: str) -> str:
        normalized = value.strip()
        return normalized.upper() if setting_type == "serial_prefix" else normalized

    @staticmethod
    def _duplicate_error(setting_type: str, value: str) -> HTTPException:
        if setting_type == "serial_prefix":
            detail = f"Serial prefix '{value}' already exists for this organization."
        elif setting_type == "channel":
            detail = f"Channel '{value}' already exists for this organization."
        elif setting_type == "destination":
            detail = f"Destination '{value}' already exists for this organization."
        elif setting_type == "shelf_life":
            detail = f"Shelf life value '{value}' already exists for this organization."
        else:
            detail = f"Setting '{setting_type}' with value '{value}' already exists."
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=detail)

    def create(
        self, data: QRProductSettingCreate, organization_id: UUID, user_id: UUID
    ):
        normalized_value = self._normalize_value(data.setting_type, data.value)
        if self.repo.value_exists(data.setting_type, normalized_value, organization_id):
            raise self._duplicate_error(data.setting_type, normalized_value)
        data = data.model_copy(update={"value": normalized_value})
        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        try:
            return self.repo.create(payload)
        except IntegrityError as exc:
            self.db.rollback()
            if "qr_prod_settings" in str(exc).lower() or data.setting_type == "serial_prefix":
                raise self._duplicate_error(data.setting_type, normalized_value) from exc
            raise

    def list_settings(
        self,
        organization_id: UUID,
        setting_type: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ):
        items, total = self.repo.list(
            organization_id, setting_type, is_active, search, page, page_size
        )
        return {
            "settings": items,
            "pagination": self._paginate(total, page, page_size),
        }

    def get_setting(self, setting_id: UUID, organization_id: UUID):
        setting = self.repo.get_by_id(setting_id, organization_id)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR product setting not found.",
            )
        return setting

    def update_setting(
        self,
        setting_id: UUID,
        data: QRProductSettingUpdate,
        organization_id: UUID,
        user_id: UUID,
    ):
        setting = self.repo.get_by_id(setting_id, organization_id)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR product setting not found.",
            )
        payload = {k: v for k, v in data.model_dump().items() if v is not None}
        if "value" in payload:
            payload["value"] = self._normalize_value(setting.setting_type, payload["value"])
            if self.repo.value_exists(
                setting.setting_type, payload["value"], organization_id, setting_id
            ):
                raise self._duplicate_error(setting.setting_type, payload["value"])
        payload["updated_by"] = user_id
        try:
            return self.repo.update(setting, payload)
        except IntegrityError as exc:
            self.db.rollback()
            if "qr_prod_settings" in str(exc).lower() or setting.setting_type == "serial_prefix":
                raise self._duplicate_error(setting.setting_type, payload.get("value", setting.value)) from exc
            raise

    def delete_setting(
        self, setting_id: UUID, organization_id: UUID, user_id: UUID
    ) -> None:
        setting = self.repo.get_by_id(setting_id, organization_id)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="QR product setting not found.",
            )
        if self.repo.is_referenced_by_product(setting_id, organization_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Setting is referenced by a product and cannot be deleted. "
                    "Reassign the product before deleting this setting."
                ),
            )
        self.repo.soft_delete(setting, user_id)
