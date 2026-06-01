"""Unit tests for VolumetricAssignmentService.

Task 11.2 covers _calc_volume and _calc_weight.
Task 11.3 covers assign_bins (this file).

All tests use unittest.mock to avoid any DB dependency.
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.services.volumetric_assignment_service import VolumetricAssignmentService


# ---------------------------------------------------------------------------
# Helpers — lightweight stand-ins for ORM objects
# ---------------------------------------------------------------------------


def make_item(
    item_id=None,
    batch_number="BATCH-001",
    quantity=Decimal("10"),
    bin_location_id=None,
    packaging_unit_id=None,
):
    """Return a simple mock that looks like a PutAwayListItem."""
    item = MagicMock()
    item.item_id = item_id or uuid.uuid4()
    item.batch_number = batch_number
    item.quantity = quantity
    item.bin_location_id = bin_location_id
    item.packaging_unit_id = packaging_unit_id
    return item


def make_bin(bin_id=None):
    """Return a simple mock that looks like a WarehouseLocation (bin)."""
    loc = MagicMock()
    loc.id = bin_id or uuid.uuid4()
    return loc


def make_packaging_unit(
    length_mm=Decimal("100"),
    width_mm=Decimal("50"),
    height_mm=Decimal("20"),
    weight_grams=Decimal("500"),
):
    """Return a mock ItemPackagingUnit with physical dimensions."""
    pu = MagicMock()
    pu.length_mm = length_mm
    pu.width_mm = width_mm
    pu.height_mm = height_mm
    pu.weight_grams = weight_grams
    return pu


# ---------------------------------------------------------------------------
# Task 11.2 — _calc_volume and _calc_weight
# ---------------------------------------------------------------------------


class TestCalcVolume:
    """Tests for VolumetricAssignmentService._calc_volume (Req 7.3)."""

    def setup_method(self):
        self.svc = VolumetricAssignmentService()

    def test_returns_correct_cc_when_all_dims_present(self):
        pu = make_packaging_unit(
            length_mm=Decimal("100"),
            width_mm=Decimal("50"),
            height_mm=Decimal("20"),
        )
        # 5 * 100 * 50 * 20 / 1000 = 500 cc
        result = self.svc._calc_volume(Decimal("5"), pu)
        assert result == Decimal("500")

    def test_returns_none_when_length_is_none(self):
        pu = make_packaging_unit(length_mm=None)
        assert self.svc._calc_volume(Decimal("10"), pu) is None

    def test_returns_none_when_width_is_none(self):
        pu = make_packaging_unit(width_mm=None)
        assert self.svc._calc_volume(Decimal("10"), pu) is None

    def test_returns_none_when_height_is_none(self):
        pu = make_packaging_unit(height_mm=None)
        assert self.svc._calc_volume(Decimal("10"), pu) is None

    def test_returns_none_when_no_packaging_unit(self):
        assert self.svc._calc_volume(Decimal("10"), None) is None


class TestCalcWeight:
    """Tests for VolumetricAssignmentService._calc_weight (Req 7.4)."""

    def setup_method(self):
        self.svc = VolumetricAssignmentService()

    def test_returns_correct_grams_when_weight_present(self):
        pu = make_packaging_unit(weight_grams=Decimal("250"))
        # 4 * 250 = 1000 g
        result = self.svc._calc_weight(Decimal("4"), pu)
        assert result == Decimal("1000")

    def test_returns_none_when_weight_grams_is_none(self):
        pu = make_packaging_unit(weight_grams=None)
        assert self.svc._calc_weight(Decimal("10"), pu) is None

    def test_returns_none_when_no_packaging_unit(self):
        assert self.svc._calc_weight(Decimal("10"), None) is None


# ---------------------------------------------------------------------------
# Task 11.3 — assign_bins
# ---------------------------------------------------------------------------


class TestAssignBins:
    """Unit tests for VolumetricAssignmentService.assign_bins (Req 7.5–7.8)."""

    def setup_method(self):
        self.svc = VolumetricAssignmentService()
        self.warehouse_id = uuid.uuid4()
        self.org_id = uuid.uuid4()
        self.db = MagicMock()

    # ------------------------------------------------------------------
    # 1. Bin with sufficient capacity is assigned (Req 7.5, 7.6)
    # ------------------------------------------------------------------

    def test_bin_assigned_when_find_best_bin_returns_bin(self):
        """When _find_best_bin returns a bin, item.bin_location_id is set to that bin's id."""
        item = make_item()
        expected_bin = make_bin()

        with (
            patch.object(self.svc, "_get_packaging_unit", return_value=None),
            patch.object(self.svc, "_find_best_bin", return_value=expected_bin),
        ):
            self.svc.assign_bins(
                put_away_list_items=[item],
                warehouse_id=self.warehouse_id,
                org_id=self.org_id,
                db=self.db,
            )

        assert item.bin_location_id == expected_bin.id

    # ------------------------------------------------------------------
    # 2. No suitable bin leaves bin_location_id = None without raising (Req 7.7)
    # ------------------------------------------------------------------

    def test_bin_location_id_is_none_when_no_bin_found(self):
        """When _find_best_bin returns None, bin_location_id stays None and no exception is raised."""
        item = make_item()

        with (
            patch.object(self.svc, "_get_packaging_unit", return_value=None),
            patch.object(self.svc, "_find_best_bin", return_value=None),
        ):
            # Must not raise
            self.svc.assign_bins(
                put_away_list_items=[item],
                warehouse_id=self.warehouse_id,
                org_id=self.org_id,
                db=self.db,
            )

        assert item.bin_location_id is None

    def test_no_exception_raised_when_no_bin_found(self):
        """assign_bins is total — it never raises when no bin is available (Req 7.7)."""
        items = [make_item() for _ in range(3)]

        with (
            patch.object(self.svc, "_get_packaging_unit", return_value=None),
            patch.object(self.svc, "_find_best_bin", return_value=None),
        ):
            # Should complete without raising
            self.svc.assign_bins(
                put_away_list_items=items,
                warehouse_id=self.warehouse_id,
                org_id=self.org_id,
                db=self.db,
            )

        for item in items:
            assert item.bin_location_id is None

    # ------------------------------------------------------------------
    # 3. Multiple items — each gets its own bin assignment
    # ------------------------------------------------------------------

    def test_each_item_gets_independent_bin_assignment(self):
        """Each item in the list is processed independently."""
        bin_a = make_bin()
        bin_b = make_bin()
        item_a = make_item()
        item_b = make_item()

        side_effects = [bin_a, bin_b]

        with (
            patch.object(self.svc, "_get_packaging_unit", return_value=None),
            patch.object(
                self.svc, "_find_best_bin", side_effect=side_effects
            ),
        ):
            self.svc.assign_bins(
                put_away_list_items=[item_a, item_b],
                warehouse_id=self.warehouse_id,
                org_id=self.org_id,
                db=self.db,
            )

        assert item_a.bin_location_id == bin_a.id
        assert item_b.bin_location_id == bin_b.id

    # ------------------------------------------------------------------
    # 4. Consolidation preference — _find_best_bin called with correct params (Req 7.8)
    # ------------------------------------------------------------------

    def test_find_best_bin_called_with_item_id_and_batch_number(self):
        """_find_best_bin receives item_id and batch_number so the SQL can rank
        consolidation bins (bins already holding the same item+batch) first."""
        item_id = uuid.uuid4()
        batch = "BATCH-XYZ"
        item = make_item(item_id=item_id, batch_number=batch)

        mock_find = MagicMock(return_value=None)

        with (
            patch.object(self.svc, "_get_packaging_unit", return_value=None),
            patch.object(self.svc, "_find_best_bin", mock_find),
        ):
            self.svc.assign_bins(
                put_away_list_items=[item],
                warehouse_id=self.warehouse_id,
                org_id=self.org_id,
                db=self.db,
            )

        mock_find.assert_called_once()
        call_kwargs = mock_find.call_args.kwargs
        assert call_kwargs["item_id"] == item_id
        assert call_kwargs["batch_number"] == batch

    def test_find_best_bin_called_with_warehouse_and_org(self):
        """_find_best_bin receives warehouse_id and org_id for tenant-scoped search."""
        item = make_item()
        mock_find = MagicMock(return_value=None)

        with (
            patch.object(self.svc, "_get_packaging_unit", return_value=None),
            patch.object(self.svc, "_find_best_bin", mock_find),
        ):
            self.svc.assign_bins(
                put_away_list_items=[item],
                warehouse_id=self.warehouse_id,
                org_id=self.org_id,
                db=self.db,
            )

        call_kwargs = mock_find.call_args.kwargs
        assert call_kwargs["warehouse_id"] == self.warehouse_id
        assert call_kwargs["org_id"] == self.org_id

    def test_find_best_bin_called_with_volumetric_params_from_packaging_unit(self):
        """When a packaging unit is present, _find_best_bin receives the computed
        volume and weight so the SQL can filter bins by capacity (Req 7.5)."""
        pu = make_packaging_unit(
            length_mm=Decimal("100"),
            width_mm=Decimal("50"),
            height_mm=Decimal("20"),
            weight_grams=Decimal("500"),
        )
        # quantity=2 → volume = 2*100*50*20/1000 = 200 cc; weight = 2*500 = 1000 g
        item = make_item(quantity=Decimal("2"))
        mock_find = MagicMock(return_value=None)

        with (
            patch.object(self.svc, "_get_packaging_unit", return_value=pu),
            patch.object(self.svc, "_find_best_bin", mock_find),
        ):
            self.svc.assign_bins(
                put_away_list_items=[item],
                warehouse_id=self.warehouse_id,
                org_id=self.org_id,
                db=self.db,
            )

        call_kwargs = mock_find.call_args.kwargs
        assert call_kwargs["required_volume_cc"] == Decimal("200")
        assert call_kwargs["required_weight_g"] == Decimal("1000")

    def test_find_best_bin_called_with_none_volumetric_params_when_no_pu(self):
        """When no packaging unit is present, volume and weight are None (unconstrained)."""
        item = make_item()
        mock_find = MagicMock(return_value=None)

        with (
            patch.object(self.svc, "_get_packaging_unit", return_value=None),
            patch.object(self.svc, "_find_best_bin", mock_find),
        ):
            self.svc.assign_bins(
                put_away_list_items=[item],
                warehouse_id=self.warehouse_id,
                org_id=self.org_id,
                db=self.db,
            )

        call_kwargs = mock_find.call_args.kwargs
        assert call_kwargs["required_volume_cc"] is None
        assert call_kwargs["required_weight_g"] is None

    # ------------------------------------------------------------------
    # 5. Empty list — no calls, no errors
    # ------------------------------------------------------------------

    def test_empty_item_list_does_not_raise(self):
        """assign_bins with an empty list completes without error."""
        with (
            patch.object(self.svc, "_get_packaging_unit") as mock_pu,
            patch.object(self.svc, "_find_best_bin") as mock_find,
        ):
            self.svc.assign_bins(
                put_away_list_items=[],
                warehouse_id=self.warehouse_id,
                org_id=self.org_id,
                db=self.db,
            )

        mock_pu.assert_not_called()
        mock_find.assert_not_called()

    # ------------------------------------------------------------------
    # 6. Mixed results — some bins found, some not
    # ------------------------------------------------------------------

    def test_mixed_results_some_bins_assigned_some_none(self):
        """Items where a bin is found get assigned; others stay None."""
        bin_found = make_bin()
        item_with_bin = make_item()
        item_without_bin = make_item()

        with (
            patch.object(self.svc, "_get_packaging_unit", return_value=None),
            patch.object(
                self.svc,
                "_find_best_bin",
                side_effect=[bin_found, None],
            ),
        ):
            self.svc.assign_bins(
                put_away_list_items=[item_with_bin, item_without_bin],
                warehouse_id=self.warehouse_id,
                org_id=self.org_id,
                db=self.db,
            )

        assert item_with_bin.bin_location_id == bin_found.id
        assert item_without_bin.bin_location_id is None
