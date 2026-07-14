"""Tax Calculation Engine service for calculating taxes on transactions"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.tax_template import TaxRule, TaxTemplate
from app.repositories.tax_template_repository import TaxTemplateRepository


@dataclass
class LineItem:
    """Line item data for tax calculation"""

    item_id: UUID
    qty: Decimal
    rate: Decimal
    amount: Decimal
    is_tax_exempt: bool = False
    item_group_id: UUID | None = None


@dataclass
class TaxContext:
    """Context information for tax calculation"""

    organization_id: UUID
    transaction_type: str  # "Sales" or "Purchase"
    item_id: UUID | None = None
    item_group_id: UUID | None = None
    customer_id: UUID | None = None
    supplier_id: UUID | None = None
    shipping_address: dict | None = None
    customer_location: dict | None = None
    supplier_location: dict | None = None
    is_customer_tax_exempt: bool = False


@dataclass
class TaxBreakdownEntry:
    """Individual tax breakdown entry"""

    tax_template_id: UUID
    tax_rule_id: UUID
    tax_type: str
    tax_rate: Decimal
    taxable_amount: Decimal
    tax_amount: Decimal
    is_compound: bool
    sequence: int
    account_head_id: UUID


@dataclass
class TaxCalculationResult:
    """Result of tax calculation"""

    net_total: Decimal
    tax_breakdown: list[TaxBreakdownEntry]
    total_tax: Decimal
    taxes_by_type: dict[str, Decimal]


class TaxCalculationEngine:
    """Engine for calculating taxes on transactions"""

    def __init__(self, db: Session):
        self.db = db
        self.tax_template_repo = TaxTemplateRepository(db)

    def calculate_taxes(
        self, line_items: list[LineItem], context: TaxContext
    ) -> TaxCalculationResult:
        """
        Calculate taxes for all line items in a transaction.

        Args:
            line_items: List of line items to calculate taxes for
            context: Tax context with transaction and customer information

        Returns:
            TaxCalculationResult with breakdown and totals
        """
        # Check if customer is tax-exempt
        if context.is_customer_tax_exempt and context.transaction_type == "Sales":
            net_total = sum(item.amount for item in line_items)
            return TaxCalculationResult(
                net_total=net_total,
                tax_breakdown=[],
                total_tax=Decimal("0.00"),
                taxes_by_type={},
            )

        # Calculate net total from non-exempt line items
        net_total = sum(item.amount for item in line_items)
        taxable_amount = sum(
            item.amount for item in line_items if not item.is_tax_exempt
        )

        # If all line items are tax-exempt, return zero taxes
        if taxable_amount == Decimal("0.00"):
            return TaxCalculationResult(
                net_total=net_total,
                tax_breakdown=[],
                total_tax=Decimal("0.00"),
                taxes_by_type={},
            )

        # Get applicable tax template
        # For simplicity, use the first line item's context
        # In a real scenario, you might need to handle multiple templates
        first_item = line_items[0] if line_items else None
        if not first_item:
            return TaxCalculationResult(
                net_total=net_total,
                tax_breakdown=[],
                total_tax=Decimal("0.00"),
                taxes_by_type={},
            )

        template_result = self.tax_template_repo.get_applicable_template(
            organization_id=context.organization_id,
            transaction_type=context.transaction_type,
            item_id=first_item.item_id,
            item_group_id=first_item.item_group_id,
            customer_location=context.customer_location or context.shipping_address,
            supplier_location=context.supplier_location,
        )

        if not template_result:
            # No applicable template found
            return TaxCalculationResult(
                net_total=net_total,
                tax_breakdown=[],
                total_tax=Decimal("0.00"),
                taxes_by_type={},
            )

        tax_template, source = template_result

        # Calculate taxes using the template
        tax_breakdown = self.calculate_line_item_taxes(taxable_amount, tax_template)

        # Calculate total tax and group by type
        total_tax = sum(entry.tax_amount for entry in tax_breakdown)
        taxes_by_type: dict[str, Decimal] = {}
        for entry in tax_breakdown:
            if entry.tax_type in taxes_by_type:
                taxes_by_type[entry.tax_type] += entry.tax_amount
            else:
                taxes_by_type[entry.tax_type] = entry.tax_amount

        return TaxCalculationResult(
            net_total=net_total,
            tax_breakdown=tax_breakdown,
            total_tax=total_tax,
            taxes_by_type=taxes_by_type,
        )

    def calculate_line_item_taxes(
        self, taxable_amount: Decimal, tax_template: TaxTemplate
    ) -> list[TaxBreakdownEntry]:
        """
        Calculate taxes for a line item using a tax template.

        Args:
            taxable_amount: The taxable amount (sum of non-exempt line items)
            tax_template: Tax template with rules to apply

        Returns:
            List of tax breakdown entries
        """
        if not tax_template.tax_rules:
            return []

        # Separate non-compound and compound taxes
        non_compound_rules = [
            rule for rule in tax_template.tax_rules if not rule.is_compound
        ]
        compound_rules = [rule for rule in tax_template.tax_rules if rule.is_compound]

        tax_breakdown: list[TaxBreakdownEntry] = []

        # Calculate non-compound taxes first
        for rule in non_compound_rules:
            tax_amount = self._calculate_tax_amount(taxable_amount, rule.tax_rate)
            entry = TaxBreakdownEntry(
                tax_template_id=tax_template.id,
                tax_rule_id=rule.id,
                tax_type=rule.tax_type,
                tax_rate=rule.tax_rate,
                taxable_amount=taxable_amount,
                tax_amount=tax_amount,
                is_compound=False,
                sequence=rule.sequence,
                account_head_id=rule.account_head_id,
            )
            tax_breakdown.append(entry)

        # Calculate compound taxes (tax on tax)
        if compound_rules:
            compound_entries = self.apply_compound_taxes(
                taxable_amount, tax_breakdown, compound_rules, tax_template.id
            )
            tax_breakdown.extend(compound_entries)

        return tax_breakdown

    def apply_compound_taxes(
        self,
        base_amount: Decimal,
        non_compound_taxes: list[TaxBreakdownEntry],
        compound_tax_rules: list[TaxRule],
        tax_template_id: UUID,
    ) -> list[TaxBreakdownEntry]:
        """
        Apply compound taxes (tax on tax).

        Args:
            base_amount: Base taxable amount
            non_compound_taxes: List of non-compound tax entries
            compound_tax_rules: List of compound tax rules to apply
            tax_template_id: ID of the tax template

        Returns:
            List of compound tax breakdown entries
        """
        # Calculate sum of non-compound taxes
        sum_non_compound = sum(entry.tax_amount for entry in non_compound_taxes)

        # Compound tax base = base_amount + sum of non-compound taxes
        compound_base = base_amount + sum_non_compound

        compound_entries: list[TaxBreakdownEntry] = []

        for rule in compound_tax_rules:
            tax_amount = self._calculate_tax_amount(compound_base, rule.tax_rate)
            entry = TaxBreakdownEntry(
                tax_template_id=tax_template_id,
                tax_rule_id=rule.id,
                tax_type=rule.tax_type,
                tax_rate=rule.tax_rate,
                taxable_amount=compound_base,
                tax_amount=tax_amount,
                is_compound=True,
                sequence=rule.sequence,
                account_head_id=rule.account_head_id,
            )
            compound_entries.append(entry)

        return compound_entries

    def _calculate_tax_amount(self, amount: Decimal, tax_rate: Decimal) -> Decimal:
        """
        Calculate tax amount from base amount and tax rate.

        Args:
            amount: Base amount
            tax_rate: Tax rate as percentage (e.g., 9.00 for 9%)

        Returns:
            Tax amount rounded to 2 decimal places
        """
        tax_amount = (amount * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
        return tax_amount
