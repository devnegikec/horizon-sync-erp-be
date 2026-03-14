"""Invoice journal posting service for creating journal entries on invoice confirmation"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.base import DefaultAccountTransactionType
from app.services.default_account_service import DefaultAccountService
from app.services.journal_entry_service import JournalEntryService
from app.services.currency_service import CurrencyService


class InvoiceJournalPostingService:
    """Service for creating journal entries when invoices are confirmed"""

    def __init__(self, db: Session):
        """
        Initialize invoice journal posting service.

        Args:
            db: Database session
        """
        self.db = db
        self.journal_entry_service = JournalEntryService(db)
        self.default_account_service = DefaultAccountService(db)
        self.currency_service = CurrencyService(db)

    def _validate_invoice_default_accounts(
        self, invoice_type: str, organization_id: UUID
    ) -> tuple[UUID, UUID]:
        """
        Validate that required default accounts are configured for invoice type.

        Args:
            invoice_type: Type of invoice ("sales" or "purchase")
            organization_id: Organization UUID

        Returns:
            Tuple of (debit_account_id, credit_account_id)

        Raises:
            ValidationError: If required default accounts are not configured
        """
        # Extract value if it's an enum
        invoice_type_value = invoice_type.value if hasattr(invoice_type, 'value') else invoice_type
        
        missing_accounts = []

        if invoice_type_value == "sales":
            # Sales invoice: Debit AR, Credit Revenue
            try:
                ar_account = self.default_account_service.get_default_account(
                    DefaultAccountTransactionType.ACCOUNTS_RECEIVABLE.value, organization_id
                )
                debit_account_id = ar_account.account_id
            except ValidationError:
                missing_accounts.append("accounts_receivable")
                debit_account_id = None

            try:
                revenue_account = self.default_account_service.get_default_account(
                    DefaultAccountTransactionType.SALES_REVENUE.value, organization_id
                )
                credit_account_id = revenue_account.account_id
            except ValidationError:
                missing_accounts.append("sales_revenue")
                credit_account_id = None

        elif invoice_type_value == "purchase":
            # Purchase invoice: Debit Expense, Credit AP
            try:
                expense_account = self.default_account_service.get_default_account(
                    DefaultAccountTransactionType.PURCHASE_EXPENSE.value, organization_id
                )
                debit_account_id = expense_account.account_id
            except ValidationError:
                missing_accounts.append("purchase_expense")
                debit_account_id = None

            try:
                ap_account = self.default_account_service.get_default_account(
                    DefaultAccountTransactionType.ACCOUNTS_PAYABLE.value, organization_id
                )
                credit_account_id = ap_account.account_id
            except ValidationError:
                missing_accounts.append("accounts_payable")
                credit_account_id = None

        else:
            raise ValidationError(f"Invalid invoice type: {invoice_type_value}")

        if missing_accounts:
            raise ValidationError(
                f"Required default accounts not configured: {', '.join(missing_accounts)}. "
                f"Please configure default accounts before confirming invoices."
            )

        return debit_account_id, credit_account_id

    def _convert_to_base_currency(
        self, amount: Decimal, from_currency: str, organization_id: UUID
    ) -> Decimal:
        """
        Convert amount to organization's base currency.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            organization_id: Organization UUID

        Returns:
            Converted amount in base currency

        Raises:
            ValidationError: If currency conversion fails
        """
        try:
            base_currency = self.currency_service.get_base_currency()

            # If already in base currency, return as-is
            if from_currency == base_currency:
                return amount

            # Convert to base currency
            converted_amount = self.currency_service.convert(
                amount, from_currency, base_currency
            )
            return converted_amount

        except Exception as e:
            raise ValidationError(
                f"Failed to convert {amount} {from_currency} to base currency: {str(e)}"
            )

    def post_invoice_journal_entry(
        self, invoice, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Create journal entry for invoice confirmation.

        Args:
            invoice: Invoice model instance
            organization_id: Organization UUID
            user_id: User ID creating the entry

        Returns:
            Created journal entry as dict

        Raises:
            ValidationError: If validation fails or default accounts not configured
        """
        try:
            # Validate invoice type
            invoice_type_value = invoice.invoice_type.value if hasattr(invoice.invoice_type, 'value') else invoice.invoice_type
            if invoice_type_value not in ["sales", "purchase"]:
                raise ValidationError(
                    f"Invalid invoice type: {invoice_type_value}. "
                    f"Must be 'sales' or 'purchase'"
                )

            # Validate grand total
            if invoice.grand_total <= 0:
                raise ValidationError("Invoice grand_total must be greater than zero")

            # Validate and get default accounts
            debit_account_id, credit_account_id = self._validate_invoice_default_accounts(
                invoice.invoice_type, organization_id
            )

            # Convert amount to base currency
            base_amount = self._convert_to_base_currency(
                invoice.grand_total, invoice.currency, organization_id
            )

            # Build journal entry data
            journal_entry_data = {
                "posting_date": invoice.submitted_at or datetime.now(),
                "status": "posted",
                "voucher_type": "Invoice Confirmation",
                "reference_type": "Invoice",
                "reference_id": invoice.id,
                "remarks": f"Invoice confirmation for {invoice.invoice_no}",
                "lines": [
                    {
                        "account_id": debit_account_id,
                        "debit": base_amount,
                        "credit": Decimal("0"),
                        "remarks": f"Invoice {invoice.invoice_no}",
                    },
                    {
                        "account_id": credit_account_id,
                        "debit": Decimal("0"),
                        "credit": base_amount,
                        "remarks": f"Invoice {invoice.invoice_no}",
                    },
                ],
            }

            # Validate debits equal credits
            total_debit = sum(line["debit"] for line in journal_entry_data["lines"])
            total_credit = sum(line["credit"] for line in journal_entry_data["lines"])
            if total_debit != total_credit:
                raise ValidationError(
                    f"Journal entry debits ({total_debit}) do not equal credits ({total_credit})"
                )

            # Create journal entry
            journal_entry = self.journal_entry_service.create(
                journal_entry_data, organization_id, user_id
            )

            return journal_entry

        except ValidationError:
            # Re-raise validation errors
            raise
        except Exception as e:
            # Log and re-raise other errors
            raise ValidationError(
                f"Failed to create journal entry for invoice {invoice.invoice_no}: {str(e)}"
            )

