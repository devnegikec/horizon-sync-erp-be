"""Unit tests for ChargeTemplateService"""

import pytest
from uuid import uuid4
from decimal import Decimal

from app.services.charge_template_service import ChargeTemplateService
from app.core.exceptions import ResourceNotFoundException


def test_create_template_fixed_amount_success(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test successful charge template creation with fixed amount"""
    service = ChargeTemplateService(db_session)

    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "SHIP_FIXED",
        "template_name": "Fixed Shipping",
        "charge_type": "Shipping",
        "description": "Fixed shipping charge",
        "calculation_method": "FIXED",
        "fixed_amount": Decimal("50.00"),
        "account_head_id": sample_account_head_id,
        "is_active": True,
        "applicability_rules": {},
        "extra_data": {},
    }

    result = service.create_template(template_data, sample_user_id)

    assert result["template_code"] == "SHIP_FIXED"
    assert result["template_name"] == "Fixed Shipping"
    assert result["charge_type"] == "Shipping"
    assert result["calculation_method"] == "FIXED"
    assert result["fixed_amount"] == Decimal("50.00")
    assert result["is_active"] is True
    assert result["created_by"] == sample_user_id


def test_create_template_percentage_success(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test successful charge template creation with percentage"""
    service = ChargeTemplateService(db_session)

    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "SHIP_PCT",
        "template_name": "Percentage Shipping",
        "charge_type": "Shipping",
        "description": "Percentage-based shipping",
        "calculation_method": "PERCENTAGE",
        "percentage_rate": Decimal("5.00"),
        "base_on": "Net_Total",
        "account_head_id": sample_account_head_id,
        "is_active": True,
        "applicability_rules": {},
        "extra_data": {},
    }

    result = service.create_template(template_data, sample_user_id)

    assert result["template_code"] == "SHIP_PCT"
    assert result["calculation_method"] == "PERCENTAGE"
    assert result["percentage_rate"] == Decimal("5.00")
    assert result["base_on"] == "Net_Total"


def test_create_template_missing_required_fields(db_session, sample_user_id):
    """Test template creation with missing required fields"""
    service = ChargeTemplateService(db_session)

    template_data = {
        "template_code": "SHIP_FIXED",
        # Missing template_name, charge_type, organization_id, calculation_method
    }

    with pytest.raises(ValueError, match="Missing required fields"):
        service.create_template(template_data, sample_user_id)


def test_create_template_fixed_missing_amount(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test FIXED template creation without fixed_amount"""
    service = ChargeTemplateService(db_session)

    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "SHIP_FIXED",
        "template_name": "Fixed Shipping",
        "charge_type": "Shipping",
        "calculation_method": "FIXED",
        "account_head_id": sample_account_head_id,
        "is_active": True,
    }

    with pytest.raises(ValueError, match="fixed_amount is required"):
        service.create_template(template_data, sample_user_id)


def test_create_template_percentage_missing_fields(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test PERCENTAGE template creation without required fields"""
    service = ChargeTemplateService(db_session)

    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "SHIP_PCT",
        "template_name": "Percentage Shipping",
        "charge_type": "Shipping",
        "calculation_method": "PERCENTAGE",
        "account_head_id": sample_account_head_id,
        "is_active": True,
    }

    with pytest.raises(ValueError, match="percentage_rate is required"):
        service.create_template(template_data, sample_user_id)


def test_create_template_duplicate_code(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test template creation with duplicate template_code"""
    service = ChargeTemplateService(db_session)

    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "SHIP_FIXED",
        "template_name": "Fixed Shipping",
        "charge_type": "Shipping",
        "calculation_method": "FIXED",
        "fixed_amount": Decimal("50.00"),
        "account_head_id": sample_account_head_id,
        "is_active": True,
    }

    # Create first template
    service.create_template(template_data, sample_user_id)

    # Try to create duplicate
    with pytest.raises(ValueError, match="already exists"):
        service.create_template(template_data, sample_user_id)


def test_get_template_success(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test successful template retrieval"""
    service = ChargeTemplateService(db_session)

    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "SHIP_FIXED",
        "template_name": "Fixed Shipping",
        "charge_type": "Shipping",
        "calculation_method": "FIXED",
        "fixed_amount": Decimal("50.00"),
        "account_head_id": sample_account_head_id,
        "is_active": True,
    }

    created = service.create_template(template_data, sample_user_id)
    retrieved = service.get_template(created["id"], sample_organization_id)

    assert retrieved["id"] == created["id"]
    assert retrieved["template_code"] == "SHIP_FIXED"


