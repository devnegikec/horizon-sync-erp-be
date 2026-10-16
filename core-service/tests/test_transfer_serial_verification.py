"""Database-backed tests for the internal-transfer serial verification path (T3.4).

Skipped by default (set ``RUN_DATABASE_TESTS=1`` to run): the SQLite fixture
cannot compile PostgreSQL UUID columns unless enabled. Covers:

* T3.3 — ASN closure is blocked while unreceived transfer serials remain.
* T0.3 / T0.4 — unknown serial is classified ``UNEXPECTED_SERIAL`` (not EXCESS).
* T0.1 / G2 — quantity-only transfers skip verification silently (guard).
"""

import uuid
from datetime import UTC, datetime

import pytest

from app.core.exceptions import ValidationError
from app.models.asn_order import AsnOrder, AsnOrderItem, AsnOrderSerialLine
from app.models.base import AsnOrderStatus
from app.models.inbound_exception import InboundException, InboundExceptionReason
from app.models.item import Item
from app.models.scan_session import ScanSession
from app.services.asn_order_service import AsnOrderService
from app.services.inbound_service import InboundService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id(db_session, org_id):
    from app.models.warehouse import Warehouse

    wh = Warehouse(
        id=uuid.uuid4(),
        organization_id=org_id,
        code="WH-T",
        name="Warehouse T",
    )
    db_session.add(wh)
    db_session.commit()
    db_session.refresh(wh)
    return wh.id


@pytest.fixture
def inbound_reason_codes(db_session):
    """Seed the Phase-0 reason codes the matcher relies on."""
    for code, name, category in (
        ("UNEXPECTED_SERIAL", "Unexpected serial", "unexpected_sku"),
        ("WRONG_ITEM", "Wrong item", "unexpected_sku"),
        ("MISSING_SERIAL", "Missing serial", "short"),
    ):
        db_session.add(
            InboundExceptionReason(
                id=uuid.uuid4(), code=code, name=name, category=category
            )
        )
    db_session.commit()


def _make_item(db, org_id, sku="SKU-A"):
    item = Item(
        organization_id=org_id,
        item_code=f"CODE-{uuid.uuid4().hex[:6]}",
        item_name="Widget",
        sku=sku,
        has_serial_no=True,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def _make_transfer_asn(db, org_id, item_id, from_wh, to_wh, serials, status):
    asn = AsnOrder(
        organization_id=org_id,
        asn_order_no=f"ASN-{uuid.uuid4().hex[:8]}",
        warehouse_id_from=from_wh,
        warehouse_id_to=to_wh,
        order_date=datetime.now(UTC),
        status=status,
        asn_type="internal_transfer",
    )
    db.add(asn)
    db.flush()
    db.add(
        AsnOrderItem(
            organization_id=org_id,
            asn_order_id=asn.id,
            item_id=item_id,
            qty=len(serials),
            uom="Nos",
        )
    )
    for serial in serials:
        db.add(
            AsnOrderSerialLine(
                organization_id=org_id,
                asn_order_id=asn.id,
                item_id=item_id,
                serial_no=serial,
            )
        )
    db.commit()
    db.refresh(asn)
    return asn


def _make_session(db, org_id, warehouse_id, asn_order_id):
    session = ScanSession(
        organization_id=org_id,
        session_type="inbound",
        worker_id=uuid.uuid4(),
        warehouse_id=warehouse_id,
        asn_order_id=asn_order_id,
        status="open",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


class TestClosureGate:
    """T3.3 — unreceived serials block ASN closure."""

    def test_close_blocked_while_serials_unreceived(
        self, db_session, org_id, worker_id, warehouse_id
    ):
        item = _make_item(db_session, org_id)
        asn = _make_transfer_asn(
            db_session,
            org_id,
            item.id,
            warehouse_id,
            warehouse_id,
            serials=["S1", "S2"],
            status=AsnOrderStatus.DELIVERED,
        )

        with pytest.raises(ValidationError) as exc_info:
            AsnOrderService(db_session).update_status(
                asn.id, "closed", org_id, worker_id
            )

        assert "not been received" in exc_info.value.message

    def test_close_allowed_when_all_serials_received(
        self, db_session, org_id, worker_id, warehouse_id
    ):
        item = _make_item(db_session, org_id)
        asn = _make_transfer_asn(
            db_session,
            org_id,
            item.id,
            warehouse_id,
            warehouse_id,
            serials=["S1"],
            status=AsnOrderStatus.DELIVERED,
        )
        line = (
            db_session.query(AsnOrderSerialLine)
            .filter(AsnOrderSerialLine.asn_order_id == asn.id)
            .first()
        )
        line.received = True
        db_session.commit()

        result = AsnOrderService(db_session).update_status(
            asn.id, "closed", org_id, worker_id
        )
        assert result["status"] == "closed"


class TestTransferSerialMatcher:
    """T0.3 / T0.4 — unknown serials are classified UNEXPECTED_SERIAL."""

    def test_unknown_serial_raises_and_records_unexpected_serial(
        self,
        db_session,
        org_id,
        worker_id,
        warehouse_id,
        inbound_reason_codes,
    ):
        item = _make_item(db_session, org_id)
        asn = _make_transfer_asn(
            db_session,
            org_id,
            item.id,
            warehouse_id,
            warehouse_id,
            serials=["S1"],
            status=AsnOrderStatus.CONFIRMED,
        )
        session = _make_session(db_session, org_id, warehouse_id, asn.id)

        with pytest.raises(ValidationError):
            InboundService(db_session)._verify_and_receive_transfer_serial(
                asn_order=asn,
                serial_no="S-UNKNOWN",
                item=item,
                session=session,
                worker_id=worker_id,
                organization_id=org_id,
            )

        exception = (
            db_session.query(InboundException)
            .filter(InboundException.asn_order_id == asn.id)
            .first()
        )
        assert exception is not None
        assert exception.reason_code == "UNEXPECTED_SERIAL"
        assert exception.exception_type == "serial_not_in_asn"

    def test_quantity_only_transfer_skips_verification(
        self, db_session, org_id, worker_id, warehouse_id
    ):
        item = _make_item(db_session, org_id)
        asn = _make_transfer_asn(
            db_session,
            org_id,
            item.id,
            warehouse_id,
            warehouse_id,
            serials=[],
            status=AsnOrderStatus.CONFIRMED,
        )
        session = _make_session(db_session, org_id, warehouse_id, asn.id)

        # No serial lines → the matcher returns without raising or recording.
        InboundService(db_session)._verify_and_receive_transfer_serial(
            asn_order=asn,
            serial_no="S-ANY",
            item=item,
            session=session,
            worker_id=worker_id,
            organization_id=org_id,
        )
