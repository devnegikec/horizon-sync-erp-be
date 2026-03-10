"""Transaction Engine service for calculating line items, taxes, and totals"""

from decimal import Decimal
from typing import Literal


class TransactionEngineInput:
    """Input data for Transaction Engine calculations"""

    def __init__(
        self,
        transaction_type: Literal["PURCHASE", "SALES"],
        line_items: list[dict],
        tax_rate: Decimal | None = None,
        discount_amount: Decimal | None = None,
    ):
        self.transaction_type = transaction_type
        self.line_items = line_items
        self.tax_rate = tax_rate or Decimal("0")
        self.discount_amount = discount_amount or Decimal("0")


class TransactionEngineOutput:
    """Output data from Transaction Engine calculations"""

    def __init__(
        self,
        line_totals: list[Decimal],
        subtotal: Decimal,
        tax_amount: Decimal,
        discount_amount: Decimal,
        grand_total: Decimal,
    ):
        self.line_totals = line_totals
        self.subtotal = subtotal
        self.tax_amount = tax_amount
        self.discount_amount = discount_amount
        self.grand_total = grand_total

    def to_dict(self) -> dict:
        """Convert output to dictionary"""
        return {
            "line_totals": [float(lt) for lt in self.line_totals],
            "subtotal": float(self.subtotal),
            "tax_amount": float(self.tax_amount),
            "discount_amount": float(self.discount_amount),
            "grand_total": float(self.grand_total),
        }


class TransactionEngine:
    """
    Shared service for calculating financial totals across purchase and sales documents.

    Handles:
    - Line total calculations (quantity × unit_price)
    - Subtotal calculations (sum of line totals)
    - Tax calculations (subtotal × tax_rate)
    - Grand total calculations (subtotal + tax - discount)
    """

    def calculate(self, input_data: TransactionEngineInput) -> TransactionEngineOutput:
        """
        Calculate line totals, subtotal, tax, and grand total for a transaction.

        Args:
            input_data: TransactionEngineInput containing transaction type, line items,
                       tax rate, and discount amount

        Returns:
            TransactionEngineOutput with all calculated values
        """
        # Calculate line_total as quantity × unit_price for each line
        line_totals = []
        for item in input_data.line_items:
            quantity = Decimal(str(item["quantity"]))
            unit_price = Decimal(str(item["unit_price"]))
            line_total = quantity * unit_price
            line_totals.append(line_total)

        # Calculate subtotal as sum of all line_totals
        subtotal = sum(line_totals, Decimal("0"))

        # Calculate tax_amount as subtotal × tax_rate
        tax_amount = subtotal * input_data.tax_rate

        # Calculate grand_total as subtotal + tax_amount - discount_amount
        grand_total = subtotal + tax_amount - input_data.discount_amount

        return TransactionEngineOutput(
            line_totals=line_totals,
            subtotal=subtotal,
            tax_amount=tax_amount,
            discount_amount=input_data.discount_amount,
            grand_total=grand_total,
        )
