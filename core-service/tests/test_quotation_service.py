"""Tests for QuotationService"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.exceptions import ResourceNotFoundException
from app.models.base import QuotationStatus, CustomerStatus, ItemStatus, ItemType, ValuationMethod
from app.models.customer import Customer
from app.models.item import Item
from app.services.quotation_service import QuotationService


@pytest.fixture
def quotation_service(db_session):
    """Create a QuotationService instance"""
    return QuotationService(db_session)


@pytest.fixture
def test_customer(db_session, mock_current_user):
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
def test_items(db_session, mock_current_user):
    """Create test items in the database"""
    items = []
    for i in range(2):
        item = Item(
            id=uuid.uuid4(),
            organization_id=mock_current_user.organization_id,
            item_code=f"ITEM-{i+1:03d}",
            item_name=f"Test Item {i+1}",
            item_type=ItemType.STOCK,
            uom="Nos" if i == 0 else "Kg",
            status=ItemStatus.ACTIVE,
            valuation_method=ValuationMethod.FIFO,
        )
        db_session.add(item)
        items.append(item)
    db_session.commit()
    for item in items:
        db_session.refresh(item)
    return items


@pytest.fixture
def test_quotation_data(mock_current_user, test_customer, test_items):
    """Sample quotation data for testing"""
    return {
        "quotation_no": "QTN-2024-001",
        "customer_id": test_customer.id,
        "quotation_date": datetime.now(UTC),
        "valid_until": datetime.now(UTC),
        "currency": "INR",
        "remarks": "Test quotation",
        "items": [
            {
                "item_id": test_items[0].id,
                "qty": Decimal("10.000"),
                "uom": "Nos",
                "rate": Decimal("100.00"),
                "sort_order": 0,
            },
            {
                "item_id": test_items[1].id,
                "qty": Decimal("5.000"),
                "uom": "Kg",
                "rate": Decimal("200.00"),
                "sort_order": 1,
            },
        ],
    }


class TestQuotationServiceCreate:
    """Tests for QuotationService.create"""

    def test_create_quotation_success(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test creating a quotation successfully"""
        result = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        assert result["id"] is not None
        assert result["organization_id"] == mock_current_user.organization_id
        assert result["quotation_no"] == test_quotation_data["quotation_no"]
        assert result["customer_id"] == test_quotation_data["customer_id"]
        assert result["status"] == QuotationStatus.DRAFT.value
        assert result["created_by"] == mock_current_user.id
        assert result["updated_by"] == mock_current_user.id
        assert len(result["items"]) == 2

    def test_create_quotation_calculates_grand_total(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that grand_total is calculated correctly from line items"""
        result = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Expected: (10 * 100) + (5 * 200) = 1000 + 1000 = 2000
        expected_total = Decimal("2000.00")
        assert Decimal(str(result["grand_total"])) == expected_total

    def test_create_quotation_calculates_item_amounts(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that line item amounts are calculated as qty * rate"""
        result = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        items = result["items"]
        assert Decimal(str(items[0]["amount"])) == Decimal("1000.00")  # 10 * 100
        assert Decimal(str(items[1]["amount"])) == Decimal("1000.00")  # 5 * 200

    def test_create_quotation_without_items(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test creating a quotation without items"""
        data = dict(test_quotation_data)
        data["items"] = []

        result = quotation_service.create(
            data, mock_current_user.organization_id, mock_current_user.id
        )

        assert result["grand_total"] == Decimal("0")
        assert len(result["items"]) == 0


class TestQuotationServiceGetById:
    """Tests for QuotationService.get_by_id"""

    def test_get_by_id_success(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test getting a quotation by ID"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        result = quotation_service.get_by_id(
            created["id"], mock_current_user.organization_id
        )

        assert result["id"] == created["id"]
        assert result["quotation_no"] == test_quotation_data["quotation_no"]
        assert len(result["items"]) == 2

    def test_get_by_id_not_found(self, quotation_service, mock_current_user):
        """Test getting a non-existent quotation raises exception"""
        fake_id = uuid.uuid4()

        with pytest.raises(ResourceNotFoundException):
            quotation_service.get_by_id(fake_id, mock_current_user.organization_id)


class TestQuotationServiceGetList:
    """Tests for QuotationService.get_list"""

    def test_get_list_empty(self, quotation_service, mock_current_user):
        """Test getting list when no quotations exist"""
        items, pagination = quotation_service.get_list(
            mock_current_user.organization_id
        )

        assert len(items) == 0
        assert pagination["total_items"] == 0

    def test_get_list_with_data(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test getting list with quotations"""
        quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        items, pagination = quotation_service.get_list(
            mock_current_user.organization_id
        )

        assert len(items) == 1
        assert pagination["total_items"] == 1
        assert items[0]["quotation_no"] == test_quotation_data["quotation_no"]


class TestQuotationServiceUpdate:
    """Tests for QuotationService.update"""

    def test_update_quotation_success(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test updating a quotation"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        update_data = {"remarks": "Updated remarks"}
        result = quotation_service.update(
            created["id"],
            update_data,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        assert result["remarks"] == "Updated remarks"
        assert result["updated_by"] == mock_current_user.id

    def test_update_quotation_with_items(
        self, quotation_service, test_quotation_data, test_items, mock_current_user
    ):
        """Test updating quotation with new items recalculates grand_total"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        new_items = [
            {
                "item_id": test_items[0].id,  # Use existing item from fixture
                "qty": Decimal("20.000"),
                "uom": "Nos",
                "rate": Decimal("50.00"),
                "sort_order": 0,
            }
        ]
        update_data = {"items": new_items}

        result = quotation_service.update(
            created["id"],
            update_data,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # Expected: 20 * 50 = 1000
        assert Decimal(str(result["grand_total"])) == Decimal("1000.00")
        assert len(result["items"]) == 1

    def test_update_quotation_not_found(self, quotation_service, mock_current_user):
        """Test updating a non-existent quotation raises exception"""
        fake_id = uuid.uuid4()

        with pytest.raises(ResourceNotFoundException):
            quotation_service.update(
                fake_id, {}, mock_current_user.organization_id, mock_current_user.id
            )


class TestQuotationServiceDelete:
    """Tests for QuotationService.delete"""

    def test_delete_quotation_success(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test deleting a quotation"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        quotation_service.delete(created["id"], mock_current_user.organization_id)

        with pytest.raises(ResourceNotFoundException):
            quotation_service.get_by_id(
                created["id"], mock_current_user.organization_id
            )

    def test_delete_quotation_not_found(self, quotation_service, mock_current_user):
        """Test deleting a non-existent quotation raises exception"""
        fake_id = uuid.uuid4()

        with pytest.raises(ResourceNotFoundException):
            quotation_service.delete(fake_id, mock_current_user.organization_id)


class TestQuotationServiceStatusTransition:
    """Tests for QuotationService._validate_status_transition"""

    def test_valid_transition_draft_to_sent(self, quotation_service):
        """Test valid transition from DRAFT to SENT"""
        # Should not raise any exception
        quotation_service._validate_status_transition(
            QuotationStatus.DRAFT, QuotationStatus.SENT
        )

    def test_valid_transition_sent_to_accepted(self, quotation_service):
        """Test valid transition from SENT to ACCEPTED"""
        quotation_service._validate_status_transition(
            QuotationStatus.SENT, QuotationStatus.ACCEPTED
        )

    def test_valid_transition_sent_to_rejected(self, quotation_service):
        """Test valid transition from SENT to REJECTED"""
        quotation_service._validate_status_transition(
            QuotationStatus.SENT, QuotationStatus.REJECTED
        )

    def test_valid_transition_sent_to_expired(self, quotation_service):
        """Test valid transition from SENT to EXPIRED"""
        quotation_service._validate_status_transition(
            QuotationStatus.SENT, QuotationStatus.EXPIRED
        )

    def test_invalid_transition_draft_to_accepted(self, quotation_service):
        """Test invalid transition from DRAFT to ACCEPTED"""
        with pytest.raises(ValueError, match="Invalid status transition"):
            quotation_service._validate_status_transition(
                QuotationStatus.DRAFT, QuotationStatus.ACCEPTED
            )

    def test_invalid_transition_draft_to_rejected(self, quotation_service):
        """Test invalid transition from DRAFT to REJECTED"""
        with pytest.raises(ValueError, match="Invalid status transition"):
            quotation_service._validate_status_transition(
                QuotationStatus.DRAFT, QuotationStatus.REJECTED
            )

    def test_invalid_transition_draft_to_expired(self, quotation_service):
        """Test invalid transition from DRAFT to EXPIRED"""
        with pytest.raises(ValueError, match="Invalid status transition"):
            quotation_service._validate_status_transition(
                QuotationStatus.DRAFT, QuotationStatus.EXPIRED
            )

    def test_terminal_state_accepted_cannot_transition(self, quotation_service):
        """Test that ACCEPTED terminal state cannot transition"""
        with pytest.raises(
            ValueError, match="Cannot change status from terminal state"
        ):
            quotation_service._validate_status_transition(
                QuotationStatus.ACCEPTED, QuotationStatus.SENT
            )

    def test_terminal_state_rejected_cannot_transition(self, quotation_service):
        """Test that REJECTED terminal state cannot transition"""
        with pytest.raises(
            ValueError, match="Cannot change status from terminal state"
        ):
            quotation_service._validate_status_transition(
                QuotationStatus.REJECTED, QuotationStatus.SENT
            )

    def test_terminal_state_expired_cannot_transition(self, quotation_service):
        """Test that EXPIRED terminal state cannot transition"""
        with pytest.raises(
            ValueError, match="Cannot change status from terminal state"
        ):
            quotation_service._validate_status_transition(
                QuotationStatus.EXPIRED, QuotationStatus.SENT
            )

    def test_invalid_transition_sent_to_draft(self, quotation_service):
        """Test invalid backward transition from SENT to DRAFT"""
        with pytest.raises(ValueError, match="Invalid status transition"):
            quotation_service._validate_status_transition(
                QuotationStatus.SENT, QuotationStatus.DRAFT
            )


class TestQuotationServiceUpdateStatus:
    """Tests for QuotationService.update_status"""

    def test_update_status_draft_to_sent(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test updating status from DRAFT to SENT"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        result = quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        assert result["status"] == QuotationStatus.SENT.value
        assert result["submitted_at"] is not None

    def test_update_status_sent_to_accepted(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test updating status from SENT to ACCEPTED"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # First transition to SENT
        quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # Then transition to ACCEPTED
        result = quotation_service.update_status(
            created["id"],
            QuotationStatus.ACCEPTED.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        assert result["status"] == QuotationStatus.ACCEPTED.value

    def test_update_status_invalid_transition(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that invalid status transition raises ValueError"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        with pytest.raises(ValueError, match="Invalid status transition"):
            quotation_service.update_status(
                created["id"],
                QuotationStatus.ACCEPTED.value,
                mock_current_user.organization_id,
                mock_current_user.id,
            )

    def test_update_status_terminal_state(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that terminal state cannot transition"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Transition to SENT then ACCEPTED
        quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )
        quotation_service.update_status(
            created["id"],
            QuotationStatus.ACCEPTED.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # Try to transition from ACCEPTED (terminal state)
        with pytest.raises(
            ValueError, match="Cannot change status from terminal state"
        ):
            quotation_service.update_status(
                created["id"],
                QuotationStatus.SENT.value,
                mock_current_user.organization_id,
                mock_current_user.id,
            )

    def test_update_status_not_found(self, quotation_service, mock_current_user):
        """Test updating status of non-existent quotation raises exception"""
        fake_id = uuid.uuid4()

        with pytest.raises(ResourceNotFoundException):
            quotation_service.update_status(
                fake_id,
                QuotationStatus.SENT.value,
                mock_current_user.organization_id,
                mock_current_user.id,
            )

    def test_update_status_sets_submitted_at_only_once(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that submitted_at is set when transitioning to SENT and not changed on subsequent updates"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # First transition to SENT
        result1 = quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )
        first_submitted_at = result1["submitted_at"]
        assert first_submitted_at is not None

        # Transition to ACCEPTED
        result2 = quotation_service.update_status(
            created["id"],
            QuotationStatus.ACCEPTED.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # submitted_at should remain the same
        assert result2["submitted_at"] == first_submitted_at


class TestQuotationServiceSentImmutability:
    """Tests for preventing line item modifications when status is SENT"""

    def test_cannot_modify_items_when_sent(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that line items cannot be modified when quotation status is SENT"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Transition to SENT
        quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # Try to update items
        new_items = [
            {
                "item_id": uuid.uuid4(),
                "qty": Decimal("5.000"),
                "uom": "Nos",
                "rate": Decimal("100.00"),
                "sort_order": 0,
            }
        ]

        with pytest.raises(
            ValueError, match="Cannot modify line items when quotation status is SENT"
        ):
            quotation_service.update(
                created["id"],
                {"items": new_items},
                mock_current_user.organization_id,
                mock_current_user.id,
            )

    def test_can_modify_other_fields_when_sent(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that non-item fields can be modified when quotation status is SENT"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Transition to SENT
        quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # Update remarks (non-item field)
        result = quotation_service.update(
            created["id"],
            {"remarks": "Updated remarks after sending"},
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        assert result["remarks"] == "Updated remarks after sending"
        assert result["status"] == QuotationStatus.SENT.value

    def test_can_modify_items_when_draft(
        self, quotation_service, test_quotation_data, test_items, mock_current_user
    ):
        """Test that line items can be modified when quotation status is DRAFT"""
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Update items while in DRAFT status
        new_items = [
            {
                "item_id": test_items[0].id,  # Use existing item from fixture
                "qty": Decimal("5.000"),
                "uom": "Nos",
                "rate": Decimal("100.00"),
                "sort_order": 0,
            }
        ]

        result = quotation_service.update(
            created["id"],
            {"items": new_items},
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        assert len(result["items"]) == 1
        assert result["status"] == QuotationStatus.DRAFT.value


class TestQuotationServiceConvertToSalesOrder:
    """Tests for QuotationService.convert_to_sales_order"""

    def test_convert_accepted_quotation_to_sales_order(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test converting an ACCEPTED quotation to sales order"""
        # Create quotation
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Transition to SENT then ACCEPTED
        quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )
        quotation_service.update_status(
            created["id"],
            QuotationStatus.ACCEPTED.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # Convert to sales order
        sales_order = quotation_service.convert_to_sales_order(
            created["id"], mock_current_user.organization_id, mock_current_user.id
        )

        # Verify sales order fields
        assert sales_order["id"] is not None
        assert sales_order["customer_id"] == created["customer_id"]
        assert sales_order["currency"] == created["currency"]
        assert sales_order["remarks"] == created["remarks"]
        assert sales_order["reference_type"] == "Quotation"
        assert sales_order["reference_id"] == created["id"]
        assert sales_order["status"] == "draft"
        assert sales_order["order_date"] is not None
        assert sales_order["delivery_date"] is None

    def test_convert_preserves_line_items(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that line items are preserved during conversion"""
        # Create quotation
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Transition to ACCEPTED
        quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )
        quotation_service.update_status(
            created["id"],
            QuotationStatus.ACCEPTED.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # Convert to sales order
        sales_order = quotation_service.convert_to_sales_order(
            created["id"], mock_current_user.organization_id, mock_current_user.id
        )

        # Verify line items
        assert len(sales_order["items"]) == len(created["items"])
        for i, item in enumerate(sales_order["items"]):
            original_item = created["items"][i]
            assert item["item_id"] == original_item["item_id"]
            assert Decimal(str(item["qty"])) == Decimal(str(original_item["qty"]))
            assert item["uom"] == original_item["uom"]
            assert Decimal(str(item["rate"])) == Decimal(str(original_item["rate"]))
            assert Decimal(str(item["amount"])) == Decimal(str(original_item["amount"]))
            assert item["sort_order"] == original_item["sort_order"]

    def test_convert_initializes_billed_and_delivered_qty(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that billed_qty and delivered_qty are initialized to 0"""
        # Create quotation
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Transition to ACCEPTED
        quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )
        quotation_service.update_status(
            created["id"],
            QuotationStatus.ACCEPTED.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # Convert to sales order
        sales_order = quotation_service.convert_to_sales_order(
            created["id"], mock_current_user.organization_id, mock_current_user.id
        )

        # Verify quantities are initialized
        for item in sales_order["items"]:
            assert Decimal(str(item["billed_qty"])) == Decimal("0")
            assert Decimal(str(item["delivered_qty"])) == Decimal("0")

    def test_convert_non_accepted_quotation_fails(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that only ACCEPTED quotations can be converted"""
        # Create quotation in DRAFT status
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Try to convert DRAFT quotation
        with pytest.raises(
            ValueError, match="Only ACCEPTED quotations can be converted"
        ):
            quotation_service.convert_to_sales_order(
                created["id"], mock_current_user.organization_id, mock_current_user.id
            )

    def test_convert_sent_quotation_fails(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that SENT quotations cannot be converted"""
        # Create quotation
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Transition to SENT
        quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # Try to convert SENT quotation
        with pytest.raises(
            ValueError, match="Only ACCEPTED quotations can be converted"
        ):
            quotation_service.convert_to_sales_order(
                created["id"], mock_current_user.organization_id, mock_current_user.id
            )

    def test_convert_rejected_quotation_fails(
        self, quotation_service, test_quotation_data, mock_current_user
    ):
        """Test that REJECTED quotations cannot be converted"""
        # Create quotation
        created = quotation_service.create(
            test_quotation_data, mock_current_user.organization_id, mock_current_user.id
        )

        # Transition to SENT then REJECTED
        quotation_service.update_status(
            created["id"],
            QuotationStatus.SENT.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )
        quotation_service.update_status(
            created["id"],
            QuotationStatus.REJECTED.value,
            mock_current_user.organization_id,
            mock_current_user.id,
        )

        # Try to convert REJECTED quotation
        with pytest.raises(
            ValueError, match="Only ACCEPTED quotations can be converted"
        ):
            quotation_service.convert_to_sales_order(
                created["id"], mock_current_user.organization_id, mock_current_user.id
            )

    def test_convert_not_found_quotation_fails(
        self, quotation_service, mock_current_user
    ):
        """Test that converting non-existent quotation raises exception"""
        fake_id = uuid.uuid4()

        with pytest.raises(ResourceNotFoundException):
            quotation_service.convert_to_sales_order(
                fake_id, mock_current_user.organization_id, mock_current_user.id
            )
