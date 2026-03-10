"""Bank Account service with business logic for banking integration"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session, joinedload

from app.core.exceptions import (
    BankAccountNotFoundException,
    DuplicateIbanException,
    InvalidAccountStateException,
    UnauthorizedException,
    ReconciledTransactionDeletionException,
    ValidationError,
)
from app.models.bank_account import BankAccount, BankAccountHistory
from app.models.bank_transaction import BankTransaction
from app.models.chart_of_account import Account
from app.schemas.bank_account import (
    BankAccountCreate,
    BankAccountListResponse,
    BankAccountResponse,
    BankAccountUpdate,
    BankingOverviewResponse,
)

logger = logging.getLogger(__name__)


class BankAccountService:
    """Service for bank account operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_bank_account(
        self,
        gl_account_id: UUID,
        data: BankAccountCreate,
        organization_id: UUID,
        current_user: str,
    ) -> BankAccount:
        """Create a new bank account linked to a GL account"""

        # Validate GL account exists and belongs to organization
        gl_account = self._get_gl_account_by_id(gl_account_id, organization_id)

        # Validate business rules
        self._validate_create_rules(data, gl_account_id, organization_id)

        # Create bank account
        bank_account = BankAccount(
            organization_id=organization_id,
            gl_account_id=gl_account_id,
            bank_name=data.bank_name,
            account_holder_name=data.account_holder_name,
            account_number=data.account_number,
            iban=data.iban,
            swift_code=data.swift_code,
            routing_number=data.routing_number,
            branch_name=data.branch_name,
            branch_code=data.branch_code,
            sort_code=data.sort_code,
            bsb_number=data.bsb_number,
            account_type=data.account_type,
            account_purpose=data.account_purpose,
            is_primary=data.is_primary,
            is_active=data.is_active,
            online_banking_enabled=data.online_banking_enabled,
            mobile_banking_enabled=data.mobile_banking_enabled,
            wire_transfer_enabled=data.wire_transfer_enabled,
            ach_enabled=data.ach_enabled,
            daily_transfer_limit=data.daily_transfer_limit,
            monthly_transfer_limit=data.monthly_transfer_limit,
            requires_dual_approval=data.requires_dual_approval,
            bank_api_enabled=data.bank_api_enabled,
            sync_frequency=data.sync_frequency,
            created_by=current_user,
            updated_by=current_user,
        )

        # Handle primary bank account logic
        if data.is_primary:
            self._ensure_single_primary_bank_account(gl_account_id, organization_id)

        # Save to database
        self.db.add(bank_account)
        self.db.flush()  # Flush to get the ID

        # Create audit history
        self._create_audit_history(
            bank_account.id,
            "created",
            None,
            self._bank_account_to_dict(bank_account),
            current_user,
            f"Bank account created for GL account {gl_account.account_code}",
        )

        self.db.commit()

        logger.info(
            f"Bank account {bank_account.id} created for GL account {gl_account_id} by {current_user}"
        )
        return bank_account

    def get_bank_account_by_id(
        self, bank_account_id: UUID, organization_id: UUID
    ) -> BankAccount:
        """Get bank account by ID"""

        bank_account = (
            self.db.query(BankAccount)
            .options(joinedload(BankAccount.gl_account))
            .filter(
                and_(
                    BankAccount.id == bank_account_id,
                    BankAccount.organization_id == organization_id,
                )
            )
            .first()
        )

        if not bank_account:
            raise BankAccountNotFoundException(
                f"Bank account {bank_account_id} not found"
            )

        return bank_account

    def get_bank_accounts_by_gl_account(
        self, gl_account_id: UUID, organization_id: UUID, include_inactive: bool = False
    ) -> list[BankAccount]:
        """Get all bank accounts for a GL account"""

        # Validate GL account exists
        self._get_gl_account_by_id(gl_account_id, organization_id)

        query = self.db.query(BankAccount).filter(
            and_(
                BankAccount.gl_account_id == gl_account_id,
                BankAccount.organization_id == organization_id,
            )
        )

        if not include_inactive:
            query = query.filter(BankAccount.is_active == True)

        return query.order_by(
            BankAccount.is_primary.desc(), BankAccount.created_at
        ).all()

    def list_bank_accounts(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        gl_account_id: UUID | None = None,
        bank_name: str | None = None,
        account_purpose: str | None = None,
        is_active: bool | None = None,
        is_primary: bool | None = None,
    ) -> BankAccountListResponse:
        """List bank accounts with pagination and filtering"""

        # Build query with filters
        query = (
            self.db.query(BankAccount)
            .options(joinedload(BankAccount.gl_account))
            .filter(BankAccount.organization_id == organization_id)
        )

        if gl_account_id:
            query = query.filter(BankAccount.gl_account_id == gl_account_id)

        if bank_name:
            query = query.filter(BankAccount.bank_name.ilike(f"%{bank_name}%"))

        if account_purpose:
            query = query.filter(BankAccount.account_purpose == account_purpose)

        if is_active is not None:
            query = query.filter(BankAccount.is_active == is_active)

        if is_primary is not None:
            query = query.filter(BankAccount.is_primary == is_primary)

        # Get total count
        total = query.count()

        # Apply pagination
        offset = (page - 1) * page_size
        bank_accounts = (
            query.order_by(BankAccount.is_primary.desc(), BankAccount.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        # Calculate pagination metadata
        total_pages = (total + page_size - 1) // page_size

        return BankAccountListResponse(
            items=[BankAccountResponse.model_validate(ba) for ba in bank_accounts],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1,
        )

    def update_bank_account(
        self,
        bank_account_id: UUID,
        data: BankAccountUpdate,
        organization_id: UUID,
        current_user: str,
    ) -> BankAccount:
        """Update an existing bank account"""

        # Get existing bank account
        bank_account = self.get_bank_account_by_id(bank_account_id, organization_id)
        old_values = self._bank_account_to_dict(bank_account)

        # Validate update rules
        self._validate_update_rules(data, bank_account)

        # Update fields
        update_fields = data.model_dump(exclude_unset=True)

        for field, value in update_fields.items():
            if hasattr(bank_account, field):
                setattr(bank_account, field, value)

        # Handle primary bank account logic
        if data.is_primary is not None and data.is_primary:
            self._ensure_single_primary_bank_account(
                bank_account.gl_account_id,
                organization_id,
                exclude_bank_account_id=bank_account_id,
            )

        # Update audit fields
        bank_account.updated_by = current_user
        bank_account.updated_at = datetime.now(UTC)

        # Create audit history
        new_values = self._bank_account_to_dict(bank_account)
        self._create_audit_history(
            bank_account.id,
            "updated",
            old_values,
            new_values,
            current_user,
            "Bank account updated",
        )

        self.db.commit()

        logger.info(f"Bank account {bank_account_id} updated by {current_user}")
        return bank_account

    def delete_bank_account(
        self, bank_account_id: UUID, organization_id: UUID, current_user: str
    ) -> None:
        """Delete (remove) a bank account"""

        # Get existing bank account
        bank_account = self.get_bank_account_by_id(bank_account_id, organization_id)
        
        # Check for reconciled transactions
        reconciled_count = (
            self.db.query(func.count(BankTransaction.id))
            .filter(
                and_(
                    BankTransaction.bank_account_id == bank_account_id,
                    BankTransaction.transaction_status == 'reconciled'
                )
            )
            .scalar()
        )
        
        if reconciled_count > 0:
            raise ReconciledTransactionDeletionException(
                f"Cannot delete bank account {bank_account_id}: "
                f"it has {reconciled_count} reconciled transaction(s). "
                f"Reconciled transactions must not be deleted to maintain data integrity."
            )
        
        old_values = self._bank_account_to_dict(bank_account)

        # Create audit history before deletion
        self._create_audit_history(
            bank_account.id,
            "deleted",
            old_values,
            None,
            current_user,
            "Bank account deleted",
        )

        # Delete the bank account (cascading will handle history)
        self.db.delete(bank_account)
        self.db.commit()

        logger.info(f"Bank account {bank_account_id} deleted by {current_user}")

    def activate_bank_account(
        self, bank_account_id: UUID, organization_id: UUID, current_user: str
    ) -> BankAccount:
        """Activate a bank account"""

        bank_account = self.get_bank_account_by_id(bank_account_id, organization_id)

        if bank_account.is_active:
            raise InvalidAccountStateException("Bank account is already active")

        old_values = self._bank_account_to_dict(bank_account)

        bank_account.is_active = True
        bank_account.updated_by = current_user
        bank_account.updated_at = datetime.now(UTC)

        new_values = self._bank_account_to_dict(bank_account)
        self._create_audit_history(
            bank_account.id,
            "activated",
            old_values,
            new_values,
            current_user,
            "Bank account activated",
        )

        self.db.commit()

        logger.info(f"Bank account {bank_account_id} activated by {current_user}")
        return bank_account

    def deactivate_bank_account(
        self, bank_account_id: UUID, organization_id: UUID, current_user: str
    ) -> BankAccount:
        """Deactivate a bank account"""

        bank_account = self.get_bank_account_by_id(bank_account_id, organization_id)

        if not bank_account.is_active:
            raise InvalidAccountStateException("Bank account is already inactive")

        old_values = self._bank_account_to_dict(bank_account)

        bank_account.is_active = False
        bank_account.updated_by = current_user
        bank_account.updated_at = datetime.now(UTC)

        new_values = self._bank_account_to_dict(bank_account)
        self._create_audit_history(
            bank_account.id,
            "deactivated",
            old_values,
            new_values,
            current_user,
            "Bank account deactivated",
        )

        self.db.commit()

        logger.info(f"Bank account {bank_account_id} deactivated by {current_user}")
        return bank_account

    def get_banking_overview(self, organization_id: UUID) -> BankingOverviewResponse:
        """Get banking overview for organization"""

        # Get summary statistics
        total_query = self.db.query(func.count(BankAccount.id)).filter(
            BankAccount.organization_id == organization_id
        )

        active_query = self.db.query(func.count(BankAccount.id)).filter(
            and_(
                BankAccount.organization_id == organization_id,
                BankAccount.is_active == True,
            )
        )

        primary_query = self.db.query(func.count(BankAccount.id)).filter(
            and_(
                BankAccount.organization_id == organization_id,
                BankAccount.is_primary == True,
            )
        )

        total_bank_accounts = total_query.scalar() or 0
        active_bank_accounts = active_query.scalar() or 0
        primary_bank_accounts = primary_query.scalar() or 0

        # Get accounts by purpose
        purpose_stats = (
            self.db.query(
                BankAccount.account_purpose, func.count(BankAccount.id).label("count")
            )
            .filter(BankAccount.organization_id == organization_id)
            .group_by(BankAccount.account_purpose)
            .all()
        )

        # Get accounts by type
        type_stats = (
            self.db.query(
                BankAccount.account_type, func.count(BankAccount.id).label("count")
            )
            .filter(BankAccount.organization_id == organization_id)
            .group_by(BankAccount.account_type)
            .all()
        )

        return BankingOverviewResponse(
            total_bank_accounts=total_bank_accounts,
            active_bank_accounts=active_bank_accounts,
            primary_bank_accounts=primary_bank_accounts,
            bank_accounts_by_purpose={
                purpose or "unspecified": count for purpose, count in purpose_stats
            },
            bank_accounts_by_type={
                account_type or "unspecified": count
                for account_type, count in type_stats
            },
        )

    def get_bank_account_history(
        self, 
        bank_account_id: UUID, 
        organization_id: UUID
    ) -> List[BankAccountHistory]:
        """Get complete audit history for a bank account"""
        
        # Validate bank account exists and belongs to organization
        self.get_bank_account_by_id(bank_account_id, organization_id)
        
        # Get history records ordered by most recent first
        history = (
            self.db.query(BankAccountHistory)
            .filter(BankAccountHistory.bank_account_id == bank_account_id)
            .order_by(BankAccountHistory.changed_at.desc())
            .all()
        )
        
        return history

    # Private helper methods

    def _get_gl_account_by_id(
        self, gl_account_id: UUID, organization_id: UUID
    ) -> Account:
        """Get GL account by ID and validate it belongs to organization"""

        gl_account = (
            self.db.query(Account)
            .filter(
                and_(
                    Account.id == gl_account_id,
                    Account.organization_id == organization_id,
                )
            )
            .first()
        )

        if not gl_account:
            raise ValidationError(
                f"GL account {gl_account_id} not found or does not belong to organization"
            )

        return gl_account

    def _validate_create_rules(
        self, data: BankAccountCreate, gl_account_id: UUID, organization_id: UUID
    ) -> None:
        """Validate business rules for creating a bank account"""
        
        # Get GL account to check its type
        gl_account = self._get_gl_account_by_id(gl_account_id, organization_id)
        
        # Validate GL account type - warn if not ASSET or LIABILITY
        if gl_account.account_type not in ['asset', 'liability']:
            logger.warning(
                f"Bank account being linked to GL account {gl_account.account_code} "
                f"of type {gl_account.account_type}. Bank accounts are typically linked to "
                f"ASSET (for regular bank accounts) or LIABILITY (for credit cards/overdrafts) accounts."
            )
        
        # Check for duplicate IBAN within organization
        if data.iban:
            existing_iban = (
                self.db.query(BankAccount)
                .filter(
                    and_(
                        BankAccount.organization_id == organization_id,
                        BankAccount.iban == data.iban,
                        BankAccount.is_active == True,
                    )
                )
                .first()
            )

            if existing_iban:
                raise DuplicateIbanException(
                    f"IBAN {data.iban} already exists for this organization"
                )

        # Validate primary bank account rules
        if data.is_primary:
            existing_primary = (
                self.db.query(BankAccount)
                .filter(
                    and_(
                        BankAccount.gl_account_id == gl_account_id,
                        BankAccount.is_primary == True,
                        BankAccount.is_active == True,
                    )
                )
                .first()
            )

            if existing_primary:
                raise ValidationError(
                    "GL account already has a primary bank account. "
                    "Please deactivate the existing primary bank account first."
                )

    def _validate_update_rules(
        self, data: BankAccountUpdate, existing_bank_account: BankAccount
    ) -> None:
        """Validate business rules for updating a bank account"""

        # Check for duplicate IBAN if IBAN is being updated
        if data.iban and data.iban != existing_bank_account.iban:
            existing_iban = (
                self.db.query(BankAccount)
                .filter(
                    and_(
                        BankAccount.organization_id
                        == existing_bank_account.organization_id,
                        BankAccount.iban == data.iban,
                        BankAccount.id != existing_bank_account.id,
                        BankAccount.is_active == True,
                    )
                )
                .first()
            )

            if existing_iban:
                raise DuplicateIbanException(
                    f"IBAN {data.iban} already exists for this organization"
                )

    def _ensure_single_primary_bank_account(
        self,
        gl_account_id: UUID,
        organization_id: UUID,
        exclude_bank_account_id: UUID | None = None,
    ) -> None:
        """Ensure only one primary bank account per GL account"""

        query = self.db.query(BankAccount).filter(
            and_(
                BankAccount.gl_account_id == gl_account_id,
                BankAccount.organization_id == organization_id,
                BankAccount.is_primary == True,
                BankAccount.is_active == True,
            )
        )

        if exclude_bank_account_id:
            query = query.filter(BankAccount.id != exclude_bank_account_id)

        existing_primary_accounts = query.all()

        # Set existing primary accounts to non-primary
        for account in existing_primary_accounts:
            account.is_primary = False

    def _bank_account_to_dict(self, bank_account: BankAccount) -> dict:
        """Convert bank account to dictionary for audit logging"""

        return {
            "bank_name": bank_account.bank_name,
            "account_holder_name": bank_account.account_holder_name,
            "account_number": "***MASKED***",  # Don't log sensitive data
            "iban": bank_account.mask_iban() if bank_account.iban else None,
            "swift_code": bank_account.swift_code,
            "account_type": bank_account.account_type,
            "account_purpose": bank_account.account_purpose,
            "is_primary": bank_account.is_primary,
            "is_active": bank_account.is_active,
        }

    def _create_audit_history(
        self,
        bank_account_id: UUID,
        action_type: str,
        old_values: dict | None,
        new_values: dict | None,
        changed_by: str,
        reason: str | None = None,
    ) -> None:
        """Create audit history record"""

        history = BankAccountHistory(
            bank_account_id=bank_account_id,
            action_type=action_type,
            old_values=old_values,
            new_values=new_values,
            changed_by=changed_by,
            reason=reason,
        )

        self.db.add(history)
