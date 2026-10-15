"""Unit tests for the org dashboard layout (Settings → Dashboard Layout).

Deliberately DB-free: the shared ``db_session`` fixture is skipped unless
``RUN_DATABASE_TESTS=1`` (SQLite can't compile the PG UUID columns), so these
tests use a fake session and an unpersisted ``Organization`` instance.
"""

from uuid import UUID

import pytest

from app.core.dashboard_widgets import (
    CHART_TYPES,
    DEFAULT_ENABLED_IDS,
    GROUP_LABELS,
    GROUP_ORDER,
    WIDGETS,
    WIDGETS_BY_ID,
)
from app.core.exceptions import OrganizationNotFoundException
from app.models.organization import Organization
from app.schemas.dashboard_layout import DashboardWidgetConfig
from app.services.dashboard_layout_service import (
    LAYOUT_KEY,
    LAYOUT_VERSION,
    DashboardLayoutService,
)

ORG_ID = UUID("0cc01d20-6f0f-4266-8042-86d1b73b998a")
USER_ID = UUID("22222222-2222-2222-2222-222222222222")


class _FakeSession:
    """Minimal stand-in for a SQLAlchemy Session — records commit/refresh."""

    def __init__(self) -> None:
        self.commit_count = 0
        self.refreshed: list = []

    def commit(self) -> None:
        self.commit_count += 1

    def refresh(self, obj) -> None:  # noqa: ANN001
        self.refreshed.append(obj)


def _org(extra_data: dict | None = None) -> Organization:
    org = Organization(
        id=ORG_ID,
        name="Test Organization",
        slug="test-org",
        extra_data=extra_data if extra_data is not None else {},
    )
    return org


def _service(org: Organization | None) -> tuple[DashboardLayoutService, _FakeSession]:
    db = _FakeSession()
    svc = DashboardLayoutService(db)
    svc.repo.get_by_id = lambda organization_id, _org=org: (  # type: ignore[method-assign]
        _org if _org is not None and str(_org.id) == str(organization_id) else None
    )
    return svc, db


# ── catalogue integrity ────────────────────────────────────────────────────


class TestWidgetCatalogue:
    def test_ids_are_unique(self):
        ids = [w.id for w in WIDGETS]
        assert len(ids) == len(set(ids))

    def test_ids_are_snake_case(self):
        for widget in WIDGETS:
            assert widget.id == widget.id.lower()
            assert " " not in widget.id
            assert "-" not in widget.id

    def test_every_widget_maps_to_a_known_group(self):
        for widget in WIDGETS:
            assert widget.group in GROUP_ORDER, widget.id
            assert widget.group in GROUP_LABELS

    def test_every_group_has_a_label(self):
        for group in GROUP_ORDER:
            assert group in GROUP_LABELS

    def test_chart_types_are_supported(self):
        for widget in WIDGETS:
            assert widget.chart_type in CHART_TYPES, widget.id

    def test_default_orders_are_unique(self):
        orders = [w.default_order for w in WIDGETS]
        assert len(orders) == len(set(orders))

    def test_labels_and_descriptions_present(self):
        for widget in WIDGETS:
            assert widget.label.strip(), widget.id
            assert widget.description.strip(), widget.id

    def test_has_some_defaults_enabled(self):
        assert DEFAULT_ENABLED_IDS
        assert len(DEFAULT_ENABLED_IDS) < len(WIDGETS)

    def test_by_id_index_matches(self):
        assert set(WIDGETS_BY_ID) == {w.id for w in WIDGETS}


# ── read / merge ───────────────────────────────────────────────────────────


