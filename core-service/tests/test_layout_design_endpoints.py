"""Tests for the JSON Layout Designer endpoints.

The design here is deliberate: `validate`, `preview`, the rule registry and the
examples are **pure**, and a refused `apply` returns *before* touching the session. So
every one of them is exercised through a real `TestClient` with a sentinel database
session - if any of them ever starts querying, this file fails loudly instead of
quietly skipping.

Only the apply/read-back round trip needs a database, and it sits behind the same
`RUN_DATABASE_TESTS` gate the rest of the suite uses.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md sections 6 and 8
"""

from __future__ import annotations

import copy
import os
import uuid

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user, get_current_user
from app.layout_design.examples import CROSS_AISLE_TWO_WAY, MINIMAL
from app.main import app

ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
WAREHOUSE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")

BASE = "/api/v1/layout-design"

# The compiler gate is what these tests are about, so an unhandled failure anywhere
# else must surface as a 500 response rather than propagating out of the client.
API = lambda: TestClient(app, raise_server_exceptions=False)  # noqa: E731


@pytest.fixture
def api():
    """A client whose database session must never be used.

    `TestClient` is intentionally not entered as a context manager: the app lifespan is
    irrelevant to these endpoints, and starting it would drag in Redis and engine setup
    that has nothing to do with what is under test.
    """
    user = CurrentUser(
        id=uuid.uuid4(),
        email="designer@example.com",
        organization_id=ORG_ID,
        user_type="user",
        permissions=["warehouse.read", "warehouse.manage"],
    )

    def override_get_db():
        yield None

    async def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user
    app.dependency_overrides[get_current_active_user] = override_current_user

    yield API()

    app.dependency_overrides.clear()


class TestRuleRegistryEndpoint:
    def test_lists_every_rule_with_its_severity(self, api):
        response = api.get(f"{BASE}/rules")

        assert response.status_code == 200
        rules = {rule["code"]: rule["severity"] for rule in response.json()}
        assert rules["LANE_OVERLAP"] == "error"
        assert rules["AISLE_TOO_NARROW"] == "warning"
        assert rules["LAYOUT_DOC_INVALID"] == "error"


class TestExampleEndpoints:
    def test_lists_templates(self, api):
        response = api.get(f"{BASE}/examples")

        assert response.status_code == 200
        names = [example["name"] for example in response.json()]
        assert "cross-aisle-two-way" in names
        assert "minimal" in names

    def test_returns_a_template_by_name(self, api):
        response = api.get(f"{BASE}/examples/minimal")

        assert response.status_code == 200
        body = response.json()
        assert body["name"] == "minimal"
        assert body["document"]["schemaVersion"] == 1

    def test_unknown_template_is_a_structured_404(self, api):
        response = api.get(f"{BASE}/examples/does-not-exist")

        assert response.status_code == 404
        detail = response.json()["detail"]
        assert detail["code"] == "LAYOUT_EXAMPLE_NOT_FOUND"
        assert "cross-aisle-two-way" in detail["available"]


class TestValidateEndpoint:
    def test_clean_document_is_valid_and_applyable(self, api):
        response = api.post(
            f"{BASE}/validate", json={"document": copy.deepcopy(CROSS_AISLE_TWO_WAY)}
        )

        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is True
        assert body["applyable"] is True
        assert body["diagnostics"] == []
        assert body["summary"]["bins"] == 240
        assert body["summary"]["active_bays"] == 48
        assert body["sample_bin_paths"][0] == "Z01-A01-B01-L01-BN001"

    def test_warnings_do_not_block(self, api):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["widthM"] = 2.0

        body = api.post(f"{BASE}/validate", json={"document": document}).json()

        assert body["valid"] is True
        assert body["applyable"] is True
        assert [item["code"] for item in body["diagnostics"]] == ["AISLE_TOO_NARROW"]

    def test_malformed_document_reports_a_diagnostic_not_a_422(self, api):
        response = api.post(f"{BASE}/validate", json={"document": {"schemaVersion": 1}})

        assert response.status_code == 200
        body = response.json()
        assert body["valid"] is False
        assert [item["code"] for item in body["diagnostics"]] == ["LAYOUT_DOC_INVALID"]

    def test_diagnostics_carry_entity_refs(self, api):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["lanes"][0]["rackTypeId"] = "rt-missing"

        body = api.post(f"{BASE}/validate", json={"document": document}).json()
        diagnostic = next(
            item
            for item in body["diagnostics"]
            if item["code"] == "LANE_UNKNOWN_RACK_TYPE"
        )

        assert diagnostic["severity"] == "error"
        assert diagnostic["entity_refs"][0]["kind"] == "lane"