def _validate_invoice_default_accounts(
    self, invoice_type: str, organization_id: UUID
) -> tuple[UUID, UUID]:
    """
    Validate that required default accounts are configured for invoice type.

    Args:
        invoice_type: Type of invoice ("sales" or "purchase")
        organization_id: Organization UUID

    Returns:
        Tuple of (debit_account_id, credit_account_id)

    Raises:
        ValidationError: If required default accounts are not configured
    """
    # Extract value if it's an enum
    invoice_type_value = invoice_type.value if hasattr(invoice_type, 'value') else invoice_type
    
    missing_accounts = []

    if invoice_type_value == "sales":
        # Sales invoice: Debit AR, Credit Revenue
        try:
            ar_account = self.default_account_service.get_default_account(
                "accounts_receivable", organization_id
            )
            debit_account_id = ar_account.account_id
        except ValidationError:
            missing_accounts.append("accounts_receivable")
            debit_account_id = None

        try:
            revenue_account = self.default_account_service.get_default_account(
                "sales_revenue", organization_id
            )
            credit_account_id = revenue_account.account_id
        except ValidationError:
            missing_accounts.append("sales_revenue")
            credit_account_id = None

    elif invoice_type_value == "purchase":
        # Purchase invoice: Debit Expense, Credit AP
        try:
            expense_account = self.default_account_service.get_default_account(
                "purchase_expense", organization_id
            )
            debit_account_id = expense_account.account_id
        except ValidationError:
            missing_accounts.append("purchase_expense")
            debit_account_id = None

        try:
            ap_account = self.default_account_service.get_default_account(
                "accounts_payable", organization_id
            )
            credit_account_id = ap_account.account_id
        except ValidationError:
            missing_accounts.append("accounts_payable")
            credit_account_id = None

    else:
        raise ValidationError(f"Invalid invoice type: {invoice_type_value}")

    if missing_accounts:
        raise ValidationError(
            f"Required default accounts not configured: {', '.join(missing_accounts)}. "
            f"Please configure default accounts before confirming invoices."
        )

    return debit_account_id, credit_account_id

