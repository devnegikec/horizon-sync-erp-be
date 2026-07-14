"""
Unit tests for TransactionImporter

Tests CSV, PDF, and MT940 import functionality with validation and duplicate detection.
"""

import io
import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction
from app.models.chart_of_account import Account
from app.services.transaction_importer import TransactionImporter, ImportResult


# db_session fixture is provided by conftest.py


@pytest.fixture
def organization_id():
    """Provide a test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def gl_account(db_session: Session, organization_id: uuid.UUID):
    """Create a test GL account"""
    account = Account(
        organization_id=organization_id,
        account_code="1000",
        account_name="Test Bank Account",
        account_type="asset",
        currency="USD",
        is_group=False,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


@pytest.fixture
def bank_account(db_session: Session, organization_id: uuid.UUID, gl_account: Account):
    """Create a test bank account"""
    account = BankAccount(
        organization_id=organization_id,
        gl_account_id=gl_account.id,
        bank_name="Test Bank",
        account_holder_name="Test Holder",
        account_number="1234567890",
        country_code="US",
        currency="USD",
        is_primary=True,
        is_active=True,
        created_by="test_user",
        updated_by="test_user"
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


class TestTransactionImporterCSV:
    """Test suite for CSV import functionality"""
    
    def test_import_csv_valid_file(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """Test importing a valid CSV file"""
        importer = TransactionImporter(db_session)
        
        csv_content = b"""date,amount,description,reference,type
2024-01-15,1500.00,Customer Payment,TXN-001,credit
2024-01-16,250.50,Office Supplies,TXN-002,debit"""
        
        result = importer.import_csv(
            bank_account_id=bank_account.id,
            file_content=csv_content,
            organization_id=organization_id
        )
        
        assert result.imported_count == 2
        assert result.skipped_count == 0
        assert result.failed_count == 0
        assert len(result.errors) == 0
        
        # Verify transactions were created
        transactions = db_session.query(BankTransaction).filter(
            BankTransaction.bank_account_id == bank_account.id
        ).all()
        
        assert len(transactions) == 2
        assert transactions[0].transaction_amount == Decimal('1500.00')
        assert transactions[0].transaction_type == 'credit'
        assert transactions[1].transaction_amount == Decimal('250.50')
        assert transactions[1].transaction_type == 'debit'
    
    def test_import_csv_missing_columns(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """Test importing CSV with missing required columns"""
        importer = TransactionImporter(db_session)
        
        csv_content = b"""date,amount,description
2024-01-15,1500.00,Customer Payment"""
        
        with pytest.raises(ValidationError) as exc_info:
            importer.import_csv(
                bank_account_id=bank_account.id,
                file_content=csv_content,
                organization_id=organization_id
            )
        
        assert "missing required columns" in str(exc_info.value).lower()
    
    def test_import_csv_invalid_date_format(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """Test importing CSV with invalid date format"""
        importer = TransactionImporter(db_session)
        
        csv_content = b"""date,amount,description,reference,type
15/01/2024,1500.00,Customer Payment,TXN-001,credit"""
        
        result = importer.import_csv(
            bank_account_id=bank_account.id,
            file_content=csv_content,
            organization_id=organization_id
        )
        
        assert result.imported_count == 0
        assert result.failed_count == 1
        assert len(result.errors) > 0
        assert "ISO 8601" in result.errors[0]
    
    def test_import_csv_invalid_amount(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """Test importing CSV with invalid amount"""
        importer = TransactionImporter(db_session)
        
        csv_content = b"""date,amount,description,reference,type
2024-01-15,invalid,Customer Payment,TXN-001,credit"""
        
        result = importer.import_csv(
            bank_account_id=bank_account.id,
            file_content=csv_content,
            organization_id=organization_id
        )
        
        assert result.imported_count == 0
        assert result.failed_count == 1
        assert len(result.errors) > 0
        assert "numeric" in result.errors[0].lower()
    
    def test_import_csv_invalid_type(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """Test importing CSV with invalid transaction type"""
        importer = TransactionImporter(db_session)
        
        csv_content = b"""date,amount,description,reference,type
2024-01-15,1500.00,Customer Payment,TXN-001,invalid"""
        
        result = importer.import_csv(
            bank_account_id=bank_account.id,
            file_content=csv_content,
            organization_id=organization_id
        )
        
        assert result.imported_count == 0
        assert result.failed_count == 1
        assert len(result.errors) > 0
        assert "debit" in result.errors[0].lower() or "credit" in result.errors[0].lower()
    
    def test_import_csv_duplicate_detection(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """Test duplicate detection during CSV import"""
        importer = TransactionImporter(db_session)
        
        # First import
        csv_content = b"""date,amount,description,reference,type
