"""Tests for the layout design service's read paths.

``validate`` / ``preview`` / ``list_rules`` / ``list_examples`` never touch the
database, so they are exercised with a sentinel session - if one of them ever
starts querying, these tests fail loudly instead of silently skipping.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md sections 6 and 8
"""

from __future__ import annotations

import copy
from unittest.mock import MagicMock

import pytest

from app.layout_design.examples import CROSS_AISLE_TWO_WAY, MINIMAL
from app.services.layout_design_service import LayoutDesignService


@pytest.fixture
def service() -> LayoutDesignService:
    """A service whose session must never be used."""
    return LayoutDesignService(db=MagicMock())


class TestValidate:
    def test_clean_document_is_valid_and_applyable(self, service):
        result = service.validate(copy.deepcopy(MINIMAL))

        assert result.valid is True
        assert result.applyable is True
        assert result.diagnostics == []
        assert result.summary.bins == 4

    def test_summary_uses_snake_case_field_names(self, service):
        result = service.validate(copy.deepcopy(CROSS_AISLE_TWO_WAY))

        summary = result.summary
        assert (summary.zones, summary.aisles, summary.lanes) == (1, 3, 6)
        assert (summary.bays, summary.active_bays) == (60, 48)
        assert (summary.levels, summary.bins) == (30, 240)
        assert (summary.rack_types, summary.obstacles) == (1, 5)
        assert (summary.errors, summary.warnings) == (0, 0)

    def test_malformed_document_reports_a_diagnostic_not_an_exception(self, service):
        result = service.validate({"schemaVersion": 1})

        assert result.valid is False
        assert result.applyable is False
        assert [item.code for item in result.diagnostics] == ["LAYOUT_DOC_INVALID"]

    def test_diagnostics_carry_entity_refs(self, service):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["lanes"][0]["rackTypeId"] = "rt-missing"

        result = service.validate(document)

        diagnostic = next(
            d for d in result.diagnostics if d.code == "LANE_UNKNOWN_RACK_TYPE"
        )
        assert diagnostic.severity == "error"
        assert diagnostic.entity_refs
        assert diagnostic.entity_refs[0].kind == "lane"
        assert diagnostic.entity_refs[0].label == "A01-L"

    def test_warnings_do_not_block(self, service):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["widthM"] = 2.0

        result = service.validate(document)

        assert result.valid is True
        assert result.applyable is True
        assert [item.code for item in result.diagnostics] == ["AISLE_TOO_NARROW"]

    def test_sample_bin_paths_are_wms_paths(self, service):
        result = service.validate(copy.deepcopy(MINIMAL))

        assert result.sample_bin_paths[0] == "Z01-A01-B01-L01-BN001"


class TestPreview:
    def test_preview_returns_zones_bins_and_plan(self, service):
        result = service.preview(copy.deepcopy(MINIMAL), limit=2)

        assert result.valid is True
        assert [zone.path for zone in result.zones] == ["Z01"]
        assert len(result.bins) == 2
        assert result.plan.footprint_length_m == 8
        assert len(result.plan.aisles) == 1
        assert result.plan.aisles[0].code == "A01"

    def test_bin_payload_splits_plan_axes_from_height(self, service):
        result = service.preview(copy.deepcopy(MINIMAL), limit=1)

        bin_ = result.bins[0]
        # x/y are the plan plane, z is height - matching position_x/y/z on the row.
        assert (bin_.x, bin_.y) == (2.35, 1.95)
        assert bin_.z == 0.78
        assert bin_.path == "Z01-A01-B01-L01-BN001"
        assert bin_.code == "BN001"
        assert bin_.label == "WH-MIN/A01/LEFT/B001/L1"

    def test_limit_zero_returns_no_bins_but_still_validates(self, service):
        result = service.preview(copy.deepcopy(MINIMAL), limit=0)

        assert result.bins == []
        assert result.summary.bins == 4

    def test_obstacles_are_returned_for_the_overlay(self, service):
        result = service.preview(copy.deepcopy(CROSS_AISLE_TWO_WAY), limit=0)

        kinds = [obstacle.kind for obstacle in result.plan.obstacles]
        assert sorted(kinds) == ["COLUMN", "COLUMN", "COLUMN", "OFFICE", "PILLAR"]
        pillar = next(o for o in result.plan.obstacles if o.kind == "PILLAR")
        assert (pillar.x, pillar.z) == (10.0, 28.5)
        assert (pillar.width_m, pillar.depth_m, pillar.height_m) == (0.8, 0.8, 9.0)

    def test_a_broken_document_still_previews_with_diagnostics(self, service):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["centerline"] = {"x1": 1, "z1": 1, "x2": 7, "z2": 5}

        result = service.preview(document, limit=10)

        assert result.applyable is False
        assert ["AISLE_NOT_AXIS_ALIGNED"] == [
            d.code for d in result.diagnostics if d.severity == "error"
        ]
        assert result.bins == []


class TestRegistry:
    def test_rules_are_exposed_with_severity(self, service):
        rules = {rule["code"]: rule for rule in service.list_rules()}

        assert rules["LANE_OVERLAP"]["severity"] == "error"
        assert rules["AISLE_TOO_NARROW"]["severity"] == "warning"
        assert all(rule["description"] for rule in rules.values())

    def test_examples_are_available_as_templates(self, service):
        examples = service.list_examples()

        assert "cross-aisle-two-way" in examples
        assert examples["cross-aisle-two-way"]["warehouse"]["code"] == "WH-A"

    def test_every_example_template_compiles(self, service):
        for name, document in service.list_examples().items():
            result = service.validate(copy.deepcopy(document))
            assert result.applyable, (
                f"example '{name}' does not compile: {result.diagnostics}"
            )