class TestPreviewEndpoint:
    def test_returns_geometry_for_the_document(self, api):
        response = api.post(
            f"{BASE}/preview", json={"document": copy.deepcopy(MINIMAL), "limit": 2}
        )

        assert response.status_code == 200
        body = response.json()
        assert [zone["path"] for zone in body["zones"]] == ["Z01"]
        assert len(body["bins"]) == 2
        assert body["plan"]["footprint_length_m"] == 8
        assert body["plan"]["aisles"][0]["code"] == "A01"

    def test_limit_zero_returns_no_bins(self, api):
        response = api.post(
            f"{BASE}/preview", json={"document": copy.deepcopy(MINIMAL), "limit": 0}
        )

        assert response.status_code == 200
        assert response.json()["bins"] == []
        assert response.json()["summary"]["bins"] == 4

    def test_an_out_of_range_limit_is_rejected_by_the_schema(self, api):
        response = api.post(
            f"{BASE}/preview",
            json={"document": copy.deepcopy(MINIMAL), "limit": 10_000},
        )

        # This service maps RequestValidationError to 400, not FastAPI's default 422
        # (see the handler in app/main.py), so assert the house shape.
        assert response.status_code == 400
        assert response.json()["detail"]["code"] == "VALIDATION_ERROR"


class TestApplyRefusal:
    """A refused apply must never reach the database."""

    def test_blocking_error_returns_400_with_the_rule_code(self, api):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["centerline"] = {"x1": 1, "z1": 1, "x2": 7, "z2": 5}

        response = api.post(
            f"{BASE}/apply",
            json={
                "warehouse_id": str(WAREHOUSE_ID),
                "document": document,
                "name": "Bad layout",
            },
        )

        assert response.status_code == 400
        detail = response.json()["detail"]
        assert detail["code"] == "AISLE_NOT_AXIS_ALIGNED"
        assert detail["status_code"] == 400
        assert any(
            item["code"] == "AISLE_NOT_AXIS_ALIGNED" for item in detail["diagnostics"]
        )

    def test_a_clean_document_passes_the_compiler_gate(self, api):
        """The sentinel session is the assertion: a clean document gets *past* the gate.

        With `db=None` the only possible failure is in the repository layer, so a 500
        proves the compiler accepted the document. A 400 here would mean the gate
        mis-fired on a valid layout.
        """
        response = api.post(
            f"{BASE}/apply",
            json={
                "warehouse_id": str(WAREHOUSE_ID),
                "document": copy.deepcopy(MINIMAL),
                "name": "Clean layout",
            },
        )

        assert response.status_code == 500


@pytest.mark.skipif(
    os.environ.get("RUN_DATABASE_TESTS") != "1",
    reason="Apply round-trip needs PostgreSQL (same gate as the rest of the suite)",
)
class TestApplyRoundTrip:
    def test_apply_writes_locations_and_stores_the_document(self, db_session):
        from app.models.warehouse import Warehouse
        from app.models.warehouse_floor_plan import WarehouseFloorPlan
        from app.models.warehouse_location import WarehouseLocation
        from app.services.layout_design_service import LayoutDesignService

        warehouse = Warehouse(
            organization_id=ORG_ID, code="WH-LD", name="Layout import test"
        )
        db_session.add(warehouse)
        db_session.commit()

        service = LayoutDesignService(db_session)
        result = service.apply(
            warehouse_id=warehouse.id,
            organization_id=ORG_ID,
            document=copy.deepcopy(MINIMAL),
            name="Imported layout",
            replace_existing=True,
        )

        assert result.applyable is True
        assert result.response is not None
        # 1 zone + 1 aisle + 1 rack row + 2 levels + 4 bins.
        assert result.response.locations_created == 9
        assert result.response.summary.bins == 4

        stored = service.get_stored_document(result.response.floor_plan_id, ORG_ID)
        assert stored is not None
        assert stored["warehouse"]["code"] == "WH-MIN"

        plan = (
            db_session.query(WarehouseFloorPlan)
            .filter(WarehouseFloorPlan.id == result.response.floor_plan_id)
            .one()
        )
        assert isinstance(plan.layout_doc, dict)
        assert "layout_doc" not in plan.config

        bins = (
            db_session.query(WarehouseLocation)
            .filter(WarehouseLocation.location_type == "bin")
            .all()
        )
        assert len(bins) == 4
        assert all(bin_.qr_code for bin_ in bins)

    def test_reapplying_the_same_document_reuses_the_locations(self, db_session):
        from app.models.warehouse import Warehouse
        from app.services.layout_design_service import LayoutDesignService

        warehouse = Warehouse(
            organization_id=ORG_ID, code="WH-LD2", name="Layout reapply test"
        )
        db_session.add(warehouse)
        db_session.commit()

        service = LayoutDesignService(db_session)
        first = service.apply(
            warehouse_id=warehouse.id,
            organization_id=ORG_ID,
            document=copy.deepcopy(MINIMAL),
            name="First",
            replace_existing=True,
        )
        second = service.apply(
            warehouse_id=warehouse.id,
            organization_id=ORG_ID,
            document=copy.deepcopy(MINIMAL),
            name="Second",
            replace_existing=True,
        )

        assert first.response is not None
        assert second.response is not None
        # Upsert by path: the second run updates rather than duplicating.
        assert second.response.locations_created == 0
        assert second.response.locations_updated == 9
        assert second.response.locations_deactivated == 0
