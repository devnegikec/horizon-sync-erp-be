"""Purchase Invoice service wrapper for Invoice API"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.transaction import transactional
from app.models.base import InvoiceType, PurchaseOrderStatus
from app.models.purchase_order import PurchaseOrder
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.purchase_order_repository import PurchaseOrderRepository
from app.services.transaction_engine import (
    TransactionEngine,
    TransactionEngineInput,
)


class PurchaseInvoiceService:
    """
    Service wrapper for creating Purchase Invoices using existing Invoice API.
    
    Integrates with:
    - Invoice API (invoice_type=PURCHASE)
    - Purchase Order validation
    - Transaction Engine for calculations
    
    Requirements: 6.1, 6.2, 6.3, 6.4
    """

    def __init__(self, db: Session):
        self.db = db
        self.invoice_repo = InvoiceRepository(db)
        self.po_repo = PurchaseOrderRepository(db)
        self.transaction_engine = TransactionEngine()

    @transactional
    def create_purchase_invoice(
        self,
        purchase_order_id: UUID,
        line_items: list[dict],
        tax_rate: Decimal | None,
        discount_amount: Decimal | None,
        organization_id: UUID,
        user_id: UUID,
        invoice_no: str,
        posting_date: str | None = None,
        due_date: str | None = None,
        remarks: str | None = None,
    ) -> dict:
        """
        Create Purchase Invoice from Purchase Order using existing Invoice API.
        
        Args:
            purchase_order_id: Source Purchase Order ID
            line_items: List of line items with item_id, quantity, unit_price
            tax_rate: Tax rate as decimal (e.g., 0.18 for 18%)
            discount_amount: Discount amount
            organization_id: Organization ID
            user_id: User ID
            invoice_no: Invoice number
            posting_date: Invoice posting date
            due_date: Payment due date
            remarks: Additional remarks
            
        Returns:
            dict: Created invoice response
            
        Requirements:
        - 6.1: Set invoice_type as PURCHASE
        - 6.2: Set reference_type as PURCHASE_ORDER and reference_id
        - 6.3: Validate Purchase Order exists and has valid status
        - 6.4: Invoke Transaction Engine with transaction_type PURCHASE
        """
        # Requirement 6.3: Validate Purchase Order exists and has valid status
        po = self.po_repo.get_by_id(purchase_order_id, organization_id)
        if not po:
            raise ResourceNotFoundException(
                f"Purchase Order {purchase_order_id} not found"
            )

        # Validate Purchase Order status
        valid_statuses = [
            PurchaseOrderStatus.SUBMITTED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
            PurchaseOrderStatus.FULLY_RECEIVED,
        ]
        if po.status not in valid_statuses:
            raise ValidationException(
                f"Cannot create Purchase Invoice for Purchase Order in {po.status.value} status. "
                f"Valid statuses: {', '.join(s.value for s in valid_statuses)}"
            )

        # Validate line items
        if not line_items:
            raise ValidationException("At least one line item is required")

        for idx, item in enumerate(line_items):
            if item.get("quantity", 0) <= 0:
                raise ValidationException(
                    f"Line item {idx}: quantity must be greater than zero"
                )
            if item.get("unit_price", 0) < 0:
                raise ValidationException(
                    f"Line item {idx}: unit_price must be non-negative"
                )

        # Requirement 6.5: Three-way matching validation
        # Validate invoiced quantities do not exceed received quantities
        self._validate_three_way_matching(po, line_items)

        # Requirement 6.4: Invoke Transaction Engine with transaction_type PURCHASE
        engine_input = TransactionEngineInput(
            transaction_type="PURCHASE",
            line_items=line_items,
            tax_rate=Decimal(str(tax_rate)) if tax_rate else None,
            discount_amount=Decimal(str(discount_amount)) if discount_amount else None,
        )
        calculation = self.transaction_engine.calculate(engine_input)

        # Requirement 6.1: Set invoice_type as PURCHASE
        # Requirement 6.2: Set reference_type as PURCHASE_ORDER and reference_id
        invoice_data = {
            "organization_id": organization_id,
            "invoice_no": invoice_no,
            "invoice_type": InvoiceType.PURCHASE,
            "party_type": "SUPPLIER",
            "party_id": po.party_id,
            "reference_type": "PURCHASE_ORDER",
            "reference_id": purchase_order_id,
            "posting_date": posting_date,
            "due_date": due_date,
            "grand_total": calculation.grand_total,
            "outstanding_amount": calculation.grand_total,
            "remarks": remarks,
            "created_by": user_id,
            "updated_by": user_id,
        }

        # Create invoice using existing Invoice API
        invoice = self.invoice_repo.create(invoice_data)

        # Store line items and calculation details in extra_data
        extra_data = {
            "line_items": [
                {
                    "item_id": str(item["item_id"]),
                    "quantity": float(item["quantity"]),
                    "unit_price": float(item["unit_price"]),
                    "line_total": float(calculation.line_totals[idx]),
                }
                for idx, item in enumerate(line_items)
            ],
            "subtotal": float(calculation.subtotal),
            "tax_amount": float(calculation.tax_amount),
            "tax_rate": float(tax_rate) if tax_rate else None,
            "discount_amount": float(calculation.discount_amount),
        }

        # Update invoice with extra_data
        self.invoice_repo.update(invoice, {"extra_data": extra_data})
        self.db.refresh(invoice)

        return self._to_response(invoice, extra_data)

    def _validate_three_way_matching(
        self, po: PurchaseOrder, invoice_line_items: list[dict]
    ) -> None:
        """
        Validate three-way matching: Purchase Order, Receipt Note, and Purchase Invoice.
        
        Ensures that invoiced quantities do not exceed received quantities for each line item.
        
        Args:
            po: Purchase Order being invoiced
            invoice_line_items: List of invoice line items with item_id and quantity
            
        Raises:
            ValidationException: If invoiced quantity exceeds received quantity
            
        Requirements: 6.5
        """
        # Build a map of Purchase Order line items by item_id
        po_lines_map = {str(line.item_id): line for line in po.line_items}

        # Validate each invoice line item
        for idx, invoice_item in enumerate(invoice_line_items):
            item_id = str(invoice_item.get("item_id"))
            invoiced_qty = Decimal(str(invoice_item.get("quantity", 0)))

            # Check if item exists in Purchase Order
            if item_id not in po_lines_map:
                raise ValidationException(
                    f"Line item {idx}: item {item_id} not found in Purchase Order {po.id}"
                )

            po_line = po_lines_map[item_id]
            received_qty = Decimal(str(po_line.received_quantity))

            # Three-way matching: invoiced quantity must not exceed received quantity
            if invoiced_qty > received_qty:
                raise ValidationException(
                    f"Line item {idx}: invoiced quantity {invoiced_qty} exceeds "
                    f"received quantity {received_qty} for item {item_id}. "
                    f"Three-way matching validation failed."
                )

    @staticmethod
    def _to_response(invoice, extra_data: dict | None = None) -> dict:
        """Convert Invoice model to response dict"""
        response = {
            "id": invoice.id,
            "organization_id": invoice.organization_id,
            "invoice_no": invoice.invoice_no,
            "invoice_type": invoice.invoice_type.value if invoice.invoice_type else None,
            "party_id": invoice.party_id,
            "party_type": invoice.party_type,
            "reference_type": invoice.reference_type,
            "reference_id": invoice.reference_id,
            "posting_date": invoice.posting_date,
            "due_date": invoice.due_date,
            "status": invoice.status.value if invoice.status else None,
            "grand_total": invoice.grand_total,
            "outstanding_amount": invoice.outstanding_amount,
            "currency": invoice.currency,
            "remarks": invoice.remarks,
            "submitted_at": invoice.submitted_at,
            "created_by": invoice.created_by,
            "updated_by": invoice.updated_by,
            "created_at": invoice.created_at,
            "updated_at": invoice.updated_at,
        }

        # Include calculation details if available
        if extra_data:
            response["line_items"] = extra_data.get("line_items", [])
            response["subtotal"] = extra_data.get("subtotal")
            response["tax_amount"] = extra_data.get("tax_amount")
            response["tax_rate"] = extra_data.get("tax_rate")
            response["discount_amount"] = extra_data.get("discount_amount")
        elif invoice.extra_data:
            response["line_items"] = invoice.extra_data.get("line_items", [])
            response["subtotal"] = invoice.extra_data.get("subtotal")
            response["tax_amount"] = invoice.extra_data.get("tax_amount")
            response["tax_rate"] = invoice.extra_data.get("tax_rate")
            response["discount_amount"] = invoice.extra_data.get("discount_amount")

        return response
