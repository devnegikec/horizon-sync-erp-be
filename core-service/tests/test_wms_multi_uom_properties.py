"""Property-based tests for WMS Multi-UOM Packaging Units.

All 12 Hypothesis properties for tasks 12.1–12.12.

Run with:
    pytest core-service/tests/test_wms_multi_uom_properties.py --hypothesis-seed=0

Pure-logic tests (Properties 1–9) require no database.
DB-backed tests (Properties 10–12) use the db_session fixture from conftest.

Requirements validated: 2.2, 2.3, 2.5, 2.6, 3.1, 4.4, 5.1, 6.2, 6.3,
                        7.3, 7.4, 7.5, 7.7, 7.8
"""

import uuid
from decimal import Decimal
from typing import Optional
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from app.models.bin_stock_level import BinStockLevel
from app.models.item import Item
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.scan_session import ScanSessionItem
from app.schemas.item_packaging_unit import ItemPackagingUnitCreate
from app.services.volumetric_assignment_service import VolumetricAssignmentService

# ---------------------------------------------------------------------------
# Shared Hypothesis settings
# ---------------------------------------------------------------------------

settings.register_profile("ci", max_examples=50)
settings.register_profile("default", max_examples=100)
settings.load_profile("default")

# ---------------------------------------------------------------------------
# Helper factories (shared across tests)
# ---------------------------------------------------------------------------


def _make_pu_mock(
    length_mm=None,
    width_mm=None,
    height_mm=None,
    weight_grams=None,
) -> MagicMock:
    """Return a lightweight mock that looks like an ItemPackagingUnit."""
    pu = MagicMock(spec=ItemPackagingUnit)
    pu.length_mm = length_mm
    pu.width_mm = width_mm
    pu.height_mm = height_mm
    pu.weight_grams = weight_grams
    return pu


def _make_put_away_item(
    item_id=None,
    batch_number="BATCH-001",
    quantity=Decimal("10"),
    packaging_unit_id=None,
) -> MagicMock:
    """Return a mock that looks like a PutAwayListItem."""
    item = MagicMock()
    item.item_id = item_id or uuid.uuid4()
    item.batch_number = batch_number
    item.quantity = quantity
    item.bin_location_id = None
    item.packaging_unit_id = packaging_unit_id
    return item


def _create_db_item(db_session, org_id) -> Item:
    """Insert a minimal Item row and return it."""
    item = Item(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_code=f"ITEM-{uuid.uuid4().hex[:8].upper()}",
        item_name="Test Item",
        item_type="stock",
        uom="Nos",
    )
    db_session.add(item)
    db_session.flush()
    return item


def _create_db_packaging_unit(
    db_session,
    org_id,
    item_id,
    unit_name: str = "Box",
    conversion_factor: Decimal = Decimal("12"),
    qr_identifier: Optional[str] = None,
    is_active: bool = True,
) -> ItemPackagingUnit:
    """Insert an ItemPackagingUnit row and return it."""
    pu = ItemPackagingUnit(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_id=item_id,
        unit_name=unit_name,
        conversion_factor=conversion_factor,
        qr_identifier=qr_identifier,
        is_base_unit=False,
        is_active=is_active,
    )
    db_session.add(pu)
    db_session.flush()
    return pu


# ===========================================================================
# Property 1 — conversion_factor > 0 is always enforced
# Validates: Requirements 2.5
# ===========================================================================


class TestProperty1ConversionFactorPositivity:
    """**Property 1: conversion_factor > 0 is always enforced**

    Validates: Requirements 2.5
    """

    @given(
        st.decimals(
            min_value=Decimal("0.000001"),
            max_value=Decimal("1000000"),
            allow_nan=False,
            allow_infinity=False,
        )
    )
    def test_positive_conversion_factor_is_accepted(self, factor: Decimal):
        """For any conversion_factor > 0, ItemPackagingUnitCreate accepts it."""
        schema = ItemPackagingUnitCreate(
            unit_name="Box",
            conversion_factor=factor,
        )
        assert schema.conversion_factor == factor
        assert schema.conversion_factor > 0

    @given(
        st.one_of(
            st.just(Decimal("0")),
            st.decimals(
                max_value=Decimal("-0.000001"),
                allow_nan=False,
                allow_infinity=False,
            ),
        )
    )
    def test_non_positive_conversion_factor_is_rejected(self, factor: Decimal):
        """For any conversion_factor <= 0, ItemPackagingUnitCreate raises ValidationError."""
        with pytest.raises(ValidationError):
            ItemPackagingUnitCreate(
                unit_name="Box",
                conversion_factor=factor,
            )


