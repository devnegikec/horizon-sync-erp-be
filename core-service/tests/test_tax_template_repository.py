"""Unit tests for TaxTemplateRepository"""

import uuid
from decimal import Decimal

import pytest

from app.repositories.tax_template_repository import TaxTemplateRepository


@pytest.fixture
def tax_template_repo(db_session):
    """Create a tax template repository instance"""
    return TaxTemplateRepository(db_session)


@pytest.fixture
def test_tax_template_data(mock_current_user, sample_account_head_id):
    """Sample tax template data for testing"""
    return {
        "organization_id": mock_current_user.organization_id,
        "template_code": "GST_18",
        "template_name": "GST 18%",
        "description": "Standard GST rate",
        "tax_category": "Output",
        "is_default": False,
        "is_active": True,
        "applicability_rules": {
            "transaction_type": "Sales",
            "customer_location": {"country": "IN"},
        },
        "extra_data": {},
        "created_by": mock_current_user.id,
        "updated_by": mock_current_user.id,
        "tax_rules": [
            {
                "rule_name": "CGST",
                "tax_type": "CGST",
                "description": "Central GST",
                "tax_rate": Decimal("9.00"),
                "account_head_id": sample_account_head_id,
                "is_compound": False,
                "sequence": 1,
                "applicability_conditions": {},
            },
            {
                "rule_name": "SGST",
                "tax_type": "SGST",
                "description": "State GST",
                "tax_rate": Decimal("9.00"),
                "account_head_id": sample_account_head_id,
                "is_compound": False,
                "sequence": 2,
                "applicability_conditions": {},
            },
        ],
    }


class TestTaxTemplateRepositoryCreate:
    """Tests for TaxTemplateRepository.create"""

    def test_create_template_success(self, tax_template_repo, test_tax_template_data):
        """Test creating a tax template with rules successfully"""
        template = tax_template_repo.create(test_tax_template_data)

        assert template.id is not None
        assert template.template_code == "GST_18"
        assert template.template_name == "GST 18%"
        assert template.tax_category == "Output"
        assert template.is_default is False
        assert template.is_active is True
        assert len(template.tax_rules) == 2
        assert template.tax_rules[0].rule_name == "CGST"
        assert template.tax_rules[0].tax_rate == Decimal("9.00")
        assert template.tax_rules[1].rule_name == "SGST"
        assert template.created_at is not None

    def test_create_template_without_rules(
        self, tax_template_repo, test_tax_template_data
    ):
        """Test creating a tax template without tax rules"""
        test_tax_template_data.pop("tax_rules")
        template = tax_template_repo.create(test_tax_template_data)

        assert template.id is not None
        assert len(template.tax_rules) == 0

    def test_create_template_with_empty_applicability_rules(
        self, tax_template_repo, test_tax_template_data
    ):
        """Test creating a template with empty applicability rules"""
        test_tax_template_data["applicability_rules"] = {}
        template = tax_template_repo.create(test_tax_template_data)

        assert template.id is not None
        assert template.applicability_rules == {}


