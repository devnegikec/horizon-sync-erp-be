"""Tests for Sales Order Service"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import SalesOrderStatus
from app.models.customer import Customer
from app.models.item import Item
from app.services.sales_order_service import SalesOrderService


@pytest.fixture
def organization_id():
    """Provide a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def user_id():
    """Provide a test user ID"""
    return uuid.uuid4()


@pytest.fixture
def customer(db_session: Session, organization_id: uuid.UUID):
    """Create a test customer"""
    customer = Customer(
        id=uuid.uuid4(),
        organization_id=organization_id,
        customer_name="Test Customer",
        customer_code="CUST001",
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def item(db_session: Session, organization_id: uuid.UUID):
    """Create a test item"""
    item = Item(
        id=uuid.uuid4(),
        organization_id=organization_id,
        item_code="ITEM001",
        item_name="Test Item",
        item_type="stock",
        uom="Pcs",
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


class TestSalesOrderServiceCreate:
    """Tests for creating sales orders"""

    def test_create_sales_order_with_items(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test creating a sales order with line items"""
        service = SalesOrderService(db_session)

        data = {
            "sales_order_no": "SO-001",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        result = service.create(data, organization_id, user_id)

        assert result["sales_order_no"] == "SO-001"
        assert result["customer_id"] == customer.id
        assert result["status"] == "draft"
        assert result["grand_total"] == Decimal("1000.00")
        assert result["currency"] == "USD"
        assert result["organization_id"] == organization_id
        assert result["created_by"] == user_id
        assert result["updated_by"] == user_id
        assert len(result["items"]) == 1

        # Check line item
        line_item = result["items"][0]
        assert line_item["item_id"] == item.id
        assert line_item["qty"] == Decimal("10.000")
        assert line_item["rate"] == Decimal("100.00")
        assert line_item["amount"] == Decimal("1000.00")
        assert line_item["billed_qty"] == Decimal("0")
        assert line_item["delivered_qty"] == Decimal("0")
        assert line_item["pending_billing_qty"] == Decimal("10.000")
        assert line_item["pending_delivery_qty"] == Decimal("10.000")

    def test_create_sales_order_initializes_quantities_to_zero(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that billed_qty and delivered_qty are initialized to 0"""
        service = SalesOrderService(db_session)

        data = {
            "sales_order_no": "SO-002",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("5.000"),
                    "uom": "Pcs",
                    "rate": Decimal("50.00"),
                }
            ],
        }

        result = service.create(data, organization_id, user_id)

        line_item = result["items"][0]
        assert line_item["billed_qty"] == Decimal("0")
        assert line_item["delivered_qty"] == Decimal("0")

    def test_create_sales_order_calculates_grand_total(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that grand_total is calculated from line items"""
        service = SalesOrderService(db_session)

        data = {
            "sales_order_no": "SO-003",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                },
                {
                    "item_id": item.id,
                    "qty": Decimal("5.000"),
                    "uom": "Pcs",
                    "rate": Decimal("200.00"),
                },
            ],
        }

        result = service.create(data, organization_id, user_id)

        # grand_total should be (10 * 100) + (5 * 200) = 2000
        assert result["grand_total"] == Decimal("2000.00")


class TestSalesOrderServiceRead:
    """Tests for reading sales orders"""

    def test_get_by_id_returns_sales_order_with_pending_quantities(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test getting a sales order by ID includes pending quantities"""
        service = SalesOrderService(db_session)

        # Create a sales order
        data = {
            "sales_order_no": "SO-004",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        created = service.create(data, organization_id, user_id)

        # Get the sales order
        result = service.get_by_id(created["id"], organization_id)

        assert result["id"] == created["id"]
        assert len(result["items"]) == 1

        line_item = result["items"][0]
        assert line_item["pending_billing_qty"] == Decimal("10.000")
        assert line_item["pending_delivery_qty"] == Decimal("10.000")

    def test_get_by_id_not_found_raises_exception(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
    ):
        """Test getting a non-existent sales order raises exception"""
        service = SalesOrderService(db_session)

        with pytest.raises(ResourceNotFoundException):
            service.get_by_id(uuid.uuid4(), organization_id)

    def test_get_list_returns_paginated_results(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test getting a list of sales orders with pagination"""
        service = SalesOrderService(db_session)

        # Create multiple sales orders
        for i in range(3):
            data = {
                "sales_order_no": f"SO-{i:03d}",
                "customer_id": customer.id,
                "order_date": datetime.now(UTC),
                "items": [
                    {
                        "item_id": item.id,
                        "qty": Decimal("10.000"),
                        "uom": "Pcs",
                        "rate": Decimal("100.00"),
                    }
                ],
            }
            service.create(data, organization_id, user_id)

        # Get list
        items, pagination = service.get_list(organization_id, page=1, page_size=2)

        assert len(items) == 2
        assert pagination["total_items"] == 3
        assert pagination["total_pages"] == 2
        assert pagination["has_next"] is True
        assert pagination["has_prev"] is False


class TestSalesOrderServiceUpdate:
    """Tests for updating sales orders"""

    def test_update_sales_order(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test updating a sales order"""
        service = SalesOrderService(db_session)

        # Create a sales order
        data = {
            "sales_order_no": "SO-005",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        created = service.create(data, organization_id, user_id)

        # Update the sales order
        update_data = {
            "remarks": "Updated remarks",
        }

        result = service.update(created["id"], update_data, organization_id, user_id)

        assert result["remarks"] == "Updated remarks"
        assert result["updated_by"] == user_id


class TestSalesOrderServiceDelete:
    """Tests for deleting sales orders"""

    def test_delete_sales_order(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test deleting a sales order"""
        service = SalesOrderService(db_session)

        # Create a sales order
        data = {
            "sales_order_no": "SO-006",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        created = service.create(data, organization_id, user_id)

        # Delete the sales order
        service.delete(created["id"], organization_id)

        # Verify it's deleted
        with pytest.raises(ResourceNotFoundException):
            service.get_by_id(created["id"], organization_id)


class TestSalesOrderStatusTransitions:
    """Tests for sales order status transition validation"""

    def test_valid_transition_draft_to_confirmed(
        self,
        db_session: Session,
    ):
        """Test valid transition from DRAFT to CONFIRMED"""
        service = SalesOrderService(db_session)

        # Should not raise an exception
        service._validate_status_transition(
            SalesOrderStatus.DRAFT, SalesOrderStatus.CONFIRMED
        )

    def test_valid_transition_confirmed_to_partially_delivered(
        self,
        db_session: Session,
    ):
        """Test valid transition from CONFIRMED to PARTIALLY_DELIVERED"""
        service = SalesOrderService(db_session)

        service._validate_status_transition(
            SalesOrderStatus.CONFIRMED, SalesOrderStatus.PARTIALLY_DELIVERED
        )

    def test_valid_transition_confirmed_to_delivered(
        self,
        db_session: Session,
    ):
        """Test valid transition from CONFIRMED to DELIVERED"""
        service = SalesOrderService(db_session)

        service._validate_status_transition(
            SalesOrderStatus.CONFIRMED, SalesOrderStatus.DELIVERED
        )

    def test_valid_transition_partially_delivered_to_delivered(
        self,
        db_session: Session,
    ):
        """Test valid transition from PARTIALLY_DELIVERED to DELIVERED"""
        service = SalesOrderService(db_session)

        service._validate_status_transition(
            SalesOrderStatus.PARTIALLY_DELIVERED, SalesOrderStatus.DELIVERED
        )

    def test_valid_transition_delivered_to_closed(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test valid transition from DELIVERED to CLOSED requires sales order with fully billed items"""
        service = SalesOrderService(db_session)

        # Create a sales order with fully billed items
        data = {
            "sales_order_no": "SO-TEST-001",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        sales_order_dict = service.create(data, organization_id, user_id)
        
        # Bill the full quantity
        items_to_bill = [
            {
                "item_id": sales_order_dict["items"][0]["id"],
                "qty_to_bill": Decimal("10.000"),
            }
        ]
        service.convert_to_invoice(
            sales_order_dict["id"], items_to_bill, organization_id, user_id
        )
        
        # Get the sales order object
        from app.repositories.sales_order_repository import SalesOrderRepository
        repo = SalesOrderRepository(db_session)
        sales_order = repo.get_by_id_with_items(sales_order_dict["id"], organization_id)

        # Should not raise an exception
        service._validate_status_transition(
            SalesOrderStatus.DELIVERED, SalesOrderStatus.CLOSED, sales_order
        )

    def test_cancelled_allowed_from_draft(
        self,
        db_session: Session,
    ):
        """Test CANCELLED is allowed from DRAFT"""
        service = SalesOrderService(db_session)

        service._validate_status_transition(
            SalesOrderStatus.DRAFT, SalesOrderStatus.CANCELLED
        )

    def test_cancelled_allowed_from_confirmed(
        self,
        db_session: Session,
    ):
        """Test CANCELLED is allowed from CONFIRMED"""
        service = SalesOrderService(db_session)

        service._validate_status_transition(
            SalesOrderStatus.CONFIRMED, SalesOrderStatus.CANCELLED
        )

    def test_cancelled_allowed_from_partially_delivered(
        self,
        db_session: Session,
    ):
        """Test CANCELLED is allowed from PARTIALLY_DELIVERED"""
        service = SalesOrderService(db_session)

        service._validate_status_transition(
            SalesOrderStatus.PARTIALLY_DELIVERED, SalesOrderStatus.CANCELLED
        )

    def test_cancelled_allowed_from_delivered(
        self,
        db_session: Session,
    ):
        """Test CANCELLED is allowed from DELIVERED"""
        service = SalesOrderService(db_session)

        service._validate_status_transition(
            SalesOrderStatus.DELIVERED, SalesOrderStatus.CANCELLED
        )

    def test_cancelled_not_allowed_from_closed(
        self,
        db_session: Session,
    ):
        """Test CANCELLED is not allowed from CLOSED"""
        service = SalesOrderService(db_session)

        with pytest.raises(
            ValueError, match="Cannot cancel a sales order that is already CLOSED"
        ):
            service._validate_status_transition(
                SalesOrderStatus.CLOSED, SalesOrderStatus.CANCELLED
            )

    def test_invalid_transition_draft_to_delivered(
        self,
        db_session: Session,
    ):
        """Test invalid transition from DRAFT to DELIVERED"""
        service = SalesOrderService(db_session)

        with pytest.raises(ValueError, match="Invalid status transition"):
            service._validate_status_transition(
                SalesOrderStatus.DRAFT, SalesOrderStatus.DELIVERED
            )

    def test_invalid_transition_draft_to_closed(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test invalid transition from DRAFT to CLOSED without fully billed items"""
        service = SalesOrderService(db_session)

        # Create a sales order without billing
        data = {
            "sales_order_no": "SO-TEST-002",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        sales_order_dict = service.create(data, organization_id, user_id)
        
        # Get the sales order object
        from app.repositories.sales_order_repository import SalesOrderRepository
        repo = SalesOrderRepository(db_session)
        sales_order = repo.get_by_id_with_items(sales_order_dict["id"], organization_id)

        with pytest.raises(ValueError, match="not all items are fully billed"):
            service._validate_status_transition(
                SalesOrderStatus.DRAFT, SalesOrderStatus.CLOSED, sales_order
            )

    def test_invalid_transition_confirmed_to_closed(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test invalid transition from CONFIRMED to CLOSED without fully billed items"""
        service = SalesOrderService(db_session)

        # Create a sales order without billing
        data = {
            "sales_order_no": "SO-TEST-003",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        sales_order_dict = service.create(data, organization_id, user_id)
        
        # Get the sales order object
        from app.repositories.sales_order_repository import SalesOrderRepository
        repo = SalesOrderRepository(db_session)
        sales_order = repo.get_by_id_with_items(sales_order_dict["id"], organization_id)

        with pytest.raises(ValueError, match="not all items are fully billed"):
            service._validate_status_transition(
                SalesOrderStatus.CONFIRMED, SalesOrderStatus.CLOSED, sales_order
            )

    def test_invalid_transition_from_cancelled(
        self,
        db_session: Session,
    ):
        """Test that no transitions are allowed from CANCELLED"""
        service = SalesOrderService(db_session)

        with pytest.raises(ValueError, match="Cannot transition from cancelled"):
            service._validate_status_transition(
                SalesOrderStatus.CANCELLED, SalesOrderStatus.DRAFT
            )

    def test_invalid_transition_from_closed(
        self,
        db_session: Session,
    ):
        """Test that no transitions are allowed from CLOSED"""
        service = SalesOrderService(db_session)

        with pytest.raises(ValueError, match="Cannot transition from closed"):
            service._validate_status_transition(
                SalesOrderStatus.CLOSED, SalesOrderStatus.DRAFT
            )

    def test_same_status_transition_allowed(
        self,
        db_session: Session,
    ):
        """Test that transitioning to the same status is allowed (no-op)"""
        service = SalesOrderService(db_session)

        # Should not raise an exception
        service._validate_status_transition(
            SalesOrderStatus.DRAFT, SalesOrderStatus.DRAFT
        )
        service._validate_status_transition(
            SalesOrderStatus.CONFIRMED, SalesOrderStatus.CONFIRMED
        )


class TestSalesOrderUpdateStatus:
    """Tests for update_status method"""

    def test_update_status_draft_to_confirmed(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test updating status from DRAFT to CONFIRMED"""
        service = SalesOrderService(db_session)

        # Create a sales order
        data = {
            "sales_order_no": "SO-STATUS-001",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        created = service.create(data, organization_id, user_id)
        assert created["status"] == "draft"
        assert created["submitted_at"] is None

        # Update status to CONFIRMED
        result = service.update_status(
            created["id"], "confirmed", organization_id, user_id
        )

        assert result["status"] == "confirmed"
        assert result["submitted_at"] is not None
        assert result["updated_by"] == user_id

    def test_update_status_sets_submitted_at_only_once(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that submitted_at is set only once when transitioning to CONFIRMED"""
        service = SalesOrderService(db_session)

        # Create a sales order
        data = {
            "sales_order_no": "SO-STATUS-002",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        created = service.create(data, organization_id, user_id)

        # Update status to CONFIRMED
        result1 = service.update_status(
            created["id"], "confirmed", organization_id, user_id
        )
        first_submitted_at = result1["submitted_at"]

        # Update status to CONFIRMED again (no-op)
        result2 = service.update_status(
            created["id"], "confirmed", organization_id, user_id
        )

        # submitted_at should remain the same
        assert result2["submitted_at"] == first_submitted_at

    def test_update_status_confirmed_to_delivered(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test updating status from CONFIRMED to DELIVERED"""
        service = SalesOrderService(db_session)

        # Create a sales order
        data = {
            "sales_order_no": "SO-STATUS-003",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        created = service.create(data, organization_id, user_id)

        # Update to CONFIRMED first
        service.update_status(created["id"], "confirmed", organization_id, user_id)

        # Update to DELIVERED
        result = service.update_status(
            created["id"], "delivered", organization_id, user_id
        )

        assert result["status"] == "delivered"

    def test_update_status_invalid_transition_raises_error(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that invalid status transition raises ValueError"""
        service = SalesOrderService(db_session)

        # Create a sales order
        data = {
            "sales_order_no": "SO-STATUS-004",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        created = service.create(data, organization_id, user_id)

        # Try to update from DRAFT to DELIVERED (invalid)
        with pytest.raises(ValueError, match="Invalid status transition"):
            service.update_status(created["id"], "delivered", organization_id, user_id)

    def test_update_status_to_cancelled_from_draft(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test updating status to CANCELLED from DRAFT"""
        service = SalesOrderService(db_session)

        # Create a sales order
        data = {
            "sales_order_no": "SO-STATUS-005",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        created = service.create(data, organization_id, user_id)

        # Update to CANCELLED
        result = service.update_status(
            created["id"], "cancelled", organization_id, user_id
        )

        assert result["status"] == "cancelled"

    def test_update_status_not_found_raises_exception(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test updating status of non-existent sales order raises exception"""
        service = SalesOrderService(db_session)

        with pytest.raises(ResourceNotFoundException):
            service.update_status(uuid.uuid4(), "confirmed", organization_id, user_id)

    def test_update_status_cannot_cancel_closed_order(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that CLOSED sales order cannot be cancelled"""
        service = SalesOrderService(db_session)

        # Create a sales order and move it to CLOSED
        data = {
            "sales_order_no": "SO-STATUS-006",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        created = service.create(data, organization_id, user_id)

        # Bill the full quantity first (required for CLOSED status)
        items_to_bill = [
            {
                "item_id": created["items"][0]["id"],
                "qty_to_bill": Decimal("10.000"),
            }
        ]
        service.convert_to_invoice(
            created["id"], items_to_bill, organization_id, user_id
        )

        # Move through the workflow to CLOSED
        service.update_status(created["id"], "confirmed", organization_id, user_id)
        service.update_status(created["id"], "delivered", organization_id, user_id)
        service.update_status(created["id"], "closed", organization_id, user_id)

        # Try to cancel - should fail
        with pytest.raises(
            ValueError, match="Cannot cancel a sales order that is already CLOSED"
        ):
            service.update_status(created["id"], "cancelled", organization_id, user_id)


class TestSalesOrderConvertToInvoice:
    """Tests for converting sales orders to invoices"""

    def test_convert_to_invoice_full_billing(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test converting a sales order to invoice with full billing"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-001",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "remarks": "Test order",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Convert to invoice with full billing
        items_to_bill = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("10.000"),
            }
        ]

        invoice = service.convert_to_invoice(
            sales_order["id"], items_to_bill, organization_id, user_id
        )

        # Verify invoice
        assert invoice["invoice_type"] == "sales"
        assert invoice["party_id"] == customer.id
        assert invoice["party_type"] == "Customer"
        assert invoice["status"] == "draft"
        assert invoice["currency"] == "USD"
        assert invoice["reference_type"] == "Sales Order"
        assert invoice["reference_id"] == sales_order["id"]
        assert invoice["remarks"] == "Test order"
        assert invoice["grand_total"] == Decimal("1000.00")

        # Verify sales order item billed_qty updated
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["billed_qty"] == Decimal("10.000")
        assert updated_so["items"][0]["pending_billing_qty"] == Decimal("0.000")

    def test_convert_to_invoice_partial_billing(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test converting a sales order to invoice with partial billing"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-002",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Convert to invoice with partial billing (5 out of 10)
        items_to_bill = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("5.000"),
            }
        ]

        invoice = service.convert_to_invoice(
            sales_order["id"], items_to_bill, organization_id, user_id
        )

        # Verify invoice
        assert invoice["grand_total"] == Decimal("500.00")

        # Verify sales order item billed_qty updated
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["billed_qty"] == Decimal("5.000")
        assert updated_so["items"][0]["pending_billing_qty"] == Decimal("5.000")

    def test_convert_to_invoice_exceeds_pending_qty_raises_error(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that billing quantity exceeding pending_billing_qty raises error"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-003",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Try to bill more than available
        items_to_bill = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("15.000"),  # More than ordered qty
            }
        ]

        with pytest.raises(ValueError, match="exceeds pending billing quantity"):
            service.convert_to_invoice(
                sales_order["id"], items_to_bill, organization_id, user_id
            )

    def test_convert_to_invoice_multiple_partial_billings(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test multiple partial billings for the same sales order"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-004",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # First partial billing (3 units)
        items_to_bill_1 = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("3.000"),
            }
        ]

        invoice1 = service.convert_to_invoice(
            sales_order["id"], items_to_bill_1, organization_id, user_id
        )

        assert invoice1["grand_total"] == Decimal("300.00")

        # Verify first update
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["billed_qty"] == Decimal("3.000")
        assert updated_so["items"][0]["pending_billing_qty"] == Decimal("7.000")

        # Second partial billing (4 units)
        items_to_bill_2 = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("4.000"),
            }
        ]

        invoice2 = service.convert_to_invoice(
            sales_order["id"], items_to_bill_2, organization_id, user_id
        )

        assert invoice2["grand_total"] == Decimal("400.00")

        # Verify second update
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["billed_qty"] == Decimal("7.000")
        assert updated_so["items"][0]["pending_billing_qty"] == Decimal("3.000")

    def test_convert_to_invoice_zero_qty_raises_error(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that zero billing quantity raises error"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-005",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Try to bill zero quantity
        items_to_bill = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("0.000"),
            }
        ]

        with pytest.raises(ValueError, match="must be greater than 0"):
            service.convert_to_invoice(
                sales_order["id"], items_to_bill, organization_id, user_id
            )

    def test_convert_to_invoice_not_found_raises_error(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test that converting non-existent sales order raises error"""
        service = SalesOrderService(db_session)

        fake_id = uuid.uuid4()
        items_to_bill = [
            {
                "item_id": uuid.uuid4(),
                "qty_to_bill": Decimal("5.000"),
            }
        ]

        with pytest.raises(ResourceNotFoundException):
            service.convert_to_invoice(fake_id, items_to_bill, organization_id, user_id)

    def test_convert_to_invoice_invalid_item_raises_error(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that billing an item not in the sales order raises error"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-006",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Try to bill an item that's not in the sales order
        items_to_bill = [
            {
                "item_id": uuid.uuid4(),  # Random item ID
                "qty_to_bill": Decimal("5.000"),
            }
        ]

        with pytest.raises(ValueError, match="not found in sales order"):
            service.convert_to_invoice(
                sales_order["id"], items_to_bill, organization_id, user_id
            )


class TestSalesOrderFullyBilledCheck:
    """Tests for fully billed check logic (Requirement 6.7)"""

    def test_fully_billed_allows_closed_status(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that fully billed sales order can transition to CLOSED"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-CLOSED-001",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Confirm the order
        service.update_status(sales_order["id"], "confirmed", organization_id, user_id)

        # Bill the full quantity
        items_to_bill = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("10.000"),
            }
        ]

        service.convert_to_invoice(
            sales_order["id"], items_to_bill, organization_id, user_id
        )

        # Verify sales order is fully billed
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["billed_qty"] == Decimal("10.000")
        assert updated_so["items"][0]["pending_billing_qty"] == Decimal("0.000")

        # Should be able to transition to CLOSED from CONFIRMED
        result = service.update_status(
            sales_order["id"], "closed", organization_id, user_id
        )

        assert result["status"] == "closed"

    def test_partially_billed_prevents_closed_status(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that partially billed sales order cannot transition to CLOSED"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-CLOSED-002",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Confirm the order
        service.update_status(sales_order["id"], "confirmed", organization_id, user_id)

        # Bill only partial quantity
        items_to_bill = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("5.000"),  # Only half
            }
        ]

        service.convert_to_invoice(
            sales_order["id"], items_to_bill, organization_id, user_id
        )

        # Verify sales order is partially billed
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["billed_qty"] == Decimal("5.000")
        assert updated_so["items"][0]["pending_billing_qty"] == Decimal("5.000")

        # Should NOT be able to transition to CLOSED
        with pytest.raises(
            ValueError, match="not all items are fully billed"
        ):
            service.update_status(
                sales_order["id"], "closed", organization_id, user_id
            )

    def test_unbilled_prevents_closed_status(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that unbilled sales order cannot transition to CLOSED"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-CLOSED-003",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Confirm the order
        service.update_status(sales_order["id"], "confirmed", organization_id, user_id)

        # Don't bill anything

        # Should NOT be able to transition to CLOSED
        with pytest.raises(
            ValueError, match="not all items are fully billed"
        ):
            service.update_status(
                sales_order["id"], "closed", organization_id, user_id
            )

    def test_fully_billed_multiple_items_allows_closed(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that sales order with multiple fully billed items can transition to CLOSED"""
        service = SalesOrderService(db_session)

        # Create sales order with multiple items
        data = {
            "sales_order_no": "SO-CLOSED-004",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                },
                {
                    "item_id": item.id,
                    "qty": Decimal("5.000"),
                    "uom": "Pcs",
                    "rate": Decimal("200.00"),
                },
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Confirm the order
        service.update_status(sales_order["id"], "confirmed", organization_id, user_id)

        # Bill all items fully
        items_to_bill = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("10.000"),
            },
            {
                "item_id": sales_order["items"][1]["id"],
                "qty_to_bill": Decimal("5.000"),
            },
        ]

        service.convert_to_invoice(
            sales_order["id"], items_to_bill, organization_id, user_id
        )

        # Should be able to transition to CLOSED
        result = service.update_status(
            sales_order["id"], "closed", organization_id, user_id
        )

        assert result["status"] == "closed"

    def test_partially_billed_multiple_items_prevents_closed(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that sales order with one partially billed item cannot transition to CLOSED"""
        service = SalesOrderService(db_session)

        # Create sales order with multiple items
        data = {
            "sales_order_no": "SO-CLOSED-005",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                },
                {
                    "item_id": item.id,
                    "qty": Decimal("5.000"),
                    "uom": "Pcs",
                    "rate": Decimal("200.00"),
                },
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Confirm the order
        service.update_status(sales_order["id"], "confirmed", organization_id, user_id)

        # Bill first item fully, second item partially
        items_to_bill = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("10.000"),  # Full
            },
            {
                "item_id": sales_order["items"][1]["id"],
                "qty_to_bill": Decimal("3.000"),  # Partial (3 out of 5)
            },
        ]

        service.convert_to_invoice(
            sales_order["id"], items_to_bill, organization_id, user_id
        )

        # Should NOT be able to transition to CLOSED
        with pytest.raises(
            ValueError, match="not all items are fully billed"
        ):
            service.update_status(
                sales_order["id"], "closed", organization_id, user_id
            )

    def test_fully_billed_from_draft_allows_closed(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that fully billed sales order can transition to CLOSED even from DRAFT"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-CLOSED-006",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Bill the full quantity (even from DRAFT status)
        items_to_bill = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_bill": Decimal("10.000"),
            }
        ]

        service.convert_to_invoice(
            sales_order["id"], items_to_bill, organization_id, user_id
        )

        # Should be able to transition to CLOSED from DRAFT if fully billed
        result = service.update_status(
            sales_order["id"], "closed", organization_id, user_id
        )

        assert result["status"] == "closed"


class TestSalesOrderConvertToDeliveryNote:
    """Tests for converting sales orders to delivery notes"""

    def test_convert_to_delivery_note_full_delivery(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test converting a sales order to delivery note with full delivery"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-DN-001",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "remarks": "Test order for delivery",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Convert to delivery note with full delivery
        items_to_deliver = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_deliver": Decimal("10.000"),
            }
        ]

        delivery_note = service.convert_to_delivery_note(
            sales_order["id"], items_to_deliver, organization_id, user_id
        )

        # Verify delivery note
        assert delivery_note["customer_id"] == customer.id
        assert delivery_note["status"] == "draft"
        assert delivery_note["reference_type"] == "Sales Order"
        assert delivery_note["reference_id"] == sales_order["id"]
        assert delivery_note["remarks"] == "Test order for delivery"

        # Verify sales order item delivered_qty updated
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["delivered_qty"] == Decimal("10.000")
        assert updated_so["items"][0]["pending_delivery_qty"] == Decimal("0.000")
        
        # Verify status automatically updated to DELIVERED
        assert updated_so["status"] == "delivered"

    def test_convert_to_delivery_note_partial_delivery(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test converting a sales order to delivery note with partial delivery"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-DN-002",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Convert to delivery note with partial delivery (5 out of 10)
        items_to_deliver = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_deliver": Decimal("5.000"),
            }
        ]

        delivery_note = service.convert_to_delivery_note(
            sales_order["id"], items_to_deliver, organization_id, user_id
        )

        # Verify delivery note created
        assert delivery_note["customer_id"] == customer.id

        # Verify sales order item delivered_qty updated
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["delivered_qty"] == Decimal("5.000")
        assert updated_so["items"][0]["pending_delivery_qty"] == Decimal("5.000")
        
        # Verify status automatically updated to PARTIALLY_DELIVERED
        assert updated_so["status"] == "partially_delivered"

    def test_convert_to_delivery_note_exceeds_pending_qty_raises_error(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that delivery quantity exceeding pending_delivery_qty raises error"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-DN-003",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Try to deliver more than available
        items_to_deliver = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_deliver": Decimal("15.000"),  # More than ordered qty
            }
        ]

        with pytest.raises(ValueError, match="exceeds pending delivery quantity"):
            service.convert_to_delivery_note(
                sales_order["id"], items_to_deliver, organization_id, user_id
            )

    def test_convert_to_delivery_note_multiple_partial_deliveries(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test multiple partial deliveries for the same sales order"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-DN-004",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # First partial delivery (3 units)
        items_to_deliver_1 = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_deliver": Decimal("3.000"),
            }
        ]

        delivery_note1 = service.convert_to_delivery_note(
            sales_order["id"], items_to_deliver_1, organization_id, user_id
        )

        assert delivery_note1["customer_id"] == customer.id

        # Verify first update
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["delivered_qty"] == Decimal("3.000")
        assert updated_so["items"][0]["pending_delivery_qty"] == Decimal("7.000")
        assert updated_so["status"] == "partially_delivered"

        # Second partial delivery (4 units)
        items_to_deliver_2 = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_deliver": Decimal("4.000"),
            }
        ]

        delivery_note2 = service.convert_to_delivery_note(
            sales_order["id"], items_to_deliver_2, organization_id, user_id
        )

        assert delivery_note2["customer_id"] == customer.id

        # Verify second update
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["delivered_qty"] == Decimal("7.000")
        assert updated_so["items"][0]["pending_delivery_qty"] == Decimal("3.000")
        assert updated_so["status"] == "partially_delivered"

        # Third delivery (remaining 3 units)
        items_to_deliver_3 = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_deliver": Decimal("3.000"),
            }
        ]

        delivery_note3 = service.convert_to_delivery_note(
            sales_order["id"], items_to_deliver_3, organization_id, user_id
        )

        # Verify final update - should be fully delivered
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["delivered_qty"] == Decimal("10.000")
        assert updated_so["items"][0]["pending_delivery_qty"] == Decimal("0.000")
        assert updated_so["status"] == "delivered"

    def test_convert_to_delivery_note_zero_qty_raises_error(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that zero delivery quantity raises error"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-DN-005",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Try to deliver zero quantity
        items_to_deliver = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_deliver": Decimal("0.000"),
            }
        ]

        with pytest.raises(ValueError, match="must be greater than 0"):
            service.convert_to_delivery_note(
                sales_order["id"], items_to_deliver, organization_id, user_id
            )

    def test_convert_to_delivery_note_not_found_raises_error(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
    ):
        """Test that converting non-existent sales order raises error"""
        service = SalesOrderService(db_session)

        fake_id = uuid.uuid4()
        items_to_deliver = [
            {
                "item_id": uuid.uuid4(),
                "qty_to_deliver": Decimal("5.000"),
            }
        ]

        with pytest.raises(ResourceNotFoundException):
            service.convert_to_delivery_note(
                fake_id, items_to_deliver, organization_id, user_id
            )

    def test_convert_to_delivery_note_invalid_item_raises_error(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test that delivering an item not in the sales order raises error"""
        service = SalesOrderService(db_session)

        # Create sales order
        data = {
            "sales_order_no": "SO-DN-006",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                    "sort_order": 0,
                }
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Try to deliver an item that's not in the sales order
        items_to_deliver = [
            {
                "item_id": uuid.uuid4(),  # Random item ID
                "qty_to_deliver": Decimal("5.000"),
            }
        ]

        with pytest.raises(ValueError, match="not found in sales order"):
            service.convert_to_delivery_note(
                sales_order["id"], items_to_deliver, organization_id, user_id
            )

    def test_convert_to_delivery_note_multiple_items(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test converting sales order with multiple items to delivery note"""
        service = SalesOrderService(db_session)

        # Create sales order with multiple items
        data = {
            "sales_order_no": "SO-DN-007",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                },
                {
                    "item_id": item.id,
                    "qty": Decimal("5.000"),
                    "uom": "Pcs",
                    "rate": Decimal("200.00"),
                },
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Deliver all items fully
        items_to_deliver = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_deliver": Decimal("10.000"),
            },
            {
                "item_id": sales_order["items"][1]["id"],
                "qty_to_deliver": Decimal("5.000"),
            },
        ]

        delivery_note = service.convert_to_delivery_note(
            sales_order["id"], items_to_deliver, organization_id, user_id
        )

        # Verify delivery note created
        assert delivery_note["customer_id"] == customer.id

        # Verify all items delivered
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["delivered_qty"] == Decimal("10.000")
        assert updated_so["items"][1]["delivered_qty"] == Decimal("5.000")
        assert updated_so["status"] == "delivered"

    def test_convert_to_delivery_note_partial_multiple_items(
        self,
        db_session: Session,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        customer: Customer,
        item: Item,
    ):
        """Test partial delivery of multiple items"""
        service = SalesOrderService(db_session)

        # Create sales order with multiple items
        data = {
            "sales_order_no": "SO-DN-008",
            "customer_id": customer.id,
            "order_date": datetime.now(UTC),
            "currency": "USD",
            "items": [
                {
                    "item_id": item.id,
                    "qty": Decimal("10.000"),
                    "uom": "Pcs",
                    "rate": Decimal("100.00"),
                },
                {
                    "item_id": item.id,
                    "qty": Decimal("5.000"),
                    "uom": "Pcs",
                    "rate": Decimal("200.00"),
                },
            ],
        }

        sales_order = service.create(data, organization_id, user_id)

        # Deliver first item fully, second item partially
        items_to_deliver = [
            {
                "item_id": sales_order["items"][0]["id"],
                "qty_to_deliver": Decimal("10.000"),  # Full
            },
            {
                "item_id": sales_order["items"][1]["id"],
                "qty_to_deliver": Decimal("3.000"),  # Partial (3 out of 5)
            },
        ]

        delivery_note = service.convert_to_delivery_note(
            sales_order["id"], items_to_deliver, organization_id, user_id
        )

        # Verify delivery note created
        assert delivery_note["customer_id"] == customer.id

        # Verify delivery quantities
        updated_so = service.get_by_id(sales_order["id"], organization_id)
        assert updated_so["items"][0]["delivered_qty"] == Decimal("10.000")
        assert updated_so["items"][1]["delivered_qty"] == Decimal("3.000")
        
        # Status should be PARTIALLY_DELIVERED since not all items are fully delivered
        assert updated_so["status"] == "partially_delivered"