def _convert_to_base_currency(
    self, amount: Decimal, from_currency: str, organization_id: UUID
) -> Decimal:
    """
    Convert amount to organization's base currency.

    Args:
        amount: Amount to convert
        from_currency: Source currency code
        organization_id: Organization UUID

    Returns:
        Converted amount in base currency

    Raises:
        ValidationError: If currency conversion fails
    """
    try:
        base_currency = self.currency_service.get_base_currency()

        # If already in base currency, return as-is
        if from_currency == base_currency:
            return amount

        # Convert to base currency
        converted_amount = self.currency_service.convert(
            amount, from_currency, base_currency
        )
        return converted_amount

    except Exception as e:
        raise ValidationError(
            f"Failed to convert {amount} {from_currency} to base currency: {str(e)}"
        )

def post_invoice_journal_entry(
    self, invoice, organization_id: UUID, user_id: UUID
) -> dict:
    """
    Create journal entry for invoice confirmation.

    Args:
        invoice: Invoice model instance
        organization_id: Organization UUID
        user_id: User ID creating the entry

    Returns:
        Created journal entry as dict

    Raises:
        ValidationError: If validation fails or default accounts not configured
    """
    try:
        # Validate invoice type
        if invoice.invoice_type not in ["Sales", "Purchase"]:
            raise ValidationError(
                f"Invalid invoice type: {invoice.invoice_type}. "
                f"Must be 'Sales' or 'Purchase'"
            )

        # Validate grand total
        if invoice.grand_total <= 0:
            raise ValidationError("Invoice grand_total must be greater than zero")

        # Validate and get default accounts
        debit_account_id, credit_account_id = self._validate_invoice_default_accounts(
            invoice.invoice_type, organization_id
        )

        # Convert amount to base currency
        base_amount = self._convert_to_base_currency(
            invoice.grand_total, invoice.currency, organization_id
        )

        # Build journal entry data
        journal_entry_data = {
            "posting_date": invoice.submitted_at or datetime.now(),
            "status": "posted",
            "voucher_type": "Invoice Confirmation",
            "reference_type": "Invoice",
            "reference_id": invoice.id,
            "remarks": f"Invoice confirmation for {invoice.invoice_no}",
            "lines": [
                {
                    "account_id": debit_account_id,
                    "debit": base_amount,
                    "credit": Decimal("0"),
                    "remarks": f"Invoice {invoice.invoice_no}",
                },
                {
                    "account_id": credit_account_id,
                    "debit": Decimal("0"),
                    "credit": base_amount,
                    "remarks": f"Invoice {invoice.invoice_no}",
                },
            ],
        }

        # Validate debits equal credits
        total_debit = sum(line["debit"] for line in journal_entry_data["lines"])
        total_credit = sum(line["credit"] for line in journal_entry_data["lines"])
        if total_debit != total_credit:
            raise ValidationError(
                f"Journal entry debits ({total_debit}) do not equal credits ({total_credit})"
            )

        # Create journal entry
        journal_entry = self.journal_entry_service.create(
            journal_entry_data, organization_id, user_id
        )

        return journal_entry

    except ValidationError:
        # Re-raise validation errors
        raise
    except Exception as e:
        # Log and re-raise other errors
        raise ValidationError(
            f"Failed to create journal entry for invoice {invoice.invoice_no}: {str(e)}"
        )

