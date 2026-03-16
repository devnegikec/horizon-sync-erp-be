"""Journal posting service for payment journal entries"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError, ResourceNotFoundException
from app.models.base import DefaultAccountTransactionType
from app.models.bank_account import BankAccount
from app.services.journal_entry_service import JournalEntryService
from app.services.default_account_service import DefaultAccountService
from app.services.currency_service import CurrencyService


class JournalPostingService:
    """Service for creating journal entries for confirmed payments"""

    def __init__(self, db: Session):
        """
        Initialize journal posting service.

        Args:
            db: Database session
        """
        self.db = db
        self.journal_entry_service = JournalEntryService(db)
        self.default_account_service = DefaultAccountService(db)
        self.currency_service = CurrencyService(db)

    def _get_payment_account_by_mode(
            self,
            payment_mode: str,
            organization_id: UUID,
            bank_account_id: UUID | None = None,
        ) -> UUID:
            """
            Get the appropriate payment account based on payment mode.

            Args:
                payment_mode: Payment mode (Cash, Check, Bank_Transfer)
                organization_id: Organization UUID
                bank_account_id: Optional bank account UUID for Bank_Transfer payments

            Returns:
                Account UUID for the payment mode

            Raises:
                ValidationError: If payment mode is invalid or account not configured
                ResourceNotFoundException: If bank_account_id provided but not found
            """
            # Handle Bank_Transfer with specific bank account
            if payment_mode == "Bank_Transfer" and bank_account_id is not None:
                # Query BankAccount model by bank_account_id
                bank_account = self.db.query(BankAccount).filter(
                    BankAccount.id == bank_account_id
                ).first()
                
                # Validate bank_account exists
                if not bank_account:
                    raise ResourceNotFoundException(
                        f"Bank account with ID '{bank_account_id}' not found"
                    )
                
                # Validate bank_account belongs to the same organization
                if bank_account.organization_id != organization_id:
                    raise ValidationError(
                        f"Bank account '{bank_account_id}' does not belong to organization '{organization_id}'"
                    )
                
                # Validate bank_account is active
                if not bank_account.is_active:
                    raise ValidationError(
                        f"Bank account '{bank_account.bank_name}' (ID: {bank_account_id}) is not active"
                    )
                
                # Return the specific bank account's GL account ID
                return bank_account.gl_account_id
            
            # Map payment modes to transaction types for default accounts
            payment_mode_mapping = {
                "Cash": DefaultAccountTransactionType.CASH.value,
                "Check": DefaultAccountTransactionType.CHECKS_RECEIVED.value,
                "Bank_Transfer": DefaultAccountTransactionType.BANK.value,
                "Demand_Draft": DefaultAccountTransactionType.DEMAND_DRAFT.value,
            }

            transaction_type = payment_mode_mapping.get(payment_mode)
            if not transaction_type:
                raise ValidationError(
                    f"Invalid payment mode '{payment_mode}'. "
                    "Must be one of: Cash, Check, Bank_Transfer, Demand_Draft"
                )

            # Get default account for this transaction type
            # (Bank_Transfer without bank_account_id falls back to generic "bank" account)
            try:
                default_account = self.default_account_service.get_default_account(
                    transaction_type=transaction_type,
                    organization_id=organization_id,
                )
                return default_account.account_id
            except ValidationError as e:
                raise ValidationError(
                    f"Default account not configured for payment mode '{payment_mode}': {str(e)}"
                )


    def _validate_default_accounts_configured(
        self,
        payment_type: str,
        payment_mode: str,
        organization_id: UUID,
    ) -> None:
        """
        Validate that all required default accounts are configured.

        Args:
            payment_type: Payment type (Customer_Payment or Supplier_Payment)
            payment_mode: Payment mode (Cash, Check, Bank_Transfer)
            organization_id: Organization UUID

        Raises:
            ValidationError: If any required account is not configured
        """
        required_accounts = []

        # Determine required accounts based on payment type
        if payment_type == "Customer_Payment":
            # Customer payments require: payment account + accounts_receivable
            required_accounts.append((DefaultAccountTransactionType.ACCOUNTS_RECEIVABLE.value, "Accounts Receivable"))
        elif payment_type == "Supplier_Payment":
            # Supplier payments require: payment account + accounts_payable
            required_accounts.append((DefaultAccountTransactionType.ACCOUNTS_PAYABLE.value, "Accounts Payable"))
        else:
            raise ValidationError(
                f"Invalid payment type '{payment_type}'. "
                "Must be one of: Customer_Payment, Supplier_Payment"
            )

        # Add payment mode account to required accounts
        payment_mode_mapping = {
            "Cash": (DefaultAccountTransactionType.CASH.value, "Cash"),
            "Check": (DefaultAccountTransactionType.CHECKS_RECEIVED.value, "Checks Received"),
            "Bank_Transfer": (DefaultAccountTransactionType.BANK.value, "Bank"),
            "Demand_Draft": (DefaultAccountTransactionType.DEMAND_DRAFT.value, "Demand Draft"),
        }

        if payment_mode not in payment_mode_mapping:
            raise ValidationError(
                f"Invalid payment mode '{payment_mode}'. "
                "Must be one of: Cash, Check, Bank_Transfer, Demand_Draft"
            )

        payment_account_type, payment_account_name = payment_mode_mapping[payment_mode]
        required_accounts.append((payment_account_type, payment_account_name))

        # Validate each required account is configured
        missing_accounts = []
        for transaction_type, account_name in required_accounts:
            try:
                self.default_account_service.get_default_account(
                    transaction_type=transaction_type,
                    organization_id=organization_id,
                )
            except ValidationError:
                missing_accounts.append(account_name)

        if missing_accounts:
            raise ValidationError(
                f"Required default accounts not configured: {', '.join(missing_accounts)}. "
                "Please configure default accounts before confirming payments."
            )

    def _convert_to_base_currency(
        self,
        amount: Decimal,
        from_currency: str,
        organization_id: UUID,
    ) -> Decimal:
        """
        Convert payment amount to organization base currency.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            organization_id: Organization UUID

        Returns:
            Converted amount in base currency

        Raises:
            ValidationError: If currency conversion fails
        """
        # Get organization base currency
        base_currency = self.currency_service.get_base_currency()

        # If already in base currency, no conversion needed
        if from_currency == base_currency:
            return amount

        # Convert to base currency
        try:
            converted_amount = self.currency_service.convert(
                amount=amount,
                from_currency=from_currency,
                to_currency=base_currency,
            )
            return converted_amount
        except Exception as e:
            raise ValidationError(
                f"Failed to convert {amount} {from_currency} to base currency {base_currency}: {str(e)}"
            )

    def post_payment_journal_entry(
        self,
        payment_entry,
        organization_id: UUID,
        user_id: UUID,
    ):
        """
        Create journal entry for customer or supplier payment.

        For customer payments:
        - Debit: Bank/Cash/Checks_Received (based on payment_mode)
        - Credit: Accounts_Receivable

        For supplier payments:
        - Debit: Accounts_Payable
        - Credit: Bank/Cash/Checks_Received (based on payment_mode)

        Args:
            payment_entry: PaymentEntry object
            organization_id: Organization UUID
            user_id: User UUID performing the action

        Returns:
            Journal entry response dict

        Raises:
            ValidationError: If required accounts not configured or validation fails
        """
        # Validate required default accounts are configured
        self._validate_default_accounts_configured(
            payment_type=payment_entry.payment_type.value,
            payment_mode=payment_entry.payment_mode.value,
            organization_id=organization_id,
        )

        base_amount = self._convert_to_base_currency(
            amount=Decimal(str(payment_entry.amount)),
            from_currency=payment_entry.currency_code,
            organization_id=organization_id,
        )

        if payment_entry.payment_type.value == "Customer_Payment":
            # Customer payment: Debit payment account, Credit AR
            debit_account_id = self._get_payment_account_by_mode(
                payment_mode=payment_entry.payment_mode.value,
                organization_id=organization_id,
                bank_account_id=payment_entry.bank_account_id,
            )
            credit_account_id = self.default_account_service.get_default_account(
                transaction_type=DefaultAccountTransactionType.ACCOUNTS_RECEIVABLE.value,
                organization_id=organization_id,
            ).account_id
            remarks = (
                f"Payment received from customer - {payment_entry.payment_mode.value}"
            )
            lines = [
                {
                    "account_id": debit_account_id,
                    "debit": base_amount,
                    "credit": Decimal("0.00"),
                    "against_account_id": credit_account_id,
                    "reference_type": "PaymentEntry",
                    "reference_id": payment_entry.id,
                    "remarks": f"Payment received - {payment_entry.payment_mode.value}",
                    "sort_order": 1,
                },
                {
                    "account_id": credit_account_id,
                    "debit": Decimal("0.00"),
                    "credit": base_amount,
                    "against_account_id": debit_account_id,
                    "reference_type": "PaymentEntry",
                    "reference_id": payment_entry.id,
                    "remarks": "Accounts Receivable",
                    "sort_order": 2,
                },
            ]
        elif payment_entry.payment_type.value == "Supplier_Payment":
            # Supplier payment: Debit AP, Credit payment account
            debit_account_id = self.default_account_service.get_default_account(
                transaction_type=DefaultAccountTransactionType.ACCOUNTS_PAYABLE.value,
                organization_id=organization_id,
            ).account_id
            credit_account_id = self._get_payment_account_by_mode(
                payment_mode=payment_entry.payment_mode.value,
                organization_id=organization_id,
                bank_account_id=payment_entry.bank_account_id,
            )
            remarks = f"Supplier payment - {payment_entry.payment_mode.value}"
            lines = [
                {
                    "account_id": debit_account_id,
                    "debit": base_amount,
                    "credit": Decimal("0.00"),
                    "against_account_id": credit_account_id,
                    "reference_type": "PaymentEntry",
                    "reference_id": payment_entry.id,
                    "remarks": "Accounts Payable",
                    "sort_order": 1,
                },
                {
                    "account_id": credit_account_id,
                    "debit": Decimal("0.00"),
                    "credit": base_amount,
                    "against_account_id": debit_account_id,
                    "reference_type": "PaymentEntry",
                    "reference_id": payment_entry.id,
                    "remarks": f"Supplier payment - {payment_entry.payment_mode.value}",
                    "sort_order": 2,
                },
            ]
        else:
            raise ValidationError(
                f"Unsupported payment type: {payment_entry.payment_type.value}"
            )

        journal_entry_data = {
            "posting_date": payment_entry.payment_date,
            "voucher_type": "Payment Entry",
            "reference_type": "PaymentEntry",
            "reference_id": payment_entry.id,
            "total_debit": base_amount,
            "total_credit": base_amount,
            "remarks": remarks,
            "status": "posted",
            "lines": lines,
        }

        # Validate debits equal credits
        total_debit = sum(line["debit"] for line in journal_entry_data["lines"])
        total_credit = sum(line["credit"] for line in journal_entry_data["lines"])
        if total_debit != total_credit:
            raise ValidationError(
                f"Journal entry debits ({total_debit}) do not equal credits ({total_credit})"
            )

        # Create journal entry using journal_entry_service
        journal_entry = self.journal_entry_service.create(
            data=journal_entry_data,
            organization_id=organization_id,
            user_id=user_id,
        )

        return journal_entry

    def reverse_payment_journal_entry(
        self,
        payment_entry,
        organization_id: UUID,
        user_id: UUID,
    ):
        """
        Create reversing journal entry for cancelled payment.

        Retrieves the original journal entry and creates a reversing entry
        with opposite debits and credits.

        Args:
            payment_entry: PaymentEntry object
            organization_id: Organization UUID
            user_id: User UUID performing the action

        Returns:
            Reversing journal entry response dict

        Raises:
            ValidationError: If original journal entry not found
        """
        # Retrieve original journal entry for payment
        original_entry = self.journal_entry_service.get_by_reference(
            reference_type="PaymentEntry",
            reference_id=payment_entry.id,
            organization_id=organization_id,
        )

        if not original_entry:
            raise ValidationError(
                f"Original journal entry not found for payment {payment_entry.id}"
            )

        # Get the original journal entry with lines to access line details
        original_je = self.journal_entry_service.repo.get_by_reference(
            reference_type="PaymentEntry",
            reference_id=payment_entry.id,
            organization_id=organization_id,
            load_lines=True,
        )

        if not original_je or not original_je.lines:
            raise ValidationError(
                f"Original journal entry lines not found for payment {payment_entry.id}"
            )

        # Create reversing journal entry with swapped debits and credits
        reversing_lines = []
        for idx, line in enumerate(original_je.lines, start=1):
            reversing_lines.append(
                {
                    "account_id": line.account_id,
                    "debit": line.credit,  # Swap: original credit becomes debit
                    "credit": line.debit,  # Swap: original debit becomes credit
                    "against_account_id": line.against_account_id,
                    "reference_type": "PaymentEntry",
                    "reference_id": payment_entry.id,
                    "remarks": f"Reversal: {line.remarks}",
                    "sort_order": idx,
                }
            )

        # Create reversing journal entry data
        reversing_entry_data = {
            "posting_date": datetime.now(),
            "voucher_type": "Payment Entry Reversal",
            "reference_type": "PaymentEntry",
            "reference_id": payment_entry.id,
            "total_debit": original_entry["total_credit"],  # Swap totals
            "total_credit": original_entry["total_debit"],  # Swap totals
            "remarks": f"Reversal of payment entry - Cancellation reason: {payment_entry.cancellation_reason or 'Not specified'}",
            "status": "posted",
            "lines": reversing_lines,
        }

        # Validate debits equal credits
        total_debit = sum(line["debit"] for line in reversing_entry_data["lines"])
        total_credit = sum(line["credit"] for line in reversing_entry_data["lines"])

        if total_debit != total_credit:
            raise ValidationError(
                f"Reversing journal entry debits ({total_debit}) do not equal credits ({total_credit})"
            )

        # Create reversing journal entry using journal_entry_service
        reversing_journal_entry = self.journal_entry_service.create(
            data=reversing_entry_data,
            organization_id=organization_id,
            user_id=user_id,
        )

        return reversing_journal_entry
