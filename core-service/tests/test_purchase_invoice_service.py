"""Tests for Purchase Invoice service"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.models.base import PurchaseOrderStatus
from app.models.item import Item
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.supplier import Supplier
from app.services.purchase_invoice_service import PurchaseInvoiceService


@pytest.fixture
def organization_id():
    """Fixture for organization ID"""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Fixture for user ID"""
    return uuid.uuid4()


@pytest.fixture
def supplier(db_session: Session, organization_id: uuid.UUID):
    """Fixture for creating a supplier"""
    supplier = Supplier(
        id=uuid.uuid4(),
        organization_id=organization_id,
        supplier_name="Test Supplier",
        supplier_code="SUP-001",
        email="john@supplier.com",
        phone="1234567890",
        address="123 Supplier St",
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier


@pytest.fixture
def item(db_session: Session, organization_id: uuid.UUID):
    """Fixture for creating an item"""
    item = Item(
        id=uuid.uuid4(),
        organization_id=organization_id,
        item_name="Test Item",
        item_code="ITEM-001",
        description="Test item description",
        uom="PCS",
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


@pytest.fixture
def purchase_order(
    db_session: Session,
    organization_id: uuid.UUID,
    user_id: uuid.UUID,
    supplier: Supplier,
    item: Item,
):
    """Fixture for creating a purchase order"""
    po = PurchaseOrder(
        id=uuid.uuid4(),
        organization_id=organization_id,
        party_type="SUPPLIER",
        party_id=supplier.id,
        status=PurchaseOrderStatus.SUBMITTED,
        subtotal=Decimal("1000.00"),
        tax_amount=Decimal("180.00"),
        tax_rate=Decimal("0.18"),
        discount_amount=Decimal("0.00"),
        grand_total=Decimal("1180.00"),
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(po)
    db_session.commit()

    # Add line item
    line = PurchaseOrderLine(
        id=uuid.uuid4(),
        organization_id=organization_id,
        purchase_order_id=po.id,
        item_id=item.id,
        quantity=Decimal("10.00"),
        unit_price=Decimal("100.00"),
        line_total=Decimal("1000.00"),
        received_quantity=Decimal("0.00"),
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(po)
    return po


class TestPurchaseInvoiceService:
    """Tests for Purchase Invoice service"""

    def test_create_purchase_invoice_success(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test successful creation of Purchase Invoice"""
        service = PurchaseInvoiceService(db_session)

        # Set received quantity to allow invoicing
        purchase_order.line_items[0].received_quantity = Decimal("10.00")
        db_session.commit()

        line_items = [
            {
                "item_id": item.id,
                "quantity": 10,
                "unit_price": 100.00,
            }
        ]

        result = service.create_purchase_invoice(
            purchase_order_id=purchase_order.id,
            line_items=line_items,
            tax_rate=Decimal("0.18"),
            discount_amount=Decimal("0.00"),
            organization_id=organization_id,
            user_id=user_id,
            invoice_no="INV-001",
            posting_date=datetime.now(UTC),
            due_date=None,
            remarks="Test invoice",
        )

        # Verify invoice was created
        assert result["id"] is not None
        assert result["invoice_type"] == "purchase"  # Enum value is lowercase
        assert result["reference_type"] == "PURCHASE_ORDER"
        assert result["reference_id"] == purchase_order.id
        assert result["party_id"] == purchase_order.party_id
        assert result["party_type"] == "SUPPLIER"
        assert result["status"] == "draft"  # Enum value is lowercase
        assert result["grand_total"] == Decimal("1180.00")
        assert result["outstanding_amount"] == Decimal("1180.00")

        # Verify line items
        assert len(result["line_items"]) == 1
        assert result["line_items"][0]["item_id"] == str(item.id)
        assert result["line_items"][0]["quantity"] == 10.0
        assert result["line_items"][0]["unit_price"] == 100.0
        assert result["line_items"][0]["line_total"] == 1000.0

        # Verify calculation details
        assert result["subtotal"] == 1000.0
        assert result["tax_amount"] == 180.0
        assert result["tax_rate"] == 0.18
        assert result["discount_amount"] == 0.0

    def test_create_purchase_invoice_po_not_found(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        item: Item,
    ):
        """Test Purchase Invoice creation fails when Purchase Order not found"""
        service = PurchaseInvoiceService(db_session)

        fake_po_id = uuid.uuid4()
        line_items = [
            {
                "item_id": item.id,
                "quantity": 10,
                "unit_price": 100.00,
            }
        ]

        with pytest.raises(ResourceNotFoundException) as exc_info:
            service.create_purchase_invoice(
                purchase_order_id=fake_po_id,
                line_items=line_items,
                tax_rate=Decimal("0.18"),
                discount_amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                invoice_no="INV-001",
            )

        assert f"Purchase Order {fake_po_id} not found" in str(exc_info.value)

    def test_create_purchase_invoice_invalid_po_status(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test Purchase Invoice creation fails for invalid Purchase Order status"""
        service = PurchaseInvoiceService(db_session)

        # Change PO status to DRAFT (invalid for invoice creation)
        purchase_order.status = PurchaseOrderStatus.DRAFT
        db_session.commit()

        line_items = [
            {
                "item_id": item.id,
                "quantity": 10,
                "unit_price": 100.00,
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            service.create_purchase_invoice(
                purchase_order_id=purchase_order.id,
                line_items=line_items,
                tax_rate=Decimal("0.18"),
                discount_amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                invoice_no="INV-001",
            )

        assert "Cannot create Purchase Invoice" in str(exc_info.value)
        assert "draft" in str(exc_info.value)  # Enum value is lowercase

    def test_create_purchase_invoice_cancelled_po(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test Purchase Invoice creation fails for cancelled Purchase Order"""
        service = PurchaseInvoiceService(db_session)

        # Change PO status to CANCELLED
        purchase_order.status = PurchaseOrderStatus.CANCELLED
        db_session.commit()

        line_items = [
            {
                "item_id": item.id,
                "quantity": 10,
                "unit_price": 100.00,
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            service.create_purchase_invoice(
                purchase_order_id=purchase_order.id,
                line_items=line_items,
                tax_rate=Decimal("0.18"),
                discount_amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                invoice_no="INV-001",
            )

        assert "Cannot create Purchase Invoice" in str(exc_info.value)

    def test_create_purchase_invoice_no_line_items(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
    ):
        """Test Purchase Invoice creation fails without line items"""
        service = PurchaseInvoiceService(db_session)

        with pytest.raises(ValidationException) as exc_info:
            service.create_purchase_invoice(
                purchase_order_id=purchase_order.id,
                line_items=[],
                tax_rate=Decimal("0.18"),
                discount_amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                invoice_no="INV-001",
            )

        assert "At least one line item is required" in str(exc_info.value)

    def test_create_purchase_invoice_zero_quantity(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test Purchase Invoice creation fails with zero quantity"""
        service = PurchaseInvoiceService(db_session)

        line_items = [
            {
                "item_id": item.id,
                "quantity": 0,
                "unit_price": 100.00,
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            service.create_purchase_invoice(
                purchase_order_id=purchase_order.id,
                line_items=line_items,
                tax_rate=Decimal("0.18"),
                discount_amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                invoice_no="INV-001",
            )

        assert "quantity must be greater than zero" in str(exc_info.value)

    def test_create_purchase_invoice_negative_unit_price(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test Purchase Invoice creation fails with negative unit price"""
        service = PurchaseInvoiceService(db_session)

        line_items = [
            {
                "item_id": item.id,
                "quantity": 10,
                "unit_price": -100.00,
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            service.create_purchase_invoice(
                purchase_order_id=purchase_order.id,
                line_items=line_items,
                tax_rate=Decimal("0.18"),
                discount_amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                invoice_no="INV-001",
            )

        assert "unit_price must be non-negative" in str(exc_info.value)

    def test_create_purchase_invoice_with_discount(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test Purchase Invoice creation with discount"""
        service = PurchaseInvoiceService(db_session)

        # Set received quantity to allow invoicing
        purchase_order.line_items[0].received_quantity = Decimal("10.00")
        db_session.commit()

        line_items = [
            {
                "item_id": item.id,
                "quantity": 10,
                "unit_price": 100.00,
            }
        ]

        result = service.create_purchase_invoice(
            purchase_order_id=purchase_order.id,
            line_items=line_items,
            tax_rate=Decimal("0.18"),
            discount_amount=Decimal("50.00"),
            organization_id=organization_id,
            user_id=user_id,
            invoice_no="INV-002",
        )

        # Verify calculations with discount
        # subtotal = 1000, tax = 180, discount = 50
        # grand_total = 1000 + 180 - 50 = 1130
        assert result["subtotal"] == 1000.0
        assert result["tax_amount"] == 180.0
        assert result["discount_amount"] == 50.0
        assert result["grand_total"] == Decimal("1130.00")

    def test_create_purchase_invoice_partially_received_po(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test Purchase Invoice creation for partially received Purchase Order"""
        service = PurchaseInvoiceService(db_session)

        # Change PO status to PARTIALLY_RECEIVED and set received quantity
        purchase_order.status = PurchaseOrderStatus.PARTIALLY_RECEIVED
        purchase_order.line_items[0].received_quantity = Decimal("5.00")
        db_session.commit()

        line_items = [
            {
                "item_id": item.id,
                "quantity": 5,
                "unit_price": 100.00,
            }
        ]

        result = service.create_purchase_invoice(
            purchase_order_id=purchase_order.id,
            line_items=line_items,
            tax_rate=Decimal("0.18"),
            discount_amount=Decimal("0.00"),
            organization_id=organization_id,
            user_id=user_id,
            invoice_no="INV-003",
        )

        # Verify invoice was created successfully
        assert result["id"] is not None
        assert result["reference_id"] == purchase_order.id
        assert result["grand_total"] == Decimal("590.00")  # 500 + 90 tax

    def test_create_purchase_invoice_fully_received_po(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test Purchase Invoice creation for fully received Purchase Order"""
        service = PurchaseInvoiceService(db_session)

        # Change PO status to FULLY_RECEIVED and set received quantity
        purchase_order.status = PurchaseOrderStatus.FULLY_RECEIVED
        purchase_order.line_items[0].received_quantity = Decimal("10.00")
        db_session.commit()

        line_items = [
            {
                "item_id": item.id,
                "quantity": 10,
                "unit_price": 100.00,
            }
        ]

        result = service.create_purchase_invoice(
            purchase_order_id=purchase_order.id,
            line_items=line_items,
            tax_rate=Decimal("0.18"),
            discount_amount=Decimal("0.00"),
            organization_id=organization_id,
            user_id=user_id,
            invoice_no="INV-004",
        )

        # Verify invoice was created successfully
        assert result["id"] is not None
        assert result["reference_id"] == purchase_order.id
        assert result["grand_total"] == Decimal("1180.00")

    def test_three_way_matching_invoiced_exceeds_received(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test three-way matching validation fails when invoiced quantity exceeds received quantity"""
        service = PurchaseInvoiceService(db_session)

        # Set received quantity to 5 (less than ordered 10)
        purchase_order.line_items[0].received_quantity = Decimal("5.00")
        db_session.commit()

        # Try to invoice 10 items (more than received 5)
        line_items = [
            {
                "item_id": item.id,
                "quantity": 10,
                "unit_price": 100.00,
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            service.create_purchase_invoice(
                purchase_order_id=purchase_order.id,
                line_items=line_items,
                tax_rate=Decimal("0.18"),
                discount_amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                invoice_no="INV-005",
            )

        error_msg = str(exc_info.value)
        assert "invoiced quantity 10" in error_msg
        assert "exceeds received quantity 5" in error_msg
        assert "Three-way matching validation failed" in error_msg

    def test_three_way_matching_invoiced_equals_received(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test three-way matching validation passes when invoiced quantity equals received quantity"""
        service = PurchaseInvoiceService(db_session)

        # Set received quantity to 10 (all items received)
        purchase_order.line_items[0].received_quantity = Decimal("10.00")
        db_session.commit()

        # Invoice all 10 items
        line_items = [
            {
                "item_id": item.id,
                "quantity": 10,
                "unit_price": 100.00,
            }
        ]

        result = service.create_purchase_invoice(
            purchase_order_id=purchase_order.id,
            line_items=line_items,
            tax_rate=Decimal("0.18"),
            discount_amount=Decimal("0.00"),
            organization_id=organization_id,
            user_id=user_id,
            invoice_no="INV-006",
        )

        # Verify invoice was created successfully
        assert result["id"] is not None
        assert result["grand_total"] == Decimal("1180.00")

    def test_three_way_matching_invoiced_less_than_received(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test three-way matching validation passes when invoiced quantity is less than received quantity"""
        service = PurchaseInvoiceService(db_session)

        # Set received quantity to 10 (all items received)
        purchase_order.line_items[0].received_quantity = Decimal("10.00")
        db_session.commit()

        # Invoice only 7 items (less than received)
        line_items = [
            {
                "item_id": item.id,
                "quantity": 7,
                "unit_price": 100.00,
            }
        ]

        result = service.create_purchase_invoice(
            purchase_order_id=purchase_order.id,
            line_items=line_items,
            tax_rate=Decimal("0.18"),
            discount_amount=Decimal("0.00"),
            organization_id=organization_id,
            user_id=user_id,
            invoice_no="INV-007",
        )

        # Verify invoice was created successfully
        assert result["id"] is not None
        assert result["grand_total"] == Decimal("826.00")  # 700 + 126 tax

    def test_three_way_matching_zero_received_quantity(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
        item: Item,
    ):
        """Test three-way matching validation fails when no items have been received"""
        service = PurchaseInvoiceService(db_session)

        # Received quantity is 0 (no items received yet)
        assert purchase_order.line_items[0].received_quantity == Decimal("0.00")

        # Try to invoice items when nothing has been received
        line_items = [
            {
                "item_id": item.id,
                "quantity": 5,
                "unit_price": 100.00,
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            service.create_purchase_invoice(
                purchase_order_id=purchase_order.id,
                line_items=line_items,
                tax_rate=Decimal("0.18"),
                discount_amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                invoice_no="INV-008",
            )

        error_msg = str(exc_info.value)
        assert "invoiced quantity 5" in error_msg
        assert "exceeds received quantity 0" in error_msg
        assert "Three-way matching validation failed" in error_msg

    def test_three_way_matching_item_not_in_po(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purchase_order: PurchaseOrder,
    ):
        """Test three-way matching validation fails when invoice item not in Purchase Order"""
        service = PurchaseInvoiceService(db_session)

        # Create a different item not in the Purchase Order
        different_item = Item(
            id=uuid.uuid4(),
            organization_id=organization_id,
            item_name="Different Item",
            item_code="ITEM-999",
            description="Item not in PO",
            uom="PCS",
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
        db_session.add(different_item)
        db_session.commit()

        # Try to invoice an item that's not in the Purchase Order
        line_items = [
            {
                "item_id": different_item.id,
                "quantity": 5,
                "unit_price": 100.00,
            }
        ]

        with pytest.raises(ValidationException) as exc_info:
            service.create_purchase_invoice(
                purchase_order_id=purchase_order.id,
                line_items=line_items,
                tax_rate=Decimal("0.18"),
                discount_amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                invoice_no="INV-009",
            )

        error_msg = str(exc_info.value)
        assert f"item {different_item.id} not found in Purchase Order" in error_msg

    def test_three_way_matching_multiple_items(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        supplier: Supplier,
    ):
        """Test three-way matching validation with multiple line items"""
        service = PurchaseInvoiceService(db_session)

        # Create multiple items
        item1 = Item(
            id=uuid.uuid4(),
            organization_id=organization_id,
            item_name="Item 1",
            item_code="ITEM-001",
            description="First item",
            uom="PCS",
            created_by=user_id,
            updated_by=user_id,
        )
        item2 = Item(
            id=uuid.uuid4(),
            organization_id=organization_id,
            item_name="Item 2",
            item_code="ITEM-002",
            description="Second item",
            uom="PCS",
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add_all([item1, item2])
        db_session.commit()

        # Create Purchase Order with multiple items
        po = PurchaseOrder(
            id=uuid.uuid4(),
            organization_id=organization_id,
            party_type="SUPPLIER",
            party_id=supplier.id,
            status=PurchaseOrderStatus.SUBMITTED,
            subtotal=Decimal("1500.00"),
            tax_amount=Decimal("270.00"),
            tax_rate=Decimal("0.18"),
            discount_amount=Decimal("0.00"),
            grand_total=Decimal("1770.00"),
            created_by=user_id,
            updated_by=user_id,
        )
        db_session.add(po)
        db_session.commit()

        # Add line items with different received quantities
        line1 = PurchaseOrderLine(
            id=uuid.uuid4(),
            organization_id=organization_id,
            purchase_order_id=po.id,
            item_id=item1.id,
            quantity=Decimal("10.00"),
            unit_price=Decimal("100.00"),
            line_total=Decimal("1000.00"),
            received_quantity=Decimal("10.00"),  # Fully received
        )
        line2 = PurchaseOrderLine(
            id=uuid.uuid4(),
            organization_id=organization_id,
            purchase_order_id=po.id,
            item_id=item2.id,
            quantity=Decimal("10.00"),
            unit_price=Decimal("50.00"),
            line_total=Decimal("500.00"),
            received_quantity=Decimal("5.00"),  # Partially received
        )
        db_session.add_all([line1, line2])
        db_session.commit()
        db_session.refresh(po)

        # Try to invoice more than received for item2
        line_items = [
            {
                "item_id": item1.id,
                "quantity": 10,  # OK: received 10
                "unit_price": 100.00,
            },
            {
                "item_id": item2.id,
                "quantity": 8,  # FAIL: only received 5
                "unit_price": 50.00,
            },
        ]

        with pytest.raises(ValidationException) as exc_info:
            service.create_purchase_invoice(
                purchase_order_id=po.id,
                line_items=line_items,
                tax_rate=Decimal("0.18"),
                discount_amount=Decimal("0.00"),
                organization_id=organization_id,
                user_id=user_id,
                invoice_no="INV-010",
            )

        error_msg = str(exc_info.value)
        assert "invoiced quantity 8" in error_msg
        assert "exceeds received quantity 5" in error_msg
        assert "Three-way matching validation failed" in error_msg
