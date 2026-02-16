"""Unit tests for ChargeTemplateRepository"""

import uuid
from decimal import Decimal

import pytest

from app.models.charge_template import ChargeTemplate
from app.repositories.charge_template_repository import ChargeTemplateRepository


@pytest.fixture
def charge_template_repo(db_session):
    """Create a charge template repository instance"""
    return ChargeTemplateRepository(db_session)


@pytest.fixture
def test_charge_template_data_fixed(mock_current_user, sample_account_head_id):
    """Sample charge template data with fixed calculation method"""
    return {
        "organization_id": mock_current_user.organization_id,
        "template_code": "SHIP_FIXED",
        "template_name": "Fixed Shipping",
        "charge_type": "Shipping",
        "description": "Fixed shipping charge",
        "calculation_method": "FIXED",
        "fixed_amount": Decimal("50.00"),
        "percentage_rate": None,
        "base_on": None,
        "account_head_id": sample_account_head_id,
        "is_active": True,
        "applicability_rules": {
            "min_order_value": 0,
            "max_order_value": 1000
        },
        "extra_data": {},
        "created_by": mock_current_user.id,
        "updated_by": mock_current_user.id,
    }


@pytest.fixture
def test_charge_template_data_percentage(mock_current_user, sample_account_head_id):
    """Sample charge template data with percentage calculation method"""
    return {
        "organization_id": mock_current_user.organization_id,
        "template_code": "SHIP_PERCENT",
        "template_name": "Percentage Shipping",
        "charge_type": "Shipping",
        "description": "Percentage-based shipping charge",
        "calculation_method": "PERCENTAGE",
        "fixed_amount": None,
        "percentage_rate": Decimal("5.00"),
        "base_on": "Net_Total",
        "account_head_id": sample_account_head_id,
        "is_active": True,
        "applicability_rules": {},
        "extra_data": {},
        "created_by": mock_current_user.id,
        "updated_by": mock_current_user.id,
    }


class TestChargeTemplateRepositoryCreate:
    """Tests for ChargeTemplateRepository.create"""

    def test_create_template_fixed_success(
        self, charge_template_repo, test_charge_template_data_fixed
    ):
        """Test creating a charge template with fixed amount"""
        template = charge_template_repo.create(test_charge_template_data_fixed)

        assert template.id is not None
        assert template.template_code == "SHIP_FIXED"
        assert template.template_name == "Fixed Shipping"
        assert template.charge_type == "Shipping"
        assert template.calculation_method == "FIXED"
        assert template.fixed_amount == Decimal("50.00")
        assert template.percentage_rate is None
        assert template.base_on is None
        assert template.is_active is True
        assert template.created_at is not None

    def test_create_template_percentage_success(
        self, charge_template_repo, test_charge_template_data_percentage
    ):
        """Test creating a charge template with percentage"""
        template = charge_template_repo.create(test_charge_template_data_percentage)

        assert template.id is not None
        assert template.template_code == "SHIP_PERCENT"
        assert template.calculation_method == "PERCENTAGE"
        assert template.percentage_rate == Decimal("5.00")
        assert template.base_on == "Net_Total"
        assert template.fixed_amount is None

    def test_create_template_with_empty_applicability_rules(
        self, charge_template_repo, test_charge_template_data_fixed
    ):
        """Test creating a template with empty applicability rules"""
        test_charge_template_data_fixed["applicability_rules"] = {}
        template = charge_template_repo.create(test_charge_template_data_fixed)

        assert template.id is not None
        assert template.applicability_rules == {}


class TestChargeTemplateRepositoryGetById:
    """Tests for ChargeTemplateRepository.get_by_id"""

    def test_get_by_id_success(
        self, charge_template_repo, test_charge_template_data_fixed, mock_current_user
    ):
        """Test getting a charge template by ID"""
        template = charge_template_repo.create(test_charge_template_data_fixed)

        retrieved = charge_template_repo.get_by_id(
            template.id, mock_current_user.organization_id
        )

        assert retrieved is not None
        assert retrieved.id == template.id
        assert retrieved.template_code == "SHIP_FIXED"

    def test_get_by_id_not_found(self, charge_template_repo, mock_current_user):
        """Test getting a non-existent template"""
        fake_id = uuid.uuid4()
        retrieved = charge_template_repo.get_by_id(
            fake_id, mock_current_user.organization_id
        )

        assert retrieved is None

    def test_get_by_id_wrong_organization(
        self, charge_template_repo, test_charge_template_data_fixed, mock_current_user
    ):
        """Test getting a template from different organization"""
        template = charge_template_repo.create(test_charge_template_data_fixed)

        wrong_org_id = uuid.uuid4()
        retrieved = charge_template_repo.get_by_id(template.id, wrong_org_id)

        assert retrieved is None

    def test_get_by_id_soft_deleted(
        self, charge_template_repo, test_charge_template_data_fixed, mock_current_user
    ):
        """Test that soft-deleted templates are not retrieved"""
        template = charge_template_repo.create(test_charge_template_data_fixed)
        charge_template_repo.soft_delete(template)

        retrieved = charge_template_repo.get_by_id(
            template.id, mock_current_user.organization_id
        )

        assert retrieved is None


class TestChargeTemplateRepositoryGetByCode:
    """Tests for ChargeTemplateRepository.get_by_code"""

    def test_get_by_code_success(
        self, charge_template_repo, test_charge_template_data_fixed, mock_current_user
    ):
        """Test getting a template by code"""
        template = charge_template_repo.create(test_charge_template_data_fixed)

        retrieved = charge_template_repo.get_by_code(
            "SHIP_FIXED", mock_current_user.organization_id
        )

        assert retrieved is not None
        assert retrieved.id == template.id
        assert retrieved.template_code == "SHIP_FIXED"

    def test_get_by_code_not_found(self, charge_template_repo, mock_current_user):
        """Test getting a non-existent template by code"""
        retrieved = charge_template_repo.get_by_code(
            "NONEXISTENT", mock_current_user.organization_id
        )

        assert retrieved is None


class TestChargeTemplateRepositoryUpdate:
    """Tests for ChargeTemplateRepository.update"""

    def test_update_template_basic_fields(
        self, charge_template_repo, test_charge_template_data_fixed, mock_current_user
    ):
        """Test updating basic template fields"""
  