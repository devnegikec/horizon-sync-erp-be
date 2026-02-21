"""Batch Payment Processor Service

This service handles batch processing of multiple payment entries in a single transaction.
It validates all entries before processing any, ensuring atomic operations.
"""

import csv
import io
from decimal import Decimal
from typing import BinaryIO
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.schemas.payment_entry import (
    BatchProcessResult,
    PaymentEntryCreate,
)
from app.services.allocation_service import AllocationService
from app.services.payment_entry_service import PaymentEntryService


class BatchPaymentProcessor:
    """
    Service for processing multiple payment entries in batch.
    
    Validates all entries before processing any to ensure atomicity.
    Supports CSV import with parsing and validation.
    """

    def __init__(
        self,
        db: Session,
        payment_service: PaymentEntryService | None = None,
        allocation_service: AllocationService | None = None,
    ):
        """
        Initialize BatchPaymentProcessor with dependencies.
        
        Args:
            db: Database session
            payment_service: Payment entry service (created if not provided)
            allocation_service: Allocation service (created if not provided)
        """
        self.db = db
        self.payment_service = payment_service or PaymentEntryService(db)
        self.allocation_service = allocation_service or AllocationService(db)

    def validate_batch(
        self,
        payments: list[PaymentEntryCreate],
        organization_id: UUID,
    ) -> list[dict]:
        """
        Validate all payment entries in the batch.
        
        Returns list of validation errors. Empty list means all valid.
        
        Args:
            payments: List of payment entry creation schemas
            organization_id: Organization UUID
            
        Returns:
            List of error dicts with 'index' and 'message' keys
        """
        errors = []

        if not payments:
            errors.append({
                "index": -1,
                "message": "Batch cannot be empty. At least one payment is required."
            })
            return errors

        for idx, payment_data in enumerate(payments):
            try:
                # Validate payment_type
                if payment_data.payment_type not in ["Customer_Payment", "Supplier_Payment"]:
                    errors.append({
                        "index": idx,
                        "message": f"Invalid payment_type: {payment_data.payment_type}. "
                                   "Must be 'Customer_Payment' or 'Supplier_Payment'."
                    })

                # Validate payment_mode
                if payment_data.payment_mode not in ["Cash", "Check", "Bank_Transfer"]:
                    errors.append({
                        "index": idx,
                        "message": f"Invalid payment_mode: {payment_data.payment_mode}. "
                                   "Must be 'Cash', 'Check', or 'Bank_Transfer'."
                    })

                # Validate reference_no requirement for Check and Bank_Transfer
                if payment_data.payment_mode in ["Check", "Bank_Transfer"]:
                    if not payment_data.reference_no or not payment_data.reference_no.strip():
                        errors.append({
                            "index": idx,
                            "message": f"reference_no is required for {payment_data.payment_mode} payments."
                        })

                # Validate amount
                if payment_data.amount <= 0:
                    errors.append({
                        "index": idx,
                        "message": f"Amount must be greater than zero. Got: {payment_data.amount}"
                    })

                # Check decimal places (max 2)
                amount_str = str(payment_data.amount)
                if '.' in amount_str:
                    decimal_places = len(amount_str.split('.')[1])
                    if decimal_places > 2:
                        errors.append({
                            "index": idx,
                            "message": f"Amount must have at most 2 decimal places. Got: {payment_data.amount}"
                        })

                # Validate currency code (basic check - full validation in schema)
                if not payment_data.currency_code or len(payment_data.currency_code) != 3:
                    errors.append({
                        "index": idx,
                        "message": f"Invalid currency_code: {payment_data.currency_code}. "
                                   "Must be 3-letter ISO 4217 code."
                    })

            except Exception as e:
                errors.append({
                    "index": idx,
                    "message": f"Validation error: {str(e)}"
                })

        return errors

    def process_batch(
        self,
        payments: list[PaymentEntryCreate],
        organization_id: UUID,
        user_id: UUID,
    ) -> BatchProcessResult:
        """
        Process multiple payment entries in a single transaction.
        
        Validates all entries before processing any. If any validation fails,
        returns all errors without creating any payments.
        
        Args:
            payments: List of payment entry creation schemas
            organization_id: Organization UUID
            user_id: User performing the batch operation
            
        Returns:
            BatchProcessResult with success/error counts and details
            
        Raises:
            ValidationError: If any payment fails validation (with all errors)
        """
        from app.models.payment_entry import PaymentEntry

        # Validate all entries first
        validation_errors = self.validate_batch(payments, organization_id)

        if validation_errors:
            # Return all validation errors without creating any payments
            return BatchProcessResult(
                total_count=len(payments),
                success_count=0,
                error_count=len(validation_errors),
                errors=validation_errors,
            )

        # All validations passed - create all payments in single transaction
        created_payments = []
        errors = []

        try:
            # Begin transaction (using existing session)
            for idx, payment_data in enumerate(payments):
                try:
                    # Create payment entry
                    payment = self.payment_service.create_payment_entry(
                        data=payment_data,
                        organization_id=organization_id,
                        user_id=user_id,
                    )
                    created_payments.append(payment)

                except Exception as e:
                    # Record error but continue to collect all errors
                    errors.append({
                        "index": idx,
                        "message": f"Failed to create payment: {str(e)}"
                    })

            # If any errors occurred during creation, rollback
            if errors:
                self.db.rollback()
                return BatchProcessResult(
                    total_count=len(payments),
                    success_count=0,
                    error_count=len(errors),
                    errors=errors,
                )

            # Commit transaction
            self.db.commit()

            # Refresh all created payments to get computed fields
            for payment in created_payments:
                self.db.refresh(payment)

            return BatchProcessResult(
                total_count=len(payments),
                success_count=len(created_payments),
                error_count=0,
                errors=[],
            )

        except Exception as e:
            # Rollback on any unexpected error
            self.db.rollback()
            return BatchProcessResult(
                total_count=len(payments),
                success_count=0,
                error_count=len(payments),
                errors=[{
                    "index": -1,
                    "message": f"Batch processing failed: {str(e)}"
                }],
            )

    def import_from_csv(
        self,
        csv_file: BinaryIO,
        organization_id: UUID,
        user_id: UUID,
    ) -> BatchProcessResult:
        """
        Import and process payments from CSV file.
        
        Expected CSV format:
        payment_type,party_id,amount,currency_code,payment_date,payment_mode,reference_no
        
        Args:
            csv_file: CSV file object (binary mode)
            organization_id: Organization UUID
            user_id: User performing the import
            
        Returns:
            BatchProcessResult with success/error counts and details
        """
        from datetime import datetime

        errors = []
        payments = []

        try:
            # Read CSV file
            csv_content = csv_file.read()
            if isinstance(csv_content, bytes):
                csv_content = csv_content.decode('utf-8')

            csv_reader = csv.DictReader(io.StringIO(csv_content))

            # Validate CSV headers
            required_headers = {
                'payment_type',
                'party_id',
                'amount',
                'payment_date',
                'payment_mode',
            }

            if not csv_reader.fieldnames:
                return BatchProcessResult(
                    total_count=0,
                    success_count=0,
                    error_count=1,
                    errors=[{
                        "index": -1,
                        "message": "CSV file is empty or has no headers"
                    }],
                )

            actual_headers = set(csv_reader.fieldnames)
            missing_headers = required_headers - actual_headers

            if missing_headers:
                return BatchProcessResult(
                    total_count=0,
                    success_count=0,
                    error_count=1,
                    errors=[{
                        "index": -1,
                        "message": f"Missing required CSV columns: {', '.join(missing_headers)}"
                    }],
                )

            # Parse CSV rows
            for idx, row in enumerate(csv_reader):
                try:
                    # Parse payment_date
                    try:
                        payment_date = datetime.fromisoformat(row['payment_date'])
                    except ValueError:
                        errors.append({
                            "index": idx,
                            "message": f"Invalid payment_date format: {row['payment_date']}. "
                                       "Expected ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"
                        })
                        continue

                    # Parse amount
                    try:
                        amount = Decimal(row['amount'])
                    except (ValueError, TypeError):
                        errors.append({
                            "index": idx,
                            "message": f"Invalid amount: {row['amount']}. Must be a valid decimal number."
                        })
                        continue

                    # Parse party_id
                    try:
                        party_id = UUID(row['party_id'])
                    except (ValueError, TypeError):
                        errors.append({
                            "index": idx,
                            "message": f"Invalid party_id: {row['party_id']}. Must be a valid UUID."
                        })
                        continue

                    # Create PaymentEntryCreate schema
                    payment_data = PaymentEntryCreate(
                        payment_type=row['payment_type'],
                        party_id=party_id,
                        amount=amount,
                        currency_code=row.get('currency_code', 'USD'),
                        payment_date=payment_date,
                        payment_mode=row['payment_mode'],
                        reference_no=row.get('reference_no'),
                    )

                    payments.append(payment_data)

                except Exception as e:
                    errors.append({
                        "index": idx,
                        "message": f"Failed to parse CSV row: {str(e)}"
                    })

            # If parsing errors occurred, return them
            if errors:
                return BatchProcessResult(
                    total_count=len(payments) + len(errors),
                    success_count=0,
                    error_count=len(errors),
                    errors=errors,
                )

            # Process the batch
            return self.process_batch(payments, organization_id, user_id)

        except Exception as e:
            return BatchProcessResult(
                total_count=0,
                success_count=0,
                error_count=1,
                errors=[{
                    "index": -1,
                    "message": f"CSV import failed: {str(e)}"
                }],
            )