class TestResolveLayout:
    def test_unset_layout_returns_catalogue_defaults(self):
        svc, _ = _service(_org())
        result = svc.get_layout(ORG_ID)

        assert result.organization_id == ORG_ID
        assert result.customized is False
        assert result.updated_at is None
        assert result.updated_by is None
        assert result.total_widgets == len(WIDGETS)
        assert all(w.is_default for w in result.widgets)

        expected = sorted(WIDGETS, key=lambda w: (w.default_order, w.id))
        assert [w.id for w in result.widgets] == [w.id for w in expected]
        assert result.enabled_widget_ids == [
            w.id for w in expected if w.default_enabled
        ]
        assert result.enabled_count == len(DEFAULT_ENABLED_IDS)

    def test_null_extra_data_is_tolerated(self):
        svc, _ = _service(_org(None))
        result = svc.get_layout(ORG_ID)
        assert result.customized is False
        assert result.total_widgets == len(WIDGETS)

    def test_saved_overrides_are_applied(self):
        org = _org(
            {
                LAYOUT_KEY: {
                    "version": LAYOUT_VERSION,
                    "updated_at": "2026-10-15T09:12:44+00:00",
                    "updated_by": str(USER_ID),
                    "widgets": [
                        {"id": "kpi_low_stock", "enabled": False, "order": 999},
                        {"id": "chart_qr_scan_trend", "enabled": True, "order": 1},
                    ],
                }
            }
        )
        svc, _ = _service(org)
        result = svc.get_layout(ORG_ID)

        assert result.customized is True
        assert result.updated_by == USER_ID
        assert result.updated_at is not None
        assert result.version == LAYOUT_VERSION

        by_id = {w.id: w for w in result.widgets}
        assert by_id["kpi_low_stock"].enabled is False
        assert by_id["kpi_low_stock"].order == 999
        assert by_id["kpi_low_stock"].is_default is False

        assert by_id["chart_qr_scan_trend"].enabled is True
        assert by_id["chart_qr_scan_trend"].is_default is False

        # saved order wins over the catalogue default
        assert result.widgets[0].id == "chart_qr_scan_trend"
        assert "kpi_low_stock" not in result.enabled_widget_ids
        assert "chart_qr_scan_trend" in result.enabled_widget_ids

    def test_widgets_removed_from_catalogue_are_reported(self):
        org = _org(
            {
                LAYOUT_KEY: {
                    "widgets": [{"id": "chart_no_longer_exists", "enabled": True}]
                }
            }
        )
        svc, _ = _service(org)
        result = svc.get_layout(ORG_ID)

        assert result.ignored_widget_ids == ["chart_no_longer_exists"]
        assert "chart_no_longer_exists" not in [w.id for w in result.widgets]

    def test_unknown_org_raises(self):
        svc, _ = _service(None)
        with pytest.raises(OrganizationNotFoundException):
            svc.get_layout(ORG_ID)


# ── write ──────────────────────────────────────────────────────────────────


