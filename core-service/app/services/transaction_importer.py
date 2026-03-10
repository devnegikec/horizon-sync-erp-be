"""
Transaction Importer Service

Imports bank transactions from CSV, PDF, and MT940 file formats.
Validates data, detects duplicates, and creates bank_transaction records.

Requirements: 11.1-11.17, 12.1-12.11, 20.1-20.10
"""

import csv
import io
import logging
import re
import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction

logger = logging.getLogger(__name__)


@dataclass
class ImportResult:
    """Result of a transaction import operation"""
    imported_count: int
    skipped_count: int
    failed_count: int
    errors: List[str]
    warnings: List[str]
    batch_id: UUID


@dataclass
class TransactionRow:
    """Represents a single transaction row from import"""
    statement_date: date
    transaction_amount: Decimal
    transaction_description: str
    bank_reference: str
    transaction_type: str
    row_number: Optional[int] = None


class TransactionImporter:
    """
    Service for importing bank transactions from various file formats.
    
    Supports CSV, PDF, and MT940 formats with validation and duplicate detection.
    """

    def __init__(self, db: Session):
        """
        Initialize the transaction importer.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def import_csv(
        self,
        bank_account_id: UUID,
        file_content: bytes,
        organization_id: UUID,
        force_import: bool = False
    ) -> ImportResult:
        """
        Import bank transactions from CSV file.
        
        CSV Format: date,amount,description,reference,type
        
        Args:
            bank_account_id: Bank account UUID
            file_content: CSV file content as bytes
            organization_id: Organization UUID
            force_import: If True, import duplicates with is_duplicate flag
            
        Returns:
            ImportResult with counts and errors
            
        Raises:
            ValidationError: If CSV format is invalid
            
        Requirements: 11.1, 11.3, 11.4, 11.5, 11.6, 11.11, 11.12, 11.13, 11.14, 11.15
        """
        # Verify bank account exists
        bank_account = self._get_bank_account(bank_account_id, organization_id)
        
        # Generate batch ID for this import
        batch_id = uuid.uuid4()
        
        # Parse CSV content
        try:
            csv_text = file_content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(csv_text))
        except Exception as e:
            raise ValidationError(f"Failed to parse CSV file: {str(e)}")
        
        # Validate required columns
        required_columns = {'date', 'amount', 'description', 'reference', 'type'}
        if csv_reader.fieldnames is None:
            raise ValidationError("CSV file is empty or has no header row")
        
        actual_columns = set(csv_reader.fieldnames)
        missing_columns = required_columns - actual_columns
        
        if missing_columns:
            raise ValidationError(
                f"CSV file is missing required columns: {', '.join(missing_columns)}"
            )
        
        # Process rows
        transactions: List[TransactionRow] = []
        errors: List[str] = []
        warnings: List[str] = []
        
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            try:
                transaction = self._parse_csv_row(row, row_num)
                transactions.append(transaction)
            except ValidationError as e:
                errors.append(f"Row {row_num}: {str(e)}")
        
        # If there were parsing errors, return early
        if errors:
            return ImportResult(
                imported_count=0,
                skipped_count=0,
                failed_count=len(errors),
                errors=errors,
                warnings=warnings,
                batch_id=batch_id
            )
        
        # Detect duplicates
        duplicates = self._detect_duplicates(
            bank_account_id,
            transactions,
            organization_id
        )
        
        # Import transactions
        imported_count = 0
        skipped_count = 0
        
        for transaction in transactions:
            is_duplicate = transaction in duplicates
            
            if is_duplicate and not force_import:
                skipped_count += 1
                warnings.append(
                    f"Skipped duplicate transaction: date={transaction.statement_date}, "
                    f"amount={transaction.transaction_amount}, ref={transaction.bank_reference}"
                )
                continue
            
            # Create bank transaction record
            bank_transaction = BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account_id,
                statement_date=transaction.statement_date,
                transaction_amount=transaction.transaction_amount,
                transaction_description=transaction.transaction_description,
                bank_reference=transaction.bank_reference,
                transaction_status='cleared',
                transaction_type=transaction.transaction_type,
                import_source='csv',
                import_batch_id=batch_id,
                is_duplicate=is_duplicate and force_import
            )
            
            self.db.add(bank_transaction)
            imported_count += 1
        
        # Commit all transactions
        try:
            self.db.commit()
            logger.info(
                f"CSV import completed: imported={imported_count}, "
                f"skipped={skipped_count}, failed={len(errors)}, batch_id={batch_id}"
            )
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to save transactions: {str(e)}")
        
        return ImportResult(
            imported_count=imported_count,
            skipped_count=skipped_count,
            failed_count=len(errors),
            errors=errors,
            warnings=warnings,
            batch_id=batch_id
        )

    def _parse_csv_row(self, row: dict, row_num: int) -> TransactionRow:
        """
        Parse a single CSV row into a TransactionRow.
        
        Args:
            row: Dictionary from CSV reader
            row_num: Row number for error messages
            
        Returns:
            TransactionRow instance
            
        Raises:
            ValidationError: If row data is invalid
            
        Requirements: 11.4, 11.5, 11.6
        """
        errors = []
        
        # Parse date (ISO 8601 format: YYYY-MM-DD)
        try:
            statement_date = datetime.strptime(row['date'].strip(), '%Y-%m-%d').date()
        except ValueError:
            errors.append("date must be in ISO 8601 format (YYYY-MM-DD)")
        
        # Parse amount (numeric with up to 2 decimal places)
        try:
            amount_str = row['amount'].strip()
            transaction_amount = Decimal(amount_str)
            
            # Validate decimal places
            if transaction_amount.as_tuple().exponent < -2:
                errors.append("amount must have at most 2 decimal places")
        except (InvalidOperation, ValueError):
            errors.append("amount must be a valid numeric value")
        
        # Parse type (debit or credit)
        transaction_type = row['type'].strip().lower()
        if transaction_type not in ('debit', 'credit'):
            errors.append("type must be either 'debit' or 'credit'")
        
        # Get description and reference
        transaction_description = row['description'].strip()
        bank_reference = row['reference'].strip()
        
        if errors:
            raise ValidationError(", ".join(errors))
        
        return TransactionRow(
            statement_date=statement_date,
            transaction_amount=transaction_amount,
            transaction_description=transaction_description,
            bank_reference=bank_reference,
            transaction_type=transaction_type,
            row_number=row_num
        )

    def _detect_duplicates(
        self,
        bank_account_id: UUID,
        transactions: List[TransactionRow],
        organization_id: UUID
    ) -> List[TransactionRow]:
        """
        Detect duplicate transactions.
        
        A transaction is considered duplicate if it matches an existing transaction on:
        - bank_account_id
        - statement_date
        - transaction_amount
        - bank_reference
        
        Args:
            bank_account_id: Bank account UUID
            transactions: List of transactions to check
            organization_id: Organization UUID
            
        Returns:
            List of transactions that are duplicates
            
        Requirements: 20.1, 20.2, 20.3, 20.4
        """
        duplicates = []
        
        for transaction in transactions:
            # Query for existing transaction with same key fields
            existing = self.db.query(BankTransaction).filter(
                and_(
                    BankTransaction.bank_account_id == bank_account_id,
                    BankTransaction.organization_id == organization_id,
                    BankTransaction.statement_date == transaction.statement_date,
                    BankTransaction.transaction_amount == transaction.transaction_amount,
                    BankTransaction.bank_reference == transaction.bank_reference
                )
            ).first()
            
            if existing:
                duplicates.append(transaction)
        
        return duplicates

    def _get_bank_account(
        self,
        bank_account_id: UUID,
        organization_id: UUID
    ) -> BankAccount:
        """
        Get bank account by ID and verify organization ownership.
        
        Args:
            bank_account_id: Bank account UUID
            organization_id: Organization UUID
            
        Returns:
            BankAccount instance
            
        Raises:
            ValidationError: If bank account not found
        """
        bank_account = self.db.query(BankAccount).filter(
            and_(
                BankAccount.id == bank_account_id,
                BankAccount.organization_id == organization_id
            )
        ).first()
        
        if not bank_account:
            raise ValidationError(
                f"Bank account {bank_account_id} not found for organization {organization_id}"
            )
        
        return bank_account

    def import_pdf(
        self,
        bank_account_id: UUID,
        file_content: bytes,
        organization_id: UUID,
        force_import: bool = False
    ) -> ImportResult:
        """
        Import bank transactions from PDF file.
        
        Extracts text from PDF and parses transaction data using regex patterns.
        Supports common bank statement formats.
        
        Args:
            bank_account_id: Bank account UUID
            file_content: PDF file content as bytes
            organization_id: Organization UUID
            force_import: If True, import duplicates with is_duplicate flag
            
        Returns:
            ImportResult with counts and errors
            
        Raises:
            ValidationError: If PDF format is not supported
            
        Requirements: 11.2, 11.7, 11.8, 11.9, 11.10, 11.16, 11.17
        """
        # Verify bank account exists
        bank_account = self._get_bank_account(bank_account_id, organization_id)
        
        # Generate batch ID for this import
        batch_id = uuid.uuid4()
        
        # Extract text from PDF
        try:
            import pdfplumber
            
            pdf_text = ""
            with pdfplumber.open(io.BytesIO(file_content)) as pdf:
                # Extract text from all pages
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pdf_text += page_text + "\n"
            
            if not pdf_text.strip():
                raise ValidationError("PDF file contains no extractable text")
                
        except ImportError:
            raise ValidationError(
                "PDF parsing library (pdfplumber) is not installed. "
                "Please install it with: pip install pdfplumber"
            )
        except Exception as e:
            raise ValidationError(f"Failed to extract text from PDF: {str(e)}")
        
        # Parse transactions from text
        try:
            transactions = self._parse_pdf_text(pdf_text)
        except Exception as e:
            raise ValidationError(
                f"PDF format not supported or parsing failed: {str(e)}. "
                "Please use CSV import or contact support for custom PDF format support."
            )
        
        if not transactions:
            raise ValidationError(
                "No transactions found in PDF. The PDF format may not be supported."
            )
        
        # Detect duplicates
        duplicates = self._detect_duplicates(
            bank_account_id,
            transactions,
            organization_id
        )
        
        # Import transactions
        imported_count = 0
        skipped_count = 0
        errors: List[str] = []
        warnings: List[str] = []
        
        for transaction in transactions:
            is_duplicate = transaction in duplicates
            
            if is_duplicate and not force_import:
                skipped_count += 1
                warnings.append(
                    f"Skipped duplicate transaction: date={transaction.statement_date}, "
                    f"amount={transaction.transaction_amount}, ref={transaction.bank_reference}"
                )
                continue
            
            # Create bank transaction record
            bank_transaction = BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account_id,
                statement_date=transaction.statement_date,
                transaction_amount=transaction.transaction_amount,
                transaction_description=transaction.transaction_description,
                bank_reference=transaction.bank_reference,
                transaction_status='cleared',
                transaction_type=transaction.transaction_type,
                import_source='pdf',
                import_batch_id=batch_id,
                is_duplicate=is_duplicate and force_import
            )
            
            self.db.add(bank_transaction)
            imported_count += 1
        
        # Commit all transactions
        try:
            self.db.commit()
            logger.info(
                f"PDF import completed: imported={imported_count}, "
                f"skipped={skipped_count}, failed={len(errors)}, batch_id={batch_id}"
            )
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to save transactions: {str(e)}")
        
        return ImportResult(
            imported_count=imported_count,
            skipped_count=skipped_count,
            failed_count=len(errors),
            errors=errors,
            warnings=warnings,
            batch_id=batch_id
        )

    def _parse_pdf_text(self, pdf_text: str) -> List[TransactionRow]:
        """
        Parse transaction data from PDF text using regex patterns.
        
        Supports common bank statement formats with patterns for:
        - Date (various formats)
        - Amount (with optional currency symbols)
        - Description
        - Reference/Transaction ID
        - Type (debit/credit based on amount sign or column position)
        
        Args:
            pdf_text: Extracted text from PDF
            
        Returns:
            List of TransactionRow instances
            
        Raises:
            ValidationError: If parsing fails
            
        Requirements: 11.8, 11.9
        """
        transactions: List[TransactionRow] = []
        
        # Common transaction patterns
        # Pattern 1: Date | Description | Reference | Debit | Credit
        # Example: 2024-01-15 | Office Supplies | TXN-12345 | 250.50 | 
        pattern1 = re.compile(
            r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\s*\|?\s*'  # Date
            r'([^\|]+?)\s*\|?\s*'  # Description
            r'([A-Z0-9\-]+)\s*\|?\s*'  # Reference
            r'(?:(\d+[,.]?\d*\.?\d{2})\s*\|?\s*(\d+[,.]?\d*\.?\d{2})?|'  # Debit | Credit
            r'(\d+[,.]?\d*\.?\d{2})\s*\|?\s*$)'  # Or single amount
        )
        
        # Pattern 2: Date Description Amount (with +/- sign)
        # Example: 2024-01-15 Customer Payment +1500.00 TXN-12345
        pattern2 = re.compile(
            r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\s+'  # Date
            r'(.+?)\s+'  # Description
            r'([+-]?\d+[,.]?\d*\.?\d{2})\s+'  # Amount with optional sign
            r'([A-Z0-9\-]+)'  # Reference
        )
        
        # Pattern 3: Date | Description | Amount | Balance | Reference
        # Example: 15/01/2024 | Office Supplies | -250.50 | 5000.00 | TXN-12345
        pattern3 = re.compile(
            r'(\d{2}/\d{2}/\d{4}|\d{4}-\d{2}-\d{2})\s*\|?\s*'  # Date
            r'([^\|]+?)\s*\|?\s*'  # Description
            r'([+-]?\d+[,.]?\d*\.?\d{2})\s*\|?\s*'  # Amount
            r'(?:\d+[,.]?\d*\.?\d{2}\s*\|?\s*)?'  # Balance (optional, ignored)
            r'([A-Z0-9\-]+)?'  # Reference (optional)
        )
        
        lines = pdf_text.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:
                continue
            
            # Try pattern 1
            match = pattern1.search(line)
            if match:
                try:
                    transaction = self._parse_pdf_match_pattern1(match, line_num)
                    transactions.append(transaction)
                    continue
                except ValidationError:
                    pass  # Try next pattern
            
            # Try pattern 2
            match = pattern2.search(line)
            if match:
                try:
                    transaction = self._parse_pdf_match_pattern2(match, line_num)
                    transactions.append(transaction)
                    continue
                except ValidationError:
                    pass  # Try next pattern
            
            # Try pattern 3
            match = pattern3.search(line)
            if match:
                try:
                    transaction = self._parse_pdf_match_pattern3(match, line_num)
                    transactions.append(transaction)
                    continue
                except ValidationError:
                    pass  # Skip this line
        
        return transactions

    def _parse_pdf_match_pattern1(
        self,
        match: re.Match,
        line_num: int
    ) -> TransactionRow:
        """Parse transaction from pattern 1: Date | Description | Reference | Debit | Credit"""
        date_str = match.group(1)
        description = match.group(2).strip()
        reference = match.group(3).strip()
        debit = match.group(4)
        credit = match.group(5)
        
        # Parse date
        statement_date = self._parse_date(date_str)
        
        # Determine amount and type
        if debit and debit.strip():
            amount_str = debit.replace(',', '')
            transaction_amount = Decimal(amount_str)
            transaction_type = 'debit'
        elif credit and credit.strip():
            amount_str = credit.replace(',', '')
            transaction_amount = Decimal(amount_str)
            transaction_type = 'credit'
        else:
            raise ValidationError("No amount found")
        
        return TransactionRow(
            statement_date=statement_date,
            transaction_amount=transaction_amount,
            transaction_description=description,
            bank_reference=reference,
            transaction_type=transaction_type,
            row_number=line_num
        )

    def _parse_pdf_match_pattern2(
        self,
        match: re.Match,
        line_num: int
    ) -> TransactionRow:
        """Parse transaction from pattern 2: Date Description +/-Amount Reference"""
        date_str = match.group(1)
        description = match.group(2).strip()
        amount_str = match.group(3).replace(',', '')
        reference = match.group(4).strip()
        
        # Parse date
        statement_date = self._parse_date(date_str)
        
        # Parse amount and determine type from sign
        amount = Decimal(amount_str)
        if amount < 0:
            transaction_type = 'debit'
            transaction_amount = abs(amount)
        else:
            transaction_type = 'credit'
            transaction_amount = amount
        
        return TransactionRow(
            statement_date=statement_date,
            transaction_amount=transaction_amount,
            transaction_description=description,
            bank_reference=reference,
            transaction_type=transaction_type,
            row_number=line_num
        )

    def _parse_pdf_match_pattern3(
        self,
        match: re.Match,
        line_num: int
    ) -> TransactionRow:
        """Parse transaction from pattern 3: Date | Description | +/-Amount | Balance | Reference"""
        date_str = match.group(1)
        description = match.group(2).strip()
        amount_str = match.group(3).replace(',', '')
        reference = match.group(4).strip() if match.group(4) else f"PDF-{line_num}"
        
        # Parse date
        statement_date = self._parse_date(date_str)
        
        # Parse amount and determine type from sign
        amount = Decimal(amount_str)
        if amount < 0:
            transaction_type = 'debit'
            transaction_amount = abs(amount)
        else:
            transaction_type = 'credit'
            transaction_amount = amount
        
        return TransactionRow(
            statement_date=statement_date,
            transaction_amount=transaction_amount,
            transaction_description=description,
            bank_reference=reference,
            transaction_type=transaction_type,
            row_number=line_num
        )

    def _parse_date(self, date_str: str) -> date:
        """
        Parse date from various formats.
        
        Supports:
        - ISO 8601: YYYY-MM-DD
        - US format: MM/DD/YYYY
        - EU format: DD/MM/YYYY
        
        Args:
            date_str: Date string
            
        Returns:
            date object
            
        Raises:
            ValidationError: If date format is not recognized
        """
        # Try ISO 8601 format
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
        
        # Try DD/MM/YYYY format
        try:
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            pass
        
        # Try MM/DD/YYYY format
        try:
            return datetime.strptime(date_str, '%m/%d/%Y').date()
        except ValueError:
            pass
        
        raise ValidationError(f"Unrecognized date format: {date_str}")

    def import_mt940(
        self,
        bank_account_id: UUID,
        file_content: str,
        organization_id: UUID,
        force_import: bool = False
    ) -> ImportResult:
        """
        Import bank transactions from MT940 SWIFT format file.
        
        Parses MT940 standard format with:
        - :60F: Opening balance
        - :61: Transaction statements
        - :86: Transaction details
        - :62F: Closing balance
        
        Args:
            bank_account_id: Bank account UUID
            file_content: MT940 file content as string
            organization_id: Organization UUID
            force_import: If True, import duplicates with is_duplicate flag
            
        Returns:
            ImportResult with counts and errors
            
        Raises:
            ValidationError: If MT940 format is invalid
            
        Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9, 12.10, 12.11
        """
        # Verify bank account exists
        bank_account = self._get_bank_account(bank_account_id, organization_id)
        
        # Generate batch ID for this import
        batch_id = uuid.uuid4()
        
        # Parse MT940 content
        try:
            transactions = self._parse_mt940(file_content)
        except Exception as e:
            raise ValidationError(f"Failed to parse MT940 file: {str(e)}")
        
        if not transactions:
            raise ValidationError("No transactions found in MT940 file")
        
        # Detect duplicates
        duplicates = self._detect_duplicates(
            bank_account_id,
            transactions,
            organization_id
        )
        
        # Import transactions
        imported_count = 0
        skipped_count = 0
        errors: List[str] = []
        warnings: List[str] = []
        
        for transaction in transactions:
            is_duplicate = transaction in duplicates
            
            if is_duplicate and not force_import:
                skipped_count += 1
                warnings.append(
                    f"Skipped duplicate transaction: date={transaction.statement_date}, "
                    f"amount={transaction.transaction_amount}, ref={transaction.bank_reference}"
                )
                continue
            
            # Create bank transaction record
            bank_transaction = BankTransaction(
                organization_id=organization_id,
                bank_account_id=bank_account_id,
                statement_date=transaction.statement_date,
                transaction_amount=transaction.transaction_amount,
                transaction_description=transaction.transaction_description,
                bank_reference=transaction.bank_reference,
                transaction_status='cleared',
                transaction_type=transaction.transaction_type,
                import_source='mt940',
                import_batch_id=batch_id,
                is_duplicate=is_duplicate and force_import
            )
            
            self.db.add(bank_transaction)
            imported_count += 1
        
        # Commit all transactions
        try:
            self.db.commit()
            logger.info(
                f"MT940 import completed: imported={imported_count}, "
                f"skipped={skipped_count}, failed={len(errors)}, batch_id={batch_id}"
            )
        except Exception as e:
            self.db.rollback()
            raise ValidationError(f"Failed to save transactions: {str(e)}")
        
        return ImportResult(
            imported_count=imported_count,
            skipped_count=skipped_count,
            failed_count=len(errors),
            errors=errors,
            warnings=warnings,
            batch_id=batch_id
        )

    def _parse_mt940(self, mt940_content: str) -> List[TransactionRow]:
        """
        Parse MT940 SWIFT format content.
        
        MT940 Format:
        :60F: Opening balance
        :61: Transaction statement
        :86: Transaction details
        :62F: Closing balance
        
        Args:
            mt940_content: MT940 file content
            
        Returns:
            List of TransactionRow instances
            
        Raises:
            ValidationError: If parsing fails
            
        Requirements: 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8, 12.9
        """
        transactions: List[TransactionRow] = []
        
        # Split into lines and process
        lines = mt940_content.split('\n')
        
        current_transaction: Optional[dict] = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Parse opening balance (:60F:)
            if line.startswith(':60F:'):
                # Format: :60F:C240115EUR5000,00
                # C/D = Credit/Debit, Date (YYMMDD), Currency, Amount
                pass  # We don't need to store opening balance
            
            # Parse transaction statement (:61:)
            elif line.startswith(':61:'):
                # Save previous transaction if exists
                if current_transaction:
                    transactions.append(self._create_transaction_from_mt940(current_transaction))
                
                # Format: :61:2401150115DR250,50NTRFNONREF//TXN-12345
                # Value date, Entry date, D/C indicator, Amount, Transaction type, Reference
                current_transaction = self._parse_mt940_transaction_line(line)
            
            # Parse transaction details (:86:)
            elif line.startswith(':86:') and current_transaction:
                # Format: :86:Office Supplies Payment
                description = line[4:].strip()
                current_transaction['description'] = description
            
            # Parse closing balance (:62F:)
            elif line.startswith(':62F:'):
                # Format: :62F:C240115EUR4750,50
                # Save last transaction if exists
                if current_transaction:
                    transactions.append(self._create_transaction_from_mt940(current_transaction))
                    current_transaction = None
        
        # Save last transaction if not saved
        if current_transaction:
            transactions.append(self._create_transaction_from_mt940(current_transaction))
        
        return transactions

    def _parse_mt940_transaction_line(self, line: str) -> dict:
        """
        Parse MT940 :61: transaction line.
        
        Format: :61:YYMMDDMMDD[D/C]Amount[Transaction Type]Reference[//Additional]
        Example: :61:2401150115DR250,50NTRFNONREF//TXN-12345
        
        Args:
            line: MT940 transaction line
            
        Returns:
            Dictionary with transaction data
            
        Raises:
            ValidationError: If line format is invalid
        """
        # Remove :61: prefix
        content = line[4:].strip()
        
        # Parse value date (YYMMDD)
        value_date_str = content[0:6]
        year = int('20' + value_date_str[0:2])
        month = int(value_date_str[2:4])
        day = int(value_date_str[4:6])
        statement_date = date(year, month, day)
        
        # Skip entry date (next 4 chars: MMDD)
        content = content[10:]
        
        # Parse debit/credit indicator
        dc_indicator = content[0:1]
        if dc_indicator == 'D':
            transaction_type = 'debit'
        elif dc_indicator == 'C':
            transaction_type = 'credit'
        else:
            # Sometimes it's 2 chars (DR/CR)
            dc_indicator = content[0:2]
            if dc_indicator == 'DR':
                transaction_type = 'debit'
            elif dc_indicator == 'CR':
                transaction_type = 'credit'
            else:
                raise ValidationError(f"Invalid D/C indicator: {dc_indicator}")
        
        # Remove D/C indicator
        if len(dc_indicator) == 1:
            content = content[1:]
        else:
            content = content[2:]
        
        # Parse amount (until non-digit/comma/period)
        amount_match = re.match(r'([\d,\.]+)', content)
        if not amount_match:
            raise ValidationError("Could not parse amount")
        
        amount_str = amount_match.group(1).replace(',', '.')
        transaction_amount = Decimal(amount_str)
        
        # Remove amount from content
        content = content[len(amount_match.group(1)):]
        
        # Parse transaction type code (optional, e.g., NTRF)
        type_code_match = re.match(r'([A-Z]{4})', content)
        if type_code_match:
            content = content[4:]
        
        # Parse reference
        # Look for // separator
        if '//' in content:
            parts = content.split('//')
            reference = parts[1].strip() if len(parts) > 1 else f"MT940-{statement_date}"
        else:
            # Use remaining content as reference
            reference = content.strip() or f"MT940-{statement_date}"
        
        return {
            'statement_date': statement_date,
            'transaction_amount': transaction_amount,
            'transaction_type': transaction_type,
            'bank_reference': reference,
            'description': ''  # Will be filled from :86: line
        }

    def _create_transaction_from_mt940(self, mt940_data: dict) -> TransactionRow:
        """
        Create TransactionRow from parsed MT940 data.
        
        Args:
            mt940_data: Dictionary with parsed MT940 transaction data
            
        Returns:
            TransactionRow instance
        """
        return TransactionRow(
            statement_date=mt940_data['statement_date'],
            transaction_amount=mt940_data['transaction_amount'],
            transaction_description=mt940_data.get('description', ''),
            bank_reference=mt940_data['bank_reference'],
            transaction_type=mt940_data['transaction_type']
        )
