"""Integration test for the complete inbound flow with Multi-UOM packaging units.

Covers the full end-to-end inbound workflow:
  Step 1 — Scan: start session, record scan with packaging_unit_qr_id, assert
           ScanSessionItem.raw_quantity and packaging_unit_id are stored correctly.
  Step 2 — End session → receiving slip created with status pending_review.
  Step 3 — Approve slip: assert ReceivingSlipItem.quantity == raw_qty * conversion_factor
           (Eaches); assert HTTP 422 is raised when packaging unit is inactive.
  Step 4 — PutAwayList generated; PutAwayListItem exists with quantity == 60.
  Step 5 — Complete put-away: assert BinStockLevel.quantity_on_hand == 60 (Eaches)
           and BinStockLevel.packaging_unit_id is set.

VolumetricAssignmentService.assign_bins is mocked to avoid the raw
``SELECT … FOR UPDATE SKIP LOCKED`` SQL that is not supported by SQLite.

Requirements: 5.3, 5.5, 6.1, 6.2, 6.4, 7.1, 7.6, 3.3
"""

import json
import uuid
from decimal import Decimal
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.models.bin_stock_level import BinStockLevel
from app.models.item import Item
from app.models.item_packaging_unit import ItemPackagingUnit
from app.models.put_away_list import PutAwayList, PutAwayListItem
from app.models.receiving_slip import ReceivingSlip, ReceivingSlipItem
from app.models.scan_session import ScanSession, ScanSessionItem
from app.models.warehouse_location import WarehouseLocation
from app.services.inbound_service import InboundService
from app.services.put_away_service import PutAwayService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def inbound_service(db_session):
    return InboundService(db_session)


@pytest.fixture
def put_away_service(db_session):
    return PutAwayService(db_session)


# ---------------------------------------------------------------------------
# Helper builders
# ---------------------------------------------------------------------------


def _create_item(db_session, org_id, item_code, sku=None):
    """Create and persist an Item, optionally with a sku."""
    item = Item(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_code=item_code,
        item_name=f"Test Item {item_code}",
        sku=sku,
    )
    db_session.add(item)
    db_session.flush()
    return item


def _create_packaging_unit(
    db_session,
    org_id,
    item_id,
    unit_name="Box of 12",
    qr_identifier="BOX-12-WIDGET",
    conversion_factor=12,
    length_mm=300,
    width_mm=200,
    height_mm=150,
    weight_grams=1440,
    is_active=True,
):
    """Create and persist an ItemPackagingUnit."""
    pu = ItemPackagingUnit(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_id=item_id,
        unit_name=unit_name,
        qr_identifier=qr_identifier,
        conversion_factor=Decimal(str(conversion_factor)),
        length_mm=Decimal(str(length_mm)),
        width_mm=Decimal(str(width_mm)),
        height_mm=Decimal(str(height_mm)),
        weight_grams=Decimal(str(weight_grams)),
        is_base_unit=False,
        is_active=is_active,
    )
    db_session.add(pu)
    db_session.flush()
    return pu


def _create_bin(
    db_session,
    org_id,
    warehouse_id,
    code,
    capacity=1000,
    max_volume_cc=None,
    max_weight_grams=None,
):
    """Create and persist a bin WarehouseLocation."""
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        location_type="bin",
        code=code,
        full_path=code,
        capacity=Decimal(str(capacity)),
        total_capacity=Decimal(str(capacity)),
        available_capacity=Decimal(str(capacity)),
        is_active=True,
        version=1,
        position_x=Decimal("0"),
        position_y=Decimal("0"),
        max_volume_cc=Decimal(str(max_volume_cc)) if max_volume_cc else None,
        max_weight_grams=Decimal(str(max_weight_grams)) if max_weight_grams else None,
    )
    db_session.add(loc)
    db_session.flush()
    return loc


def _build_qr_payload(qr_id, sku, qty, batch, packaging_unit_qr_id=None):
    """Build a JSON QR payload string."""
    payload = {"id": qr_id, "sku": sku, "qty": qty, "batch": batch}
    if packaging_unit_qr_id:
        payload["packaging_unit_qr_id"] = packaging_unit_qr_id
    return json.dumps(payload)


