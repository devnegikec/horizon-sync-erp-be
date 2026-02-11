"""Quotation repository tests"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.models.base import QuotationStatus
from app.models.quotation import Quotation, QuotationItem
from app.repositories.quotation_repository import QuotationRepository


@pytest.fixture
def quotation_repo(db_session):
    """Create a quotation repository instance"""
    return QuotationRepository(db_session)


@pytest.fixture
def test_quotation_data(mock_current_user):
    """Sample quotation data for testing"""
    return {
        "organization_id": mock_current_user.organization_id,
        "quotation_no": "QTN-2024-001",
        "customer_id": uuid.uuid4(),
        "quotation_date": datetime.now(UTC),
        "valid_until": datetime.now(UTC),
        "status": QuotationStatus.DRAFT,
        "grand_total": Decimal("1000.00"),
        "currency": "INR",
        "remarks": "Test quotation",
        "created_by": mock_current_user.id,
        "updated_by": mock_current_user.id,
    }


class TestQuotationRepositoryCreate:
    """Tests for QuotationRepository.create"""

    def test_create_quotation_success(self, quotation_repo, test_quotation_data):
        """Test creating a quotation successfully"""
        quotation = quotation_repo.create(test_quotation_data)

        assert quotation.id is not None
        assert quotation.quotation_no == test_quotation_data["quotation_no"]
        assert quotation.organization_id == test_quotation_data["organization_id"]
        assert quotation.status == QuotationStatus.DRAFT
        assert quotation.grand_total == Decimal("1000.00")
        assert quotation.created_at is not None
        assert quotation.updated_at is not None


class TestQuotationRepositoryGetById:
    """Tests for QuotationRepository.get_by_id"""

    def test_get_by_id_success(
        self, quotation_repo, test_quotation_data, mock_current_user
    ):
        """Test getting a quotation by ID"""
        quotation = quotation_repo.create(test_quotation_data)

        retrieved = quotation_repo.get_by_id(
            quotation.id, mock_current_user.organization_id
        )

        assert retrieved is not None
        assert retrieved.id == quotation.id
        assert retrieved.quotation_no == test_quotation_data["quotation_no"]

    def test_get_by_id_not_found(self, quotation_repo, mock_current_user):
        """Test getting a non-existent quotation"""
        fake_id = uuid.uuid4()
        retrieved = quotation_repo.get_by_id(fake_id, mock_current_user.organization_id)

        assert retrieved is None

    def test_get_by_id_wrong_organization(
        self, quotation_repo, test_quotation_data, mock_current_user
    ):
        """Test getting a quotation from different organization"""
        quotation = quotation_repo.create(test_quotation_data)

        # Try to get with different organization_id
        wrong_org_id = uuid.uuid4()
        retrieved = quotation_repo.get_by_id(quotation.id, wrong_org_id)

        assert retrieved is None


class TestQuotationRepositoryList:
    """Tests for QuotationRepository.list_quotations"""

    def test_list_quotations_empty(self, quotation_repo, mock_current_user):
        """Test listing quotations when none exist"""
        quotations, total = quotation_repo.list_quotations(
            mock_current_user.organization_id
        )

        assert quotations == []
        assert total == 0

    def test_list_quotations_with_data(
        self, quotation_repo, test_quotation_data, mock_current_user
    ):
        """Test listing quotations with data"""
        quotation_repo.create(test_quotation_data)

        quotations, total = quotation_repo.list_quotations(
            mock_current_user.organization_id
        )

        assert len(quotations) == 1
        assert total == 1
        assert quotations[0].quotation_no == test_quotation_data["quotation_no"]

    def test_list_quotations_filter_by_customer(
        self, quotation_repo, test_quotation_data, mock_current_user
    ):
        """Test filtering quotations by customer_id"""
        customer_id = uuid.uuid4()
        test_quotation_data["customer_id"] = customer_id
        quotation_repo.create(test_quotation_data)

        # Create another quotation with different customer
        other_data = test_quotation_data.copy()
        other_data["quotation_no"] = "QTN-2024-002"
        other_data["customer_id"] = uuid.uuid4()
        quotation_repo.create(other_data)

        quotations, total = quotation_repo.list_quotations(
            mock_current_user.organization_id, customer_id=customer_id
        )

        assert len(quotations) == 1
        assert total == 1
        assert quotations[0].customer_id == customer_id

    def test_list_quotations_filter_by_status(
        self, quotation_repo, test_quotation_data, mock_current_user
    ):
        """Test filtering quotations by status"""
        quotation_repo.create(test_quotation_data)

        # Create another quotation with different status
        other_data = test_quotation_data.copy()
        other_data["quotation_no"] = "QTN-2024-002"
        other_data["status"] = QuotationStatus.SENT
        quotation_repo.create(other_data)

        quotations, total = quotation_repo.list_quotations(
            mock_current_user.organization_id, status=QuotationStatus.DRAFT.value
        )

        assert len(quotations) == 1
        assert total == 1
        assert quotations[0].status == QuotationStatus.DRAFT

    def test_list_quotations_pagination(
        self, quotation_repo, test_quotation_data, mock_current_user
    ):
        """Test pagination"""
        # Create multiple quotations
        for i in range(5):
            data = test_quotation_data.copy()
            data["quotation_no"] = f"QTN-2024-{i:03d}"
            quotation_repo.create(data)

        quotations, total = quotation_repo.list_quotations(
            mock_current_user.organization_id, page=1, page_size=2
        )

        assert len(quotations) == 2
        assert total == 5

    def test_list_quotations_sorting(
        self, quotation_repo, test_quotation_data, mock_current_user
    ):
        """Test sorting"""
        # Create quotations with different dates
        for i in range(3):
            data = test_quotation_data.copy()
            data["quotation_no"] = f"QTN-2024-{i:03d}"
            quotation_repo.create(data)

        # Test descending order (default)
        quotations_desc, _ = quotation_repo.list_quotations(
            mock_current_user.organization_id, sort_by="quotation_date", sort_order="desc"
        )

        # Test ascending order
        quotations_asc, _ = quotation_repo.list_quotations(
            mock_current_user.organization_id, sort_by="quotation_date", sort_order="asc"
        )

        assert len(quotations_desc) == 3
        assert len(quotations_asc) == 3


class TestQuotationRepositoryUpdate:
    """Tests for QuotationRepository.update"""

    def test_update_quotation_success(
        self, quotation_repo, test_quotation_data, mock_current_user
    ):
        """Test updating a quotation"""
        quotation = quotation_repo.create(test_quotation_data)

        update_data = {
            "remarks": "Updated remarks",
            "grand_total": Decimal("2000.00"),
            "status": QuotationStatus.SENT,
        }

        updated = quotation_repo.update(quotation, update_data)

        assert updated.remarks == "Updated remarks"
        assert updated.grand_total == Decimal("2000.00")
        assert updated.status == QuotationStatus.SENT


class TestQuotationRepositoryDelete:
    """Tests for QuotationRepository.delete"""

    def test_delete_quotation_success(
        self, quotation_repo, test_quotation_data, mock_current_user
    ):
        """Test deleting a quotation"""
        quotation = quotation_repo.create(test_quotation_data)
        quotation_id = quotation.id

        quotation_repo.delete(quotation)

        # Verify it's deleted
        retrieved = quotation_repo.get_by_id(
            quotation_id, mock_current_user.organization_id
        )
        assert retrieved is None