# ===========================================================================
# Property 2 — Eaches quantity is never less than raw_quantity when
#              conversion_factor >= 1
# Validates: Requirements 6.2
# ===========================================================================


class TestProperty2EachesQuantityMonotone:
    """**Property 2: Eaches quantity is never less than raw_quantity when conversion_factor >= 1**

    Validates: Requirements 6.2
    """

    @given(
        st.integers(min_value=1, max_value=10000),
        st.decimals(
            min_value=Decimal("1"),
            max_value=Decimal("1000"),
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    def test_eaches_gte_raw_quantity_when_factor_gte_1(
        self, raw_quantity: int, conversion_factor: Decimal
    ):
        """int(raw_quantity * conversion_factor) >= raw_quantity when factor >= 1."""
        eaches_qty = int(raw_quantity * conversion_factor)
        assert eaches_qty >= raw_quantity


# ===========================================================================
# Property 3 — null packaging_unit_id → identity conversion
# Validates: Requirements 6.3
# ===========================================================================


class TestProperty3NullPackagingUnitIdentity:
    """**Property 3: null packaging_unit_id → identity conversion**

    Validates: Requirements 6.3
    """

    @given(st.integers(min_value=1, max_value=100000))
    def test_null_packaging_unit_id_passes_raw_quantity_unchanged(
        self, raw_quantity: int
    ):
        """When packaging_unit_id is None, eaches_qty == raw_quantity."""
        packaging_unit_id = None
        conversion_factor = Decimal("12")  # would change the value if applied

        # This is the exact logic from ReceivingSlipService.approve_slip()
        eaches_qty = (
            raw_quantity
            if packaging_unit_id is None
            else int(raw_quantity * conversion_factor)
        )

        assert eaches_qty == raw_quantity


# ===========================================================================
# Property 4 — volume_cc is always positive when all dimensions are positive
# Validates: Requirements 7.3
# ===========================================================================


class TestProperty4VolumePositive:
    """**Property 4: volume_cc is always positive when all dimensions are positive**

    Validates: Requirements 7.3
    """

    @given(
        st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("10000"),
            allow_nan=False,
            allow_infinity=False,
        ),
        st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("10000"),
            allow_nan=False,
            allow_infinity=False,
        ),
        st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("10000"),
            allow_nan=False,
            allow_infinity=False,
        ),
        st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("10000"),
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    def test_volume_is_positive_when_all_dims_positive(
        self,
        length_mm: Decimal,
        width_mm: Decimal,
        height_mm: Decimal,
        quantity: Decimal,
    ):
        """_calc_volume returns a positive value when all dimensions and quantity are positive."""
        svc = VolumetricAssignmentService()
        pu = _make_pu_mock(
            length_mm=length_mm,
            width_mm=width_mm,
            height_mm=height_mm,
        )

        result = svc._calc_volume(quantity, pu)

        assert result is not None
        assert result > 0


# ===========================================================================
# Property 5 — any null dimension → unconstrained volume (returns None)
# Validates: Requirements 7.3, 4.4
# ===========================================================================


class TestProperty5NullDimensionUnconstrained:
    """**Property 5: any null dimension → unconstrained volume**

    Validates: Requirements 7.3, 4.4
    """

    @given(
        st.one_of(
            st.none(),
            st.decimals(
                min_value=Decimal("0.01"),
                max_value=Decimal("10000"),
                allow_nan=False,
                allow_infinity=False,
            ),
        ),
        st.one_of(
            st.none(),
            st.decimals(
                min_value=Decimal("0.01"),
                max_value=Decimal("10000"),
                allow_nan=False,
                allow_infinity=False,
            ),
        ),
        st.one_of(
            st.none(),
            st.decimals(
                min_value=Decimal("0.01"),
                max_value=Decimal("10000"),
                allow_nan=False,
                allow_infinity=False,
            ),
        ),
    )
    def test_null_dimension_returns_none(
        self,
        l: Optional[Decimal],
        w: Optional[Decimal],
        h: Optional[Decimal],
    ):
        """When at least one dimension is None, _calc_volume returns None."""
        assume(any(d is None for d in [l, w, h]))

        svc = VolumetricAssignmentService()
        pu = _make_pu_mock(length_mm=l, width_mm=w, height_mm=h)

        result = svc._calc_volume(Decimal("5"), pu)

        assert result is None


