"""
Receipt Service for Payment Flow System.

This service handles receipt generation for confirmed payments including:
- Receipt number generation (format: RCP-{year}-{sequence})
- PDF receipt generation with organization branding
- QR code generation for receipt verification
"""

import io
from datetime import datetime
from uuid import UUID

import qrcode
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError


class ReceiptService:
    """Service for generating payment receipts"""

    def __init__(self, db: Session):
        """
        Initialize receipt service.

        Args:
            db: Database session
        """
        self.db = db

        # Import repositories
        from app.repositories.payment_entry_repository import PaymentEntryRepository

        self.payment_repo = PaymentEntryRepository(db)

    def generate_receipt_number(
        self,
        organization_id: UUID,
        payment_date: datetime,
    ) -> str:
        """
        Generate unique receipt number in format: RCP-{year}-{sequence}.

        This method queries the database for the highest sequence number
        for the given year and organization, then increments it.
        The sequence is zero-padded to 5 digits.

        Args:
            organization_id: Organization UUID
            payment_date: Payment date to extract year

        Returns:
            Unique receipt number string (e.g., "RCP-2024-00001")

        Raises:
            ValidationError: If receipt number generation fails
        """
        from sqlalchemy import func

        from app.models.payment_entry import PaymentEntry

        # Extract year from payment_date
        year = payment_date.year

        # Query database for max sequence number for current year
        # Receipt numbers follow format: RCP-{year}-{sequence}
        max_receipt = (
            self.db.query(func.max(PaymentEntry.receipt_number))
            .filter(
                PaymentEntry.organization_id == organization_id,
                PaymentEntry.receipt_number.like(f"RCP-{year}-%"),
            )
            .scalar()
        )

        # Increment sequence number
        if max_receipt:
            # Extract sequence from format RCP-{year}-{sequence}
            try:
                parts = max_receipt.split("-")
                if len(parts) == 3 and parts[0] == "RCP" and parts[1] == str(year):
                    sequence = int(parts[2]) + 1
                else:
                    # Invalid format, start from 1
                    sequence = 1
            except (ValueError, IndexError):
                # Failed to parse, start from 1
                sequence = 1
        else:
            # No receipts for this year yet, start from 1
            sequence = 1

        # Format receipt number with zero-padding (5 digits)
        receipt_number = f"RCP-{year}-{sequence:05d}"

        return receipt_number

    def generate_receipt_qr_code(
        self,
        receipt_number: str,
        organization_id: UUID,
    ) -> bytes:
        """
        Generate QR code for receipt verification.

        The QR code contains the receipt number and a verification URL
        that can be used to verify the authenticity of the receipt.

        Args:
            receipt_number: Receipt number to encode
            organization_id: Organization UUID

        Returns:
            QR code image as bytes (PNG format)

        Raises:
            ValidationError: If QR code generation fails
        """
        try:
            # Create verification URL with receipt number and organization
            # In production, this would be a real verification endpoint
            verification_url = f"https://app.horizonsync.com/verify-receipt?receipt={receipt_number}&org={organization_id}"

            # Create QR code instance
            qr = qrcode.QRCode(
                version=1,  # Controls size (1 is smallest)
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )

            # Add data to QR code
            qr.add_data(verification_url)
            qr.make(fit=True)

            # Create image
            qr_image = qr.make_image(fill_color="black", back_color="white")

            # Convert to bytes
            buffer = io.BytesIO()
            qr_image.save(buffer, format="PNG")
            qr_bytes = buffer.getvalue()
            buffer.close()

            return qr_bytes

        except Exception as e:
            raise ValidationError(f"Failed to generate QR code: {str(e)}")

    def generate_receipt_pdf(
        self,
        payment_id: UUID,
        organization_id: UUID,
    ) -> bytes:
        """
        Generate PDF receipt for a confirmed payment.

        The receipt includes:
        - Organization details (name, address, logo if available)
        - Customer/Supplier details
        - Payment information (date, amount, mode, receipt number)
        - List of allocated invoices with amounts
        - Unallocated amount (if any)
        - QR code for verification

        Args:
            payment_id: Payment entry UUID
            organization_id: Organization UUID

        Returns:
            PDF data as bytes

        Raises:
            ValidationError: If payment not found or PDF generation fails
        """
        from app.models.base import PaymentEntryStatus
        from app.repositories.payment_reference_repository import (
            PaymentReferenceRepository,
        )

        # Retrieve payment entry
        payment_entry = self.payment_repo.get_by_id(payment_id, organization_id)
        if not payment_entry:
            raise ValidationError(
                f"Payment entry with ID {payment_id} not found or does not belong to organization"
            )

        # Validate payment is confirmed and has receipt number
        if payment_entry.status != PaymentEntryStatus.CONFIRMED:
            raise ValidationError(
                f"Cannot generate receipt for payment with status '{payment_entry.status.value}'. "
                "Only Confirmed payments have receipts."
            )

        if not payment_entry.receipt_number:
            raise ValidationError(
                "Payment entry does not have a receipt number. Cannot generate receipt."
            )

        # Get payment allocations
        reference_repo = PaymentReferenceRepository(self.db)
        allocations = reference_repo.get_by_payment_id(payment_id, organization_id)

        # Get party details (customer or supplier)
        party_name = self._get_party_name(
            payment_entry.party_id, payment_entry.payment_type.value
        )

        # Get organization details
        org_details = self._get_organization_details(organization_id)

        # Generate QR code
        qr_code_bytes = self.generate_receipt_qr_code(
            payment_entry.receipt_number,
            organization_id,
        )

        # Create PDF in memory
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=0.75 * inch,
            leftMargin=0.75 * inch,
            topMargin=0.75 * inch,
            bottomMargin=0.75 * inch,
        )

        # Container for PDF elements
        elements = []

        # Define styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=24,
            textColor=colors.HexColor("#1a1a1a"),
            spaceAfter=12,
            alignment=TA_CENTER,
        )
        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=14,
            textColor=colors.HexColor("#333333"),
            spaceAfter=6,
            spaceBefore=12,
        )
        normal_style = styles["Normal"]

        # Add organization name and title
        elements.append(Paragraph(org_details.get("name", "Organization"), title_style))
        elements.append(Paragraph("PAYMENT RECEIPT", heading_style))
        elements.append(Spacer(1, 0.2 * inch))

        # Add organization address if available
        if org_details.get("address"):
            org_address = Paragraph(org_details["address"], normal_style)
            elements.append(org_address)
            elements.append(Spacer(1, 0.1 * inch))

        # Add receipt number and date
        receipt_info = [
            ["Receipt Number:", payment_entry.receipt_number],
            ["Payment Date:", payment_entry.payment_date.strftime("%Y-%m-%d")],
            ["Payment Mode:", payment_entry.payment_mode.value],
        ]

        if payment_entry.reference_no:
            receipt_info.append(["Reference Number:", payment_entry.reference_no])

        receipt_table = Table(receipt_info, colWidths=[2 * inch, 4 * inch])
        receipt_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
                    ("ALIGN", (0, 0), (0, -1), "LEFT"),
                    ("ALIGN", (1, 0), (1, -1), "LEFT"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(receipt_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Add party details
        party_type = (
            "Customer"
            if payment_entry.payment_type.value == "Customer_Payment"
            else "Supplier"
        )
        elements.append(Paragraph(f"{party_type} Details", heading_style))
        party_info = [
            [f"{party_type} Name:", party_name],
        ]
        party_table = Table(party_info, colWidths=[2 * inch, 4 * inch])
        party_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
                ]
            )
        )
        elements.append(party_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Add payment amount
        elements.append(Paragraph("Payment Amount", heading_style))
        amount_info = [
            [
                "Total Amount:",
                f"{payment_entry.currency_code} {payment_entry.amount:,.2f}",
            ],
        ]
        amount_table = Table(amount_info, colWidths=[2 * inch, 4 * inch])
        amount_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 12),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#1a1a1a")),
                ]
            )
        )
        elements.append(amount_table)
        elements.append(Spacer(1, 0.3 * inch))

        # Add allocated invoices section
        if allocations:
            elements.append(Paragraph("Allocated to Invoices", heading_style))

            # Create table data
            allocation_data = [["Invoice Number", "Allocated Amount"]]
            for allocation in allocations:
                invoice_number = self._get_invoice_number(allocation.invoice_id)
                allocation_data.append(
                    [
                        invoice_number,
                        f"{payment_entry.currency_code} {allocation.allocated_amount:,.2f}",
                    ]
                )

            # Create table
            allocation_table = Table(allocation_data, colWidths=[3 * inch, 3 * inch])
            allocation_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#333333")),
                        ("ALIGN", (0, 0), (0, -1), "LEFT"),
                        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
                        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ]
                )
            )
            elements.append(allocation_table)
            elements.append(Spacer(1, 0.2 * inch))

        # Add unallocated amount if greater than zero
        if payment_entry.unallocated_amount > 0:
            elements.append(Paragraph("Unallocated Amount", heading_style))
            unallocated_info = [
                [
                    "Unallocated:",
                    f"{payment_entry.currency_code} {payment_entry.unallocated_amount:,.2f}",
                ],
            ]
            unallocated_table = Table(unallocated_info, colWidths=[2 * inch, 4 * inch])
            unallocated_table.setStyle(
                TableStyle(
                    [
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#ff6600")),
                    ]
                )
            )
            elements.append(unallocated_table)
            elements.append(Spacer(1, 0.2 * inch))

        # Add QR code
        elements.append(Spacer(1, 0.3 * inch))
        elements.append(Paragraph("Scan to Verify Receipt", heading_style))

        # Create QR code image from bytes
        qr_image_buffer = io.BytesIO(qr_code_bytes)
        qr_image = Image(qr_image_buffer, width=1.5 * inch, height=1.5 * inch)
        elements.append(qr_image)

        # Add footer
        elements.append(Spacer(1, 0.5 * inch))
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.HexColor("#666666"),
            alignment=TA_CENTER,
        )
        footer_text = f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        elements.append(Paragraph(footer_text, footer_style))

        # Build PDF
        doc.build(elements)

        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()

        return pdf_data

    def _get_party_name(self, party_id: UUID, payment_type: str) -> str:
        """
        Get party (customer or supplier) name.

        Args:
            party_id: Party UUID
            payment_type: Payment type (Customer_Payment or Supplier_Payment)

        Returns:
            Party name string
        """
        if payment_type == "Customer_Payment":
            from app.models.customer import Customer

            party = self.db.query(Customer).filter(Customer.id == party_id).first()
            return party.name if party else "Unknown Customer"
        else:
            from app.models.supplier import Supplier

            party = self.db.query(Supplier).filter(Supplier.id == party_id).first()
            return party.name if party else "Unknown Supplier"

    def _get_organization_details(self, organization_id: UUID) -> dict:
        """
        Get organization details for receipt header.

        Args:
            organization_id: Organization UUID

        Returns:
            Dictionary with organization details (name, address, logo_url)
        """
        # In a real implementation, this would query the organization service
        # For now, return placeholder data
        # TODO: Integrate with organization service to get real data
        return {
            "name": "HorizonSync ERP",
            "address": "123 Business Street, City, Country",
            "logo_url": None,  # Logo URL if available
        }

    def _get_invoice_number(self, invoice_id: UUID) -> str:
        """
        Get invoice number by ID.

        Args:
            invoice_id: Invoice UUID

        Returns:
            Invoice number string
        """
        from app.models.invoice import Invoice

        invoice = self.db.query(Invoice).filter(Invoice.id == invoice_id).first()
        return invoice.invoice_number if invoice else "Unknown"
