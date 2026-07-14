"""Bank Reconciliation API endpoints for banking integration"""

import csv
import io
import logging
from datetime import datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user, require_feature_flag
from app.models.bank_account import BankAccount
from app.models.bank_transaction import BankTransaction
from app.models.bank_reconciliation import BankReconciliation
from app.models.chart_of_account import Account
from app.models.journal_entry import JournalEntry
from app.schemas.bank_reconciliation import (
    AutoReconciliationRequest,
    AutoReconciliationResultResponse,
    BankAccountBalanceResponse,
    BankReconciliationResponse,
    ConfirmReconciliationRequest,
    ManualReconciliationRequest,
    ManyToOneReconciliationRequest,
    ReconciliationReportResponse,
    ReconciliationReportTransactionItem,
    RejectReconciliationRequest,
    SuggestedMatchResponse,
    UndoReconciliationRequest,
    UnreconciledJournalEntryResponse,
    UnreconciledTransactionResponse,
)
from app.services.auto_reconciliation_service import AutoReconciliationService
from app.services.reconciliation_engine import ReconciliationEngine
from app.core.constants import BOOK_MODULE_ENABLED, BOOK_CHART_OF_ACCOUNT_ENABLED

logger = logging.getLogger(__name__)
# Reconciliations require both the banking module and chart of accounts to be enabled
router = APIRouter(
    dependencies=[
        Depends(require_feature_flag(BOOK_MODULE_ENABLED)),
        Depends(require_feature_flag(BOOK_CHART_OF_ACCOUNT_ENABLED)),
    ]
)


