"""
Test cases for Opening Balance feature
This file demonstrates how to test the opening balance functionality
"""

import json
from decimal import Decimal
from uuid import uuid4
import pytest


def test_create_account_with_opening_balance(client, auth_headers):
    """Test creating an account with opening balance"""
    account_data = {
        "account_code": "TEST-OB-001",
        "account_name": "Test Account with Opening Balance",
        "account_type": "asset",
        "currency": "USD",
        "opening_balance": 5000.00
    }
    
    response = client.post(
        "/api/v1/chart-of-accounts",
        json=account_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify account was created
    assert data["account_code"] == "TEST-OB-001"
    assert data["account_name"] == "Test Account with Opening Balance"
    assert data["account_type"] == "asset"
    assert "id" in data
    
    # The opening_balance should be reflected in the account
    account_id = data["id"]
    
    # Retrieve the account and verify balance
    response = client.get(
        f"/api/v1/chart-of-accounts/{account_id}",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Opening balance should be retrievable
    assert "opening_balance" in data
    

def test_create_account_without_opening_balance(client, auth_headers):
    """Test creating an account without opening balance"""
    account_data = {
        "account_code": "TEST-NO-OB-001",
        "account_name": "Test Account without Opening Balance",
        "account_type": "liability"
    }
    
    response = client.post(
        "/api/v1/chart-of-accounts",
        json=account_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()
    
    # Verify account was created with zero balance
    assert data["opening_balance"] == 0 or data["opening_balance"] == 0.0


def test_asset_opening_balance_creates_debit_entry(client, auth_headers, db_session):
    """
    Test that asset account opening balance creates a DEBIT journal entry
    (Assets natural balance is DEBIT)
    """
    account_data = {
        "account_code": "ASSET-TEST-001",
        "account_name": "Asset Test Account",
        "account_type": "asset",
        "opening_balance": 10000.00
    }
    
    response = client.post(
        "/api/v1/chart-of-accounts",
        json=account_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    account_data = response.json()
    account_id = account_data["id"]
    
    # Verify journal entry was created
    # The journal entry should have:
    # - account_id = account_id
    # - debit = 10000
    # - credit = 0
    # - status = POSTED
    # - voucher_type = "Opening Balance"
    
    from app.models.journal_entry import JournalEntryLine
    lines = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.account_id == account_id
    ).all()
    
    assert len(lines) > 0
    assert float(lines[0].debit) == 10000.00
    assert float(lines[0].credit) == 0.00


def test_liability_opening_balance_creates_credit_entry(client, auth_headers, db_session):
    """
    Test that liability account opening balance creates a CREDIT journal entry
    (Liabilities natural balance is CREDIT)
    """
    account_data = {
        "account_code": "LIABILITY-TEST-001",
        "account_name": "Liability Test Account",
        "account_type": "liability",
        "opening_balance": 5000.00
    }
    
    response = client.post(
        "/api/v1/chart-of-accounts",
        json=account_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    account_data = response.json()
    account_id = account_data["id"]
    
    # Verify journal entry was created
    # The journal entry should have:
    # - account_id = account_id
    # - debit = 0
    # - credit = 5000
    # - status = POSTED
    # - voucher_type = "Opening Balance"
    
    from app.models.journal_entry import JournalEntryLine
    lines = db_session.query(JournalEntryLine).filter(
        JournalEntryLine.account_id == account_id
    ).all()
    
    assert len(lines) > 0
    assert float(lines[0].debit) == 0.00
    assert float(lines[0].credit) == 5000.00


def test_balance_calculator_includes_opening_balance(client, auth_headers):
    """
    Test that balance_calculator correctly includes opening balance
    in calculated balance
    """
    account_data = {
        "account_code": "BALANCE-TEST-001",
        "account_name": "Balance Test Account",
        "account_type": "asset",
        "opening_balance": 25000.00
    }
    
    response = client.post(
        "/api/v1/chart-of-accounts",
        json=account_data,
        headers=auth_headers
    )
    
    assert response.status_code == 201
    account_data = response.json()
    account_id = account_data["id"]
    
    # Retrieve account from list to get calculated balance
    response = client.get(
        "/api/v1/chart-of-accounts",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    list_data = response.json()
    
    # Find our test account in the list
    test_account = None
    for account in list_data["chart_of_accounts"]:
        if account["account_code"] == "BALANCE-TEST-001":
            test_account = account
            break
    
    assert test_account is not None
    
    # opening_balance should match what we provided
    assert float(test_account["opening_balance"]) == 25000.00
    
    # current_balance should also be 25000 (no other transactions)
    assert float(test_account["current_balance"]) == 25000.00


if __name__ == "__main__":
    print("Opening Balance Feature Test Cases")
    print("=" * 50)
    print("\nTo run these tests:")
    print("$ pytest tests/test_opening_balance.py -v")
    print("\nTest Cases:")
    print("1. test_create_account_with_opening_balance")
    print("2. test_create_account_without_opening_balance")
    print("3. test_asset_opening_balance_creates_debit_entry")
    print("4. test_liability_opening_balance_creates_credit_entry")
    print("5. test_balance_calculator_includes_opening_balance")
