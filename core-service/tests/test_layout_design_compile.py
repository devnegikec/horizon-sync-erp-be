"""Tests for the layout document compiler.

The compiler is pure, so these need no database and no fixtures beyond the
reference documents. They assert the *derived* numbers and the *full* diagnostics
list, because those are the contract the frontend engine mirrors.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md sections 3 and 8
"""

from __future__ import annotations

import copy

import pytest

from app.layout_design import build_layout, naming
from app.layout_design.examples import CROSS_AISLE_TWO_WAY, MINIMAL
from app.layout_design.rules import BLOCKING_RULE_CODES, RULES


def codes_of(compiled) -> list[str]:
    return [diagnostic.code for diagnostic in compiled.diagnostics]


class TestReferenceDocuments:
    """Every shipped example must compile with zero diagnostics."""

    @pytest.mark.parametrize("name", ["cross-aisle-two-way", "minimal"])
    def test_example_compiles_cleanly(self, name):
        document = {"cross-aisle-two-way": CROSS_AISLE_TWO_WAY, "minimal": MINIMAL}[
            name
        ]
        compiled = build_layout(copy.deepcopy(document))

        assert compiled.diagnostics == [], [
            f"{d.severity} {d.code}: {d.message}" for d in compiled.diagnostics
        ]
        assert compiled.applyable is True
        assert compiled.bins, "an example must produce bins"

    def test_cross_aisle_yields_expected_counts(self):
        compiled = build_layout(copy.deepcopy(CROSS_AISLE_TWO_WAY))

        summary = compiled.summary()
        assert summary["zones"] == 1
        assert summary["aisles"] == 3
        assert summary["lanes"] == 6
        assert summary["bays"] == 60  # 3 aisles x 2 lanes x 10 bays
        assert summary["activeBays"] == 48  # 2 bays lost per lane to the cross-aisle
        assert summary["bins"] == 240  # 48 active bays x 5 levels

    def test_cross_aisle_removes_the_middle_bays_of_every_level(self):
        """The gap must remove bins 5 and 6 of every level, and nothing else."""
        compiled = build_layout(copy.deepcopy(CROSS_AISLE_TWO_WAY))

        level_one = [
            bin_.code
            for bin_ in compiled.bins
            if bin_.path.startswith("Z01-A01-B01-L01-")
        ]
        assert level_one == [
            "BN001",
            "BN002",
            "BN003",
            "BN004",
            "BN007",
            "BN008",
            "BN009",
            "BN010",
        ]

    def test_every_bin_path_is_unique(self):
        compiled = build_layout(copy.deepcopy(CROSS_AISLE_TWO_WAY))

        paths = [bin_.path for bin_ in compiled.bins]
        assert len(paths) == len(set(paths))


