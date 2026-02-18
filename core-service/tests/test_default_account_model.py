"""Tests for DefaultAccount model"""

import uuid
import pytest
from sqlalchemy.exc import IntegrityError

from app.models.default_account import DefaultAccount


def test_default_account_creation(db_session):
    """Test creating a default account mapping"""
    # Create a default account
    default_account = DefaultAccount(
        transaction_type="INVENTORY_PURCHASE",
        scenario="DOMESTIC",
        account_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
    )
    
    db_session.add(default_account)
    db_session.commit()
    
    # Verify it was created
    assert default_account.id is not None
    assert default_account.transaction_type == "INVENTORY_PURCHASE"
    assert default_account.scenario == "DOMESTIC"
    assert default_account.created_at is not None
    assert default_account.updated_at is not None


def test_default_account_without_scenario(db_session):
    """Test creating a default account without a scenario"""
    default_account = DefaultAccount(
        transaction_type="SALES_REVENUE",
        scenario=None,
        account_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
    )
    
    db_session.add(default_account)
    db_session.commit()
    
    assert default_account.id is not None
    assert default_account.scenario is None


def test_default_account_multiple_scenarios_same_type(db_session):
    """Test that multiple scenarios can exist for the same transaction type"""
    org_id = uuid.uuid4()
    
    # Create domestic scenario
    default_account1 = DefaultAccount(
        transaction_type="SALES_REVENUE",
        scenario="DOMESTIC",
        account_id=uuid.uuid4(),
        organization_id=org_id,
    )
    db_session.add(default_account1)
    db_session.commit()
    
    # Create international scenario for same transaction type
    default_account2 = DefaultAccount(
        transaction_type="SALES_REVENUE",
        scenario="INTERNATIONAL",
        account_id=uuid.uuid4(),
        organization_id=org_id,
    )
    db_session.add(default_account2)
    db_session.commit()
    
    # Both should exist
    assert default_account1.id is not None
    assert default_account2.id is not None
    assert default_account1.transaction_type == default_account2.transaction_type
    assert default_account1.scenario != default_account2.scenario


def test_default_account_repr(db_session):
    """Test the string representation of DefaultAccount"""
    default_account = DefaultAccount(
        transaction_type="INVENTORY_PURCHASE",
        scenario="INTERNATIONAL",
        account_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
    )
    
    repr_str = repr(default_account)
    assert "DefaultAccount" in repr_str
    assert "INVENTORY_PURCHASE" in repr_str
    assert "INTERNATIONAL" in repr_str


def test_default_account_repr_without_scenario(db_session):
    """Test the string representation without scenario"""
    default_account = DefaultAccount(
        transaction_type="SALES_REVENUE",
        scenario=None,
        account_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
    )
    
    repr_str = repr(default_account)
    assert "DefaultAccount" in repr_str
    assert "SALES_REVENUE" in repr_str
    assert "scenario" not in repr_str
