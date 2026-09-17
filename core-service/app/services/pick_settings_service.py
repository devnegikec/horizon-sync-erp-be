"""Pick settings service + read-once config resolver (PR-02 / T-17).

- ``PickSettingsService`` reads/writes tenant-scoped overrides in
  ``pick_settings`` and always merges them over the code-defined defaults.
- ``PickConfigResolver`` is the server-side enforcement helper: it snapshots the
  effective settings once per pick session and serves typed reads from memory,
  so pick workflows never trust the UI (NFR-007) and never hit the DB per scan.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.pick_config import (
    BOOL,
    ENUM,
    INT,
    LIST,
    NUMERIC,
    default_value,
    normalize_key,
    validate_value,
)
from app.models.pick_setting import PickSetting

logger = logging.getLogger(__name__)


class PickSettingsService:
    """Load/save tenant-scoped ``pick.*`` overrides."""

    def __init__(self, db: Session):
        self.db = db

    def get_settings(self, organization_id: UUID) -> dict[str, Any]:
        """Return effective settings: defaults merged with org overrides."""
        settings = {key: default_value(key) for key in self._all_keys()}
        rows = (
            self.db.query(PickSetting)
            .filter(PickSetting.organization_id == organization_id)
            .all()
        )
        for row in rows:
            if row.key in settings:
                settings[row.key] = row.value
        return settings

    def get_value(self, organization_id: UUID, key: str) -> Any:
        """Return the effective value for a single key."""
        key = normalize_key(key)
        row = (
            self.db.query(PickSetting)
            .filter(
                PickSetting.organization_id == organization_id,
                PickSetting.key == key,
            )
            .first()
        )
        if row is not None:
            return row.value
        return default_value(key)

    def update_settings(
        self,
        organization_id: UUID,
        updates: dict[str, Any],
        updated_by: UUID | None = None,
    ) -> dict[str, Any]:
        """Validate and upsert overrides; returns the new effective settings.

        Raises ``ValueError`` for unknown keys or invalid values.
        """
        # Validate everything first so a bad payload changes nothing.
        validated: dict[str, Any] = {}
        for raw_key, raw_value in updates.items():
            key = normalize_key(raw_key)
            validated[key] = validate_value(key, raw_value)

        existing = {
            row.key: row
            for row in self.db.query(PickSetting)
            .filter(PickSetting.organization_id == organization_id)
            .all()
        }

        for key, value in validated.items():
            row = existing.get(key)
            if row is None:
                row = PickSetting(
                    organization_id=organization_id,
                    key=key,
                    value=value,
                    updated_by=updated_by,
                )
                self.db.add(row)
            else:
                row.value = value
                row.updated_by = updated_by

        self.db.commit()
        return self.get_settings(organization_id)

    def reset_to_defaults(self, organization_id: UUID) -> None:
        """Delete all overrides for the organization (falls back to defaults)."""
        self.db.query(PickSetting).filter(
            PickSetting.organization_id == organization_id
        ).delete(synchronize_session=False)
        self.db.commit()

    @staticmethod
    def _all_keys() -> list[str]:
        from app.core.pick_config import PICK_CONFIG_CATALOG

        return list(PICK_CONFIG_CATALOG)


class PickConfigResolver:
    """Read-once snapshot of effective pick settings with typed accessors.

    Instantiate once per pick session (via ``from_org``) and read from memory
    thereafter. Every accessor falls back to the code default for unset keys.
    """

    def __init__(self, settings: dict[str, Any] | None = None):
        self._settings: dict[str, Any] = settings or {}

    @classmethod
    def from_org(cls, db: Session, organization_id: UUID) -> PickConfigResolver:
        return cls(PickSettingsService(db).get_settings(organization_id))

    def resolve(self, key: str) -> Any:
        """Return the effective value for ``key`` (default fallback)."""
        key = normalize_key(key)
        if key in self._settings:
            return self._settings[key]
        return default_value(key)

    def get_bool(self, key: str) -> bool:
        value = self.resolve(key)
        return bool(value)

    def get_int(self, key: str) -> int:
        value = self.resolve(key)
        return int(value)

    def get_numeric(self, key: str) -> float:
        return float(self.resolve(key))

    def get_enum(self, key: str) -> str:
        return str(self.resolve(key))

    def get_list(self, key: str) -> list[str]:
        value = self.resolve(key)
        return list(value) if isinstance(value, list) else []

    def snapshot(self) -> dict[str, Any]:
        """Return a copy of the effective settings dict."""
        return dict(self._settings)


# Re-export type constants for convenience in downstream modules.
__all__ = [
    "PickSettingsService",
    "PickConfigResolver",
    "BOOL",
    "INT",
    "NUMERIC",
    "ENUM",
    "LIST",
]
