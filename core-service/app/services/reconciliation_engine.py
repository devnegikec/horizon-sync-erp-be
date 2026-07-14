"""
Reconciliation Engine Service

Provides methods for manual reconciliation, many-to-one matching, undo operations,
and balance calculations. This is the core service for managing bank reconciliations.

Requirements: 7.1-7.10, 10.1-10.9, 14.8, 14.9, 17.1-17.10
"""

import logging
from datetime import date, datetime, UTC
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.models.bank_transaction import BankTransaction
from app.models.bank_reconciliation import BankReconciliation
from app.models.journal_entry import JournalEntry

logger = logging.getLogger(__name__)


class ReconciliationEngine:
    """
    Service for managing bank reconciliations.
    
    Provides methods for:
    - Retrieving unreconciled transactions and journal entries
    - Creating manual reconciliations
    - Creating many-to-one reconciliations
    - Confirming and rejecting suggested matches
    - Undoing reconciliations
    - Calculating balances and reconciliation differences
    """

    def __init__(self, db: Session):
        """
        Initialize the reconciliation engine.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def get_unreconciled_transactions(
        self,
        bank_account_id: UUID,
        date_from: date,
        date_to: date,
        organization_id: UUID
    ) -> List[BankTransaction]:
        """
        Get unreconciled bank transactions for a given bank account and date range.
        
        Filters transactions with:
        - status = "cleared"
        - reconciled_at is null
        - within the specified date range
        
        Args:
            bank_account_id: UUID of the bank account
            date_from: Start date for filtering
            date_to: End date for filtering
            organization_id: Organization UUID for multi-tenant isolation
            
        Returns:
            List of unreconciled BankTransaction instances
            
        Requirements: 7.1, 14.8
        """
        transactions = (
            self.db.query(BankTransaction)
            .filter(
                and_(
                    BankTransaction.organization_id == organization_id,
                    BankTransaction.bank_account_id == bank_account_id,
                    BankTransaction.transaction_status == "cleared",
                    BankTransaction.reconciled_at.is_(None),
                    BankTransaction.statement_date >= date_from,
                    BankTransaction.statement_date <= date_to
                )
            )
            .order_by(BankTransaction.statement_date)
            .all()
        )
        
        logger.info(
            f"Found {len(transactions)} unreconciled transactions for "
            f"bank_account_id={bank_account_id}, date_range={date_from} to {date_to}"
        )
        
        return transactions

    def get_unreconciled_journal_entries(
        self,
        gl_account_id: UUID,
        date_from: date,
        date_to: date,
        organization_id: UUID
    ) -> List[JournalEntry]:
        """
        Get unreconciled journal entries for a given GL account and date range.
        
        Filters journal entries that:
        - Are posted (status = 'posted')
        - Are within the specified date range
        - Have not been reconciled yet (no active reconciliation)
        
        Args:
            gl_account_id: UUID of the GL account (bank account's linked account)
            date_from: Start date for filtering
            date_to: End date for filtering
            organization_id: Organization UUID for multi-tenant isolation
            
        Returns:
            List of unreconciled JournalEntry instances
            
        Requirements: 7.2, 14.8
        """
        # Get all journal entries in the date range
        journal_entries = (
            self.db.query(JournalEntry)
            .filter(
                and_(
                    JournalEntry.organization_id == organization_id,
                    JournalEntry.posting_date >= date_from,
                    JournalEntry.posting_date <= date_to,
                    JournalEntry.status == "posted"
                )
            )
            .order_by(JournalEntry.posting_date)
            .all()
        )
        
        # Filter out entries that are already reconciled
        unreconciled = []
        for je in journal_entries:
            # Check if this journal entry has any active reconciliations
            has_active_reconciliation = (
                self.db.query(BankReconciliation)
                .filter(
                    and_(
                        BankReconciliation.journal_entry_id == je.id,
                        BankReconciliation.is_active == True,
                        BankReconciliation.reconciliation_status == "confirmed"
                    )
                )
                .first()
            ) is not None
            
            if not has_active_reconciliation:
                unreconciled.append(je)
        
        logger.info(
            f"Found {len(unreconciled)} unreconciled journal entries for "
            f"gl_account_id={gl_account_id}, date_range={date_from} to {date_to}"
        )
        
        return unreconciled

    def calculate_reconciliation_difference(
        self,
        bank_balance: Decimal,
        gl_balance: Decimal
    ) -> Decimal:
        """
        Calculate the difference between bank balance and GL balance.
        
        This represents the unreconciled amount - the difference between what
        the bank shows and what the general ledger shows.
        
        Args:
            bank_balance: Balance calculated from bank transactions
            gl_balance: Balance calculated from journal entries
            
        Returns:
            Decimal representing the difference (bank_balance - gl_balance)
            
        Requirements: 14.9
        """
        difference = Decimal(str(bank_balance)) - Decimal(str(gl_balance))
        
        logger.info(
            f"Calculated reconciliation difference: "
            f"bank_balance={bank_balance}, gl_balance={gl_balance}, "
            f"difference={difference}"
        )
        
        return difference

    def create_manual_match(
        self,
        bank_transaction_id: UUID,
        journal_entry_ids: List[UUID],
        reconciled_by: str,
        organization_id: UUID,
        notes: Optional[str] = None
    ) -> List[BankReconciliation]:
        """
        Create manual reconciliation match(es) between a bank transaction and journal entry(ies).
        
        This method:
        1. Validates that the bank transaction is not already reconciled
        2. Creates reconciliation record(s) with type "manual" and status "confirmed"
        3. Updates the bank transaction status to "reconciled"
        4. Sets reconciled_at timestamp and reconciled_by user
        5. Supports optional notes parameter
        
        Args:
            bank_transaction_id: UUID of the bank transaction to reconcile
            journal_entry_ids: List of journal entry UUIDs to match (typically one, but supports many-to-one)
            reconciled_by: User identifier performing the reconciliation
            organization_id: Organization UUID for multi-tenant isolation
            notes: Optional notes or remarks about the reconciliation
            
        Returns:
            List of created BankReconciliation instances
            
        Raises:
            ValueError: If bank transaction is already reconciled or not found
            ValueError: If any journal entry is not found
            
        Requirements: 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10
        """
        # Fetch the bank transaction
        bank_transaction = (
            self.db.query(BankTransaction)
            .filter(
                and_(
                    BankTransaction.id == bank_transaction_id,
                    BankTransaction.organization_id == organization_id
                )
            )
            .first()
        )
        
        if not bank_transaction:
            raise ValueError(f"Bank transaction {bank_transaction_id} not found")
        
        # Requirement 7.10: Prevent double reconciliation
        if bank_transaction.is_reconciled:
            raise ValueError(
                f"Bank transaction {bank_transaction_id} is already reconciled. "
                f"Cannot reconcile the same transaction twice."
            )
        
        # Check if there are any active reconciliations for this transaction
        existing_reconciliation = (
            self.db.query(BankReconciliation)
            .filter(
                and_(
                    BankReconciliation.bank_transaction_id == bank_transaction_id,
                    BankReconciliation.is_active == True,
                    BankReconciliation.reconciliation_status == "confirmed"
                )
            )
            .first()
        )
        
        if existing_reconciliation:
            raise ValueError(
                f"Bank transaction {bank_transaction_id} already has an active reconciliation. "
                f"Cannot reconcile the same transaction twice."
            )
        
        # Fetch all journal entries
        journal_entries = (
            self.db.query(JournalEntry)
            .filter(
                and_(
                    JournalEntry.id.in_(journal_entry_ids),
                    JournalEntry.organization_id == organization_id
                )
            )
            .all()
        )
        
        if len(journal_entries) != len(journal_entry_ids):
            found_ids = {je.id for je in journal_entries}
            missing_ids = set(journal_entry_ids) - found_ids
            raise ValueError(f"Journal entries not found: {missing_ids}")
        
        # Create reconciliation records
        reconciliations = []
        current_time = datetime.now(UTC)
        
        for journal_entry in journal_entries:
            # Requirement 7.4: Set reconciliation_type to "manual"
            # Requirement 7.5: Set reconciliation_status to "confirmed"
            reconciliation = BankReconciliation(
                organization_id=organization_id,
                bank_transaction_id=bank_transaction_id,
                journal_entry_id=journal_entry.id,
                reconciliation_type="manual",
                reconciliation_status="confirmed",
                match_confidence=Decimal("1.0"),  # Manual matches have full confidence
                reconciled_by=reconciled_by,  # Requirement 7.8: Store user identifier
                reconciled_at=current_time,  # Requirement 7.7: Set reconciled_at timestamp
                notes=notes,  # Requirement 7.9: Support notes parameter
                is_active=True
            )
            
            self.db.add(reconciliation)
            reconciliations.append(reconciliation)
        
        # Requirement 7.6: Update bank transaction status to "reconciled"
        bank_transaction.transaction_status = "reconciled"
        bank_transaction.reconciled_at = current_time
        
        # Commit the transaction
        self.db.commit()
        
        # Refresh to get updated data
        for reconciliation in reconciliations:
            self.db.refresh(reconciliation)
        self.db.refresh(bank_transaction)
        
        logger.info(
            f"Created manual reconciliation: bank_transaction_id={bank_transaction_id}, "
            f"journal_entry_ids={journal_entry_ids}, reconciled_by={reconciled_by}, "
            f"reconciliation_count={len(reconciliations)}"
        )
        
        return reconciliations

    def create_many_to_one_match(
        self,
        bank_transaction_id: UUID,
        journal_entry_ids: List[UUID],
        reconciled_by: str,
        organization_id: UUID,
        notes: Optional[str] = None
    ) -> List[BankReconciliation]:
        """
        Create many-to-one reconciliation matching multiple journal entries to one bank transaction.

        This method:
        1. Calculates the sum of all selected journal entries
        2. Validates that the sum equals the bank transaction amount (with 0.01 tolerance)
        3. Creates multiple reconciliation records with type "many_to_one" and status "confirmed"
        4. Updates the bank transaction status to "reconciled"
        5. Sets reconciled_at timestamp and reconciled_by user

        Args:
            bank_transaction_id: UUID of the bank transaction to reconcile
            journal_entry_ids: List of journal entry UUIDs to match (must be multiple entries)
            reconciled_by: User identifier performing the reconciliation
            organization_id: Organization UUID for multi-tenant isolation
            notes: Optional notes or remarks about the reconciliation

        Returns:
            List of created BankReconciliation instances

        Raises:
            ValueError: If bank transaction is already reconciled or not found
            ValueError: If any journal entry is not found
            ValueError: If sum of journal entries does not equal bank transaction amount
            ValueError: If only one journal entry is provided (use create_manual_match instead)

        Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 10.9
        """
        # Requirement 10.1: Allow users to select multiple journal entries
        if len(journal_entry_ids) < 2:
            raise ValueError(
                "Many-to-one reconciliation requires at least 2 journal entries. "
                "For single entry reconciliation, use create_manual_match instead."
            )

        # Fetch the bank transaction
        bank_transaction = (
            self.db.query(BankTransaction)
            .filter(
                and_(
                    BankTransaction.id == bank_transaction_id,
                    BankTransaction.organization_id == organization_id
                )
            )
            .first()
        )

        if not bank_transaction:
            raise ValueError(f"Bank transaction {bank_transaction_id} not found")

        # Prevent double reconciliation
        if bank_transaction.is_reconciled:
            raise ValueError(
                f"Bank transaction {bank_transaction_id} is already reconciled. "
                f"Cannot reconcile the same transaction twice."
            )

        # Check if there are any active reconciliations for this transaction
        existing_reconciliation = (
            self.db.query(BankReconciliation)
            .filter(
                and_(
                    BankReconciliation.bank_transaction_id == bank_transaction_id,
                    BankReconciliation.is_active == True,
                    BankReconciliation.reconciliation_status == "confirmed"
                )
            )
            .first()
        )

        if existing_reconciliation:
            raise ValueError(
                f"Bank transaction {bank_transaction_id} already has an active reconciliation. "
                f"Cannot reconcile the same transaction twice."
            )

        # Fetch all journal entries
        journal_entries = (
            self.db.query(JournalEntry)
            .filter(
                and_(
                    JournalEntry.id.in_(journal_entry_ids),
                    JournalEntry.organization_id == organization_id
                )
            )
            .all()
        )

        if len(journal_entries) != len(journal_entry_ids):
            found_ids = {je.id for je in journal_entries}
            missing_ids = set(journal_entry_ids) - found_ids
            raise ValueError(f"Journal entries not found: {missing_ids}")

        # Requirement 10.2: Calculate sum of selected journal entries
        # Sum the total_debit or total_credit from each journal entry
        # For reconciliation purposes, we use the absolute value of the amounts
        journal_entry_sum = sum(
            (je.total_debit if je.total_debit > 0 else je.total_credit)
            for je in journal_entries
        )

        logger.info(
            f"Many-to-one reconciliation: bank_transaction_amount={bank_transaction.transaction_amount}, "
            f"journal_entries_sum={journal_entry_sum}, "
            f"journal_entry_count={len(journal_entries)}"
        )

        # Requirement 10.3, 10.4: Validate sum equals bank transaction amount (with 0.01 tolerance)
        tolerance = Decimal("0.01")
        difference = abs(Decimal(str(bank_transaction.transaction_amount)) - Decimal(str(journal_entry_sum)))

        if difference > tolerance:
            raise ValueError(
                f"Sum of journal entries ({journal_entry_sum}) does not equal "
                f"bank transaction amount ({bank_transaction.transaction_amount}). "
                f"Difference: {difference}. Reconciliation prevented."
            )

        # Create reconciliation records
        reconciliations = []
        current_time = datetime.now(UTC)

        # Requirement 10.5: Create multiple reconciliation records linking each journal entry to the bank transaction
        for journal_entry in journal_entries:
            # Requirement 10.6: Set reconciliation_type to "many_to_one"
            # Requirement 10.7: Set reconciliation_status to "confirmed"
            reconciliation = BankReconciliation(
                organization_id=organization_id,
                bank_transaction_id=bank_transaction_id,
                journal_entry_id=journal_entry.id,
                reconciliation_type="many_to_one",
                reconciliation_status="confirmed",
                match_confidence=Decimal("1.0"),  # Many-to-one matches have full confidence when manually confirmed
                reconciled_by=reconciled_by,
                reconciled_at=current_time,
                notes=notes,
                is_active=True
            )

            self.db.add(reconciliation)
            reconciliations.append(reconciliation)

        # Requirement 10.8: Update bank transaction status to "reconciled"
        bank_transaction.transaction_status = "reconciled"
        bank_transaction.reconciled_at = current_time

        # Commit the transaction
        self.db.commit()

        # Refresh to get updated data
        for reconciliation in reconciliations:
            self.db.refresh(reconciliation)
        self.db.refresh(bank_transaction)

        logger.info(
            f"Created many-to-one reconciliation: bank_transaction_id={bank_transaction_id}, "
            f"journal_entry_ids={journal_entry_ids}, reconciled_by={reconciled_by}, "
            f"reconciliation_count={len(reconciliations)}"
        )

        return reconciliations

    def confirm_suggested_match(
        self,
        reconciliation_id: UUID,
        confirmed_by: str,
        organization_id: UUID
    ) -> BankReconciliation:
        """
        Confirm a suggested fuzzy match reconciliation.

        This method:
        1. Validates that the reconciliation exists and has status "suggested"
        2. Updates the reconciliation status to "confirmed"
        3. Updates the bank transaction status to "reconciled"
        4. Sets reconciled_at timestamp and reconciled_by user

        Args:
            reconciliation_id: UUID of the reconciliation to confirm
            confirmed_by: User identifier confirming the match
            organization_id: Organization UUID for multi-tenant isolation

        Returns:
            Updated BankReconciliation instance

        Raises:
            ValueError: If reconciliation not found or not in suggested status

        Requirements: 9.10
        """
        # Fetch the reconciliation
        reconciliation = (
            self.db.query(BankReconciliation)
            .filter(
                and_(
                    BankReconciliation.id == reconciliation_id,
                    BankReconciliation.organization_id == organization_id
                )
            )
            .first()
        )

        if not reconciliation:
            raise ValueError(f"Reconciliation {reconciliation_id} not found")

        # Validate that the reconciliation is in suggested status
        if reconciliation.reconciliation_status != "suggested":
            raise ValueError(
                f"Reconciliation {reconciliation_id} has status '{reconciliation.reconciliation_status}'. "
                f"Only suggested matches can be confirmed."
            )

        # Validate that the reconciliation is active
        if not reconciliation.is_active:
            raise ValueError(
                f"Reconciliation {reconciliation_id} is not active. "
                f"Cannot confirm an inactive reconciliation."
            )

        # Fetch the bank transaction
        bank_transaction = (
            self.db.query(BankTransaction)
            .filter(
                and_(
                    BankTransaction.id == reconciliation.bank_transaction_id,
                    BankTransaction.organization_id == organization_id
                )
            )
            .first()
        )

        if not bank_transaction:
            raise ValueError(
                f"Bank transaction {reconciliation.bank_transaction_id} not found"
            )

        # Update reconciliation status to confirmed
        current_time = datetime.now(UTC)
        reconciliation.reconciliation_status = "confirmed"
        reconciliation.reconciled_by = confirmed_by
        reconciliation.reconciled_at = current_time

        # Update bank transaction status to reconciled
        bank_transaction.transaction_status = "reconciled"
        bank_transaction.reconciled_at = current_time

        # Commit the transaction
        self.db.commit()

        # Refresh to get updated data
        self.db.refresh(reconciliation)
        self.db.refresh(bank_transaction)

        logger.info(
            f"Confirmed suggested match: reconciliation_id={reconciliation_id}, "
            f"bank_transaction_id={bank_transaction.id}, "
            f"journal_entry_id={reconciliation.journal_entry_id}, "
            f"confirmed_by={confirmed_by}"
        )

        return reconciliation

    def reject_suggested_match(
        self,
        reconciliation_id: UUID,
        rejected_by: str,
        organization_id: UUID,
        reason: Optional[str] = None
    ) -> BankReconciliation:
        """
        Reject a suggested fuzzy match reconciliation.

        This method:
        1. Validates that the reconciliation exists and has status "suggested"
        2. Updates the reconciliation status to "rejected"
        3. Does NOT update the bank transaction status (remains "cleared")
        4. Records who rejected the match and when
        5. Optionally stores a reason for rejection

        Args:
            reconciliation_id: UUID of the reconciliation to reject
            rejected_by: User identifier rejecting the match
            organization_id: Organization UUID for multi-tenant isolation
            reason: Optional reason for rejecting the match

        Returns:
            Updated BankReconciliation instance

        Raises:
            ValueError: If reconciliation not found or not in suggested status

        Requirements: 9.10
        """
        # Fetch the reconciliation
        reconciliation = (
            self.db.query(BankReconciliation)
            .filter(
                and_(
                    BankReconciliation.id == reconciliation_id,
                    BankReconciliation.organization_id == organization_id
                )
            )
            .first()
        )

        if not reconciliation:
            raise ValueError(f"Reconciliation {reconciliation_id} not found")

        # Validate that the reconciliation is in suggested status
        if reconciliation.reconciliation_status != "suggested":
            raise ValueError(
                f"Reconciliation {reconciliation_id} has status '{reconciliation.reconciliation_status}'. "
                f"Only suggested matches can be rejected."
            )

        # Validate that the reconciliation is active
        if not reconciliation.is_active:
            raise ValueError(
                f"Reconciliation {reconciliation_id} is not active. "
                f"Cannot reject an inactive reconciliation."
            )

        # Update reconciliation status to rejected
        current_time = datetime.now(UTC)
        reconciliation.reconciliation_status = "rejected"
        reconciliation.reconciled_by = rejected_by
        reconciliation.reconciled_at = current_time

        # Store rejection reason if provided
        if reason:
            if reconciliation.notes:
                reconciliation.notes = f"{reconciliation.notes}\n\nRejection reason: {reason}"
            else:
                reconciliation.notes = f"Rejection reason: {reason}"

        # Note: Bank transaction status remains unchanged (stays "cleared")
        # This allows the transaction to be matched with a different journal entry

        # Commit the transaction
        self.db.commit()

        # Refresh to get updated data
        self.db.refresh(reconciliation)

        logger.info(
            f"Rejected suggested match: reconciliation_id={reconciliation_id}, "
            f"bank_transaction_id={reconciliation.bank_transaction_id}, "
            f"journal_entry_id={reconciliation.journal_entry_id}, "
            f"rejected_by={rejected_by}, "
            f"reason={reason}"
        )

        return reconciliation


    def undo_reconciliation(
        self,
        reconciliation_id: UUID,
        undone_by: str,
        organization_id: UUID,
        reason: str,
        has_elevated_permissions: bool = False
    ) -> BankReconciliation:
        """
        Undo a confirmed reconciliation match.
        
        This method:
        1. Updates the reconciliation status to "rejected"
        2. Updates the bank transaction status back to "cleared"
        3. Sets reconciled_at and reconciled_by to null
        4. Preserves the reconciliation record (does not delete)
        5. Logs the undo action with user and timestamp
        6. Checks 90-day restriction for non-elevated users
        
        Args:
            reconciliation_id: UUID of the reconciliation to undo
            undone_by: User identifier performing the undo
            organization_id: Organization UUID for multi-tenant isolation
            reason: Reason for undoing the reconciliation
            has_elevated_permissions: Whether the user has elevated permissions (default: False)
            
        Returns:
            Updated BankReconciliation instance
            
        Raises:
            ValueError: If reconciliation is not found or cannot be undone
            ValueError: If reconciliation is older than 90 days and user lacks elevated permissions
            
        Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8, 17.9, 17.10
        """
        # Fetch the reconciliation
        reconciliation = (
            self.db.query(BankReconciliation)
            .filter(
                and_(
                    BankReconciliation.id == reconciliation_id,
                    BankReconciliation.organization_id == organization_id
                )
            )
            .first()
        )
        
        if not reconciliation:
            raise ValueError(f"Reconciliation {reconciliation_id} not found")
        
        # Requirement 17.1: Allow users to undo a confirmed reconciliation
        if not reconciliation.can_be_undone:
            raise ValueError(
                f"Reconciliation {reconciliation_id} cannot be undone. "
                f"Status: {reconciliation.reconciliation_status}, Active: {reconciliation.is_active}"
            )
        
        # Requirement 17.9: Check 90-day restriction for non-elevated users
        if not has_elevated_permissions and reconciliation.reconciled_at:
            from datetime import timedelta
            days_since_reconciliation = (datetime.now(UTC) - reconciliation.reconciled_at).days
            if days_since_reconciliation > 90:
                raise ValueError(
                    f"Cannot undo reconciliation older than 90 days without elevated permissions. "
                    f"Reconciliation age: {days_since_reconciliation} days"
                )
        
        # Fetch the bank transaction
        bank_transaction = (
            self.db.query(BankTransaction)
            .filter(
                and_(
                    BankTransaction.id == reconciliation.bank_transaction_id,
                    BankTransaction.organization_id == organization_id
                )
            )
            .first()
        )
        
        if not bank_transaction:
            raise ValueError(
                f"Bank transaction {reconciliation.bank_transaction_id} not found"
            )
        
        # Check if there are other active reconciliations for this bank transaction
        # (in case of many-to-one reconciliation)
        other_active_reconciliations = (
            self.db.query(BankReconciliation)
            .filter(
                and_(
                    BankReconciliation.bank_transaction_id == bank_transaction.id,
                    BankReconciliation.id != reconciliation_id,
                    BankReconciliation.is_active == True,
                    BankReconciliation.reconciliation_status == "confirmed"
                )
            )
            .all()
        )
        
        # Requirement 17.2: Update reconciliation status to "rejected"
        reconciliation.reconciliation_status = "rejected"
        
        # Requirement 17.6: Do NOT delete the reconciliation record (preserve it)
        # We set is_active to False to mark it as undone, but keep the record
        reconciliation.is_active = False
        
        # Requirement 17.7: Log the undo action with user identifier and timestamp
        reconciliation.undone_by = undone_by
        reconciliation.undone_at = datetime.now(UTC)
        
        # Requirement 17.8: Store the reason for undoing
        reconciliation.undo_reason = reason
        
        # Only update bank transaction if there are no other active reconciliations
        if not other_active_reconciliations:
            # Requirement 17.3: Update bank transaction status back to "cleared"
            bank_transaction.transaction_status = "cleared"
            
            # Requirement 17.4: Set reconciled_at to null
            bank_transaction.reconciled_at = None
            
            # Note: Requirement 17.5 mentions setting reconciled_by to null,
            # but the BankTransaction model doesn't have a reconciled_by field.
            # The reconciled_by is stored in the BankReconciliation model.
        
        # Commit the transaction
        self.db.commit()
        
        # Refresh to get updated data
        self.db.refresh(reconciliation)
        self.db.refresh(bank_transaction)
        
        logger.info(
            f"Undone reconciliation: reconciliation_id={reconciliation_id}, "
            f"bank_transaction_id={bank_transaction.id}, "
            f"undone_by={undone_by}, reason={reason}, "
            f"other_active_reconciliations={len(other_active_reconciliations)}"
        )
        
        return reconciliation

    def reconcile_with_currency_conversion(
        self,
        bank_transaction_id: UUID,
        journal_entry_id: UUID,
        exchange_rate: Decimal,
        reconciled_by: str,
        organization_id: UUID,
        notes: Optional[str] = None
    ) -> BankReconciliation:
        """
        Reconcile a bank transaction with a journal entry using currency conversion.

        This method handles reconciliation when the bank transaction currency differs
        from the journal entry currency. It:
        1. Requires an exchange_rate parameter when currencies differ
        2. Calculates converted_amount as transaction_amount × exchange_rate
        3. Validates converted amount matches journal entry amount within 0.01 tolerance
        4. Stores exchange_rate in the reconciliation record

        Args:
            bank_transaction_id: UUID of the bank transaction to reconcile
            journal_entry_id: UUID of the journal entry to match
            exchange_rate: Exchange rate to convert transaction amount to journal entry currency
            reconciled_by: User identifier performing the reconciliation
            organization_id: Organization UUID for multi-tenant isolation
            notes: Optional notes or remarks about the reconciliation

        Returns:
            Created BankReconciliation instance

        Raises:
            ValueError: If bank transaction or journal entry is not found
            ValueError: If bank transaction is already reconciled
            ValueError: If exchange_rate is not provided or invalid
            ValueError: If converted amount does not match journal entry amount within tolerance

        Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7, 19.8, 19.9, 19.10
        """
        # Fetch the bank transaction
        bank_transaction = (
            self.db.query(BankTransaction)
            .filter(
                and_(
                    BankTransaction.id == bank_transaction_id,
                    BankTransaction.organization_id == organization_id
                )
            )
            .first()
        )

        if not bank_transaction:
            raise ValueError(f"Bank transaction {bank_transaction_id} not found")

        # Prevent double reconciliation
        if bank_transaction.is_reconciled:
            raise ValueError(
                f"Bank transaction {bank_transaction_id} is already reconciled. "
                f"Cannot reconcile the same transaction twice."
            )

        # Check if there are any active reconciliations for this transaction
        existing_reconciliation = (
            self.db.query(BankReconciliation)
            .filter(
                and_(
                    BankReconciliation.bank_transaction_id == bank_transaction_id,
                    BankReconciliation.is_active == True,
                    BankReconciliation.reconciliation_status == "confirmed"
                )
            )
            .first()
        )

        if existing_reconciliation:
            raise ValueError(
                f"Bank transaction {bank_transaction_id} already has an active reconciliation. "
                f"Cannot reconcile the same transaction twice."
            )

        # Fetch the journal entry
        journal_entry = (
            self.db.query(JournalEntry)
            .filter(
                and_(
                    JournalEntry.id == journal_entry_id,
                    JournalEntry.organization_id == organization_id
                )
            )
            .first()
        )

        if not journal_entry:
            raise ValueError(f"Journal entry {journal_entry_id} not found")

        # Requirement 19.3: Require exchange_rate parameter when currencies differ
        if exchange_rate is None:
            raise ValueError(
                "Exchange rate is required for multi-currency reconciliation"
            )

        # Validate exchange_rate is positive
        if exchange_rate <= 0:
            raise ValueError(
                f"Exchange rate must be positive, got {exchange_rate}"
            )

        # Requirement 19.4: Calculate converted_amount as transaction_amount × exchange_rate
        transaction_amount = Decimal(str(bank_transaction.transaction_amount))
        converted_amount = transaction_amount * Decimal(str(exchange_rate))

        # Get the journal entry amount (use total_debit or total_credit, whichever is non-zero)
        journal_entry_amount = (
            Decimal(str(journal_entry.total_debit))
            if journal_entry.total_debit > 0
            else Decimal(str(journal_entry.total_credit))
        )

        # Requirement 19.5: Validate converted amount matches journal entry amount within 0.01 tolerance
        tolerance = Decimal("0.01")
        difference = abs(converted_amount - journal_entry_amount)

        if difference > tolerance:
            raise ValueError(
                f"Converted amount ({converted_amount}) does not match "
                f"journal entry amount ({journal_entry_amount}) within tolerance ({tolerance}). "
                f"Difference: {difference}"
            )

        # Create reconciliation record
        current_time = datetime.now(UTC)

        # Requirement 19.6: Store exchange_rate in reconciliation record
        reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction_id,
            journal_entry_id=journal_entry_id,
            reconciliation_type="manual",  # Multi-currency reconciliation is always manual
            reconciliation_status="confirmed",
            match_confidence=Decimal("1.0"),
            exchange_rate=Decimal(str(exchange_rate)),  # Requirement 19.6
            converted_amount=converted_amount,  # Store the converted amount
            reconciled_by=reconciled_by,
            reconciled_at=current_time,
            notes=notes,
            is_active=True
        )

        self.db.add(reconciliation)

        # Update bank transaction status to "reconciled"
        bank_transaction.transaction_status = "reconciled"
        bank_transaction.reconciled_at = current_time

        # Commit the transaction
        self.db.commit()

        # Refresh to get updated data
        self.db.refresh(reconciliation)
        self.db.refresh(bank_transaction)

        logger.info(
            f"Created multi-currency reconciliation: bank_transaction_id={bank_transaction_id}, "
            f"journal_entry_id={journal_entry_id}, exchange_rate={exchange_rate}, "
            f"transaction_amount={transaction_amount}, converted_amount={converted_amount}, "
            f"journal_entry_amount={journal_entry_amount}, reconciled_by={reconciled_by}"
        )

        return reconciliation

    def calculate_bank_balance(
        self,
        bank_account_id: UUID,
        organization_id: UUID,
        as_of_date: Optional[date] = None
    ) -> Decimal:
        """
        Calculate bank balance from bank transactions.
        
        Calculates the balance by summing all cleared and reconciled bank transactions
        up to the specified date. Credits increase the balance, debits decrease it.
        
        Args:
            bank_account_id: UUID of the bank account
            organization_id: Organization UUID for multi-tenant isolation
            as_of_date: Optional date to calculate balance as of (defaults to today)
            
        Returns:
            Decimal representing the bank balance
            
        Requirements: 14.8, 19.9
        """
        if as_of_date is None:
            as_of_date = date.today()
        
        # Get all cleared and reconciled transactions up to the specified date
        transactions = (
            self.db.query(BankTransaction)
            .filter(
                and_(
                    BankTransaction.organization_id == organization_id,
                    BankTransaction.bank_account_id == bank_account_id,
                    BankTransaction.statement_date <= as_of_date,
                    BankTransaction.transaction_status.in_(['cleared', 'reconciled'])
                )
            )
            .all()
        )
        
        # Calculate balance: credits add, debits subtract
        balance = Decimal('0.00')
        for transaction in transactions:
            amount = Decimal(str(transaction.transaction_amount))
            if transaction.transaction_type == 'credit':
                balance += amount
            else:  # debit
                balance -= amount
        
        logger.info(
            f"Calculated bank balance for bank_account_id={bank_account_id}, "
            f"as_of_date={as_of_date}, balance={balance}, "
            f"transaction_count={len(transactions)}"
        )
        
        return balance

    def calculate_gl_balance(
        self,
        gl_account_id: UUID,
        organization_id: UUID,
        as_of_date: Optional[date] = None
    ) -> Decimal:
        """
        Calculate GL balance from journal entries.
        
        Calculates the balance by summing all posted journal entry lines for the
        specified GL account up to the specified date. Debits increase the balance
        for asset accounts, credits increase it for liability accounts.
        
        Args:
            gl_account_id: UUID of the GL account (bank account's linked account)
            organization_id: Organization UUID for multi-tenant isolation
            as_of_date: Optional date to calculate balance as of (defaults to today)
            
        Returns:
            Decimal representing the GL balance
            
        Requirements: 14.8, 19.8
        """
        from app.models.journal_entry import JournalEntryLine
        
        if as_of_date is None:
            as_of_date = date.today()
        
        # Get all posted journal entry lines for this account up to the specified date
        lines = (
            self.db.query(JournalEntryLine)
            .join(JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id)
            .filter(
                and_(
                    JournalEntry.organization_id == organization_id,
                    JournalEntryLine.account_id == gl_account_id,
                    JournalEntry.posting_date <= as_of_date,
                    JournalEntry.status == 'posted'
                )
            )
            .all()
        )
        
        # Calculate balance: sum of debits minus sum of credits
        # For bank accounts (asset accounts), debits increase balance, credits decrease
        total_debits = sum(Decimal(str(line.debit)) for line in lines)
        total_credits = sum(Decimal(str(line.credit)) for line in lines)
        balance = total_debits - total_credits
        
        logger.info(
            f"Calculated GL balance for gl_account_id={gl_account_id}, "
            f"as_of_date={as_of_date}, balance={balance}, "
            f"total_debits={total_debits}, total_credits={total_credits}, "
            f"line_count={len(lines)}"
        )
        
        return balance

    def calculate_unreconciled_amount(
        self,
        bank_account_id: UUID,
        gl_account_id: UUID,
        organization_id: UUID,
        as_of_date: Optional[date] = None
    ) -> Decimal:
        """
        Calculate unreconciled amount (difference between bank and GL balances).
        
        This represents the difference between what the bank shows and what the
        general ledger shows. A positive value means the bank balance is higher
        than the GL balance, a negative value means the GL balance is higher.
        
        Args:
            bank_account_id: UUID of the bank account
            gl_account_id: UUID of the GL account (bank account's linked account)
            organization_id: Organization UUID for multi-tenant isolation
            as_of_date: Optional date to calculate balances as of (defaults to today)
            
        Returns:
            Decimal representing the unreconciled amount (bank_balance - gl_balance)
            
        Requirements: 14.9
        """
        bank_balance = self.calculate_bank_balance(
            bank_account_id=bank_account_id,
            organization_id=organization_id,
            as_of_date=as_of_date
        )
        
        gl_balance = self.calculate_gl_balance(
            gl_account_id=gl_account_id,
            organization_id=organization_id,
            as_of_date=as_of_date
        )
        
        unreconciled_amount = self.calculate_reconciliation_difference(
            bank_balance=bank_balance,
            gl_balance=gl_balance
        )
        
        logger.info(
            f"Calculated unreconciled amount: bank_account_id={bank_account_id}, "
            f"gl_account_id={gl_account_id}, as_of_date={as_of_date}, "
            f"bank_balance={bank_balance}, gl_balance={gl_balance}, "
            f"unreconciled_amount={unreconciled_amount}"
        )
        
        return unreconciled_amount

    def undo_reconciliation(
        self,
        reconciliation_id: UUID,
        undone_by: str,
        organization_id: UUID,
        reason: str,
        has_elevated_permissions: bool = False
    ) -> BankReconciliation:
        """
        Undo a confirmed reconciliation match.

        This method:
        1. Updates the reconciliation status to "rejected"
        2. Updates the bank transaction status back to "cleared"
        3. Sets reconciled_at and reconciled_by to null
        4. Preserves the reconciliation record (does not delete)
        5. Logs the undo action with user and timestamp
        6. Checks 90-day restriction for non-elevated users

        Args:
            reconciliation_id: UUID of the reconciliation to undo
            undone_by: User identifier performing the undo
            organization_id: Organization UUID for multi-tenant isolation
            reason: Reason for undoing the reconciliation
            has_elevated_permissions: Whether the user has elevated permissions (default: False)

        Returns:
            Updated BankReconciliation instance

        Raises:
            ValueError: If reconciliation is not found or cannot be undone
            ValueError: If reconciliation is older than 90 days and user lacks elevated permissions

        Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8, 17.9, 17.10
        """
        # Fetch the reconciliation
        reconciliation = (
            self.db.query(BankReconciliation)
            .filter(
                and_(
                    BankReconciliation.id == reconciliation_id,
                    BankReconciliation.organization_id == organization_id
                )
            )
            .first()
        )

        if not reconciliation:
            raise ValueError(f"Reconciliation {reconciliation_id} not found")

        # Requirement 17.1: Allow users to undo a confirmed reconciliation
        if not reconciliation.can_be_undone:
            raise ValueError(
                f"Reconciliation {reconciliation_id} cannot be undone. "
                f"Status: {reconciliation.reconciliation_status}, Active: {reconciliation.is_active}"
            )

        # Requirement 17.9: Check 90-day restriction for non-elevated users
        if not has_elevated_permissions and reconciliation.reconciled_at:
            from datetime import timedelta
            # Ensure both datetimes are timezone-aware for comparison
            reconciled_at_aware = reconciliation.reconciled_at
            if reconciled_at_aware.tzinfo is None:
                # If reconciled_at is naive, assume it's UTC
                reconciled_at_aware = reconciled_at_aware.replace(tzinfo=UTC)
            
            days_since_reconciliation = (datetime.now(UTC) - reconciled_at_aware).days
            if days_since_reconciliation > 90:
                raise ValueError(
                    f"Cannot undo reconciliation older than 90 days without elevated permissions. "
                    f"Reconciliation age: {days_since_reconciliation} days"
                )

        # Fetch the bank transaction
        bank_transaction = (
            self.db.query(BankTransaction)
            .filter(
                and_(
                    BankTransaction.id == reconciliation.bank_transaction_id,
                    BankTransaction.organization_id == organization_id
                )
            )
            .first()
        )

        if not bank_transaction:
            raise ValueError(
                f"Bank transaction {reconciliation.bank_transaction_id} not found"
            )

        # Check if there are other active reconciliations for this bank transaction
        # (in case of many-to-one reconciliation)
        other_active_reconciliations = (
            self.db.query(BankReconciliation)
            .filter(
                and_(
                    BankReconciliation.bank_transaction_id == bank_transaction.id,
                    BankReconciliation.id != reconciliation_id,
                    BankReconciliation.is_active == True,
                    BankReconciliation.reconciliation_status == "confirmed"
                )
            )
            .all()
        )

        # Requirement 17.2: Update reconciliation status to "rejected"
        reconciliation.reconciliation_status = "rejected"

        # Requirement 17.6: Do NOT delete the reconciliation record (preserve it)
        # We set is_active to False to mark it as undone, but keep the record
        reconciliation.is_active = False

        # Requirement 17.7: Log the undo action with user identifier and timestamp
        reconciliation.undone_by = undone_by
        reconciliation.undone_at = datetime.now(UTC)

        # Requirement 17.8: Store the reason for undoing
        reconciliation.undo_reason = reason

        # Only update bank transaction if there are no other active reconciliations
        if not other_active_reconciliations:
            # Requirement 17.3: Update bank transaction status back to "cleared"
            bank_transaction.transaction_status = "cleared"

            # Requirement 17.4: Set reconciled_at to null
            bank_transaction.reconciled_at = None

            # Note: Requirement 17.5 mentions setting reconciled_by to null,
            # but the BankTransaction model doesn't have a reconciled_by field.
            # The reconciled_by is stored in the BankReconciliation model.

        # Commit the transaction
        self.db.commit()

        # Refresh to get updated data
        self.db.refresh(reconciliation)
        self.db.refresh(bank_transaction)

        logger.info(
            f"Undone reconciliation: reconciliation_id={reconciliation_id}, "
            f"bank_transaction_id={bank_transaction.id}, "
            f"undone_by={undone_by}, reason={reason}, "
            f"other_active_reconciliations={len(other_active_reconciliations)}"
        )

        return reconciliation


    def calculate_bank_balance(
        self,
        bank_account_id: UUID,
        organization_id: UUID,
        as_of_date: Optional[date] = None
    ) -> Decimal:
        """
        Calculate bank balance from bank transactions.

        Calculates the balance by summing all cleared and reconciled bank transactions
        up to the specified date. Credits increase the balance, debits decrease it.

        Args:
            bank_account_id: UUID of the bank account
            organization_id: Organization UUID for multi-tenant isolation
            as_of_date: Optional date to calculate balance as of (defaults to today)

        Returns:
            Decimal representing the bank balance

        Requirements: 14.8, 19.9
        """
        if as_of_date is None:
            as_of_date = date.today()

        # Get all cleared and reconciled transactions up to the specified date
        transactions = (
            self.db.query(BankTransaction)
            .filter(
                and_(
                    BankTransaction.organization_id == organization_id,
                    BankTransaction.bank_account_id == bank_account_id,
                    BankTransaction.statement_date <= as_of_date,
                    BankTransaction.transaction_status.in_(['cleared', 'reconciled'])
                )
            )
            .all()
        )

        # Calculate balance: credits add, debits subtract
        balance = Decimal('0.00')
        for transaction in transactions:
            amount = Decimal(str(transaction.transaction_amount))
            if transaction.transaction_type == 'credit':
                balance += amount
            else:  # debit
                balance -= amount

        logger.info(
            f"Calculated bank balance for bank_account_id={bank_account_id}, "
            f"as_of_date={as_of_date}, balance={balance}, "
            f"transaction_count={len(transactions)}"
        )

        return balance

    def calculate_gl_balance(
        self,
        gl_account_id: UUID,
        organization_id: UUID,
        as_of_date: Optional[date] = None
    ) -> Decimal:
        """
        Calculate GL balance from journal entries.

        Calculates the balance by summing all posted journal entry lines for the
        specified GL account up to the specified date. Debits increase the balance
        for asset accounts, credits increase it for liability accounts.

        Args:
            gl_account_id: UUID of the GL account (bank account's linked account)
            organization_id: Organization UUID for multi-tenant isolation
            as_of_date: Optional date to calculate balance as of (defaults to today)

        Returns:
            Decimal representing the GL balance

        Requirements: 14.8, 19.8
        """
        from app.models.journal_entry import JournalEntryLine

        if as_of_date is None:
            as_of_date = date.today()

        # Get all posted journal entry lines for this account up to the specified date
        lines = (
            self.db.query(JournalEntryLine)
            .join(JournalEntry, JournalEntryLine.journal_entry_id == JournalEntry.id)
            .filter(
                and_(
                    JournalEntry.organization_id == organization_id,
                    JournalEntryLine.account_id == gl_account_id,
                    JournalEntry.posting_date <= as_of_date,
                    JournalEntry.status == 'posted'
                )
            )
            .all()
        )

        # Calculate balance: sum of debits minus sum of credits
        # For bank accounts (asset accounts), debits increase balance, credits decrease
        total_debits = sum(Decimal(str(line.debit)) for line in lines)
        total_credits = sum(Decimal(str(line.credit)) for line in lines)
        balance = total_debits - total_credits

        logger.info(
            f"Calculated GL balance for gl_account_id={gl_account_id}, "
            f"as_of_date={as_of_date}, balance={balance}, "
            f"total_debits={total_debits}, total_credits={total_credits}, "
            f"line_count={len(lines)}"
        )

        return balance

    def calculate_unreconciled_amount(
        self,
        bank_account_id: UUID,
        gl_account_id: UUID,
        organization_id: UUID,
        as_of_date: Optional[date] = None
    ) -> Decimal:
        """
        Calculate unreconciled amount (difference between bank and GL balances).

        This represents the difference between what the bank shows and what the
        general ledger shows. A positive value means the bank balance is higher
        than the GL balance, a negative value means the GL balance is higher.

        Args:
            bank_account_id: UUID of the bank account
            gl_account_id: UUID of the GL account (bank account's linked account)
            organization_id: Organization UUID for multi-tenant isolation
            as_of_date: Optional date to calculate balances as of (defaults to today)

        Returns:
            Decimal representing the unreconciled amount (bank_balance - gl_balance)

        Requirements: 14.9
        """
        bank_balance = self.calculate_bank_balance(
            bank_account_id=bank_account_id,
            organization_id=organization_id,
            as_of_date=as_of_date
        )

        gl_balance = self.calculate_gl_balance(
            gl_account_id=gl_account_id,
            organization_id=organization_id,
            as_of_date=as_of_date
        )

        unreconciled_amount = self.calculate_reconciliation_difference(
            bank_balance=bank_balance,
            gl_balance=gl_balance
        )

        logger.info(
            f"Calculated unreconciled amount: bank_account_id={bank_account_id}, "
            f"gl_account_id={gl_account_id}, as_of_date={as_of_date}, "
            f"bank_balance={bank_balance}, gl_balance={gl_balance}, "
            f"unreconciled_amount={unreconciled_amount}"
        )

        return unreconciled_amount




