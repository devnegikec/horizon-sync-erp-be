"""Invoice service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import InvoiceStatus, InvoiceType
from app.models.customer import Customer
from app.models.item import Item
from app.models.supplier import Supplier
from app.repositories.invoice_repository import InvoiceRepository
from app.repositories.stock_level_repository import StockLevelRepository
from app.repositories.tax_template_repository import TaxTemplateRepository


class InvoiceService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = InvoiceRepository(db)
        self.stock_level_repo = StockLevelRepository(db)
        self.tax_template_repo = TaxTemplateRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = dict(data)
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        # Auto-generate invoice_no if not provided
        if not payload.get("invoice_no"):
            from app.services.document_numbering_service import DocumentNumberingService

            payload["invoice_no"] = DocumentNumberingService(self.db).get_next_number(
                organization_id, "invoice"
            )
        if payload.get("invoice_type"):
            payload["invoice_type"] = InvoiceType(payload["invoice_type"])
        if payload.get("status"):
            payload["status"] = InvoiceStatus(payload["status"])
        inv = self.repo.create(payload)
        return self._to_response(inv)

    def get_by_id(self, invoice_id: UUID, organization_id: UUID) -> dict:
        inv = self.repo.get_by_id(invoice_id, organization_id)
        if not inv:
            raise ResourceNotFoundException(f"Invoice {invoice_id} not found")
        return self._to_response(inv)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        party_id: UUID | None = None,
        status: str | None = None,
        invoice_type: str | None = None,
        sort_by: str = "posting_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_invoices(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            party_id=party_id,
            status=status,
            invoice_type=invoice_type,
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

        # Batch-load party names/codes to avoid N+1 queries
        party_map = self._build_party_map(items)

        return [self._to_list_item(x, party_map) for x in items], pagination

    def update(
        self, invoice_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        inv = self.repo.get_by_id(invoice_id, organization_id)
        if not inv:
            raise ResourceNotFoundException(f"Invoice {invoice_id} not found")
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = InvoiceStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(inv, payload)
        self.db.refresh(inv)
        return self._to_response(inv)

    def delete(self, invoice_id: UUID, organization_id: UUID) -> None:
        inv = self.repo.get_by_id(invoice_id, organization_id)
        if not inv:
            raise ResourceNotFoundException(f"Invoice {invoice_id} not found")
        self.repo.delete(inv)

    def _to_response(self, inv) -> dict:
        # Get customer or supplier details based on party_type
        party_details = None
        party_type_lower = inv.party_type.lower() if inv.party_type else None

        if party_type_lower == "customer":
            customer = (
                self.db.query(Customer).filter(Customer.id == inv.party_id).first()
            )
            if customer:
                party_details = {
                    "customer_name": customer.customer_name,
                    "customer_code": customer.customer_code,
                    "email": customer.email,
                    "phone": customer.phone,
                    "address": customer.address,
                    "address_line1": customer.address_line1,
                    "address_line2": customer.address_line2,
                    "city": customer.city,
                    "state": customer.state,
                    "postal_code": customer.postal_code,
                    "country": customer.country,
                    "tax_number": customer.tax_number,
                    "status": customer.status.value if customer.status else None,
                }
        elif party_type_lower == "supplier":
            supplier = (
                self.db.query(Supplier).filter(Supplier.id == inv.party_id).first()
            )
            if supplier:
                party_details = {
                    "supplier_name": supplier.supplier_name,
                    "supplier_code": supplier.supplier_code,
                    "email": supplier.email,
                    "phone": supplier.phone,
                    "address": supplier.address,
                    "address_line1": supplier.address_line1,
                    "address_line2": supplier.address_line2,
                    "city": supplier.city,
                    "state": supplier.state,
                    "postal_code": supplier.postal_code,
                    "country": supplier.country,
                    "tax_number": supplier.tax_number,
                    "status": supplier.status.value if supplier.status else None,
                }

        # Support both string and enum for invoice_type/status (DB uses String columns)
        inv_type = inv.invoice_type
        inv_type_val = getattr(inv_type, "value", inv_type) if inv_type else None
        st = inv.status
        status_val = getattr(st, "value", st) if st else None
        response = {
            "id": inv.id,
            "organization_id": inv.organization_id,
            "invoice_no": inv.invoice_no,
            "invoice_type": inv_type_val,
            "party_id": inv.party_id,
            "party_type": inv.party_type,
            "posting_date": inv.posting_date,
            "due_date": inv.due_date,
            "status": status_val,
            "grand_total": inv.grand_total,
            "outstanding_amount": inv.outstanding_amount,
            "currency": inv.currency,
            "discount_type": getattr(inv, "discount_type", None) or "percentage",
            "discount_value": getattr(inv, "discount_value", None) or 0,
            "reference_type": getattr(inv, "reference_type", None),
            "reference_id": getattr(inv, "reference_id", None),
            "remarks": getattr(inv, "remarks", None),
            "submitted_at": getattr(inv, "submitted_at", None),
            "created_by": inv.created_by,
            "updated_by": inv.updated_by,
            "created_at": inv.created_at,
            "updated_at": inv.updated_at,
        }

        # Add customer or supplier details
        if party_details:
            if party_type_lower == "customer":
                response["customer"] = party_details
            else:
                response["supplier"] = party_details

        # Add items if they exist
        if hasattr(inv, "items") and inv.items:
            response["items"] = [
                {
                    "id": item.id,
                    "organization_id": item.organization_id,
                    "invoice_id": item.invoice_id,
                    "item_id": item.item_id,
                    "item_code": item.item_code,
                    "item_name": item.item_name,
                    "qty": item.qty,
                    "uom": item.uom,
                    "rate": item.rate,
                    "amount": item.amount,
                    "sort_order": item.sort_order,
                    "extra_data": item.extra_data,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                    **self._get_item_details(item, inv.organization_id),
                }
                for item in inv.items
            ]

        return response

    def _get_item_details(self, invoice_item, organization_id: UUID) -> dict:
        """Get comprehensive item details including description, tax info, and order quantities."""
        if not invoice_item.item_id:
            return {
                "description": None,
                "min_order_qty": 1,
                "max_order_qty": None,
                "standard_rate": "0.00",
                "tax_template_id": None,
                "tax_rate": "0.00",
                "tax_amount": "0.00",
                "total_amount": str(invoice_item.amount or "0.00"),
                "tax_info": None,
            }

        # Fetch item details
        item = self.db.query(Item).filter(Item.id == invoice_item.item_id).first()
        if not item:
            return {
                "description": None,
                "min_order_qty": 1,
                "max_order_qty": None,
                "standard_rate": "0.00",
                "tax_template_id": None,
                "tax_rate": "0.00",
                "tax_amount": "0.00",
                "total_amount": str(invoice_item.amount or "0.00"),
                "tax_info": None,
            }

        # Get tax template for this item
        tax_info = None
        tax_template_id = None
        tax_rate = "0.00"
        tax_amount = "0.00"

        # Try to get tax template from item's default or organization settings
        tax_result = self.tax_template_repo.get_applicable_template(
            organization_id=organization_id,
            transaction_type="Sales",  # Adjust based on invoice_type if needed
            item_id=item.id,
            item_group_id=item.item_group_id,
        )

        if tax_result:
            template, _ = tax_result
            tax_template_id = template.id

            # Calculate tax rate from template rules
            total_tax_rate = sum(
                float(rule.tax_rate or 0) for rule in (template.tax_rules or [])
            )
            tax_rate = f"{total_tax_rate:.2f}"

            # Calculate tax amount
            from decimal import Decimal

            amount = Decimal(str(invoice_item.amount or 0))
            tax_amount_decimal = amount * Decimal(str(total_tax_rate)) / Decimal("100")
            tax_amount = f"{tax_amount_decimal:.2f}"

            # Build tax info breakup
            breakup = [
                {
                    "rule_name": rule.rule_name,
                    "tax_type": rule.tax_type,
                    "rate": float(rule.tax_rate or 0),
                    "is_compound": bool(rule.is_compound),
                }
                for rule in (template.tax_rules or [])
            ]
            is_compound = any(r.get("is_compound", False) for r in breakup)
            tax_info = {
                "id": str(template.id),
                "template_name": template.template_name,
                "template_code": template.template_code,
                "is_compound": is_compound,
                "breakup": breakup,
            }

        # Calculate total amount (amount + tax)
        from decimal import Decimal

        amount = Decimal(str(invoice_item.amount or 0))
        tax_amt = Decimal(str(tax_amount))
        total_amount = f"{(amount + tax_amt):.2f}"

        return {
            "description": item.description,
            "min_order_qty": item.min_order_qty or 1,
            "max_order_qty": item.max_order_qty,
            "standard_rate": str(item.standard_rate or "0.00"),
            "tax_template_id": str(tax_template_id) if tax_template_id else None,
            "tax_rate": tax_rate,
            "tax_amount": tax_amount,
            "total_amount": total_amount,
            "tax_info": tax_info,
        }

    def _build_party_map(self, invoices: list) -> dict:
        """Batch-load party name/code for a list of invoices."""
        customer_ids = set()
        supplier_ids = set()
        for inv in invoices:
            pt = (inv.party_type or "").lower()
            if pt == "customer" and inv.party_id:
                customer_ids.add(inv.party_id)
            elif pt == "supplier" and inv.party_id:
                supplier_ids.add(inv.party_id)

        party_map: dict = {}
        if customer_ids:
            customers = (
                self.db.query(
                    Customer.id, Customer.customer_name, Customer.customer_code
                )
                .filter(Customer.id.in_(customer_ids))
                .all()
            )
            for c in customers:
                party_map[c.id] = {"name": c.customer_name, "code": c.customer_code}
        if supplier_ids:
            suppliers = (
                self.db.query(
                    Supplier.id, Supplier.supplier_name, Supplier.supplier_code
                )
                .filter(Supplier.id.in_(supplier_ids))
                .all()
            )
            for s in suppliers:
                party_map[s.id] = {"name": s.supplier_name, "code": s.supplier_code}
        return party_map

    @staticmethod
    def _to_list_item(inv, party_map: dict | None = None) -> dict:
        # invoice_type and status are String columns in DB; support both str and enum
        inv_type = inv.invoice_type
        inv_type_val = getattr(inv_type, "value", inv_type) if inv_type else None
        st = inv.status
        status_val = getattr(st, "value", st) if st else None
        party_info = (party_map or {}).get(inv.party_id) or {}
        return {
            "id": inv.id,
            "organization_id": inv.organization_id,
            "invoice_no": inv.invoice_no,
            "invoice_type": inv_type_val,
            "party_id": inv.party_id,
            "party_name": party_info.get("name"),
            "party_code": party_info.get("code"),
            "status": status_val,
            "posting_date": inv.posting_date,
            "grand_total": inv.grand_total,
            "outstanding_amount": getattr(inv, "outstanding_amount", None),
            "created_at": inv.created_at,
        }
