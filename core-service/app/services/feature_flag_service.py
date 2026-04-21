"""Feature flag service layer with evaluation logic and helper."""

import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.feature_flag_repository import FeatureFlagRepository
from app.schemas.feature_flag import (
    FeatureFlagCreate,
    FeatureFlagEvaluation,
    FeatureFlagListResponse,
    FeatureFlagResponse,
    FeatureFlagUpdate,
)

logger = logging.getLogger(__name__)


class FeatureFlagService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = FeatureFlagRepository(db)

    def create_flag(self, data: FeatureFlagCreate) -> FeatureFlagResponse:
        if self.repo.name_exists(data.name):
            raise HTTPException(
                status_code=409,
                detail=f"Feature flag with name '{data.name}' already exists",
            )
        flag_data = data.model_dump()
        flag_data["scope"] = "GLOBAL"
        flag_data["tenant_id"] = None
        flag_data["user_id"] = None
        flag = self.repo.create(flag_data)
        return FeatureFlagResponse.model_validate(flag)

    def get_flag(self, flag_id: UUID) -> FeatureFlagResponse:
        flag = self.repo.get_by_id(flag_id)
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        return FeatureFlagResponse.model_validate(flag)

    def list_flags(self) -> FeatureFlagListResponse:
        flags = self.repo.list_all()
        return FeatureFlagListResponse(
            flags=[FeatureFlagResponse.model_validate(f) for f in flags]
        )

    def update_flag(
        self, flag_id: UUID, data: FeatureFlagUpdate
    ) -> FeatureFlagResponse:
        flag = self.repo.get_by_id(flag_id)
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        update_data = data.model_dump(exclude_unset=True)
        if "name" in update_data and update_data["name"] != flag.name:
            if self.repo.name_exists(update_data["name"], exclude_id=flag_id):
                raise HTTPException(
                    status_code=409,
                    detail=f"Feature flag with name '{update_data['name']}' already exists",
                )
        updated = self.repo.update(flag, update_data)
        return FeatureFlagResponse.model_validate(updated)

    def delete_flag(self, flag_id: UUID) -> None:
        flag = self.repo.get_by_id(flag_id)
        if not flag:
            raise HTTPException(status_code=404, detail="Feature flag not found")
        self.repo.delete(flag)

    def evaluate(self, feature_name: str) -> FeatureFlagEvaluation:
        try:
            flag = self.repo.get_by_name(feature_name, scope="GLOBAL")
            enabled = flag.enabled if flag else False
            visible = flag.visible if flag else True
            logger.info(
                "Feature flag '%s' evaluated: enabled=%s, visible=%s",
                feature_name,
                enabled,
                visible,
            )
            return FeatureFlagEvaluation(
                feature_name=feature_name, enabled=enabled, visible=visible
            )
        except Exception:
            logger.error(
                "Error evaluating feature flag '%s'", feature_name, exc_info=True
            )
            return FeatureFlagEvaluation(
                feature_name=feature_name, enabled=False, visible=True
            )


def is_feature_enabled(feature_name: str, db: Session) -> bool:
    """Check if a GLOBAL feature flag is enabled. Returns False on any error."""
    try:
        repo = FeatureFlagRepository(db)
        flag = repo.get_by_name(feature_name, scope="GLOBAL")
        enabled = flag.enabled if flag else False
        logger.info(
            "Feature flag '%s' evaluated: %s",
            feature_name,
            "enabled" if enabled else "disabled",
        )
        return enabled
    except Exception:
        logger.error(
            "Error evaluating feature flag '%s'", feature_name, exc_info=True
        )
        return False


def is_feature_visible(feature_name: str, db: Session) -> bool:
    """Check if a GLOBAL feature flag is visible. Returns True on any error (safe default — show the feature if unsure)."""
    try:
        repo = FeatureFlagRepository(db)
        flag = repo.get_by_name(feature_name, scope="GLOBAL")
        visible = flag.visible if flag else True
        logger.info(
            "Feature flag '%s' visibility: %s",
            feature_name,
            "visible" if visible else "hidden",
        )
        return visible
    except Exception:
        logger.error(
            "Error checking visibility for feature flag '%s'",
            feature_name,
            exc_info=True,
        )
        return True