class TestSaveLayout:
    def test_save_persists_and_returns_merged(self):
        org = _org({})
        svc, db = _service(org)

        result = svc.save_layout(
            ORG_ID,
            [
                DashboardWidgetConfig(id="kpi_low_stock", enabled=True, order=5),
                DashboardWidgetConfig(id="kpi_out_of_stock", enabled=False),
            ],
            updated_by=USER_ID,
        )

        assert db.commit_count == 1
        stored = org.extra_data[LAYOUT_KEY]
        assert stored["version"] == LAYOUT_VERSION
        assert stored["updated_by"] == str(USER_ID)
        assert stored["updated_at"]

        stored_ids = {w["id"] for w in stored["widgets"]}
        assert stored_ids == {"kpi_low_stock", "kpi_out_of_stock"}
        # omitted order falls back to the catalogue default
        stored_by_id = {w["id"]: w for w in stored["widgets"]}
        assert (
            stored_by_id["kpi_out_of_stock"]["order"]
            == WIDGETS_BY_ID["kpi_out_of_stock"].default_order
        )

        assert result.customized is True
        assert result.updated_by == USER_ID
        assert result.ignored_widget_ids == []

    def test_save_preserves_unrelated_extra_data_keys(self):
        org = _org({"naming_series": {"invoice": {"current_number": 41}}})
        svc, _ = _service(org)

        svc.save_layout(
            ORG_ID, [DashboardWidgetConfig(id="kpi_low_stock", enabled=True)]
        )

        assert org.extra_data["naming_series"] == {"invoice": {"current_number": 41}}
        assert LAYOUT_KEY in org.extra_data

    def test_save_reassigns_dict_instead_of_mutating_in_place(self):
        """Plain JSON columns have no mutation tracking — the dict must be replaced."""
        original = {"naming_series": {"a": 1}}
        org = _org(original)
        svc, _ = _service(org)

        svc.save_layout(
            ORG_ID, [DashboardWidgetConfig(id="kpi_low_stock", enabled=True)]
        )

        assert org.extra_data is not original
        assert LAYOUT_KEY not in original, "caller's dict must not be mutated"

    def test_unknown_widget_ids_are_ignored_not_fatal(self):
        org = _org({})
        svc, _ = _service(org)

        result = svc.save_layout(
            ORG_ID,
            [
                DashboardWidgetConfig(id="kpi_low_stock", enabled=True),
                DashboardWidgetConfig(id="not_a_widget", enabled=True),
            ],
        )

        assert result.ignored_widget_ids == ["not_a_widget"]
        stored_ids = {w["id"] for w in org.extra_data[LAYOUT_KEY]["widgets"]}
        assert stored_ids == {"kpi_low_stock"}

    def test_duplicate_ids_in_payload_are_collapsed(self):
        org = _org({})
        svc, _ = _service(org)

        svc.save_layout(
            ORG_ID,
            [
                DashboardWidgetConfig(id="kpi_low_stock", enabled=True),
                DashboardWidgetConfig(id="kpi_low_stock", enabled=False),
            ],
        )

        stored = org.extra_data[LAYOUT_KEY]["widgets"]
        assert len(stored) == 1
        assert stored[0]["enabled"] is True  # first occurrence wins

    def test_widgets_omitted_before_are_reset_to_default(self):
        org = _org(
            {LAYOUT_KEY: {"widgets": [{"id": "kpi_low_stock", "enabled": False}]}}
        )
        svc, _ = _service(org)

        result = svc.save_layout(
            ORG_ID, [DashboardWidgetConfig(id="kpi_out_of_stock", enabled=False)]
        )

        by_id = {w.id: w for w in result.widgets}
        # kpi_low_stock is no longer overridden -> back to its default
        assert by_id["kpi_low_stock"].is_default is True
        assert by_id["kpi_low_stock"].enabled is True
        assert by_id["kpi_out_of_stock"].enabled is False

    def test_empty_payload_clears_customisation_flag(self):
        org = _org(
            {LAYOUT_KEY: {"widgets": [{"id": "kpi_low_stock", "enabled": False}]}}
        )
        svc, _ = _service(org)

        result = svc.save_layout(ORG_ID, [])

        assert result.customized is False
        assert result.enabled_widget_ids == list(DEFAULT_ENABLED_IDS)

    def test_saved_order_drives_render_order(self):
        org = _org({})
        svc, _ = _service(org)

        result = svc.save_layout(
            ORG_ID,
            [
                DashboardWidgetConfig(id="feed_recent_activity", enabled=True, order=1),
                DashboardWidgetConfig(
                    id="chart_inbound_outbound", enabled=True, order=2
                ),
            ],
        )

        assert [w.id for w in result.widgets][:2] == [
            "feed_recent_activity",
            "chart_inbound_outbound",
        ]

    def test_unknown_org_raises(self):
        svc, _ = _service(None)
        with pytest.raises(OrganizationNotFoundException):
            svc.save_layout(ORG_ID, [])


# ── reset ──────────────────────────────────────────────────────────────────


class TestResetLayout:
    def test_reset_removes_saved_layout(self):
        org = _org({})
        svc, db = _service(org)
        svc.save_layout(ORG_ID, [DashboardWidgetConfig(id="kpi_low_stock")])
        assert LAYOUT_KEY in org.extra_data

        result = svc.reset_layout(ORG_ID)

        assert LAYOUT_KEY not in org.extra_data
        assert result.customized is False
        assert result.enabled_widget_ids == list(DEFAULT_ENABLED_IDS)
        assert db.commit_count == 2

    def test_reset_keeps_other_extra_data(self):
        org = _org({"naming_series": {"a": 1}})
        svc, _ = _service(org)
        svc.save_layout(ORG_ID, [DashboardWidgetConfig(id="kpi_low_stock")])

        svc.reset_layout(ORG_ID)

        assert org.extra_data == {"naming_series": {"a": 1}}

    def test_reset_when_nothing_saved_is_a_noop(self):
        org = _org({})
        svc, db = _service(org)

        result = svc.reset_layout(ORG_ID)

        assert db.commit_count == 0
        assert result.customized is False

    def test_reset_unknown_org_raises(self):
        svc, _ = _service(None)
        with pytest.raises(OrganizationNotFoundException):
            svc.reset_layout(ORG_ID)


