"""Schemas for the pick configuration layer (PR-02 / T-17)."""

from typing import Any

from pydantic import BaseModel, Field


class PickConfigCatalogItem(BaseModel):
    """A single catalog entry for the settings editor."""

    key: str
    type: str
    default: Any
    allowed: list[str] | None = None
    label: str
    description: str


class PickConfigCatalogResponse(BaseModel):
    """Response for the full pick config catalog."""

    config: list[PickConfigCatalogItem]


class PickSettingsUpdate(BaseModel):
    """Body for upserting pick settings overrides.

    Keys may be sent with or without the ``pick.`` prefix.
    """

    settings: dict[str, Any] = Field(
        ..., description="Map of pick config key → value overrides"
    )


class PickSettingsResponse(BaseModel):
    """Effective settings (defaults merged with overrides) for an org."""

    organization_id: str
    settings: dict[str, Any]
