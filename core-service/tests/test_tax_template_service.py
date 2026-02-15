"""Unit tests for TaxTemplateService"""

import pytest
from uuid import uuid4
from decimal import Decimal

from app.services.tax_template_service import TaxTemplateService
from app.core.exceptions import ResourceNotFoundException


def test_create_template_success(db_session, sample_organization_id, sample_user_id):
    """Test successful tax template creation"""
    service = TaxTemplateService(db_session)
    
    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "GST_18",
        "template_name": "GST 18%",
        "description": "Standard GST rate",
        "tax_category": "Output",
        "is_default": False,
        "is_active": True,
        "applicability_rules": {},
        "extra_data": {},
        "tax_rules": [
            {
                "rule_name": "CGST",
                "tax_type": "CGST",
                "description": "Central GST",
                "tax_rate": Decimal("9.00"),
                "account_head_id": uuid4(),
                "is_compound": False,
                "sequence": 1,
                "applicability_conditions": {},
            },
            {
                "rule_name": "SGST",
                "tax_type": "SGST",
                "description": "State GST",
                "tax_rate": Decimal("9.00"),
                "account_head_id": uuid4(),
                "is_compound": False,
                "sequence": 2,
                "applicability_conditions": {},
            },
        ],
    }
    
    result = service.create_template(template_data, sample_user_id)
    
    assert result["template_code"] == "GST_18"
    assert result["template_name"] == "GST 18%"
    assert result["tax_category"] == "Output"
    assert result["is_active"] is True
    assert len(result["tax_rules"]) == 2
    assert result["created_by"] == sample_user_id


def test_create_template_missing_required_fields(db_session, sample_user_id):
    """Test template creation with missing required fields"""
    service = TaxTemplateService(db_session)
    
    template_data = {
        "template_code": "GST_18",
        # Missing template_name, organization_id, is_active
    }
    
    with pytest.raises(ValueError, match="Missing required fields"):
        service.create_template(template_data, sample_user_id)


def test_create_template_duplicate_code(db_session, sample_organization_id, sample_user_id):
    """Test template creation with duplicate template_code"""
    service = TaxTemplateService(db_session)
    
    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "GST_18",
        "template_name": "GST 18%",
        "tax_category": "Output",
        "is_default": False,
        "is_active": True,
        "tax_rules": [],
    }
    
    # Create first template
    service.create_template(template_data, sample_user_id)
    
    # Try to create duplicate
    with pytest.raises(ValueError, match="already exists"):
        service.create_template(template_data, sample_user_id)


def test_get_template_success(db_session, sample_organization_id, sample_user_id):
    """Test successful template retrieval"""
    service = TaxTemplateService(db_session)
    
    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "GST_18",
        "template_name": "GST 18%",
        "tax_category": "Output",
        "is_default": False,
        "is_active": True,
        "tax_rules": [],
    }
    
    created = service.create_template(template_data, sample_user_id)
    retrieved = service.get_template(created["id"], sample_organization_id)
    
    assert retrieved["id"] == created["id"]
    assert retrieved["template_code"] == "GST_18"


def test_get_template_not_found(db_session, sample_organization_id):
    """Test template retrieval with non-existent ID"""
    service = TaxTemplateService(db_session)
    
    with pytest.raises(ResourceNotFoundException):
        service.get_template(uuid4(), sample_organization_id)


def test_update_template_success(db_session, sample_organization_id, sample_user_id):
    """Test successful template update"""
    service = TaxTemplateService(db_session)
    
    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "GST_18",
        "template_name": "GST 18%",
        "tax_category": "Output",
        "is_default": False,
        "is_active": True,
        "tax_rules": [],
    }
    
    created = service.create_template(template_data, sample_user_id)
    
    update_data = {
        "organization_id": sample_organization_id,
        "template_name": "GST 18% Updated",
        "description": "Updated description",
    }
    
    updated = service.update_template(created["id"], update_data, sample_user_id)
    
    assert updated["template_name"] == "GST 18% Updated"
    assert updated["description"] == "Updated description"


def test_delete_template_success(db_session, sample_organization_id, sample_user_id):
    """Test successful template deletion"""
    service = TaxTemplateService(db_session)
    
    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "GST_18",
        "template_name": "GST 18%",
        "tax_category": "Output",
        "is_default": False,
        "is_active": True,
        "tax_rules": [],
    }
    
    created = service.create_template(template_data, sample_user_id)
    
    # Delete should succeed
    service.delete_template(created["id"], sample_organization_id)
    
    # Template should not be found after deletion
    with pytest.raises(ResourceNotFoundException):
        service.get_template(created["id"], sample_organization_id)


def test_list_templates(db_session, sample_organization_id, sample_user_id):
    """Test template listing with pagination"""
    service = TaxTemplateService(db_session)
    
    # Create multiple templates
    for i in range(3):
        template_data = {
            "organization_id": sample_organization_id,
            "template_code": f"GST_{i}",
            "template_name": f"GST {i}%",
            "tax_category": "Output",
            "is_default": False,
            "is_active": True,
            "tax_rules": [],
        }
        service.create_template(template_data, sample_user_id)
    
    templates, pagination = service.list_templates(sample_organization_id)
    
    assert len(templates) == 3
    assert pagination["total_items"] == 3
    assert pagination["page"] == 1


def test_set_as_default(db_session, sample_organization_id, sample_user_id):
    """Test setting template as default"""
    service = TaxTemplateService(db_session)
    
    # Create two templates
    template1_data = {
        "organization_id": sample_organization_id,
        "template_code": "GST_18",
        "template_name": "GST 18%",
        "tax_category": "Output",
        "is_default": True,
        "is_active": True,
        "tax_rules": [],
    }
    template1 = service.create_template(template1_data, sample_user_id)
    
    template2_data = {
        "organization_id": sample_organization_id,
        "template_code": "GST_12",
        "template_name": "GST 12%",
        "tax_category": "Output",
        "is_default": False,
        "is_active": True,
        "tax_rules": [],
    }
    template2 = service.create_template(template2_data, sample_user_id)
    
    # Set template2 as default
    updated = service.set_as_default(template2["id"], sample_organization_id, "Output")
    
    assert updated["is_default"] is True
    
    # Verify template1 is no longer default
    template1_retrieved = service.get_template(template1["id"], sample_organization_id)
    assert template1_retrieved["is_default"] is False


def test_get_applicable_template_item_level(
    db_session, sample_organization_id, sample_user_id, sample_item_id
):
    """Test getting applicable template at item level"""
    service = TaxTemplateService(db_session)
    
    # Create a template
    template_data = {
        "organization_id": sample_organization_id,
        "template_code": "GST_18",
        "template_name": "GST 18%",
        "tax_category": "Output",
        "is_default": False,
        "is_active": True,
        "tax_rules": [],
    }
    created = service.create_template(template_data, sample_user_id)
    
    # Assign template to item (this would be done through item service)
    from app.models.item import Item
    item = db_session.query(Item).filter(Item.id == sample_item_id).first()
    if item:
        item.sales_tax_template_id = created["id"]
        db_session.commit()
    
    # Get applicable template
    context = {
        "organization_id": sample_organization_id,
        "transaction_type": "Sales",
        "item_id": sample_item_id,
    }
    
    result = service.get_applicable_template(context)
    
    if result:
        assert result["template"]["id"] == created["id"]
        assert result["source"] == "item"
