"""
Test configuration and utilities for Chart of Account bug validation tests.

This module provides fixtures and utilities specifically for testing
the Chart of Account functionality issues.
"""

import pytest
from typing import Generator
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database import get_db
from app.models.organization import Organization
from app.models.user import User
from app.models.base import UserStatus


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """
    Create a test client for API testing.
    """
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_organization(db_session: Session) -> Organization:
    """
    Create a test organization for account testing.
    """
    # Check if organization already exists
    existing_org = db_session.query(Organization).filter(
        Organization.name == "Test Organization"
    ).first()
    
    if existing_org:
        return existing_org
    
    organization = Organization(
        name="Test Organization",
        description="Test organization for account validation",
        created_by="test-system",
        updated_by="test-system"
    )
    db_session.add(organization)
    db_session.commit()
    db_session.refresh(organization)
    return organization


@pytest.fixture  
def sample_user(db_session: Session, sample_organization: Organization) -> User:
    """
    Create a test user for authentication in tests.
    """
    # Check if user already exists
    existing_user = db_session.query(User).filter(
        User.email == "test@example.com"
    ).first()
    
    if existing_user:
        return existing_user
    
    user = User(
        email="test@example.com",
        username="testuser",
        first_name="Test",
        last_name="User", 
        organization_id=sample_organization.id,
        status=UserStatus.ACTIVE,
        created_by="test-system",
        updated_by="test-system"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def run_balance_validation_tests():
    """
    Run only the balance-related validation tests.
    
    Usage:
        pytest tests/test_chart_of_accounts_bug_validation.py::TestChartOfAccountBalancePopulation -v
    """
    pass


def run_hierarchy_validation_tests():
    """
    Run only the hierarchy-related validation tests.
    
    Usage:
        pytest tests/test_chart_of_accounts_bug_validation.py::TestChartOfAccountHierarchyLevels -v
        pytest tests/test_chart_of_accounts_bug_validation.py::TestChartOfAccountGroupHierarchy -v
    """
    pass


def run_pagination_validation_tests():
    """
    Run only the pagination-related validation tests.
    
    Usage:
        pytest tests/test_chart_of_accounts_bug_validation.py::TestChartOfAccountPagination -v
    """
    pass


def run_parent_name_validation_tests():
    """
    Run only the parent name population validation tests.
    
    Usage:
        pytest tests/test_chart_of_accounts_bug_validation.py::TestEditAccountDialogParentName -v
    """
    pass


def run_all_validation_tests():
    """
    Run all Chart of Account bug validation tests.
    
    Usage:
        pytest tests/test_chart_of_accounts_bug_validation.py -v
    """
    pass


# Test data helpers

def create_test_account_hierarchy(db_session: Session, organization_id, base_code: str = "TEST"):
    """
    Helper function to create a standard test account hierarchy.
    
    Returns:
        tuple: (parent_account, child_account, grandchild_account)
    """
    from app.models.chart_of_account import Account
    from app.models.base import AccountType, AccountStatus
    
    parent = Account(
        organization_id=organization_id,
        account_code=f"{base_code}00",
        account_name=f"{base_code} Parent Account",
        account_type=AccountType.ASSET,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=False,
        level=1,
        is_group=True,
        created_by="test-user",
        updated_by="test-user",
    )
    
    child = Account( 
        organization_id=organization_id,
        account_code=f"{base_code}10",
        account_name=f"{base_code} Child Account",
        account_type=AccountType.ASSET,
        parent_account_id=parent.id,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=False,
        level=2,
        is_group=True,
        created_by="test-user",
        updated_by="test-user",
    )
    
    grandchild = Account(
        organization_id=organization_id,
        account_code=f"{base_code}11",
        account_name=f"{base_code} Grandchild Account", 
        account_type=AccountType.ASSET,
        parent_account_id=child.id,
        currency="USD",
        status=AccountStatus.ACTIVE,
        is_posting_account=True,
        level=3,
        is_group=False,
        created_by="test-user",
        updated_by="test-user",
    )
    
    db_session.add_all([parent, child, grandchild])
    db_session.commit()
    
    return parent, child, grandchild


def create_test_accounts_for_pagination(db_session: Session, organization_id, count: int = 20):
    """
    Helper function to create multiple test accounts for pagination testing.
    
    Args:
        db_session: Database session
        organization_id: Organization UUID
        count: Number of accounts to create
        
    Returns:
        list: List of created Account objects
    """
    from app.models.chart_of_account import Account
    from app.models.base import AccountType, AccountStatus
    
    accounts = []
    account_types = [AccountType.ASSET, AccountType.LIABILITY, AccountType.EQUITY, 
                    AccountType.REVENUE, AccountType.EXPENSE]
    
    for i in range(count):
        account_type = account_types[i % len(account_types)]
        
        account = Account(
            organization_id=organization_id,
            account_code=f"PA{i:03d}",
            account_name=f"Pagination Test Account {i:02d}",
            account_type=account_type,
            currency="USD",
            status=AccountStatus.ACTIVE,
            is_posting_account=True,
            level=1,
            is_group=False,
            created_by="test-user",
            updated_by="test-user",
        )
        accounts.append(account)
    
    db_session.add_all(accounts)
    db_session.commit()
    
    return accounts


# Assertion helpers

def assert_account_has_balance_fields(account_data: dict):
    """
    Assert that an account data dictionary has the required balance fields.
    
    Args:
        account_data: Account data from API response
    """
    balance_fields = ["current_balance", "opening_balance"]
    
    for field in balance_fields:
        assert field in account_data or hasattr(account_data, field), \
            f"Account should have {field} field for UI display"


def assert_account_has_hierarchy_fields(account_data: dict):
    """
    Assert that an account data dictionary has the required hierarchy fields.
    
    Args:
        account_data: Account data from API response
    """
    hierarchy_fields = ["level", "is_group", "parent_account_id"]
    
    for field in hierarchy_fields:
        # parent_account_id can be None for root accounts
        if field == "parent_account_id":
            assert field in account_data, f"Account should have {field} field"
        else:
            assert field in account_data and account_data[field] is not None, \
                f"Account should have non-null {field} field"


def assert_pagination_metadata_complete(pagination_data: dict):
    """
    Assert that pagination metadata contains all required fields.
    
    Args:
        pagination_data: Pagination data from API response
    """
    required_fields = ["page", "page_size", "total_count", "total_pages", 
                      "has_next", "has_previous"]
    
    for field in required_fields:
        assert field in pagination_data, f"Pagination should include {field}"
        
    # Verify data types
    assert isinstance(pagination_data["page"], int)
    assert isinstance(pagination_data["page_size"], int)
    assert isinstance(pagination_data["total_count"], int)
    assert isinstance(pagination_data["total_pages"], int)
    assert isinstance(pagination_data["has_next"], bool)
    assert isinstance(pagination_data["has_previous"], bool)


def assert_parent_info_complete(account_data: dict):
    """
    Assert that parent account information is complete in account data.
    
    Args:
        account_data: Account data from API response that should include parent info
    """
    if account_data.get("parent_account_id"):
        # If account has a parent, verify parent info is included
        assert "parent" in account_data, "Account with parent should include parent info"
        
        if account_data["parent"]:  # parent info might be null
            parent_info = account_data["parent"]
            required_parent_fields = ["id", "account_code", "account_name"]
            
            for field in required_parent_fields:
                assert field in parent_info, f"Parent info should include {field}"
                assert parent_info[field], f"Parent {field} should not be empty"