"""Subscription Invoice Service for B2B billing system.

This service handles creation and management of subscription invoices for 
customer organizations based on their billing cycles, seat limits, and credit usage.

Task 1B-2 implementation: Subscription Invoice Service
"""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.base import BillingCycle, InvoiceType
from app.models.invoice import Invoice, InvoiceItem
from app.repositories.invoice_repository import InvoiceRepository
from app.schemas.invoice import InvoiceCreate, InvoiceItemCreate


class SubscriptionInvoiceService:
    """Service for managing subscription invoices in the B2B billing system."""
    
    def __init__(self, db: Session):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
    
    def create_subscription_invoice(
        self,
        organization_id: UUID,
        billing_cycle: BillingCycle,
        seat_count: int,
        credit_usage: Decimal = Decimal("0"),
        base_price_per_seat: Decimal = Decimal("10.00"),
        credit_rate: Decimal = Decimal("0.01"),
        created_by: Optional[UUID] = None
    ) -> Dict:
        """Create subscription invoice for organization billing.
        
        Args:
            organization_id: Organization to bill (cannot be master org)
            billing_cycle: Monthly, quarterly, or yearly billing
            seat_count: Number of user seats to bill
            credit_usage: Amount of credits consumed
            base_price_per_seat: Price per seat for the billing cycle
            credit_rate: Cost per credit unit
            created_by: User creating the invoice (system admin)
            
        Returns:
            Dictionary containing invoice data
            
        Raises:
            ValueError: If organization is master org or invalid parameters
        """
        # Validate organization (cannot invoice master org)
        if self._is_master_organization(organization_id):
            raise ValueError("Cannot create subscription invoice for master organization")
            
        # Calculate billing period
        period_start, period_end = self._calculate_billing_period(billing_cycle)
        
        # Generate invoice number
        invoice_no = self._generate_invoice_number(organization_id, billing_cycle)
        
        # Calculate invoice amounts
        line_items = self._calculate_line_items(
            billing_cycle, seat_count, credit_usage, base_price_per_seat, credit_rate
        )
        
        # Calculate totals
        subtotal = sum(item["amount"] for item in line_items)
        grand_total = subtotal  # No tax for B2B subscriptions in this implementation
        
        # Set payment terms based on billing cycle
        due_date = self._calculate_due_date(period_start, billing_cycle)
        
        # Create invoice data
        invoice_data = InvoiceCreate(
            organization_id=organization_id,
            invoice_no=invoice_no,
            invoice_type=InvoiceType.SUBSCRIPTION.value,
            party_id=organization_id,  # Self-billing for subscription
            party_type="organization", 
            posting_date=datetime.now(UTC),
            due_date=due_date,
            status="draft",
            grand_total=grand_total,
            outstanding_amount=grand_total,
            currency="USD",
            reference_type="subscription",
            remarks=f"Subscription billing for {billing_cycle.value} period",
            billing_cycle=billing_cycle.value,
            subscription_period_start=period_start,
            subscription_period_end=period_end,
            seat_count=seat_count,
            credit_usage=credit_usage,
            net_total=subtotal,
            total_tax=Decimal("0"),
            created_by=created_by,
            items=line_items
        ).model_dump()
        
        # Create invoice with items
        invoice = self._create_invoice_with_items(invoice_data, line_items)
        
        return self._to_response(invoice)
    
    def _calculate_billing_period(self, billing_cycle: BillingCycle) -> tuple[datetime, datetime]:
        """Calculate billing period start and end dates."""
        now = datetime.now(UTC)
        period_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        if billing_cycle == BillingCycle.MONTHLY:
            next_month = period_start.replace(month=period_start.month + 1) if period_start.month < 12 else period_start.replace(year=period_start.year + 1, month=1)
            period_end = next_month - timedelta(days=1)
        elif billing_cycle == BillingCycle.QUARTERLY:
            # Start of current quarter
            quarter_start_month = ((period_start.month - 1) // 3) * 3 + 1
            period_start = period_start.replace(month=quarter_start_month)
            # End of quarter (3 months later)
            end_month = quarter_start_month + 2
            if end_month > 12:
                period_end = period_start.replace(year=period_start.year + 1, month=end_month - 12, day=31)
            else:
                period_end = period_start.replace(month=end_month, day=31)
        elif billing_cycle == BillingCycle.YEARLY:
            # Start of year
            period_start = period_start.replace(month=1, day=1)
            # End of year
            period_end = period_start.replace(month=12, day=31)
        else:
            raise ValueError(f"Unsupported billing cycle: {billing_cycle}")
            
        return period_start, period_end
    
    def _calculate_due_date(self, period_start: datetime, billing_cycle: BillingCycle) -> datetime:
        """Calculate payment due date based on billing cycle."""
        if billing_cycle == BillingCycle.MONTHLY:
            return period_start + timedelta(days=30)  # 30 days from period start
        elif billing_cycle == BillingCycle.QUARTERLY:
            return period_start + timedelta(days=45)  # 45 days for quarterly
        elif billing_cycle == BillingCycle.YEARLY:
            return period_start + timedelta(days=60)  # 60 days for yearly
        else:
            return period_start + timedelta(days=30)  # Default to 30 days
    
    def _calculate_line_items(
        self,
        billing_cycle: BillingCycle,
        seat_count: int,
        credit_usage: Decimal,
        base_price_per_seat: Decimal,
        credit_rate: Decimal
    ) -> List[Dict]:
        """Calculate line items for subscription invoice."""
        line_items = []
        
        # Base subscription fee (seats)
        if seat_count > 0:
            # Adjust price based on billing cycle
            cycle_multiplier = {"monthly": 1, "quarterly": 3, "yearly": 12}
            seat_price = base_price_per_seat * cycle_multiplier.get(billing_cycle.value, 1)
            seat_amount = seat_price * seat_count
            
            line_items.append({
                "item_code": f"SUB-{billing_cycle.value.upper()}",
                "item_name": f"Subscription - {billing_cycle.value.title()} ({seat_count} seats)",
                "qty": seat_count,
                "uom": "seats",
                "rate": seat_price,
                "amount": seat_amount,
                "total_amount": seat_amount,
                "sort_order": 1
            })
        
        # Credit usage charge
        if credit_usage > 0:
            credit_amount = credit_usage * credit_rate
            line_items.append({
                "item_code": "CREDIT-USAGE",
                "item_name": f"Credit Usage ({credit_usage} credits)",
                "qty": credit_usage,
                "uom": "credits",
                "rate": credit_rate,
                "amount": credit_amount,
                "total_amount": credit_amount,
                "sort_order": 2
            })
        
        return line_items
    
    def _generate_invoice_number(self, organization_id: UUID, billing_cycle: BillingCycle) -> str:
        """Generate unique invoice number for subscription."""
        now = datetime.now(UTC)
        date_part = now.strftime("%Y%m")
        cycle_prefix = {"monthly": "M", "quarterly": "Q", "yearly": "Y"}
        prefix = cycle_prefix.get(billing_cycle.value, "S")
        
        # Use first 8 chars of org ID for uniqueness
        org_part = str(organization_id).replace("-", "")[:8].upper()
        
        return f"SUB-{prefix}-{date_part}-{org_part}"
    
    def _create_invoice_with_items(self, invoice_data: Dict, line_items: List[Dict]) -> Invoice:
        """Create invoice with associated line items."""
        # Remove items from invoice_data before creating invoice
        items_data = invoice_data.pop("items", [])
        
        # Create invoice
        invoice = Invoice(**invoice_data)
        self.db.add(invoice)
        self.db.flush()  # Get invoice ID
        
        # Create invoice items
        for item_data in line_items:
            item_data["invoice_id"] = invoice.id
            item_data["organization_id"] = invoice.organization_id
            item = InvoiceItem(**item_data)
            self.db.add(item)
        
        self.db.commit()
        self.db.refresh(invoice)
        
        return invoice
    
    def _is_master_organization(self, organization_id: UUID) -> bool:
        """Check if organization is master organization (simplified check)."""
        # In real implementation, this would query the organization service
        # For now, return False to allow testing
        # TODO: Integrate with identity service to check organization type
        return False
    
    def _to_response(self, invoice: Invoice) -> Dict:
        """Convert invoice model to response dictionary."""
        return {
            "id": invoice.id,
            "organization_id": invoice.organization_id,
            "invoice_no": invoice.invoice_no,
            "invoice_type": invoice.invoice_type,
            "party_id": invoice.party_id,
            "party_type": invoice.party_type,
            "posting_date": invoice.posting_date,
            "due_date": invoice.due_date,
            "status": invoice.status,
            "grand_total": float(invoice.grand_total),
            "outstanding_amount": float(invoice.outstanding_amount),
            "currency": invoice.currency,
            "billing_cycle": invoice.billing_cycle,
            "subscription_period_start": invoice.subscription_period_start,
            "subscription_period_end": invoice.subscription_period_end,
            "seat_count": invoice.seat_count,
            "credit_usage": float(invoice.credit_usage) if invoice.credit_usage else None,
            "net_total": float(invoice.net_total),
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at
        }
    
    def get_subscription_invoices_for_organization(
        self,
        organization_id: UUID,
        limit: int = 50
    ) -> List[Dict]:
        """Get subscription invoices for an organization."""
        invoices = (
            self.db.query(Invoice)
            .filter(
                Invoice.organization_id == organization_id,
                Invoice.invoice_type == InvoiceType.SUBSCRIPTION.value
            )
            .order_by(Invoice.posting_date.desc())
            .limit(limit)
            .all()
        )
        
        return [self._to_response(invoice) for invoice in invoices]
    
    def get_overdue_subscription_invoices(self) -> List[Dict]:
        """Get all overdue subscription invoices across organizations."""
        now = datetime.now(UTC)
        invoices = (
            self.db.query(Invoice)
            .filter(
                Invoice.invoice_type == InvoiceType.SUBSCRIPTION.value,
                Invoice.due_date < now,
                Invoice.outstanding_amount > 0,
                Invoice.status.in_(["draft", "pending", "partial"])
            )
            .order_by(Invoice.due_date.asc())
            .all()
        )
        
        return [self._to_response(invoice) for invoice in invoices]

    def create_setup_fee_invoice(
        self,
        organization_id: UUID,
        setup_fee_amount: Decimal,
        onboarding_fee: Decimal = Decimal("0.00"),
        line_items: Optional[List[Dict]] = None,
        notes: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> Dict:
        """Create setup fee invoice for new customer organization"""
        if self._is_master_organization(organization_id):
            raise ValueError("Cannot create setup fee invoice for master organization")
        
        # Generate invoice number
        invoice_no = self._generate_setup_invoice_number(organization_id)
        
        # Calculate line items if not provided
        if not line_items:
            line_items = [
                {
                    "item_code": "SETUP-FEE",
                    "item_name": "Initial Setup Fee",
                    "qty": 1,
                    "uom": "service",
                    "rate": setup_fee_amount,
                    "amount": setup_fee_amount,
                    "total_amount": setup_fee_amount,
                    "sort_order": 1
                }
            ]
            
            if onboarding_fee > 0:
                line_items.append({
                    "item_code": "ONBOARD-FEE",
                    "item_name": "Onboarding and Training Services",
                    "qty": 1,
                    "uom": "service",
                    "rate": onboarding_fee,
                    "amount": onboarding_fee,
                    "total_amount": onboarding_fee,
                    "sort_order": 2
                })
        
        # Calculate totals
        grand_total = sum(item["amount"] for item in line_items)
        
        # Create invoice data
        invoice_data = {
            "organization_id": organization_id,
            "invoice_no": invoice_no,
            "invoice_type": InvoiceType.SETUP_FEE.value,
            "party_id": organization_id,
            "party_type": "organization",
            "posting_date": datetime.now(UTC),
            "due_date": datetime.now(UTC) + timedelta(days=15),  # 15 days for setup fee
            "status": "draft",
            "grand_total": grand_total,
            "outstanding_amount": grand_total,
            "currency": "USD",
            "reference_type": "setup_fee",
            "remarks": notes or "Initial setup fee for organization onboarding",
            "net_total": grand_total,
            "total_tax": Decimal("0"),
            "created_by": created_by,
        }
        
        # Create invoice with items
        invoice = self._create_invoice_with_items(invoice_data, line_items)
        return self._to_response(invoice)

    def create_overage_invoice(
        self,
        organization_id: UUID,
        overage_type: str,
        overage_quantity: int,
        overage_rate: Decimal,
        billing_period_start: datetime,
        billing_period_end: datetime,
        notes: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> Dict:
        """Create overage charges invoice for usage exceeding limits"""
        if self._is_master_organization(organization_id):
            raise ValueError("Cannot create overage invoice for master organization")
        
        # Generate invoice number
        invoice_no = self._generate_overage_invoice_number(organization_id, overage_type)
        
        # Calculate overage charges
        overage_amount = overage_quantity * overage_rate
        
        line_items = [{
            "item_code": f"OVERAGE-{overage_type.upper()}",
            "item_name": f"Overage Charges - {overage_type.title()} ({overage_quantity} units)",
            "qty": overage_quantity,
            "uom": "units",
            "rate": overage_rate,
            "amount": overage_amount,
            "total_amount": overage_amount,
            "sort_order": 1
        }]
        
        # Create invoice data
        invoice_data = {
            "organization_id": organization_id,
            "invoice_no": invoice_no,
            "invoice_type": InvoiceType.OVERAGE.value,
            "party_id": organization_id,
            "party_type": "organization",
            "posting_date": datetime.now(UTC),
            "due_date": datetime.now(UTC) + timedelta(days=30),
            "status": "draft",
            "grand_total": overage_amount,
            "outstanding_amount": overage_amount,
            "currency": "USD",
            "reference_type": "overage",
            "remarks": notes or f"Overage charges for {overage_type} usage from {billing_period_start.date()} to {billing_period_end.date()}",
            "subscription_period_start": billing_period_start,
            "subscription_period_end": billing_period_end,
            "net_total": overage_amount,
            "total_tax": Decimal("0"),
            "created_by": created_by,
        }
        
        # Create invoice with items
        invoice = self._create_invoice_with_items(invoice_data, line_items)
        return self._to_response(invoice)

    def create_addon_invoice(
        self,
        organization_id: UUID,
        addon_name: str,
        addon_description: str,
        addon_price: Decimal,
        billing_cycle: BillingCycle,
        start_date: Optional[datetime] = None,
        notes: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> Dict:
        """Create addon service invoice for additional features/services"""
        if self._is_master_organization(organization_id):
            raise ValueError("Cannot create addon invoice for master organization")
        
        # Generate invoice number
        invoice_no = self._generate_addon_invoice_number(organization_id, addon_name)
        
        # Calculate billing period for addon
        start_date = start_date or datetime.now(UTC)
        period_start, period_end = self._calculate_billing_period(billing_cycle)
        
        line_items = [{
            "item_code": f"ADDON-{addon_name.upper().replace(' ', '-')}",
            "item_name": f"Add-on Service: {addon_name}",
            "description": addon_description,
            "qty": 1,
            "uom": "service",
            "rate": addon_price,
            "amount": addon_price,
            "total_amount": addon_price,
            "sort_order": 1
        }]
        
        # Create invoice data
        invoice_data = {
            "organization_id": organization_id,
            "invoice_no": invoice_no,
            "invoice_type": InvoiceType.ADDON.value,
            "party_id": organization_id,
            "party_type": "organization",
            "posting_date": datetime.now(UTC),
            "due_date": self._calculate_due_date(start_date, billing_cycle),
            "status": "draft",
            "grand_total": addon_price,
            "outstanding_amount": addon_price,
            "currency": "USD",
            "reference_type": "addon",
            "remarks": notes or f"Add-on service: {addon_name} - {addon_description}",
            "billing_cycle": billing_cycle.value,
            "subscription_period_start": period_start,
            "subscription_period_end": period_end,
            "net_total": addon_price,
            "total_tax": Decimal("0"),
            "created_by": created_by,
        }
        
        # Create invoice with items
        invoice = self._create_invoice_with_items(invoice_data, line_items)
        return self._to_response(invoice)

    def create_credit_adjustment_invoice(
        self,
        organization_id: UUID,
        adjustment_type: str,  # credit, refund, discount
        adjustment_amount: Decimal,
        reason: str,
        reference_invoice_id: Optional[UUID] = None,
        notes: Optional[str] = None,
        created_by: Optional[UUID] = None
    ) -> Dict:
        """Create credit adjustment or refund invoice"""
        if self._is_master_organization(organization_id):
            raise ValueError("Cannot create credit adjustment for master organization")
        
        # Generate invoice number
        invoice_no = self._generate_credit_adjustment_number(organization_id, adjustment_type)
        
        # For credit adjustments, amount should be negative to reduce outstanding balance
        if adjustment_type in ["credit", "refund"]:
            adjustment_amount = -abs(adjustment_amount)
        
        line_items = [{
            "item_code": f"CREDIT-{adjustment_type.upper()}",
            "item_name": f"{adjustment_type.title()} Adjustment",
            "description": reason,
            "qty": 1,
            "uom": "adjustment",
            "rate": adjustment_amount,
            "amount": adjustment_amount,
            "total_amount": adjustment_amount,
            "sort_order": 1
        }]
        
        # Create invoice data
        invoice_data = {
            "organization_id": organization_id,
            "invoice_no": invoice_no,
            "invoice_type": InvoiceType.CREDIT_ADJUSTMENT.value,
            "party_id": organization_id,
            "party_type": "organization",
            "posting_date": datetime.now(UTC),
            "due_date": datetime.now(UTC),  # Credit adjustments are immediate
            "status": "paid" if adjustment_type in ["credit", "refund"] else "draft",
            "grand_total": adjustment_amount,
            "outstanding_amount": Decimal("0") if adjustment_type in ["credit", "refund"] else adjustment_amount,
            "currency": "USD",
            "reference_type": "credit_adjustment",
            "remarks": notes or f"{adjustment_type.title()} adjustment: {reason}",
            "net_total": adjustment_amount,
            "total_tax": Decimal("0"),
            "created_by": created_by,
        }
        
        # Add reference to original invoice if provided
        if reference_invoice_id:
            invoice_data["reference_id"] = reference_invoice_id
        
        # Create invoice with items
        invoice = self._create_invoice_with_items(invoice_data, line_items)
        return self._to_response(invoice)

    def _generate_setup_invoice_number(self, organization_id: UUID) -> str:
        """Generate invoice number for setup fee"""
        now = datetime.now(UTC)
        date_part = now.strftime("%Y%m")
        org_part = str(organization_id).replace("-", "")[:8].upper()
        return f"SETUP-{date_part}-{org_part}"

    def _generate_overage_invoice_number(self, organization_id: UUID, overage_type: str) -> str:
        """Generate invoice number for overage charges"""
        now = datetime.now(UTC)
        date_part = now.strftime("%Y%m")
        org_part = str(organization_id).replace("-", "")[:8].upper()
        type_part = overage_type[:4].upper()
        return f"OVER-{type_part}-{date_part}-{org_part}"

    def _generate_addon_invoice_number(self, organization_id: UUID, addon_name: str) -> str:
        """Generate invoice number for addon services"""
        now = datetime.now(UTC)
        date_part = now.strftime("%Y%m")
        org_part = str(organization_id).replace("-", "")[:8].upper()
        addon_part = addon_name[:4].upper().replace(" ", "")
        return f"ADD-{addon_part}-{date_part}-{org_part}"

    def _generate_credit_adjustment_number(self, organization_id: UUID, adjustment_type: str) -> str:
        """Generate invoice number for credit adjustments"""
        now = datetime.now(UTC)
        date_part = now.strftime("%Y%m")
        org_part = str(organization_id).replace("-", "")[:8].upper()
        type_part = adjustment_type[:4].upper()
        return f"CR-{type_part}-{date_part}-{org_part}"