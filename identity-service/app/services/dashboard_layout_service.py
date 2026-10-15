"""Dashboard layout (Settings → Dashboard Layout) read/write service.

The layout is stored org-wide in ``organizations.extra_data["dashboard_layout"]``::

    {
      "dashboard_layout": {
        "version": 1,
        "updated_at": "2026-10-15T09:12:44.123456+00:00",
        "updated_by": "<user uuid>",
        "widgets": [{"id": "chart_inbound_outbound", "enabled": true, "order": 110}]
      }
    }

Only the *state* (id/enabled/order) is stored — the widget definitions come from
``app.core.dashboard_widgets``, so the payload stays small and adding a widget
never requires a data migration.

NOTE: ``Organization.extra_data`` is a plain ``sqlalchemy.JSON`` column, so it has
no mutation tracking. Always reassign a new dict rather than mutating in place.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.dashboard_widgets import (
    GROUP_LABELS,
    WIDGETS,
    WIDGETS_BY_ID,
)
from app.core.exceptions import OrganizationNotFoundException
from app.models.organization import Organization
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.dashboard_layout import (
    DashboardLayoutResponse,
    DashboardWidgetConfig,
    DashboardWidgetState,
)

logger = logging.getLogger(__name__)

LAYOUT_KEY = "dashboard_layout"
LAYOUT_VERSION = 1


class DashboardLayoutService:
    """Reads and writes the org-wide dashboard layout."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = OrganizationRepository(db)

    # ── internals ─────────────────────────────────────────────────────────

    def _get_org(self, organization_id: UUID) -> Organization:
        org = self.repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundException(
                f"Organization with ID {organization_id} not found"
            )
        return org

    @staticmethod
    def _stored_raw(org: Organization) -> dict:
        """Return the raw stored ``dashboard_layout`` block (never raises)."""
        extra = org.extra_data if isinstance(org.extra_data, dict) else {}
        raw = extra.get(LAYOUT_KEY)
        return raw if isinstance(raw, dict) else {}

    @staticmethod
    def _saved_overrides(org: Organization) -> dict[str, dict]:
        """Return ``{widget_id: {"enabled": bool, "order": int|None}}``."""
        raw = DashboardLayoutService._stored_raw(org)
        widgets = raw.get("widgets")
        if not isinstance(widgets, list):
            return {}
        overrides: dict[str, dict] = {}
        for item in widgets:
            if not isinstance(item, dict):
                continue
            widget_id = item.get("id")
            if not isinstance(widget_id, str) or not widget_id:
                continue
            order = item.get("order")
            overrides[widget_id] = {
                "enabled": bool(item.get("enabled", True)),
                "order": int(order) if isinstance(order, int) else None,
            }
        return overrides

    @staticmethod
    def _parse_version(raw: dict) -> int:
        """Coerce a stored version to an int, falling back to the current one."""
        value = raw.get("version")
        if isinstance(value, bool):  # bool is an int subclass — reject it
            return LAYOUT_VERSION
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return LAYOUT_VERSION

    @staticmethod
    def _parse_updated_at(raw: dict) -> datetime | None:
        value = raw.get("updated_at")
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)

    @staticmethod
    def _parse_updated_by(raw: dict) -> UUID | None:
        value = raw.get("updated_by")
        if not isinstance(value, str):
            return None
        try:
            return UUID(value)
        except ValueError:
            return None

    # ── public API ────────────────────────────────────────────────────────

    def resolve(
        self,
        org: Organization,
        ignored_widget_ids: list[str] | None = None,
    ) -> DashboardLayoutResponse:
        """Merge the catalogue with the org's saved overrides."""
        overrides = self._saved_overrides(org)

        states: list[DashboardWidgetState] = []
        for widget in WIDGETS:
            saved = overrides.get(widget.id)
            if saved is None:
                enabled = widget.default_enabled
                order = widget.default_order
                is_default = True
            else:
                enabled = saved["enabled"]
                order = (
                    saved["order"]
                    if saved["order"] is not None
                    else widget.default_order
                )
                is_default = False

            states.append(
                DashboardWidgetState(
                    id=widget.id,
                    label=widget.label,
                    description=widget.description,
                    group=widget.group,
                    group_label=GROUP_LABELS.get(widget.group, widget.group),
                    chart_type=widget.chart_type,
                    default_enabled=widget.default_enabled,
                    default_order=widget.default_order,
                    permission=widget.permission,
                    data_source=widget.data_source,
                    requires_feature_flag=widget.requires_feature_flag,
                    configurable=list(widget.configurable),
                    enabled=enabled,
                    order=order,
                    is_default=is_default,
                )
            )

        # Render order: saved order first, catalogue default as tiebreaker.
        states.sort(key=lambda s: (s.order, s.default_order, s.id))
        enabled_ids = [s.id for s in states if s.enabled]

        # Ids present in storage but no longer in the catalogue (widget removed
        # server-side) are surfaced instead of silently dropped.
        stale_ids = sorted(set(overrides) - set(WIDGETS_BY_ID))
        ignored = sorted(set(ignored_widget_ids or []) | set(stale_ids))

        raw = self._stored_raw(org)
        return DashboardLayoutResponse(
            organization_id=org.id,
            version=self._parse_version(raw),
            customized=bool(overrides),
            updated_at=self._parse_updated_at(raw),
            updated_by=self._parse_updated_by(raw),
            widgets=states,
            enabled_widget_ids=enabled_ids,
            enabled_count=len(enabled_ids),
            total_widgets=len(states),
            groups=dict(GROUP_LABELS),
            ignored_widget_ids=ignored,
        )

    def get_layout(self, organization_id: UUID) -> DashboardLayoutResponse:
        """Return the catalogue merged with the saved layout (defaults if unset)."""
        return self.resolve(self._get_org(organization_id))

    def save_layout(
        self,
        organization_id: UUID,
        widgets: list[DashboardWidgetConfig],
        updated_by: UUID | None = None,
    ) -> DashboardLayoutResponse:
        """Persist the layout. Unknown widget ids are ignored, not an error."""
        org = self._get_org(organization_id)

        ignored: list[str] = []
        payload: list[dict] = []
        seen: set[str] = set()
        for widget in widgets:
            definition = WIDGETS_BY_ID.get(widget.id)
            if definition is None:
                ignored.append(widget.id)
                continue
            if widget.id in seen:
                continue
            seen.add(widget.id)
            payload.append(
                {
                    "id": widget.id,
                    "enabled": bool(widget.enabled),
                    "order": (
                        widget.order
                        if widget.order is not None
                        else definition.default_order
                    ),
                }
            )

        extra = dict(org.extra_data or {})
        extra[LAYOUT_KEY] = {
            "version": LAYOUT_VERSION,
            "widgets": payload,
            "updated_at": datetime.now(UTC).isoformat(),
            "updated_by": str(updated_by) if updated_by else None,
        }
        # Reassign so the JSON column change is detected (no mutation tracking).
        org.extra_data = extra
        self.db.commit()
        self.db.refresh(org)

        logger.info(
            "Saved dashboard layout for org %s (%d widgets, %d ignored)",
            organization_id,
            len(payload),
            len(ignored),
        )
        return self.resolve(org, ignored_widget_ids=sorted(set(ignored)))

    def reset_layout(self, organization_id: UUID) -> DashboardLayoutResponse:
        """Remove the saved layout so every widget falls back to its default."""
        org = self._get_org(organization_id)
        extra = dict(org.extra_data or {})
        if extra.pop(LAYOUT_KEY, None) is not None:
            org.extra_data = extra
            self.db.commit()
            self.db.refresh(org)
            logger.info("Reset dashboard layout for org %s", organization_id)
        return self.resolve(org)
