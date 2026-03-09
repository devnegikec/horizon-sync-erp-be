"""Transaction Integration Service for applying taxes and charges to transactions"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.transaction_breakdown import (
    TransactionChargeBreakdown,
    TransactionTaxBreakdown,
)
from app.services.charge_calculation_engine import (
    ChargeBreakdownEntry,
    ChargeCalculationEngine,
    ChargeContext,
)
from app.services.tax_calculation_engine import (
    LineItem,
    TaxBreakdownEntry,
    TaxCalculationEngine,
    TaxContext,
)


@dataclass
class Transaction:
    """Generic transaction data structure"""

    id: UUID
    organization_id: UUID
    transaction_type: (
        str  # "Quotation", "Sales_Order", "Purchase_Order", "Invoice", etc.
    )
    customer_id: UUID | None = None
    supplier_id: UUID | None = None
    line_items: list[dict] = None
    net_total: Decimal = Decimal("0.00")
    total_tax: Decimal = Decimal("0.00")
    total_charges: Decimal = Decimal("0.00")
    grand_total: Decimal = Decimal("0.00")
    shipping_address: dict | None = None
    is_customer_tax_exempt: bool = False
    extra_data: dict | None = None

    def __post_init__(self):
        if self.line_items is None:
            self.line_items = []
        if self.extra_data is None:
            self.extra_data = {}


class TransactionIntegrationService:
    """Service for integrating tax and charge calculations into transaction workflows"""

    def __init__(self, db: Session):
        self.db = db
        self.tax_engine = TaxCalculationEngine(db)
        self.charge_engine = ChargeCalculationEngine(db)

    def apply_taxes_and_charges(
        self, transaction: Transaction, user_id: UUID
    ) -> Transaction:
        """
        Apply taxes and charges to a transaction.

        Args:
            transaction: Transaction object with line items
            user_id: ID of the user performing the operation

        Returns:
            Updated transaction with calculated taxes and charges
        """
        # Convert line items to LineItem dataclass
        line_items = self._convert_to_line_items(transaction.line_items)

        # Build tax context
        tax_context = TaxContext(
            organization_id=transaction.organization_id,
            transaction_type=self._get_transaction_category(
                transaction.transaction_type
            ),
            customer_id=transaction.customer_id,
            supplier_id=transaction.supplier_id,
            shipping_address=transaction.shipping_address,
            customer_location=transaction.shipping_address,
            supplier_location=None,
            is_customer_tax_exempt=transaction.is_customer_tax_exempt,
        )

        # Calculate taxes
        tax_result = self.tax_engine.calculate_taxes(line_items, tax_context)

        # Build charge context
        charge_context = ChargeContext(
            organization_id=transaction.organization_id,
            transaction_type=transaction.transaction_type,
            net_total=tax_result.net_total,
            customer_id=transaction.customer_id,
            shipping_address=transaction.shipping_address,
            customer_location=transaction.shipping_address,
        )

        # Calculate charges
        charge_result = self.charge_engine.calculate_charges(
            charge_context, tax_result.net_total, tax_result.total_tax
        )

        # Update transaction with calculated values
        transaction.net_total = tax_result.net_total
        transaction.total_tax = tax_result.total_tax
        transaction.total_charges = charge_result.total_charges
        transaction.grand_total = (
            tax_result.net_total + tax_result.total_tax + charge_result.total_charges
        )

        # Store breakdown data in extra_data for later persistence
        if transaction.extra_data is None:
            transaction.extra_data = {}

        transaction.extra_data["tax_breakdown"] = [
            self._tax_entry_to_dict(entry) for entry in tax_result.tax_breakdown
        ]
        transaction.extra_data["charge_breakdown"] = [
            self._charge_entry_to_dict(entry)
            for entry in charge_result.charge_breakdown
        ]

        return transaction

    def recalculate_totals(self, transaction: Transaction) -> Transaction:
        """
        Recalculate totals for a transaction (e.g., when line items change).

        Args:
            transaction: Transaction object with updated line items

        Returns:
            Transaction with recalculated totals
        """
        # Reuse apply_taxes_and_charges logic
        # Pass a dummy user_id since we're just recalculating
        return self.apply_taxes_and_charges(transaction, transaction.organization_id)

    def persist_tax_breakdown(
        self,
        transaction_id: UUID,
        transaction_type: str,
        tax_breakdown: list[TaxBreakdownEntry],
        organization_id: UUID,
    ) -> None:
        """
        Persist tax breakdown entries to the database.

        Args:
            transaction_id: ID of the transaction
            transaction_type: Type of transaction (e.g., "Quotation", "Sales_Order")
            tax_breakdown: List of tax breakdown entries
            organization_id: Organization ID for multi-tenancy
        """
        # Delete existing tax breakdown entries for this transaction
        self.db.query(TransactionTaxBreakdown).filter(
            TransactionTaxBreakdown.transaction_id == transaction_id,
            TransactionTaxBreakdown.transaction_type == transaction_type,
        ).delete()

        # Create new tax breakdown entries
        for entry in tax_breakdown:
            breakdown = TransactionTaxBreakdown(
                organization_id=organization_id,
                transaction_type=transaction_type,
                transaction_id=transaction_id,
                tax_template_id=entry.tax_template_id,
                tax_rule_id=entry.tax_rule_id,
                tax_type=entry.tax_type,
                tax_rate=entry.tax_rate,
                taxable_amount=entry.taxable_amount,
                tax_amount=entry.tax_amount,
                is_compound=entry.is_compound,
                sequence=entry.sequence,
                account_head_id=entry.account_head_id,
            )
            self.db.add(breakdown)

        self.db.flush()

    def persist_charge_breakdown(
        self,
        transaction_id: UUID,
        transaction_type: str,
        charge_breakdown: list[ChargeBreakdownEntry],
        organization_id: UUID,
    ) -> None:
        """
        Persist charge breakdown entries to the database.

        Args:
            transaction_id: ID of the transaction
            transaction_type: Type of transaction (e.g., "Quotation", "Sales_Order")
            charge_breakdown: List of charge breakdown entries
            organization_id: Organization ID for multi-tenancy
        """
        # Delete existing charge breakdown entries for this transaction
        self.db.query(TransactionChargeBreakdown).filter(
            TransactionChargeBreakdown.transaction_id == transaction_id,
            TransactionChargeBreakdown.transaction_type == transaction_type,
        ).delete()

        # Create new charge breakdown entries
        for entry in charge_breakdown:
            breakdown = TransactionChargeBreakdown(
                organization_id=organization_id,
                transaction_type=transaction_type,
                transaction_id=transaction_id,
                charge_template_id=entry.charge_template_id,
                charge_type=entry.charge_type,
                description=entry.description,
                calculation_method=entry.calculation_method,
                charge_amount=entry.charge_amount,
                account_head_id=entry.account_head_id,
                is_auto_calculated=entry.is_auto_calculated,
            )
            self.db.add(breakdown)

        self.db.flush()

    def copy_taxes_and_charges(
        self, source_transaction: Transaction, target_transaction: Transaction
    ) -> None:
        """
        Copy tax and charge breakdowns from source to target transaction.

        Args:
            source_transaction: Source transaction to copy from
            target_transaction: Target transaction to copy to
        """
        # Get tax breakdown from source
        source_tax_breakdown = (
            self.db.query(TransactionTaxBreakdown)
            .filter(
                TransactionTaxBreakdown.transaction_id == source_transaction.id,
                TransactionTaxBreakdown.transaction_type
                == source_transaction.transaction_type,
            )
            .all()
        )

        # Get charge breakdown from source
        source_charge_breakdown = (
            self.db.query(TransactionChargeBreakdown)
            .filter(
                TransactionChargeBreakdown.transaction_id == source_transaction.id,
                TransactionChargeBreakdown.transaction_type
                == source_transaction.transaction_type,
            )
            .all()
        )

        # Convert to dataclass entries
        tax_entries = [
            TaxBreakdownEntry(
                tax_template_id=entry.tax_template_id,
                tax_rule_id=entry.tax_rule_id,
                tax_type=entry.tax_type,
                tax_rate=entry.tax_rate,
                taxable_amount=entry.taxable_amount,
                tax_amount=entry.tax_amount,
                is_compound=entry.is_compound,
                sequence=entry.sequence,
                account_head_id=entry.account_head_id,
            )
            for entry in source_tax_breakdown
        ]

        charge_entries = [
            ChargeBreakdownEntry(
                charge_template_id=entry.charge_template_id,
                charge_type=entry.charge_type,
                description=entry.description,
                calculation_method=entry.calculation_method,
                charge_amount=entry.charge_amount,
                account_head_id=entry.account_head_id,
                is_auto_calculated=entry.is_auto_calculated,
            )
            for entry in source_charge_breakdown
        ]

        # Persist to target transaction
        self.persist_tax_breakdown(
            target_transaction.id,
            target_transaction.transaction_type,
            tax_entries,
            target_transaction.organization_id,
        )

        self.persist_charge_breakdown(
            target_transaction.id,
            target_transaction.transaction_type,
            charge_entries,
            target_transaction.organization_id,
        )

        # Update target transaction totals
        target_transaction.net_total = source_transaction.net_total
        target_transaction.total_tax = source_transaction.total_tax
        target_transaction.total_charges = source_transaction.total_charges
        target_transaction.grand_total = source_transaction.grand_total

    def _convert_to_line_items(self, line_items_data: list[dict]) -> list[LineItem]:
        """
        Convert line item dictionaries to LineItem dataclass instances.

        Args:
            line_items_data: List of line item dictionaries

        Returns:
            List of LineItem instances
        """
        line_items = []
        for item_data in line_items_data:
            line_item = LineItem(
                item_id=item_data["item_id"],
                qty=Decimal(str(item_data["qty"])),
                rate=Decimal(str(item_data["rate"])),
                amount=Decimal(str(item_data["amount"])),
                is_tax_exempt=item_data.get("is_tax_exempt", False),
                item_group_id=item_data.get("item_group_id"),
            )
            line_items.append(line_item)
        return line_items

    def _get_transaction_category(self, transaction_type: str) -> str:
        """
        Get transaction category (Sales or Purchase) from transaction type.

        Args:
            transaction_type: Transaction type (e.g., "Quotation", "Sales_Order")

        Returns:
            "Sales" or "Purchase"
        """
        sales_types = ["Quotation", "Sales_Order", "Invoice", "Delivery_Note"]
        purchase_types = ["Purchase_Order", "Purchase_Receipt", "Purchase_Invoice"]

        if transaction_type in sales_types:
            return "Sales"
        elif transaction_type in purchase_types:
            return "Purchase"
        else:
            # Default to Sales for unknown types
            return "Sales"

    def _tax_entry_to_dict(self, entry: TaxBreakdownEntry) -> dict[str, Any]:
        """Convert TaxBreakdownEntry to dictionary for storage"""
        return {
            "tax_template_id": str(entry.tax_template_id),
            "tax_rule_id": str(entry.tax_rule_id),
            "tax_type": entry.tax_type,
            "tax_rate": float(entry.tax_rate),
            "taxable_amount": float(entry.taxable_amount),
            "tax_amount": float(entry.tax_amount),
            "is_compound": entry.is_compound,
            "sequence": entry.sequence,
            "account_head_id": str(entry.account_head_id),
        }

    def _charge_entry_to_dict(self, entry: ChargeBreakdownEntry) -> dict[str, Any]:
        """Convert ChargeBreakdownEntry to dictionary for storage"""
        return {
            "charge_template_id": str(entry.charge_template_id)
            if entry.charge_template_id
            else None,
            "charge_type": entry.charge_type,
            "description": entry.description,
            "calculation_method": entry.calculation_method,
            "charge_amount": float(entry.charge_amount),
            "account_head_id": str(entry.account_head_id),
            "is_auto_calculated": entry.is_auto_calculated,
        }
