"""Unit tests for PickListService SAP invoice webhook wiring.

Tests that create_from_invoice properly wires together:
- FIFO bin resolution (resolve_bin_locations)
- Routing optimization (sort_order assignment)
- Worker task creation (TaskService.create_task)

Requirements: 9.3, 9.4
"""

import uuid
from decimal import Decimal

import pytest

from app.models.bin_stock_level import BinStockLevel
from app.models.warehouse_location import WarehouseLocation
from app.models.worker_task import WorkerTask
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
def worker_id():
    return uuid.uuid4()


@pytest.fixture
def pick_list_service(db_session):
    return PickListService(db_session)


def _create_warehouse(db_session, warehouse_id, org_id):
    """Helper to create a warehouse record for FK constraints."""
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
    """Helper to create an item record."""
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


def _create_bin_location(
    db_session,
    org_id,
    warehouse_id,
    code="BIN01",
    full_path="Z01-A01-B01-L01-BIN01",
    position_x=0,
    position_y=0,
    capacity=100,
):
    """Helper to create a bin location."""
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        location_type="bin",
        code=code,
        full_path=full_path,
        capacity=Decimal(str(capacity)),
        total_capacity=Decimal(str(capacity)),
        available_capacity=Decimal(str(capacity)),
        position_x=Decimal(str(position_x)),
        position_y=Decimal(str(position_y)),
        is_active=True,
        version=1,
    )
    db_session.add(loc)
    db_session.flush()
    return loc


def _create_bin_stock(db_session, org_id, bin_location_id, item_id, quantity):
    """Helper to create a bin stock level record."""
    bsl = BinStockLevel(
        id=uuid.uuid4(),
        organization_id=org_id,
        bin_location_id=bin_location_id,
        item_id=item_id,
        quantity_on_hand=Decimal(str(quantity)),
    )
    db_session.add(bsl)
    db_session.flush()
    return bsl


