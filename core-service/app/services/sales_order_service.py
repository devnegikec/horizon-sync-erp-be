"""Sales Order service"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import SalesOrderStatus
from app.models.sales_order import SalesOrderItem
from app.repositories.sales_order_repository import SalesOrderRepository


class SalesOrderService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SalesOrderRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = dict(data)
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id

        # Handle status enum conversion
        if payload.get("status"):
            payload["status"] = SalesOrderStatus(payload["status"])

        # Extract items and calculate grand_total
        items_data = payload.pop("items", [])
        grand_total = self._calculate_grand_total(items_data)
        payload["grand_total"] = grand_total

        # Create sales order
        sales_order = self.repo.create(payload)

        # Create sales order items
        for item_data in items_data:
            item_payload = dict(item_data)
            item_payload["organization_id"] = organization_id
            item_payload["sales_order_id"] = sales_order.id
            # Calculate amount as qty * rate
            item_payload["amount"] = Decimal(str(item_payload["qty"])) * Decimal(
                str(item_payload["rate"])
            )
            # Initialize billed_qty and delivered_qty to 0
            item_payload["billed_qty"] = Decimal("0")
            item_payload["delivered_qty"] = Decimal("0")
            item = SalesOrderItem(**item_payload)
            self.db.add(item)

        self.db.commit()
        self.db.refresh(sales_order)
        return self._to_response(sales_order)

    def get_by_id(self, sales_order_id: UUID, organization_id: UUID) -> dict:
        sales_order = self.repo.get_by_id_with_items(sales_order_id, organization_id)
        if not sales_order:
            raise ResourceNotFoundException(f"Sales Order {sales_order_id} not found")
        return self._to_response(sales_order)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        customer_id: UUID | None = None,
        status: str | None = None,
        sort_by: str = "order_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_sales_orders(
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
        self, sales_order_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        sales_order = self.repo.get_by_id_with_items(sales_order_id, organization_id)
        if not sales_order:
            raise ResourceNotFoundException(f"Sales Order {sales_order_id} not found")

        payload = {k: v for k, v in data.items() if v is not None and k != "items"}

        # Handle status enum conversion
        if payload.get("status"):
            payload["status"] = SalesOrderStatus(payload["status"])

        payload["updated_by"] = user_id

        # Handle items update if provided
        if "items" in data:
            items_data = data["items"]

            # Delete existing items
            for item in sales_order.items:
                self.db.delete(item)

            # Create new items
            for item_data in items_data:
                item_payload = dict(item_data)
                item_payload["organization_id"] = organization_id
                item_payload["sales_order_id"] = sales_order.id
                # Calculate amount as qty * rate
                item_payload["amount"] = Decimal(str(item_payload["qty"])) * Decimal(
                    str(item_payload["rate"])
                )
                # Initialize billed_qty and delivered_qty to 0 if not provided
                if "billed_qty" not in item_payload:
                    item_payload["billed_qty"] = Decimal("0")
                if "delivered_qty" not in item_payload:
                    item_payload["delivered_qty"] = Decimal("0")
                item = SalesOrderItem(**item_payload)
                self.db.add(item)

            # Recalculate grand_total
            payload["grand_total"] = self._calculate_grand_total(items_data)

        self.repo.update(sales_order, payload)
        self.db.refresh(sales_order)
        return self._to_response(sales_order)

    def delete(self, sales_order_id: UUID, organization_id: UUID) -> None:
        sales_order = self.repo.get_by_id(sales_order_id, organization_id)
        if not sales_order:
            raise ResourceNotFoundException(f"Sales Order {sales_order_id} not found")
        self.repo.delete(sales_order)

    def update_status(
        self,
        sales_order_id: UUID,
        new_status: str,
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """Update sales order status with validation

        Args:
            sales_order_id: ID of the sales order to update
            new_status: New status value (string)
            organization_id: Organization ID for multi-tenancy
            user_id: User ID for audit trail

        Returns:
            Updated sales order as dict

        Raises:
            ResourceNotFoundException: If sales order not found
            ValueError: If status transition is invalid
        """
        sales_order = self.repo.get_by_id_with_items(sales_order_id, organization_id)
        if not sales_order:
            raise ResourceNotFoundException(f"Sales Order {sales_order_id} not found")

        # Convert string to enum
        new_status_enum = SalesOrderStatus(new_status)

        # Validate status transition
        self._validate_status_transition(sales_order.status, new_status_enum)

        # Prepare update payload
        payload = {
            "status": new_status_enum,
            "updated_by": user_id,
        }

        # Set submitted_at when status changes to CONFIRMED
        if (
            new_status_enum == SalesOrderStatus.CONFIRMED
            and sales_order.submitted_at is None
        ):
            from datetime import UTC, datetime

            payload["submitted_at"] = datetime.now(UTC)

        # Update the sales order
        self.repo.update(sales_order, payload)
        self.db.refresh(sales_order)
        return self._to_response(sales_order)

    def convert_to_invoice(
        self,
        sales_order_id: UUID,
        items_to_bill: list[dict],
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """Convert sales order to invoice with partial billing support

        Args:
            sales_order_id: ID of the sales order to convert
            items_to_bill: List of dicts with item_id and qty_to_bill for each item
            organization_id: Organization ID for multi-tenancy
            user_id: User ID for audit trail

        Returns:
            Created invoice as dict

        Raises:
            ResourceNotFoundException: If sales order not found
            ValueError: If billing quantities exceed pending_billing_qty
        """
        from datetime import UTC, datetime

        from app.models.base import InvoiceStatus, InvoiceType
        from app.models.invoice import Invoice

        # Get sales order with items
        sales_order = self.repo.get_by_id_with_items(sales_order_id, organization_id)
        if not sales_order:
            raise ResourceNotFoundException(f"Sales Order {sales_order_id} not found")

        # Validate billing quantities
        self._validate_billing_quantities(sales_order, items_to_bill)

        # Use database transaction for atomicity
        try:
            # Create invoice
            invoice_data = {
                "organization_id": organization_id,
                "invoice_no": f"INV-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",  # Temporary, should use sequence
                "invoice_type": InvoiceType.SALES,
                "party_id": sales_order.customer_id,
                "party_type": "Customer",
                "posting_date": datetime.now(UTC),
                "status": InvoiceStatus.DRAFT,
                "currency": sales_order.currency,
                "reference_type": "Sales Order",
                "reference_id": sales_order.id,
                "remarks": sales_order.remarks,
                "created_by": user_id,
                "updated_by": user_id,
            }

            # Calculate grand_total from items_to_bill
            grand_total = Decimal("0")
            for item_to_bill in items_to_bill:
                # Find the corresponding sales order item
                so_item = next(
                    (
                        item
                        for item in sales_order.items
                        if item.id == item_to_bill["item_id"]
                    ),
                    None,
                )
                if so_item:
                    qty_to_bill = Decimal(str(item_to_bill["qty_to_bill"]))
                    grand_total += qty_to_bill * so_item.rate

            invoice_data["grand_total"] = grand_total
            invoice_data["outstanding_amount"] = grand_total

            # Create invoice
            invoice = Invoice(**invoice_data)
            self.db.add(invoice)
            self.db.flush()  # Flush to get invoice ID

            # Update sales_order_item.billed_qty for each billed item
            self._update_billed_quantities(sales_order, items_to_bill)

            # Commit transaction
            self.db.commit()
            self.db.refresh(invoice)

            # Return invoice response
            return {
                "id": invoice.id,
                "organization_id": invoice.organization_id,
                "invoice_no": invoice.invoice_no,
                "invoice_type": invoice.invoice_type.value,
                "party_id": invoice.party_id,
                "party_type": invoice.party_type,
                "posting_date": invoice.posting_date,
                "due_date": invoice.due_date,
                "status": invoice.status.value,
                "grand_total": invoice.grand_total,
                "outstanding_amount": invoice.outstanding_amount,
                "currency": invoice.currency,
                "reference_type": invoice.reference_type,
                "reference_id": invoice.reference_id,
                "remarks": invoice.remarks,
                "submitted_at": invoice.submitted_at,
                "created_by": invoice.created_by,
                "updated_by": invoice.updated_by,
                "created_at": invoice.created_at,
                "updated_at": invoice.updated_at,
            }

        except Exception as e:
            self.db.rollback()
            raise e

    def _validate_status_transition(
        self, current_status: SalesOrderStatus, new_status: SalesOrderStatus
    ) -> None:
        """Validate status transition according to workflow rules

        Workflow: DRAFT → CONFIRMED → PARTIALLY_DELIVERED → DELIVERED → CLOSED
        CANCELLED allowed from any state except CLOSED

        Args:
            current_status: Current status of the sales order
            new_status: Requested new status

        Raises:
            ValueError: If the status transition is not allowed
        """
        # No transition needed if status is the same
        if current_status == new_status:
            return

        # CANCELLED can be set from any state except CLOSED
        if new_status == SalesOrderStatus.CANCELLED:
            if current_status == SalesOrderStatus.CLOSED:
                raise ValueError("Cannot cancel a sales order that is already CLOSED")
            return

        # Cannot transition from CANCELLED or CLOSED to any other status
        if current_status in (SalesOrderStatus.CANCELLED, SalesOrderStatus.CLOSED):
            raise ValueError(
                f"Cannot transition from {current_status.value} to {new_status.value}"
            )

        # Define valid transitions for the main workflow
        valid_transitions = {
            SalesOrderStatus.DRAFT: [SalesOrderStatus.CONFIRMED],
            SalesOrderStatus.CONFIRMED: [
                SalesOrderStatus.PARTIALLY_DELIVERED,
                SalesOrderStatus.DELIVERED,
            ],
            SalesOrderStatus.PARTIALLY_DELIVERED: [SalesOrderStatus.DELIVERED],
            SalesOrderStatus.DELIVERED: [SalesOrderStatus.CLOSED],
        }

        allowed_next_statuses = valid_transitions.get(current_status, [])

        if new_status not in allowed_next_statuses:
            raise ValueError(
                f"Invalid status transition from {current_status.value} to {new_status.value}. "
                f"Allowed transitions: {', '.join(s.value for s in allowed_next_statuses)}"
            )

    def _validate_billing_quantities(
        self, sales_order, items_to_bill: list[dict]
    ) -> None:
        """Validate that billing quantities don't exceed pending_billing_qty

        Args:
            sales_order: SalesOrder object with items
            items_to_bill: List of dicts with item_id and qty_to_bill

        Raises:
            ValueError: If any billing quantity exceeds pending_billing_qty
        """
        for item_to_bill in items_to_bill:
            item_id = item_to_bill["item_id"]
            qty_to_bill = Decimal(str(item_to_bill["qty_to_bill"]))

            # Find the corresponding sales order item
            so_item = next(
                (item for item in sales_order.items if item.id == item_id), None
            )

            if not so_item:
                raise ValueError(
                    f"Item {item_id} not found in sales order {sales_order.id}"
                )

            # Calculate pending_billing_qty
            pending_billing_qty = so_item.qty - so_item.billed_qty

            # Validate quantity
            if qty_to_bill > pending_billing_qty:
                raise ValueError(
                    f"Billing quantity {qty_to_bill} exceeds pending billing quantity "
                    f"{pending_billing_qty} for item {item_id}"
                )

            if qty_to_bill <= 0:
                raise ValueError(
                    f"Billing quantity must be greater than 0 for item {item_id}"
                )

    def _update_billed_quantities(self, sales_order, items_to_bill: list[dict]) -> None:
        """Update billed_qty for each billed item

        Args:
            sales_order: SalesOrder object with items
            items_to_bill: List of dicts with item_id and qty_to_bill
        """
        for item_to_bill in items_to_bill:
            item_id = item_to_bill["item_id"]
            qty_to_bill = Decimal(str(item_to_bill["qty_to_bill"]))

            # Find the corresponding sales order item
            so_item = next(
                (item for item in sales_order.items if item.id == item_id), None
            )

            if so_item:
                so_item.billed_qty += qty_to_bill

    def _calculate_grand_total(self, items: list[dict]) -> Decimal:
        """Calculate grand total from line items"""
        total = Decimal("0")
        for item in items:
            qty = Decimal(str(item.get("qty", 0)))
            rate = Decimal(str(item.get("rate", 0)))
            total += qty * rate
        return total

    def _to_response(self, sales_order) -> dict:
        """Convert sales order to response dict with pending quantities"""
        return {
            "id": sales_order.id,
            "organization_id": sales_order.organization_id,
            "sales_order_no": sales_order.sales_order_no,
            "customer_id": sales_order.customer_id,
            "order_date": sales_order.order_date,
            "delivery_date": sales_order.delivery_date,
            "status": sales_order.status.value if sales_order.status else None,
            "grand_total": sales_order.grand_total,
            "currency": sales_order.currency,
            "reference_type": sales_order.reference_type,
            "reference_id": sales_order.reference_id,
            "remarks": sales_order.remarks,
            "submitted_at": sales_order.submitted_at,
            "extra_data": sales_order.extra_data,
            "created_by": sales_order.created_by,
            "updated_by": sales_order.updated_by,
            "created_at": sales_order.created_at,
            "updated_at": sales_order.updated_at,
            "items": [
                {
                    "id": item.id,
                    "item_id": item.item_id,
                    "qty": item.qty,
                    "uom": item.uom,
                    "rate": item.rate,
                    "amount": item.amount,
                    "billed_qty": item.billed_qty,
                    "delivered_qty": item.delivered_qty,
                    "pending_billing_qty": item.qty - item.billed_qty,
                    "pending_delivery_qty": item.qty - item.delivered_qty,
                    "sort_order": item.sort_order,
                    "extra_data": item.extra_data,
                }
                for item in sales_order.items
            ],
        }

    @staticmethod
    def _to_list_item(sales_order) -> dict:
        """Convert sales order to list item dict"""
        return {
            "id": sales_order.id,
            "organization_id": sales_order.organization_id,
            "sales_order_no": sales_order.sales_order_no,
            "customer_id": sales_order.customer_id,
            "order_date": sales_order.order_date,
            "status": sales_order.status.value if sales_order.status else None,
            "grand_total": sales_order.grand_total,
            "currency": sales_order.currency,
            "created_at": sales_order.created_at,
        }
