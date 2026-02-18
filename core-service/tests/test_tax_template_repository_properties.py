"""
Property-based tests for TaxTemplateRepository.

Tests universal properties that should hold across all valid inputs.
Feature: tax-and-charges-api
"""
import uuid
from datetime import UTC, datetime

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from sqlalchemy.orm import Session

from app.models.tax_template import TaxTemplate, TaxRule
from app.repositories.tax_template_repository import TaxTemplateRepository


class TestTaxTemplateRepositoryProperties:
    """Property-based test suite for TaxTemplateRepository."""

    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        tax_category=st.sampled_from(["Input", "Output"]),
        num_templates=st.integers(min_value=2, max_value=5),
    )
    def test_property_3_default_template_uniqueness(
        self, db_session: Session, mock_current_user, tax_category: str, num_templates: int
    ):
        """
        Feature: tax-and-charges-api, Property 3: Default Template Uniqueness
        
        For any organization and tax_category combination, at most one tax template
        should have is_default set to true. When a template is marked as default,
        any previously default template for the same organization and tax_category
        should be unmarked.
        
        Validates: Requirements 1.4
        """
        repo = TaxTemplateRepository(db_session)
        organization_id = mock_current_user.organization_id
        
        # Create multiple templates for the same organization and tax_category
        template_ids = []
        for i in range(num_templates):
            template_data = {
                "organization_id": organization_id,
                "template_code": f"TEST-{tax_category}-{i}-{uuid.uuid4().hex[:8]}",
                "template_name": f"Test Template {i}",
                "tax_category": tax_category,
                "is_default": False,
                "is_active": True,
                "applicability_rules": {},
                "extra_data": {},
                "created_by": mock_current_user.id,
                "updated_by": mock_current_user.id,
            }
            template = repo.create(template_data)
            template_ids.append(template.id)
        
        # Mark each template as default one by one and verify uniqueness
        for template_id in template_ids:
            # Mark this template as default
            repo.unmark_default_templates(organization_id, tax_category)
            template = repo.get_by_id(template_id, organization_id)
            repo.update(template, {"is_default": True})
            
            # Property 1: Exactly one template should be marked as default
            default_templates = (
                db_session.query(TaxTemplate)
                .filter(
                    TaxTemplate.organization_id == organization_id,
                    TaxTemplate.tax_category == tax_category,
                    TaxTemplate.is_default == True,
                    TaxTemplate.deleted_at.is_(None),
                )
                .all()
            )
            assert len(default_templates) == 1, (
                f"Expected exactly 1 default template, found {len(default_templates)}"
            )
            
            # Property 2: The default template should be the one we just marked
            assert default_templates[0].id == template_id
            
            # Property 3: All other templates should have is_default = False
            other_templates = (
                db_session.query(TaxTemplate)
                .filter(
                    TaxTemplate.organization_id == organization_id,
                    TaxTemplate.tax_category == tax_category,
                    TaxTemplate.id != template_id,
                    TaxTemplate.deleted_at.is_(None),
                )
                .all()
            )
            for other_template in other_templates:
                assert other_template.is_default == False, (
                    f"Template {other_template.id} should not be default"
                )
        
        # Property 4: get_default_template should return the correct template
        final_default = repo.get_default_template(organization_id, tax_category)
        assert final_default is not None
        assert final_default.id == template_ids[-1]
        assert final_default.is_default == True

    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        num_orgs=st.integers(min_value=2, max_value=3),
        tax_category=st.sampled_from(["Input", "Output"]),
    )
    def test_property_3_default_template_isolation_across_organizations(
        self, db_session: Session, tax_category: str, num_orgs: int
    ):
        """
        Feature: tax-and-charges-api, Property 3: Default Template Uniqueness
        
        Default template uniqueness should be isolated per organization.
        Each organization can have its own default template for the same tax_category.
        
        Validates: Requirements 1.4, 19.1
        """
        repo = TaxTemplateRepository(db_session)
        
        # Create templates for multiple organizations
        org_template_map = {}
        for org_idx in range(num_orgs):
            org_id = uuid.uuid4()
            user_id = uuid.uuid4()
            
            template_data = {
                "organization_id": org_id,
                "template_code": f"TEST-{tax_category}-{uuid.uuid4().hex[:8]}",
                "template_name": f"Default Template for Org {org_idx}",
                "tax_category": tax_category,
                "is_default": True,
                "is_active": True,
                "applicability_rules": {},
                "extra_data": {},
                "created_by": user_id,
                "updated_by": user_id,
            }
            template = repo.create(template_data)
            org_template_map[org_id] = template.id
        
        # Property: Each organization should have exactly one default template
        for org_id, expected_template_id in org_template_map.items():
            default_template = repo.get_default_template(org_id, tax_category)
            assert default_template is not None
            assert default_template.id == expected_template_id
            assert default_template.organization_id == org_id
            
            # Verify no other templates are default for this org
            all_defaults = (
                db_session.query(TaxTemplate)
                .filter(
                    TaxTemplate.organization_id == org_id,
                    TaxTemplate.tax_category == tax_category,
                    TaxTemplate.is_default == True,
                    TaxTemplate.deleted_at.is_(None),
                )
                .all()
            )
            assert len(all_defaults) == 1

    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        num_templates_input=st.integers(min_value=1, max_value=3),
        num_templates_output=st.integers(min_value=1, max_value=3),
    )
    def test_property_3_default_template_isolation_across_categories(
        self, db_session: Session, mock_current_user, 
        num_templates_input: int, num_templates_output: int
    ):
        """
        Feature: tax-and-charges-api, Property 3: Default Template Uniqueness
        
        Default template uniqueness should be isolated per tax_category.
        An organization can have one default template for Input and one for Output.
        
        Validates: Requirements 1.4
        """
        repo = TaxTemplateRepository(db_session)
        organization_id = mock_current_user.organization_id
        
        # Create templates for both Input and Output categories
        input_template_ids = []
        output_template_ids = []
        
        for i in range(num_templates_input):
            template_data = {
                "organization_id": organization_id,
                "template_code": f"TEST-INPUT-{i}-{uuid.uuid4().hex[:8]}",
                "template_name": f"Input Template {i}",
                "tax_category": "Input",
                "is_default": (i == 0),  # First one is default
                "is_active": True,
                "applicability_rules": {},
                "extra_data": {},
                "created_by": mock_current_user.id,
                "updated_by": mock_current_user.id,
            }
            template = repo.create(template_data)
            input_template_ids.append(template.id)
        
        for i in range(num_templates_output):
            template_data = {
                "organization_id": organization_id,
                "template_code": f"TEST-OUTPUT-{i}-{uuid.uuid4().hex[:8]}",
                "template_name": f"Output Template {i}",
                "tax_category": "Output",
                "is_default": (i == 0),  # First one is default
                "is_active": True,
                "applicability_rules": {},
                "extra_data": {},
                "created_by": mock_current_user.id,
                "updated_by": mock_current_user.id,
            }
            template = repo.create(template_data)
            output_template_ids.append(template.id)
        
        # Property 1: Should have exactly one default for Input category
        input_default = repo.get_default_template(organization_id, "Input")
        assert input_default is not None
        assert input_default.tax_category == "Input"
        assert input_default.is_default == True
        
        # Property 2: Should have exactly one default for Output category
        output_default = repo.get_default_template(organization_id, "Output")
        assert output_default is not None
        assert output_default.tax_category == "Output"
        assert output_default.is_default == True
        
        # Property 3: The defaults should be different templates
        assert input_default.id != output_default.id
        
        # Property 4: Marking a new Input template as default should not affect Output
        if len(input_template_ids) > 1:
            new_input_default_id = input_template_ids[1]
            repo.unmark_default_templates(organization_id, "Input")
            new_input_template = repo.get_by_id(new_input_default_id, organization_id)
            repo.update(new_input_template, {"is_default": True})
            
            # Output default should remain unchanged
            output_default_after = repo.get_default_template(organization_id, "Output")
            assert output_default_after.id == output_default.id
            
            # Input default should be the new one
            input_default_after = repo.get_default_template(organization_id, "Input")
            assert input_default_after.id == new_input_default_id

    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        tax_category=st.sampled_from(["Input", "Output"]),
    )
    def test_property_3_unmark_default_templates_idempotency(
        self, db_session: Session, mock_current_user, tax_category: str
    ):
        """
        Feature: tax-and-charges-api, Property 3: Default Template Uniqueness
        
        Calling unmark_default_templates multiple times should be idempotent
        and should not cause errors.
        
        Validates: Requirements 1.4
        """
        repo = TaxTemplateRepository(db_session)
        organization_id = mock_current_user.organization_id
        
        # Create a default template
        template_data = {
            "organization_id": organization_id,
            "template_code": f"TEST-{tax_category}-{uuid.uuid4().hex[:8]}",
            "template_name": "Default Template",
            "tax_category": tax_category,
            "is_default": True,
            "is_active": True,
            "applicability_rules": {},
            "extra_data": {},
            "created_by": mock_current_user.id,
            "updated_by": mock_current_user.id,
        }
        template = repo.create(template_data)
        
        # Verify it's marked as default
        assert template.is_default == True
        
        # Call unmark_default_templates multiple times
        for _ in range(3):
            repo.unmark_default_templates(organization_id, tax_category)
            
            # Property: No templates should be marked as default
            default_templates = (
                db_session.query(TaxTemplate)
                .filter(
                    TaxTemplate.organization_id == organization_id,
                    TaxTemplate.tax_category == tax_category,
                    TaxTemplate.is_default == True,
                    TaxTemplate.deleted_at.is_(None),
                )
                .all()
            )
            assert len(default_templates) == 0
        
        # Property: get_default_template should return None
        default_template = repo.get_default_template(organization_id, tax_category)
        assert default_template is None

    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        tax_category=st.sampled_from(["Input", "Output"]),
    )
    def test_property_3_soft_deleted_templates_not_considered_default(
        self, db_session: Session, mock_current_user, tax_category: str
    ):
        """
        Feature: tax-and-charges-api, Property 3: Default Template Uniqueness
        
        Soft-deleted templates should not be considered when checking for
        default templates, even if they have is_default = True.
        
        Validates: Requirements 1.4, 1.7
        """
        repo = TaxTemplateRepository(db_session)
        organization_id = mock_current_user.organization_id
        
        # Create a default template
        template_data = {
            "organization_id": organization_id,
            "template_code": f"TEST-{tax_category}-{uuid.uuid4().hex[:8]}",
            "template_name": "Default Template",
            "tax_category": tax_category,
            "is_default": True,
            "is_active": True,
            "applicability_rules": {},
            "extra_data": {},
            "created_by": mock_current_user.id,
            "updated_by": mock_current_user.id,
        }
        template = repo.create(template_data)
        template_id = template.id
        
        # Verify it's the default
        default_template = repo.get_default_template(organization_id, tax_category)
        assert default_template is not None
        assert default_template.id == template_id
        
        # Soft delete the template
        repo.soft_delete(template)
        
        # Property 1: get_default_template should return None
        default_template_after = repo.get_default_template(organization_id, tax_category)
        assert default_template_after is None
        
        # Property 2: The template should still exist in DB with deleted_at set
        deleted_template = (
            db_session.query(TaxTemplate)
            .filter(TaxTemplate.id == template_id)
            .first()
        )
        assert deleted_template is not None
        assert deleted_template.deleted_at is not None
        assert deleted_template.is_default == True  # Flag is still True, but ignored
        
        # Property 3: Creating a new default template should work without conflicts
        new_template_data = {
            "organization_id": organization_id,
            "template_code": f"TEST-{tax_category}-NEW-{uuid.uuid4().hex[:8]}",
            "template_name": "New Default Template",
            "tax_category": tax_category,
            "is_default": True,
            "is_active": True,
            "applicability_rules": {},
            "extra_data": {},
            "created_by": mock_current_user.id,
            "updated_by": mock_current_user.id,
        }
        new_template = repo.create(new_template_data)
        
        # The new template should be the default
        final_default = repo.get_default_template(organization_id, tax_category)
        assert final_default is not None
        assert final_default.id == new_template.id
