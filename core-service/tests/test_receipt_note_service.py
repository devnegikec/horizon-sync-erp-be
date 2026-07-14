"""Unit tests for Receipt Note service"""

import uuid
from datetime import datetime
from decimal import Decimal

import pytest

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.models.base import PurchaseOrderStatus
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.services.receipt_note_service import ReceiptNoteService


@pytest.fixture
def receipt_note_service(db_session):
    """Create Receipt Note service instance"""
    return ReceiptNoteService(db_session)


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
def test_item_id():
    """Test item ID"""
    return uuid.uuid4()


@pytest.fixture
def test_warehouse_id():
    """Test warehouse ID"""
    return uuid.uuid4()


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


@pytest.fixture
def partially_received_purchase_order(
    db_session, test_organization_id, test_user_id, test_supplier_id, test_item_id
):
    """Create a partially received Purchase Order for testing"""
    po = PurchaseOrder(
        organization_id=test_organization_id,
        party_type="SUPPLIER",
        party_id=test_supplier_id,
        status=PurchaseOrderStatus.PARTIALLY_RECEIVED,
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

    # Add line items with partial receipt
    line = PurchaseOrderLine(
        organization_id=test_organization_id,
        purchase_order_id=po.id,
        item_id=test_item_id,
        quantity=Decimal("100.00"),
        unit_price=Decimal("10.00"),
        line_total=Decimal("1000.00"),
        received_quantity=Decimal("50.00"),
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(po)

    return po


class TestCreateReceiptNote:
    """Tests for create_receipt_note method"""

    def test_create_receipt_note_for_submitted_purchase_order(
        self,
        receipt_note_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
        test_warehouse_id,
    ):
        """Test creating Receipt Note for a submitted Purchase Order"""
        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": submitted_purchase_order.line_items[0].item_id,
                "qty": 50.0,
                "uom": "Nos",
            }
        ]

        result = receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-001",
            receipt_date=receipt_date,
            line_items=line_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
            warehouse_id=test_warehouse_id,
            remarks="Test receipt",
        )

        # Verify Receipt Note was created
        assert result["id"] is not None
        assert result["purchase_receipt_no"] == "RN-001"
        assert result["supplier_id"] == submitted_purchase_order.party_id
        assert result["reference_type"] == "PURCHASE_ORDER"
        assert result["reference_id"] == submitted_purchase_order.id
        assert result["warehouse_id"] == test_warehouse_id
        assert result["remarks"] == "Test receipt"

    def test_create_receipt_note_for_partially_received_purchase_order(
        self,
        receipt_note_service,
        partially_received_purchase_order,
        test_organization_id,
        test_user_id,
    ):
        """Test creating Receipt Note for a partially received Purchase Order"""
        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": partially_received_purchase_order.line_items[0].item_id,
                "qty": 30.0,
                "uom": "Nos",
            }
        ]

        result = receipt_note_service.create_receipt_note(
            purchase_order_id=partially_received_purchase_order.id,
            receipt_no="RN-002",
            receipt_date=receipt_date,
            line_items=line_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify Receipt Note was created
        assert result["id"] is not None
        assert result["reference_type"] == "PURCHASE_ORDER"
        assert result["reference_id"] == partially_received_purchase_order.id

    def test_create_receipt_note_for_nonexistent_purchase_order(
        self,
        receipt_note_service,
        test_organization_id,
        test_user_id,
    ):
        """Test creating Receipt Note for non-existent Purchase Order"""
        non_existent_id = uuid.uuid4()
        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": uuid.uuid4(),
                "qty": 50.0,
                "uom": "Nos",
            }
        ]

        with pytest.raises(ResourceNotFoundException) as exc_info:
            receipt_note_service.create_receipt_note(
                purchase_order_id=non_existent_id,
                receipt_no="RN-003",
                receipt_date=receipt_date,
                line_items=line_items,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert str(non_existent_id) in str(exc_info.value)

    def test_create_receipt_note_for_draft_purchase_order(
        self,
        receipt_note_service,
        db_session,
        test_organization_id,
        test_user_id,
        test_supplier_id,
        test_item_id,
    ):
        """Test creating Receipt Note for DRAFT Purchase Order should fail"""
        # Create DRAFT Purchase Order
        po = PurchaseOrder(
            organization_id=test_organization_id,
            party_type="SUPPLIER",
            party_id=test_supplier_id,
            status=PurchaseOrderStatus.DRAFT,
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("100.00"),
            grand_total=Decimal("1100.00"),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(po)
        db_session.commit()

        # Add line item
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

        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": test_item_id,
                "qty": 50.0,
                "uom": "Nos",
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            receipt_note_service.create_receipt_note(
                purchase_order_id=po.id,
                receipt_no="RN-004",
                receipt_date=receipt_date,
                line_items=line_items,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "SUBMITTED" in str(exc_info.value) or "PARTIALLY_RECEIVED" in str(
            exc_info.value
        )

    def test_create_receipt_note_for_cancelled_purchase_order(
        self,
        receipt_note_service,
        db_session,
        test_organization_id,
        test_user_id,
        test_supplier_id,
        test_item_id,
    ):
        """Test creating Receipt Note for CANCELLED Purchase Order should fail"""
        # Create CANCELLED Purchase Order
        po = PurchaseOrder(
            organization_id=test_organization_id,
            party_type="SUPPLIER",
            party_id=test_supplier_id,
            status=PurchaseOrderStatus.CANCELLED,
            subtotal=Decimal("1000.00"),
            tax_amount=Decimal("100.00"),
            grand_total=Decimal("1100.00"),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(po)
        db_session.commit()

        # Add line item
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

        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": test_item_id,
                "qty": 50.0,
                "uom": "Nos",
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            receipt_note_service.create_receipt_note(
                purchase_order_id=po.id,
                receipt_no="RN-005",
                receipt_date=receipt_date,
                line_items=line_items,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "SUBMITTED" in str(exc_info.value) or "PARTIALLY_RECEIVED" in str(
            exc_info.value
        )

    def test_create_receipt_note_without_line_items(
        self,
        receipt_note_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
    ):
        """Test creating Receipt Note without line items should fail"""
        receipt_date = datetime.now()

        with pytest.raises(ValidationException) as exc_info:
            receipt_note_service.create_receipt_note(
                purchase_order_id=submitted_purchase_order.id,
                receipt_no="RN-006",
                receipt_date=receipt_date,
                line_items=[],
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "line item" in str(exc_info.value).lower()

    def test_create_receipt_note_with_zero_quantity(
        self,
        receipt_note_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
    ):
        """Test creating Receipt Note with zero quantity should fail"""
        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": submitted_purchase_order.line_items[0].item_id,
                "qty": 0.0,
                "uom": "Nos",
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            receipt_note_service.create_receipt_note(
                purchase_order_id=submitted_purchase_order.id,
                receipt_no="RN-007",
                receipt_date=receipt_date,
                line_items=line_items,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "quantity" in str(exc_info.value).lower()

    def test_create_receipt_note_with_item_not_in_purchase_order(
        self,
        receipt_note_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
    ):
        """Test creating Receipt Note with item not in Purchase Order should fail"""
        receipt_date = datetime.now()
        invalid_item_id = uuid.uuid4()
        line_items = [
            {
                "item_id": invalid_item_id,
                "qty": 50.0,
                "uom": "Nos",
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            receipt_note_service.create_receipt_note(
                purchase_order_id=submitted_purchase_order.id,
                receipt_no="RN-008",
                receipt_date=receipt_date,
                line_items=line_items,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "not found in Purchase Order" in str(exc_info.value)

    def test_create_receipt_note_exceeding_ordered_quantity(
        self,
        receipt_note_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
    ):
        """Test creating Receipt Note with quantity exceeding ordered quantity should fail"""
        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": submitted_purchase_order.line_items[0].item_id,
                "qty": 150.0,  # Ordered quantity is 100
                "uom": "Nos",
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            receipt_note_service.create_receipt_note(
                purchase_order_id=submitted_purchase_order.id,
                receipt_no="RN-009",
                receipt_date=receipt_date,
                line_items=line_items,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "exceeds remaining quantity" in str(exc_info.value)

    def test_create_receipt_note_exceeding_remaining_quantity(
        self,
        receipt_note_service,
        partially_received_purchase_order,
        test_organization_id,
        test_user_id,
    ):
        """Test creating Receipt Note exceeding remaining quantity should fail"""
        receipt_date = datetime.now()
        # Ordered: 100, Already received: 50, Remaining: 50
        line_items = [
            {
                "item_id": partially_received_purchase_order.line_items[0].item_id,
                "qty": 60.0,  # Exceeds remaining 50
                "uom": "Nos",
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            receipt_note_service.create_receipt_note(
                purchase_order_id=partially_received_purchase_order.id,
                receipt_no="RN-010",
                receipt_date=receipt_date,
                line_items=line_items,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "exceeds remaining quantity" in str(exc_info.value)


class TestReceiptNoteStatusUpdate:
    """Tests for Purchase Order status update when creating Receipt Notes"""

    def test_receipt_note_updates_po_to_partially_received(
        self,
        receipt_note_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
        db_session,
    ):
        """Test creating Receipt Note updates PO status to PARTIALLY_RECEIVED"""
        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": submitted_purchase_order.line_items[0].item_id,
                "qty": 50.0,
                "uom": "Nos",
            }
        ]

        receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-STATUS-001",
            receipt_date=receipt_date,
            line_items=line_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Refresh PO and verify status
        db_session.refresh(submitted_purchase_order)
        assert submitted_purchase_order.status == PurchaseOrderStatus.PARTIALLY_RECEIVED
        assert submitted_purchase_order.line_items[0].received_quantity == Decimal(
            "50.00"
        )

    def test_receipt_note_updates_po_to_fully_received(
        self,
        receipt_note_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
        db_session,
    ):
        """Test creating Receipt Note updates PO status to FULLY_RECEIVED"""
        receipt_date = datetime.now()
        line_items = [
            {
                "item_id": submitted_purchase_order.line_items[0].item_id,
                "qty": 100.0,
                "uom": "Nos",
            }
        ]

        receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-STATUS-002",
            receipt_date=receipt_date,
            line_items=line_items,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Refresh PO and verify status
        db_session.refresh(submitted_purchase_order)
        assert submitted_purchase_order.status == PurchaseOrderStatus.FULLY_RECEIVED
        assert submitted_purchase_order.line_items[0].received_quantity == Decimal(
            "100.00"
        )

    def test_multiple_receipts_update_po_status_correctly(
        self,
        receipt_note_service,
        submitted_purchase_order,
        test_organization_id,
        test_user_id,
        db_session,
    ):
        """Test multiple receipts update PO status correctly"""
        receipt_date = datetime.now()

        # First receipt - partial
        line_items_1 = [
            {
                "item_id": submitted_purchase_order.line_items[0].item_id,
                "qty": 30.0,
                "uom": "Nos",
            }
        ]
        receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-STATUS-003",
            receipt_date=receipt_date,
            line_items=line_items_1,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        db_session.refresh(submitted_purchase_order)
        assert submitted_purchase_order.status == PurchaseOrderStatus.PARTIALLY_RECEIVED
        assert submitted_purchase_order.line_items[0].received_quantity == Decimal(
            "30.00"
        )

        # Second receipt - still partial
        line_items_2 = [
            {
                "item_id": submitted_purchase_order.line_items[0].item_id,
                "qty": 40.0,
                "uom": "Nos",
            }
        ]
        receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-STATUS-004",
            receipt_date=receipt_date,
            line_items=line_items_2,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        db_session.refresh(submitted_purchase_order)
        assert submitted_purchase_order.status == PurchaseOrderStatus.PARTIALLY_RECEIVED
        assert submitted_purchase_order.line_items[0].received_quantity == Decimal(
            "70.00"
        )

        # Third receipt - fully received
        line_items_3 = [
            {
                "item_id": submitted_purchase_order.line_items[0].item_id,
                "qty": 30.0,
                "uom": "Nos",
            }
        ]
        receipt_note_service.create_receipt_note(
            purchase_order_id=submitted_purchase_order.id,
            receipt_no="RN-STATUS-005",
            receipt_date=receipt_date,
            line_items=line_items_3,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )
        db_session.refresh(submitted_purchase_order)
        assert submitted_purchase_order.status == PurchaseOrderStatus.FULLY_RECEIVED
        assert submitted_purchase_order.line_items[0].received_quantity == Decimal(
            "100.00"
        )