class TestWmsNaming:
    """The whole point of the import: it must emit WMS codes."""

    def test_default_scheme_prefixes_every_segment(self):
        compiled = build_layout(copy.deepcopy(MINIMAL))

        assert [bin_.path for bin_ in compiled.bins] == [
            "Z01-A01-B01-L01-BN001",
            "Z01-A01-B01-L02-BN001",
            "Z01-A01-B01-L01-BN002",
            "Z01-A01-B01-L02-BN002",
        ]

    def test_left_lane_is_b01_and_right_lane_is_b02(self):
        compiled = build_layout(copy.deepcopy(CROSS_AISLE_TWO_WAY))

        bay_paths = {bay.laneCode: bay.path for bay in compiled.bays}
        assert bay_paths["A01-L"] == "Z01-A01-B01"
        assert bay_paths["A01-R"] == "Z01-A01-B02"

    def test_floorplan_scheme_leaves_zone_and_aisle_bare(self):
        document = copy.deepcopy(MINIMAL)
        document["layout"] = {"namingScheme": "wms_floorplan"}

        compiled = build_layout(document)

        assert compiled.diagnostics == []
        assert compiled.bins[0].path == "01-01-B01-L01-BN01"

    def test_zone_code_drives_the_zone_segment(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["zoneCode"] = "Z07"

        compiled = build_layout(document)

        assert compiled.bins[0].path.startswith("Z07-")

    def test_authored_aisle_code_number_wins_over_position(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["code"] = "A12"

        compiled = build_layout(document)

        assert compiled.bins[0].path == "Z01-A12-B01-L01-BN001"


class TestNamingHelpers:
    def test_trailing_digits(self):
        assert naming.trailing_digits("A03") == "03"
        assert naming.trailing_digits("MAIN") == ""
        assert naming.trailing_digits(None) == ""

    def test_display_path_dashes_only_the_last_segment(self):
        assert (
            naming.format_display_path("Z01-A03-B02-L04-BN001")
            == "Z01-A03-B02-L04-BN-001"
        )

    def test_code_pattern_validation(self):
        assert naming.is_valid_code_pattern("{warehouse}/{lane}/B{bay:03}")
        assert not naming.is_valid_code_pattern("no-placeholders")
        assert not naming.is_valid_code_pattern("{unknown}")

    def test_code_pattern_padding(self):
        rendered = naming.format_bin_code(
            "{warehouse}/{aisle}/{side}/B{bay:03}/L{level}",
            {"warehouse": "WH1", "aisle": "A01", "side": "LEFT", "bay": 5, "level": 2},
        )
        assert rendered == "WH1/A01/LEFT/B005/L2"

    def test_qr_codes_are_unique_and_readable(self):
        codes = naming.generate_qr_codes(200, existing={"ABCDE"})

        assert len(codes) == len(set(codes)) == 200
        assert "ABCDE" not in codes
        for code in codes:
            assert len(code) == naming.QR_LENGTH
            assert not set(code) & set("IO01")


class TestDocumentDiagnostics:
    """A diagnostic per failure mode, so a bad import explains itself."""

    def test_invalid_document_reports_layout_doc_invalid(self):
        compiled = build_layout({"schemaVersion": 1, "warehouse": {"code": "WH1"}})

        assert codes_of(compiled) == ["LAYOUT_DOC_INVALID"]
        assert compiled.applyable is False

    def test_unsupported_schema_version(self):
        document = copy.deepcopy(MINIMAL)
        document["schemaVersion"] = 99

        compiled = build_layout(document)

        assert codes_of(compiled) == ["SCHEMA_VERSION_UNSUPPORTED"]

    def test_diagonal_aisle(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["centerline"] = {"x1": 1, "z1": 1, "x2": 7, "z2": 5}

        compiled = build_layout(document)

        assert "AISLE_NOT_AXIS_ALIGNED" in codes_of(compiled)

    def test_zero_length_aisle(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["centerline"] = {"x1": 4, "z1": 4, "x2": 4, "z2": 4}

        compiled = build_layout(document)

        assert "AISLE_ZERO_LENGTH" in codes_of(compiled)

    def test_orientation_mismatch(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["orientation"] = "Z"

        compiled = build_layout(document)

        assert "AISLE_ORIENTATION_MISMATCH" in codes_of(compiled)

    def test_unknown_rack_type(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["lanes"][0]["rackTypeId"] = "rt-missing"

        compiled = build_layout(document)

        assert "LANE_UNKNOWN_RACK_TYPE" in codes_of(compiled)

    def test_no_rack_types_defined(self):
        document = copy.deepcopy(MINIMAL)
        document["rackTypes"] = []

        compiled = build_layout(document)

        assert "NO_RACK_TYPES_DEFINED" in codes_of(compiled)

    def test_aisle_outside_the_footprint(self):
        document = copy.deepcopy(MINIMAL)
        document["warehouse"]["lengthM"] = 3  # aisle runs to x=7

        compiled = build_layout(document)

        assert "AISLE_OUT_OF_FOOTPRINT" in codes_of(compiled)

    def test_level_stack_taller_than_the_building(self):
        document = copy.deepcopy(MINIMAL)
        document["warehouse"]["heightM"] = 2  # two 1.48 m levels

        compiled = build_layout(document)

        assert "LEVEL_STACK_EXCEEDS_HEIGHT" in codes_of(compiled)
        assert compiled.applyable is False

    def test_obstacle_overlapping_a_bay(self):
        document = copy.deepcopy(MINIMAL)
        # Inside the left rack (z 1.4-2.5), clear of the corridor (z 2.5-5.5).
        document["obstacles"] = [
            {
                "kind": "PILLAR",
                "x": 2.0,
                "z": 1.7,
                "widthM": 0.5,
                "depthM": 0.5,
                "heightM": 3,
            }
        ]

        compiled = build_layout(document)

        assert "BAY_OBSTACLE_OVERLAP" in codes_of(compiled)
        assert "AISLE_OBSTACLE_OVERLAP" not in codes_of(compiled)

    def test_obstacle_inside_the_corridor(self):
        document = copy.deepcopy(MINIMAL)
        document["obstacles"] = [
            {
                "kind": "COLUMN",
                "x": 3.0,
                "z": 3.8,
                "widthM": 0.5,
                "depthM": 0.5,
                "heightM": 3,
            }
        ]

        compiled = build_layout(document)

        assert "AISLE_OBSTACLE_OVERLAP" in codes_of(compiled)

    def test_narrow_aisle_warns_but_does_not_block(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["widthM"] = 2.0

        compiled = build_layout(document)

        assert "AISLE_TOO_NARROW" in codes_of(compiled)
        assert compiled.applyable is True

    def test_lane_longer_than_its_aisle(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["lanes"][0]["lengthM"] = 99

        compiled = build_layout(document)

        assert "LANE_RUN_EXCEEDS_AISLE" in codes_of(compiled)

    def test_lane_shorter_than_one_bay(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["lanes"][0]["lengthM"] = 1.0

        compiled = build_layout(document)

        assert "LANE_ZERO_BAYS" in codes_of(compiled)
        assert compiled.bins == []

    def test_aisle_without_lanes(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["lanes"] = []

        compiled = build_layout(document)

        assert "AISLE_WITHOUT_LANES" in codes_of(compiled)

    def test_duplicate_aisle_code(self):
        document = copy.deepcopy(CROSS_AISLE_TWO_WAY)
        document["aisles"][1]["code"] = "A01"

        compiled = build_layout(document)

        assert "AISLE_CODE_DUPLICATE" in codes_of(compiled)

    def test_level_deeper_than_the_rack_warns(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["lanes"][0]["levels"][0]["binDepthM"] = 5.0

        compiled = build_layout(document)

        assert "LEVEL_DEPTH_EXCEEDS_RACK" in codes_of(compiled)
        assert compiled.applyable is True

    def test_lane_overlap_detected_when_aisles_are_too_close(self):
        document = copy.deepcopy(MINIMAL)
        # A second aisle whose left rack occupies the same floor as the first's.
        second = copy.deepcopy(document["aisles"][0])
        second["code"] = "A02"
        second["centerline"] = {"x1": 1, "z1": 4, "x2": 7, "z2": 4}
        document["aisles"].append(second)

        compiled = build_layout(document)

        assert "LANE_OVERLAP" in codes_of(compiled)

    def test_bin_code_pattern_collision(self):
        document = copy.deepcopy(MINIMAL)
        # A pattern without a lane/side/bay token collides across positions.
        document["aisles"][0]["lanes"][0]["binCodePattern"] = "{warehouse}/L{level}"

        compiled = build_layout(document)

        assert "BIN_CODE_DUPLICATE" in codes_of(compiled)


class TestRuleRegistry:
    def test_registry_is_complete_and_consistent(self):
        assert RULES, "the registry must not be empty"
        for code, rule in RULES.items():
            assert rule.code == code
            assert rule.severity in ("error", "warning")
            assert rule.description
            assert (code in BLOCKING_RULE_CODES) is (rule.severity == "error")

    def test_every_reported_code_exists_in_the_registry(self):
        document = copy.deepcopy(MINIMAL)
        document["warehouse"]["lengthM"] = 3
        document["aisles"][0]["widthM"] = 1.0
        document["obstacles"] = [
            {
                "kind": "WALL",
                "x": 2.0,
                "z": 2.5,
                "widthM": 1.0,
                "depthM": 1.0,
                "heightM": 3,
            }
        ]

        compiled = build_layout(document)

        for diagnostic in compiled.diagnostics:
            assert diagnostic.code in RULES
            assert diagnostic.severity == RULES[diagnostic.code].severity
