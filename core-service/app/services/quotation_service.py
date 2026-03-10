"""Quotation service"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import QuotationStatus
from app.models.customer import Customer
from app.models.item import Item
from app.models.quotation import QuotationItem
from app.repositories.quotation_repository import QuotationRepository
from app.repositories.stock_level_repository import StockLevelRepository
from app.repositories.tax_template_repository import TaxTemplateRepository
from app.services.tax_calculation_engine import (
    LineItem,
    TaxCalculationEngine,
    TaxContext,
)


class QuotationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QuotationRepository(db)
        self.stock_level_repo = StockLevelRepository(db)
        self.tax_template_repo = TaxTemplateRepository(db)
        self.tax_engine = TaxCalculationEngine(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = dict(data)
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id

        # Auto-generate quotation_no if not provided
        quotation_no = payload.get("quotation_no")
        if not quotation_no:
            from app.services.document_numbering_service import DocumentNumberingService

            quotation_no = DocumentNumberingService(self.db).get_next_number(
                organization_id, "quotation"
            )
            payload["quotation_no"] = quotation_no

        # Handle status enum conversion
        if payload.get("status"):
            payload["status"] = QuotationStatus(payload["status"])

        # Extract items
        items_data = payload.pop("items", [])

        # Validate customer_id belongs to same organization
        if "customer_id" in payload:
            self._validate_customer_organization(
                payload["customer_id"], organization_id
            )

        # Validate item_id in line items belongs to same organization
        for item_data in items_data:
            if "item_id" in item_data:
                self._validate_item_organization(item_data["item_id"], organization_id)

        # Create quotation first (we need quotation.id for item payloads)
        quotation = self.repo.create(payload)

        customer = (
            self.db.query(Customer)
            .filter(Customer.id == payload["customer_id"])
            .first()
        )
        shipping_address = (
            {
                "city": customer.city,
                "state": customer.state,
                "country": customer.country,
            }
            if customer and (customer.city or customer.state or customer.country)
            else None
        )

        subtotal = Decimal("0")
        for item_data in items_data:
            item_payload = self._build_quotation_item_payload(
                item_data, quotation.id, organization_id, shipping_address
            )
            subtotal += item_payload["total_amount"]
            item = QuotationItem(**item_payload)
            self.db.add(item)

        discount_type = (payload.get("discount_type") or "percentage").lower()
        if discount_type not in ("flat", "percentage"):
            discount_type = "percentage"
        discount_value = Decimal(str(payload.get("discount_value") or 0))
        discount_amount = self._compute_document_discount(
            subtotal, discount_type, discount_value
        )
        grand_total = max(Decimal("0"), subtotal - discount_amount)
        self.repo.update(
            quotation,
            {
                "grand_total": grand_total,
                "discount_type": discount_type,
                "discount_value": discount_value,
                "discount_amount": discount_amount,
            },
        )

        self.db.commit()
        self.db.refresh(quotation)
        return self._to_response(quotation)

    def get_by_id(self, quotation_id: UUID, organization_id: UUID) -> dict:
        quotation = self.repo.get_by_id(quotation_id, organization_id)
        if not quotation:
            raise ResourceNotFoundException(f"Quotation {quotation_id} not found")
        return self._to_response(quotation)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "quotation_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_quotations(
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
        self, quotation_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        quotation = self._get_quotation_for_update(quotation_id, organization_id, data)
        payload = self._prepare_update_payload(data, organization_id, user_id)

        if "items" in data:
            subtotal = self._update_quotation_items(
                quotation, data["items"], organization_id
            )
            discount_type = (
                data.get("discount_type")
                or getattr(quotation, "discount_type", None)
                or "percentage"
            ).lower()
            if discount_type not in ("flat", "percentage"):
                discount_type = "percentage"
            discount_value = Decimal(
                str(
                    data.get("discount_value", getattr(quotation, "discount_value", 0))
                    or 0
                )
            )
            discount_amount = self._compute_document_discount(
                subtotal, discount_type, discount_value
            )
            payload["grand_total"] = max(Decimal("0"), subtotal - discount_amount)
            payload["discount_type"] = discount_type
            payload["discount_value"] = discount_value
            payload["discount_amount"] = discount_amount
        elif "discount_type" in data or "discount_value" in data:
            self.db.refresh(quotation)
            subtotal = sum(
                Decimal(str(item.total_amount or 0)) for item in quotation.items
            )
            discount_type = (
                data.get("discount_type")
                or getattr(quotation, "discount_type", None)
                or "percentage"
            ).lower()
            if discount_type not in ("flat", "percentage"):
                discount_type = "percentage"
            discount_value = Decimal(
                str(
                    data.get("discount_value", getattr(quotation, "discount_value", 0))
                    or 0
                )
            )
            discount_amount = self._compute_document_discount(
                subtotal, discount_type, discount_value
            )
            payload["grand_total"] = max(Decimal("0"), subtotal - discount_amount)
            payload["discount_type"] = discount_type
            payload["discount_value"] = discount_value
            payload["discount_amount"] = discount_amount

        self.repo.update(quotation, payload)
        self.db.refresh(quotation)
        return self._to_response(quotation)

    def _get_quotation_for_update(
        self, quotation_id: UUID, organization_id: UUID, data: dict
    ):
        quotation = self.repo.get_by_id(quotation_id, organization_id)
        if not quotation:
            raise ResourceNotFoundException(f"Quotation {quotation_id} not found")

        if "items" in data and quotation.status == QuotationStatus.SENT:
            raise ValueError("Cannot modify line items when quotation status is SENT")

        return quotation

    def _prepare_update_payload(
        self, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        payload = {k: v for k, v in data.items() if v is not None and k != "items"}

        if payload.get("status"):
            payload["status"] = QuotationStatus(payload["status"])

        payload["updated_by"] = user_id

        if "customer_id" in payload:
            self._validate_customer_organization(
                payload["customer_id"], organization_id
            )

        return payload

    def _update_quotation_items(
        self, quotation, items_data: list, organization_id: UUID
    ) -> Decimal:
        for item_data in items_data:
            if "item_id" in item_data:
                self._validate_item_organization(item_data["item_id"], organization_id)

        for item in quotation.items:
            self.db.delete(item)

        customer = quotation.customer
        shipping_address = self._get_shipping_address(customer)

        grand_total = Decimal("0")
        for item_data in items_data:
            item_payload = self._build_quotation_item_payload(
                item_data, quotation.id, organization_id, shipping_address
            )
            grand_total += item_payload["total_amount"]
            item = QuotationItem(**item_payload)
            self.db.add(item)

        return grand_total

    def _get_shipping_address(self, customer) -> dict | None:
        return (
            {
                "city": customer.city,
                "state": customer.state,
                "country": customer.country,
            }
            if customer and (customer.city or customer.state or customer.country)
            else None
        )

    def delete(self, quotation_id: UUID, organization_id: UUID) -> None:
        quotation = self.repo.get_by_id(quotation_id, organization_id)
        if not quotation:
            raise ResourceNotFoundException(f"Quotation {quotation_id} not found")
        self.repo.delete(quotation)

    def update_status(
        self, quotation_id: UUID, new_status: str, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Update quotation status with validation.

        Args:
            quotation_id: ID of the quotation to update
            new_status: New status value (string)
            organization_id: Organization ID for multi-tenancy
            user_id: User ID for audit trail

        Returns:
            Updated quotation as dict

        Raises:
            ResourceNotFoundException: If quotation not found
            ValueError: If status transition is invalid
        """
        quotation = self.repo.get_by_id(quotation_id, organization_id)
        if not quotation:
            raise ResourceNotFoundException(f"Quotation {quotation_id} not found")

        # Convert string to enum
        new_status_enum = QuotationStatus(new_status)

        # Validate status transition
        self._validate_status_transition(quotation.status, new_status_enum)

        # Prepare update payload
        payload = {
            "status": new_status_enum,
            "updated_by": user_id,
        }

        # Set submitted_at when status changes to SENT
        if new_status_enum == QuotationStatus.SENT and quotation.submitted_at is None:
            from datetime import UTC, datetime

            payload["submitted_at"] = datetime.now(UTC)

        # Update quotation
        self.repo.update(quotation, payload)
        self.db.refresh(quotation)
        return self._to_response(quotation)

    @staticmethod
    def _compute_discount_amount(
        amount: Decimal,
        discount_type: str,
        discount_value: Decimal,
    ) -> Decimal:
        """Compute discount amount from type and value. Tax is applied on (amount - discount_amount)."""
        if discount_value <= 0:
            return Decimal("0")
        if discount_type == "percentage":
            return (amount * discount_value / 100).quantize(Decimal("0.01"))
        # flat
        return min(discount_value, amount)

    @staticmethod
    def _compute_document_discount(
        subtotal: Decimal,
        discount_type: str,
        discount_value: Decimal,
    ) -> Decimal:
        """Compute document-level discount amount from type and value applied to subtotal."""
        if discount_value <= 0:
            return Decimal("0")
        if (discount_type or "percentage").lower() == "percentage":
            return (subtotal * discount_value / 100).quantize(Decimal("0.01"))
        return min(discount_value, subtotal)

    def _build_quotation_item_payload(
        self,
        item_data: dict,
        quotation_id: UUID,
        organization_id: UUID,
        shipping_address: dict | None = None,
    ) -> dict:
        """Build quotation item payload with amount, discount, and tax calculation.
        Order: amount = qty*rate, discount on amount, tax on (amount - discount_amount), total = net + tax.
        """
        qty = Decimal(str(item_data.get("qty", 0)))
        rate = Decimal(str(item_data.get("rate", 0)))
        amount = qty * rate
        discount_type = (item_data.get("discount_type") or "percentage").lower()
        if discount_type not in ("flat", "percentage"):
            discount_type = "percentage"
        discount_value = Decimal(str(item_data.get("discount_value") or 0))
        discount_amount = self._compute_discount_amount(
            amount, discount_type, discount_value
        )
        net_amount = amount - discount_amount

        item_payload = {
            "organization_id": organization_id,
            "quotation_id": quotation_id,
            "item_id": item_data["item_id"],
            "qty": qty,
            "uom": item_data.get("uom", "Nos"),
            "rate": rate,
            "amount": amount,
            "sort_order": item_data.get("sort_order", 0),
            "discount_type": discount_type,
            "discount_value": discount_value,
            "discount_amount": discount_amount,
            "tax_template_id": None,
            "tax_rate": Decimal("0"),
            "tax_amount": Decimal("0"),
            "total_amount": net_amount,
        }

        # Tax is applied on net amount (after discount)
        item = (
            self.db.query(Item)
            .filter(
                Item.id == item_data["item_id"],
                Item.organization_id == organization_id,
            )
            .first()
        )

        if item and net_amount > 0:
            tax_result = self.tax_engine.calculate_taxes(
                [
                    LineItem(
                        item_id=item.id,
                        qty=qty,
                        rate=rate,
                        amount=net_amount,
                        is_tax_exempt=False,
                        item_group_id=item.item_group_id,
                    )
                ],
                TaxContext(
                    organization_id=organization_id,
                    transaction_type="Sales",
                    item_id=item.id,
                    item_group_id=item.item_group_id,
                    shipping_address=shipping_address,
                    customer_location=shipping_address,
                ),
            )

            if tax_result.total_tax > 0 and tax_result.tax_breakdown:
                first_entry = tax_result.tax_breakdown[0]
                item_payload["tax_template_id"] = first_entry.tax_template_id
                item_payload["tax_amount"] = tax_result.total_tax
                item_payload["tax_rate"] = (
                    (tax_result.total_tax / net_amount * 100)
                    if net_amount
                    else Decimal("0")
                )
                item_payload["total_amount"] = net_amount + tax_result.total_tax

        # Allow override from request (e.g. explicit tax_template_id or pre-calculated totals)
        if item_data.get("tax_template_id"):
            item_payload["tax_template_id"] = item_data["tax_template_id"]
        if "tax_rate" in item_data and item_data["tax_rate"] is not None:
            item_payload["tax_rate"] = Decimal(str(item_data["tax_rate"]))
        if "tax_amount" in item_data and item_data["tax_amount"] is not None:
            item_payload["tax_amount"] = Decimal(str(item_data["tax_amount"]))
        if "total_amount" in item_data and item_data["total_amount"] is not None:
            item_payload["total_amount"] = Decimal(str(item_data["total_amount"]))
        if "discount_amount" in item_data and item_data["discount_amount"] is not None:
            item_payload["discount_amount"] = Decimal(str(item_data["discount_amount"]))

        return item_payload

    def convert_to_sales_order(
        self, quotation_id: UUID, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Convert an accepted quotation to a sales order.

        Args:
            quotation_id: ID of the quotation to convert
            organization_id: Organization ID for multi-tenancy
            user_id: User ID for audit trail

        Returns:
            Created sales order as dict

        Raises:
            ResourceNotFoundException: If quotation not found
            ValueError: If quotation status is not ACCEPTED
        """
        from datetime import UTC, datetime

        from app.services.sales_order_service import SalesOrderService

        # Get the quotation
        quotation = self.repo.get_by_id(quotation_id, organization_id)
        if not quotation:
            raise ResourceNotFoundException(f"Quotation {quotation_id} not found")

        # Validate quotation status is ACCEPTED
        if quotation.status != QuotationStatus.ACCEPTED:
            raise ValueError(
                f"Cannot convert quotation with status {quotation.status.value}. "
                "Only ACCEPTED quotations can be converted to sales orders."
            )

        # Use database transaction for atomicity
        try:
            # Generate sales order number from quotation number
            # Replace QTN prefix with SO prefix, or generate new number
            if quotation.quotation_no.startswith("QTN"):
                sales_order_no = quotation.quotation_no.replace("QTN", "SO", 1)
            else:
                # Fallback: generate based on timestamp
                timestamp = datetime.now(UTC).strftime("%Y%m%d%H%M%S")
                sales_order_no = f"SO-{timestamp}"

            # Prepare sales order data (carry forward document-level discount from quotation)
            sales_order_data = {
                "sales_order_no": sales_order_no,
                "customer_id": quotation.customer_id,
                "order_date": datetime.now(UTC),
                "delivery_date": None,
                "currency": quotation.currency,
                "reference_type": "Quotation",
                "reference_id": quotation.id,
                "remarks": quotation.remarks,
                "discount_type": getattr(quotation, "discount_type", None)
                or "percentage",
                "discount_value": getattr(quotation, "discount_value", None) or 0,
                "discount_amount": getattr(quotation, "discount_amount", None) or 0,
                "items": [
                    {
                        "item_id": item.item_id,
                        "qty": item.qty,
                        "uom": item.uom,
                        "rate": item.rate,
                        "amount": item.amount,
                        "sort_order": item.sort_order,
                        "discount_type": getattr(item, "discount_type", None)
                        or "percentage",
                        "discount_value": getattr(item, "discount_value", None) or 0,
                        "discount_amount": getattr(item, "discount_amount", None) or 0,
                        "tax_template_id": item.tax_template_id,
                        "tax_rate": item.tax_rate,
                        "tax_amount": item.tax_amount,
                        "total_amount": item.total_amount,
                    }
                    for item in quotation.items
                ],
            }

            # Create sales order using SalesOrderService
            sales_order_service = SalesOrderService(self.db)
            sales_order = sales_order_service.create(
                sales_order_data, organization_id, user_id
            )

            # Mark quotation as converted to sales order
            self.repo.update(quotation, {"converted_to_sales_order": True})
            self.db.commit()

            return sales_order

        except Exception as e:
            # Rollback is handled by the session
            self.db.rollback()
            raise e

    def _validate_status_transition(
        self, current_status: QuotationStatus, new_status: QuotationStatus
    ) -> None:
        """
        Validate quotation status transitions.

        Valid workflow: DRAFT → SENT → ACCEPTED/REJECTED/EXPIRED
        Terminal states (ACCEPTED, REJECTED, EXPIRED) cannot transition further.

        Args:
            current_status: Current quotation status
            new_status: Requested new status

        Raises:
            ValueError: If the status transition is invalid
        """
        # Terminal states cannot transition
        terminal_states = {
            QuotationStatus.ACCEPTED,
            QuotationStatus.REJECTED,
            QuotationStatus.EXPIRED,
        }
        if current_status in terminal_states:
            raise ValueError(
                f"Cannot change status from terminal state {current_status.value}"
            )

        # Define valid transitions
        valid_transitions = {
            QuotationStatus.DRAFT: {QuotationStatus.SENT},
            QuotationStatus.SENT: {
                QuotationStatus.ACCEPTED,
                QuotationStatus.REJECTED,
                QuotationStatus.EXPIRED,
            },
        }

        # Check if transition is valid
        allowed_next_states = valid_transitions.get(current_status, set())
        if new_status not in allowed_next_states:
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status.value}. "
                f"Allowed transitions: {', '.join(s.value for s in allowed_next_states)}"
            )

    def _validate_customer_organization(
        self, customer_id: UUID, organization_id: UUID
    ) -> None:
        """
        Validate that customer_id belongs to the same organization_id.

        Args:
            customer_id: Customer ID to validate
            organization_id: Expected organization ID

        Raises:
            ValueError: If customer doesn't exist or belongs to different organization
        """
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()

        if not customer:
            raise ValueError(f"Customer {customer_id} not found")

        if customer.organization_id != organization_id:
            raise ValueError(
                f"Customer {customer_id} belongs to a different organization"
            )

    def _validate_item_organization(self, item_id: UUID, organization_id: UUID) -> None:
        """
        Validate that item_id belongs to the same organization_id.

        Args:
            item_id: Item ID to validate
            organization_id: Expected organization ID

        Raises:
            ValueError: If item doesn't exist or belongs to different organization
        """
        item = self.db.query(Item).filter(Item.id == item_id).first()

        if not item:
            raise ValueError(f"Item {item_id} not found")

        if item.organization_id != organization_id:
            raise ValueError(f"Item {item_id} belongs to a different organization")

    def _get_item_details(self, item: QuotationItem, organization_id: UUID) -> dict:
        """Get comprehensive item details including stock levels, item group, and tax info."""
        if not item.item:
            return {
                "item_code": None,
                "item_name": None,
                "uom": item.uom,
                "min_order_qty": 1,
                "max_order_qty": None,
                "standard_rate": "0.00",
                "stock_levels": {
                    "quantity_on_hand": 0,
                    "quantity_reserved": 0,
                    "quantity_available": 0,
                },
                "item_group": None,
                "tax_info": None,
            }

        # Get stock levels
        stock_agg = self.stock_level_repo.get_aggregated_by_products(
            product_ids=[item.item.id],
            organization_id=organization_id,
        )
        stock = stock_agg.get(
            item.item.id,
            {"quantity_on_hand": 0, "quantity_reserved": 0, "quantity_available": 0},
        )

        # Build item group data
        item_group = None
        if item.item.item_group:
            item_group = {
                "id": item.item.item_group.id,
                "name": item.item.item_group.name,
                "code": item.item.item_group.code,
            }

        # Build tax info from the applied tax template
        tax_info = None
        if item.tax_template_id:
            tax_result = self.tax_template_repo.get_applicable_template(
                organization_id=organization_id,
                transaction_type="Sales",
                item_id=item.item.id,
                item_group_id=item.item.item_group_id,
            )
            if tax_result:
                template, _ = tax_result
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
                    "id": template.id,
                    "template_name": template.template_name,
                    "template_code": template.template_code,
                    "is_compound": is_compound,
                    "breakup": breakup,
                }

        return {
            "item_code": item.item.item_code,
            "item_name": item.item.item_name,
            "uom": item.item.uom or "Nos",
            "min_order_qty": item.item.min_order_qty or 1,
            "max_order_qty": item.item.max_order_qty,
            "standard_rate": str(item.item.standard_rate or "0.00"),
            "stock_levels": stock,
            "item_group": item_group,
            "tax_info": tax_info,
        }

    def _to_response(self, quotation) -> dict:
        customer = quotation.customer
        return {
            "id": quotation.id,
            "organization_id": quotation.organization_id,
            "quotation_no": quotation.quotation_no,
            "customer_id": quotation.customer_id,
            "customer": {
                "id": customer.id,
                "name": customer.customer_name,
                "code": customer.customer_code,
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
            }
            if customer
            else None,
            "quotation_date": quotation.quotation_date,
            "valid_until": quotation.valid_until,
            "status": quotation.status.value if quotation.status else None,
            "grand_total": quotation.grand_total,
            "currency": quotation.currency,
            "remarks": quotation.remarks,
            "discount_type": getattr(quotation, "discount_type", None) or "percentage",
            "discount_value": getattr(quotation, "discount_value", None) or 0,
            "discount_amount": getattr(quotation, "discount_amount", None) or 0,
            "converted_to_sales_order": quotation.converted_to_sales_order,
            "submitted_at": quotation.submitted_at,
            "extra_data": quotation.extra_data,
            "created_by": quotation.created_by,
            "updated_by": quotation.updated_by,
            "created_at": quotation.created_at,
            "updated_at": quotation.updated_at,
            "items": [
                {
                    "id": item.id,
                    "organization_id": item.organization_id,
                    "quotation_id": item.quotation_id,
                    "item_id": item.item_id,
                    "qty": item.qty,
                    "uom": item.uom,
                    "rate": item.rate,
                    "amount": item.amount,
                    "sort_order": item.sort_order,
                    "discount_type": getattr(item, "discount_type", None)
                    or "percentage",
                    "discount_value": getattr(item, "discount_value", None) or 0,
                    "discount_amount": getattr(item, "discount_amount", None) or 0,
                    "tax_template_id": item.tax_template_id,
                    "tax_rate": item.tax_rate,
                    "tax_amount": item.tax_amount,
                    "total_amount": item.total_amount,
                    "extra_data": item.extra_data,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                    **self._get_item_details(item, quotation.organization_id),
                }
                for item in quotation.items
            ],
        }

    @staticmethod
    def _to_list_item(quotation) -> dict:
        customer = quotation.customer
        return {
            "id": quotation.id,
            "organization_id": quotation.organization_id,
            "quotation_no": quotation.quotation_no,
            "customer": {
                "id": customer.id,
                "name": customer.customer_name,
                "code": customer.customer_code,
            }
            if customer
            else None,
            "quotation_date": quotation.quotation_date,
            "valid_until": quotation.valid_until,
            "status": quotation.status.value if quotation.status else None,
            "grand_total": quotation.grand_total,
            "currency": quotation.currency,
            "discount_type": getattr(quotation, "discount_type", None),
            "discount_value": getattr(quotation, "discount_value", None),
            "discount_amount": getattr(quotation, "discount_amount", None),
            "converted_to_sales_order": quotation.converted_to_sales_order,
            "created_at": quotation.created_at,
        }
