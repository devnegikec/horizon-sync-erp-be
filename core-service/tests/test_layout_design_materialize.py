"""Tests for materialising a compiled layout into WarehouseLocation rows.

These build ORM objects without adding them to a session, so they need no
database - only the conftest environment for the model imports.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md section 4
"""

from __future__ import annotations

import copy
import uuid

from app.layout_design import build_layout
from app.layout_design.examples import CROSS_AISLE_TWO_WAY, MINIMAL
from app.layout_design.materialize import materialize_layout

ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")
WAREHOUSE_ID = uuid.UUID("22222222-2222-2222-2222-222222222222")


def materialize(document, **kwargs):
    compiled = build_layout(copy.deepcopy(document))
    assert compiled.applyable, [d.message for d in compiled.diagnostics]
    return compiled, materialize_layout(
        compiled, organization_id=ORG_ID, warehouse_id=WAREHOUSE_ID, **kwargs
    )


class TestHierarchy:
    def test_row_counts_match_the_document(self):
        _, result = materialize(CROSS_AISLE_TWO_WAY)

        assert result.counts() == {
            "zones": 1,
            "aisles": 3,
            "bays": 6,
            "levels": 30,
            "bins": 240,
            "locations": 280,
        }

    def test_every_row_carries_the_org_and_warehouse(self):
        _, result = materialize(MINIMAL)

        for row in result.rows:
            assert row.organization_id == ORG_ID
            assert row.warehouse_id == WAREHOUSE_ID

    def test_parent_chain_is_zone_aisle_bay_level_bin(self):
        _, result = materialize(MINIMAL)

        by_path = {row.full_path: row for row in result.rows}
        bin_row = by_path["Z01-A01-B01-L01-BN001"]
        level_row = by_path["Z01-A01-B01-L01"]
        bay_row = by_path["Z01-A01-B01"]
        aisle_row = by_path["Z01-A01"]
        zone_row = by_path["Z01"]

        assert bin_row.location_type == "bin"
        assert bin_row.parent_location_id == level_row.id
        assert level_row.parent_location_id == bay_row.id
        assert bay_row.location_type == "bay"
        assert bay_row.parent_location_id == aisle_row.id
        assert aisle_row.location_type == "aisle"
        assert aisle_row.parent_location_id == zone_row.id
        assert zone_row.location_type == "zone"
        assert zone_row.parent_location_id is None

    def test_required_columns_are_populated(self):
        _, result = materialize(MINIMAL)

        for row in result.rows:
            assert row.id is not None
            assert row.code
            assert row.full_path
            assert row.is_active is True
            assert row.version == 1

    def test_paths_are_unique(self):
        _, result = materialize(CROSS_AISLE_TWO_WAY)

        paths = [row.full_path for row in result.rows]
        assert len(paths) == len(set(paths))

    def test_every_level_of_a_row_shares_one_level_location(self):
        _, result = materialize(MINIMAL)

        level_rows = [row for row in result.rows if row.location_type == "level"]
        bin_rows = [row for row in result.rows if row.location_type == "bin"]

        assert len(level_rows) == 2
        assert len(bin_rows) == 4
        assert {row.parent_location_id for row in bin_rows} == {
            row.id for row in level_rows
        }


class TestPhysicalLimits:
    def test_bins_carry_volume_and_weight_limits(self):
        _, result = materialize(MINIMAL)

        bin_rows = [row for row in result.rows if row.location_type == "bin"]
        assert bin_rows
        for row in bin_rows:
            assert row.capacity_uom == "volume"
            # 2.7 m bay x 1.4 m clear x 1.0 m deep, 85% usable, in cc.
            assert float(row.max_volume_cc) == 3213000.0
            assert row.max_weight_grams is None

    def test_weight_limit_converts_kg_to_grams(self):
        document = copy.deepcopy(MINIMAL)
        for level in document["aisles"][0]["lanes"][0]["levels"]:
            level["maxWeightKg"] = 750

        _, result = materialize(document)

        bin_rows = [row for row in result.rows if row.location_type == "bin"]
        assert {float(row.max_weight_grams) for row in bin_rows} == {750000.0}

    def test_bins_carry_the_usable_volume_as_capacity(self):
        # Warehouse capacity is a roll-up of SUM(bin.capacity), so the usable
        # volume has to land on `capacity` as well — leaving it at the column
        # default made every layout-derived bin (and its warehouse) report 0.
        _, result = materialize(MINIMAL)

        bin_rows = [row for row in result.rows if row.location_type == "bin"]
        assert bin_rows
        for row in bin_rows:
            assert float(row.capacity) == 3.213
            assert float(row.total_capacity) == 3.213
            # Stated in m³, matching capacity_uom="volume" and max_volume_cc.
            assert float(row.capacity) == float(row.max_volume_cc) / 1_000_000

    def test_non_bin_rows_carry_no_capacity_of_their_own(self):
        _, result = materialize(MINIMAL)

        for row in result.rows:
            if row.location_type == "bin":
                continue
            assert row.capacity is None

    def test_only_bins_have_limits(self):
        _, result = materialize(MINIMAL)

        for row in result.rows:
            if row.location_type != "bin":
                assert row.max_volume_cc is None
                assert row.max_weight_grams is None