class TestTaxTemplateRepositoryGetById:
    """Tests for TaxTemplateRepository.get_by_id"""

    def test_get_by_id_success(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test getting a tax template by ID"""
        template = tax_template_repo.create(test_tax_template_data)

        retrieved = tax_template_repo.get_by_id(
            template.id, mock_current_user.organization_id
        )

        assert retrieved is not None
        assert retrieved.id == template.id
        assert retrieved.template_code == "GST_18"
        assert len(retrieved.tax_rules) == 2

    def test_get_by_id_without_rules(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test getting a template without loading rules"""
        template = tax_template_repo.create(test_tax_template_data)

        retrieved = tax_template_repo.get_by_id(
            template.id, mock_current_user.organization_id, include_rules=False
        )

        assert retrieved is not None
        assert retrieved.id == template.id

    def test_get_by_id_not_found(self, tax_template_repo, mock_current_user):
        """Test getting a non-existent template"""
        fake_id = uuid.uuid4()
        retrieved = tax_template_repo.get_by_id(
            fake_id, mock_current_user.organization_id
        )

        assert retrieved is None

    def test_get_by_id_wrong_organization(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test getting a template from different organization"""
        template = tax_template_repo.create(test_tax_template_data)

        wrong_org_id = uuid.uuid4()
        retrieved = tax_template_repo.get_by_id(template.id, wrong_org_id)

        assert retrieved is None

    def test_get_by_id_soft_deleted(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test that soft-deleted templates are not retrieved"""
        template = tax_template_repo.create(test_tax_template_data)
        tax_template_repo.soft_delete(template)

        retrieved = tax_template_repo.get_by_id(
            template.id, mock_current_user.organization_id
        )

        assert retrieved is None


class TestTaxTemplateRepositoryGetByCode:
    """Tests for TaxTemplateRepository.get_by_code"""

    def test_get_by_code_success(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test getting a template by code"""
        template = tax_template_repo.create(test_tax_template_data)

        retrieved = tax_template_repo.get_by_code(
            "GST_18", mock_current_user.organization_id
        )

        assert retrieved is not None
        assert retrieved.id == template.id
        assert retrieved.template_code == "GST_18"

    def test_get_by_code_not_found(self, tax_template_repo, mock_current_user):
        """Test getting a non-existent template by code"""
        retrieved = tax_template_repo.get_by_code(
            "NONEXISTENT", mock_current_user.organization_id
        )

        assert retrieved is None


class TestTaxTemplateRepositoryUpdate:
    """Tests for TaxTemplateRepository.update"""

    def test_update_template_basic_fields(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test updating basic template fields"""
        template = tax_template_repo.create(test_tax_template_data)

        update_data = {
            "template_name": "GST 18% Updated",
            "description": "Updated description",
            "is_active": False,
        }

        updated = tax_template_repo.update(template, update_data)

        assert updated.template_name == "GST 18% Updated"
        assert updated.description == "Updated description"
        assert updated.is_active is False
        assert updated.template_code == "GST_18"  # Unchanged

    def test_update_template_rules(
        self,
        tax_template_repo,
        test_tax_template_data,
        mock_current_user,
        sample_account_head_id,
    ):
        """Test updating tax rules"""
        template = tax_template_repo.create(test_tax_template_data)
        original_rule_count = len(template.tax_rules)

        new_rules = [
            {
                "rule_name": "IGST",
                "tax_type": "IGST",
                "description": "Integrated GST",
                "tax_rate": Decimal("18.00"),
                "account_head_id": sample_account_head_id,
                "is_compound": False,
                "sequence": 1,
                "applicability_conditions": {},
            }
        ]

        update_data = {"tax_rules": new_rules}
        updated = tax_template_repo.update(template, update_data)

        assert len(updated.tax_rules) == 1
        assert updated.tax_rules[0].rule_name == "IGST"
        assert updated.tax_rules[0].tax_rate == Decimal("18.00")

    def test_update_template_applicability_rules(
        self, tax_template_repo, test_tax_template_data
    ):
        """Test updating applicability rules"""
        template = tax_template_repo.create(test_tax_template_data)

        new_rules = {
            "transaction_type": "Purchase",
            "supplier_location": {"country": "US"},
        }

        update_data = {"applicability_rules": new_rules}
        updated = tax_template_repo.update(template, update_data)

        assert updated.applicability_rules["transaction_type"] == "Purchase"
        assert updated.applicability_rules["supplier_location"]["country"] == "US"


class TestTaxTemplateRepositorySoftDelete:
    """Tests for TaxTemplateRepository.soft_delete"""

    def test_soft_delete_success(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test soft deleting a template"""
        template = tax_template_repo.create(test_tax_template_data)

        deleted = tax_template_repo.soft_delete(template)

        assert deleted.deleted_at is not None
        assert deleted.id == template.id

        # Verify it's not retrieved by get_by_id
        retrieved = tax_template_repo.get_by_id(
            template.id, mock_current_user.organization_id
        )
        assert retrieved is None


class TestTaxTemplateRepositoryListTemplates:
    """Tests for TaxTemplateRepository.list_templates"""

    def test_list_templates_empty(self, tax_template_repo, mock_current_user):
        """Test listing templates when none exist"""
        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id
        )

        assert templates == []
        assert total == 0

    def test_list_templates_basic(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test listing templates"""
        tax_template_repo.create(test_tax_template_data)

        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id
        )

        assert len(templates) == 1
        assert total == 1
        assert templates[0].template_code == "GST_18"

    def test_list_templates_filter_by_tax_category(
        self,
        tax_template_repo,
        test_tax_template_data,
        mock_current_user,
        sample_account_head_id,
    ):
        """Test filtering templates by tax category"""
        # Create Output template
        tax_template_repo.create(test_tax_template_data)

        # Create Input template
        input_template_data = test_tax_template_data.copy()
        input_template_data["template_code"] = "GST_INPUT_18"
        input_template_data["tax_category"] = "Input"
        input_template_data["tax_rules"] = []
        tax_template_repo.create(input_template_data)

        # Filter by Output
        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id, tax_category="Output"
        )

        assert len(templates) == 1
        assert total == 1
        assert templates[0].tax_category == "Output"

    def test_list_templates_filter_by_is_active(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test filtering templates by active status"""
        # Create active template
        tax_template_repo.create(test_tax_template_data)

        # Create inactive template
        inactive_data = test_tax_template_data.copy()
        inactive_data["template_code"] = "GST_INACTIVE"
        inactive_data["is_active"] = False
        inactive_data["tax_rules"] = []
        tax_template_repo.create(inactive_data)

        # Filter by active
        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id, is_active=True
        )

        assert len(templates) == 1
        assert total == 1
        assert templates[0].is_active is True

    def test_list_templates_filter_by_is_default(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test filtering templates by default status"""
        # Create default template
        default_data = test_tax_template_data.copy()
        default_data["is_default"] = True
        tax_template_repo.create(default_data)

        # Create non-default template
        non_default_data = test_tax_template_data.copy()
        non_default_data["template_code"] = "GST_NON_DEFAULT"
        non_default_data["is_default"] = False
        non_default_data["tax_rules"] = []
        tax_template_repo.create(non_default_data)

        # Filter by default
        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id, is_default=True
        )

        assert len(templates) == 1
        assert total == 1
        assert templates[0].is_default is True

    def test_list_templates_search(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test searching templates by code or name"""
        tax_template_repo.create(test_tax_template_data)

        # Search by code
        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id, search="GST_18"
        )

        assert len(templates) == 1
        assert total == 1

        # Search by name
        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id, search="GST 18%"
        )

        assert len(templates) == 1
        assert total == 1

    def test_list_templates_pagination(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test pagination"""
        # Create 3 templates
        for i in range(3):
            data = test_tax_template_data.copy()
            data["template_code"] = f"GST_{i}"
            data["tax_rules"] = []
            tax_template_repo.create(data)

        # Get page 1 with page_size 2
        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id, page=1, page_size=2
        )

        assert len(templates) == 2
        assert total == 3

        # Get page 2
        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id, page=2, page_size=2
        )

        assert len(templates) == 1
        assert total == 3

    def test_list_templates_sorting(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test sorting templates"""
        # Create templates with different codes
        for code in ["GST_C", "GST_A", "GST_B"]:
            data = test_tax_template_data.copy()
            data["template_code"] = code
            data["tax_rules"] = []
            tax_template_repo.create(data)

        # Sort by template_code ascending
        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id, sort_by="template_code", sort_order="asc"
        )

        assert len(templates) == 3
        assert templates[0].template_code == "GST_A"
        assert templates[1].template_code == "GST_B"
        assert templates[2].template_code == "GST_C"

    def test_list_templates_excludes_soft_deleted(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test that soft-deleted templates are excluded from list"""
        template = tax_template_repo.create(test_tax_template_data)
        tax_template_repo.soft_delete(template)

        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id
        )

        assert len(templates) == 0
        assert total == 0

    def test_list_templates_organization_isolation(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test that templates from other organizations are not listed"""
        # Create template for current organization
        tax_template_repo.create(test_tax_template_data)

        # Create template for different organization
        other_org_data = test_tax_template_data.copy()
        other_org_data["organization_id"] = uuid.uuid4()
        other_org_data["template_code"] = "OTHER_ORG"
        other_org_data["tax_rules"] = []
        tax_template_repo.create(other_org_data)

        # List templates for current organization
        templates, total = tax_template_repo.list_templates(
            mock_current_user.organization_id
        )

        assert len(templates) == 1
        assert total == 1
        assert templates[0].organization_id == mock_current_user.organization_id


class TestTaxTemplateRepositoryGetDefaultTemplate:
    """Tests for TaxTemplateRepository.get_default_template"""

    def test_get_default_template_success(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test getting default template"""
        test_tax_template_data["is_default"] = True
        template = tax_template_repo.create(test_tax_template_data)

        default = tax_template_repo.get_default_template(
            mock_current_user.organization_id, "Output"
        )

        assert default is not None
        assert default.id == template.id
        assert default.is_default is True

    def test_get_default_template_not_found(self, tax_template_repo, mock_current_user):
        """Test getting default template when none exists"""
        default = tax_template_repo.get_default_template(
            mock_current_user.organization_id, "Output"
        )

        assert default is None

    def test_get_default_template_inactive_excluded(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test that inactive default templates are not returned"""
        test_tax_template_data["is_default"] = True
        test_tax_template_data["is_active"] = False
        tax_template_repo.create(test_tax_template_data)

        default = tax_template_repo.get_default_template(
            mock_current_user.organization_id, "Output"
        )

        assert default is None


class TestTaxTemplateRepositoryUnmarkDefaultTemplates:
    """Tests for TaxTemplateRepository.unmark_default_templates"""

    def test_unmark_default_templates(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test unmarking default templates"""
        # Create default template
        test_tax_template_data["is_default"] = True
        template = tax_template_repo.create(test_tax_template_data)

        # Unmark defaults
        tax_template_repo.unmark_default_templates(
            mock_current_user.organization_id, "Output"
        )

        # Verify template is no longer default
        retrieved = tax_template_repo.get_by_id(
            template.id, mock_current_user.organization_id
        )
        assert retrieved.is_default is False

    def test_unmark_default_templates_multiple(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test unmarking multiple default templates"""
        # Create two default templates (shouldn't happen, but test it)
        test_tax_template_data["is_default"] = True
        tax_template_repo.create(test_tax_template_data)

        test_tax_template_data["template_code"] = "GST_18_ALT"
        test_tax_template_data["tax_rules"] = []
        tax_template_repo.create(test_tax_template_data)

        # Unmark defaults
        tax_template_repo.unmark_default_templates(
            mock_current_user.organization_id, "Output"
        )

        # Verify no default templates remain
        default = tax_template_repo.get_default_template(
            mock_current_user.organization_id, "Output"
        )
        assert default is None


class TestTaxTemplateRepositoryApplicabilityRules:
    """Tests for applicability rules evaluation"""

    def test_matches_applicability_rules_no_rules(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test that templates with no rules match any context"""
        test_tax_template_data["applicability_rules"] = {}
        template = tax_template_repo.create(test_tax_template_data)

        matches = tax_template_repo._matches_applicability_rules(template)
        assert matches is True

    def test_matches_applicability_rules_customer_location_country(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test matching customer location by country"""
        test_tax_template_data["applicability_rules"] = {
            "customer_location": {"country": "IN"}
        }
        template = tax_template_repo.create(test_tax_template_data)

        # Matching location
        matches = tax_template_repo._matches_applicability_rules(
            template, customer_location={"country": "IN", "state": "MH"}
        )
        assert matches is True

        # Non-matching location
        matches = tax_template_repo._matches_applicability_rules(
            template, customer_location={"country": "US", "state": "CA"}
        )
        assert matches is False

    def test_matches_applicability_rules_customer_location_state(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test matching customer location by country and state"""
        test_tax_template_data["applicability_rules"] = {
            "customer_location": {"country": "IN", "state": "MH"}
        }
        template = tax_template_repo.create(test_tax_template_data)

        # Matching location
        matches = tax_template_repo._matches_applicability_rules(
            template, customer_location={"country": "IN", "state": "MH"}
        )
        assert matches is True

        # Non-matching state
        matches = tax_template_repo._matches_applicability_rules(
            template, customer_location={"country": "IN", "state": "KA"}
        )
        assert matches is False

    def test_matches_applicability_rules_supplier_location(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test matching supplier location"""
        test_tax_template_data["applicability_rules"] = {
            "supplier_location": {"country": "US"}
        }
        template = tax_template_repo.create(test_tax_template_data)

        # Matching location
        matches = tax_template_repo._matches_applicability_rules(
            template, supplier_location={"country": "US", "state": "CA"}
        )
        assert matches is True

        # Non-matching location
        matches = tax_template_repo._matches_applicability_rules(
            template, supplier_location={"country": "IN"}
        )
        assert matches is False


class TestTaxTemplateRepositoryTemplateCodeExists:
    """Tests for TaxTemplateRepository.template_code_exists"""

    def test_template_code_exists_true(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test checking if template code exists"""
        tax_template_repo.create(test_tax_template_data)

        exists = tax_template_repo.template_code_exists(
            "GST_18", mock_current_user.organization_id
        )

        assert exists is True

    def test_template_code_exists_false(self, tax_template_repo, mock_current_user):
        """Test checking non-existent template code"""
        exists = tax_template_repo.template_code_exists(
            "NONEXISTENT", mock_current_user.organization_id
        )

        assert exists is False

    def test_template_code_exists_organization_isolation(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test that template code check is organization-specific"""
        tax_template_repo.create(test_tax_template_data)

        # Check with different organization
        other_org_id = uuid.uuid4()
        exists = tax_template_repo.template_code_exists("GST_18", other_org_id)

        assert exists is False


class TestTaxTemplateRepositoryIsTemplateReferenced:
    """Tests for TaxTemplateRepository.is_template_referenced"""

    def test_is_template_referenced_no_references(
        self, tax_template_repo, test_tax_template_data, mock_current_user
    ):
        """Test checking references when none exist"""
        template = tax_template_repo.create(test_tax_template_data)

        references = tax_template_repo.is_template_referenced(
            template.id, mock_current_user.organization_id
        )

        assert references["items"] == []
        assert references["item_groups"] == []
        assert references["transactions"] == []

    def test_is_template_referenced_by_item(
        self, tax_template_repo, test_tax_template_data, mock_current_user, db_session
    ):
        """Test checking references when template is used by an item"""
        from app.models.item import Item

        template = tax_template_repo.create(test_tax_template_data)

        # Create item with tax template
        item = Item(
            id=uuid.uuid4(),
            organization_id=mock_current_user.organization_id,
            item_code="TEST-ITEM",
            item_name="Test Item",
            item_type="stock",
            uom="Nos",
            maintain_stock=True,
            standard_rate=100.00,
            sales_tax_template_id=template.id,
            created_by=mock_current_user.id,
            updated_by=mock_current_user.id,
        )
        db_session.add(item)
        db_session.commit()

        references = tax_template_repo.is_template_referenced(
            template.id, mock_current_user.organization_id
        )

        assert len(references["items"]) == 1
        assert str(item.id) in references["items"]
        assert references["item_groups"] == []
        assert references["transactions"] == []
