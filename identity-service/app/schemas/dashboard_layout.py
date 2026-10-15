"""Schemas for the organization dashboard layout (Settings → Dashboard Layout)."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class DashboardWidgetConfig(BaseModel):
    """One widget toggle supplied by the client when saving a layout."""

    id: str = Field(..., min_length=1, max_length=64)
    enabled: bool = True
    order: int | None = Field(
        None,
        ge=0,
        le=100_000,
        description="Display order. Omit to keep the catalogue default.",
    )


class DashboardLayoutUpdate(BaseModel):
    """Request body for saving a layout.

    Widgets not listed fall back to their catalogue defaults, so sending the full
    list (as the Settings tab does) is a full replacement.
    """

    widgets: list[DashboardWidgetConfig] = Field(default_factory=list, max_length=200)

    @field_validator("widgets")
    @classmethod
    def _reject_duplicate_ids(
        cls, value: list[DashboardWidgetConfig]
    ) -> list[DashboardWidgetConfig]:
        seen: set[str] = set()
        for widget in value:
            if widget.id in seen:
                raise ValueError(f"duplicate widget id '{widget.id}'")
            seen.add(widget.id)
        return value


class DashboardWidgetState(BaseModel):
    """A catalogue widget merged with this organization's saved state."""

    # ── catalogue definition (server-owned) ───────────────────────────────
    id: str
    label: str
    description: str
    group: str
    group_label: str
    chart_type: str
    default_enabled: bool
    default_order: int
    permission: str | None = None
    data_source: str | None = None
    requires_feature_flag: str | None = None
    configurable: list[str] = Field(default_factory=list)

    # ── saved state ───────────────────────────────────────────────────────
    enabled: bool
    order: int
    is_default: bool = Field(
        ...,
        description="True when the organization has never overridden this widget.",
    )


class DashboardLayoutResponse(BaseModel):
    """Response for GET/PUT/DELETE of the dashboard layout."""

    organization_id: UUID
    version: int
    customized: bool = Field(
        ..., description="True once the organization has saved a layout."
    )
    updated_at: datetime | None = None
    updated_by: UUID | None = None

    widgets: list[DashboardWidgetState] = Field(default_factory=list)
    enabled_widget_ids: list[str] = Field(default_factory=list)
    enabled_count: int = 0
    total_widgets: int = 0

    groups: dict[str, str] = Field(
        default_factory=dict,
        description="Widget group key -> human label, in render order.",
    )
    ignored_widget_ids: list[str] = Field(
        default_factory=list,
        description="Ids sent by the client that are not in the catalogue.",
    )
