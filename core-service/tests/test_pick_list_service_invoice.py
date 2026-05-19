"""Unit tests for PickListService SAP invoice-triggered workflow.

Tests create_from_invoice and resolve_bin_locations methods.
Requirements: 9.1, 9.2, 9.3, 9.4, 9.5
"""

import uuid
from decimal import Decimal

import pytest

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.base import PickListStatus
from app.models.bin_stock_level import BinStockLevel
from app.models.pick_list import PickList, PickListItem
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


class TestCreateFromInvoice:
    """Tests for create_from_invoice method."""

    def test_creates_pick_list_from_invoice(
        self, db_session, pick_list_service, org_id, warehouse_id, item_id
    ):
        """Should create a pick list with DRAFT status from SAP invoice data."""
        _create_warehouse(db_session, warehouse_id, org_id)
        _create_item(db_session, item_id, org_id)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-2025-001",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id,
                    sku="ITEM-001",
                    quantity=Decimal("50"),
                    uom="Nos",
                )
            ],
        )

        result = pick_list_service.create_from_invoice(invoice_data, org_id)

        assert result is not None
        assert result.status == PickListStatus.DRAFT
        assert result.warehouse_id == warehouse_id
        assert result.invoice_reference == "INV-2025-001"
        assert result.reference_type == "sap_invoice"
        assert result.organization_id == org_id
        assert result.pick_list_no is not None

    def test_populates_items_from_invoice_lines(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """Should create pick list items matching invoice line items."""
        _create_warehouse(db_session, warehouse_id, org_id)
        item1_id = uuid.uuid4()
        item2_id = uuid.uuid4()
        _create_item(db_session, item1_id, org_id, "SKU-A")
        _create_item(db_session, item2_id, org_id, "SKU-B")
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-2025-002",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item1_id, sku="SKU-A", quantity=Decimal("30"), uom="Nos"
                ),
                SAPInvoiceItem(
                    item_id=item2_id, sku="SKU-B", quantity=Decimal("20"), uom="Boxes"
                ),
            ],
        )

        result = pick_list_service.create_from_invoice(invoice_data, org_id)

        assert len(result.items) == 2
        items_by_id = {item.item_id: item for item in result.items}
        assert items_by_id[item1_id].qty == Decimal("30")
        assert items_by_id[item1_id].uom == "Nos"
        assert items_by_id[item2_id].qty == Decimal("20")
        assert items_by_id[item2_id].uom == "Boxes"

    def test_stores_invoice_data_as_json(
        self, db_session, pick_list_service, org_id, warehouse_id, item_id
    ):
        """Should store the full invoice payload as JSON in invoice_data column."""
        _create_warehouse(db_session, warehouse_id, org_id)
        _create_item(db_session, item_id, org_id)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-2025-003",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id, sku="ITEM-001", quantity=Decimal("10"), uom="Nos"
                )
            ],
        )

        result = pick_list_service.create_from_invoice(invoice_data, org_id)

        assert result.invoice_data is not None
        assert result.invoice_data["invoice_reference"] == "INV-2025-003"
        assert len(result.invoice_data["items"]) == 1

    def test_rejects_empty_items(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """Should raise ValidationError when invoice has no items."""
        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-2025-004",
            warehouse_id=warehouse_id,
            items=[],
        )

        with pytest.raises(ValidationError, match="at least one line item"):
            pick_list_service.create_from_invoice(invoice_data, org_id)

    def test_rejects_missing_invoice_reference(
        self, db_session, pick_list_service, org_id, warehouse_id, item_id
    ):
        """Should raise ValidationError when invoice reference is empty."""
        invoice_data = SAPInvoicePayload(
            invoice_reference="",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id, sku="ITEM-001", quantity=Decimal("10"), uom="Nos"
                )
            ],
        )

        with pytest.raises(ValidationError, match="Invoice reference is required"):
            pick_list_service.create_from_invoice(invoice_data, org_id)

    def test_sets_warehouse_from_invoice(
        self, db_session, pick_list_service, org_id, item_id
    ):
        """Should set pick list warehouse from invoice data (Req 9.5)."""
        wh_id = uuid.uuid4()
        _create_warehouse(db_session, wh_id, org_id)
        _create_item(db_session, item_id, org_id)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-2025-005",
            warehouse_id=wh_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id, sku="ITEM-001", quantity=Decimal("5"), uom="Nos"
                )
            ],
        )

        result = pick_list_service.create_from_invoice(invoice_data, org_id)

        assert result.warehouse_id == wh_id


