"""Purchase Order service"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.transaction import transactional
from app.models.base import PurchaseOrderStatus, RFQStatus
from app.repositories.purchase_order_repository import PurchaseOrderRepository
from app.repositories.rfq_repository import RFQRepository
from app.repositories.supplier_repository import SupplierRepository
from app.services.state_machine import StateMachine
from app.services.status_transition_service import StatusTransitionService
from app.services.transaction_engine import (
    TransactionEngine,
    TransactionEngineInput,
)


class PurchaseOrderService:
    """Service for Purchase Order operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = PurchaseOrderRepository(db)
        self.rfq_repo = RFQRepository(db)
        self.status_transition_service = StatusTransitionService(db)
        self.supplier_repo = SupplierRepository(db)
        self.transaction_engine = TransactionEngine()

    @transactional
    def create_from_rfq(
        self,
        rfq_id: UUID,
        supplier_id: UUID,
        line_items: list[dict],
        tax_rate: Decimal | None,
        discount_amount: Decimal | None,
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """
        Create Purchase Order from RFQ.
        - Validates RFQ exists and has quotes
        - Copies selected line items with supplier-quoted prices
        - Sets party_type to SUPPLIER and party_id to selected supplier
        - Validates supplier exists
        - Invokes Transaction Engine to calculate totals
        """
        # Validate RFQ exists
        rfq = self.rfq_repo.get_by_id(rfq_id, organization_id)
        if not rfq:
            raise ResourceNotFoundException(f"RFQ {rfq_id} not found")

        # Validate RFQ has quotes
        has_quotes = any(len(line.quotes) > 0 for line in rfq.line_items)
        if not has_quotes:
            raise ValidationException(
                f"RFQ {rfq_id} does not have any supplier quotes"
            )

        # Validate supplier exists
        supplier = self.supplier_repo.get_supplier_by_id(supplier_id, organization_id)
        if not supplier:
            raise ResourceNotFoundException(
                f"Supplier {supplier_id} not found"
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

        # Calculate totals using Transaction Engine
        engine_input = TransactionEngineInput(
            transaction_type="PURCHASE",
            line_items=line_items,
            tax_rate=Decimal(str(tax_rate)) if tax_rate else None,
            discount_amount=Decimal(str(discount_amount)) if discount_amount else None,
        )
        calculation = self.transaction_engine.calculate(engine_input)

        # Create Purchase Order
        po_data = {
            "organization_id": organization_id,
            "rfq_id": rfq_id,
            "reference_type": "RFQ",
            "reference_id": rfq_id,
            "party_type": "SUPPLIER",
            "party_id": supplier_id,
            "status": PurchaseOrderStatus.DRAFT,
            "subtotal": calculation.subtotal,
            "tax_amount": calculation.tax_amount,
            "tax_rate": tax_rate,
            "discount_amount": calculation.discount_amount,
            "grand_total": calculation.grand_total,
            "created_by": user_id,
            "updated_by": user_id,
        }

        po = self.repo.create(po_data)

        # Create line items with calculated line_totals
        for idx, item in enumerate(line_items):
            line_data = {
                "organization_id": organization_id,
                "purchase_order_id": po.id,
                "item_id": item["item_id"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "line_total": calculation.line_totals[idx],
                "received_quantity": 0,
            }
            self.repo.create_line_item(line_data)

        # Refresh to get line items
        self.db.refresh(po)

        # Update RFQ status to CLOSED when Purchase Order is created
        # (Workflow connection: RFQ → Purchase Order)
        self._close_rfq_after_po_creation(rfq_id, organization_id)

        return self._to_response(po)



    @transactional
    def create(
        self,
        party_id: UUID,
        line_items: list[dict],
        tax_rate: Decimal | None,
        discount_amount: Decimal | None,
        organization_id: UUID,
        user_id: UUID,
        rfq_id: UUID | None = None,
    ) -> dict:
        """
        Create Purchase Order directly (without RFQ).
        - Validates supplier exists
        - Invokes Transaction Engine to calculate totals
        """
        # Validate supplier exists
        supplier = self.supplier_repo.get_supplier_by_id(party_id, organization_id)
        if not supplier:
            raise ResourceNotFoundException(
                f"Supplier {party_id} not found"
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

        # Calculate totals using Transaction Engine
        engine_input = TransactionEngineInput(
            transaction_type="PURCHASE",
            line_items=line_items,
            tax_rate=Decimal(str(tax_rate)) if tax_rate else None,
            discount_amount=Decimal(str(discount_amount)) if discount_amount else None,
        )
        calculation = self.transaction_engine.calculate(engine_input)

        # Create Purchase Order
        po_data = {
            "organization_id": organization_id,
            "rfq_id": rfq_id,
            "reference_type": "RFQ" if rfq_id else None,
            "reference_id": rfq_id,
            "party_type": "SUPPLIER",
            "party_id": party_id,
            "status": PurchaseOrderStatus.DRAFT,
            "subtotal": calculation.subtotal,
            "tax_amount": calculation.tax_amount,
            "tax_rate": tax_rate,
            "discount_amount": calculation.discount_amount,
            "grand_total": calculation.grand_total,
            "created_by": user_id,
            "updated_by": user_id,
        }

        po = self.repo.create(po_data)

        # Create line items with calculated line_totals
        for idx, item in enumerate(line_items):
            line_data = {
                "organization_id": organization_id,
                "purchase_order_id": po.id,
                "item_id": item["item_id"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"],
                "line_total": calculation.line_totals[idx],
                "received_quantity": 0,
            }
            self.repo.create_line_item(line_data)

        # Refresh to get line items
        self.db.refresh(po)
        return self._to_response(po)

    def get_by_id(self, po_id: UUID, organization_id: UUID) -> dict:
        """Get Purchase Order by ID"""
        po = self.repo.get_by_id(po_id, organization_id)
        if not po:
            raise ResourceNotFoundException(f"Purchase Order {po_id} not found")
        return self._to_response(po)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        rfq_id: UUID | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[dict], dict]:
        """List Purchase Orders with pagination"""
        items, total = self.repo.list_purchase_orders(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            status=status,
            rfq_id=rfq_id,
            sort_by=sort_by,
            sort_order=sort_order,
            search=search,
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

    @transactional
    def update(
        self,
        po_id: UUID,
        data: dict,
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """
        Update Purchase Order (DRAFT only).
        Prevents modifications after submission.
        """
        po = self.repo.get_by_id(po_id, organization_id)
        if not po:
            raise ResourceNotFoundException(f"Purchase Order {po_id} not found")

        # Prevent modifications after submission
        if po.status != PurchaseOrderStatus.DRAFT:
            raise ValidationException(
                f"Cannot modify Purchase Order in {po.status.value} status. Only DRAFT can be modified."
            )

        # Validate supplier if party_id is being updated
        if "party_id" in data:
            supplier = self.supplier_repo.get_supplier_by_id(
                data["party_id"], organization_id
            )
            if not supplier:
                raise ResourceNotFoundException(
                    f"Supplier {data['party_id']} not found"
                )

        # Update line items if provided
        if "line_items" in data:
            line_items = data["line_items"]
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

            # Recalculate totals
            tax_rate = data.get("tax_rate", po.tax_rate)
            discount_amount = data.get("discount_amount", po.discount_amount)

            engine_input = TransactionEngineInput(
                transaction_type="PURCHASE",
                line_items=line_items,
                tax_rate=Decimal(str(tax_rate)) if tax_rate else None,
                discount_amount=Decimal(str(discount_amount)) if discount_amount else None,
            )
            calculation = self.transaction_engine.calculate(engine_input)

            # Delete existing line items and create new ones
            self.repo.delete_line_items(po.id)
            for idx, item in enumerate(line_items):
                line_data = {
                    "organization_id": organization_id,
                    "purchase_order_id": po.id,
                    "item_id": item["item_id"],
                    "quantity": item["quantity"],
                    "unit_price": item["unit_price"],
                    "line_total": calculation.line_totals[idx],
                    "received_quantity": 0,
                }
                self.repo.create_line_item(line_data)

            # Update Purchase Order with new totals
            update_data = {
                "subtotal": calculation.subtotal,
                "tax_amount": calculation.tax_amount,
                "tax_rate": tax_rate,
                "discount_amount": calculation.discount_amount,
                "grand_total": calculation.grand_total,
                "updated_by": user_id,
            }
            if "party_id" in data:
                update_data["party_id"] = data["party_id"]

            self.repo.update(po, update_data)
        else:
            # Update only non-line-item fields
            update_data = {"updated_by": user_id}
            if "party_id" in data:
                update_data["party_id"] = data["party_id"]
            if "tax_rate" in data or "discount_amount" in data:
                # Recalculate totals with existing line items
                line_items = [
                    {
                        "item_id": line.item_id,
                        "quantity": line.quantity,
                        "unit_price": line.unit_price,
                    }
                    for line in po.line_items
                ]

                tax_rate = data.get("tax_rate", po.tax_rate)
                discount_amount = data.get("discount_amount", po.discount_amount)

                engine_input = TransactionEngineInput(
                    transaction_type="PURCHASE",
                    line_items=line_items,
                    tax_rate=Decimal(str(tax_rate)) if tax_rate else None,
                    discount_amount=Decimal(str(discount_amount)) if discount_amount else None,
                )
                calculation = self.transaction_engine.calculate(engine_input)

                update_data.update({
                    "subtotal": calculation.subtotal,
                    "tax_amount": calculation.tax_amount,
                    "tax_rate": tax_rate,
                    "discount_amount": calculation.discount_amount,
                    "grand_total": calculation.grand_total,
                })

            self.repo.update(po, update_data)

        self.db.refresh(po)
        return self._to_response(po)

    def delete(self, po_id: UUID, organization_id: UUID) -> None:
        """Delete Purchase Order (DRAFT only)"""
        po = self.repo.get_by_id(po_id, organization_id)
        if not po:
            raise ResourceNotFoundException(f"Purchase Order {po_id} not found")

        # Only allow deletion of DRAFT
        if po.status != PurchaseOrderStatus.DRAFT:
            raise ValidationException(
                f"Cannot delete Purchase Order in {po.status.value} status. Only DRAFT can be deleted."
            )

        self.repo.delete(po)

    @transactional
    def submit(
        self, po_id: UUID, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Submit Purchase Order.
        Changes status from DRAFT to SUBMITTED.
        Prevents modifications after submission.
        """
        po = self.repo.get_by_id(po_id, organization_id)
        if not po:
            raise ResourceNotFoundException(f"Purchase Order {po_id} not found")

        # Store previous status for logging
        previous_status = po.status

        # Validate state transition using state machine
        state_machine = StateMachine("PURCHASE_ORDER")
        try:
            state_machine.validate_transition(previous_status.value, "submitted")
        except ValueError as e:
            raise ValidationException(str(e))

        # Validate line items exist
        if not po.line_items:
            raise ValidationException(
                "Cannot submit Purchase Order without line items"
            )

        # Validate supplier exists
        supplier = self.supplier_repo.get_supplier_by_id(po.party_id, organization_id)
        if not supplier:
            raise ResourceNotFoundException(
                f"Supplier {po.party_id} not found"
            )

        # Update status to SUBMITTED
        new_status = PurchaseOrderStatus.SUBMITTED
        update_data = {
            "status": new_status,
            "updated_by": user_id,
        }
        self.repo.update(po, update_data)
        self.db.refresh(po)

        # Log status transition
        self.status_transition_service.log_transition(
            entity_type="PURCHASE_ORDER",
            entity_id=po_id,
            previous_status=previous_status.value,
            new_status=new_status.value,
            user_id=user_id,
        )

        return self._to_response(po)

    @transactional
    def cancel(
        self, po_id: UUID, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Cancel Purchase Order.
        Changes status to CANCELLED.
        """
        po = self.repo.get_by_id(po_id, organization_id)
        if not po:
            raise ResourceNotFoundException(f"Purchase Order {po_id} not found")

        # Store previous status for logging
        previous_status = po.status

        # Validate state transition using state machine
        state_machine = StateMachine("PURCHASE_ORDER")
        try:
            state_machine.validate_transition(previous_status.value, "cancelled")
        except ValueError as e:
            raise ValidationException(str(e))

        # Update status
        new_status = PurchaseOrderStatus.CANCELLED
        update_data = {
            "status": new_status,
            "updated_by": user_id,
        }
        self.repo.update(po, update_data)
        self.db.refresh(po)

        # Log status transition
        self.status_transition_service.log_transition(
            entity_type="PURCHASE_ORDER",
            entity_id=po_id,
            previous_status=previous_status.value,
            new_status=new_status.value,
            user_id=user_id,
        )

        return self._to_response(po)

    @transactional
    def close(
        self, po_id: UUID, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Close Purchase Order.
        Changes status to CLOSED.
        Validates that status is FULLY_RECEIVED.
        """
        po = self.repo.get_by_id(po_id, organization_id)
        if not po:
            raise ResourceNotFoundException(f"Purchase Order {po_id} not found")

        # Store previous status for logging
        previous_status = po.status

        # Validate state transition using state machine
        state_machine = StateMachine("PURCHASE_ORDER")
        try:
            state_machine.validate_transition(previous_status.value, "closed")
        except ValueError as e:
            raise ValidationException(str(e))

        # Update status
        new_status = PurchaseOrderStatus.CLOSED
        update_data = {
            "status": new_status,
            "updated_by": user_id,
        }
        self.repo.update(po, update_data)
        self.db.refresh(po)

        # Log status transition
        self.status_transition_service.log_transition(
            entity_type="PURCHASE_ORDER",
            entity_id=po_id,
            previous_status=previous_status.value,
            new_status=new_status.value,
            user_id=user_id,
        )

        return self._to_response(po)

    @staticmethod
    def _to_response(po) -> dict:
        """Convert Purchase Order model to response dict"""
        return {
            "id": po.id,
            "organization_id": po.organization_id,
            "rfq_id": po.rfq_id,
            "reference_type": po.reference_type,
            "reference_id": po.reference_id,
            "party_type": po.party_type,
            "party_id": po.party_id,
            "status": po.status.value if po.status else None,
            "subtotal": po.subtotal,
            "tax_amount": po.tax_amount,
            "tax_rate": po.tax_rate,
            "discount_amount": po.discount_amount,
            "grand_total": po.grand_total,
            "created_by": po.created_by,
            "updated_by": po.updated_by,
            "created_at": po.created_at,
            "updated_at": po.updated_at,
            "line_items": [
                {
                    "id": line.id,
                    "organization_id": line.organization_id,
                    "purchase_order_id": line.purchase_order_id,
                    "item_id": line.item_id,
                    "quantity": line.quantity,
                    "unit_price": line.unit_price,
                    "line_total": line.line_total,
                    "received_quantity": line.received_quantity,
                    "created_at": line.created_at,
                    "updated_at": line.updated_at,
                }
                for line in po.line_items
            ],
        }

    @transactional
    def update_received_quantities(
        self,
        po_id: UUID,
        received_items: list[dict],
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """
        Update received quantities for Purchase Order line items.
        Calculates and updates Purchase Order status based on received quantities.
        
        Uses SELECT FOR UPDATE to prevent race conditions in concurrent status updates.
        
        Args:
            po_id: Purchase Order ID
            received_items: List of dicts with item_id and qty
            organization_id: Organization ID
            user_id: User ID for status transition logging
            
        Returns:
            dict: Updated Purchase Order response
            
        Requirements: 5.4, 5.5, 11.7
        """
        # Requirement 11.7: Use SELECT FOR UPDATE to lock the row for concurrent updates
        po = self.repo.get_by_id(po_id, organization_id, for_update=True)
        if not po:
            raise ResourceNotFoundException(f"Purchase Order {po_id} not found")

        # Build a map of item_id to received quantity
        received_map = {}
        for item in received_items:
            item_id = str(item.get("item_id"))
            qty = Decimal(str(item.get("qty", 0)))
            if item_id in received_map:
                received_map[item_id] += qty
            else:
                received_map[item_id] = qty

        # Update received quantities for each line item
        for line in po.line_items:
            item_id = str(line.item_id)
            if item_id in received_map:
                new_received_qty = line.received_quantity + received_map[item_id]
                self.repo.update_line_item_received_quantity(line.id, new_received_qty)

        # Refresh to get updated line items
        self.db.refresh(po)

        # Calculate new status based on received quantities
        new_status = self._calculate_po_status(po)

        # Update status if changed
        if new_status != po.status:
            previous_status = po.status
            update_data = {
                "status": new_status,
                "updated_by": user_id,
            }
            self.repo.update(po, update_data)
            self.db.refresh(po)

            # Log status transition
            self.status_transition_service.log_transition(
                entity_type="PURCHASE_ORDER",
                entity_id=po_id,
                previous_status=previous_status.value,
                new_status=new_status.value,
                user_id=user_id,
            )

        return self._to_response(po)

    def _calculate_po_status(self, po) -> PurchaseOrderStatus:
        """
        Calculate Purchase Order status based on received quantities.
        
        - FULLY_RECEIVED: All line items have received_quantity == quantity
        - PARTIALLY_RECEIVED: Some line items have received_quantity > 0 but < quantity
        - SUBMITTED: No items received yet
        
        Requirements: 5.4, 5.5
        """
        if not po.line_items:
            return po.status

        all_fully_received = True
        any_partially_received = False

        for line in po.line_items:
            if line.received_quantity >= line.quantity:
                # Fully received
                continue
            elif line.received_quantity > 0:
                # Partially received
                all_fully_received = False
                any_partially_received = True
            else:
                # Not received
                all_fully_received = False

        if all_fully_received:
            return PurchaseOrderStatus.FULLY_RECEIVED
        elif any_partially_received or any(line.received_quantity > 0 for line in po.line_items):
            return PurchaseOrderStatus.PARTIALLY_RECEIVED
        else:
            return po.status

    def _to_list_item(self, po) -> dict:
        """Convert Purchase Order model to list item dict"""
        line_items_count = self.repo.get_line_items_count(po.id)
        return {
            "id": po.id,
            "organization_id": po.organization_id,
            "rfq_id": po.rfq_id,
            "party_id": po.party_id,
            "status": po.status.value if po.status else None,
            "grand_total": po.grand_total,
            "created_at": po.created_at,
            "created_by": po.created_by,
            "line_items_count": line_items_count,
        }

    def _close_rfq_after_po_creation(
        self, rfq_id: UUID, organization_id: UUID
    ) -> None:
        """
        Close RFQ after Purchase Order is created.
        
        Workflow connection: RFQ → Purchase Order
        
        When a Purchase Order is created from an RFQ, the RFQ should be closed
        to indicate that the procurement process has moved forward.
        
        Requirements: 2.5
        """
        rfq = self.rfq_repo.get_by_id(rfq_id, organization_id)
        if not rfq:
            return

        # Only close if RFQ is not already closed
        if rfq.status != RFQStatus.CLOSED:
            update_data = {"status": RFQStatus.CLOSED}
            self.rfq_repo.update(rfq, update_data)