# ── malformed stored data (defensive) ──────────────────────────────────────


class TestMalformedStoredLayout:
    def test_non_dict_layout_block_is_ignored(self):
        svc, _ = _service(_org({LAYOUT_KEY: "not-a-dict"}))
        result = svc.get_layout(ORG_ID)
        assert result.customized is False
        assert result.total_widgets == len(WIDGETS)

    def test_widgets_not_a_list_is_ignored(self):
        svc, _ = _service(_org({LAYOUT_KEY: {"widgets": {"a": 1}}}))
        result = svc.get_layout(ORG_ID)
        assert result.customized is False

    def test_malformed_entries_are_skipped(self):
        svc, _ = _service(
            _org(
                {
                    LAYOUT_KEY: {
                        "widgets": [
                            "not-a-dict",
                            {"no_id": True},
                            {"id": ""},
                            {"id": 123},
                            {"id": "kpi_low_stock", "enabled": False},
                        ]
                    }
                }
            )
        )
        result = svc.get_layout(ORG_ID)
        by_id = {w.id: w for w in result.widgets}
        assert by_id["kpi_low_stock"].enabled is False
        assert result.customized is True

    def test_non_int_order_falls_back_to_default(self):
        svc, _ = _service(
            _org({LAYOUT_KEY: {"widgets": [{"id": "kpi_low_stock", "order": "5"}]}})
        )
        result = svc.get_layout(ORG_ID)
        by_id = {w.id: w for w in result.widgets}
        assert (
            by_id["kpi_low_stock"].order == WIDGETS_BY_ID["kpi_low_stock"].default_order
        )

    def test_garbage_metadata_does_not_break_response(self):
        svc, _ = _service(
            _org(
                {
                    LAYOUT_KEY: {
                        "widgets": [],
                        "version": "bad",
                        "updated_at": "not-a-date",
                        "updated_by": "not-a-uuid",
                    }
                }
            )
        )
        result = svc.get_layout(ORG_ID)
        assert result.updated_at is None
        assert result.updated_by is None
        assert result.version == LAYOUT_VERSION


# ── schema validation ──────────────────────────────────────────────────────


class TestDashboardLayoutUpdateValidation:
    def test_duplicate_ids_rejected(self):
        from app.schemas.dashboard_layout import DashboardLayoutUpdate

        with pytest.raises(ValueError, match="duplicate widget id"):
            DashboardLayoutUpdate(
                widgets=[
                    {"id": "kpi_low_stock"},
                    {"id": "kpi_low_stock"},
                ]
            )

    def test_negative_order_rejected(self):
        from app.schemas.dashboard_layout import DashboardLayoutUpdate

        with pytest.raises(ValueError):
            DashboardLayoutUpdate(widgets=[{"id": "kpi_low_stock", "order": -1}])

    def test_empty_id_rejected(self):
        from app.schemas.dashboard_layout import DashboardLayoutUpdate

        with pytest.raises(ValueError):
            DashboardLayoutUpdate(widgets=[{"id": ""}])

    def test_defaults_to_enabled_true(self):
        from app.schemas.dashboard_layout import DashboardLayoutUpdate

        body = DashboardLayoutUpdate(widgets=[{"id": "kpi_low_stock"}])
        assert body.widgets[0].enabled is True
        assert body.widgets[0].order is None


# ── org-scoped permission gate (CodeAnt PR #291) ───────────────────────────


