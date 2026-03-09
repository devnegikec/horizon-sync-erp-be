"""
Tests for bank reconciliation endpoints

Tests the FastAPI endpoints for bank reconciliation operations.
"""

import uuid
from datetime import date, datetime, UTC
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction
from app.models.bank_reconciliation import BankReconciliation
from app.models.chart_of_account import Account
from app.models.journal_entry import JournalEntry
from app.models.base import JournalStatus


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Mock authentication headers"""
    # In a real test, you would generate a valid JWT token
    # For now, we'll assume the endpoint is accessible
    return {"Authorization": "Bearer mock-token"}


@pytest.fixture
def gl_account(db_session: Session, sample_organization_id: uuid.UUID) -> Account:
    """Create a test GL account"""
    account = Account(
        organization_id=sample_organization_id,
        account_code="1000",
        account_name="Test Bank Account",
        account_type="Bank",
        currency="USD",
        is_active=True
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def bank_account(
    db_session: Session,
    gl_account: Account,
    sample_organization_id: uuid.UUID
) -> BankAccount:
    """Create a test bank account"""
    account = BankAccount(
        organization_id=sample_organization_id,
        gl_account_id=gl_account.id,
        bank_name="Test Bank",
        account_holder_name="Test Holder",
        account_number="1234567890",
        country_code="US",
        currency="USD",
        is_active=True,
        is_primary=True,
        created_by="test@example.com",
        updated_by="test@example.com"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def bank_transaction(
    db_session: Session,
    bank_account: BankAccount,
    sample_organization_id: uuid.UUID
) -> BankTransaction:
    """Create a test bank transaction"""
    transaction = BankTransaction(
        organization_id=sample_organization_id,
        bank_account_id=bank_account.id,
        statement_date=date(2024, 1, 15),
        transaction_amount=Decimal("1500.00"),
        transaction_description="Customer Payment",
        bank_reference="TXN-001",
        transaction_status="cleared",
        transaction_type="credit",
        imported_at=datetime.now(UTC)
    )
    db_session.add(transaction)
    db_session.commit()
    db_session.refresh(transaction)
    return transaction


@pytest.fixture
def journal_entry(
    db_session: Session,
    gl_account: Account,
    sample_organization_id: uuid.UUID
) -> JournalEntry:
    """Create a test journal entry"""
    entry = JournalEntry(
        organization_id=sample_organization_id,
        entry_no="JE-001",
        posting_date=datetime(2024, 1, 15),
        status=JournalStatus.POSTED,
        reference_id="TXN-001",
        total_debit=Decimal("1500.00"),
        total_credit=Decimal("1500.00"),
        created_by="test@example.com"
    )
    db_session.add(entry)
    db_session.commit()
    db_session.refresh(entry)
    return entry


class TestReconciliationEndpoints:
    """Test suite for reconciliation endpoints"""
    
    def test_get_unreconciled_transactions_endpoint_exists(self, client):
        """Test that unreconciled transactions endpoint exists"""
        # This will fail without proper authentication but tests endpoint exists
        response = client.get(
            "/api/v1/reconciliations/unreconciled-transactions",
            params={
                "bank_account_id": str(uuid.uuid4()),
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            }
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_get_unreconciled_journal_entries_endpoint_exists(self, client):
        """Test that unreconciled journal entries endpoint exists"""
        response = client.get(
            "/api/v1/reconciliations/unreconciled-journal-entries",
            params={
                "gl_account_id": str(uuid.uuid4()),
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            }
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_create_manual_reconciliation_endpoint_exists(self, client):
        """Test that manual reconciliation endpoint exists"""
        response = client.post(
            "/api/v1/reconciliations/manual",
            json={
                "bank_transaction_id": str(uuid.uuid4()),
                "journal_entry_ids": [str(uuid.uuid4())],
                "notes": "Test reconciliation"
            }
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403, 422], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_create_many_to_one_reconciliation_endpoint_exists(self, client):
        """Test that many-to-one reconciliation endpoint exists"""
        response = client.post(
            "/api/v1/reconciliations/many-to-one",
            json={
                "bank_transaction_id": str(uuid.uuid4()),
                "journal_entry_ids": [str(uuid.uuid4()), str(uuid.uuid4())],
                "notes": "Test many-to-one"
            }
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403, 422], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_run_auto_reconciliation_endpoint_exists(self, client):
        """Test that auto-reconciliation endpoint exists"""
        response = client.post(
            "/api/v1/reconciliations/auto-run",
            json={
                "bank_account_id": str(uuid.uuid4()),
                "date_from": "2024-01-01",
                "date_to": "2024-01-31"
            }
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403, 422], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_confirm_suggested_match_endpoint_exists(self, client):
        """Test that confirm suggested match endpoint exists"""
        reconciliation_id = uuid.uuid4()
        response = client.post(
            f"/api/v1/reconciliations/{reconciliation_id}/confirm"
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403, 422], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_reject_suggested_match_endpoint_exists(self, client):
        """Test that reject suggested match endpoint exists"""
        reconciliation_id = uuid.uuid4()
        response = client.post(
            f"/api/v1/reconciliations/{reconciliation_id}/reject",
            json={"reason": "Test rejection"}
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403, 422], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_undo_reconciliation_endpoint_exists(self, client):
        """Test that undo reconciliation endpoint exists"""
        reconciliation_id = uuid.uuid4()
        response = client.post(
            f"/api/v1/reconciliations/{reconciliation_id}/undo",
            json={"reason": "Test undo"}
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403, 422], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_get_suggested_matches_endpoint_exists(self, client):
        """Test that suggested matches endpoint exists"""
        response = client.get(
            "/api/v1/reconciliations/suggested"
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403], \
            f"Endpoint should exist (got {response.status_code})"
