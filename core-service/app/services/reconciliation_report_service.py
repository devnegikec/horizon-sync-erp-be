"""Reconciliation Report Service for Payment Flow system"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID
from typing import Any

from sqlalchemy.orm import Session

from app.repositories.payment_entry_repository import PaymentEntryRepository
from app.repositories.payment_reference_repository import PaymentReferenceRepository
from app.models.base import PaymentEntryStatus, PaymentMode


class ReconciliationReportService:
    """Service for generating payment reconciliation reports"""

    def __init__(self, db: Session):
        """
        Initialize reconciliation report service.

        Args:
            db: Database session
        """
        self.db = db
        self.payment_repo = PaymentEntryRepository(db)
        self.reference_repo = PaymentReferenceRepository(db)

    def generate_report(
        self,
        organization_id: UUID,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        party_id: UUID | None = None,
        payment_mode: str | None = None,
        status: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate reconciliation report for specified date range and filters.

        Args:
            organization_id: Organization UUID
            date_from: Start date for payment date range (inclusive)
            date_to: End date for payment date range (inclusive)
            party_id: Optional filter by customer/supplier ID
            payment_mode: Optional filter by payment mode (Cash, Check, Bank_Transfer)
            status: Optional filter by payment status (Draft, Confirmed, Cancelled)

        Returns:
            Dictionary containing:
                - summary: Total payments received, total allocated, total unallocated
                - payments_by_status: Payments grouped by status
                - payments_by_mode: Payments grouped by payment mode
                - payments: List of payment details with allocated invoices
                - unallocated_payments: List of payments with unallocated amounts
        """
        # Convert filter strings to enums if provided
        status_enum = None
        if status:
            try:
                status_value = status.strip()
                for s in PaymentEntryStatus:
                    if s.value == status_value or s.name.lower() == status_value.lower():
                        status_enum = s
                        break
            except (ValueError, AttributeError):
                pass

        payment_mode_enum = None
        if payment_mode:
            try:
                mode_value = payment_mode.strip()
                for mode in PaymentMode:
                    if mode.value == mode_value or mode.name.lower() == mode_value.lower():
                        payment_mode_enum = mode
                        break
            except (ValueError, AttributeError):
                pass

        # Fetch all payment entries matching the filters
        payment_entries = self.payment_repo.list_with_filters(
            organization_id=organization_id,
            status=status_enum,
            payment_mode=payment_mode_enum,
            payment_type=None,
            party_id=party_id,
            date_from=date_from,
            date_to=date_to,
            search=None,
            has_unallocated=None,
            sort_by="payment_date",
            sort_order="desc",
            limit=None,
            offset=None,
        )

        # Calculate summary totals
        total_payments_received = Decimal("0.00")
        total_allocated = Decimal("0.00")
        total_unallocated = Decimal("0.00")

        for payment in payment_entries:
            total_payments_received += Decimal(str(payment.amount))
            
            # Calculate allocated amount for this payment
            allocated_for_payment = self.reference_repo.get_total_allocated_for_payment(
                payment.id, organization_id
            )
            total_allocated += allocated_for_payment
            
            # Calculate unallocated amount
            unallocated = Decimal(str(payment.amount)) - allocated_for_payment
            total_unallocated += unallocated

        # Group payments by status
        payments_by_status = {}
        for payment in payment_entries:
            status_key = payment.status.value
            if status_key not in payments_by_status:
                payments_by_status[status_key] = {
                    "count": 0,
                    "total_amount": Decimal("0.00"),
                    "payments": []
                }
            
            payments_by_status[status_key]["count"] += 1
            payments_by_status[status_key]["total_amount"] += Decimal(str(payment.amount))
            payments_by_status[status_key]["payments"].append(self._format_payment(payment, organization_id))

        # Group payments by payment_mode
        payments_by_mode = {}
        for payment in payment_entries:
            mode_key = payment.payment_mode.value
            if mode_key not in payments_by_mode:
                payments_by_mode[mode_key] = {
                    "count": 0,
                    "total_amount": Decimal("0.00"),
                    "payments": []
                }
            
            payments_by_mode[mode_key]["count"] += 1
            payments_by_mode[mode_key]["total_amount"] += Decimal(str(payment.amount))
            payments_by_mode[mode_key]["payments"].append(self._format_payment(payment, organization_id))

        # Format all payments with details
        payments = [self._format_payment(payment, organization_id) for payment in payment_entries]

        # Filter payments with unallocated amounts
        unallocated_payments = [
            p for p in payments if Decimal(str(p["unallocated_amount"])) > 0
        ]

        # Build report structure
        report = {
            "summary": {
                "total_payments_received": str(total_payments_received),
                "total_allocated": str(total_allocated),
                "total_unallocated": str(total_unallocated),
                "payment_count": len(payment_entries),
                "unallocated_payment_count": len(unallocated_payments),
            },
            "payments_by_status": {
                status: {
                    "count": data["count"],
                    "total_amount": str(data["total_amount"]),
                    "payments": data["payments"]
                }
                for status, data in payments_by_status.items()
            },
            "payments_by_mode": {
                mode: {
                    "count": data["count"],
                    "total_amount": str(data["total_amount"]),
                    "payments": data["payments"]
                }
                for mode, data in payments_by_mode.items()
            },
            "payments": payments,
            "unallocated_payments": unallocated_payments,
            "filters": {
                "date_from": date_from.isoformat() if date_from else None,
                "date_to": date_to.isoformat() if date_to else None,
                "party_id": str(party_id) if party_id else None,
                "payment_mode": payment_mode,
                "status": status,
            },
        }

        return report

    def _format_payment(self, payment, organization_id: UUID) -> dict[str, Any]:
        """
        Format payment entry with allocated invoices for report.

        Args:
            payment: PaymentEntry object
            organization_id: Organization UUID

        Returns:
            Dictionary with payment details and allocated invoices
        """
        # Get payment references with invoice details
        payment_references = self.reference_repo.get_by_payment_id_with_invoice_details(
            payment.id, organization_id
        )

        # Format allocated invoices
        allocated_invoices = []
        for ref in payment_references:
            invoice_data = {
                "invoice_id": str(ref.invoice_id),
                "allocated_amount": str(ref.allocated_amount),
                "exchange_rate": str(ref.exchange_rate),
                "allocated_amount_invoice_currency": str(ref.allocated_amount_invoice_currency),
            }
            
            # Add invoice details if available
            if hasattr(ref, 'invoice') and ref.invoice:
                invoice_data.update({
                    "invoice_number": ref.invoice.invoice_number if hasattr(ref.invoice, 'invoice_number') else None,
                    "invoice_date": ref.invoice.invoice_date.isoformat() if hasattr(ref.invoice, 'invoice_date') else None,
                    "invoice_amount": str(ref.invoice.grand_total) if hasattr(ref.invoice, 'grand_total') else None,
                })
            
            allocated_invoices.append(invoice_data)

        # Calculate total allocated for this payment
        total_allocated = sum(
            Decimal(str(ref.allocated_amount)) for ref in payment_references
        )
        unallocated_amount = Decimal(str(payment.amount)) - total_allocated

        # Format payment data
        payment_data = {
            "id": str(payment.id),
            "payment_type": payment.payment_type.value,
            "party_id": str(payment.party_id),
            "amount": str(payment.amount),
            "currency_code": payment.currency_code,
            "payment_date": payment.payment_date.isoformat(),
            "payment_mode": payment.payment_mode.value,
            "reference_no": payment.reference_no,
            "status": payment.status.value,
            "receipt_number": payment.receipt_number,
            "unallocated_amount": str(unallocated_amount),
            "allocated_invoices": allocated_invoices,
            "allocation_count": len(allocated_invoices),
            "created_at": payment.created_at.isoformat(),
        }

        return payment_data