2024-01-15,1500.00,Customer Payment,TXN-001,credit"""
        
        result1 = importer.import_csv(
            bank_account_id=bank_account.id,
            file_content=csv_content,
            organization_id=organization_id
        )
        
        assert result1.imported_count == 1
        
        # Second import with same data
        result2 = importer.import_csv(
            bank_account_id=bank_account.id,
            file_content=csv_content,
            organization_id=organization_id
        )
        
        assert result2.imported_count == 0
        assert result2.skipped_count == 1
        assert len(result2.warnings) > 0
        assert "duplicate" in result2.warnings[0].lower()
    
    def test_import_csv_force_import_duplicates(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """Test force importing duplicates"""
        importer = TransactionImporter(db_session)
        
        # First import
        csv_content = b"""date,amount,description,reference,type
2024-01-15,1500.00,Customer Payment,TXN-001,credit"""
        
        result1 = importer.import_csv(
            bank_account_id=bank_account.id,
            file_content=csv_content,
            organization_id=organization_id
        )
        
        assert result1.imported_count == 1
        
        # Second import with force_import=True
        result2 = importer.import_csv(
            bank_account_id=bank_account.id,
            file_content=csv_content,
            organization_id=organization_id,
            force_import=True
        )
        
        assert result2.imported_count == 1
        assert result2.skipped_count == 0
        
        # Verify duplicate flag is set
        transactions = db_session.query(BankTransaction).filter(
            BankTransaction.bank_account_id == bank_account.id,
            BankTransaction.is_duplicate == True
        ).all()
        
        assert len(transactions) == 1


class TestTransactionImporterMT940:
    """Test suite for MT940 import functionality"""
    
    def test_import_mt940_valid_file(
        self,
        db_session: Session,
        bank_account: BankAccount,
        organization_id: uuid.UUID
    ):
        """Test importing a valid MT940 file"""
        importer = TransactionImporter(db_session)
        
        mt940_content = """:60F:C240115EUR5000,00
:61:2401150115DR250,50NTRFNONREF//TXN-12345
:86:Office Supplies Payment
:61:2401160116CR1500,00NTRFNONREF//TXN-12346
:86:Customer Payment
:62F:C240116EUR6250,50"""
        
        result = importer.import_mt940(
            bank_account_id=bank_account.id,
            file_content=mt940_content,
            organization_id=organization_id
        )
        
        assert result.imported_count == 2
        assert result.skipped_count == 0
        assert result.failed_count == 0
        
        # Verify transactions were created
        transactions = db_session.query(BankTransaction).filter(
            BankTransaction.bank_account_id == bank_account.id
        ).order_by(BankTransaction.statement_date).all()
        
        assert len(transactions) == 2
        assert transactions[0].transaction_amount == Decimal('250.50')
        assert transactions[0].transaction_type == 'debit'
        assert transactions[0].transaction_description == 'Office Supplies Payment'
        assert transactions[1].transaction_amount == Decimal('1500.00')
        assert transactions[1].transaction_type == 'credit'
        assert transactions[1].transaction_description == 'Customer Payment'


class TestTransactionImporterHelpers:
    """Test suite for helper methods"""
    
    def test_parse_date_iso_format(self, db_session: Session):
        """Test date parsing with ISO 8601 format"""
        importer = TransactionImporter(db_session)
        
        result = importer._parse_date('2024-01-15')
        assert result == date(2024, 1, 15)
    
    def test_parse_date_dd_mm_yyyy_format(self, db_session: Session):
        """Test date parsing with DD/MM/YYYY format"""
        importer = TransactionImporter(db_session)
        
        result = importer._parse_date('15/01/2024')
        assert result == date(2024, 1, 15)
    
    def test_parse_date_mm_dd_yyyy_format(self, db_session: Session):
        """Test date parsing with MM/DD/YYYY format"""
        importer = TransactionImporter(db_session)
        
        result = importer._parse_date('01/15/2024')
        assert result == date(2024, 1, 15)
    
    def test_parse_date_invalid_format(self, db_session: Session):
        """Test date parsing with invalid format"""
        importer = TransactionImporter(db_session)
        
        with pytest.raises(ValidationError) as exc_info:
            importer._parse_date('invalid-date')
        
        assert "unrecognized date format" in str(exc_info.value).lower()