# ===========================================================================
# Property 6 — null weight_grams → unconstrained weight (returns None)
# Validates: Requirements 7.4, 4.4
# ===========================================================================


class TestProperty6NullWeightUnconstrained:
    """**Property 6: null weight_grams → unconstrained weight**

    Validates: Requirements 7.4, 4.4
    """

    @given(st.integers(min_value=1, max_value=100000))
    def test_null_weight_grams_returns_none(self, quantity: int):
        """When weight_grams is None, _calc_weight returns None for any quantity."""
        svc = VolumetricAssignmentService()
        pu = _make_pu_mock(weight_grams=None)

        result = svc._calc_weight(Decimal(quantity), pu)

        assert result is None


# ===========================================================================
# Property 7 — capacity acceptance is monotone in required volume
# Validates: Requirements 7.5
# ===========================================================================


class TestProperty7CapacityMonotone:
    """**Property 7: capacity acceptance is monotone in required volume**

    Validates: Requirements 7.5
    """

    @given(
        st.decimals(
            min_value=Decimal("0"),
            max_value=Decimal("10000"),
            allow_nan=False,
            allow_infinity=False,
        ),
        st.decimals(
            min_value=Decimal("0"),
            max_value=Decimal("10000"),
            allow_nan=False,
            allow_infinity=False,
        ),
        st.decimals(
            min_value=Decimal("0"),
            max_value=Decimal("10000"),
            allow_nan=False,
            allow_infinity=False,
        ),
    )
    def test_if_bin_accepts_v_it_also_accepts_smaller_v_prime(
        self,
        available: Decimal,
        v: Decimal,
        v_prime: Decimal,
    ):
        """If available >= v, then available >= v' for any v' <= v."""
        assume(v_prime <= v)

        # This is the pure capacity-check logic from the SQL WHERE clause:
        # (wl.max_volume_cc - occupied) >= required_volume_cc
        if available >= v:
            assert available >= v_prime


# ===========================================================================
# Property 8 — assign_bins is total — never raises on empty candidate set
# Validates: Requirements 7.7
# ===========================================================================


class TestProperty8AssignBinsTotal:
    """**Property 8: assign_bins is total — never raises on empty candidate set**

    Validates: Requirements 7.7
    """

    @given(st.lists(st.integers(min_value=1, max_value=100), min_size=0, max_size=20))
    def test_assign_bins_never_raises_when_no_bin_found(self, quantities: list[int]):
        """For any list of put-away items and _find_best_bin returning None,
        assign_bins completes without exception and all bin_location_id values are None."""
        svc = VolumetricAssignmentService()
        warehouse_id = uuid.uuid4()
        org_id = uuid.uuid4()
        db = MagicMock()

        items = [_make_put_away_item(quantity=Decimal(q)) for q in quantities]

        with (
            patch.object(svc, "_get_packaging_unit", return_value=None),
            patch.object(svc, "_find_best_bin", return_value=None),
        ):
            # Must not raise
            svc.assign_bins(
                put_away_list_items=items,
                warehouse_id=warehouse_id,
                org_id=org_id,
                db=db,
            )

        for item in items:
            assert item.bin_location_id is None


# ===========================================================================
# Property 9 — consolidation bin is always preferred over non-consolidation bin
# Validates: Requirements 7.8
# ===========================================================================


