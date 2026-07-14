"""Charge Calculation Engine service for calculating extra charges on transactions"""

from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.charge_template import ChargeTemplate
from app.repositories.charge_template_repository import ChargeTemplateRepository


@dataclass
class ChargeContext:
    """Context information for charge calculation"""

    organization_id: UUID
    transaction_type: str
    net_total: Decimal
    total_weight: Decimal | None = None
    customer_id: UUID | None = None
    shipping_address: dict | None = None
    customer_location: dict | None = None


@dataclass
class ChargeBreakdownEntry:
    """Individual charge breakdown entry"""

    charge_template_id: UUID | None
    charge_type: str
    description: str
    calculation_method: str  # "FIXED" or "PERCENTAGE"
    charge_amount: Decimal
    account_head_id: UUID
    is_auto_calculated: bool


@dataclass
class ChargeCalculationResult:
    """Result of charge calculation"""

    charge_breakdown: list[ChargeBreakdownEntry]
    total_charges: Decimal


class ChargeCalculationEngine:
    """Engine for calculating extra charges on transactions"""

    def __init__(self, db: Session):
        self.db = db
        self.charge_template_repo = ChargeTemplateRepository(db)

    def calculate_charges(
        self, context: ChargeContext, net_total: Decimal, total_tax: Decimal
    ) -> ChargeCalculationResult:
        """
        Calculate applicable extra charges for a transaction.

        Args:
            context: Charge context with transaction information
            net_total: Net total amount of transaction
            total_tax: Total tax amount calculated

        Returns:
            ChargeCalculationResult with breakdown and total
        """
        # Get all applicable charge templates
        applicable_templates = self.charge_template_repo.get_applicable_charges(
            organization_id=context.organization_id,
            transaction_type=context.transaction_type,
            net_total=float(net_total),
            customer_location=context.customer_location or context.shipping_address,
            total_weight=float(context.total_weight) if context.total_weight else None,
        )

        if not applicable_templates:
            return ChargeCalculationResult(
                charge_breakdown=[],
                total_charges=Decimal("0.00"),
            )

        # Calculate charges for each applicable template
        charge_breakdown: list[ChargeBreakdownEntry] = []
        grand_total = net_total + total_tax

        for template in applicable_templates:
            # Determine base amount based on template configuration
            if template.calculation_method == "PERCENTAGE":
                if template.base_on == "Grand_Total":
                    base_amount = grand_total
                else:  # Default to Net_Total
                    base_amount = net_total
            else:
                base_amount = (
                    net_total  # Not used for FIXED, but passed for consistency
                )

            charge_entry = self.calculate_single_charge(template, base_amount)
            charge_breakdown.append(charge_entry)

        # Calculate total charges
        total_charges = sum(entry.charge_amount for entry in charge_breakdown)

        return ChargeCalculationResult(
            charge_breakdown=charge_breakdown,
            total_charges=total_charges,
        )

    def calculate_single_charge(
        self, charge_template: ChargeTemplate, base_amount: Decimal
    ) -> ChargeBreakdownEntry:
        """
        Calculate a single charge based on template configuration.

        Args:
            charge_template: Charge template to apply
            base_amount: Base amount for percentage calculations (Net_Total or Grand_Total)

        Returns:
            ChargeBreakdownEntry with calculated amount
        """
        if charge_template.calculation_method == "FIXED":
            # Use fixed amount directly
            charge_amount = Decimal(str(charge_template.fixed_amount))
        elif charge_template.calculation_method == "PERCENTAGE":
            # Calculate percentage of base amount
            percentage_rate = Decimal(str(charge_template.percentage_rate))
            charge_amount = (base_amount * percentage_rate / Decimal("100")).quantize(
                Decimal("0.01")
            )
        else:
            # Invalid calculation method, default to zero
            charge_amount = Decimal("0.00")

        return ChargeBreakdownEntry(
            charge_template_id=charge_template.id,
            charge_type=charge_template.charge_type,
            description=charge_template.template_name,
            calculation_method=charge_template.calculation_method,
            charge_amount=charge_amount,
            account_head_id=charge_template.account_head_id,
            is_auto_calculated=True,
        )