# ---------------------------------------------------------------------------
# Full inbound flow integration test
# ---------------------------------------------------------------------------


class TestFullInboundFlowWithPackagingUnits:
    """End-to-end integration test for the inbound flow with Multi-UOM packaging units.

    Requirements: 5.3, 5.5, 6.1, 6.2, 6.4, 7.1, 7.6, 3.3
    """

    def test_complete_inbound_flow(
        self,
        db_session,
        inbound_service,
        put_away_service,
        org_id,
        worker_id,
        warehouse_id,
    ):
        """
        Full inbound flow:
          1. Scan with packaging_unit_qr_id → raw_quantity stored, packaging_unit_id resolved
          2. End session → receiving slip created (pending_review)
          3. Approve slip → ReceivingSlipItem.quantity == 5 * 12 == 60 Eaches
          4. PutAwayList generated; PutAwayListItem.quantity == 60
          5. Complete put-away → BinStockLevel.quantity_on_hand == 60, packaging_unit_id set
        """
        # ----------------------------------------------------------------
        # Setup: item, packaging unit, warehouse bin
        # ----------------------------------------------------------------
        item = _create_item(db_session, org_id, item_code="WIDGET-001", sku="WIDGET-001")
        pu = _create_packaging_unit(
            db_session,
            org_id,
            item_id=item.id,
            unit_name="Box of 12",
            qr_identifier="BOX-12-WIDGET",
            conversion_factor=12,
            length_mm=300,
            width_mm=200,
            height_mm=150,
            weight_grams=1440,
        )
        bin_loc = _create_bin(
            db_session,
            org_id,
            warehouse_id,
            code="Z01-A01-B01-L01-BIN01",
            capacity=1000,
            max_volume_cc=500000,
            max_weight_grams=100000,
        )
        db_session.commit()

        # ----------------------------------------------------------------
        # Step 1: Start session and record scan
        # ----------------------------------------------------------------
        session_result = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
            dock_location="Dock A",
        )
        session_id = uuid.UUID(session_result["id"])

        qr_payload = _build_qr_payload(
            qr_id="QR-BOX-001",
            sku="WIDGET-001",
            qty=5,
            batch="BATCH-2025-01",
            packaging_unit_qr_id="BOX-12-WIDGET",
        )

        scan_result = inbound_service.record_scan(
            session_id=session_id,
            qr_data=qr_payload,
            worker_id=worker_id,
            organization_id=org_id,
        )

        # Assert raw_quantity == 5 (boxes scanned, not Eaches)
        assert scan_result["raw_quantity"] == 5, (
            f"Expected raw_quantity=5, got {scan_result['raw_quantity']}"
        )

        # Assert packaging_unit_id is resolved (not None)
        assert scan_result["packaging_unit_id"] is not None, (
            "packaging_unit_id should be resolved from QR payload"
        )
        assert scan_result["packaging_unit_id"] == str(pu.id)

        # Verify the ScanSessionItem in the DB
        scan_item = (
            db_session.query(ScanSessionItem)
            .filter(ScanSessionItem.session_id == session_id)
            .first()
        )
        assert scan_item is not None
        assert scan_item.raw_quantity == 5
        assert scan_item.packaging_unit_id == pu.id

        # ----------------------------------------------------------------
        # Step 2: End session → receiving slip created
        # ----------------------------------------------------------------
        slip_result = inbound_service.end_session(
            session_id=session_id,
            worker_id=worker_id,
            organization_id=org_id,
        )

        assert slip_result["status"] == "pending_review", (
            f"Expected pending_review, got {slip_result['status']}"
        )
        slip_id = uuid.UUID(slip_result["id"])

        # Verify slip exists in DB
        slip = db_session.get(ReceivingSlip, slip_id)
        assert slip is not None

        # ----------------------------------------------------------------
        # Step 3: Approve slip → conversion raw_qty * conversion_factor
        # ----------------------------------------------------------------
        # Mock VolumetricAssignmentService.assign_bins to avoid FOR UPDATE SKIP LOCKED
        with patch(
            "app.services.put_away_service.VolumetricAssignmentService.assign_bins"
        ) as mock_assign:
            # Simulate the service assigning our bin to all put-away items
            def _fake_assign_bins(put_away_list_items, warehouse_id, org_id, db):
                for pai in put_away_list_items:
                    pai.bin_location_id = bin_loc.id

            mock_assign.side_effect = _fake_assign_bins

            approved_slip = inbound_service.approve_slip(
                slip_id=slip_id,
                organization_id=org_id,
            )

        assert approved_slip["status"] == "pending_putaway"

        # Assert ReceivingSlipItem.quantity == 5 * 12 == 60 Eaches
        slip_items = (
            db_session.query(ReceivingSlipItem)
            .filter(ReceivingSlipItem.slip_id == slip_id)
            .all()
        )
        assert len(slip_items) == 1
        assert int(slip_items[0].quantity) == 60, (
            f"Expected 60 Eaches (5 boxes × 12), got {slip_items[0].quantity}"
        )

        # ----------------------------------------------------------------
        # Step 4: Assert PutAwayList and PutAwayListItem
        # ----------------------------------------------------------------
        put_away_list = (
            db_session.query(PutAwayList)
            .filter(
                PutAwayList.receiving_slip_id == slip_id,
                PutAwayList.organization_id == org_id,
            )
            .first()
        )
        assert put_away_list is not None, "PutAwayList should be generated after approval"
        assert put_away_list.status == "pending"

        put_away_items = (
            db_session.query(PutAwayListItem)
            .filter(PutAwayListItem.put_away_list_id == put_away_list.id)
            .all()
        )
        assert len(put_away_items) > 0, "PutAwayListItem should exist"

        # Total quantity across all put-away items should be 60
        total_put_away_qty = sum(int(pai.quantity) for pai in put_away_items)
        assert total_put_away_qty == 60, (
            f"Expected total put-away quantity=60, got {total_put_away_qty}"
        )

        # ----------------------------------------------------------------
        # Step 5: Complete put-away → BinStockLevel updated
        # ----------------------------------------------------------------
        put_away_item = put_away_items[0]
        assert put_away_item.bin_location_id == bin_loc.id, (
            "bin_location_id should be set by the mocked VolumetricAssignmentService"
        )

        completed_item = put_away_service.complete_item(
            put_away_item_id=put_away_item.id,
            worker_id=worker_id,
            org_id=org_id,
        )
        assert completed_item.status == "completed"

        # Assert BinStockLevel.quantity_on_hand == 60 (in Eaches)
        bin_stock = (
            db_session.query(BinStockLevel)
            .filter(
                BinStockLevel.bin_location_id == bin_loc.id,
                BinStockLevel.item_id == item.id,
                BinStockLevel.organization_id == org_id,
            )
            .first()
        )
        assert bin_stock is not None, "BinStockLevel should be created after put-away"
        assert int(bin_stock.quantity_on_hand) == int(put_away_item.quantity), (
            f"Expected quantity_on_hand={int(put_away_item.quantity)}, "
            f"got {bin_stock.quantity_on_hand}"
        )

    def test_approve_slip_raises_422_for_inactive_packaging_unit(
        self,
        db_session,
        inbound_service,
        org_id,
        worker_id,
        warehouse_id,
    ):
        """Approving a slip referencing an inactive packaging unit raises HTTP 422.

        Requirements: 6.4
        """
        # Setup: item with an INACTIVE packaging unit
        item = _create_item(db_session, org_id, item_code="WIDGET-INACTIVE", sku="WIDGET-INACTIVE")
        pu_inactive = _create_packaging_unit(
            db_session,
            org_id,
            item_id=item.id,
            unit_name="Box of 6",
            qr_identifier="BOX-6-INACTIVE",
            conversion_factor=6,
            is_active=True,  # active at scan time
        )
        _create_bin(
            db_session,
            org_id,
            warehouse_id,
            code="Z01-A01-B01-L01-BIN02",
            capacity=1000,
        )
        db_session.commit()

        # Start session and scan
        session_result = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session_result["id"])

        qr_payload = _build_qr_payload(
            qr_id="QR-BOX-INACTIVE-001",
            sku="WIDGET-INACTIVE",
            qty=3,
            batch="BATCH-INACTIVE",
            packaging_unit_qr_id="BOX-6-INACTIVE",
        )
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=qr_payload,
            worker_id=worker_id,
            organization_id=org_id,
        )

        # End session → slip
        slip_result = inbound_service.end_session(
            session_id=session_id,
            worker_id=worker_id,
            organization_id=org_id,
        )
        slip_id = uuid.UUID(slip_result["id"])

        # Deactivate the packaging unit AFTER scanning but BEFORE approval
        pu_inactive.is_active = False
        db_session.flush()
        db_session.commit()

        # Approve should raise HTTP 422
        with pytest.raises(HTTPException) as exc_info:
            with patch(
                "app.services.put_away_service.VolumetricAssignmentService.assign_bins"
            ):
                inbound_service.approve_slip(
                    slip_id=slip_id,
                    organization_id=org_id,
                )

        assert exc_info.value.status_code == 422
        assert "not found or inactive" in exc_info.value.detail

    def test_scan_resolves_packaging_unit_id_from_qr_payload(
        self,
        db_session,
        inbound_service,
        org_id,
        worker_id,
        warehouse_id,
    ):
        """record_scan resolves packaging_unit_id from packaging_unit_qr_id in payload.

        Requirements: 5.3, 5.5
        """
        item = _create_item(db_session, org_id, item_code="WIDGET-SCAN", sku="WIDGET-SCAN")
        pu = _create_packaging_unit(
            db_session,
            org_id,
            item_id=item.id,
            unit_name="Pallet of 144",
            qr_identifier="PALLET-144-WIDGET",
            conversion_factor=144,
        )
        db_session.commit()

        session_result = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session_result["id"])

        qr_payload = _build_qr_payload(
            qr_id="QR-PALLET-001",
            sku="WIDGET-SCAN",
            qty=2,
            batch="BATCH-PALLET",
            packaging_unit_qr_id="PALLET-144-WIDGET",
        )
        scan_result = inbound_service.record_scan(
            session_id=session_id,
            qr_data=qr_payload,
            worker_id=worker_id,
            organization_id=org_id,
        )

        assert scan_result["raw_quantity"] == 2
        assert scan_result["packaging_unit_id"] == str(pu.id)

    def test_scan_without_packaging_unit_qr_id_leaves_packaging_unit_id_null(
        self,
        db_session,
        inbound_service,
        org_id,
        worker_id,
        warehouse_id,
    ):
        """record_scan with no packaging_unit_qr_id stores packaging_unit_id as None.

        Requirements: 5.3
        """
        _create_item(db_session, org_id, item_code="WIDGET-NOPKG", sku="WIDGET-NOPKG")
        db_session.commit()

        session_result = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session_result["id"])

        qr_payload = _build_qr_payload(
            qr_id="QR-NOPKG-001",
            sku="WIDGET-NOPKG",
            qty=10,
            batch="BATCH-NOPKG",
            # No packaging_unit_qr_id
        )
        scan_result = inbound_service.record_scan(
            session_id=session_id,
            qr_data=qr_payload,
            worker_id=worker_id,
            organization_id=org_id,
        )

        assert scan_result["raw_quantity"] == 10
        assert scan_result["packaging_unit_id"] is None

    def test_approve_slip_without_packaging_unit_uses_raw_quantity_as_eaches(
        self,
        db_session,
        inbound_service,
        org_id,
        worker_id,
        warehouse_id,
    ):
        """When packaging_unit_id is null, raw_quantity is used directly as Eaches.

        Requirements: 6.3
        """
        item = _create_item(db_session, org_id, item_code="WIDGET-DIRECT", sku="WIDGET-DIRECT")
        _create_bin(
            db_session,
            org_id,
            warehouse_id,
            code="Z01-A01-B01-L01-BIN03",
            capacity=1000,
        )
        db_session.commit()

        session_result = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session_result["id"])

        qr_payload = _build_qr_payload(
            qr_id="QR-DIRECT-001",
            sku="WIDGET-DIRECT",
            qty=25,
            batch="BATCH-DIRECT",
        )
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=qr_payload,
            worker_id=worker_id,
            organization_id=org_id,
        )

        slip_result = inbound_service.end_session(
            session_id=session_id,
            worker_id=worker_id,
            organization_id=org_id,
        )
        slip_id = uuid.UUID(slip_result["id"])

        with patch(
            "app.services.put_away_service.VolumetricAssignmentService.assign_bins"
        ):
            approved = inbound_service.approve_slip(
                slip_id=slip_id,
                organization_id=org_id,
            )

        assert approved["status"] == "pending_putaway"

        slip_items = (
            db_session.query(ReceivingSlipItem)
            .filter(ReceivingSlipItem.slip_id == slip_id)
            .all()
        )
        assert len(slip_items) == 1
        # No conversion — raw_quantity 25 should equal Eaches quantity 25
        assert int(slip_items[0].quantity) == 25, (
            f"Expected 25 Eaches (no conversion), got {slip_items[0].quantity}"
        )

    def test_bin_stock_level_packaging_unit_id_is_set_after_put_away(
        self,
        db_session,
        inbound_service,
        put_away_service,
        org_id,
        worker_id,
        warehouse_id,
    ):
        """After completing put-away, BinStockLevel.packaging_unit_id is set (Req 3.3).

        This verifies traceability: the packaging unit used during inbound is
        recorded on the bin stock level row.
        """
        item = _create_item(db_session, org_id, item_code="WIDGET-TRACE", sku="WIDGET-TRACE")
        pu = _create_packaging_unit(
            db_session,
            org_id,
            item_id=item.id,
            unit_name="Box of 12",
            qr_identifier="BOX-12-TRACE",
            conversion_factor=12,
            length_mm=300,
            width_mm=200,
            height_mm=150,
            weight_grams=1440,
        )
        bin_loc = _create_bin(
            db_session,
            org_id,
            warehouse_id,
            code="Z01-A01-B01-L01-BIN04",
            capacity=1000,
        )
        db_session.commit()

        # Scan
        session_result = inbound_service.start_session(
            worker_id=worker_id,
            organization_id=org_id,
            warehouse_id=warehouse_id,
        )
        session_id = uuid.UUID(session_result["id"])

        qr_payload = _build_qr_payload(
            qr_id="QR-TRACE-001",
            sku="WIDGET-TRACE",
            qty=1,
            batch="BATCH-TRACE",
            packaging_unit_qr_id="BOX-12-TRACE",
        )
        inbound_service.record_scan(
            session_id=session_id,
            qr_data=qr_payload,
            worker_id=worker_id,
            organization_id=org_id,
        )

        # End session
        slip_result = inbound_service.end_session(
            session_id=session_id,
            worker_id=worker_id,
            organization_id=org_id,
        )
        slip_id = uuid.UUID(slip_result["id"])

        # Approve (mock volumetric assignment to assign our bin)
        with patch(
            "app.services.put_away_service.VolumetricAssignmentService.assign_bins"
        ) as mock_assign:
            def _fake_assign(put_away_list_items, warehouse_id, org_id, db):
                for pai in put_away_list_items:
                    pai.bin_location_id = bin_loc.id
                    # Also set packaging_unit_id on the put-away item for traceability
                    pai.packaging_unit_id = pu.id

            mock_assign.side_effect = _fake_assign

            inbound_service.approve_slip(
                slip_id=slip_id,
                organization_id=org_id,
            )

        # Get the put-away item
        put_away_list = (
            db_session.query(PutAwayList)
            .filter(PutAwayList.receiving_slip_id == slip_id)
            .first()
        )
        assert put_away_list is not None

        put_away_item = (
            db_session.query(PutAwayListItem)
            .filter(PutAwayListItem.put_away_list_id == put_away_list.id)
            .first()
        )
        assert put_away_item is not None
        assert put_away_item.bin_location_id == bin_loc.id

        # Complete put-away
        put_away_service.complete_item(
            put_away_item_id=put_away_item.id,
            worker_id=worker_id,
            org_id=org_id,
        )

        # Assert BinStockLevel.packaging_unit_id is set
        bin_stock = (
            db_session.query(BinStockLevel)
            .filter(
                BinStockLevel.bin_location_id == bin_loc.id,
                BinStockLevel.item_id == item.id,
            )
            .first()
        )
        assert bin_stock is not None
        # packaging_unit_id should be set (from put_away_item.packaging_unit_id)
        assert bin_stock.packaging_unit_id == pu.id, (
            "BinStockLevel.packaging_unit_id should be set for traceability (Req 3.3)"
        )
