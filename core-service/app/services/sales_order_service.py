"""Sales Order service"""

import uuid
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import SalesOrderStatus
from app.models.customer import Customer
from app.models.item import Item
from app.models.sales_order import SalesOrderItem
from app.repositories.sales_order_repository import SalesOrderRepository
from app.repositories.stock_level_repository import StockLevelRepository
from app.repositories.tax_template_repository import TaxTemplateRepository
from app.services.tax_calculation_engine import (
    LineItem,
    TaxCalculationEngine,
    TaxContext,
)


class SalesOrderService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SalesOrderRepository(db)
        self.stock_level_repo = StockLevelRepository(db)
        self.tax_template_repo = TaxTemplateRepository(db)
        self.tax_engine = TaxCalculationEngine(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = dict(data)
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id

        # Handle status enum conversion
        if payload.get("status"):
            payload["status"] = SalesOrderStatus(payload["status"])

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

        # Create sales order first (we need sales_order.id for item payloads)
        sales_order = self.repo.create(payload)

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

        grand_total = Decimal("0")
        for item_data in items_data:
            item_payload = self._build_sales_order_item_payload(
                item_data, sales_order.id, organization_id, shipping_address
            )
            grand_total += item_payload["total_amount"]
            item = SalesOrderItem(**item_payload)
            self.db.add(item)

        self.repo.update(sales_order, {"grand_total": grand_total})

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

        # Validate customer_id if being updated
        if "customer_id" in payload:
            self._validate_customer_organization(
                payload["customer_id"], organization_id
            )

        # Handle items update if provided
        if "items" in data:
            items_data = data["items"]

            # Validate item_id in line items belongs to same organization
            for item_data in items_data:
                if "item_id" in item_data:
                    self._validate_item_organization(
                        item_data["item_id"], organization_id
                    )

            # Delete existing items
            for item in sales_order.items:
                self.db.delete(item)

            customer = sales_order.customer
            shipping_address = (
                {
                    "city": customer.city,
                    "state": customer.state,
                    "country": customer.country,
                }
                if customer and (customer.city or customer.state or customer.country)
                else None
            )

            # Create new items
            for item_data in items_data:
                item_payload = self._build_sales_order_item_payload(
                    item_data, sales_order.id, organization_id, shipping_address
                )
                item = SalesOrderItem(**item_payload)
                self.db.add(item)

            # Recalculate grand_total from built item payloads
            grand_total = Decimal("0")
            for item_data in items_data:
                item_payload = self._build_sales_order_item_payload(
                    item_data, sales_order.id, organization_id, shipping_address
                )
                grand_total += item_payload["total_amount"]
            payload["grand_total"] = grand_total

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

        # Validate status transition (pass sales_order for CLOSED status validation)
        self._validate_status_transition(
            sales_order.status, new_status_enum, sales_order
        )

        # If confirming the order, reserve stock and split items across warehouses
        if (
            new_status_enum == SalesOrderStatus.CONFIRMED
            and sales_order.status == SalesOrderStatus.DRAFT
        ):
            self._reserve_stock_and_split_items(sales_order, organization_id, user_id)

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

    def _reserve_stock_and_split_items(
        self, sales_order, organization_id: UUID, user_id: UUID
    ) -> None:
        """Reserve stock and split sales order items across warehouses when confirming.

        For each SO item, queries stock_levels ordered by quantity_available DESC
        and splits the required qty across warehouses. Creates multiple sales_order_items
        entries if an item needs to be fulfilled from multiple warehouses.

        Updates stock_levels: quantity_reserved++, quantity_available--

        Args:
            sales_order: SalesOrder object with items
            organization_id: Organization ID
            user_id: User ID for audit trail

        Raises:
            ValidationError: If insufficient stock available
        """
        from decimal import Decimal

        from app.core.exceptions import ValidationError
        from app.models.item import Item
        from app.models.sales_order import SalesOrderItem
        from app.models.stock_level import StockLevel
        from app.models.warehouse import Warehouse

        # Collect original items to process
        original_items = list(sales_order.items)

        # Track new items to add
        new_items_to_add = []

        # Process each original item
        for so_item in original_items:
            remaining_qty = so_item.qty

            # Fetch stock levels ordered by availability (richest first)
            stock_rows = (
                self.db.query(StockLevel)
                .filter(
                    StockLevel.product_id == so_item.item_id,
                    StockLevel.organization_id == organization_id,
                    StockLevel.quantity_available > 0,
                )
                .order_by(StockLevel.quantity_available.desc())
                .all()
            )

            if not stock_rows:
                raise ValidationError(
                    f"No stock available for item {so_item.item_id}"
                )

            # Calculate total available stock
            total_available = sum(sl.quantity_available for sl in stock_rows)
            if total_available < int(remaining_qty):
                item = self.db.query(Item).filter(Item.id == so_item.item_id).first()
                item_name = item.item_name if item else str(so_item.item_id)
                raise ValidationError(
                    f"Insufficient stock for item {item_name}: "
                    f"required={int(remaining_qty)}, available={total_available}"
                )

            # Split across warehouses
            allocations = []
            for sl in stock_rows:
                if remaining_qty <= 0:
                    break

                alloc_qty = min(Decimal(str(sl.quantity_available)), remaining_qty)
                allocations.append(
                    {
                        "warehouse_id": sl.warehouse_id,
                        "qty": alloc_qty,
                    }
                )
                remaining_qty -= alloc_qty

            # If only one warehouse, update the existing item with warehouse_id
            if len(allocations) == 1:
                # Add warehouse_id to extra_data
                if so_item.extra_data is None:
                    so_item.extra_data = {}
                so_item.extra_data["warehouse_id"] = str(allocations[0]["warehouse_id"])

                # Reserve stock
                sl = (
                    self.db.query(StockLevel)
                    .filter(
                        StockLevel.product_id == so_item.item_id,
                        StockLevel.warehouse_id == allocations[0]["warehouse_id"],
                        StockLevel.organization_id == organization_id,
                    )
                    .with_for_update()
                    .first()
                )
                qty_int = int(allocations[0]["qty"])
                sl.quantity_reserved = (sl.quantity_reserved or 0) + qty_int
                sl.quantity_available = (sl.quantity_available or 0) - qty_int

            # If multiple warehouses, create additional items
            else:
                # Update the first allocation on the existing item
                first_alloc = allocations[0]
                if so_item.extra_data is None:
                    so_item.extra_data = {}
                so_item.extra_data["warehouse_id"] = str(first_alloc["warehouse_id"])

                # Adjust qty, amount, tax_amount, total_amount proportionally
                proportion = first_alloc["qty"] / so_item.qty
                so_item.qty = first_alloc["qty"]
                so_item.amount = so_item.rate * first_alloc["qty"]
                so_item.tax_amount = so_item.tax_amount * proportion if so_item.tax_amount else Decimal("0")
                so_item.total_amount = so_item.amount + so_item.tax_amount

                # Reserve stock for first allocation
                sl = (
                    self.db.query(StockLevel)
                    .filter(
                        StockLevel.product_id == so_item.item_id,
                        StockLevel.warehouse_id == first_alloc["warehouse_id"],
                        StockLevel.organization_id == organization_id,
                    )
                    .with_for_update()
                    .first()
                )
                qty_int = int(first_alloc["qty"])
                sl.quantity_reserved = (sl.quantity_reserved or 0) + qty_int
                sl.quantity_available = (sl.quantity_available or 0) - qty_int

                # Create new items for remaining allocations
                for alloc in allocations[1:]:
                    proportion = alloc["qty"] / (so_item.qty + sum(a["qty"] for a in allocations[1:]))
                    new_item = SalesOrderItem(
                        id=uuid.uuid4(),
                        organization_id=organization_id,
                        sales_order_id=sales_order.id,
                        item_id=so_item.item_id,
                        qty=alloc["qty"],
                        uom=so_item.uom,
                        rate=so_item.rate,
                        amount=so_item.rate * alloc["qty"],
                        billed_qty=Decimal("0"),
                        delivered_qty=Decimal("0"),
                        sort_order=so_item.sort_order,
                        tax_template_id=so_item.tax_template_id,
                        tax_rate=so_item.tax_rate,
                        tax_amount=(so_item.tax_amount / (so_item.qty / alloc["qty"])) if so_item.tax_amount else Decimal("0"),
                        total_amount=(so_item.rate * alloc["qty"]) + ((so_item.tax_amount / (so_item.qty / alloc["qty"])) if so_item.tax_amount else Decimal("0")),
                        extra_data={"warehouse_id": str(alloc["warehouse_id"])},
                    )
                    new_items_to_add.append(new_item)

                    # Reserve stock for this allocation
                    sl = (
                        self.db.query(StockLevel)
                        .filter(
                            StockLevel.product_id == so_item.item_id,
                            StockLevel.warehouse_id == alloc["warehouse_id"],
                            StockLevel.organization_id == organization_id,
                        )
                        .with_for_update()
                        .first()
                    )
                    qty_int = int(alloc["qty"])
                    sl.quantity_reserved = (sl.quantity_reserved or 0) + qty_int
                    sl.quantity_available = (sl.quantity_available or 0) - qty_int

        # Add new items to the session
        for new_item in new_items_to_add:
            self.db.add(new_item)

        self.db.flush()

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
        self,
        current_status: SalesOrderStatus,
        new_status: SalesOrderStatus,
        sales_order=None,
    ) -> None:
        """Validate status transition according to workflow rules

        Workflow: DRAFT → CONFIRMED → PARTIALLY_DELIVERED → DELIVERED → CLOSED
        CANCELLED allowed from any state except CLOSED
        CLOSED allowed from any state if all items are fully billed

        Args:
            current_status: Current status of the sales order
            new_status: Requested new status
            sales_order: Optional SalesOrder object for additional validation

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

        # Special handling for CLOSED status (Requirement 6.7)
        # Allow transition to CLOSED from any status if all items are fully billed
        if new_status == SalesOrderStatus.CLOSED:
            if sales_order is None:
                raise ValueError(
                    "Cannot validate CLOSED status transition without sales order data"
                )

            # Check if all items are fully billed
            all_items_fully_billed = all(
                item.billed_qty >= item.qty for item in sales_order.items
            )

            if not all_items_fully_billed:
                raise ValueError(
                    "Cannot transition to CLOSED status: not all items are fully billed"
                )

            # If fully billed, allow transition to CLOSED from any status
            return

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

    def convert_to_delivery_note(
        self,
        sales_order_id: UUID,
        items_to_deliver: list[dict],
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """Convert sales order to delivery note with partial delivery support

        Args:
            sales_order_id: ID of the sales order to convert
            items_to_deliver: List of dicts with item_id and qty_to_deliver for each item
            organization_id: Organization ID for multi-tenancy
            user_id: User ID for audit trail

        Returns:
            Created delivery note as dict

        Raises:
            ResourceNotFoundException: If sales order not found
            ValueError: If delivery quantities exceed pending_delivery_qty
        """
        from datetime import UTC, datetime

        from app.models.base import DocumentStatus
        from app.models.delivery_note import DeliveryNote, DeliveryNoteItem

        # Get sales order with items
        sales_order = self.repo.get_by_id_with_items(sales_order_id, organization_id)
        if not sales_order:
            raise ResourceNotFoundException(f"Sales Order {sales_order_id} not found")

        # Validate delivery quantities
        self._validate_delivery_quantities(sales_order, items_to_deliver)

        # Use database transaction for atomicity
        try:
            # Create delivery note
            delivery_note_data = {
                "organization_id": organization_id,
                "delivery_note_no": f"DN-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",  # Temporary, should use sequence
                "customer_id": sales_order.customer_id,
                "delivery_date": datetime.now(UTC),
                "status": DocumentStatus.DRAFT,
                "reference_type": "Sales Order",
                "reference_id": sales_order.id,
                "remarks": sales_order.remarks,
                "created_by": user_id,
                "updated_by": user_id,
            }

            # Create delivery note
            delivery_note = DeliveryNote(**delivery_note_data)
            self.db.add(delivery_note)
            self.db.flush()  # Flush to get delivery note ID

            # Create delivery note items
            for item_to_deliver in items_to_deliver:
                # Find the corresponding sales order item
                so_item = next(
                    (
                        item
                        for item in sales_order.items
                        if item.id == item_to_deliver["item_id"]
                    ),
                    None,
                )
                if so_item:
                    qty_to_deliver = Decimal(str(item_to_deliver["qty_to_deliver"]))

                    dn_item_data = {
                        "organization_id": organization_id,
                        "delivery_note_id": delivery_note.id,
                        "item_id": so_item.item_id,
                        "qty": qty_to_deliver,
                        "uom": so_item.uom,
                        "rate": so_item.rate,
                        "amount": qty_to_deliver * so_item.rate,
                        "sort_order": so_item.sort_order,
                    }

                    dn_item = DeliveryNoteItem(**dn_item_data)
                    self.db.add(dn_item)

            # Update sales_order_item.delivered_qty for each delivered item
            self._update_delivered_quantities(sales_order, items_to_deliver)

            # Update sales order delivery status automatically
            self._check_and_update_delivery_status(sales_order)

            # Commit transaction
            self.db.commit()
            self.db.refresh(delivery_note)

            # Return delivery note response
            return {
                "id": delivery_note.id,
                "organization_id": delivery_note.organization_id,
                "delivery_note_no": delivery_note.delivery_note_no,
                "customer_id": delivery_note.customer_id,
                "delivery_date": delivery_note.delivery_date,
                "status": delivery_note.status.value,
                "reference_type": delivery_note.reference_type,
                "reference_id": delivery_note.reference_id,
                "remarks": delivery_note.remarks,
                "submitted_at": delivery_note.submitted_at,
                "created_by": delivery_note.created_by,
                "updated_by": delivery_note.updated_by,
                "created_at": delivery_note.created_at,
                "updated_at": delivery_note.updated_at,
            }

        except Exception as e:
            self.db.rollback()
            raise e

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

    def _validate_delivery_quantities(
        self, sales_order, items_to_deliver: list[dict]
    ) -> None:
        """Validate that delivery quantities don't exceed pending_delivery_qty

        Args:
            sales_order: SalesOrder object with items
            items_to_deliver: List of dicts with item_id and qty_to_deliver

        Raises:
            ValueError: If any delivery quantity exceeds pending_delivery_qty
        """
        for item_to_deliver in items_to_deliver:
            item_id = item_to_deliver["item_id"]
            qty_to_deliver = Decimal(str(item_to_deliver["qty_to_deliver"]))

            # Find the corresponding sales order item
            so_item = next(
                (item for item in sales_order.items if item.id == item_id), None
            )

            if not so_item:
                raise ValueError(
                    f"Item {item_id} not found in sales order {sales_order.id}"
                )

            # Calculate pending_delivery_qty
            pending_delivery_qty = so_item.qty - so_item.delivered_qty

            # Validate quantity
            if qty_to_deliver > pending_delivery_qty:
                raise ValueError(
                    f"Delivery quantity {qty_to_deliver} exceeds pending delivery quantity "
                    f"{pending_delivery_qty} for item {item_id}"
                )

            if qty_to_deliver <= 0:
                raise ValueError(
                    f"Delivery quantity must be greater than 0 for item {item_id}"
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

        # Check if sales order is fully billed
        self._check_and_update_billing_status(sales_order)

    def _update_delivered_quantities(
        self, sales_order, items_to_deliver: list[dict]
    ) -> None:
        """Update delivered_qty for each delivered item

        Args:
            sales_order: SalesOrder object with items
            items_to_deliver: List of dicts with item_id and qty_to_deliver
        """
        for item_to_deliver in items_to_deliver:
            item_id = item_to_deliver["item_id"]
            qty_to_deliver = Decimal(str(item_to_deliver["qty_to_deliver"]))

            # Find the corresponding sales order item
            so_item = next(
                (item for item in sales_order.items if item.id == item_id), None
            )

            if so_item:
                so_item.delivered_qty += qty_to_deliver

    def _check_and_update_billing_status(self, sales_order) -> None:
        """Check if sales order is fully billed and update status if needed

        After updating billed quantities, this method checks if all items
        have billed_qty equal to qty. If fully billed, the sales order
        becomes eligible for status transition to CLOSED.

        Args:
            sales_order: SalesOrder object with items

        Note:
            This method does not automatically change the status to CLOSED.
            It only ensures the sales order is in a state where CLOSED
            status transition is allowed (per requirement 6.7).
        """
        # Check if all items are fully billed
        all_items_fully_billed = all(
            item.billed_qty >= item.qty for item in sales_order.items
        )

        # If fully billed and not already closed, the order is eligible for closure
        # The actual status change to CLOSED should be done via update_status endpoint
        # This method just ensures the data state allows for that transition
        if all_items_fully_billed:
            # Log or mark that the order is fully billed
            # The status transition validation will allow CLOSED status
            pass

    def _check_and_update_delivery_status(self, sales_order) -> None:
        """Check delivery status and update sales order status automatically

        After updating delivered quantities, this method checks if:
        - All items have delivered_qty = qty → Set status to DELIVERED
        - Some items have delivered_qty > 0 → Set status to PARTIALLY_DELIVERED

        Args:
            sales_order: SalesOrder object with items

        Note:
            This method automatically updates the sales order status based on
            delivery progress (per requirements 7.7 and 7.8).
        """
        # Check if all items are fully delivered
        all_items_fully_delivered = all(
            item.delivered_qty >= item.qty for item in sales_order.items
        )

        # Check if any items are partially delivered
        any_items_delivered = any(item.delivered_qty > 0 for item in sales_order.items)

        # Update status based on delivery progress
        if all_items_fully_delivered:
            # All items fully delivered → DELIVERED status
            sales_order.status = SalesOrderStatus.DELIVERED
        elif any_items_delivered:
            # Some items delivered → PARTIALLY_DELIVERED status
            sales_order.status = SalesOrderStatus.PARTIALLY_DELIVERED

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

    def _build_sales_order_item_payload(
        self,
        item_data: dict,
        sales_order_id: UUID,
        organization_id: UUID,
        shipping_address: dict | None = None,
    ) -> dict:
        """Build sales order item payload with amount and tax calculation."""
        qty = Decimal(str(item_data.get("qty", 0)))
        rate = Decimal(str(item_data.get("rate", 0)))
        amount = qty * rate

        item_payload = {
            "organization_id": organization_id,
            "sales_order_id": sales_order_id,
            "item_id": item_data["item_id"],
            "qty": qty,
            "uom": item_data.get("uom", "Nos"),
            "rate": rate,
            "amount": amount,
            "billed_qty": Decimal("0"),
            "delivered_qty": Decimal("0"),
            "sort_order": item_data.get("sort_order", 0),
            "tax_template_id": None,
            "tax_rate": Decimal("0"),
            "tax_amount": Decimal("0"),
            "total_amount": amount,
        }

        # Calculate tax using applicable template
        item = (
            self.db.query(Item)
            .filter(
                Item.id == item_data["item_id"],
                Item.organization_id == organization_id,
            )
            .first()
        )

        if item:
            tax_result = self.tax_engine.calculate_taxes(
                [
                    LineItem(
                        item_id=item.id,
                        qty=qty,
                        rate=rate,
                        amount=amount,
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
                    (tax_result.total_tax / amount * 100) if amount else Decimal("0")
                )
                item_payload["total_amount"] = amount + tax_result.total_tax

        # Allow override from request (e.g. explicit tax_template_id)
        if item_data.get("tax_template_id"):
            item_payload["tax_template_id"] = item_data["tax_template_id"]
        if "tax_rate" in item_data and item_data["tax_rate"] is not None:
            item_payload["tax_rate"] = Decimal(str(item_data["tax_rate"]))
        if "tax_amount" in item_data and item_data["tax_amount"] is not None:
            item_payload["tax_amount"] = Decimal(str(item_data["tax_amount"]))
        if "total_amount" in item_data and item_data["total_amount"] is not None:
            item_payload["total_amount"] = Decimal(str(item_data["total_amount"]))

        # Keep existing billed_qty and delivered_qty if provided
        if "billed_qty" in item_data and item_data["billed_qty"] is not None:
            item_payload["billed_qty"] = Decimal(str(item_data["billed_qty"]))
        if "delivered_qty" in item_data and item_data["delivered_qty"] is not None:
            item_payload["delivered_qty"] = Decimal(str(item_data["delivered_qty"]))

        return item_payload

    def _calculate_grand_total(self, items: list[dict]) -> Decimal:
        """Calculate grand total from line items including tax amounts"""
        total = Decimal("0")
        for item in items:
            if "total_amount" in item:
                total += Decimal(str(item.get("total_amount", 0)))
            else:
                qty = Decimal(str(item.get("qty", 0)))
                rate = Decimal(str(item.get("rate", 0)))
                amount = qty * rate
                tax_amount = Decimal(str(item.get("tax_amount", 0)))
                total += amount + tax_amount
        return total

    def _get_item_details(self, item: SalesOrderItem, organization_id: UUID) -> dict:
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
                    "organization_id": item.organization_id,
                    "sales_order_id": item.sales_order_id,
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
                    "tax_template_id": item.tax_template_id,
                    "tax_rate": item.tax_rate,
                    "tax_amount": item.tax_amount,
                    "total_amount": item.total_amount,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                    "extra_data": item.extra_data,
                    **self._get_item_details(item, sales_order.organization_id),
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
