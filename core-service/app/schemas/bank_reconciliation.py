"""Bank Reconciliation schemas for API requests and responses"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ManualReconciliationRequest(BaseModel):
    """Request schema for creating manual reconciliation"""
    
    bank_transaction_id: UUID = Field(..., description="UUID of the bank transaction to reconcile")
    journal_entry_ids: List[UUID] = Field(..., description="List of journal entry UUIDs to match")
    notes: Optional[str] = Field(None, description="Optional notes about the reconciliation")
    
    @field_validator('journal_entry_ids')
    @classmethod
    def validate_journal_entry_ids(cls, v):
        if not v or len(v) == 0:
            raise ValueError("At least one journal entry ID is required")
        return v


class ManyToOneReconciliationRequest(BaseModel):
    """Request schema for creating many-to-one reconciliation"""
    
    bank_transaction_id: UUID = Field(..., description="UUID of the bank transaction to reconcile")
    journal_entry_ids: List[UUID] = Field(..., description="List of journal entry UUIDs to match (must be 2 or more)")
    notes: Optional[str] = Field(None, description="Optional notes about the reconciliation")
    
    @field_validator('journal_entry_ids')
    @classmethod
    def validate_journal_entry_ids(cls, v):
        if not v or len(v) < 2:
            raise ValueError("Many-to-one reconciliation requires at least 2 journal entries")
        return v


class AutoReconciliationRequest(BaseModel):
    """Request schema for running auto-reconciliation"""
    
    bank_account_id: UUID = Field(..., description="UUID of the bank account to reconcile")
    date_from: date = Field(..., description="Start date for reconciliation")
    date_to: date = Field(..., description="End date for reconciliation")


class ConfirmReconciliationRequest(BaseModel):
    """Request schema for confirming a suggested match"""
    
    pass  # No additional fields needed, reconciliation_id comes from path


class RejectReconciliationRequest(BaseModel):
    """Request schema for rejecting a suggested match"""
    
    reason: Optional[str] = Field(None, description="Optional reason for rejecting the match")


class UndoReconciliationRequest(BaseModel):
    """Request schema for undoing a reconciliation"""
    
    reason: str = Field(..., description="Reason for undoing the reconciliation")


class BankReconciliationResponse(BaseModel):
    """Response schema for bank reconciliation details"""
    
    id: UUID
    organization_id: UUID
    bank_transaction_id: UUID
    journal_entry_id: UUID
    reconciliation_type: str  # manual, auto_exact, auto_fuzzy, many_to_one
    reconciliation_status: str  # suggested, confirmed, rejected
    match_confidence: Optional[Decimal] = None
    exchange_rate: Optional[Decimal] = None
    converted_amount: Optional[Decimal] = None
    reconciled_by: Optional[str] = None
    reconciled_at: Optional[datetime] = None
    notes: Optional[str] = None
    is_active: bool
    undone_by: Optional[str] = None
    undone_at: Optional[datetime] = None
    undo_reason: Optional[str] = None
    
    model_config = {"from_attributes": True}


class UnreconciledTransactionResponse(BaseModel):
    """Response schema for unreconciled bank transactions"""
    
    id: UUID
    bank_account_id: UUID
    statement_date: date
    transaction_amount: Decimal
    transaction_description: Optional[str] = None
    bank_reference: Optional[str] = None
    transaction_type: str  # debit, credit
    imported_at: datetime
    
    model_config = {"from_attributes": True}


class UnreconciledJournalEntryResponse(BaseModel):
    """Response schema for unreconciled journal entries"""
    
    id: UUID
    entry_no: str
    posting_date: datetime
    total_debit: Decimal
    total_credit: Decimal
    reference_id: Optional[str] = None
    description: Optional[str] = None
    status: str
    
    model_config = {"from_attributes": True}


class SuggestedMatchResponse(BaseModel):
    """Response schema for suggested reconciliation matches"""
    
    reconciliation: BankReconciliationResponse
    bank_transaction: UnreconciledTransactionResponse
    journal_entry: UnreconciledJournalEntryResponse
    match_confidence: Decimal
    match_reasons: List[str] = Field(default_factory=list, description="Reasons why this match was suggested")
    
    model_config = {"from_attributes": True}


class AutoReconciliationResultResponse(BaseModel):
    """Response schema for auto-reconciliation results"""
    
    exact_matches: int = Field(..., description="Number of exact matches found and confirmed")
    fuzzy_matches: int = Field(..., description="Number of fuzzy matches suggested")
    many_to_one_matches: int = Field(..., description="Number of many-to-one matches detected")
    unmatched: int = Field(..., description="Number of transactions that couldn't be matched")
    total_processed: int = Field(..., description="Total number of transactions processed")
    
    model_config = {"from_attributes": True}


class ReconciliationListResponse(BaseModel):
    """Response schema for paginated list of reconciliations"""
    
    items: List[BankReconciliationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    model_config = {"from_attributes": True}


class ReconciliationFilterParams(BaseModel):
    """Query parameters for filtering reconciliations"""
    
    bank_account_id: Optional[UUID] = Field(None, description="Filter by bank account")
    reconciliation_type: Optional[str] = Field(None, description="Filter by reconciliation type")
    reconciliation_status: Optional[str] = Field(None, description="Filter by reconciliation status")
    date_from: Optional[date] = Field(None, description="Filter reconciliations from this date")
    date_to: Optional[date] = Field(None, description="Filter reconciliations to this date")
    
    @field_validator('reconciliation_type')
    @classmethod
    def validate_reconciliation_type(cls, v):
        if v and v not in ('manual', 'auto_exact', 'auto_fuzzy', 'many_to_one'):
            raise ValueError("Reconciliation type must be one of: manual, auto_exact, auto_fuzzy, many_to_one")
        return v
    
    @field_validator('reconciliation_status')
    @classmethod
    def validate_reconciliation_status(cls, v):
        if v and v not in ('suggested', 'confirmed', 'rejected'):
            raise ValueError("Reconciliation status must be one of: suggested, confirmed, rejected")
        return v


class ReconciliationReportTransactionItem(BaseModel):
    """Transaction item in reconciliation report"""
    
    transaction_id: UUID
    transaction_date: date
    amount: Decimal
    description: Optional[str] = None
    reference: Optional[str] = None
    status: str  # pending, cleared, reconciled, void
    transaction_type: str  # debit, credit
    matched_journal_entry: Optional[str] = Field(None, description="Journal entry number if reconciled")
    reconciliation_type: Optional[str] = Field(None, description="Type of reconciliation if matched")
    
    model_config = {"from_attributes": True}


class ReconciliationReportResponse(BaseModel):
    """Response schema for reconciliation report"""
    
    bank_account_id: UUID
    bank_account_name: str
    date_from: date
    date_to: date
    transactions: List[ReconciliationReportTransactionItem]
    total_imported: Decimal = Field(..., description="Sum of all bank transaction amounts")
    total_reconciled: Decimal = Field(..., description="Sum of reconciled bank transaction amounts")
    total_unreconciled: Decimal = Field(..., description="Difference between imported and reconciled")
    reconciled_count: int = Field(..., description="Number of reconciled transactions")
    cleared_count: int = Field(..., description="Number of cleared (unreconciled) transactions")
    pending_count: int = Field(..., description="Number of pending transactions")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    generated_by: str = Field(..., description="User who generated the report")
    
    model_config = {"from_attributes": True}


class BankAccountBalanceResponse(BaseModel):
    """Response schema for bank account balance information"""
    
    bank_account_id: UUID
    bank_account_name: str
    gl_account_id: UUID
    gl_account_name: str
    currency: str
    bank_balance: Decimal = Field(..., description="Balance calculated from bank transactions")
    gl_balance: Decimal = Field(..., description="Balance calculated from journal entries")
    unreconciled_amount: Decimal = Field(..., description="Difference between bank and GL balance")
    last_reconciled_date: Optional[date] = Field(None, description="Date of last reconciliation")
    unreconciled_transaction_count: int = Field(..., description="Number of unreconciled transactions")
    
    model_config = {"from_attributes": True}