class TestOrgScopedPermissionGate:
    """``CurrentUser.permissions`` is the union across every active organization
    role, so an ``org.update`` grant held in *another* organization must not
    authorise writing this organization's layout.

    ``_org_permission_codes`` is stubbed (not ``_require_org_update``) so the
    real ``has_permission`` wildcard logic still runs — and so a revert to the
    cross-org ``has_permission(current_user.permissions, ...)`` check fails
    these tests instead of silently passing.
    """

    BASE = f"/api/v1/identity/organizations/{ORG_ID}/dashboard-layout"

    @pytest.fixture(autouse=True)
    def _clear_dependency_overrides(self):
        yield
        import app.main as main_module

        main_module.app.dependency_overrides.clear()

    def _client(self, monkeypatch, *, token_permissions, org_permissions):
        from fastapi.testclient import TestClient

        import app.main as main_module
        from app.api.v1.endpoints import dashboard_layout as dl
        from app.database import get_db
        from app.dependencies import CurrentUser, get_current_active_user
        from app.repositories.organization_repository import OrganizationRepository

        org = Organization(id=ORG_ID, name="Test Org", slug="test-org", extra_data={})

        class _DB:
            def commit(self):
                pass

            def refresh(self, _obj):
                pass

            def query(self, *_args, **_kwargs):
                raise AssertionError("db.query() should not be reached")

        def _user():
            return CurrentUser(
                id=USER_ID,
                email="user@example.com",
                first_name="U",
                last_name="Ser",
                display_name="User",
                user_type=None,
                status=None,
                is_active=True,
                permissions=list(token_permissions),
            )

        main_module.app.dependency_overrides[get_current_active_user] = _user
        main_module.app.dependency_overrides[get_db] = lambda: _DB()
        monkeypatch.setattr(dl, "validate_user_in_organization", lambda *_a, **_k: None)
        monkeypatch.setattr(
            OrganizationRepository,
            "get_by_id",
            lambda _self, oid: org if str(oid) == str(ORG_ID) else None,
        )
        monkeypatch.setattr(
            dl,
            "_org_permission_codes",
            lambda _db, _uid, _oid: list(org_permissions),
        )
        return TestClient(main_module.app), org

    def test_cross_org_org_update_grant_is_rejected(self, monkeypatch):
        """Token carries org.update from ANOTHER org; this org grants nothing."""
        client, org = self._client(
            monkeypatch, token_permissions=["org.update"], org_permissions=[]
        )

        response = client.put(self.BASE, json={"widgets": []})

        assert response.status_code == 403
        assert "dashboard_layout" not in org.extra_data

    def test_delete_uses_the_same_org_scoped_gate(self, monkeypatch):
        client, org = self._client(
            monkeypatch, token_permissions=["org.update"], org_permissions=[]
        )

        assert client.delete(self.BASE).status_code == 403
        assert "dashboard_layout" not in org.extra_data

    def test_org_scoped_grant_is_accepted(self, monkeypatch):
        """Permission comes from the target org, not the token claim."""
        client, org = self._client(
            monkeypatch, token_permissions=[], org_permissions=["org.update"]
        )

        response = client.put(
            self.BASE, json={"widgets": [{"id": "kpi_low_stock", "enabled": True}]}
        )

        assert response.status_code == 200
        assert response.json()["customized"] is True
        assert org.extra_data["dashboard_layout"]["widgets"] == [
            {
                "id": "kpi_low_stock",
                "enabled": True,
                "order": WIDGETS_BY_ID["kpi_low_stock"].default_order,
            }
        ]

    def test_org_scoped_wildcard_is_accepted(self, monkeypatch):
        client, _org = self._client(
            monkeypatch, token_permissions=[], org_permissions=["*.*"]
        )

        assert client.put(self.BASE, json={"widgets": []}).status_code == 200

    def test_read_only_role_in_org_is_rejected(self, monkeypatch):
        client, _org = self._client(
            monkeypatch, token_permissions=[], org_permissions=["org.read"]
        )

        assert client.put(self.BASE, json={"widgets": []}).status_code == 403

    def test_system_admin_still_bypasses(self, monkeypatch):
        client, _org = self._client(
            monkeypatch,
            token_permissions=["system_admin.master"],
            org_permissions=[],
        )

        assert client.put(self.BASE, json={"widgets": []}).status_code == 200

    def test_get_remains_open_to_any_member(self, monkeypatch):
        client, _org = self._client(
            monkeypatch, token_permissions=[], org_permissions=[]
        )

        response = client.get(self.BASE)

        assert response.status_code == 200
        assert response.json()["customized"] is False
