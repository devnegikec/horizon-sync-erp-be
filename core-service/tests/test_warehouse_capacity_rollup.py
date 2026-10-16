"""Unit tests for the warehouse capacity roll-up derived from active bins.

``WarehouseService._derived_capacity`` is pure — it takes one aggregate row — so
the roll-up rules are covered without a database.
"""

from __future__ import annotations

from decimal import Decimal

from app.services.warehouse_service import WarehouseService


def _row(total, volume_cc, bin_count, uom_count, distinct_uoms, uom):
    return (total, volume_cc, bin_count, uom_count, distinct_uoms, uom)


class TestDerivedCapacity:
    def test_volume_layout_is_summed_from_the_physical_limit(self):
        # 900 bins x 3,213,000 cc. The legacy `capacity` column is 0 on volume
        # bins, so summing it reported a warehouse capacity of 0.
        row = _row(Decimal("0.000"), Decimal("2891700000"), 900, 900, 1, "volume")

        assert WarehouseService._derived_capacity(row) == (2891.7, "m³")

    def test_unit_count_layout_still_sums_capacity(self):
        row = _row(Decimal("120"), Decimal("0"), 12, 12, 1, "units")

        assert WarehouseService._derived_capacity(row) == (120.0, "units")

    def test_mixed_units_clear_the_label(self):
        # Half the bins are volume-limited, half are count-limited: the summed
        # total is not in any single unit, so it must not be labelled.
        row = _row(Decimal("120"), Decimal("3213000"), 12, 12, 2, "volume")

        assert WarehouseService._derived_capacity(row) == (120.0, None)

    def test_bins_with_blank_uom_clear_the_label(self):
        row = _row(Decimal("120"), Decimal("0"), 12, 0, 1, None)

        assert WarehouseService._derived_capacity(row) == (120.0, None)

    def test_unknown_total_is_preserved(self):
        # No bins summed a value: leave the warehouse's stored capacity alone.
        row = _row(None, Decimal("0"), 0, 0, 0, None)

        assert WarehouseService._derived_capacity(row) == (None, None)

    def test_volume_layout_without_limits_reports_zero(self):
        row = _row(Decimal("0.000"), Decimal("0"), 1, 1, 1, "volume")

        assert WarehouseService._derived_capacity(row) == (0.0, "m³")

    def test_volume_uom_is_case_insensitive(self):
        row = _row(Decimal("0.000"), Decimal("3213000"), 1, 1, 1, "VOLUME")

        assert WarehouseService._derived_capacity(row) == (3.213, "m³")

    def test_weight_layout_keeps_its_stored_total(self):
        row = _row(Decimal("800"), Decimal("0"), 4, 4, 1, "weight")

        assert WarehouseService._derived_capacity(row) == (800.0, "kg")