class TestResolveBinLocations:
    """Tests for resolve_bin_locations method."""

    def test_resolves_single_bin_fifo(
        self, db_session, pick_list_service, org_id, warehouse_id, item_id
    ):
        """Should assign bin location from oldest stock (FIFO)."""
        _create_warehouse(db_session, warehouse_id, org_id)
        _create_item(db_session, item_id, org_id)

        bin1 = _create_bin_location(
            db_session, org_id, warehouse_id, "BIN01", "Z01-A01-B01-L01-BIN01"
        )
        _create_bin_stock(db_session, org_id, bin1.id, item_id, 100)
        db_session.commit()

        # Create a pick list with one item
        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-FIFO-001",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id, sku="ITEM-001", quantity=Decimal("30"), uom="Nos"
                )
            ],
        )
        pick_list = pick_list_service.create_from_invoice(invoice_data, org_id)

        # Resolve bin locations
        result = pick_list_service.resolve_bin_locations(pick_list.id, org_id)

        assert len(result.items) == 1
        assert result.items[0].bin_location_id == bin1.id

    def test_splits_across_bins_when_needed(
        self, db_session, pick_list_service, org_id, warehouse_id, item_id
    ):
        """Should split item across multiple bins when single bin has insufficient stock."""
        _create_warehouse(db_session, warehouse_id, org_id)
        _create_item(db_session, item_id, org_id)

        bin1 = _create_bin_location(
            db_session, org_id, warehouse_id, "BIN01", "Z01-A01-B01-L01-BIN01",
            position_x=1, position_y=1,
        )
        bin2 = _create_bin_location(
            db_session, org_id, warehouse_id, "BIN02", "Z01-A01-B01-L01-BIN02",
            position_x=2, position_y=2,
        )

        # Bin1 has 20, Bin2 has 30 — need 40 total
        _create_bin_stock(db_session, org_id, bin1.id, item_id, 20)
        _create_bin_stock(db_session, org_id, bin2.id, item_id, 30)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-SPLIT-001",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id, sku="ITEM-001", quantity=Decimal("40"), uom="Nos"
                )
            ],
        )
        pick_list = pick_list_service.create_from_invoice(invoice_data, org_id)

        result = pick_list_service.resolve_bin_locations(pick_list.id, org_id)

        # Should have 2 items (split across bins)
        assert len(result.items) == 2
        quantities = sorted([item.qty for item in result.items])
        assert quantities == [Decimal("20"), Decimal("20")]

    def test_fifo_order_oldest_first(
        self, db_session, pick_list_service, org_id, warehouse_id, item_id
    ):
        """Should allocate from oldest bin stock first (FIFO)."""
        import time

        _create_warehouse(db_session, warehouse_id, org_id)
        _create_item(db_session, item_id, org_id)

        bin1 = _create_bin_location(
            db_session, org_id, warehouse_id, "BIN01", "Z01-A01-B01-L01-BIN01"
        )
        bin2 = _create_bin_location(
            db_session, org_id, warehouse_id, "BIN02", "Z01-A02-B01-L01-BIN02"
        )

        # Create bin1 stock first (older), then bin2 stock (newer)
        bsl1 = _create_bin_stock(db_session, org_id, bin1.id, item_id, 50)
        # Manually set created_at to ensure ordering
        from datetime import UTC, datetime, timedelta

        bsl1.created_at = datetime.now(UTC) - timedelta(days=10)
        db_session.flush()

        bsl2 = _create_bin_stock(db_session, org_id, bin2.id, item_id, 50)
        bsl2.created_at = datetime.now(UTC)
        db_session.flush()
        db_session.commit()

        # Request 30 — should come from bin1 (oldest)
        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-FIFO-002",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id, sku="ITEM-001", quantity=Decimal("30"), uom="Nos"
                )
            ],
        )
        pick_list = pick_list_service.create_from_invoice(invoice_data, org_id)

        result = pick_list_service.resolve_bin_locations(pick_list.id, org_id)

        assert len(result.items) == 1
        assert result.items[0].bin_location_id == bin1.id

    def test_applies_routing_optimization(
        self, db_session, pick_list_service, org_id, warehouse_id
    ):
        """Should assign sort_order via RoutingOptimizer after bin resolution."""
        _create_warehouse(db_session, warehouse_id, org_id)

        item1_id = uuid.uuid4()
        item2_id = uuid.uuid4()
        _create_item(db_session, item1_id, org_id, "SKU-A")
        _create_item(db_session, item2_id, org_id, "SKU-B")

        # Create bins at different positions
        bin1 = _create_bin_location(
            db_session, org_id, warehouse_id, "BIN01", "Z01-A01-B01-L01-BIN01",
            position_x=10, position_y=10,
        )
        bin2 = _create_bin_location(
            db_session, org_id, warehouse_id, "BIN02", "Z01-A01-B01-L01-BIN02",
            position_x=1, position_y=1,
        )

        _create_bin_stock(db_session, org_id, bin1.id, item1_id, 100)
        _create_bin_stock(db_session, org_id, bin2.id, item2_id, 100)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-ROUTE-001",
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
        pick_list = pick_list_service.create_from_invoice(invoice_data, org_id)

        result = pick_list_service.resolve_bin_locations(pick_list.id, org_id)

        # Both items should have sort_order assigned (non-zero for at least one)
        sort_orders = [item.sort_order for item in result.items]
        assert all(so > 0 for so in sort_orders)
        # Sort orders should be unique sequential integers
        assert sorted(sort_orders) == [1, 2]

    def test_handles_no_stock_available(
        self, db_session, pick_list_service, org_id, warehouse_id, item_id
    ):
        """Should keep item without bin assignment when no stock is available."""
        _create_warehouse(db_session, warehouse_id, org_id)
        _create_item(db_session, item_id, org_id)
        db_session.commit()

        invoice_data = SAPInvoicePayload(
            invoice_reference="INV-NOSTOCK-001",
            warehouse_id=warehouse_id,
            items=[
                SAPInvoiceItem(
                    item_id=item_id, sku="ITEM-001", quantity=Decimal("10"), uom="Nos"
                )
            ],
        )
        pick_list = pick_list_service.create_from_invoice(invoice_data, org_id)

        result = pick_list_service.resolve_bin_locations(pick_list.id, org_id)

        assert len(result.items) == 1
        assert result.items[0].bin_location_id is None

    def test_raises_not_found_for_invalid_pick_list(
        self, db_session, pick_list_service, org_id
    ):
        """Should raise ResourceNotFoundException for non-existent pick list."""
        with pytest.raises(ResourceNotFoundException):
            pick_list_service.resolve_bin_locations(uuid.uuid4(), org_id)
