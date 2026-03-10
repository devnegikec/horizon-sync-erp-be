"""
Auto-Reconciliation Service

Automatically matches bank transactions with journal entries using various algorithms.
Implements exact match, fuzzy match, and many-to-one detection strategies.

Requirements: 8.1-8.10, 9.1-9.10, 10.10
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


class AutoReconciliationService:
    """
    Service for automatically matching bank transactions with journal entries.
    
    Provides algorithms for exact matching, fuzzy matching, and many-to-one
    detection to automate the reconciliation process.
    """

    def __init__(self, db: Session):
        """
        Initialize the auto-reconciliation service.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db

    def run_auto_reconciliation(
        self,
        bank_account_id: UUID,
        date_from: date,
        date_to: date,
        organization_id: UUID
    ) -> dict:
        """
        Run auto-reconciliation for unreconciled bank transactions.
        
        Filters bank transactions with status "cleared" and reconciled_at is null,
        then attempts to match them with journal entries using various algorithms.
        
        Args:
            bank_account_id: UUID of the bank account to reconcile
            date_from: Start date for transaction filtering
            date_to: End date for transaction filtering
            organization_id: Organization UUID for multi-tenant isolation
            
        Returns:
            Dictionary containing reconciliation results with counts of:
            - exact_matches: Number of exact matches found
            - fuzzy_matches: Number of fuzzy matches suggested
            - many_to_one_matches: Number of many-to-one matches detected
            - unmatched: Number of transactions that couldn't be matched
            
        Requirements: 8.1
        """
        logger.info(
            f"Starting auto-reconciliation for bank_account_id={bank_account_id}, "
            f"date_range={date_from} to {date_to}"
        )
        
        # Filter bank transactions with status "cleared" and reconciled_at is null
        unreconciled_transactions = self._get_unreconciled_transactions(
            bank_account_id=bank_account_id,
            date_from=date_from,
            date_to=date_to,
            organization_id=organization_id
        )
        
        logger.info(
            f"Found {len(unreconciled_transactions)} unreconciled transactions "
            f"for bank_account_id={bank_account_id}"
        )
        
        # Initialize result counters
        result = {
            "exact_matches": 0,
            "fuzzy_matches": 0,
            "many_to_one_matches": 0,
            "unmatched": 0,
            "total_processed": len(unreconciled_transactions)
        }
        
        # Get unreconciled journal entries for matching
        unreconciled_journal_entries = self._get_unreconciled_journal_entries(
            organization_id=organization_id,
            date_from=date_from,
            date_to=date_to
        )
        
        logger.info(
            f"Found {len(unreconciled_journal_entries)} unreconciled journal entries "
            f"for matching"
        )
        
        # Process each unreconciled transaction
        for transaction in unreconciled_transactions:
            # Try exact match first
            exact_match = self.find_exact_matches(
                bank_transaction=transaction,
                journal_entries=unreconciled_journal_entries
            )
            
            if exact_match:
                # Create reconciliation record
                self._create_exact_match_reconciliation(
                    bank_transaction=transaction,
                    journal_entry=exact_match,
                    organization_id=organization_id
                )
                result["exact_matches"] += 1
                # Remove matched journal entry from available pool
                unreconciled_journal_entries.remove(exact_match)
                continue
            
            # Try fuzzy match if no exact match found
            fuzzy_matches = self.find_fuzzy_matches(
                bank_transaction=transaction,
                journal_entries=unreconciled_journal_entries
            )
            
            if fuzzy_matches:
                # Create suggested reconciliation for the best fuzzy match
                best_match, confidence = fuzzy_matches[0]
                self._create_fuzzy_match_reconciliation(
                    bank_transaction=transaction,
                    journal_entry=best_match,
                    confidence=confidence,
                    organization_id=organization_id
                )
                result["fuzzy_matches"] += 1
                continue
            
            # Try many-to-one match if no exact or fuzzy match found
            many_to_one_matches = self.find_many_to_one_matches(
                bank_transaction=transaction,
                journal_entries=unreconciled_journal_entries
            )
            
            if many_to_one_matches:
                # Create suggested reconciliation for many-to-one match
                # Note: This creates a suggested match that needs user confirmation
                # The actual reconciliation creation is handled by ReconciliationEngine
                result["many_to_one_matches"] += 1
                logger.info(
                    f"Found many-to-one match: BankTransaction {transaction.id} "
                    f"<-> {len(many_to_one_matches)} journal entries"
                )
                continue
            
            # No match found
            result["unmatched"] += 1
        
        logger.info(f"Auto-reconciliation completed: {result}")
        return result

    def _get_unreconciled_transactions(
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
            
        Requirements: 8.1
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
        
        return transactions

    def _get_unreconciled_journal_entries(
        self,
        organization_id: UUID,
        date_from: date,
        date_to: date
    ) -> List[JournalEntry]:
        """
        Get unreconciled journal entries for a given date range.
        
        Filters journal entries that:
        - Are posted (status = 'posted')
        - Are within the specified date range
        - Have not been reconciled yet (no active reconciliation)
        
        Args:
            organization_id: Organization UUID for multi-tenant isolation
            date_from: Start date for filtering
            date_to: End date for filtering
            
        Returns:
            List of unreconciled JournalEntry instances
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
        
        return unreconciled

    def find_exact_matches(
        self,
        bank_transaction: BankTransaction,
        journal_entries: List[JournalEntry]
    ) -> Optional[JournalEntry]:
        """
        Find exact match for a bank transaction among journal entries.
        
        Match criteria (all must match exactly):
        1. Amount equals exactly
        2. Date equals exactly
        3. Reference equals exactly (bank_reference matches entry_no)
        
        Args:
            bank_transaction: BankTransaction to match
            journal_entries: List of candidate JournalEntry instances
            
        Returns:
            Matching JournalEntry if found, None otherwise
            
        Requirements: 8.2, 8.3, 8.4
        """
        for je in journal_entries:
            # Extract date from posting_date (datetime) for comparison
            je_date = je.posting_date.date() if hasattr(je.posting_date, 'date') else je.posting_date
            
            # Check all three conditions for exact match
            amount_matches = (
                abs(Decimal(str(je.total_debit)) - Decimal(str(bank_transaction.transaction_amount))) < Decimal('0.01')
                if bank_transaction.transaction_type == "debit"
                else abs(Decimal(str(je.total_credit)) - Decimal(str(bank_transaction.transaction_amount))) < Decimal('0.01')
            )
            
            date_matches = je_date == bank_transaction.statement_date
            
            # Reference matching - bank_reference should match entry_no
            # Both must exist and match exactly
            reference_matches = (
                bank_transaction.bank_reference is not None
                and je.entry_no is not None
                and bank_transaction.bank_reference == je.entry_no
            )
            
            if amount_matches and date_matches and reference_matches:
                logger.info(
                    f"Found exact match: BankTransaction {bank_transaction.id} "
                    f"<-> JournalEntry {je.id}"
                )
                return je
        
        return None

    def find_fuzzy_matches(
        self,
        bank_transaction: BankTransaction,
        journal_entries: List[JournalEntry]
    ) -> List[tuple[JournalEntry, Decimal]]:
        """
        Find fuzzy matches for a bank transaction among journal entries.
        
        Match criteria with confidence scoring:
        - Amount match (exact): Required (if not matched, skip entry)
        - Date exact match: Base confidence 0.8
        - Date within 3 days: Base confidence 0.7
        - Reference partial match: +0.15 bonus
        
        Confidence levels:
        - 0.7: Amount + date within 3 days
        - 0.8: Amount + exact date
        - 0.85: Amount + date within 3 days + reference
        - 0.95: Amount + exact date + reference
        
        Args:
            bank_transaction: BankTransaction to match
            journal_entries: List of candidate JournalEntry instances
            
        Returns:
            List of tuples (JournalEntry, confidence) sorted by confidence (highest first)
            Only returns matches with confidence >= 0.7
            
        Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
        """
        matches = []
        
        for je in journal_entries:
            confidence = Decimal("0.0")
            
            # Extract date from posting_date (datetime) for comparison
            je_date = je.posting_date.date() if hasattr(je.posting_date, 'date') else je.posting_date
            
            # Amount match (required)
            amount_matches = (
                abs(Decimal(str(je.total_debit)) - Decimal(str(bank_transaction.transaction_amount))) < Decimal('0.01')
                if bank_transaction.transaction_type == "debit"
                else abs(Decimal(str(je.total_credit)) - Decimal(str(bank_transaction.transaction_amount))) < Decimal('0.01')
            )
            
            if not amount_matches:
                continue  # Skip if amount doesn't match exactly
            
            # Date proximity scoring
            date_diff = abs((je_date - bank_transaction.statement_date).days)
            if date_diff == 0:
                # Exact date match gives base confidence of 0.8
                confidence = Decimal("0.8")
            elif date_diff <= 3:
                # Within 3 days gives base confidence of 0.7
                confidence = Decimal("0.7")
            else:
                # Date too far apart, skip this entry
                continue
            
            # Reference similarity (partial match) adds 0.15 to reach 0.95
            if bank_transaction.bank_reference and je.entry_no:
                # Check if either reference contains the other (partial match)
                if (bank_transaction.bank_reference in je.entry_no or 
                    je.entry_no in bank_transaction.bank_reference):
                    confidence += Decimal("0.15")
            
            # Only include matches with confidence >= 0.7
            if confidence >= Decimal("0.7"):
                matches.append((je, confidence))
                logger.info(
                    f"Found fuzzy match: BankTransaction {bank_transaction.id} "
                    f"<-> JournalEntry {je.id} (confidence: {confidence})"
                )
        
        # Sort by confidence (highest first)
        return sorted(matches, key=lambda x: x[1], reverse=True)

    def _create_exact_match_reconciliation(
        self,
        bank_transaction: BankTransaction,
        journal_entry: JournalEntry,
        organization_id: UUID
    ) -> BankReconciliation:
        """
        Create a reconciliation record for an exact match.
        
        Sets:
        - reconciliation_type: "auto_exact"
        - reconciliation_status: "confirmed"
        - match_confidence: 1.0
        - Updates bank transaction status to "reconciled"
        - Sets reconciled_at to current timestamp
        
        Args:
            bank_transaction: BankTransaction to reconcile
            journal_entry: Matching JournalEntry
            organization_id: Organization UUID
            
        Returns:
            Created BankReconciliation instance
            
        Requirements: 8.5, 8.6, 8.7, 8.8, 8.9, 8.10
        """
        # Create reconciliation record
        reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="auto_exact",
            reconciliation_status="confirmed",
            match_confidence=Decimal("1.0"),
            reconciled_by="system",
            reconciled_at=datetime.now(UTC),
            is_active=True
        )
        
        self.db.add(reconciliation)
        
        # Update bank transaction status
        bank_transaction.transaction_status = "reconciled"
        bank_transaction.reconciled_at = datetime.now(UTC)
        
        # Commit changes
        self.db.commit()
        self.db.refresh(reconciliation)
        
        logger.info(
            f"Created exact match reconciliation: {reconciliation.id} "
            f"(BankTransaction {bank_transaction.id} <-> JournalEntry {journal_entry.id})"
        )
        
        return reconciliation

    def _create_fuzzy_match_reconciliation(
        self,
        bank_transaction: BankTransaction,
        journal_entry: JournalEntry,
        confidence: Decimal,
        organization_id: UUID
    ) -> BankReconciliation:
        """
        Create a reconciliation record for a fuzzy match.
        
        Sets:
        - reconciliation_type: "auto_fuzzy"
        - reconciliation_status: "suggested"
        - match_confidence: calculated confidence score (0.7 to 0.95)
        - Does NOT update bank transaction status (remains "cleared")
        - Does NOT set reconciled_at (remains null)
        
        Args:
            bank_transaction: BankTransaction to reconcile
            journal_entry: Matching JournalEntry
            confidence: Match confidence score (0.7 to 0.95)
            organization_id: Organization UUID
            
        Returns:
            Created BankReconciliation instance
            
        Requirements: 9.7, 9.8, 9.9
        """
        # Create reconciliation record with "suggested" status
        reconciliation = BankReconciliation(
            organization_id=organization_id,
            bank_transaction_id=bank_transaction.id,
            journal_entry_id=journal_entry.id,
            reconciliation_type="auto_fuzzy",
            reconciliation_status="suggested",
            match_confidence=confidence,
            reconciled_by=None,  # Not reconciled yet, just suggested
            reconciled_at=None,  # Not reconciled yet
            is_active=True
        )
        
        self.db.add(reconciliation)
        
        # Do NOT update bank transaction status - it remains "cleared"
        # Do NOT set reconciled_at - it remains null
        # User must confirm the suggested match before reconciliation is complete
        
        # Commit changes
        self.db.commit()
        self.db.refresh(reconciliation)
        
        logger.info(
            f"Created fuzzy match reconciliation (suggested): {reconciliation.id} "
            f"(BankTransaction {bank_transaction.id} <-> JournalEntry {journal_entry.id}, "
            f"confidence: {confidence})"
        )
        
        return reconciliation

    def find_many_to_one_matches(
        self,
        bank_transaction: BankTransaction,
        journal_entries: List[JournalEntry],
        date_tolerance_days: int = 7
    ) -> Optional[List[JournalEntry]]:
        """
        Find combinations of journal entries that sum to bank transaction amount.
        
        This method detects many-to-one reconciliation scenarios where multiple
        journal entries (e.g., daily sales) are batched into one bank deposit.
        
        Algorithm:
        1. Filter journal entries within date_tolerance_days of the bank transaction
        2. Use subset sum algorithm to find combinations that sum to the target amount
        3. Apply tolerance of 0.01 for decimal precision
        
        Args:
            bank_transaction: BankTransaction to match
            journal_entries: List of candidate JournalEntry instances
            date_tolerance_days: Number of days before/after to search (default: 7)
            
        Returns:
            List of JournalEntry instances that sum to the bank transaction amount,
            or None if no valid combination is found
            
        Requirements: 10.10
        """
        from datetime import timedelta
        
        # Filter entries within date range
        date_from = bank_transaction.statement_date - timedelta(days=date_tolerance_days)
        date_to = bank_transaction.statement_date + timedelta(days=date_tolerance_days)
        
        candidates = []
        for je in journal_entries:
            # Extract date from posting_date (datetime) for comparison
            je_date = je.posting_date.date() if hasattr(je.posting_date, 'date') else je.posting_date
            
            if date_from <= je_date <= date_to:
                candidates.append(je)
        
        if not candidates:
            return None
        
        logger.info(
            f"Searching for many-to-one matches: {len(candidates)} candidates "
            f"within {date_tolerance_days} days of {bank_transaction.statement_date}"
        )
        
        # Find subset sum matching bank transaction amount
        target_amount = Decimal(str(bank_transaction.transaction_amount))
        tolerance = Decimal('0.01')
        
        matches = self._find_subset_sum(
            candidates=candidates,
            target_amount=target_amount,
            tolerance=tolerance,
            transaction_type=bank_transaction.transaction_type
        )
        
        if matches:
            logger.info(
                f"Found many-to-one match: {len(matches)} journal entries "
                f"sum to {target_amount}"
            )
        
        return matches if matches else None

    def _find_subset_sum(
        self,
        candidates: List[JournalEntry],
        target_amount: Decimal,
        tolerance: Decimal,
        transaction_type: str
    ) -> Optional[List[JournalEntry]]:
        """
        Find a subset of journal entries that sum to the target amount.
        
        Uses a dynamic programming approach to find combinations of journal entries
        that sum to the target amount within the specified tolerance.
        
        This is a simplified subset sum algorithm that finds the first valid
        combination. For production use, this could be enhanced to find the
        best combination or multiple combinations.
        
        Args:
            candidates: List of JournalEntry instances to consider
            target_amount: Target sum to match
            tolerance: Acceptable difference from target (e.g., 0.01)
            transaction_type: "debit" or "credit" to determine which field to use
            
        Returns:
            List of JournalEntry instances that sum to target_amount (within tolerance),
            or None if no valid combination is found
        """
        if not candidates:
            return None
        
        # Extract amounts from journal entries based on transaction type
        amounts = []
        for je in candidates:
            if transaction_type == "debit":
                amount = Decimal(str(je.total_debit))
            else:
                amount = Decimal(str(je.total_credit))
            amounts.append(amount)
        
        # Try to find a subset using backtracking
        # This is a simplified approach that works well for small to medium datasets
        result = self._backtrack_subset_sum(
            candidates=candidates,
            amounts=amounts,
            target=target_amount,
            tolerance=tolerance,
            index=0,
            current_sum=Decimal('0'),
            current_subset=[]
        )
        
        return result

    def _backtrack_subset_sum(
        self,
        candidates: List[JournalEntry],
        amounts: List[Decimal],
        target: Decimal,
        tolerance: Decimal,
        index: int,
        current_sum: Decimal,
        current_subset: List[JournalEntry]
    ) -> Optional[List[JournalEntry]]:
        """
        Backtracking helper for subset sum algorithm.
        
        Recursively explores combinations of journal entries to find a subset
        that sums to the target amount within tolerance.
        
        Args:
            candidates: List of all candidate JournalEntry instances
            amounts: List of amounts corresponding to candidates
            target: Target sum to match
            tolerance: Acceptable difference from target
            index: Current index in candidates list
            current_sum: Current sum of selected entries
            current_subset: Current subset of selected entries
            
        Returns:
            List of JournalEntry instances that sum to target (within tolerance),
            or None if no valid combination is found
        """
        # Check if current sum matches target within tolerance
        if abs(current_sum - target) <= tolerance:
            return current_subset.copy()
        
        # If we've exceeded the target by more than tolerance, prune this branch
        if current_sum > target + tolerance:
            return None
        
        # If we've exhausted all candidates, no solution found
        if index >= len(candidates):
            return None
        
        # Try including the current candidate
        new_subset = current_subset + [candidates[index]]
        new_sum = current_sum + amounts[index]
        
        result = self._backtrack_subset_sum(
            candidates=candidates,
            amounts=amounts,
            target=target,
            tolerance=tolerance,
            index=index + 1,
            current_sum=new_sum,
            current_subset=new_subset
        )
        
        if result is not None:
            return result
        
        # Try excluding the current candidate
        result = self._backtrack_subset_sum(
            candidates=candidates,
            amounts=amounts,
            target=target,
            tolerance=tolerance,
            index=index + 1,
            current_sum=current_sum,
            current_subset=current_subset
        )
        
        return result