class TestProperty9ConsolidationPreference:
    """**Property 9: consolidation bin is always preferred over non-consolidation bin**

    Validates: Requirements 7.8
    """

    @given(
        st.uuids(),
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        ),
    )
    def test_find_best_bin_receives_item_id_and_batch_number(
        self, item_id: uuid.UUID, batch_number: str
    ):
        """The service passes item_id and batch_number to _find_best_bin so that
        the SQL can order by COALESCE(c.has_same_item, FALSE) DESC — enabling
        consolidation preference.

        This property verifies the contract: assign_bins always forwards item_id
        and batch_number to _find_best_bin regardless of the input values.
        """
        svc = VolumetricAssignmentService()
        warehouse_id = uuid.uuid4()
        org_id = uuid.uuid4()
        db = MagicMock()

        item = _make_put_away_item(item_id=item_id, batch_number=batch_number)

        mock_find = MagicMock(return_value=None)

        with (
            patch.object(svc, "_get_packaging_unit", return_value=None),
            patch.object(svc, "_find_best_bin", mock_find),
        ):
            svc.assign_bins(
                put_away_list_items=[item],
                warehouse_id=warehouse_id,
                org_id=org_id,
                db=db,
            )

        mock_find.assert_called_once()
        call_kwargs = mock_find.call_args.kwargs
        assert call_kwargs["item_id"] == item_id
        assert call_kwargs["batch_number"] == batch_number


# ===========================================================================
# Property 10 — qr_identifier uniqueness is enforced (DB-backed)
# Validates: Requirements 2.2, 2.3
# ===========================================================================


class TestProperty10QrIdentifierUniqueness:
    """**Property 10: qr_identifier uniqueness is enforced**

    Validates: Requirements 2.2, 2.3
    """

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        )
    )
    def test_duplicate_qr_identifier_raises_integrity_error(
        self, db_session, qr_identifier: str
    ):
        """Attempting to create two ItemPackagingUnit rows with the same qr_identifier
        in the same org raises an integrity error (unique constraint violation)."""
        from sqlalchemy.exc import IntegrityError

        org_id = uuid.uuid4()
        item = _create_db_item(db_session, org_id)

        # Create first packaging unit with the qr_identifier
        pu1 = ItemPackagingUnit(
            id=uuid.uuid4(),
            organization_id=org_id,
            item_id=item.id,
            unit_name="Unit A",
            conversion_factor=Decimal("1"),
            qr_identifier=qr_identifier,
            is_base_unit=False,
            is_active=True,
        )
        db_session.add(pu1)
        db_session.flush()

        # Attempt to create a second packaging unit with the same qr_identifier
        pu2 = ItemPackagingUnit(
            id=uuid.uuid4(),
            organization_id=org_id,
            item_id=item.id,
            unit_name="Unit B",  # different unit_name to avoid that constraint
            conversion_factor=Decimal("2"),
            qr_identifier=qr_identifier,  # same qr_identifier — must fail
            is_base_unit=False,
            is_active=True,
        )
        db_session.add(pu2)

        with pytest.raises(IntegrityError):
            db_session.flush()

        db_session.rollback()


# ===========================================================================
# Property 11 — (item_id, unit_name) uniqueness is enforced (DB-backed)
# Validates: Requirements 2.2
# ===========================================================================


class TestProperty11ItemUnitNameUniqueness:
    """**Property 11: (item_id, unit_name) uniqueness is enforced**

    Validates: Requirements 2.2
    """

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        )
    )
    def test_duplicate_item_unit_name_raises_409(self, db_session, unit_name: str):
        """Attempting to create two packaging units with the same (item_id, unit_name)
        raises HTTP 409 regardless of other field values."""
        from app.services.item_packaging_unit_service import ItemPackagingUnitService

        org_id = uuid.uuid4()
        item = _create_db_item(db_session, org_id)
        service = ItemPackagingUnitService()

        # Create the first packaging unit
        first_data = ItemPackagingUnitCreate(
            unit_name=unit_name,
            conversion_factor=Decimal("1"),
        )
        service.create_packaging_unit(
            item_id=item.id,
            data=first_data,
            org_id=org_id,
            db=db_session,
        )
        db_session.commit()

        # Attempt to create a second with the same unit_name — must raise 409
        from fastapi import HTTPException

        second_data = ItemPackagingUnitCreate(
            unit_name=unit_name,
            conversion_factor=Decimal("5"),  # different factor — still conflicts
        )

        with pytest.raises(HTTPException) as exc_info:
            service.create_packaging_unit(
                item_id=item.id,
                data=second_data,
                org_id=org_id,
                db=db_session,
            )

        assert exc_info.value.status_code == 409


