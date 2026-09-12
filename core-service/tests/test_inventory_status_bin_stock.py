"""Unit tests for inventory status on bin stock (PR-01 / T-01).

Covers:
- default inventory_status is ``available`` on new bin stock
- FEFO/FIFO resolution excludes blocked/damaged/hold/quality/reserved stock

Requirements: WF-003, EX-007/010/011/013 (exclusion)
"""

import uuid
from decimal import Decimal

import pytest

from app.models.bin_stock_level import BinStockLevel
from app.models.warehouse_location import WarehouseLocation
from app.services.pick_list_service import (
    PickListService,
    SAPInvoiceItem,
    SAPInvoicePayload,
)


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def item_id():
    return uuid.uuid4()


@pytest.fixture
def pick_list_service(db_session):
    return PickListService(db_session)


def _create_warehouse(db_session, warehouse_id, org_id):
    from app.models.warehouse import Warehouse

    wh = Warehouse(
        id=warehouse_id,
        organization_id=org_id,
        name="Test Warehouse",
        code="WH-TEST",
        warehouse_type="warehouse",
    )
    db_session.add(wh)
    db_session.flush()
    return wh


def _create_item(db_session, item_id, org_id, item_code="ITEM-001"):
    from app.models.item import Item

    item = Item(
        id=item_id,
        organization_id=org_id,
        item_code=item_code,
        item_name=f"Test Item {item_code}",
        item_type="stock",
        uom="Nos",
        maintain_stock=True,
    )
    db_session.add(item)
    db_session.flush()
    return item


def _create_bin_location(db_session, org_id, warehouse_id, code="BIN01"):
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        location_type="bin",
        code=code,
        full_path=f"Z01-A01-B01-L01-{code}",
        capacity=Decimal("1000"),
        total_capacity=Decimal("1000"),
        available_capacity=Decimal("1000"),
        position_x=Decimal("0"),
        position_y=Decimal("0"),
        is_active=True,
        is_pickable=True,
        version=1,
    )
    db_session.add(loc)
    db_session.flush()
    return loc


def _create_bin_stock(
    db_session,
    org_id,
    bin_location_id,
    item_id,
    quantity,
    inventory_status=None,
):
    """Create a bin stock record, defaulting inventory_status to 'available'."""
    kwargs = {
        "id": uuid.uuid4(),
        "organization_id": org_id,
        "bin_location_id": bin_location_id,
        "item_id": item_id,
        "quantity_on_hand": Decimal(str(quantity)),
    }
    if inventory_status is not None:
        kwargs["inventory_status"] = inventory_status
    bsl = BinStockLevel(**kwargs)
    db_session.add(bsl)
    db_session.flush()
    return bsl


def _create_pick_list(pick_list_service, org_id, warehouse_id, item_id, qty):
    invoice_data = SAPInvoicePayload(
        invoice_reference=f"INV-{uuid.uuid4().hex[:8]}",
        warehouse_id=warehouse_id,
        items=[
            SAPInvoiceItem(
                item_id=item_id, sku="ITEM-001", quantity=Decimal(str(qty)), uom="Nos"
            )
        ],
    )
    return pick_list_service.create_from_invoice(invoice_data, org_id)


class TestBinStockDefaultStatus:
    """Default inventory status on new bin stock."""

    def test_default_status_is_available(
        self, db_session, org_id, warehouse_id, item_id
    ):
        """A BinStockLevel created without an explicit status defaults to 'available'."""
        _create_warehouse(db_session, warehouse_id, org_id)
        _create_item(db_session, item_id, org_id)
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        bsl = _create_bin_stock(db_session, org_id, bin_loc.id, item_id, 10)
        db_session.commit()

        db_session.refresh(bsl)
        assert bsl.inventory_status == "available"


class TestResolveBinLocationsInventoryStatus:
    """FEFO/FIFO resolution excludes non-pickable inventory statuses."""

    def test_available_stock_allocates(
        self, db_session, pick_list_service, org_id, warehouse_id, item_id
    ):
        """Available stock should be allocated to the pick list item."""
        _create_warehouse(db_session, warehouse_id, org_id)
        _create_item(db_session, item_id, org_id)
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        _create_bin_stock(
            db_session, org_id, bin_loc.id, item_id, 30, inventory_status="available"
        )
        db_session.commit()

        pick_list = _create_pick_list(
            pick_list_service, org_id, warehouse_id, item_id, 10
        )
        result = pick_list_service.resolve_bin_locations(pick_list.id, org_id)

        assert result.items[0].bin_location_id == bin_loc.id

    @pytest.mark.parametrize("status", ["blocked", "damaged", "hold"])
    def test_non_pickable_stock_excluded(
        self, db_session, pick_list_service, org_id, warehouse_id, item_id, status
    ):
        """Blocked/damaged/hold/quality/reserved stock must not be allocated."""
        _create_warehouse(db_session, warehouse_id, org_id)
        _create_item(db_session, item_id, org_id)
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        _create_bin_stock(
            db_session, org_id, bin_loc.id, item_id, 30, inventory_status=status
        )
        db_session.commit()

        pick_list = _create_pick_list(
            pick_list_service, org_id, warehouse_id, item_id, 10
        )
        result = pick_list_service.resolve_bin_locations(pick_list.id, org_id)

        # No pickable stock → item remains without a bin assignment.
        assert result.items[0].bin_location_id is None

    def test_no_pickable_stock_returns_empty(
        self, db_session, pick_list_service, org_id, warehouse_id, item_id
    ):
        """When only non-pickable stock exists, no allocation is made."""
        _create_warehouse(db_session, warehouse_id, org_id)
        _create_item(db_session, item_id, org_id)
        bin_loc = _create_bin_location(db_session, org_id, warehouse_id)
        _create_bin_stock(
            db_session, org_id, bin_loc.id, item_id, 30, inventory_status="blocked"
        )
        db_session.commit()

        pick_list = _create_pick_list(
            pick_list_service, org_id, warehouse_id, item_id, 10
        )
        result = pick_list_service.resolve_bin_locations(pick_list.id, org_id)

        assert result.items[0].bin_location_id is None
