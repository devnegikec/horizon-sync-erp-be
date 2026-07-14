"""Sales Order repository tests"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.base import SalesOrderStatus
from app.models.sales_order import SalesOrderItem
from app.repositories.sales_order_repository import SalesOrderRepository


@pytest.fixture
def sales_order_repo(db_session):
    """Create a sales order repository instance"""
    return SalesOrderRepository(db_session)


@pytest.fixture
def test_sales_order_data(mock_current_user):
    """Sample sales order data for testing"""
    return {
        "organization_id": mock_current_user.organization_id,
        "sales_order_no": "SO-2024-001",
        "customer_id": uuid.uuid4(),
        "order_date": datetime.now(UTC),
        "delivery_date": None,
        "status": SalesOrderStatus.DRAFT,
        "grand_total": Decimal("1000.00"),
        "currency": "INR",
        "reference_type": None,
        "reference_id": None,
        "remarks": "Test sales order",
        "created_by": mock_current_user.id,
        "updated_by": mock_current_user.id,
    }


@pytest.fixture
def test_sales_order_item_data(mock_current_user):
    """Sample sales order item data for testing"""
    return {
        "organization_id": mock_current_user.organization_id,
        "item_id": uuid.uuid4(),
        "qty": Decimal("10.000"),
        "uom": "Nos",
        "rate": Decimal("100.00"),
        "amount": Decimal("1000.00"),
        "billed_qty": Decimal("0.000"),
        "delivered_qty": Decimal("0.000"),
        "sort_order": 0,
    }


class TestSalesOrderRepositoryCreate:
    """Tests for SalesOrderRepository.create"""

    def test_create_sales_order_success(self, sales_order_repo, test_sales_order_data):
        """Test creating a sales order successfully"""
        sales_order = sales_order_repo.create(test_sales_order_data)

        assert sales_order.id is not None
        assert sales_order.sales_order_no == test_sales_order_data["sales_order_no"]
        assert sales_order.organization_id == test_sales_order_data["organization_id"]
        assert sales_order.status == SalesOrderStatus.DRAFT
        assert sales_order.grand_total == Decimal("1000.00")
        assert sales_order.created_at is not None
        assert sales_order.updated_at is not None


class TestSalesOrderRepositoryGetById:
    """Tests for SalesOrderRepository.get_by_id"""

    def test_get_by_id_success(
        self, sales_order_repo, test_sales_order_data, mock_current_user
    ):
        """Test getting a sales order by ID"""
        sales_order = sales_order_repo.create(test_sales_order_data)

        retrieved = sales_order_repo.get_by_id(
            sales_order.id, mock_current_user.organization_id
        )

        assert retrieved is not None
        assert retrieved.id == sales_order.id
        assert retrieved.sales_order_no == test_sales_order_data["sales_order_no"]

    def test_get_by_id_not_found(self, sales_order_repo, mock_current_user):
        """Test getting a non-existent sales order"""
        fake_id = uuid.uuid4()
        retrieved = sales_order_repo.get_by_id(
            fake_id, mock_current_user.organization_id
        )

        assert retrieved is None

    def test_get_by_id_wrong_organization(
        self, sales_order_repo, test_sales_order_data, mock_current_user
    ):
        """Test getting a sales order from different organization"""
        sales_order = sales_order_repo.create(test_sales_order_data)

        # Try to get with different organization_id
        wrong_org_id = uuid.uuid4()
        retrieved = sales_order_repo.get_by_id(sales_order.id, wrong_org_id)

        assert retrieved is None


class TestSalesOrderRepositoryGetByIdWithItems:
    """Tests for SalesOrderRepository.get_by_id_with_items"""

    def test_get_by_id_with_items_success(
        self,
        sales_order_repo,
        test_sales_order_data,
        test_sales_order_item_data,
        mock_current_user,
        db_session,
    ):
        """Test getting a sales order with items"""
        sales_order = sales_order_repo.create(test_sales_order_data)

        # Add an item
        test_sales_order_item_data["sales_order_id"] = sales_order.id
        item = SalesOrderItem(**test_sales_order_item_data)
        db_session.add(item)
        db_session.commit()

        retrieved = sales_order_repo.get_by_id_with_items(
            sales_order.id, mock_current_user.organization_id
        )

        assert retrieved is not None
        assert retrieved.id == sales_order.id
        assert len(retrieved.items) == 1
        assert retrieved.items[0].qty == Decimal("10.000")
        assert retrieved.items[0].billed_qty == Decimal("0.000")
        assert retrieved.items[0].delivered_qty == Decimal("0.000")

    def test_get_by_id_with_items_not_found(self, sales_order_repo, mock_current_user):
        """Test getting a non-existent sales order with items"""
        fake_id = uuid.uuid4()
        retrieved = sales_order_repo.get_by_id_with_items(
            fake_id, mock_current_user.organization_id
        )

        assert retrieved is None


class TestSalesOrderRepositoryList:
    """Tests for SalesOrderRepository.list_sales_orders"""

    def test_list_sales_orders_empty(self, sales_order_repo, mock_current_user):
        """Test listing sales orders when none exist"""
        sales_orders, total = sales_order_repo.list_sales_orders(
            mock_current_user.organization_id
        )

        assert sales_orders == []
        assert total == 0

    def test_list_sales_orders_with_data(
        self, sales_order_repo, test_sales_order_data, mock_current_user
    ):
        """Test listing sales orders with data"""
        sales_order_repo.create(test_sales_order_data)

        sales_orders, total = sales_order_repo.list_sales_orders(
            mock_current_user.organization_id
        )

        assert len(sales_orders) == 1
        assert total == 1
        assert sales_orders[0].sales_order_no == test_sales_order_data["sales_order_no"]

    def test_list_sales_orders_filter_by_customer(
        self, sales_order_repo, test_sales_order_data, mock_current_user
    ):
        """Test filtering sales orders by customer_id"""
        customer_id = uuid.uuid4()
        test_sales_order_data["customer_id"] = customer_id
        sales_order_repo.create(test_sales_order_data)

        # Create another sales order with different customer
        other_data = test_sales_order_data.copy()
        other_data["sales_order_no"] = "SO-2024-002"
        other_data["customer_id"] = uuid.uuid4()
        sales_order_repo.create(other_data)

        sales_orders, total = sales_order_repo.list_sales_orders(
            mock_current_user.organization_id, customer_id=customer_id
        )

        assert len(sales_orders) == 1
        assert total == 1
        assert sales_orders[0].customer_id == customer_id

    def test_list_sales_orders_filter_by_status(
        self, sales_order_repo, test_sales_order_data, mock_current_user
    ):
        """Test filtering sales orders by status"""
        sales_order_repo.create(test_sales_order_data)

        # Create another sales order with different status
        other_data = test_sales_order_data.copy()
        other_data["sales_order_no"] = "SO-2024-002"
        other_data["status"] = SalesOrderStatus.CONFIRMED
        sales_order_repo.create(other_data)

        sales_orders, total = sales_order_repo.list_sales_orders(
            mock_current_user.organization_id, status=SalesOrderStatus.DRAFT.value
        )

        assert len(sales_orders) == 1
        assert total == 1
        assert sales_orders[0].status == SalesOrderStatus.DRAFT

    def test_list_sales_orders_pagination(
        self, sales_order_repo, test_sales_order_data, mock_current_user
    ):
        """Test pagination"""
        # Create multiple sales orders
        for i in range(5):
            data = test_sales_order_data.copy()
            data["sales_order_no"] = f"SO-2024-{i:03d}"
            sales_order_repo.create(data)

        sales_orders, total = sales_order_repo.list_sales_orders(
            mock_current_user.organization_id, page=1, page_size=2
        )

        assert len(sales_orders) == 2
        assert total == 5

    def test_list_sales_orders_sorting(
        self, sales_order_repo, test_sales_order_data, mock_current_user
    ):
        """Test sorting"""
        # Create sales orders with different dates
        for i in range(3):
            data = test_sales_order_data.copy()
            data["sales_order_no"] = f"SO-2024-{i:03d}"
            sales_order_repo.create(data)

        # Test descending order (default)
        sales_orders_desc, _ = sales_order_repo.list_sales_orders(
            mock_current_user.organization_id, sort_by="order_date", sort_order="desc"
        )

        # Test ascending order
        sales_orders_asc, _ = sales_order_repo.list_sales_orders(
            mock_current_user.organization_id, sort_by="order_date", sort_order="asc"
        )

        assert len(sales_orders_desc) == 3
        assert len(sales_orders_asc) == 3


class TestSalesOrderRepositoryUpdate:
    """Tests for SalesOrderRepository.update"""

    def test_update_sales_order_success(
        self, sales_order_repo, test_sales_order_data, mock_current_user
    ):
        """Test updating a sales order"""
        sales_order = sales_order_repo.create(test_sales_order_data)

        update_data = {
            "remarks": "Updated remarks",
            "grand_total": Decimal("2000.00"),
            "status": SalesOrderStatus.CONFIRMED,
        }

        updated = sales_order_repo.update(sales_order, update_data)

        assert updated.remarks == "Updated remarks"
        assert updated.grand_total == Decimal("2000.00")
        assert updated.status == SalesOrderStatus.CONFIRMED


class TestSalesOrderRepositoryDelete:
    """Tests for SalesOrderRepository.delete"""

    def test_delete_sales_order_success(
        self, sales_order_repo, test_sales_order_data, mock_current_user
    ):
        """Test deleting a sales order"""
        sales_order = sales_order_repo.create(test_sales_order_data)
        sales_order_id = sales_order.id

        sales_order_repo.delete(sales_order)

        # Verify it's deleted
        retrieved = sales_order_repo.get_by_id(
            sales_order_id, mock_current_user.organization_id
        )
        assert retrieved is None

    def test_delete_sales_order_cascades_to_items(
        self,
        sales_order_repo,
        test_sales_order_data,
        test_sales_order_item_data,
        mock_current_user,
        db_session,
    ):
        """Test that deleting a sales order cascades to items"""
        sales_order = sales_order_repo.create(test_sales_order_data)

        # Add an item
        test_sales_order_item_data["sales_order_id"] = sales_order.id
        item = SalesOrderItem(**test_sales_order_item_data)
        db_session.add(item)
        db_session.commit()
        item_id = item.id

        # Delete the sales order
        sales_order_repo.delete(sales_order)

        # Verify the item is also deleted
        deleted_item = (
            db_session.query(SalesOrderItem)
            .filter(SalesOrderItem.id == item_id)
            .first()
        )
        assert deleted_item is None


class TestSalesOrderRepositoryUpdateItemBilledQty:
    """Tests for SalesOrderRepository.update_item_billed_qty"""

    def test_update_item_billed_qty_success(
        self,
        sales_order_repo,
        test_sales_order_data,
        test_sales_order_item_data,
        mock_current_user,
        db_session,
    ):
        """Test updating item billed quantity"""
        sales_order = sales_order_repo.create(test_sales_order_data)

        # Add an item
        test_sales_order_item_data["sales_order_id"] = sales_order.id
        item = SalesOrderItem(**test_sales_order_item_data)
        db_session.add(item)
        db_session.commit()
        item_id = item.id

        # Update billed quantity
        sales_order_repo.update_item_billed_qty(item_id, Decimal("5.000"))

        # Verify the update
        updated_item = (
            db_session.query(SalesOrderItem)
            .filter(SalesOrderItem.id == item_id)
            .first()
        )
        assert updated_item.billed_qty == Decimal("5.000")

    def test_update_item_billed_qty_incremental(
        self,
        sales_order_repo,
        test_sales_order_data,
        test_sales_order_item_data,
        mock_current_user,
        db_session,
    ):
        """Test incrementally updating item billed quantity"""
        sales_order = sales_order_repo.create(test_sales_order_data)

        # Add an item
        test_sales_order_item_data["sales_order_id"] = sales_order.id
        item = SalesOrderItem(**test_sales_order_item_data)
        db_session.add(item)
        db_session.commit()
        item_id = item.id

        # Update billed quantity twice
        sales_order_repo.update_item_billed_qty(item_id, Decimal("3.000"))
        sales_order_repo.update_item_billed_qty(item_id, Decimal("2.000"))

        # Verify the cumulative update
        updated_item = (
            db_session.query(SalesOrderItem)
            .filter(SalesOrderItem.id == item_id)
            .first()
        )
        assert updated_item.billed_qty == Decimal("5.000")

    def test_update_item_billed_qty_nonexistent_item(self, sales_order_repo):
        """Test updating billed quantity for non-existent item"""
        fake_id = uuid.uuid4()
        # Should not raise an error, just do nothing
        sales_order_repo.update_item_billed_qty(fake_id, Decimal("5.000"))


class TestSalesOrderRepositoryUpdateItemDeliveredQty:
    """Tests for SalesOrderRepository.update_item_delivered_qty"""

    def test_update_item_delivered_qty_success(
        self,
        sales_order_repo,
        test_sales_order_data,
        test_sales_order_item_data,
        mock_current_user,
        db_session,
    ):
        """Test updating item delivered quantity"""
        sales_order = sales_order_repo.create(test_sales_order_data)

        # Add an item
        test_sales_order_item_data["sales_order_id"] = sales_order.id
        item = SalesOrderItem(**test_sales_order_item_data)
        db_session.add(item)
        db_session.commit()
        item_id = item.id

        # Update delivered quantity
        sales_order_repo.update_item_delivered_qty(item_id, Decimal("7.000"))

        # Verify the update
        updated_item = (
            db_session.query(SalesOrderItem)
            .filter(SalesOrderItem.id == item_id)
            .first()
        )
        assert updated_item.delivered_qty == Decimal("7.000")

    def test_update_item_delivered_qty_incremental(
        self,
        sales_order_repo,
        test_sales_order_data,
        test_sales_order_item_data,
        mock_current_user,
        db_session,
    ):
        """Test incrementally updating item delivered quantity"""
        sales_order = sales_order_repo.create(test_sales_order_data)

        # Add an item
        test_sales_order_item_data["sales_order_id"] = sales_order.id
        item = SalesOrderItem(**test_sales_order_item_data)
        db_session.add(item)
        db_session.commit()
        item_id = item.id

        # Update delivered quantity twice
        sales_order_repo.update_item_delivered_qty(item_id, Decimal("4.000"))
        sales_order_repo.update_item_delivered_qty(item_id, Decimal("3.000"))

        # Verify the cumulative update
        updated_item = (
            db_session.query(SalesOrderItem)
            .filter(SalesOrderItem.id == item_id)
            .first()
        )
        assert updated_item.delivered_qty == Decimal("7.000")

    def test_update_item_delivered_qty_nonexistent_item(self, sales_order_repo):
        """Test updating delivered quantity for non-existent item"""
        fake_id = uuid.uuid4()
        # Should not raise an error, just do nothing
        sales_order_repo.update_item_delivered_qty(fake_id, Decimal("5.000"))
