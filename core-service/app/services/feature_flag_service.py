"""Feature flag service layer with evaluation logic and helper."""

import logging
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.repositories.feature_flag_repository import FeatureFlagRepository
from app.core.constants import DEFAULT_SCOPE, TENANT_SCOPE
from app.schemas.feature_flag import (
    FeatureFlagCreate,
    FeatureFlagEvaluation,
    FeatureFlagListResponse,
    FeatureFlagResponse,
    FeatureFlagTenantUpdate,
    FeatureFlagUpdate,
    TenantFeatureFlagResponse,
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
        flag_data["scope"] = DEFAULT_SCOPE
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

    def list_flags_for_org(
        self, organization_id: UUID
    ) -> list[TenantFeatureFlagResponse]:
        """Return ONLY tenant-scoped flags for the organization.

        Global flags are managed exclusively by system administrators and are
        intentionally NOT exposed to organization admins/owners. A tenant can
        only see (and override) flags scoped to its own organization.
        """
        tenant_flags = self.repo.list_by_tenant(organization_id)
        return [
            TenantFeatureFlagResponse(
                name=flag.name,
                description=flag.description,
                enabled=flag.enabled,
                visible=flag.visible,
                scope=TENANT_SCOPE,
                tenant_id=flag.tenant_id,
                inherited=False,
            )
            for flag in sorted(tenant_flags, key=lambda f: f.name)
        ]

    def upsert_tenant_flag(
        self,
        organization_id: UUID,
        feature_name: str,
        data: FeatureFlagTenantUpdate,
    ) -> FeatureFlagResponse:
        """Create or update a TENANT-scoped flag override for an organization."""
        flag = self.repo.get_by_name_for_tenant(feature_name, organization_id)
        if flag is None:
            flag = self.repo.create(
                {
                    "name": feature_name,
                    "scope": TENANT_SCOPE,
                    "tenant_id": organization_id,
                    "enabled": data.enabled if data.enabled is not None else False,
                    "visible": data.visible if data.visible is not None else True,
                    "description": data.description,
                }
            )
        else:
            update_data = data.model_dump(exclude_unset=True)
            flag = self.repo.update(flag, update_data)
        return FeatureFlagResponse.model_validate(flag)

    def evaluate(self, feature_name: str) -> FeatureFlagEvaluation:
        try:
            flag = self.repo.get_by_name(feature_name, scope=DEFAULT_SCOPE)
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

    def evaluate_for_org(
        self, feature_name: str, organization_id: UUID
    ) -> FeatureFlagEvaluation:
        """Evaluate a flag for a specific tenant: tenant override first, else global."""
        try:
            flag = self.repo.get_by_name_for_tenant(feature_name, organization_id)
            if flag is None:
                flag = self.repo.get_by_name(feature_name, scope=DEFAULT_SCOPE)
            enabled = flag.enabled if flag else False
            visible = flag.visible if flag else True
            return FeatureFlagEvaluation(
                feature_name=feature_name, enabled=enabled, visible=visible
            )
        except Exception:
            logger.error(
                "Error evaluating feature flag '%s' for org %s",
                feature_name,
                organization_id,
                exc_info=True,
            )
            return FeatureFlagEvaluation(
                feature_name=feature_name, enabled=False, visible=True
            )


def is_feature_enabled(feature_name: str, db: Session) -> bool:
    """Check if a GLOBAL feature flag is enabled. Returns False on any error."""
    try:
        repo = FeatureFlagRepository(db)
        flag = repo.get_by_name(feature_name, scope=DEFAULT_SCOPE)
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


def is_feature_enabled_for_org(
    feature_name: str, db: Session, organization_id: UUID
) -> bool:
    """Check a tenant-scoped flag first, then fall back to GLOBAL. False on error."""
    try:
        repo = FeatureFlagRepository(db)
        flag = repo.get_by_name_for_tenant(feature_name, organization_id)
        if flag is None:
            flag = repo.get_by_name(feature_name, scope=DEFAULT_SCOPE)
        return flag.enabled if flag else False
    except Exception:
        logger.error(
            "Error evaluating feature flag '%s' for org %s",
            feature_name,
            organization_id,
            exc_info=True,
        )
        return False


def is_feature_visible(feature_name: str, db: Session) -> bool:
    """Check if a GLOBAL feature flag is visible. Returns True on any error (safe default — show the feature if unsure)."""
    try:
        repo = FeatureFlagRepository(db)
        flag = repo.get_by_name(feature_name, scope=DEFAULT_SCOPE)
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
