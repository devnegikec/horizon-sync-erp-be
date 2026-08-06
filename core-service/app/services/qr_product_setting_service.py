"""Service layer for QR Product Settings"""

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.repositories.qr_product_setting_repository import QRProductSettingRepository
from app.schemas.qr_product_setting import QRProductSettingCreate, QRProductSettingUpdate


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

    def create(
        self, data: QRProductSettingCreate, organization_id: UUID, user_id: UUID
    ):
        if self.repo.value_exists(data.setting_type, data.value, organization_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Setting '{data.setting_type}' with value '{data.value}' "
                    f"already exists for this organization."
                ),
            )
        payload = data.model_dump()
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        return self.repo.create(payload)

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
        if "value" in payload and payload["value"] != setting.value:
            if self.repo.value_exists(
                setting.setting_type, payload["value"], organization_id, setting_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"Setting '{setting.setting_type}' with value "
                        f"'{payload['value']}' already exists."
                    ),
                )
        payload["updated_by"] = user_id
        return self.repo.update(setting, payload)

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