class TestCreateFromInvoiceWiring:
    """Tests that create_from_invoice wires bin resolution, routing, and task creation."""

    def test_resolves_bin_locations_on_create(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """create_from_invoice should resolve bin locations using FIFO (Req 9.3)."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "SKU-A")

        bin1 = _create_bin_location(
            db_session,
            org_id,
            warehouse_id,
            "BIN01",
            "Z01-A01-B01-L01-BIN01",
            position_x=5,
            position_y=5,
        )
        _create_bin_stock(db_session, org_id, bin1.id, item_id, 100)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-WIRE-001",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id, sku="SKU-A", quantity=Decimal("20"), uom="Nos"
                ),
            ],
        )

        result = pick_list_service.create_from_invoice(invoice_data, org_id)

        # Bin location should be resolved
        assert len(result.items) == 1
        assert result.items[0].bin_location_id == bin1.id

    def test_sets_sort_order_via_routing_optimizer(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """create_from_invoice should set sort_order on items via RoutingOptimizer (Req 9.4)."""
        _create_warehouse(db_session, warehouse_id, org_id)

        item1_id = uuid.uuid4()
        item2_id = uuid.uuid4()
        _create_item(db_session, item1_id, org_id, "SKU-A")
        _create_item(db_session, item2_id, org_id, "SKU-B")

        # Create bins at different positions in different aisles
        bin1 = _create_bin_location(
            db_session,
            org_id,
            warehouse_id,
            "BIN01",
            "Z01-A02-B01-L01-BIN01",
            position_x=10,
            position_y=10,
        )
        bin2 = _create_bin_location(
            db_session,
            org_id,
            warehouse_id,
            "BIN02",
            "Z01-A01-B01-L01-BIN02",
            position_x=1,
            position_y=1,
        )

        _create_bin_stock(db_session, org_id, bin1.id, item1_id, 100)
        _create_bin_stock(db_session, org_id, bin2.id, item2_id, 100)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-WIRE-002",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item1_id, sku="SKU-A", quantity=Decimal("5"), uom="Nos"
                ),
                SAPInvoiceItem(
                    item_id=item2_id, sku="SKU-B", quantity=Decimal("5"), uom="Nos"
                ),
            ],
        )

        result = pick_list_service.create_from_invoice(invoice_data, org_id)

        # Both items should have sort_order assigned (positive integers)
        sort_orders = [item.sort_order for item in result.items]
        assert all(so > 0 for so in sort_orders)
        # Sort orders should be unique sequential integers
        assert sorted(sort_orders) == [1, 2]

    def test_creates_worker_task_when_worker_id_provided(
        self, db_session, pick_list_service, org_id, warehouse_id, worker_id
    ):
        """create_from_invoice should create a worker task via TaskService (Req 9.3, 9.4)."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "SKU-A")

        bin1 = _create_bin_location(
            db_session,
            org_id,
            warehouse_id,
            "BIN01",
            "Z01-A01-B01-L01-BIN01",
        )
        _create_bin_stock(db_session, org_id, bin1.id, item_id, 100)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-WIRE-003",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id, sku="SKU-A", quantity=Decimal("10"), uom="Nos"
                ),
            ],
        )

        result = pick_list_service.create_from_invoice(
            invoice_data, org_id, worker_id=worker_id
        )

        # Verify worker task was created
        task = (
            db_session.query(WorkerTask)
            .filter(
                WorkerTask.organization_id == org_id,
                WorkerTask.reference_id == result.id,
                WorkerTask.task_type == "pick",
            )
            .first()
        )
        assert task is not None
        assert task.worker_id == worker_id
        assert task.status == "assigned"
        assert task.reference_id == result.id

    def test_no_worker_task_when_worker_id_not_provided(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """create_from_invoice should NOT create a worker task when worker_id is None."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item_id = uuid.uuid4()
        _create_item(db_session, item_id, org_id, "SKU-A")

        bin1 = _create_bin_location(
            db_session,
            org_id,
            warehouse_id,
            "BIN01",
            "Z01-A01-B01-L01-BIN01",
        )
        _create_bin_stock(db_session, org_id, bin1.id, item_id, 100)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-WIRE-004",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id, sku="SKU-A", quantity=Decimal("10"), uom="Nos"
                ),
            ],
        )

        result = pick_list_service.create_from_invoice(invoice_data, org_id)

        # Verify no worker task was created
        task_count = (
            db_session.query(WorkerTask)
            .filter(
                WorkerTask.organization_id == org_id,
                WorkerTask.reference_id == result.id,
            )
            .count()
        )
        assert task_count == 0

    def test_items_have_bin_location_id_and_sort_order_set(
        self, db_session, pick_list_service, org_id, warehouse_id, worker_id
    ):
        """Pick list items should have bin_location_id and sort_order properly set."""
        _create_warehouse(db_session, warehouse_id, org_id)

        item1_id = uuid.uuid4()
        item2_id = uuid.uuid4()
        _create_item(db_session, item1_id, org_id, "SKU-X")
        _create_item(db_session, item2_id, org_id, "SKU-Y")

        bin1 = _create_bin_location(
            db_session,
            org_id,
            warehouse_id,
            "BIN01",
            "Z01-A01-B01-L01-BIN01",
            position_x=3,
            position_y=3,
        )
        bin2 = _create_bin_location(
            db_session,
            org_id,
            warehouse_id,
            "BIN02",
            "Z01-A02-B01-L01-BIN02",
            position_x=8,
            position_y=8,
        )

        _create_bin_stock(db_session, org_id, bin1.id, item1_id, 50)
        _create_bin_stock(db_session, org_id, bin2.id, item2_id, 50)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-WIRE-005",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item1_id, sku="SKU-X", quantity=Decimal("10"), uom="Nos"
                ),
                SAPInvoiceItem(
                    item_id=item2_id, sku="SKU-Y", quantity=Decimal("15"), uom="Nos"
                ),
            ],
        )

        result = pick_list_service.create_from_invoice(
            invoice_data, org_id, worker_id=worker_id
        )

        # All items should have bin_location_id set
        for item in result.items:
            assert (
                item.bin_location_id is not None
            ), f"Item {item.item_id} should have bin_location_id set"
            assert (
                item.sort_order > 0
            ), f"Item {item.item_id} should have sort_order > 0"

        # Verify bin assignments are correct
        item_bins = {item.item_id: item.bin_location_id for item in result.items}
        assert item_bins[item1_id] == bin1.id
        assert item_bins[item2_id] == bin2.id