class TestPositions:
    def test_zone_sits_at_the_origin_and_aisle_at_its_start(self):
        _, result = materialize(MINIMAL)

        by_path = {row.full_path: row for row in result.rows}
        assert (float(by_path["Z01"].position_x), float(by_path["Z01"].position_z)) == (
            0.0,
            0.0,
        )
        # Centerline starts at (1, 4) and levels stack in position_z.
        assert float(by_path["Z01-A01"].position_x) == 1.0
        assert float(by_path["Z01-A01"].position_y) == 4.0
        assert float(by_path["Z01-A01"].position_z) == 0.0

    def test_level_height_accumulates_beam_plus_clear(self):
        _, result = materialize(MINIMAL)

        by_path = {row.full_path: row for row in result.rows}
        # Level 1 centre = beam 0.08 + clear/2 = 0.78; level 2 = 1.48 + 0.08 + 0.7.
        assert float(by_path["Z01-A01-B01-L01"].position_z) == 0.78
        assert float(by_path["Z01-A01-B01-L02"].position_z) == 2.26

    def test_bin_sits_between_the_corridor_and_the_rack_face(self):
        _, result = materialize(MINIMAL)

        bin_rows = [row for row in result.rows if row.location_type == "bin"]
        # Aisle centreline at z=4, half width 1.5, rack depth 1.1 -> rack centre 1.95.
        assert {float(row.position_y) for row in bin_rows} == {1.95}

    def test_zone_and_aisle_orientations_along_z(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["orientation"] = "Z"
        document["aisles"][0]["centerline"] = {"x1": 4, "z1": 1, "x2": 4, "z2": 7}

        _, result = materialize(document)

        bin_rows = [row for row in result.rows if row.location_type == "bin"]
        # forward = +Z, so LEFT is +X: rack centre = 4 + 1.5 + 0.55.
        assert {float(row.position_x) for row in bin_rows} == {6.05}


class TestQrCodes:
    def test_qr_codes_are_assigned_to_bins_only(self):
        _, result = materialize(CROSS_AISLE_TWO_WAY, qr_codes=None)

        assert all(row.qr_code is None for row in result.rows)

    def test_supplied_qr_codes_land_on_bins_in_order(self):
        codes = [f"QR{i:03d}" for i in range(240)]

        _, result = materialize(MINIMAL, qr_codes=["AAAAA", "BBBBB", "CCCCC", "DDDDD"])

        bin_rows = [row for row in result.rows if row.location_type == "bin"]
        assert [row.qr_code for row in bin_rows] == ["AAAAA", "BBBBB", "CCCCC", "DDDDD"]
        # Non-bin rows never take a QR code.
        assert all(
            row.qr_code is None for row in result.rows if row.location_type != "bin"
        )
        assert len(codes) == 240


class TestConflicts:
    def test_path_taken_by_a_different_type_is_reported_not_overwritten(self):
        _, result = materialize(
            MINIMAL,
            existing_paths={"Z01-A01-B01-L01-BN001": "bay"},
        )

        assert [conflict.code for conflict in result.conflicts] == [
            "LOCATION_PATH_ALREADY_EXISTS"
        ]
        conflict = result.conflicts[0]
        assert conflict.data == {
            "path": "Z01-A01-B01-L01-BN001",
            "existingType": "bay",
            "generatedType": "bin",
        }
        # The conflicting row is skipped, the rest still materialise.
        assert all(row.full_path != "Z01-A01-B01-L01-BN001" for row in result.rows)

    def test_path_taken_by_the_same_type_is_reused(self):
        _, result = materialize(MINIMAL, existing_paths={"Z01-A01": "aisle"})

        assert result.conflicts == []
        assert any(row.full_path == "Z01-A01" for row in result.rows)


class TestGuards:
    def test_an_unapplyable_document_materialises_nothing(self):
        document = copy.deepcopy(MINIMAL)
        document["aisles"][0]["centerline"] = {"x1": 1, "z1": 1, "x2": 7, "z2": 5}

        compiled = build_layout(document)
        result = materialize_layout(
            compiled, organization_id=ORG_ID, warehouse_id=WAREHOUSE_ID
        )

        assert result.rows == []
        assert result.counts()["locations"] == 0
