"""
Tests for bank transaction import endpoints

Tests the FastAPI endpoints for importing transactions from CSV, PDF, and MT940 files.
"""

import io
import uuid
from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction
from app.models.chart_of_account import Account


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


class TestTransactionImportEndpoints:
    """Test suite for transaction import endpoints"""
    
    def test_import_csv_endpoint_structure(self, client, bank_account):
        """Test that CSV import endpoint exists and has correct structure"""
        # This is a basic structure test - actual authentication would be needed
        # for a full integration test
        
        csv_content = """date,amount,description,reference,type
2024-01-15,1500.00,Customer Payment,TXN-001,credit
2024-01-16,250.50,Office Supplies,TXN-002,debit"""
        
        # Note: This will fail without proper authentication
        # but it tests that the endpoint exists
        response = client.post(
            f"/api/v1/bank-accounts/{bank_account.id}/import/csv",
            files={"file": ("test.csv", csv_content, "text/csv")}
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403, 422], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_import_pdf_endpoint_structure(self, client, bank_account):
        """Test that PDF import endpoint exists"""
        response = client.post(
            f"/api/v1/bank-accounts/{bank_account.id}/import/pdf",
            files={"file": ("test.pdf", b"fake pdf content", "application/pdf")}
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403, 422], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_import_mt940_endpoint_structure(self, client, bank_account):
        """Test that MT940 import endpoint exists"""
        mt940_content = """:60F:C240115EUR5000,00
:61:2401150115DR250,50NTRFNONREF//TXN-12345
:86:Office Supplies Payment
:62F:C240115EUR4750,50"""
        
        response = client.post(
            f"/api/v1/bank-accounts/{bank_account.id}/import/mt940",
            files={"file": ("test.mt940", mt940_content, "text/plain")}
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403, 422], \
            f"Endpoint should exist (got {response.status_code})"
    
    def test_list_transactions_endpoint_structure(self, client, bank_account):
        """Test that list transactions endpoint exists"""
        response = client.get(
            f"/api/v1/bank-accounts/{bank_account.id}/transactions"
        )
        
        # We expect 401 or 403 without auth, not 404
        assert response.status_code in [401, 403, 422], \
            f"Endpoint should exist (got {response.status_code})"


class TestTransactionListEndpoint:
    """Test suite for transaction list endpoint"""
    
    def test_list_transactions_with_filters(
        self,
        db_session: Session,
        bank_account: BankAccount,
        sample_organization_id: uuid.UUID
    ):
        """Test listing transactions with various filters"""
        # Create test transactions
        transactions = [
            BankTransaction(
                organization_id=sample_organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2024, 1, 15),
                transaction_amount=Decimal('1500.00'),
                transaction_description='Customer Payment',
                bank_reference='TXN-001',
                transaction_status='cleared',
                transaction_type='credit',
                import_source='csv'
            ),
            BankTransaction(
                organization_id=sample_organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2024, 1, 16),
                transaction_amount=Decimal('250.50'),
                transaction_description='Office Supplies',
                bank_reference='TXN-002',
                transaction_status='cleared',
                transaction_type='debit',
                import_source='csv'
            ),
            BankTransaction(
                organization_id=sample_organization_id,
                bank_account_id=bank_account.id,
                statement_date=date(2024, 1, 17),
                transaction_amount=Decimal('500.00'),
                transaction_description='Rent Payment',
                bank_reference='TXN-003',
                transaction_status='reconciled',
                transaction_type='debit',
                import_source='csv'
            )
        ]
        
        for txn in transactions:
            db_session.add(txn)
        db_session.commit()
        
        # Test: Get all transactions
        all_txns = db_session.query(BankTransaction).filter(
            BankTransaction.bank_account_id == bank_account.id
        ).all()
        assert len(all_txns) == 3
        
        # Test: Filter by status
        cleared_txns = db_session.query(BankTransaction).filter(
            BankTransaction.bank_account_id == bank_account.id,
            BankTransaction.transaction_status == 'cleared'
        ).all()
        assert len(cleared_txns) == 2
        
        # Test: Filter by type
        debit_txns = db_session.query(BankTransaction).filter(
            BankTransaction.bank_account_id == bank_account.id,
            BankTransaction.transaction_type == 'debit'
        ).all()
        assert len(debit_txns) == 2
        
        # Test: Filter by date range
        date_filtered = db_session.query(BankTransaction).filter(
            BankTransaction.bank_account_id == bank_account.id,
            BankTransaction.statement_date >= date(2024, 1, 16)
        ).all()
        assert len(date_filtered) == 2