def test_get_template_not_found(db_session, sample_organization_id):
    """Test template retrieval with non-existent ID"""
    service = ChargeTemplateService(db_session)

    with pytest.raises(ResourceNotFoundException):
        service.get_template(uuid4(), sample_organization_id)


def test_update_template_success(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test successful template update"""
    service = ChargeTemplateService(db_session)

    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "SHIP_FIXED",
        "template_name": "Fixed Shipping",
        "charge_type": "Shipping",
        "calculation_method": "FIXED",
        "fixed_amount": Decimal("50.00"),
        "account_head_id": sample_account_head_id,
        "is_active": True,
    }

    created = service.create_template(template_data, sample_user_id)

    update_data = {
        "organization_id": sample_organization_id,
        "template_name": "Fixed Shipping Updated",
        "description": "Updated description",
        "fixed_amount": Decimal("75.00"),
    }

    updated = service.update_template(created["id"], update_data, sample_user_id)

    assert updated["template_name"] == "Fixed Shipping Updated"
    assert updated["description"] == "Updated description"
    assert updated["fixed_amount"] == Decimal("75.00")


def test_delete_template_success(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test successful template deletion"""
    service = ChargeTemplateService(db_session)

    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "SHIP_FIXED",
        "template_name": "Fixed Shipping",
        "charge_type": "Shipping",
        "calculation_method": "FIXED",
        "fixed_amount": Decimal("50.00"),
        "account_head_id": sample_account_head_id,
        "is_active": True,
    }

    created = service.create_template(template_data, sample_user_id)

    # Delete should succeed
    service.delete_template(created["id"], sample_organization_id)

    # Template should not be found after deletion
    with pytest.raises(ResourceNotFoundException):
        service.get_template(created["id"], sample_organization_id)


def test_list_templates(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test template listing with pagination"""
    service = ChargeTemplateService(db_session)

    # Create multiple templates
    for i in range(3):
        template_data = {
            "organization_id": sample_organization_id,
            "template_code": f"SHIP_{i}",
            "template_name": f"Shipping {i}",
            "charge_type": "Shipping",
            "calculation_method": "FIXED",
            "fixed_amount": Decimal(f"{50 + i * 10}.00"),
            "account_head_id": sample_account_head_id,
            "is_active": True,
        }
        service.create_template(template_data, sample_user_id)

    templates, pagination = service.list_templates(sample_organization_id)

    assert len(templates) == 3
    assert pagination["total_items"] == 3
    assert pagination["page"] == 1


def test_list_templates_with_filters(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test template listing with filters"""
    service = ChargeTemplateService(db_session)

    # Create templates with different charge types
    template_data_1 = {
        "organization_id": sample_organization_id,
        "template_code": "SHIP_1",
        "template_name": "Shipping 1",
        "charge_type": "Shipping",
        "calculation_method": "FIXED",
        "fixed_amount": Decimal("50.00"),
        "account_head_id": sample_account_head_id,
        "is_active": True,
    }
    service.create_template(template_data_1, sample_user_id)

    template_data_2 = {
        "organization_id": sample_organization_id,
        "template_code": "HAND_1",
        "template_name": "Handling 1",
        "charge_type": "Handling",
        "calculation_method": "FIXED",
        "fixed_amount": Decimal("25.00"),
        "account_head_id": sample_account_head_id,
        "is_active": True,
    }
    service.create_template(template_data_2, sample_user_id)

    # Filter by charge_type
    filters = {"charge_type": "Shipping"}
    templates, pagination = service.list_templates(sample_organization_id, filters)

    assert len(templates) == 1
    assert templates[0]["charge_type"] == "Shipping"


def test_get_applicable_charges(
    db_session, sample_organization_id, sample_user_id, sample_account_head_id
):
    """Test getting applicable charges based on context"""
    service = ChargeTemplateService(db_session)

    # Create a template with applicability rules
    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "SHIP_SMALL",
        "template_name": "Small Order Shipping",
        "charge_type": "Shipping",
        "calculation_method": "FIXED",
        "fixed_amount": Decimal("50.00"),
        "account_head_id": sample_account_head_id,
        "is_active": True,
        "applicability_rules": {
            "min_order_value": 0,
            "max_order_value": 1000,
        },
    }
    created = service.create_template(template_data, sample_user_id)

    # Test with matching context
    context = {
        "organization_id": sample_organization_id,
        "transaction_type": "Sales_Order",
        "net_total": 500.00,
    }

    applicable = service.get_applicable_charges(context)

    assert len(applicable) >= 1
    assert any(charge["id"] == created["id"] for charge in applicable)
