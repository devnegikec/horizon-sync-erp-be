"""Delivery note service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import DocumentStatus
from app.repositories.delivery_note_repository import DeliveryNoteRepository


class DeliveryNoteService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = DeliveryNoteRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = {k: v for k, v in data.items() if k != "items"}
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        # Auto-generate delivery_note_no if not provided
        if not payload.get("delivery_note_no"):
            from app.services.document_numbering_service import DocumentNumberingService

            payload["delivery_note_no"] = DocumentNumberingService(
                self.db
            ).get_next_number(organization_id, "delivery_note")
        if payload.get("status"):
            payload["status"] = DocumentStatus(payload["status"])
        items = data.get("items") or []
        dn = self.repo.create(payload, [dict(it) for it in items])
        return self._to_response(dn)

    def get_by_id(self, delivery_note_id: UUID, organization_id: UUID) -> dict:
        dn = self.repo.get_by_id(delivery_note_id, organization_id)
        if not dn:
            raise ResourceNotFoundException(
                f"Delivery note {delivery_note_id} not found"
            )
        return self._to_response(dn)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "delivery_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_delivery_notes(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            customer_id=customer_id,
            status=status,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return [self._to_list_item(x) for x in items], pagination

    def update(
        self, delivery_note_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        dn = self.repo.get_by_id(delivery_note_id, organization_id)
        if not dn:
            raise ResourceNotFoundException(
                f"Delivery note {delivery_note_id} not found"
            )
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = DocumentStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(dn, payload)
        self.db.refresh(dn)
        return self._to_response(dn)

    def delete(self, delivery_note_id: UUID, organization_id: UUID) -> None:
        dn = self.repo.get_by_id(delivery_note_id, organization_id)
        if not dn:
            raise ResourceNotFoundException(
                f"Delivery note {delivery_note_id} not found"
            )
        self.repo.delete(dn)

    def convert_to_invoice(
        self,
        delivery_note_id: UUID,
        items_to_bill: list[dict],
        organization_id: UUID,
        user_id: UUID,
        due_date=None,
        remarks: str | None = None,
    ) -> dict:
        """Convert a submitted delivery note to a sales invoice.

        Only items present on the delivery note can be billed, and only up to
        the delivered qty.  Creates an Invoice + InvoiceItems, links back to
        the delivery note via reference_type/reference_id, and updates
        billed_qty on the related sales order items when a SO reference exists.

        Args:
            delivery_note_id: Delivery note to convert
            items_to_bill: List of {item_id (DN item UUID), qty_to_bill}
            organization_id: Tenant
            user_id: Audit trail
            due_date: Optional invoice due date
            remarks: Optional invoice remarks

        Returns:
            dict with invoice_id, invoice_no, grand_total

        Raises:
            ResourceNotFoundException: DN not found
            StateError: DN not in submitted status
            ValidationError: qty exceeds delivered qty or item not found
        """
        from datetime import UTC, datetime
        from decimal import Decimal

        from app.core.exceptions import StateError, ValidationError
        from app.models.base import DocumentStatus, InvoiceStatus, InvoiceType
        from app.models.invoice import Invoice, InvoiceItem
        from app.models.item import Item
        from app.models.sales_order import SalesOrder, SalesOrderItem
        from app.services.document_numbering_service import DocumentNumberingService

        dn = self.repo.get_by_id(delivery_note_id, organization_id)
        if not dn:
            raise ResourceNotFoundException(
                f"Delivery note {delivery_note_id} not found"
            )

        if dn.status != DocumentStatus.SUBMITTED:
            raise StateError(
                "Delivery note must be in submitted status to convert to invoice",
                current_state=dn.status.value,
                required_state=["submitted"],
            )

        # Check if an invoice already exists for this delivery note
        existing_invoice = (
            self.db.query(Invoice)
            .filter(
                Invoice.reference_type == "delivery_note",
                Invoice.reference_id == delivery_note_id,
                Invoice.organization_id == organization_id,
            )
            .first()
        )
        if existing_invoice:
            raise StateError(
                f"An invoice ({existing_invoice.invoice_no}) already exists for this delivery note",
                current_state="invoiced",
                required_state=["not_invoiced"],
            )

        # Build a lookup of DN items by id
        dn_item_map = {item.id: item for item in dn.items}

        # Validate every requested item
        grand_total = Decimal("0")
        validated_items: list[dict] = []
        for req in items_to_bill:
            dn_item_id = req["item_id"]
            qty_to_bill = Decimal(str(req["qty_to_bill"]))

            dn_item = dn_item_map.get(dn_item_id)
            if not dn_item:
                raise ValidationError(
                    f"Item {dn_item_id} not found in delivery note {delivery_note_id}"
                )

            if qty_to_bill <= 0:
                raise ValidationError(
                    f"Billing quantity must be greater than 0 for item {dn_item_id}"
                )

            if qty_to_bill > dn_item.qty:
                raise ValidationError(
                    f"Billing quantity {qty_to_bill} exceeds delivered quantity "
                    f"{dn_item.qty} for item {dn_item_id}"
                )

            rate = dn_item.rate or Decimal("0")
            amount = qty_to_bill * rate
            grand_total += amount

            # Resolve item_code / item_name for the invoice line
            item_obj = self.db.query(Item).filter(Item.id == dn_item.item_id).first()

            validated_items.append(
                {
                    "dn_item": dn_item,
                    "qty": qty_to_bill,
                    "rate": rate,
                    "amount": amount,
                    "item_obj": item_obj,
                }
            )

        try:
            now = datetime.now(UTC)
            invoice_no = DocumentNumberingService(self.db).get_next_number(
                organization_id, "invoice"
            )

            invoice = Invoice(
                organization_id=organization_id,
                invoice_no=invoice_no,
                invoice_type=InvoiceType.SALES,
                party_id=dn.customer_id,
                party_type="Customer",
                posting_date=now,
                due_date=due_date,
                status=InvoiceStatus.DRAFT,
                grand_total=grand_total,
                outstanding_amount=grand_total,
                currency="INR",
                reference_type="delivery_note",
                reference_id=dn.id,
                remarks=remarks or dn.remarks,
                created_by=user_id,
                updated_by=user_id,
            )
            self.db.add(invoice)
            self.db.flush()

            for idx, v in enumerate(validated_items):
                dn_item = v["dn_item"]
                item_obj = v["item_obj"]
                inv_item = InvoiceItem(
                    organization_id=organization_id,
                    invoice_id=invoice.id,
                    item_id=dn_item.item_id,
                    item_code=item_obj.item_code if item_obj else None,
                    item_name=item_obj.item_name if item_obj else None,
                    qty=v["qty"],
                    uom=dn_item.uom,
                    rate=v["rate"],
                    amount=v["amount"],
                    sort_order=idx,
                )
                self.db.add(inv_item)

            # If the DN was created from a sales order, update billed_qty
            if dn.reference_type == "sales_order" and dn.reference_id:
                so = (
                    self.db.query(SalesOrder)
                    .filter(
                        SalesOrder.id == dn.reference_id,
                        SalesOrder.organization_id == organization_id,
                    )
                    .first()
                )
                if so:
                    for v in validated_items:
                        dn_item = v["dn_item"]
                        soi = (
                            self.db.query(SalesOrderItem)
                            .filter(
                                SalesOrderItem.sales_order_id == so.id,
                                SalesOrderItem.item_id == dn_item.item_id,
                            )
                            .first()
                        )
                        if soi:
                            soi.billed_qty = (soi.billed_qty or 0) + v["qty"]

            self.db.commit()
            self.db.refresh(invoice)

            return {
                "invoice_id": invoice.id,
                "invoice_no": invoice.invoice_no,
                "grand_total": invoice.grand_total,
            }

        except Exception as e:
            self.db.rollback()
            raise e

    def _to_response(self, dn) -> dict:
        from app.models.item import Item
        from app.models.pick_list import PickList
        from app.models.sales_order import SalesOrder

        # Get customer data
        customer_data = None
        if dn.customer:
            customer_data = {
                "customer_name": dn.customer.customer_name,
                "customer_code": dn.customer.customer_code,
                "phone": dn.customer.phone,
                "email": dn.customer.email,
            }

        # Get warehouse data
        warehouse_data = None
        if dn.warehouse:
            warehouse_data = {
                "warehouse_name": dn.warehouse.name,
                "warehouse_code": dn.warehouse.code,
            }

        # Get reference data (sales_order or pick_list)
        reference_data = None
        resolved_currency = None
        if dn.reference_type and dn.reference_id:
            if dn.reference_type == "sales_order":
                ref_obj = (
                    self.db.query(SalesOrder)
                    .filter(SalesOrder.id == dn.reference_id)
                    .first()
                )
                if ref_obj:
                    reference_data = {
                        "id": str(dn.reference_id),
                        "reference_type": "sales_order",
                        "name": ref_obj.sales_order_no,
                        "code": ref_obj.sales_order_no,
                    }
                    resolved_currency = ref_obj.currency
            elif dn.reference_type == "pick_list":
                ref_obj = (
                    self.db.query(PickList)
                    .filter(PickList.id == dn.reference_id)
                    .first()
                )
                if ref_obj:
                    reference_data = {
                        "id": str(dn.reference_id),
                        "reference_type": "pick_list",
                        "name": ref_obj.pick_list_no,
                        "code": ref_obj.pick_list_no,
                    }
                    # Try to resolve currency from pick list's sales order
                    if hasattr(ref_obj, 'sales_order_id') and ref_obj.sales_order_id:
                        so = self.db.query(SalesOrder).filter(SalesOrder.id == ref_obj.sales_order_id).first()
                        if so:
                            resolved_currency = so.currency

        # Get items data with enriched item details
        items_data = []
        if hasattr(dn, "items") and dn.items:
            for item in dn.items:
                # Get item details
                item_obj = self.db.query(Item).filter(Item.id == item.item_id).first()
                item_data = None
                if item_obj:
                    item_data = {
                        "id": str(item_obj.id),
                        "name": item_obj.item_name,
                        "code": item_obj.item_code,
                    }

                items_data.append(
                    {
                        "id": item.id,
                        "item": item_data,
                        "qty": item.qty,
                        "uom": item.uom,
                        "rate": item.rate,
                        "amount": item.amount,
                        "warehouse_id": item.warehouse_id,
                        "batch_no": item.batch_no,
                        "serial_nos": item.serial_nos,
                        "sort_order": item.sort_order,
                        "extra_data": item.extra_data,
                    }
                )

        return {
            "id": dn.id,
            "organization_id": dn.organization_id,
            "delivery_note_no": dn.delivery_note_no,
            "customer_id": dn.customer_id,
            "customer": customer_data,
            "delivery_date": dn.delivery_date,
            "status": dn.status.value if dn.status else None,
            "currency": resolved_currency or "INR",
            "warehouse_id": dn.warehouse_id,
            "warehouse": warehouse_data,
            "pick_list_id": dn.pick_list_id,
            "reference_type": dn.reference_type,
            "reference_id": dn.reference_id,
            "reference": reference_data,
            "remarks": dn.remarks,
            "extra_data": dn.extra_data,
            "items": items_data,
            "submitted_at": dn.submitted_at,
            "created_by": dn.created_by,
            "updated_by": dn.updated_by,
            "created_at": dn.created_at,
            "updated_at": dn.updated_at,
        }

    @staticmethod
    def _to_list_item(dn) -> dict:
        # Get customer data
        customer_data = None
        if dn.customer:
            customer_data = {
                "customer_name": dn.customer.customer_name,
                "customer_code": dn.customer.customer_code,
                "phone": dn.customer.phone,
                "email": dn.customer.email,
            }

        # Get warehouse data
        warehouse_data = None
        if dn.warehouse:
            warehouse_data = {
                "warehouse_name": dn.warehouse.name,
                "warehouse_code": dn.warehouse.code,
            }

        return {
            "id": dn.id,
            "organization_id": dn.organization_id,
            "delivery_note_no": dn.delivery_note_no,
            "customer_id": dn.customer_id,
            "customer": customer_data,
            "status": dn.status.value if dn.status else None,
            "delivery_date": dn.delivery_date,
            "warehouse_id": dn.warehouse_id,
            "warehouse": warehouse_data,
            "remarks": dn.remarks,
            "created_at": dn.created_at,
        }