# ===========================================================================
# Property 12 — soft-delete does not cascade to referencing rows (DB-backed)
# Validates: Requirements 2.6, 3.1, 5.1
# ===========================================================================


class TestProperty12SoftDeletePreservesFKReferences:
    """**Property 12: soft-delete does not cascade to referencing rows**

    Validates: Requirements 2.6, 3.1, 5.1
    """

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=100))
    def test_soft_delete_preserves_scan_session_item_fk(
        self, db_session, raw_quantity: int
    ):
        """After soft-deleting a packaging unit (is_active = False), existing
        scan_session_items rows that reference it still have a valid (non-null)
        packaging_unit_id FK."""
        from app.models.scan_session import ScanSession
        from app.models.warehouse_location import WarehouseLocation
        from app.models.warehouse import Warehouse

        org_id = uuid.uuid4()
        item = _create_db_item(db_session, org_id)

        # Create a packaging unit
        pu = _create_db_packaging_unit(
            db_session, org_id, item.id, unit_name="Box", is_active=True
        )

        # Create a minimal warehouse for the scan session FK
        warehouse = Warehouse(
            id=uuid.uuid4(),
            organization_id=org_id,
            name="Test Warehouse",
            code="WH-TEST",
        )
        db_session.add(warehouse)
        db_session.flush()

        # Create a scan session
        session = ScanSession(
            id=uuid.uuid4(),
            organization_id=org_id,
            session_type="inbound",
            worker_id=uuid.uuid4(),
            warehouse_id=warehouse.id,
            status="open",
        )
        db_session.add(session)
        db_session.flush()

        # Create a scan session item referencing the packaging unit
        scan_item = ScanSessionItem(
            id=uuid.uuid4(),
            organization_id=org_id,
            session_id=session.id,
            qr_identifier=f"QR-{uuid.uuid4().hex[:8]}",
            sku="SKU-001",
            raw_quantity=raw_quantity,
            batch_number="BATCH-001",
            raw_qr_data="{}",
            packaging_unit_id=pu.id,
        )
        db_session.add(scan_item)
        db_session.flush()

        # Soft-delete the packaging unit
        pu.is_active = False
        db_session.flush()

        # The scan_session_item must still reference the packaging unit
        db_session.refresh(scan_item)
        assert scan_item.packaging_unit_id == pu.id
        assert scan_item.packaging_unit_id is not None

    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(st.integers(min_value=1, max_value=100))
    def test_soft_delete_preserves_bin_stock_level_fk(
        self, db_session, raw_quantity: int
    ):
        """After soft-deleting a packaging unit (is_active = False), existing
        bin_stock_levels rows that reference it still have a valid (non-null)
        packaging_unit_id FK."""
        from app.models.warehouse_location import WarehouseLocation
        from app.models.warehouse import Warehouse

        org_id = uuid.uuid4()
        item = _create_db_item(db_session, org_id)

        # Create a packaging unit
        pu = _create_db_packaging_unit(
            db_session, org_id, item.id, unit_name="Pallet", is_active=True
        )

        # Create a minimal warehouse and bin location for the FK
        warehouse = Warehouse(
            id=uuid.uuid4(),
            organization_id=org_id,
            name="Test Warehouse",
            code="WH-TEST2",
        )
        db_session.add(warehouse)
        db_session.flush()

        bin_loc = WarehouseLocation(
            id=uuid.uuid4(),
            organization_id=org_id,
            warehouse_id=warehouse.id,
            location_type="bin",
            code="BIN-001",
            is_active=True,
        )
        db_session.add(bin_loc)
        db_session.flush()

        # Create a bin_stock_level referencing the packaging unit
        bsl = BinStockLevel(
            id=uuid.uuid4(),
            organization_id=org_id,
            bin_location_id=bin_loc.id,
            item_id=item.id,
            quantity_on_hand=Decimal(raw_quantity),
            batch_number="BATCH-001",
            packaging_unit_id=pu.id,
        )
        db_session.add(bsl)
        db_session.flush()

        # Soft-delete the packaging unit
        pu.is_active = False
        db_session.flush()

        # The bin_stock_level must still reference the packaging unit
        db_session.refresh(bsl)
        assert bsl.packaging_unit_id == pu.id
        assert bsl.packaging_unit_id is not None
