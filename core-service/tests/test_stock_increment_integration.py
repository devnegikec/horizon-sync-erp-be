"""Unit tests for stock increment integration in Receipt Note service"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.models.base import ItemType, PurchaseOrderStatus, WarehouseType
from app.models.item import Item
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.stock_level import StockLevel
from app.models.supplier import Supplier
from app.models.warehouse import Warehouse
from app.services.receipt_note_service import ReceiptNoteService
from app.services.stock_level_service import StockLevelService


@pytest.fixture
def receipt_note_service(db_session):
    """Create Receipt Note service instance"""
    return ReceiptNoteService(db_session)


@pytest.fixture
def stock_level_service(db_session):
    """Create Stock Level service instance"""
    return StockLevelService(db_session)


@pytest.fixture
def test_organization_id():
    """Test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


@pytest.fixture
def test_supplier_id(db_session, test_organization_id, test_user_id):
    """Create a real supplier and return its ID."""
    supplier = Supplier(
        organization_id=test_organization_id,
        supplier_name="Stock Test Supplier",
        supplier_code="SUP-STOCK-001",
        email="stock-supplier@test.com",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier.id


@pytest.fixture
def test_item_id(db_session, test_organization_id, test_user_id):
    """Create a real item and return its ID."""
    item = Item(
        organization_id=test_organization_id,
        item_code="ITEM-STOCK-001",
        item_name="Stock Integration Item",
        item_type=ItemType.STOCK,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item.id


@pytest.fixture
def test_warehouse_id(db_session, test_organization_id, test_user_id):
    """Create a real warehouse and return its ID."""
    warehouse = Warehouse(
        organization_id=test_organization_id,
        code="WH-STOCK-001",
        name="Stock Test Warehouse",
        warehouse_type=WarehouseType.WAREHOUSE,
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(warehouse)
    db_session.commit()
    db_session.refresh(warehouse)
    return warehouse.id


@pytest.fixture
def submitted_purchase_order(
    db_session, test_organization_id, test_user_id, test_supplier_id, test_item_id
):
    """Create a submitted Purchase Order for testing"""
    po = PurchaseOrder(
        organization_id=test_organization_id,
        party_type="SUPPLIER",
        party_id=test_supplier_id,
        status=PurchaseOrderStatus.SUBMITTED,
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("100.00"),
        tax_rate=Decimal("0.10"),
        discount_amount=Decimal("0.00"),
        grand_total=Decimal("1100.00"),
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(po)
    db_session.commit()
    db_session.refresh(po)

    # Add line items
    line = PurchaseOrderLine(
        organization_id=test_organization_id,
        purchase_order_id=po.id,
        item_id=test_item_id,
        quantity=Decimal("100.00"),
        unit_price=Decimal("10.00"),
        line_total=Decimal("1000.00"),
        received_quantity=Decimal("0.00"),
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(po)

    return po


class TestStockIncrementIntegration:
    """Tests for stock increment integration (Requirement 5.3)"""

    def test_receipt_note_increments_stock_for_new_item(
        self,
        receipt_note_service,
        stock_level_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
        test_warehouse_id,
        test_item_id,
        db_session,
    ):
        """Test that creating Receipt Note increments stock for a new item"""
        # Verify no stock level exists initially
        stock_levels = db_session.query(StockLevel).filter(
            StockLevel.organization_id == test_organization_id,
            StockLevel.product_id == test_item_id,
            StockLevel.warehouse_id == test_warehouse_id,
        ).all()
        assert len(stock_levels) == 0

        # Create Receipt Note
        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": test_item_id,
                "qty": 50.0,
                "uom": "Nos",
            }
        ]

        receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-STOCK-001",
            receipt_date=receipt_date,
            line_items=line_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
            warehouse_id=test_warehouse_id,
        )

        # Verify stock level was created and incremented
        stock_level = stock_level_service.get(
            item_id=test_item_id,
            warehouse_id=test_warehouse_id,
            organization_id=test_organization_id,
        )
        assert stock_level is not None
        assert stock_level.quantity_on_hand == 50

    def test_receipt_note_increments_existing_stock(
        self,
        receipt_note_service,
        stock_level_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
        test_warehouse_id,
        test_item_id,
        db_session,
    ):
        """Test that creating Receipt Note increments existing stock"""
        # Create initial stock level
        initial_stock = StockLevel(
            organization_id=test_organization_id,
            product_id=test_item_id,
            warehouse_id=test_warehouse_id,
            quantity_on_hand=100,
            quantity_reserved=0,
            quantity_available=100,
        )
        db_session.add(initial_stock)
        db_session.commit()

        # Create Receipt Note
        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": test_item_id,
                "qty": 50.0,
                "uom": "Nos",
            }
        ]

        receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-STOCK-002",
            receipt_date=receipt_date,
            line_items=line_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
            warehouse_id=test_warehouse_id,
        )

        # Verify stock level was incremented
        stock_level = stock_level_service.get(
            item_id=test_item_id,
            warehouse_id=test_warehouse_id,
            organization_id=test_organization_id,
        )
        assert stock_level.quantity_on_hand == 150  # 100 + 50

    def test_multiple_receipts_increment_stock_correctly(
        self,
        receipt_note_service,
        stock_level_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
        test_warehouse_id,
        test_item_id,
        db_session,
    ):
        """Test that multiple receipts increment stock correctly"""
        receipt_date = datetime.now()

        # First receipt
        line_items_1 = [
            {
                "item_id": test_item_id,
                "qty": 30.0,
                "uom": "Nos",
            }
        ]
        receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-STOCK-003",
            receipt_date=receipt_date,
            line_items=line_items_1,
            organization_id=test_organization_id,
            user_id=test_user_id,
            warehouse_id=test_warehouse_id,
        )

        # Verify first increment
        stock_level = stock_level_service.get(
            item_id=test_item_id,
            warehouse_id=test_warehouse_id,
            organization_id=test_organization_id,
        )
        assert stock_level.quantity_on_hand == 30

        # Second receipt
        line_items_2 = [
            {
                "item_id": test_item_id,
                "qty": 40.0,
                "uom": "Nos",
            }
        ]
        receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-STOCK-004",
            receipt_date=receipt_date,
            line_items=line_items_2,
            organization_id=test_organization_id,
            user_id=test_user_id,
            warehouse_id=test_warehouse_id,
        )

        # Verify second increment
        db_session.refresh(stock_level)
        stock_level = stock_level_service.get(
            item_id=test_item_id,
            warehouse_id=test_warehouse_id,
            organization_id=test_organization_id,
        )
        assert stock_level.quantity_on_hand == 70  # 30 + 40

    def test_receipt_note_without_warehouse_skips_stock_increment(
        self,
        receipt_note_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
        test_item_id,
        db_session,
    ):
        """Test that Receipt Note without warehouse skips stock increment"""
        # Create Receipt Note without warehouse_id
        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": test_item_id,
                "qty": 50.0,
                "uom": "Nos",
            }
        ]

        receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-STOCK-005",
            receipt_date=receipt_date,
            line_items=line_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
            warehouse_id=None,  # No warehouse
        )

        # Verify no stock level was created
        stock_levels = db_session.query(StockLevel).filter(
            StockLevel.organization_id == test_organization_id,
            StockLevel.product_id == test_item_id,
        ).all()
        assert len(stock_levels) == 0

    def test_receipt_note_with_multiple_items_increments_all(
        self,
        receipt_note_service,
        stock_level_service,
        db_session,
        test_organization_id,
        test_user_id,
        test_supplier_id,
        test_warehouse_id,
    ):
        """Test that Receipt Note with multiple items increments stock for all items"""
        # Create items
        item_1 = Item(
            organization_id=test_organization_id,
            item_code="ITEM-STOCK-002",
            item_name="Stock Integration Item 2",
            item_type=ItemType.STOCK,
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        item_2 = Item(
            organization_id=test_organization_id,
            item_code="ITEM-STOCK-003",
            item_name="Stock Integration Item 3",
            item_type=ItemType.STOCK,
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add_all([item_1, item_2])
        db_session.commit()
        db_session.refresh(item_1)
        db_session.refresh(item_2)

        # Create Purchase Order with multiple items
        po = PurchaseOrder(
            organization_id=test_organization_id,
            party_type="SUPPLIER",
            party_id=test_supplier_id,
            status=PurchaseOrderStatus.SUBMITTED,
            subtotal=Decimal("2000.00"),
            tax_amount=Decimal("200.00"),
            grand_total=Decimal("2200.00"),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(po)
        db_session.commit()

        # Add line items
        line1 = PurchaseOrderLine(
            organization_id=test_organization_id,
            purchase_order_id=po.id,
            item_id=item_1.id,
            quantity=Decimal("100.00"),
            unit_price=Decimal("10.00"),
            line_total=Decimal("1000.00"),
            received_quantity=Decimal("0.00"),
        )
        line2 = PurchaseOrderLine(
            organization_id=test_organization_id,
            purchase_order_id=po.id,
            item_id=item_2.id,
            quantity=Decimal("50.00"),
            unit_price=Decimal("20.00"),
            line_total=Decimal("1000.00"),
            received_quantity=Decimal("0.00"),
        )
        db_session.add_all([line1, line2])
        db_session.commit()

        # Create Receipt Note with both items
        receipt_date = datetime.now()
        line_items = [
            {"item_id": item_1.id, "qty": 60.0, "uom": "Nos"},
            {"item_id": item_2.id, "qty": 30.0, "uom": "Nos"},
        ]

        receipt_note_service.create_receipt_note(
            purchase_order_id=po.id,
            receipt_no="RN-STOCK-006",
            receipt_date=receipt_date,
            line_items=line_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
            warehouse_id=test_warehouse_id,
        )

        # Verify stock levels for both items
        stock_level_1 = stock_level_service.get(
            item_id=item_1.id,
            warehouse_id=test_warehouse_id,
            organization_id=test_organization_id,
        )
        assert stock_level_1.quantity_on_hand == 60

        stock_level_2 = stock_level_service.get(
            item_id=item_2.id,
            warehouse_id=test_warehouse_id,
            organization_id=test_organization_id,
        )
        assert stock_level_2.quantity_on_hand == 30
