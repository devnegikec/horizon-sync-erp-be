"""
Bank Account Manager Service

Manages bank account lifecycle with encryption, validation, and audit trail.
Integrates with EncryptionService and CountryValidator.

Requirements: 1.1-1.8, 2.1-2.12, 18.1-18.10
"""

import logging
from datetime import UTC, datetime
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.bank_account import BankAccount, BankAccountHistory
from app.models.chart_of_account import Account
from app.schemas.bank_account import BankAccountCreate, BankAccountUpdate
from app.services.country_validator import get_country_validator
from app.services.encryption_service import get_encryption_service

logger = logging.getLogger(__name__)


class BankAccountManager:
    """
    Manager for bank account lifecycle operations.
    
    Provides high-level business logic for creating, updating, and managing
    bank accounts with encryption, country-specific validation, and audit trails.
    """

    def __init__(self, db: Session):
        """
        Initialize the bank account manager.
        
        Args:
            db: SQLAlchemy database session
        """
        self.db = db
        self.encryption_service = get_encryption_service()
        self.country_validator = get_country_validator()

    def create_bank_account(
        self,
        organization_id: UUID,
        gl_account_id: UUID,
        bank_details: BankAccountCreate,
        created_by: str,
        country_code: str,
        currency: str,
    ) -> BankAccount:
        """
        Create a new bank account with encryption and validation.
        
        Args:
            organization_id: Organization UUID
            gl_account_id: GL account UUID to link to
            bank_details: Bank account details
            created_by: User identifier creating the account
            country_code: ISO 3166-1 alpha-2 country code
            currency: ISO 4217 currency code
            
        Returns:
            Created BankAccount instance
            
        Raises:
            ValidationError: If validation fails
            
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1-2.12
        """
        # Validate GL account exists and belongs to organization
        gl_account = self._get_gl_account(gl_account_id, organization_id)
        
        # Validate country-specific banking information
        banking_info = {
            "routing_number": bank_details.routing_number,
            "account_number": bank_details.account_number,
            "iban": bank_details.iban,
            "swift_code": bank_details.swift_code,
            "sort_code": bank_details.sort_code,
            "bsb_number": bank_details.bsb_number,
            "ifsc_code": getattr(bank_details, "ifsc_code", None),
        }
        
        validation_result = self.country_validator.validate_banking_info(
            country_code, banking_info
        )
        
        if not validation_result.is_valid:
            raise ValidationError(
                f"Banking information validation failed: {', '.join(validation_result.errors)}"
            )
        
        # Encrypt sensitive fields before storage
        encrypted_account_number = self.encryption_service.encrypt_field(
            bank_details.account_number
        )
        encrypted_iban = (
            self.encryption_service.encrypt_field(bank_details.iban)
            if bank_details.iban
            else None
        )
        encrypted_routing_number = (
            self.encryption_service.encrypt_field(bank_details.routing_number)
            if bank_details.routing_number
            else None
        )
        encrypted_swift_code = (
            self.encryption_service.encrypt_field(bank_details.swift_code)
            if bank_details.swift_code
            else None
        )
        encrypted_sort_code = (
            self.encryption_service.encrypt_field(bank_details.sort_code)
            if bank_details.sort_code
            else None
        )
        encrypted_bsb_number = (
            self.encryption_service.encrypt_field(bank_details.bsb_number)
            if bank_details.bsb_number
            else None
        )
        encrypted_ifsc_code = (
            self.encryption_service.encrypt_field(
                getattr(bank_details, "ifsc_code", None)
            )
            if getattr(bank_details, "ifsc_code", None)
            else None
        )
        
        # Handle primary bank account logic
        if bank_details.is_primary:
            self._ensure_single_primary(gl_account_id, organization_id)
        
        # Create bank account with encrypted fields
        bank_account = BankAccount(
            organization_id=organization_id,
            gl_account_id=gl_account_id,
            bank_name=bank_details.bank_name,
            account_holder_name=bank_details.account_holder_name,
            account_number=encrypted_account_number,
            iban=encrypted_iban,
            swift_code=encrypted_swift_code,
            routing_number=encrypted_routing_number,
            sort_code=encrypted_sort_code,
            bsb_number=encrypted_bsb_number,
            ifsc_code=encrypted_ifsc_code,
            branch_name=bank_details.branch_name,
            branch_code=bank_details.branch_code,
            country_code=country_code,
            currency=currency,
            account_type=bank_details.account_type,
            account_purpose=bank_details.account_purpose,
            is_primary=bank_details.is_primary,
            is_active=bank_details.is_active,
            online_banking_enabled=bank_details.online_banking_enabled,
            mobile_banking_enabled=bank_details.mobile_banking_enabled,
            wire_transfer_enabled=bank_details.wire_transfer_enabled,
            ach_enabled=bank_details.ach_enabled,
            daily_transfer_limit=bank_details.daily_transfer_limit,
            monthly_transfer_limit=bank_details.monthly_transfer_limit,
            requires_dual_approval=bank_details.requires_dual_approval,
            bank_api_enabled=bank_details.bank_api_enabled,
            sync_frequency=bank_details.sync_frequency,
            created_by=created_by,
            updated_by=created_by,
        )
        
        self.db.add(bank_account)
        self.db.flush()
        
        # Create audit trail
        self._create_history_record(
            bank_account_id=bank_account.id,
            action_type="created",
            old_values=None,
            new_values=self._serialize_for_audit(bank_account),
            changed_by=created_by,
            reason=f"Bank account created for GL account {gl_account.account_code}",
        )
        
        self.db.commit()
        
        logger.info(
            f"Bank account {bank_account.id} created for organization {organization_id} by {created_by}"
        )
        
        return bank_account

    def create_default_bank_account(
        self,
        organization_id: UUID,
        organization_currency: str,
        created_by: str,
        skip_on_error: bool = True,
    ) -> Optional[BankAccount]:
        """
        Create a default bank account for a new organization.
        
        Args:
            organization_id: Organization UUID
            organization_currency: Organization's base currency
            created_by: User identifier creating the account
            skip_on_error: If True, log error and return None on failure; if False, raise exception
            
        Returns:
            Created BankAccount instance or None if skip_on_error=True and creation fails
            
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8
        """
        try:
            # Find or create a default GL account of type "Bank"
            gl_account = self._get_or_create_default_gl_account(
                organization_id, organization_currency, created_by
            )
            
            # Create minimal bank account details
            bank_details = BankAccountCreate(
                bank_name="Default Bank",
                account_holder_name="Organization Default Account",
                account_number="0000000000",  # Placeholder
                is_primary=True,
                is_active=True,
            )
            
            # Use a generic country code (US as default)
            # In production, this should come from organization settings
            country_code = "US"
            
            bank_account = self.create_bank_account(
                organization_id=organization_id,
                gl_account_id=gl_account.id,
                bank_details=bank_details,
                created_by=created_by,
                country_code=country_code,
                currency=organization_currency,
            )
            
            logger.info(
                f"Default bank account {bank_account.id} created for organization {organization_id}"
            )
            
            return bank_account
            
        except Exception as e:
            logger.error(
                f"Failed to create default bank account for organization {organization_id}: {str(e)}"
            )
            
            if skip_on_error:
                return None
            else:
                raise

    def update_bank_account(
        self,
        bank_account_id: UUID,
        updates: BankAccountUpdate,
        updated_by: str,
        organization_id: UUID,
    ) -> BankAccount:
        """
        Update an existing bank account with history tracking.
        
        Args:
            bank_account_id: Bank account UUID
            updates: Update data
            updated_by: User identifier performing the update
            organization_id: Organization UUID for validation
            
        Returns:
            Updated BankAccount instance
            
        Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 18.1, 18.2, 18.5, 18.6, 18.7, 18.8
        """
        # Get existing bank account
        bank_account = self._get_bank_account(bank_account_id, organization_id)
        
        # Store old values for audit
        old_values = self._serialize_for_audit(bank_account)
        
        # Update fields
        update_data = updates.model_dump(exclude_unset=True)
        
        # Handle sensitive field encryption
        if "account_number" in update_data and update_data["account_number"]:
            update_data["account_number"] = self.encryption_service.encrypt_field(
                update_data["account_number"]
            )
        
        if "iban" in update_data and update_data["iban"]:
            update_data["iban"] = self.encryption_service.encrypt_field(
                update_data["iban"]
            )
        
        if "routing_number" in update_data and update_data["routing_number"]:
            update_data["routing_number"] = self.encryption_service.encrypt_field(
                update_data["routing_number"]
            )
        
        if "swift_code" in update_data and update_data["swift_code"]:
            update_data["swift_code"] = self.encryption_service.encrypt_field(
                update_data["swift_code"]
            )
        
        if "sort_code" in update_data and update_data["sort_code"]:
            update_data["sort_code"] = self.encryption_service.encrypt_field(
                update_data["sort_code"]
            )
        
        if "bsb_number" in update_data and update_data["bsb_number"]:
            update_data["bsb_number"] = self.encryption_service.encrypt_field(
                update_data["bsb_number"]
            )
        
        # Handle primary bank account logic
        if updates.is_primary is not None and updates.is_primary:
            self._ensure_single_primary(
                bank_account.gl_account_id,
                organization_id,
                exclude_id=bank_account_id,
            )
        
        # Apply updates
        for field, value in update_data.items():
            if hasattr(bank_account, field):
                setattr(bank_account, field, value)
        
        # Update audit fields
        bank_account.updated_by = updated_by
        bank_account.updated_at = datetime.now(UTC)
        
        # Store new values for audit
        new_values = self._serialize_for_audit(bank_account)
        
        # Create audit trail
        self._create_history_record(
            bank_account_id=bank_account.id,
            action_type="updated",
            old_values=old_values,
            new_values=new_values,
            changed_by=updated_by,
            reason="Bank account updated",
        )
        
        self.db.commit()
        
        logger.info(
            f"Bank account {bank_account_id} updated by {updated_by}"
        )
        
        return bank_account

    def deactivate_bank_account(
        self,
        bank_account_id: UUID,
        organization_id: UUID,
        deactivated_by: str,
        reason: Optional[str] = None,
    ) -> BankAccount:
        """
        Deactivate a bank account.
        
        Args:
            bank_account_id: Bank account UUID
            organization_id: Organization UUID for validation
            deactivated_by: User identifier performing the deactivation
            reason: Optional reason for deactivation
            
        Returns:
            Deactivated BankAccount instance
            
        Requirements: 1.1, 1.2, 1.3, 1.4, 18.1, 18.3, 18.5, 18.6, 18.7, 18.8
        """
        # Get existing bank account
        bank_account = self._get_bank_account(bank_account_id, organization_id)
        
        # Store old values for audit
        old_values = self._serialize_for_audit(bank_account)
        
        # Deactivate
        bank_account.is_active = False
        bank_account.updated_by = deactivated_by
        bank_account.updated_at = datetime.now(UTC)
        
        # Store new values for audit
        new_values = self._serialize_for_audit(bank_account)
        
        # Create audit trail
        self._create_history_record(
            bank_account_id=bank_account.id,
            action_type="deactivated",
            old_values=old_values,
            new_values=new_values,
            changed_by=deactivated_by,
            reason=reason or "Bank account deactivated",
        )
        
        self.db.commit()
        
        logger.info(
            f"Bank account {bank_account_id} deactivated by {deactivated_by}"
        )
        
        return bank_account

    def reactivate_bank_account(
        self,
        bank_account_id: UUID,
        organization_id: UUID,
        reactivated_by: str,
        reason: Optional[str] = None,
    ) -> BankAccount:
        """
        Reactivate a bank account.
        
        Args:
            bank_account_id: Bank account UUID
            organization_id: Organization UUID for validation
            reactivated_by: User identifier performing the reactivation
            reason: Optional reason for reactivation
            
        Returns:
            Reactivated BankAccount instance
            
        Requirements: 18.1, 18.4, 18.5, 18.6, 18.7, 18.8
        """
        # Get existing bank account
        bank_account = self._get_bank_account(bank_account_id, organization_id)
        
        # Store old values for audit
        old_values = self._serialize_for_audit(bank_account)
        
        # Reactivate
        bank_account.is_active = True
        bank_account.updated_by = reactivated_by
        bank_account.updated_at = datetime.now(UTC)
        
        # Store new values for audit
        new_values = self._serialize_for_audit(bank_account)
        
        # Create audit trail
        self._create_history_record(
            bank_account_id=bank_account.id,
            action_type="reactivated",
            old_values=old_values,
            new_values=new_values,
            changed_by=reactivated_by,
            reason=reason or "Bank account reactivated",
        )
        
        self.db.commit()
        
        logger.info(
            f"Bank account {bank_account_id} reactivated by {reactivated_by}"
        )
        
        return bank_account

    def get_bank_account_history(
        self, bank_account_id: UUID, organization_id: UUID
    ) -> List[BankAccountHistory]:
        """
        Get complete history of a bank account.
        
        Args:
            bank_account_id: Bank account UUID
            organization_id: Organization UUID for validation
            
        Returns:
            List of BankAccountHistory records ordered by changed_at descending
            
        Requirements: 18.9
        """
        # Validate bank account exists and belongs to organization
        self._get_bank_account(bank_account_id, organization_id)
        
        # Get history records
        history = (
            self.db.query(BankAccountHistory)
            .filter(BankAccountHistory.bank_account_id == bank_account_id)
            .order_by(BankAccountHistory.changed_at.desc())
            .all()
        )
        
        return history

    # Private helper methods

    def _get_gl_account(self, gl_account_id: UUID, organization_id: UUID) -> Account:
        """Get and validate GL account."""
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

    def _get_bank_account(
        self, bank_account_id: UUID, organization_id: UUID
    ) -> BankAccount:
        """Get and validate bank account."""
        bank_account = (
            self.db.query(BankAccount)
            .filter(
                and_(
                    BankAccount.id == bank_account_id,
                    BankAccount.organization_id == organization_id,
                )
            )
            .first()
        )
        
        if not bank_account:
            raise ValidationError(
                f"Bank account {bank_account_id} not found or does not belong to organization"
            )
        
        return bank_account

    def _get_or_create_default_gl_account(
        self, organization_id: UUID, currency: str, created_by: str
    ) -> Account:
        """Get or create a default GL account of type Bank."""
        # Try to find existing default bank account
        gl_account = (
            self.db.query(Account)
            .filter(
                and_(
                    Account.organization_id == organization_id,
                    Account.account_type == "Bank",
                    Account.account_code == "1000",  # Standard bank account code
                )
            )
            .first()
        )
        
        if gl_account:
            return gl_account
        
        # Create new default bank GL account
        gl_account = Account(
            organization_id=organization_id,
            account_code="1000",
            account_name="Default Bank Account",
            account_type="Bank",
            currency=currency,
            is_active=True,
            created_by=created_by,
            updated_by=created_by,
        )
        
        self.db.add(gl_account)
        self.db.flush()
        
        return gl_account

    def _ensure_single_primary(
        self,
        gl_account_id: UUID,
        organization_id: UUID,
        exclude_id: Optional[UUID] = None,
    ) -> None:
        """Ensure only one primary bank account per GL account."""
        query = self.db.query(BankAccount).filter(
            and_(
                BankAccount.gl_account_id == gl_account_id,
                BankAccount.organization_id == organization_id,
                BankAccount.is_primary == True,
                BankAccount.is_active == True,
            )
        )
        
        if exclude_id:
            query = query.filter(BankAccount.id != exclude_id)
        
        existing_primary = query.all()
        
        # Set existing primary accounts to non-primary
        for account in existing_primary:
            account.is_primary = False

    def _serialize_for_audit(self, bank_account: BankAccount) -> dict:
        """Serialize bank account for audit trail (with masked sensitive data)."""
        return {
            "bank_name": bank_account.bank_name,
            "account_holder_name": bank_account.account_holder_name,
            "account_number": bank_account.mask_account_number(),
            "iban": bank_account.mask_iban(),
            "country_code": bank_account.country_code,
            "currency": bank_account.currency,
            "account_type": bank_account.account_type,
            "account_purpose": bank_account.account_purpose,
            "is_primary": bank_account.is_primary,
            "is_active": bank_account.is_active,
        }

    def _create_history_record(
        self,
        bank_account_id: UUID,
        action_type: str,
        old_values: Optional[dict],
        new_values: Optional[dict],
        changed_by: str,
        reason: Optional[str] = None,
    ) -> None:
        """
        Create audit history record.
        
        Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8
        """
        history = BankAccountHistory(
            bank_account_id=bank_account_id,
            action_type=action_type,
            old_values=old_values,
            new_values=new_values,
            changed_by=changed_by,
            reason=reason,
        )
        
        self.db.add(history)
