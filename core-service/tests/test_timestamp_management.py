"""Test automatic timestamp management for quotations and sales orders"""

import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.base import (
    CustomerStatus,
    ItemStatus,
    ItemType,
    QuotationStatus,
    SalesOrderStatus,
    ValuationMethod,
)
from app.models.customer import Customer
from app.models.item import Item
from app.models.quotation import Quotation, QuotationItem
from app.models.sales_order import SalesOrder, SalesOrderItem


@pytest.fixture
def sample_organization(mock_current_user):
    """Return the organization from mock_current_user"""
    class Organization:
        def __init__(self, org_id):
            self.id = org_id
    return Organization(mock_current_user.organization_id)


@pytest.fixture
def sample_customer(db_session, mock_current_user):
    """Create a test customer in the database"""
    customer = Customer(
        id=uuid.uuid4(),
        organization_id=mock_current_user.organization_id,
        customer_name="Test Customer",
        customer_code="CUST-001",
        email="customer@test.com",
        status=CustomerStatus.ACTIVE,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


@pytest.fixture
def sample_item(db_session, mock_current_user):
    """Create a test item in the database"""
    item = Item(
        id=uuid.uuid4(),
        organization_id=mock_current_user.organization_id,
        item_code="ITEM-001",
        item_name="Test Item",
        item_type=ItemType.STOCK,
        uom="PCS",
        status=ItemStatus.ACTIVE,
        valuation_method=ValuationMethod.FIFO,
    )
    db_session.add(item)
    db_session.commit()
    db_session.refresh(item)
    return item


class TestTimestampManagement:
    """Test automatic timestamp management (Requirements 12.1, 12.2, 12.3)"""

    def test_quotation_created_at_set_on_creation(
        self, db_session, sample_organization, sample_customer, sample_item
    ):
        """Test that created_at is automatically set when creating a quotation"""
        # Create quotation
        quotation = Quotation(
            organization_id=sample_organization.id,
            quotation_no="QTN-TEST-001",
            customer_id=sample_customer.id,
            quotation_date=datetime.now(UTC),
            status=QuotationStatus.DRAFT,
            grand_total=Decimal("1000.00"),
            currency="INR",
        )
        db_session.add(quotation)
        db_session.commit()
        db_session.refresh(quotation)
        
        # Verify created_at is set
        assert quotation.created_at is not None
        # Verify it's a datetime object
        assert isinstance(quotation.created_at, datetime)
        
    def test_quotation_updated_at_updated_on_modification(
        self, db_session, sample_organization, sample_customer, sample_item
    ):
        """Test that updated_at is automatically updated when modifying a quotation"""
        # Create quotation
        quotation = Quotation(
            organization_id=sample_organization.id,
            quotation_no="QTN-TEST-002",
            customer_id=sample_customer.id,
            quotation_date=datetime.now(UTC),
            status=QuotationStatus.DRAFT,
            grand_total=Decimal("1000.00"),
            currency="INR",
        )
        db_session.add(quotation)
        db_session.commit()
        db_session.refresh(quotation)
        
        # Store initial timestamps
        initial_created_at = quotation.created_at
        initial_updated_at = quotation.updated_at
        
        # Wait a small amount to ensure timestamp difference
        time.sleep(0.1)
        
        # Modify quotation
        quotation.grand_total = Decimal("2000.00")
        db_session.commit()
        db_session.refresh(quotation)
        
        # Verify updated_at changed but created_at did not
        assert quotation.created_at == initial_created_at
        assert quotation.updated_at > initial_updated_at
        
    def test_quotation_submitted_at_set_on_status_transition_to_sent(
        self, db_session, sample_organization, sample_customer, sample_item
    ):
        """Test that submitted_at is set when quotation status changes to SENT"""
        # Create quotation in DRAFT status
        quotation = Quotation(
            organization_id=sample_organization.id,
            quotation_no="QTN-TEST-003",
            customer_id=sample_customer.id,
            quotation_date=datetime.now(UTC),
            status=QuotationStatus.DRAFT,
            grand_total=Decimal("1000.00"),
            currency="INR",
        )
        db_session.add(quotation)
        db_session.commit()
        db_session.refresh(quotation)
        
        # Verify submitted_at is initially None
        assert quotation.submitted_at is None
        
        # Change status to SENT
        quotation.status = QuotationStatus.SENT
        quotation.submitted_at = datetime.now(UTC)
        db_session.commit()
        db_session.refresh(quotation)
        
        # Verify submitted_at is set
        assert quotation.submitted_at is not None
        assert isinstance(quotation.submitted_at, datetime)
        
    def test_sales_order_created_at_set_on_creation(
        self, db_session, sample_organization, sample_customer, sample_item
    ):
        """Test that created_at is automatically set when creating a sales order"""
        # Create sales order
        sales_order = SalesOrder(
            organization_id=sample_organization.id,
            sales_order_no="SO-TEST-001",
            customer_id=sample_customer.id,
            order_date=datetime.now(UTC),
            status=SalesOrderStatus.DRAFT,
            grand_total=Decimal("1000.00"),
            currency="INR",
        )
        db_session.add(sales_order)
        db_session.commit()
        db_session.refresh(sales_order)
        
        # Verify created_at is set
        assert sales_order.created_at is not None
        assert isinstance(sales_order.created_at, datetime)
        
    def test_sales_order_updated_at_updated_on_modification(
        self, db_session, sample_organization, sample_customer, sample_item
    ):
        """Test that updated_at is automatically updated when modifying a sales order"""
        # Create sales order
        sales_order = SalesOrder(
            organization_id=sample_organization.id,
            sales_order_no="SO-TEST-002",
            customer_id=sample_customer.id,
            order_date=datetime.now(UTC),
            status=SalesOrderStatus.DRAFT,
            grand_total=Decimal("1000.00"),
            currency="INR",
        )
        db_session.add(sales_order)
        db_session.commit()
        db_session.refresh(sales_order)
        
        # Store initial timestamps
        initial_created_at = sales_order.created_at
        initial_updated_at = sales_order.updated_at
        
        # Wait a small amount to ensure timestamp difference
        time.sleep(0.1)
        
        # Modify sales order
        sales_order.grand_total = Decimal("2000.00")
        db_session.commit()
        db_session.refresh(sales_order)
        
        # Verify updated_at changed but created_at did not
        assert sales_order.created_at == initial_created_at
        assert sales_order.updated_at > initial_updated_at
        
    def test_sales_order_submitted_at_set_on_status_transition_to_confirmed(
        self, db_session, sample_organization, sample_customer, sample_item
    ):
        """Test that submitted_at is set when sales order status changes to CONFIRMED"""
        # Create sales order in DRAFT status
        sales_order = SalesOrder(
            organization_id=sample_organization.id,
            sales_order_no="SO-TEST-003",
            customer_id=sample_customer.id,
            order_date=datetime.now(UTC),
            status=SalesOrderStatus.DRAFT,
            grand_total=Decimal("1000.00"),
            currency="INR",
        )
        db_session.add(sales_order)
        db_session.commit()
        db_session.refresh(sales_order)
        
        # Verify submitted_at is initially None
        assert sales_order.submitted_at is None
        
        # Change status to CONFIRMED
        sales_order.status = SalesOrderStatus.CONFIRMED
        sales_order.submitted_at = datetime.now(UTC)
        db_session.commit()
        db_session.refresh(sales_order)
        
        # Verify submitted_at is set
        assert sales_order.submitted_at is not None
        assert isinstance(sales_order.submitted_at, datetime)
        
    def test_quotation_item_timestamps(
        self, db_session, sample_organization, sample_customer, sample_item
    ):
        """Test that quotation items also have automatic timestamp management"""
        # Create quotation
        quotation = Quotation(
            organization_id=sample_organization.id,
            quotation_no="QTN-TEST-004",
            customer_id=sample_customer.id,
            quotation_date=datetime.now(UTC),
            status=QuotationStatus.DRAFT,
            grand_total=Decimal("1000.00"),
            currency="INR",
        )
        db_session.add(quotation)
        db_session.commit()
        db_session.refresh(quotation)
        
        # Create quotation item
        item = QuotationItem(
            organization_id=sample_organization.id,
            quotation_id=quotation.id,
            item_id=sample_item.id,
            qty=Decimal("10.000"),
            uom="PCS",
            rate=Decimal("100.00"),
            amount=Decimal("1000.00"),
            sort_order=1,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        
        # Verify timestamps are set
        assert item.created_at is not None
        assert item.updated_at is not None
        assert isinstance(item.created_at, datetime)
        assert isinstance(item.updated_at, datetime)
        
        # Store initial timestamps
        initial_created_at = item.created_at
        initial_updated_at = item.updated_at
        
        # Wait and modify
        time.sleep(0.1)
        item.qty = Decimal("20.000")
        db_session.commit()
        db_session.refresh(item)
        
        # Verify updated_at changed but created_at did not
        assert item.created_at == initial_created_at
        assert item.updated_at > initial_updated_at
        
    def test_sales_order_item_timestamps(
        self, db_session, sample_organization, sample_customer, sample_item
    ):
        """Test that sales order items also have automatic timestamp management"""
        # Create sales order
        sales_order = SalesOrder(
            organization_id=sample_organization.id,
            sales_order_no="SO-TEST-004",
            customer_id=sample_customer.id,
            order_date=datetime.now(UTC),
            status=SalesOrderStatus.DRAFT,
            grand_total=Decimal("1000.00"),
            currency="INR",
        )
        db_session.add(sales_order)
        db_session.commit()
        db_session.refresh(sales_order)
        
        # Create sales order item
        item = SalesOrderItem(
            organization_id=sample_organization.id,
            sales_order_id=sales_order.id,
            item_id=sample_item.id,
            qty=Decimal("10.000"),
            uom="PCS",
            rate=Decimal("100.00"),
            amount=Decimal("1000.00"),
            billed_qty=Decimal("0.000"),
            delivered_qty=Decimal("0.000"),
            sort_order=1,
        )
        db_session.add(item)
        db_session.commit()
        db_session.refresh(item)
        
        # Verify timestamps are set
        assert item.created_at is not None
        assert item.updated_at is not None
        assert isinstance(item.created_at, datetime)
        assert isinstance(item.updated_at, datetime)
        
        # Store initial timestamps
        initial_created_at = item.created_at
        initial_updated_at = item.updated_at
        
        # Wait and modify
        time.sleep(0.1)
        item.billed_qty = Decimal("5.000")
        db_session.commit()
        db_session.refresh(item)
        
        # Verify updated_at changed but created_at did not
        assert item.created_at == initial_created_at
        assert item.updated_at > initial_updated_at
