"""Default Account service for transaction type mappings"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    ChartOfAccountNotFoundException,
    ValidationError,
)
from app.models.base import AccountStatus, AccountType, DefaultAccountTransactionType
from app.models.default_account import DefaultAccount


class DefaultAccountService:
    """Service for default account configuration operations"""

    # Mapping of transaction types to appropriate account types
    TRANSACTION_TYPE_ACCOUNT_TYPES = {
        DefaultAccountTransactionType.INVENTORY_PURCHASE: [AccountType.ASSET, AccountType.EXPENSE],
        DefaultAccountTransactionType.INVENTORY_SALE: [AccountType.REVENUE],
        DefaultAccountTransactionType.ACCOUNTS_PAYABLE: [AccountType.LIABILITY],
        DefaultAccountTransactionType.ACCOUNTS_RECEIVABLE: [AccountType.ASSET],
        DefaultAccountTransactionType.SALES_REVENUE: [AccountType.REVENUE],
        DefaultAccountTransactionType.PURCHASE_EXPENSE: [AccountType.EXPENSE],
        DefaultAccountTransactionType.COST_OF_GOODS_SOLD: [AccountType.EXPENSE],
        DefaultAccountTransactionType.INVENTORY_ASSET: [AccountType.ASSET],
        DefaultAccountTransactionType.CASH: [AccountType.ASSET],
        DefaultAccountTransactionType.BANK: [AccountType.ASSET],
        DefaultAccountTransactionType.TAX_PAYABLE: [AccountType.LIABILITY],
        DefaultAccountTransactionType.TAX_RECEIVABLE: [AccountType.ASSET],
        DefaultAccountTransactionType.DISCOUNT_GIVEN: [AccountType.EXPENSE],
        DefaultAccountTransactionType.DISCOUNT_RECEIVED: [AccountType.REVENUE],
        DefaultAccountTransactionType.FREIGHT_EXPENSE: [AccountType.EXPENSE],
        DefaultAccountTransactionType.SHIPPING_CHARGES: [AccountType.EXPENSE],
        DefaultAccountTransactionType.SALES_INVOICE: [AccountType.ASSET, AccountType.REVENUE],
        DefaultAccountTransactionType.PURCHASE_INVOICE: [AccountType.LIABILITY, AccountType.EXPENSE],
        DefaultAccountTransactionType.PAYMENT: [AccountType.ASSET],
    }

    def __init__(self, db: Session):
        """
        Initialize default account service.

        Args:
            db: Database session
        """
        self.db = db

    def set_default_account(
        self,
        transaction_type: str | DefaultAccountTransactionType,
        account_id: UUID,
        organization_id: UUID,
        scenario: str | None = None,
    ) -> DefaultAccount:
        """
        Set or update a default account for a transaction type.

        Args:
            transaction_type: Type of transaction (enum or string for backward compatibility)
            account_id: UUID of the account to set as default
            organization_id: Organization UUID
            scenario: Optional scenario for multiple defaults per type (e.g., "domestic", "international")

        Returns:
            DefaultAccount object

        Raises:
            ValidationError: If validation fails
            ChartOfAccountNotFoundException: If account not found
        """
        # Convert enum to string value if needed
        transaction_type_value = (
            transaction_type.value 
            if isinstance(transaction_type, DefaultAccountTransactionType) 
            else transaction_type
        )
        
        # Validate transaction type
        if not transaction_type_value or not transaction_type_value.strip():
            raise ValidationError("Transaction type is required and cannot be empty")

        # Validate account exists and is active
        from app.repositories.chart_of_account_repository import AccountRepository

        account_repo = AccountRepository(self.db)
        account = account_repo.get_by_id(account_id, organization_id)

        if not account:
            raise ChartOfAccountNotFoundException(
                f"Account with ID {account_id} not found"
            )

        # Validate account is active
        if account.status != AccountStatus.ACTIVE:
            raise ValidationError(
                f"Cannot set inactive account '{account.account_code}' as default "
                f"(status: {account.status.value})"
            )

        # Validate account type is appropriate for transaction type
        # Try to match as enum first for validation
        transaction_type_enum = None
        try:
            transaction_type_enum = DefaultAccountTransactionType(transaction_type_value)
        except ValueError:
            # Not a valid enum value, skip validation
            pass
            
        if transaction_type_enum and transaction_type_enum in self.TRANSACTION_TYPE_ACCOUNT_TYPES:
            allowed_types = self.TRANSACTION_TYPE_ACCOUNT_TYPES[transaction_type_enum]
            if account.account_type not in allowed_types:
                allowed_types_str = ", ".join([t.value for t in allowed_types])
                raise ValidationError(
                    f"Account type '{account.account_type.value}' is not appropriate for "
                    f"transaction type '{transaction_type_value}'. "
                    f"Allowed types: {allowed_types_str}"
                )

        # Check if default already exists for this transaction type and scenario
        existing = (
            self.db.query(DefaultAccount)
            .filter(
                DefaultAccount.organization_id == organization_id,
                DefaultAccount.transaction_type == transaction_type_value,
                DefaultAccount.scenario == scenario,
            )
            .first()
        )

        if existing:
            # Update existing default
            existing.account_id = account_id
            self.db.commit()
            self.db.refresh(existing)
            return existing

        # Create new default
        default_account = DefaultAccount(
            transaction_type=transaction_type_value,
            scenario=scenario,
            account_id=account_id,
            organization_id=organization_id,
        )
        self.db.add(default_account)
        self.db.commit()
        self.db.refresh(default_account)

        return default_account

    def get_default_account(
        self,
        transaction_type: str,
        organization_id: UUID,
        scenario: str | None = None,
    ) -> DefaultAccount:
        """
        Get the default account for a transaction type and scenario.

        Args:
            transaction_type: Type of transaction
            organization_id: Organization UUID
            scenario: Optional scenario for multiple defaults per type

        Returns:
            DefaultAccount object

        Raises:
            ValidationError: If no default account is configured
        """
        default = (
            self.db.query(DefaultAccount)
            .filter(
                DefaultAccount.organization_id == organization_id,
                DefaultAccount.transaction_type == transaction_type,
                DefaultAccount.scenario == scenario,
            )
            .first()
        )

        if not default:
            scenario_msg = f" and scenario '{scenario}'" if scenario else ""
            raise ValidationError(
                f"No default account configured for transaction type '{transaction_type}'{scenario_msg}"
            )

        return default

    def list_default_accounts(
        self,
        organization_id: UUID,
        transaction_type: str | None = None,
    ) -> list[DefaultAccount]:
        """
        List all default accounts for an organization.

        Args:
            organization_id: Organization UUID
            transaction_type: Optional filter by transaction type

        Returns:
            List of DefaultAccount objects
        """
        query = self.db.query(DefaultAccount).filter(
            DefaultAccount.organization_id == organization_id
        )

        if transaction_type:
            query = query.filter(DefaultAccount.transaction_type == transaction_type)

        return query.order_by(
            DefaultAccount.transaction_type,
            DefaultAccount.scenario,
        ).all()

    def delete_default_account(
        self,
        transaction_type: str,
        organization_id: UUID,
        scenario: str | None = None,
    ) -> None:
        """
        Delete a default account configuration.

        Args:
            transaction_type: Type of transaction
            organization_id: Organization UUID
            scenario: Optional scenario

        Raises:
            ValidationError: If no default account is configured
        """
        default = (
            self.db.query(DefaultAccount)
            .filter(
                DefaultAccount.organization_id == organization_id,
                DefaultAccount.transaction_type == transaction_type,
                DefaultAccount.scenario == scenario,
            )
            .first()
        )

        if not default:
            scenario_msg = f" and scenario '{scenario}'" if scenario else ""
            raise ValidationError(
                f"No default account configured for transaction type '{transaction_type}'{scenario_msg}"
            )

        self.db.delete(default)
        self.db.commit()
