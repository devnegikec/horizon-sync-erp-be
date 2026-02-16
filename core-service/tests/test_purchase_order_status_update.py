"""Unit tests for Purchase Order status update logic"""

import uuid
from decimal import Decimal

import pytest

from app.models.base import PurchaseOrderStatus
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.services.purchase_order_service import PurchaseOrderService


@pytest.fixture
def purchase_order_service(db_session):
    """Create Purchase Order service instance"""
    return PurchaseOrderService(db_session)


@pytest.fixture
def test_organization_id():
    """Test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


@pytest.fixture
def test_supplier_id():
    """Test supplier ID"""
    return uuid.uuid4()


@pytest.fixture
def test_item_id_1():
    """Test item ID 1"""
    return uuid.uuid4()


@pytest.fixture
def test_item_id_2():
    """Test item ID 2"""
    return uuid.uuid4()


@pytest.fixture
def submitted_purchase_order_single_item(
    db_session, test_organization_id, test_user_id, test_supplier_id, test_item_id_1
):
    """Create a submitted Purchase Order with single line item"""
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

    # Add line item
    line = PurchaseOrderLine(
        organization_id=test_organization_id,
        purchase_order_id=po.id,
        item_id=test_item_id_1,
        quantity=Decimal("100.00"),
        unit_price=Decimal("10.00"),
        line_total=Decimal("1000.00"),
        received_quantity=Decimal("0.00"),
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(po)

    return po


@pytest.fixture
def submitted_purchase_order_multiple_items(
    db_session,
    test_organization_id,
    test_user_id,
    test_supplier_id,
    test_item_id_1,
    test_item_id_2,
):
    """Create a submitted Purchase Order with multiple line items"""
    po = PurchaseOrder(
        organization_id=test_organization_id,
        party_type="SUPPLIER",
        party_id=test_supplier_id,
        status=PurchaseOrderStatus.SUBMITTED,
        subtotal=Decimal("3000.00"),
        tax_amount=Decimal("300.00"),
        tax_rate=Decimal("0.10"),
        discount_amount=Decimal("0.00"),
        grand_total=Decimal("3300.00"),
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(po)
    db_session.commit()
    db_session.refresh(po)

    # Add line items
    line1 = PurchaseOrderLine(
        organization_id=test_organization_id,
        purchase_order_id=po.id,
        item_id=test_item_id_1,
        quantity=Decimal("100.00"),
        unit_price=Decimal("10.00"),
        line_total=Decimal("1000.00"),
        received_quantity=Decimal("0.00"),
    )
    line2 = PurchaseOrderLine(
        organization_id=test_organization_id,
        purchase_order_id=po.id,
        item_id=test_item_id_2,
        quantity=Decimal("200.00"),
        unit_price=Decimal("10.00"),
        line_total=Decimal("2000.00"),
        received_quantity=Decimal("0.00"),
    )
    db_session.add(line1)
    db_session.add(line2)
    db_session.commit()
    db_session.refresh(po)

    return po


class TestUpdateReceivedQuantities:
    """Tests for update_received_quantities method"""

    def test_partial_receipt_single_item(
        self,
        purchase_order_service,
        submitted_purchase_order_single_item,
        test_organization_id,
        test_user_id,
        test_item_id_1,
    ):
        """Test partial receipt updates status to PARTIALLY_RECEIVED"""
        received_items = [
            {"item_id": test_item_id_1, "qty": 50.0}
        ]

        result = purchase_order_service.update_received_quantities(
            po_id=submitted_purchase_order_single_item.id,
            received_items=received_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify status updated to PARTIALLY_RECEIVED
        assert result["status"] == PurchaseOrderStatus.PARTIALLY_RECEIVED.value
        
        # Verify received quantity updated
        assert result["line_items"][0]["received_quantity"] == Decimal("50.00")
        assert result["line_items"][0]["quantity"] == Decimal("100.00")

    def test_full_receipt_single_item(
        self,
        purchase_order_service,
        submitted_purchase_order_single_item,
        test_organization_id,
        test_user_id,
        test_item_id_1,
    ):
        """Test full receipt updates status to FULLY_RECEIVED"""
        received_items = [
            {"item_id": test_item_id_1, "qty": 100.0}
        ]

        result = purchase_order_service.update_received_quantities(
            po_id=submitted_purchase_order_single_item.id,
            received_items=received_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify status updated to FULLY_RECEIVED
        assert result["status"] == PurchaseOrderStatus.FULLY_RECEIVED.value
        
        # Verify received quantity updated
        assert result["line_items"][0]["received_quantity"] == Decimal("100.00")
        assert result["line_items"][0]["quantity"] == Decimal("100.00")

    def test_multiple_partial_receipts_single_item(
        self,
        purchase_order_service,
        submitted_purchase_order_single_item,
        test_organization_id,
        test_user_id,
        test_item_id_1,
    ):
        """Test multiple partial receipts accumulate correctly"""
        # First receipt
        received_items_1 = [
            {"item_id": test_item_id_1, "qty": 30.0}
        ]
        result1 = purchase_order_service.update_received_quantities(
            po_id=submitted_purchase_order_single_item.id,
            received_items=received_items_1,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        assert result1["status"] == PurchaseOrderStatus.PARTIALLY_RECEIVED.value
        assert result1["line_items"][0]["received_quantity"] == Decimal("30.00")

        # Second receipt
        received_items_2 = [
            {"item_id": test_item_id_1, "qty": 40.0}
        ]
        result2 = purchase_order_service.update_received_quantities(
            po_id=submitted_purchase_order_single_item.id,
            received_items=received_items_2,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        assert result2["status"] == PurchaseOrderStatus.PARTIALLY_RECEIVED.value
        assert result2["line_items"][0]["received_quantity"] == Decimal("70.00")

        # Third receipt completes the order
        received_items_3 = [
            {"item_id": test_item_id_1, "qty": 30.0}
        ]
        result3 = purchase_order_service.update_received_quantities(
            po_id=submitted_purchase_order_single_item.id,
            received_items=received_items_3,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        assert result3["status"] == PurchaseOrderStatus.FULLY_RECEIVED.value
        assert result3["line_items"][0]["received_quantity"] == Decimal("100.00")

    def test_partial_receipt_multiple_items_one_item_received(
        self,
        purchase_order_service,
        submitted_purchase_order_multiple_items,
        test_organization_id,
        test_user_id,
        test_item_id_1,
    ):
        """Test receiving only one item from multiple items"""
        received_items = [
            {"item_id": test_item_id_1, "qty": 50.0}
        ]

        result = purchase_order_service.update_received_quantities(
            po_id=submitted_purchase_order_multiple_items.id,
            received_items=received_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify status updated to PARTIALLY_RECEIVED
        assert result["status"] == PurchaseOrderStatus.PARTIALLY_RECEIVED.value
        
        # Verify only first item received
        assert result["line_items"][0]["received_quantity"] == Decimal("50.00")
        assert result["line_items"][1]["received_quantity"] == Decimal("0.00")

    def test_partial_receipt_multiple_items_both_partial(
        self,
        purchase_order_service,
        submitted_purchase_order_multiple_items,
        test_organization_id,
        test_user_id,
        test_item_id_1,
        test_item_id_2,
    ):
        """Test receiving partial quantities of multiple items"""
        received_items = [
            {"item_id": test_item_id_1, "qty": 50.0},
            {"item_id": test_item_id_2, "qty": 100.0},
        ]

        result = purchase_order_service.update_received_quantities(
            po_id=submitted_purchase_order_multiple_items.id,
            received_items=received_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify status updated to PARTIALLY_RECEIVED
        assert result["status"] == PurchaseOrderStatus.PARTIALLY_RECEIVED.value
        
        # Verify both items partially received
        assert result["line_items"][0]["received_quantity"] == Decimal("50.00")
        assert result["line_items"][1]["received_quantity"] == Decimal("100.00")

    def test_full_receipt_multiple_items_one_complete(
        self,
        purchase_order_service,
        submitted_purchase_order_multiple_items,
        test_organization_id,
        test_user_id,
        test_item_id_1,
    ):
        """Test receiving full quantity of one item when multiple items exist"""
        received_items = [
            {"item_id": test_item_id_1, "qty": 100.0}
        ]

        result = purchase_order_service.update_received_quantities(
            po_id=submitted_purchase_order_multiple_items.id,
            received_items=received_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify status is PARTIALLY_RECEIVED (not all items complete)
        assert result["status"] == PurchaseOrderStatus.PARTIALLY_RECEIVED.value
        
        # Verify first item fully received, second not
        assert result["line_items"][0]["received_quantity"] == Decimal("100.00")
        assert result["line_items"][1]["received_quantity"] == Decimal("0.00")

    def test_full_receipt_multiple_items_all_complete(
        self,
        purchase_order_service,
        submitted_purchase_order_multiple_items,
        test_organization_id,
        test_user_id,
        test_item_id_1,
        test_item_id_2,
    ):
        """Test receiving full quantities of all items"""
        received_items = [
            {"item_id": test_item_id_1, "qty": 100.0},
            {"item_id": test_item_id_2, "qty": 200.0},
        ]

        result = purchase_order_service.update_received_quantities(
            po_id=submitted_purchase_order_multiple_items.id,
            received_items=received_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify status updated to FULLY_RECEIVED
        assert result["status"] == PurchaseOrderStatus.FULLY_RECEIVED.value
        
        # Verify all items fully received
        assert result["line_items"][0]["received_quantity"] == Decimal("100.00")
        assert result["line_items"][1]["received_quantity"] == Decimal("200.00")

    def test_over_receipt_single_item(
        self,
        purchase_order_service,
        submitted_purchase_order_single_item,
        test_organization_id,
        test_user_id,
        test_item_id_1,
    ):
        """Test over-receiving (receiving more than ordered) marks as FULLY_RECEIVED"""
        received_items = [
            {"item_id": test_item_id_1, "qty": 120.0}  # Ordered 100
        ]

        result = purchase_order_service.update_received_quantities(
            po_id=submitted_purchase_order_single_item.id,
            received_items=received_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify status updated to FULLY_RECEIVED
        assert result["status"] == PurchaseOrderStatus.FULLY_RECEIVED.value
        
        # Verify received quantity is more than ordered
        assert result["line_items"][0]["received_quantity"] == Decimal("120.00")
        assert result["line_items"][0]["quantity"] == Decimal("100.00")


class TestCalculatePOStatus:
    """Tests for _calculate_po_status method"""

    def test_calculate_status_no_items_received(
        self,
        purchase_order_service,
        submitted_purchase_order_single_item,
    ):
        """Test status calculation when no items received"""
        status = purchase_order_service._calculate_po_status(
            submitted_purchase_order_single_item
        )
        
        # Should remain SUBMITTED
        assert status == PurchaseOrderStatus.SUBMITTED

    def test_calculate_status_partial_receipt(
        self,
        purchase_order_service,
        db_session,
        submitted_purchase_order_single_item,
    ):
        """Test status calculation for partial receipt"""
        # Update received quantity
        line = submitted_purchase_order_single_item.line_items[0]
        line.received_quantity = Decimal("50.00")
        db_session.commit()
        db_session.refresh(submitted_purchase_order_single_item)

        status = purchase_order_service._calculate_po_status(
            submitted_purchase_order_single_item
        )
        
        assert status == PurchaseOrderStatus.PARTIALLY_RECEIVED

    def test_calculate_status_full_receipt(
        self,
        purchase_order_service,
        db_session,
        submitted_purchase_order_single_item,
    ):
        """Test status calculation for full receipt"""
        # Update received quantity to match ordered
        line = submitted_purchase_order_single_item.line_items[0]
        line.received_quantity = Decimal("100.00")
        db_session.commit()
        db_session.refresh(submitted_purchase_order_single_item)

        status = purchase_order_service._calculate_po_status(
            submitted_purchase_order_single_item
        )
        
        assert status == PurchaseOrderStatus.FULLY_RECEIVED

    def test_calculate_status_over_receipt(
        self,
        purchase_order_service,
        db_session,
        submitted_purchase_order_single_item,
    ):
        """Test status calculation for over-receipt"""
        # Update received quantity to exceed ordered
        line = submitted_purchase_order_single_item.line_items[0]
        line.received_quantity = Decimal("120.00")
        db_session.commit()
        db_session.refresh(submitted_purchase_order_single_item)

        status = purchase_order_service._calculate_po_status(
            submitted_purchase_order_single_item
        )
        
        assert status == PurchaseOrderStatus.FULLY_RECEIVED
