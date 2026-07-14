"""Unit tests for OutboundService dispatch record management."""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundError, StateError
from app.models.gate_verification import GateVerificationSession
from app.models.pick_list import PickList, PickListItem
from app.models.stock_level import StockLevel
from app.services.outbound_service import OutboundService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id(db_session, org_id):
    """Create a warehouse record for FK constraints."""
    from app.models.warehouse import Warehouse

    wh = Warehouse(
        id=uuid.uuid4(),
        organization_id=org_id,
        code="WH-TEST",
        name="Test Warehouse",
    )
    db_session.add(wh)
    db_session.commit()
    db_session.refresh(wh)
    return wh.id


@pytest.fixture
def item_id(db_session, org_id):
    """Create an item record for FK constraints."""
    from app.models.item import Item

    item = Item(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_code="ITEM-001",
        item_name="Test Item",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item.id


@pytest.fixture
def pick_list(db_session, org_id, warehouse_id):
    """Create a pick list for testing."""
    pl = PickList(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_no="PL-2025-00001",
        warehouse_id=warehouse_id,
        status="completed",
        invoice_reference="INV-2025-001",
    )
    db_session.add(pl)
    db_session.commit()
    db_session.refresh(pl)
    return pl


@pytest.fixture
def pick_list_with_items(db_session, org_id, warehouse_id, item_id, pick_list):
    """Create a pick list with items for stock decrement testing."""
    pli = PickListItem(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_id=pick_list.id,
        item_id=item_id,
        warehouse_id=warehouse_id,
        qty=Decimal("10"),
        picked_qty=Decimal("10"),
        uom="Pieces",
    )
    db_session.add(pli)
    db_session.commit()
    return pick_list


@pytest.fixture
def stock_level(db_session, org_id, warehouse_id, item_id):
    """Create a stock level record."""
    sl = StockLevel(
        id=uuid.uuid4(),
        organization_id=org_id,
        product_id=item_id,
        warehouse_id=warehouse_id,
        quantity_on_hand=100,
        quantity_reserved=10,
        quantity_available=90,
    )
    db_session.add(sl)
    db_session.commit()
    db_session.refresh(sl)
    return sl


@pytest.fixture
def verified_gate_session(db_session, org_id, warehouse_id, worker_id, pick_list):
    """Create a verified gate verification session."""
    gs = GateVerificationSession(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_id=pick_list.id,
        warehouse_id=warehouse_id,
        worker_id=worker_id,
        vehicle_number="KA-01-AB-1234",
        driver_name="John Driver",
        status="verified",
        verified_at=datetime.now(UTC),
    )
    db_session.add(gs)
    db_session.commit()
    db_session.refresh(gs)
    return gs


@pytest.fixture
def open_gate_session(db_session, org_id, warehouse_id, worker_id, pick_list):
    """Create an open (non-verified) gate verification session."""
    gs = GateVerificationSession(
        id=uuid.uuid4(),
        organization_id=org_id,
        pick_list_id=pick_list.id,
        warehouse_id=warehouse_id,
        worker_id=worker_id,
        vehicle_number="KA-02-CD-5678",
        driver_name="Jane Driver",
        status="open",
    )
    db_session.add(gs)
    db_session.commit()
    db_session.refresh(gs)
    return gs


@pytest.fixture
def outbound_service(db_session):
    return OutboundService(db_session)


class TestCreateDispatch:
    """Tests for create_dispatch method."""

    def test_creates_dispatch_from_verified_session(
        self, outbound_service, org_id, verified_gate_session, pick_list
    ):
        """Should create a dispatch record from a verified gate session."""
        result = outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        assert result["dispatch_number"] is not None
        assert result["pick_list_id"] == str(pick_list.id)
        assert result["gate_session_id"] == str(verified_gate_session.id)
        assert result["vehicle_number"] == "KA-01-AB-1234"
        assert result["driver_name"] == "John Driver"
        assert result["invoice_reference"] == "INV-2025-001"
        assert result["dispatched_at"] is not None

    def test_generates_unique_dispatch_number(
        self, outbound_service, org_id, verified_gate_session
    ):
        """Should generate a dispatch number using document numbering service."""
        result = outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        # Dispatch number should follow the pattern DSP-YYYY-NNNNN
        assert result["dispatch_number"].startswith("DSP-")

    def test_updates_pick_list_dispatch_reference(
        self, outbound_service, org_id, verified_gate_session, pick_list, db_session
    ):
        """Should update the pick list with dispatch record reference."""
        result = outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        db_session.refresh(pick_list)
        assert str(pick_list.dispatch_record_id) == result["id"]

    def test_decrements_stock_levels(
        self,
        outbound_service,
        org_id,
        verified_gate_session,
        pick_list_with_items,
        stock_level,
        db_session,
    ):
        """Should decrement warehouse stock levels for dispatched items."""
        # Stock starts at 100 on_hand
        assert stock_level.quantity_on_hand == 100

        outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        db_session.refresh(stock_level)
        # Should be decremented by picked_qty (10)
        assert stock_level.quantity_on_hand == 90

    def test_raises_not_found_for_missing_session(self, outbound_service, org_id):
        """Should raise NotFoundError if gate session doesn't exist."""
        with pytest.raises(NotFoundError) as exc_info:
            outbound_service.create_dispatch(
                gate_session_id=uuid.uuid4(),
                org_id=org_id,
            )

        assert "Gate verification session not found" in str(exc_info.value)

    def test_raises_state_error_for_non_verified_session(
        self, outbound_service, org_id, open_gate_session
    ):
        """Should raise StateError if gate session is not verified."""
        with pytest.raises(StateError) as exc_info:
            outbound_service.create_dispatch(
                gate_session_id=open_gate_session.id,
                org_id=org_id,
            )

        assert "VERIFIED" in str(exc_info.value)

    def test_raises_not_found_for_wrong_org(
        self, outbound_service, verified_gate_session
    ):
        """Should raise NotFoundError if gate session belongs to different org."""
        with pytest.raises(NotFoundError):
            outbound_service.create_dispatch(
                gate_session_id=verified_gate_session.id,
                org_id=uuid.uuid4(),  # Different org
            )


class TestListDispatches:
    """Tests for list_dispatches method."""

    def test_lists_dispatches_for_org(
        self, outbound_service, org_id, verified_gate_session
    ):
        """Should list dispatch records for the organization."""
        # Create a dispatch first
        outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        result = outbound_service.list_dispatches(org_id=org_id)

        assert len(result["dispatches"]) == 1
        assert result["pagination"]["total_items"] == 1
        assert result["pagination"]["page"] == 1

    def test_filters_by_vehicle_number(
        self, outbound_service, org_id, verified_gate_session
    ):
        """Should filter dispatches by vehicle number."""
        outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        # Should find with partial match
        result = outbound_service.list_dispatches(org_id=org_id, vehicle_number="KA-01")
        assert len(result["dispatches"]) == 1

        # Should not find with non-matching
        result = outbound_service.list_dispatches(
            org_id=org_id, vehicle_number="NONEXISTENT"
        )
        assert len(result["dispatches"]) == 0

    def test_filters_by_invoice_reference(
        self, outbound_service, org_id, verified_gate_session
    ):
        """Should filter dispatches by invoice reference."""
        outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        result = outbound_service.list_dispatches(
            org_id=org_id, invoice_reference="INV-2025"
        )
        assert len(result["dispatches"]) == 1

        result = outbound_service.list_dispatches(
            org_id=org_id, invoice_reference="NONEXISTENT"
        )
        assert len(result["dispatches"]) == 0

    def test_filters_by_date_range(
        self, outbound_service, org_id, verified_gate_session
    ):
        """Should filter dispatches by date range."""
        outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        # Should find with wide date range
        result = outbound_service.list_dispatches(
            org_id=org_id,
            date_from=datetime(2020, 1, 1, tzinfo=UTC),
            date_to=datetime(2030, 12, 31, tzinfo=UTC),
        )
        assert len(result["dispatches"]) == 1

        # Should not find with past date range
        result = outbound_service.list_dispatches(
            org_id=org_id,
            date_from=datetime(2020, 1, 1, tzinfo=UTC),
            date_to=datetime(2020, 12, 31, tzinfo=UTC),
        )
        assert len(result["dispatches"]) == 0

    def test_pagination(self, outbound_service, org_id):
        """Should return correct pagination metadata."""
        result = outbound_service.list_dispatches(org_id=org_id, page=1, page_size=10)

        assert result["pagination"]["page"] == 1
        assert result["pagination"]["page_size"] == 10
        assert result["pagination"]["total_items"] == 0
        assert result["pagination"]["has_next"] is False
        assert result["pagination"]["has_prev"] is False

    def test_returns_empty_for_different_org(
        self, outbound_service, org_id, verified_gate_session
    ):
        """Should return empty list for a different organization."""
        outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        result = outbound_service.list_dispatches(org_id=uuid.uuid4())
        assert len(result["dispatches"]) == 0


class TestGetDispatch:
    """Tests for get_dispatch method."""

    def test_gets_dispatch_by_id(self, outbound_service, org_id, verified_gate_session):
        """Should retrieve a dispatch record by ID."""
        created = outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        result = outbound_service.get_dispatch(
            dispatch_id=uuid.UUID(created["id"]),
            org_id=org_id,
        )

        assert result["id"] == created["id"]
        assert result["dispatch_number"] == created["dispatch_number"]

    def test_raises_not_found_for_missing_dispatch(self, outbound_service, org_id):
        """Should raise NotFoundError if dispatch doesn't exist."""
        with pytest.raises(NotFoundError) as exc_info:
            outbound_service.get_dispatch(
                dispatch_id=uuid.uuid4(),
                org_id=org_id,
            )

        assert "Dispatch record not found" in str(exc_info.value)

    def test_raises_not_found_for_wrong_org(
        self, outbound_service, org_id, verified_gate_session
    ):
        """Should raise NotFoundError if dispatch belongs to different org."""
        created = outbound_service.create_dispatch(
            gate_session_id=verified_gate_session.id,
            org_id=org_id,
        )

        with pytest.raises(NotFoundError):
            outbound_service.get_dispatch(
                dispatch_id=uuid.UUID(created["id"]),
                org_id=uuid.uuid4(),  # Different org
            )
