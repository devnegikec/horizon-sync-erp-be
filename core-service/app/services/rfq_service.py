"""RFQ service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.transaction import transactional
from app.models.base import MaterialRequestStatus, RFQStatus
from app.repositories.material_request_repository import MaterialRequestRepository
from app.repositories.rfq_repository import RFQRepository
from app.services.document_numbering_service import DocumentNumberingService
from app.services.state_machine import StateMachine
from app.services.status_transition_service import StatusTransitionService


class RFQService:
    """Service for RFQ operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = RFQRepository(db)
        self.mr_repo = MaterialRequestRepository(db)
        self.status_transition_service = StatusTransitionService(db)

    @transactional
    def create_from_material_request(
        self,
        material_request_id: UUID,
        closing_date,
        supplier_ids: list[UUID],
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """
        Create RFQ from Material Request.
        - Validates Material Request exists and has status SUBMITTED
        - Copies all line items from source Material Request
        - Sets reference_type as MATERIAL_REQUEST and reference_id
        - Validates suppliers exist
        """
        # Validate Material Request exists and has status SUBMITTED
        mr = self.mr_repo.get_by_id(material_request_id, organization_id)
        if not mr:
            raise ResourceNotFoundException(
                f"Material Request {material_request_id} not found"
            )

        if mr.status != MaterialRequestStatus.SUBMITTED:
            raise ValidationException(
                f"Material Request must be in SUBMITTED status. Current status: {mr.status.value}"
            )

        # Validate Material Request has line items
        if not mr.line_items:
            raise ValidationException(
                "Material Request must have line items to create RFQ"
            )

        # Validate suppliers
        if not supplier_ids:
            raise ValidationException("At least one supplier is required")

        # TODO: Validate suppliers exist in Suppliers API
        # This will be implemented when we integrate with the Suppliers API

        # Create RFQ
        rfq_data = {
            "organization_id": organization_id,
            "rfq_no": DocumentNumberingService(self.db).get_next_number(organization_id, "rfq"),
            "material_request_id": material_request_id,
            "reference_type": "MATERIAL_REQUEST",
            "reference_id": material_request_id,
            "status": RFQStatus.DRAFT,
            "closing_date": closing_date,
            "created_by": user_id,
            "updated_by": user_id,
        }

        rfq = self.repo.create(rfq_data)

        # Copy all line items from Material Request
        for mr_line in mr.line_items:
            line_data = {
                "organization_id": organization_id,
                "rfq_id": rfq.id,
                "item_id": mr_line.item_id,
                "quantity": mr_line.quantity,
                "required_date": mr_line.required_date,
                "description": mr_line.description,
            }
            self.repo.create_line_item(line_data)

        # Add suppliers
        for supplier_id in supplier_ids:
            supplier_data = {
                "organization_id": organization_id,
                "rfq_id": rfq.id,
                "supplier_id": supplier_id,
            }
            self.repo.create_supplier(supplier_data)

        # Refresh to get line items and suppliers
        self.db.refresh(rfq)

        # Update Material Request status to PARTIALLY_QUOTED
        # (Workflow connection: Material Request → RFQ)
        self._update_material_request_status(material_request_id, organization_id)

        return self._to_response(rfq)

    @transactional
    def add_suppliers(
        self,
        rfq_id: UUID,
        supplier_ids: list[UUID],
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """
        Add suppliers to an RFQ.
        - Validates RFQ exists and is in DRAFT status
        - Validates suppliers exist
        - Adds suppliers to RFQ
        """
        # Get RFQ
        rfq = self.repo.get_by_id(rfq_id, organization_id)
        if not rfq:
            raise ResourceNotFoundException(f"RFQ {rfq_id} not found")

        # Validate RFQ is in DRAFT status
        if rfq.status != RFQStatus.DRAFT:
            raise ValidationException(
                f"Cannot add suppliers to RFQ in {rfq.status.value} status. Only DRAFT can be modified."
            )

        # Validate suppliers
        if not supplier_ids:
            raise ValidationException("At least one supplier is required")

        # TODO: Validate suppliers exist in Suppliers API
        # This will be implemented when we integrate with the Suppliers API

        # Get existing supplier IDs
        existing_supplier_ids = {s.supplier_id for s in rfq.suppliers}

        # Add new suppliers (avoid duplicates)
        for supplier_id in supplier_ids:
            if supplier_id not in existing_supplier_ids:
                supplier_data = {
                    "organization_id": organization_id,
                    "rfq_id": rfq.id,
                    "supplier_id": supplier_id,
                }
                self.repo.create_supplier(supplier_data)

        # Update RFQ
        update_data = {"updated_by": user_id}
        self.repo.update(rfq, update_data)

        # Refresh to get updated suppliers
        self.db.refresh(rfq)
        return self._to_response(rfq)

    @transactional
    def send(
        self, rfq_id: UUID, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Send RFQ to suppliers.
        - Changes status from DRAFT to SENT
        """
        rfq = self.repo.get_by_id(rfq_id, organization_id)
        if not rfq:
            raise ResourceNotFoundException(f"RFQ {rfq_id} not found")

        # Store previous status for logging
        previous_status = rfq.status

        # Validate current status
        if rfq.status != RFQStatus.DRAFT:
            raise ValidationException(
                f"Cannot send RFQ in {rfq.status.value} status. Only DRAFT can be sent."
            )

        # Validate RFQ has line items
        if not rfq.line_items:
            raise ValidationException("Cannot send RFQ without line items")

        # Validate RFQ has suppliers
        if not rfq.suppliers:
            raise ValidationException("Cannot send RFQ without suppliers")

        # Update status to SENT
        new_status = RFQStatus.SENT
        update_data = {
            "status": new_status,
            "updated_by": user_id,
        }
        self.repo.update(rfq, update_data)
        self.db.refresh(rfq)

        # Log status transition
        self.status_transition_service.log_transition(
            entity_type="RFQ",
            entity_id=rfq_id,
            previous_status=previous_status.value,
            new_status=new_status.value,
            user_id=user_id,
        )

        return self._to_response(rfq)

    @transactional
    def record_quote(
        self,
        rfq_id: UUID,
        rfq_line_id: UUID,
        supplier_id: UUID,
        quoted_price: float,
        quoted_delivery_date,
        supplier_notes: str | None,
        organization_id: UUID,
    ) -> dict:
        """
        Record supplier quote for an RFQ line item.
        - Validates RFQ exists and is in SENT or PARTIALLY_RESPONDED status
        - Validates RFQ line exists
        - Validates supplier is associated with the RFQ
        - Creates or updates supplier quote
        """
        # Get RFQ
        rfq = self.repo.get_by_id(rfq_id, organization_id)
        if not rfq:
            raise ResourceNotFoundException(f"RFQ {rfq_id} not found")

        # Validate RFQ status
        if rfq.status not in [RFQStatus.SENT, RFQStatus.PARTIALLY_RESPONDED]:
            raise ValidationException(
                f"Cannot record quote for RFQ in {rfq.status.value} status"
            )

        # Validate RFQ line exists
        rfq_line = None
        for line in rfq.line_items:
            if line.id == rfq_line_id:
                rfq_line = line
                break

        if not rfq_line:
            raise ValidationException(f"RFQ line {rfq_line_id} not found in RFQ {rfq_id}")

        # Validate supplier is associated with RFQ
        supplier_ids = {s.supplier_id for s in rfq.suppliers}
        if supplier_id not in supplier_ids:
            raise ValidationException(
                f"Supplier {supplier_id} is not associated with RFQ {rfq_id}"
            )

        # Check if quote already exists
        existing_quote = self.repo.get_quote(rfq_line_id, supplier_id, organization_id)

        if existing_quote:
            # Update existing quote
            quote_data = {
                "quoted_price": quoted_price,
                "quoted_delivery_date": quoted_delivery_date,
                "supplier_notes": supplier_notes,
            }
            self.repo.update_quote(existing_quote, quote_data)
        else:
            # Create new quote
            quote_data = {
                "organization_id": organization_id,
                "rfq_line_id": rfq_line_id,
                "supplier_id": supplier_id,
                "quoted_price": quoted_price,
                "quoted_delivery_date": quoted_delivery_date,
                "supplier_notes": supplier_notes,
            }
            self.repo.create_quote(quote_data)

        # Refresh RFQ to get updated quotes
        self.db.refresh(rfq)

        # Update RFQ status based on quote completeness
        # Check if all line items have at least one quote
        all_lines_quoted = all(len(line.quotes) > 0 for line in rfq.line_items)

        if all_lines_quoted:
            # Check if all suppliers have quoted for all lines
            num_suppliers = len(rfq.suppliers)
            all_fully_responded = all(
                len(line.quotes) == num_suppliers for line in rfq.line_items
            )

            if all_fully_responded:
                update_data = {"status": RFQStatus.FULLY_RESPONDED}
            else:
                update_data = {"status": RFQStatus.PARTIALLY_RESPONDED}

            self.repo.update(rfq, update_data)
            self.db.refresh(rfq)

        # Update Material Request status when quotes are recorded
        # (Workflow connection: Material Request → RFQ)
        if rfq.material_request_id:
            self._update_material_request_status(rfq.material_request_id, organization_id)

        return self._to_response(rfq)

    def get_by_id(self, rfq_id: UUID, organization_id: UUID) -> dict:
        """Get RFQ by ID"""
        rfq = self.repo.get_by_id(rfq_id, organization_id)
        if not rfq:
            raise ResourceNotFoundException(f"RFQ {rfq_id} not found")
        return self._to_response(rfq)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        material_request_id: UUID | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[dict], dict]:
        """List RFQs with pagination"""
        items, total = self.repo.list_rfqs(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            status=status,
            material_request_id=material_request_id,
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
        rfq_id: UUID,
        data: dict,
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """
        Update RFQ (DRAFT only).
        Prevents modifications after sending.
        """
        rfq = self.repo.get_by_id(rfq_id, organization_id)
        if not rfq:
            raise ResourceNotFoundException(f"RFQ {rfq_id} not found")

        # Prevent modifications after sending
        if rfq.status != RFQStatus.DRAFT:
            raise ValidationException(
                f"Cannot modify RFQ in {rfq.status.value} status. Only DRAFT can be modified."
            )

        # Update closing date if provided
        if "closing_date" in data:
            update_data = {
                "closing_date": data["closing_date"],
                "updated_by": user_id,
            }
            self.repo.update(rfq, update_data)

        # Update line items if provided
        if "line_items" in data:
            line_items = data["line_items"]
            if not line_items:
                raise ValidationException("At least one line item is required")

            # Delete existing line items and create new ones
            self.repo.delete_line_items(rfq.id)
            for item in line_items:
                line_data = {
                    "organization_id": organization_id,
                    "rfq_id": rfq.id,
                    "item_id": item["item_id"],
                    "quantity": item["quantity"],
                    "required_date": item["required_date"],
                    "description": item.get("description"),
                }
                self.repo.create_line_item(line_data)

        # Update suppliers if provided
        if "supplier_ids" in data:
            supplier_ids = data["supplier_ids"]
            if not supplier_ids:
                raise ValidationException("At least one supplier is required")

            # Delete existing suppliers and create new ones
            self.repo.delete_suppliers(rfq.id)
            for supplier_id in supplier_ids:
                supplier_data = {
                    "organization_id": organization_id,
                    "rfq_id": rfq.id,
                    "supplier_id": supplier_id,
                }
                self.repo.create_supplier(supplier_data)

        self.db.refresh(rfq)
        return self._to_response(rfq)

    def delete(self, rfq_id: UUID, organization_id: UUID) -> None:
        """Delete RFQ (DRAFT only)"""
        rfq = self.repo.get_by_id(rfq_id, organization_id)
        if not rfq:
            raise ResourceNotFoundException(f"RFQ {rfq_id} not found")

        # Only allow deletion of DRAFT
        if rfq.status != RFQStatus.DRAFT:
            raise ValidationException(
                f"Cannot delete RFQ in {rfq.status.value} status. Only DRAFT can be deleted."
            )

        self.repo.delete(rfq)

    @transactional
    def close(self, rfq_id: UUID, organization_id: UUID, user_id: UUID) -> dict:
        """
        Close RFQ.
        Changes status to CLOSED.
        """
        rfq = self.repo.get_by_id(rfq_id, organization_id)
        if not rfq:
            raise ResourceNotFoundException(f"RFQ {rfq_id} not found")

        # Store previous status for logging
        previous_status = rfq.status

        # Validate state transition using state machine
        state_machine = StateMachine("RFQ")
        try:
            state_machine.validate_transition(previous_status.value, "closed")
        except ValueError as e:
            raise ValidationException(str(e))

        # Update status
        new_status = RFQStatus.CLOSED
        update_data = {
            "status": new_status,
            "updated_by": user_id,
        }
        self.repo.update(rfq, update_data)
        self.db.refresh(rfq)

        # Log status transition
        self.status_transition_service.log_transition(
            entity_type="RFQ",
            entity_id=rfq_id,
            previous_status=previous_status.value,
            new_status=new_status.value,
            user_id=user_id,
        )

        return self._to_response(rfq)

    @staticmethod
    def _to_response(rfq) -> dict:
        """Convert RFQ model to response dict"""
        # Handle status - it might be an enum or a string
        status_value = None
        if rfq.status:
            status_value = rfq.status.value if hasattr(rfq.status, 'value') else rfq.status

        return {
            "id": rfq.id,
            "organization_id": rfq.organization_id,
            "rfq_no": rfq.rfq_no,
            "material_request_id": rfq.material_request_id,
            "reference_type": rfq.reference_type,
            "reference_id": rfq.reference_id,
            "status": status_value,
            "closing_date": rfq.closing_date,
            "created_by": rfq.created_by,
            "updated_by": rfq.updated_by,
            "created_at": rfq.created_at,
            "updated_at": rfq.updated_at,
            "line_items": [
                {
                    "id": line.id,
                    "organization_id": line.organization_id,
                    "rfq_id": line.rfq_id,
                    "item_id": line.item_id,
                    "quantity": line.quantity,
                    "required_date": line.required_date,
                    "description": line.description,
                    "created_at": line.created_at,
                    "updated_at": line.updated_at,
                    "quotes": [
                        {
                            "id": quote.id,
                            "organization_id": quote.organization_id,
                            "rfq_line_id": quote.rfq_line_id,
                            "supplier_id": quote.supplier_id,
                            "quoted_price": quote.quoted_price,
                            "quoted_delivery_date": quote.quoted_delivery_date,
                            "supplier_notes": quote.supplier_notes,
                            "created_at": quote.created_at,
                            "updated_at": quote.updated_at,
                        }
                        for quote in line.quotes
                    ],
                }
                for line in rfq.line_items
            ],
            "suppliers": [
                {
                    "id": supplier.id,
                    "organization_id": supplier.organization_id,
                    "rfq_id": supplier.rfq_id,
                    "supplier_id": supplier.supplier_id,
                    "created_at": supplier.created_at,
                }
                for supplier in rfq.suppliers
            ],
        }

    def _to_list_item(self, rfq) -> dict:
        """Convert RFQ model to list item dict"""
        line_items_count = self.repo.get_line_items_count(rfq.id)
        suppliers_count = self.repo.get_suppliers_count(rfq.id)

        # Handle status - it might be an enum or a string
        status_value = None
        if rfq.status:
            status_value = rfq.status.value if hasattr(rfq.status, 'value') else rfq.status

        return {
            "id": rfq.id,
            "organization_id": rfq.organization_id,
            "material_request_id": rfq.material_request_id,
            "status": status_value,
            "closing_date": rfq.closing_date,
            "created_at": rfq.created_at,
            "created_by": rfq.created_by,
            "line_items_count": line_items_count,
            "suppliers_count": suppliers_count,
        }

    def _update_material_request_status(
        self, material_request_id: UUID, organization_id: UUID
    ) -> None:
        """
        Update Material Request status when RFQ is created.

        Workflow connection: Material Request → RFQ

        - If all line items have RFQs with quotes, set to FULLY_QUOTED
        - Otherwise, set to PARTIALLY_QUOTED

        Requirements: 8.2
        """
        mr = self.mr_repo.get_by_id(material_request_id, organization_id)
        if not mr:
            return

        # Get all RFQs for this Material Request
        rfqs = self.repo.get_rfqs_by_material_request(material_request_id, organization_id)

        # Check if all line items have at least one quote
        mr_item_ids = {str(line.item_id) for line in mr.line_items}
        quoted_item_ids = set()

        for rfq in rfqs:
            for line in rfq.line_items:
                if len(line.quotes) > 0:
                    quoted_item_ids.add(str(line.item_id))

        # Determine new status
        if quoted_item_ids >= mr_item_ids:
            # All items have quotes
            new_status = MaterialRequestStatus.FULLY_QUOTED
        else:
            # Some items have quotes
            new_status = MaterialRequestStatus.PARTIALLY_QUOTED

        # Update Material Request status if changed
        if mr.status != new_status:
            update_data = {"status": new_status}
            self.mr_repo.update(mr, update_data)