@router.get(
    "/unreconciled-transactions",
    response_model=List[UnreconciledTransactionResponse],
    summary="List unreconciled transactions",
    description="Get list of unreconciled bank transactions for a given bank account and date range",
)
async def get_unreconciled_transactions(
    bank_account_id: UUID = Query(..., description="Bank account UUID"),
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get unreconciled bank transactions.
    
    Returns bank transactions with:
    - status = "cleared"
    - reconciled_at is null
    - within the specified date range
    
    **Requirements: 7.1, 14.8**
    """
    try:
        from datetime import datetime
        
        # Parse dates
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
        
        # Get unreconciled transactions
        engine = ReconciliationEngine(db)
        transactions = engine.get_unreconciled_transactions(
            bank_account_id=bank_account_id,
            date_from=date_from_obj,
            date_to=date_to_obj,
            organization_id=current_user.organization_id
        )
        
        return [UnreconciledTransactionResponse.model_validate(t) for t in transactions]
    
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Error fetching unreconciled transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch unreconciled transactions"
        )


@router.get(
    "/unreconciled-journal-entries",
    response_model=List[UnreconciledJournalEntryResponse],
    summary="List unreconciled journal entries",
    description="Get list of unreconciled journal entries for a given GL account and date range",
)
async def get_unreconciled_journal_entries(
    gl_account_id: UUID = Query(..., description="GL account UUID"),
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get unreconciled journal entries.
    
    Returns journal entries that:
    - Are posted (status = 'posted')
    - Are within the specified date range
    - Have not been reconciled yet (no active reconciliation)
    
    **Requirements: 7.2, 14.8**
    """
    try:
        from datetime import datetime
        
        # Parse dates
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
        
        # Get unreconciled journal entries
        engine = ReconciliationEngine(db)
        journal_entries = engine.get_unreconciled_journal_entries(
            gl_account_id=gl_account_id,
            date_from=date_from_obj,
            date_to=date_to_obj,
            organization_id=current_user.organization_id
        )
        
        return [UnreconciledJournalEntryResponse.model_validate(je) for je in journal_entries]
    
    except ValueError as e:
        logger.error(f"Invalid date format: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format. Use YYYY-MM-DD: {str(e)}"
        )
    
    except Exception as e:
        logger.error(f"Error fetching unreconciled journal entries: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch unreconciled journal entries"
        )


@router.post(
    "/manual",
    response_model=List[BankReconciliationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create manual reconciliation",
    description="Manually match a bank transaction with one or more journal entries",
)
async def create_manual_reconciliation(
    data: ManualReconciliationRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create manual reconciliation match.
    
    This endpoint:
    - Validates that the bank transaction is not already reconciled
    - Creates reconciliation record(s) with type "manual" and status "confirmed"
    - Updates the bank transaction status to "reconciled"
    - Sets reconciled_at timestamp and reconciled_by user
    - Supports optional notes parameter
    
    **Requirements: 7.3-7.10**
    """
    try:
        engine = ReconciliationEngine(db)
        reconciliations = engine.create_manual_match(
            bank_transaction_id=data.bank_transaction_id,
            journal_entry_ids=data.journal_entry_ids,
            reconciled_by=current_user.email,
            organization_id=current_user.organization_id,
            notes=data.notes
        )
        
        return [BankReconciliationResponse.model_validate(r) for r in reconciliations]
    
    except ValueError as e:
        logger.error(f"Validation error creating manual reconciliation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Error creating manual reconciliation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create manual reconciliation"
        )


@router.post(
    "/many-to-one",
    response_model=List[BankReconciliationResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Create many-to-one reconciliation",
    description="Match multiple journal entries to one bank transaction",
)
async def create_many_to_one_reconciliation(
    data: ManyToOneReconciliationRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create many-to-one reconciliation match.
    
    This endpoint:
    - Calculates the sum of all selected journal entries
    - Validates that the sum equals the bank transaction amount (with 0.01 tolerance)
    - Creates multiple reconciliation records with type "many_to_one" and status "confirmed"
    - Updates the bank transaction status to "reconciled"
    - Sets reconciled_at timestamp and reconciled_by user
    
    **Requirements: 10.1-10.9**
    """
    try:
        engine = ReconciliationEngine(db)
        reconciliations = engine.create_many_to_one_match(
            bank_transaction_id=data.bank_transaction_id,
            journal_entry_ids=data.journal_entry_ids,
            reconciled_by=current_user.email,
            organization_id=current_user.organization_id,
            notes=data.notes
        )
        
        return [BankReconciliationResponse.model_validate(r) for r in reconciliations]
    
    except ValueError as e:
        logger.error(f"Validation error creating many-to-one reconciliation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Error creating many-to-one reconciliation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create many-to-one reconciliation"
        )


@router.post(
    "/auto-run",
    response_model=AutoReconciliationResultResponse,
    summary="Run auto-reconciliation",
    description="Automatically match bank transactions with journal entries using various algorithms",
)
async def run_auto_reconciliation(
    data: AutoReconciliationRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Run auto-reconciliation for unreconciled bank transactions.
    
    Filters bank transactions with status "cleared" and reconciled_at is null,
    then attempts to match them with journal entries using:
    - Exact match algorithm (amount, date, reference all match exactly)
    - Fuzzy match algorithm (amount matches, date within 3 days, optional reference match)
    - Many-to-one detection (multiple journal entries sum to bank transaction amount)
    
    **Requirements: 8.1-8.10, 9.1-9.10, 10.10**
    """
    try:
        service = AutoReconciliationService(db)
        result = service.run_auto_reconciliation(
            bank_account_id=data.bank_account_id,
            date_from=data.date_from,
            date_to=data.date_to,
            organization_id=current_user.organization_id
        )
        
        return AutoReconciliationResultResponse(**result)
    
    except Exception as e:
        logger.error(f"Error running auto-reconciliation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to run auto-reconciliation"
        )


@router.post(
    "/{reconciliation_id}/confirm",
    response_model=BankReconciliationResponse,
    summary="Confirm suggested match",
    description="Confirm a suggested fuzzy match reconciliation",
)
async def confirm_suggested_match(
    reconciliation_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Confirm a suggested fuzzy match reconciliation.
    
    This endpoint:
    - Validates that the reconciliation exists and has status "suggested"
    - Updates the reconciliation status to "confirmed"
    - Updates the bank transaction status to "reconciled"
    - Sets reconciled_at timestamp and reconciled_by user
    
    **Requirements: 9.10**
    """
    try:
        engine = ReconciliationEngine(db)
        reconciliation = engine.confirm_suggested_match(
            reconciliation_id=reconciliation_id,
            confirmed_by=current_user.email,
            organization_id=current_user.organization_id
        )
        
        return BankReconciliationResponse.model_validate(reconciliation)
    
    except ValueError as e:
        logger.error(f"Validation error confirming suggested match: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Error confirming suggested match: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to confirm suggested match"
        )


@router.post(
    "/{reconciliation_id}/reject",
    response_model=BankReconciliationResponse,
    summary="Reject suggested match",
    description="Reject a suggested fuzzy match reconciliation",
)
async def reject_suggested_match(
    reconciliation_id: UUID,
    data: RejectReconciliationRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Reject a suggested fuzzy match reconciliation.
    
    This endpoint:
    - Validates that the reconciliation exists and has status "suggested"
    - Updates the reconciliation status to "rejected"
    - Does NOT update the bank transaction status (remains "cleared")
    - Records who rejected the match and when
    - Optionally stores a reason for rejection
    
    **Requirements: 9.10**
    """
    try:
        engine = ReconciliationEngine(db)
        reconciliation = engine.reject_suggested_match(
            reconciliation_id=reconciliation_id,
            rejected_by=current_user.email,
            organization_id=current_user.organization_id,
            reason=data.reason
        )
        
        return BankReconciliationResponse.model_validate(reconciliation)
    
    except ValueError as e:
        logger.error(f"Validation error rejecting suggested match: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Error rejecting suggested match: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject suggested match"
        )


@router.post(
    "/{reconciliation_id}/undo",
    response_model=BankReconciliationResponse,
    summary="Undo reconciliation",
    description="Undo a confirmed reconciliation match",
)
async def undo_reconciliation(
    reconciliation_id: UUID,
    data: UndoReconciliationRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Undo a confirmed reconciliation match.
    
    This endpoint:
    - Updates the reconciliation status to "rejected"
    - Updates the bank transaction status back to "cleared"
    - Sets reconciled_at and reconciled_by to null
    - Preserves the reconciliation record (does not delete)
    - Logs the undo action with user and timestamp
    - Checks 90-day restriction for non-elevated users
    
    **Requirements: 17.1-17.10**
    """
    try:
        engine = ReconciliationEngine(db)
        
        # TODO: Implement proper permission checking for elevated permissions
        # For now, assume all users have elevated permissions
        has_elevated_permissions = True
        
        reconciliation = engine.undo_reconciliation(
            reconciliation_id=reconciliation_id,
            undone_by=current_user.email,
            organization_id=current_user.organization_id,
            reason=data.reason,
            has_elevated_permissions=has_elevated_permissions
        )
        
        return BankReconciliationResponse.model_validate(reconciliation)
    
    except ValueError as e:
        logger.error(f"Validation error undoing reconciliation: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Error undoing reconciliation: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to undo reconciliation"
        )


@router.get(
    "/suggested",
    response_model=List[SuggestedMatchResponse],
    summary="List suggested matches",
    description="Get list of suggested fuzzy match reconciliations",
)
async def get_suggested_matches(
    bank_account_id: Optional[UUID] = Query(None, description="Filter by bank account"),
    date_from: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    min_confidence: Optional[float] = Query(None, description="Minimum match confidence (0.0-1.0)"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get suggested fuzzy match reconciliations.
    
    Returns reconciliations with:
    - reconciliation_status = "suggested"
    - is_active = true
    - Optional filters by bank account, date range, and minimum confidence
    
    **Requirements: 9.10**
    """
    try:
        from datetime import datetime
        from decimal import Decimal
        
        # Build query
        query = db.query(BankReconciliation).filter(
            and_(
                BankReconciliation.organization_id == current_user.organization_id,
                BankReconciliation.reconciliation_status == "suggested",
                BankReconciliation.is_active == True
            )
        )
        
        # Apply filters
        if bank_account_id:
            query = query.join(BankTransaction).filter(
                BankTransaction.bank_account_id == bank_account_id
            )
        
        if date_from:
            date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
            query = query.join(BankTransaction).filter(
                BankTransaction.statement_date >= date_from_obj
            )
        
        if date_to:
            date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
            query = query.join(BankTransaction).filter(
                BankTransaction.statement_date <= date_to_obj
            )
        
        if min_confidence is not None:
            query = query.filter(
                BankReconciliation.match_confidence >= Decimal(str(min_confidence))
            )
        
        # Execute query
        reconciliations = query.all()
        
        # Build response with related data
        results = []
        for reconciliation in reconciliations:
            # Fetch related bank transaction
            bank_transaction = db.query(BankTransaction).filter(
                BankTransaction.id == reconciliation.bank_transaction_id
            ).first()
            
            # Fetch related journal entry
            journal_entry = db.query(JournalEntry).filter(
                JournalEntry.id == reconciliation.journal_entry_id
            ).first()
            
            if bank_transaction and journal_entry:
                # Determine match reasons based on confidence
                match_reasons = []
                if reconciliation.match_confidence >= Decimal("0.95"):
                    match_reasons = ["Amount matches exactly", "Date matches exactly", "Reference has partial match"]
                elif reconciliation.match_confidence >= Decimal("0.8"):
                    match_reasons = ["Amount matches exactly", "Date matches exactly"]
                elif reconciliation.match_confidence >= Decimal("0.7"):
                    match_reasons = ["Amount matches exactly", "Date within 3 days"]
                
                results.append(
                    SuggestedMatchResponse(
                        reconciliation=BankReconciliationResponse.model_validate(reconciliation),
                        bank_transaction=UnreconciledTransactionResponse.model_validate(bank_transaction),
                        journal_entry=UnreconciledJournalEntryResponse.model_validate(journal_entry),
                        match_confidence=reconciliation.match_confidence,
                        match_reasons=match_reasons
                    )
                )
        
        return results
    
    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except Exception as e:
        logger.error(f"Error fetching suggested matches: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch suggested matches"
        )



@router.get(
    "/report",
    response_model=ReconciliationReportResponse,
    summary="Generate reconciliation report",
    description="Generate a comprehensive reconciliation report for a bank account with filters",
)
async def generate_reconciliation_report(
    bank_account_id: UUID = Query(..., description="Bank account UUID"),
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by transaction status (pending, cleared, reconciled, void)"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Generate reconciliation report showing all bank transactions for a specified period
    """


@router.get(
    "/report",
    response_model=ReconciliationReportResponse,
    summary="Generate reconciliation report",
    description="Generate a comprehensive reconciliation report for a bank account and date range",
)
async def generate_reconciliation_report(
    bank_account_id: UUID = Query(..., description="Bank account UUID"),
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status: pending, cleared, reconciled, void"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Generate reconciliation report showing all bank transactions for a selected date range.
    
    The report includes:
    - Transaction details (date, amount, description, status, matched journal entry)
    - Summary statistics (total imported, total reconciled, total unreconciled)
    - Transactions grouped by status
    - Report generation metadata
    
    **Requirements: 16.1-16.7**
    """
    try:
        from datetime import datetime
        
        # Parse dates
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
        
        # Verify bank account exists and belongs to organization
        bank_account = db.query(BankAccount).filter(
            and_(
                BankAccount.id == bank_account_id,
                BankAccount.organization_id == current_user.organization_id
            )
        ).first()
        
        if not bank_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found"
            )
        
        # Get GL account name
        gl_account = db.query(Account).filter(Account.id == bank_account.gl_account_id).first()
        gl_account_name = gl_account.account_name if gl_account else "Unknown"
        
        # Build query for transactions
        query = db.query(BankTransaction).filter(
            and_(
                BankTransaction.bank_account_id == bank_account_id,
                BankTransaction.organization_id == current_user.organization_id,
                BankTransaction.statement_date >= date_from_obj,
                BankTransaction.statement_date <= date_to_obj
            )
        )
        
        # Apply status filter if provided
        if status:
            if status not in ('pending', 'cleared', 'reconciled', 'void'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Status must be one of: pending, cleared, reconciled, void"
                )
            query = query.filter(BankTransaction.transaction_status == status)
        
        # Execute query
        transactions = query.order_by(BankTransaction.statement_date).all()
        
        # Build transaction items with reconciliation info
        transaction_items = []
        total_imported = Decimal('0')
        total_reconciled = Decimal('0')
        reconciled_count = 0
        cleared_count = 0
        pending_count = 0
        
        for txn in transactions:
            # Get reconciliation info if exists
            reconciliation = db.query(BankReconciliation).filter(
                and_(
                    BankReconciliation.bank_transaction_id == txn.id,
                    BankReconciliation.is_active == True,
                    BankReconciliation.reconciliation_status == "confirmed"
                )
            ).first()
            
            matched_journal_entry = None
            reconciliation_type = None
            
            if reconciliation:
                journal_entry = db.query(JournalEntry).filter(
                    JournalEntry.id == reconciliation.journal_entry_id
                ).first()
                if journal_entry:
                    matched_journal_entry = journal_entry.entry_no
                    reconciliation_type = reconciliation.reconciliation_type
            
            # Build transaction item
            transaction_items.append(
                ReconciliationReportTransactionItem(
                    transaction_id=txn.id,
                    transaction_date=txn.statement_date,
                    amount=txn.transaction_amount,
                    description=txn.transaction_description,
                    reference=txn.bank_reference,
                    status=txn.transaction_status,
                    transaction_type=txn.transaction_type,
                    matched_journal_entry=matched_journal_entry,
                    reconciliation_type=reconciliation_type
                )
            )
            
            # Update statistics
            total_imported += txn.transaction_amount
            
            if txn.transaction_status == "reconciled":
                total_reconciled += txn.transaction_amount
                reconciled_count += 1
            elif txn.transaction_status == "cleared":
                cleared_count += 1
            elif txn.transaction_status == "pending":
                pending_count += 1
        
        # Calculate unreconciled amount
        total_unreconciled = total_imported - total_reconciled
        
        # Build response
        return ReconciliationReportResponse(
            bank_account_id=bank_account_id,
            bank_account_name=f"{bank_account.bank_name} - {bank_account.account_holder_name}",
            date_from=date_from_obj,
            date_to=date_to_obj,
            transactions=transaction_items,
            total_imported=total_imported,
            total_reconciled=total_reconciled,
            total_unreconciled=total_unreconciled,
            reconciled_count=reconciled_count,
            cleared_count=cleared_count,
            pending_count=pending_count,
            generated_at=datetime.now(),
            generated_by=current_user.email
        )
    
    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error generating reconciliation report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate reconciliation report"
        )


@router.get(
    "/report/export/csv",
    summary="Export reconciliation report to CSV",
    description="Export reconciliation report as CSV file",
)
async def export_reconciliation_report_csv(
    bank_account_id: UUID = Query(..., description="Bank account UUID"),
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status: pending, cleared, reconciled, void"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Export reconciliation report to CSV format.
    
    Returns a CSV file with columns:
    - Date
    - Amount
    - Description
    - Reference
    - Status
    - Type
    - Matched Journal Entry
    - Reconciliation Type
    
    **Requirements: 16.8**
    """
    try:
        # Generate the report data
        report = await generate_reconciliation_report(
            bank_account_id=bank_account_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
            current_user=current_user,
            db=db
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Date",
            "Amount",
            "Description",
            "Reference",
            "Status",
            "Type",
            "Matched Journal Entry",
            "Reconciliation Type"
        ])
        
        # Write transaction rows
        for txn in report.transactions:
            writer.writerow([
                txn.transaction_date.strftime("%Y-%m-%d"),
                str(txn.amount),
                txn.description or "",
                txn.reference or "",
                txn.status,
                txn.transaction_type,
                txn.matched_journal_entry or "",
                txn.reconciliation_type or ""
            ])
        
        # Write summary rows
        writer.writerow([])
        writer.writerow(["Summary"])
        writer.writerow(["Total Imported", str(report.total_imported)])
        writer.writerow(["Total Reconciled", str(report.total_reconciled)])
        writer.writerow(["Total Unreconciled", str(report.total_unreconciled)])
        writer.writerow(["Reconciled Count", str(report.reconciled_count)])
        writer.writerow(["Cleared Count", str(report.cleared_count)])
        writer.writerow(["Pending Count", str(report.pending_count)])
        writer.writerow([])
        writer.writerow(["Generated At", report.generated_at.strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(["Generated By", report.generated_by])
        
        # Return CSV response
        csv_content = output.getvalue()
        output.close()
        
        filename = f"reconciliation_report_{bank_account_id}_{date_from}_{date_to}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error exporting reconciliation report to CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export reconciliation report to CSV"
        )


@router.get(
    "/report/export/pdf",
    summary="Export reconciliation report to PDF",
    description="Export reconciliation report as PDF file",
)
async def export_reconciliation_report_pdf(
    bank_account_id: UUID = Query(..., description="Bank account UUID"),
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status: pending, cleared, reconciled, void"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Export reconciliation report to PDF format.
    
    Note: This is a stub implementation. Full PDF generation requires
    a PDF library like ReportLab or WeasyPrint.
    
    **Requirements: 16.9**
    """
    try:
        # Generate the report data
        report = await generate_reconciliation_report(
            bank_account_id=bank_account_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
            current_user=current_user,
            db=db
        )
        
        # TODO: Implement PDF generation using ReportLab or WeasyPrint
        # For now, return a simple text-based PDF placeholder
        
        pdf_content = f"""
RECONCILIATION REPORT
=====================

Bank Account: {report.bank_account_name}
Period: {report.date_from} to {report.date_to}
Generated: {report.generated_at.strftime("%Y-%m-%d %H:%M:%S")}
Generated By: {report.generated_by}

SUMMARY
-------
Total Imported: {report.total_imported}
Total Reconciled: {report.total_reconciled}
Total Unreconciled: {report.total_unreconciled}

Reconciled Transactions: {report.reconciled_count}
Cleared Transactions: {report.cleared_count}
Pending Transactions: {report.pending_count}

TRANSACTIONS
------------
"""
        
        for txn in report.transactions:
            transaction_info = f"""
Date: {txn.transaction_date}
Amount: {txn.amount} ({txn.transaction_type})
Description: {txn.description or 'N/A'}
Reference: {txn.reference or 'N/A'}
Status: {txn.status}
Matched Journal Entry: {txn.matched_journal_entry or 'Not reconciled'}
Reconciliation Type: {txn.reconciliation_type or 'N/A'}
---
"""
            pdf_content += transaction_info
        
        filename = f"reconciliation_report_{bank_account_id}_{date_from}_{date_to}.pdf"
        
        # Return as plain text for now (should be PDF in production)
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error exporting reconciliation report to PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export reconciliation report to PDF"
        )


@router.get(
    "/report",
    response_model=ReconciliationReportResponse,
    summary="Generate reconciliation report",
    description="Generate a comprehensive reconciliation report for a bank account and date range",
)
async def generate_reconciliation_report(
    bank_account_id: UUID = Query(..., description="Bank account UUID"),
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status: pending, cleared, reconciled, void"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Generate reconciliation report showing all bank transactions for a selected date range.
    
    The report includes:
    - Transaction details (date, amount, description, status, matched journal entry)
    - Summary statistics (total imported, total reconciled, total unreconciled)
    - Transactions grouped by status
    - Report generation metadata
    
    **Requirements: 16.1-16.7**
    """
    try:
        from datetime import datetime
        
        # Parse dates
        date_from_obj = datetime.strptime(date_from, "%Y-%m-%d").date()
        date_to_obj = datetime.strptime(date_to, "%Y-%m-%d").date()
        
        # Verify bank account exists and belongs to organization
        bank_account = db.query(BankAccount).filter(
            and_(
                BankAccount.id == bank_account_id,
                BankAccount.organization_id == current_user.organization_id
            )
        ).first()
        
        if not bank_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found"
            )
        
        # Get GL account name
        gl_account = db.query(Account).filter(Account.id == bank_account.gl_account_id).first()
        gl_account_name = gl_account.account_name if gl_account else "Unknown"
        
        # Build query for transactions
        query = db.query(BankTransaction).filter(
            and_(
                BankTransaction.bank_account_id == bank_account_id,
                BankTransaction.organization_id == current_user.organization_id,
                BankTransaction.statement_date >= date_from_obj,
                BankTransaction.statement_date <= date_to_obj
            )
        )
        
        # Apply status filter if provided
        if status:
            if status not in ('pending', 'cleared', 'reconciled', 'void'):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Status must be one of: pending, cleared, reconciled, void"
                )
            query = query.filter(BankTransaction.transaction_status == status)
        
        # Execute query
        transactions = query.order_by(BankTransaction.statement_date).all()
        
        # Build transaction items with reconciliation info
        transaction_items = []
        total_imported = Decimal('0')
        total_reconciled = Decimal('0')
        reconciled_count = 0
        cleared_count = 0
        pending_count = 0
        
        for txn in transactions:
            # Get reconciliation info if exists
            reconciliation = db.query(BankReconciliation).filter(
                and_(
                    BankReconciliation.bank_transaction_id == txn.id,
                    BankReconciliation.is_active == True,
                    BankReconciliation.reconciliation_status == "confirmed"
                )
            ).first()
            
            matched_journal_entry = None
            reconciliation_type = None
            
            if reconciliation:
                journal_entry = db.query(JournalEntry).filter(
                    JournalEntry.id == reconciliation.journal_entry_id
                ).first()
                if journal_entry:
                    matched_journal_entry = journal_entry.entry_no
                    reconciliation_type = reconciliation.reconciliation_type
            
            # Build transaction item
            transaction_items.append(
                ReconciliationReportTransactionItem(
                    transaction_id=txn.id,
                    transaction_date=txn.statement_date,
                    amount=txn.transaction_amount,
                    description=txn.transaction_description,
                    reference=txn.bank_reference,
                    status=txn.transaction_status,
                    transaction_type=txn.transaction_type,
                    matched_journal_entry=matched_journal_entry,
                    reconciliation_type=reconciliation_type
                )
            )
            
            # Update statistics
            total_imported += txn.transaction_amount
            
            if txn.transaction_status == "reconciled":
                total_reconciled += txn.transaction_amount
                reconciled_count += 1
            elif txn.transaction_status == "cleared":
                cleared_count += 1
            elif txn.transaction_status == "pending":
                pending_count += 1
        
        # Calculate unreconciled amount
        total_unreconciled = total_imported - total_reconciled
        
        # Build response
        return ReconciliationReportResponse(
            bank_account_id=bank_account_id,
            bank_account_name=f"{bank_account.bank_name} - {bank_account.account_holder_name}",
            date_from=date_from_obj,
            date_to=date_to_obj,
            transactions=transaction_items,
            total_imported=total_imported,
            total_reconciled=total_reconciled,
            total_unreconciled=total_unreconciled,
            reconciled_count=reconciled_count,
            cleared_count=cleared_count,
            pending_count=pending_count,
            generated_at=datetime.now(),
            generated_by=current_user.email
        )
    
    except ValueError as e:
        logger.error(f"Invalid parameter: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error generating reconciliation report: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate reconciliation report"
        )


@router.get(
    "/report/export/csv",
    summary="Export reconciliation report to CSV",
    description="Export reconciliation report as CSV file",
)
async def export_reconciliation_report_csv(
    bank_account_id: UUID = Query(..., description="Bank account UUID"),
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status: pending, cleared, reconciled, void"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Export reconciliation report to CSV format.
    
    Returns a CSV file with columns:
    - Date
    - Amount
    - Description
    - Reference
    - Status
    - Type
    - Matched Journal Entry
    - Reconciliation Type
    
    **Requirements: 16.8**
    """
    try:
        # Generate the report data
        report = await generate_reconciliation_report(
            bank_account_id=bank_account_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
            current_user=current_user,
            db=db
        )
        
        # Create CSV in memory
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "Date",
            "Amount",
            "Description",
            "Reference",
            "Status",
            "Type",
            "Matched Journal Entry",
            "Reconciliation Type"
        ])
        
        # Write transaction rows
        for txn in report.transactions:
            writer.writerow([
                txn.transaction_date.strftime("%Y-%m-%d"),
                str(txn.amount),
                txn.description or "",
                txn.reference or "",
                txn.status,
                txn.transaction_type,
                txn.matched_journal_entry or "",
                txn.reconciliation_type or ""
            ])
        
        # Write summary rows
        writer.writerow([])
        writer.writerow(["Summary"])
        writer.writerow(["Total Imported", str(report.total_imported)])
        writer.writerow(["Total Reconciled", str(report.total_reconciled)])
        writer.writerow(["Total Unreconciled", str(report.total_unreconciled)])
        writer.writerow(["Reconciled Count", str(report.reconciled_count)])
        writer.writerow(["Cleared Count", str(report.cleared_count)])
        writer.writerow(["Pending Count", str(report.pending_count)])
        writer.writerow([])
        writer.writerow(["Generated At", report.generated_at.strftime("%Y-%m-%d %H:%M:%S")])
        writer.writerow(["Generated By", report.generated_by])
        
        # Return CSV response
        csv_content = output.getvalue()
        output.close()
        
        filename = f"reconciliation_report_{bank_account_id}_{date_from}_{date_to}.csv"
        
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error exporting reconciliation report to CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export reconciliation report to CSV"
        )


@router.get(
    "/report/export/pdf",
    summary="Export reconciliation report to PDF",
    description="Export reconciliation report as PDF file",
)
async def export_reconciliation_report_pdf(
    bank_account_id: UUID = Query(..., description="Bank account UUID"),
    date_from: str = Query(..., description="Start date (YYYY-MM-DD)"),
    date_to: str = Query(..., description="End date (YYYY-MM-DD)"),
    status: Optional[str] = Query(None, description="Filter by status: pending, cleared, reconciled, void"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Export reconciliation report to PDF format.
    
    Note: This is a stub implementation. Full PDF generation requires
    a PDF library like ReportLab or WeasyPrint.
    
    **Requirements: 16.9**
    """
    try:
        # Generate the report data
        report = await generate_reconciliation_report(
            bank_account_id=bank_account_id,
            date_from=date_from,
            date_to=date_to,
            status=status,
            current_user=current_user,
            db=db
        )
        
        # TODO: Implement PDF generation using ReportLab or WeasyPrint
        # For now, return a simple text-based PDF placeholder
        
        pdf_content = f"""
RECONCILIATION REPORT
=====================

Bank Account: {report.bank_account_name}
Period: {report.date_from} to {report.date_to}
Generated: {report.generated_at.strftime("%Y-%m-%d %H:%M:%S")}
Generated By: {report.generated_by}

SUMMARY
-------
Total Imported: {report.total_imported}
Total Reconciled: {report.total_reconciled}
Total Unreconciled: {report.total_unreconciled}

Reconciled Transactions: {report.reconciled_count}
Cleared Transactions: {report.cleared_count}
Pending Transactions: {report.pending_count}

TRANSACTIONS
------------
"""
        
        for txn in report.transactions:
            transaction_info = f"""
Date: {txn.transaction_date}
Amount: {txn.amount} ({txn.transaction_type})
Description: {txn.description or 'N/A'}
Reference: {txn.reference or 'N/A'}
Status: {txn.status}
Matched Journal Entry: {txn.matched_journal_entry or 'Not reconciled'}
Reconciliation Type: {txn.reconciliation_type or 'N/A'}
---
"""
            pdf_content += transaction_info
        
        filename = f"reconciliation_report_{bank_account_id}_{date_from}_{date_to}.pdf"
        
        # Return as plain text for now (should be PDF in production)
        return Response(
            content=pdf_content,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error exporting reconciliation report to PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to export reconciliation report to PDF"
        )
