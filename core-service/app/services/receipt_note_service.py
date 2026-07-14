"""Receipt Note service wrapper for Purchase Receipt API integration"""

from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.transaction import transactional
from app.models.base import PurchaseOrderStatus
from app.repositories.purchase_order_repository import PurchaseOrderRepository
from app.services.purchase_receipt_service import PurchaseReceiptService
from app.services.stock_level_service import StockLevelService


class ReceiptNoteService:
    """
    Service wrapper for creating Receipt Notes using the existing Purchase Receipt API.
    Integrates with Purchase Order workflow for goods receipt.
    """

    def __init__(self, db: Session):
        self.db = db
        self.purchase_receipt_service = PurchaseReceiptService(db)
        self.po_repo = PurchaseOrderRepository(db)
        self.stock_level_service = StockLevelService(db)

    @transactional
    def create_receipt_note(
        self,
        purchase_order_id: UUID,
        receipt_no: str,
        receipt_date,
        line_items: list[dict],
        organization_id: UUID,
        user_id: UUID,
        warehouse_id: UUID | None = None,
        remarks: str | None = None,
    ) -> dict:
        """
        Create Receipt Note for a Purchase Order.

        Args:
            purchase_order_id: ID of the Purchase Order to receive against
            receipt_no: Receipt note number
            receipt_date: Date of receipt
            line_items: List of items being received with quantities
            organization_id: Organization ID
            user_id: User creating the receipt
            warehouse_id: Optional warehouse ID
            remarks: Optional remarks

        Returns:
            dict: Created receipt note response

        Raises:
            ResourceNotFoundException: If Purchase Order not found
            ValidationException: If Purchase Order status is invalid

        Requirements: 5.1, 5.2
        """
        # Validate Purchase Order exists
        po = self.po_repo.get_by_id(purchase_order_id, organization_id)
        if not po:
            raise ResourceNotFoundException(
                f"Purchase Order {purchase_order_id} not found"
            )

        # Validate Purchase Order status (must be SUBMITTED or PARTIALLY_RECEIVED)
        valid_statuses = [
            PurchaseOrderStatus.SUBMITTED,
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
        ]
        if po.status not in valid_statuses:
            raise ValidationException(
                f"Cannot create Receipt Note for Purchase Order in {po.status.value} status. "
                f"Purchase Order must be in SUBMITTED or PARTIALLY_RECEIVED status."
            )

        # Validate line items
        if not line_items:
            raise ValidationException("At least one line item is required")

        # Validate received quantities don't exceed ordered quantities
        po_line_items_map = {str(line.item_id): line for line in po.line_items}

        for idx, item in enumerate(line_items):
            item_id = str(item.get("item_id"))
            qty = item.get("qty", 0)

            if qty <= 0:
                raise ValidationException(
                    f"Line item {idx}: quantity must be greater than zero"
                )

            # Check if item exists in Purchase Order
            if item_id not in po_line_items_map:
                raise ValidationException(
                    f"Line item {idx}: item {item_id} not found in Purchase Order"
                )

            po_line = po_line_items_map[item_id]
            remaining_qty = Decimal(str(po_line.quantity)) - Decimal(
                str(po_line.received_quantity)
            )

            if Decimal(str(qty)) > remaining_qty:
                raise ValidationException(
                    f"Line item {idx}: received quantity {qty} exceeds remaining quantity {remaining_qty}"
                )

        # Prepare Purchase Receipt data with reference to Purchase Order
        receipt_data = {
            "purchase_receipt_no": receipt_no,
            "supplier_id": po.party_id,
            "receipt_date": receipt_date,
            "status": "draft",
            "warehouse_id": warehouse_id,
            "reference_type": "PURCHASE_ORDER",
            "reference_id": purchase_order_id,
            "remarks": remarks,
            "items": line_items,
        }

        # Create Purchase Receipt using existing API
        receipt = self.purchase_receipt_service.create(
            data=receipt_data,
            organization_id=organization_id,
            user_id=user_id,
        )

        # Trigger stock increment for each received line item (Requirement 5.3)
        if warehouse_id:
            self._increment_stock(
                line_items=line_items,
                warehouse_id=warehouse_id,
                organization_id=organization_id,
            )

        # Update Purchase Order received quantities and status
        # Import here to avoid circular dependency
        from app.services.purchase_order_service import PurchaseOrderService

        po_service = PurchaseOrderService(self.db)
        po_service.update_received_quantities(
            po_id=purchase_order_id,
            received_items=line_items,
            organization_id=organization_id,
            user_id=user_id,
        )

        return receipt

    def _increment_stock(
        self,
        line_items: list[dict],
        warehouse_id: UUID,
        organization_id: UUID,
    ) -> None:
        """
        Increment stock levels for received items.

        Args:
            line_items: List of received items with item_id and qty
            warehouse_id: Warehouse where items are received
            organization_id: Organization ID

        Requirements: 5.3
        """
        for item in line_items:
            item_id = item.get("item_id")
            qty = Decimal(str(item.get("qty", 0)))

            if qty <= 0:
                continue

            # Get or create stock level for this item in this warehouse
            stock_level = self.stock_level_service.get_or_create(
                item_id=item_id,
                warehouse_id=warehouse_id,
                organization_id=organization_id,
            )

            # Increment quantity on hand
            new_quantity = (stock_level.quantity_on_hand or 0) + int(qty)

            # Update stock level
            from app.schemas.stock_level import StockLevelUpdate

            self.stock_level_service.update_by_id(
                level_id=stock_level.id,
                data=StockLevelUpdate(quantity_on_hand=new_quantity),
                organization_id=organization_id,
            )
