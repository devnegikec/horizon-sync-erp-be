"""Material Request service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.transaction import transactional
from app.models.base import MaterialRequestStatus
from app.models.invoice import Invoice
from app.models.payment import Payment
from app.models.purchase_order import PurchaseOrder
from app.models.purchase_receipt import PurchaseReceipt
from app.models.rfq import RFQ
from app.repositories.material_request_repository import MaterialRequestRepository
from app.services.state_machine import StateMachine
from app.services.status_transition_service import StatusTransitionService


class MaterialRequestService:
    """Service for Material Request operations"""

    def __init__(self, db: Session):
        self.db = db
        self.repo = MaterialRequestRepository(db)
        self.status_transition_service = StatusTransitionService(db)

    @transactional
    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        """
        Create a new Material Request with DRAFT status.
        Validates that all line items have positive quantities.
        Auto-generates request_no if not provided.
        """
        # Validate line items
        line_items = data.get("line_items", [])
        if not line_items:
            raise ValidationException("At least one line item is required")

        for idx, item in enumerate(line_items):
            if item.get("quantity", 0) <= 0:
                raise ValidationException(
                    f"Line item {idx}: quantity must be greater than zero"
                )

        # Auto-generate request_no if not provided
        request_no = data.get("request_no")
        if not request_no:
            # Generate format: MR-YYYY-NNNN
            from datetime import datetime

            year = datetime.now().year
            # Get count of MRs this year for this org
            count = self.repo.count_by_year(organization_id, year)
            request_no = f"MR-{year}-{count + 1:04d}"

        # Prepare Material Request data
        mr_data = {
            "organization_id": organization_id,
            "request_no": request_no,
            "type": data.get("type", "purchase"),
            "priority": data.get("priority", "medium"),
            "status": MaterialRequestStatus.DRAFT,
            "target_warehouse_id": data.get("target_warehouse_id"),
            "requested_by": data.get("requested_by", user_id),
            "department": data.get("department"),
            "notes": data.get("notes"),
            "created_by": user_id,
            "updated_by": user_id,
        }

        # Create Material Request
        mr = self.repo.create(mr_data)

        # Create line items
        for item in line_items:
            line_data = {
                "organization_id": organization_id,
                "material_request_id": mr.id,
                "item_id": item["item_id"],
                "quantity": item["quantity"],
                "uom": item.get("uom"),
                "required_date": item["required_date"],
                "description": item.get("description"),
                "estimated_unit_cost": item.get("estimated_unit_cost"),
                "requested_for": item.get("requested_for"),
                "requested_for_department": item.get("requested_for_department"),
            }
            self.repo.create_line_item(line_data)

        # Refresh to get line items
        self.db.refresh(mr)
        return self._to_response(mr)

    def get_by_id(self, material_request_id: UUID, organization_id: UUID) -> dict:
        """Get Material Request by ID"""
        mr = self.repo.get_by_id(material_request_id, organization_id)
        if not mr:
            raise ResourceNotFoundException(
                f"Material Request {material_request_id} not found"
            )
        return self._to_response(mr)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        search: str | None = None,
    ) -> tuple[list[dict], dict]:
        """List Material Requests with pagination"""
        items, total = self.repo.list_material_requests(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            status=status,
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
        material_request_id: UUID,
        data: dict,
        organization_id: UUID,
        user_id: UUID,
    ) -> dict:
        """
        Update Material Request (DRAFT only).
        Prevents modifications after submission.
        """
        mr = self.repo.get_by_id(material_request_id, organization_id)
        if not mr:
            raise ResourceNotFoundException(
                f"Material Request {material_request_id} not found"
            )

        # Prevent modifications after submission
        if mr.status != MaterialRequestStatus.DRAFT:
            raise ValidationException(
                f"Cannot modify Material Request in {mr.status.value} status. Only DRAFT can be modified."
            )

        # Validate line items if provided
        line_items = data.get("line_items")
        if line_items is not None:
            if not line_items:
                raise ValidationException("At least one line item is required")

            for idx, item in enumerate(line_items):
                if item.get("quantity", 0) <= 0:
                    raise ValidationException(
                        f"Line item {idx}: quantity must be greater than zero"
                    )

            # Delete existing line items and create new ones
            self.repo.delete_line_items(mr.id)
            for item in line_items:
                line_data = {
                    "organization_id": organization_id,
                    "material_request_id": mr.id,
                    "item_id": item["item_id"],
                    "quantity": item["quantity"],
                    "uom": item.get("uom"),
                    "required_date": item["required_date"],
                    "description": item.get("description"),
                    "estimated_unit_cost": item.get("estimated_unit_cost"),
                    "requested_for": item.get("requested_for"),
                    "requested_for_department": item.get("requested_for_department"),
                }
                self.repo.create_line_item(line_data)

        # Update Material Request fields
        update_data = {
            "request_no": data.get("request_no", mr.request_no),
            "type": data.get("type", mr.type),
            "priority": data.get("priority", mr.priority),
            "target_warehouse_id": data.get(
                "target_warehouse_id", mr.target_warehouse_id
            ),
            "requested_by": data.get("requested_by", mr.requested_by),
            "department": data.get("department", mr.department),
            "notes": data.get("notes", mr.notes),
            "updated_by": user_id,
        }

        self.repo.update(mr, update_data)
        self.db.refresh(mr)
        return self._to_response(mr)

    def delete(self, material_request_id: UUID, organization_id: UUID) -> None:
        """Delete Material Request (DRAFT only)"""
        mr = self.repo.get_by_id(material_request_id, organization_id)
        if not mr:
            raise ResourceNotFoundException(
                f"Material Request {material_request_id} not found"
            )

        # Only allow deletion of DRAFT
        if mr.status != MaterialRequestStatus.DRAFT:
            raise ValidationException(
                f"Cannot delete Material Request in {mr.status.value} status. Only DRAFT can be deleted."
            )

        self.repo.delete(mr)

    @transactional
    def submit(
        self, material_request_id: UUID, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Submit Material Request.
        Changes status from DRAFT to SUBMITTED.
        """
        mr = self.repo.get_by_id(material_request_id, organization_id)
        if not mr:
            raise ResourceNotFoundException(
                f"Material Request {material_request_id} not found"
            )

        # Store previous status for logging
        previous_status = mr.status

        # Validate state transition using state machine
        state_machine = StateMachine("MATERIAL_REQUEST")
        try:
            state_machine.validate_transition(previous_status.value, "submitted")
        except ValueError as e:
            raise ValidationException(str(e))

        # Validate line items exist
        if not mr.line_items:
            raise ValidationException(
                "Cannot submit Material Request without line items"
            )

        # Validate all line items have positive quantities
        for idx, item in enumerate(mr.line_items):
            if item.quantity <= 0:
                raise ValidationException(
                    f"Line item {idx}: quantity must be greater than zero"
                )

        # Update status
        new_status = MaterialRequestStatus.SUBMITTED
        update_data = {
            "status": new_status,
            "updated_by": user_id,
        }
        self.repo.update(mr, update_data)
        self.db.refresh(mr)

        # Log status transition
        self.status_transition_service.log_transition(
            entity_type="MATERIAL_REQUEST",
            entity_id=material_request_id,
            previous_status=previous_status.value,
            new_status=new_status.value,
            user_id=user_id,
        )

        return self._to_response(mr)

    @transactional
    def cancel(
        self, material_request_id: UUID, organization_id: UUID, user_id: UUID
    ) -> dict:
        """
        Cancel Material Request.
        Changes status to CANCELLED.
        """
        mr = self.repo.get_by_id(material_request_id, organization_id)
        if not mr:
            raise ResourceNotFoundException(
                f"Material Request {material_request_id} not found"
            )

        # Store previous status for logging
        previous_status = mr.status

        # Validate state transition using state machine
        state_machine = StateMachine("MATERIAL_REQUEST")
        try:
            state_machine.validate_transition(previous_status.value, "cancelled")
        except ValueError as e:
            raise ValidationException(str(e))

        # Update status
        new_status = MaterialRequestStatus.CANCELLED
        update_data = {
            "status": new_status,
            "updated_by": user_id,
        }
        self.repo.update(mr, update_data)
        self.db.refresh(mr)

        # Log status transition
        self.status_transition_service.log_transition(
            entity_type="MATERIAL_REQUEST",
            entity_id=material_request_id,
            previous_status=previous_status.value,
            new_status=new_status.value,
            user_id=user_id,
        )

        return self._to_response(mr)

    def get_workflow_status(
        self, material_request_id: UUID, organization_id: UUID
    ) -> dict:
        """
        Get complete workflow status for a Material Request.
        Traces: MR → RFQs → Purchase Orders → Receipts → Invoices → Payments
        """
        mr = self.repo.get_by_id(material_request_id, organization_id)
        if not mr:
            raise ResourceNotFoundException(
                f"Material Request {material_request_id} not found"
            )

        # Get RFQs linked to this MR
        rfqs = (
            self.db.query(RFQ)
            .filter(
                RFQ.material_request_id == material_request_id,
                RFQ.organization_id == organization_id,
                RFQ.deleted_at.is_(None),
            )
            .all()
        )

        rfq_ids = [rfq.id for rfq in rfqs]

        # Get Purchase Orders linked to those RFQs
        purchase_orders = []
        if rfq_ids:
            purchase_orders = (
                self.db.query(PurchaseOrder)
                .filter(
                    PurchaseOrder.rfq_id.in_(rfq_ids),
                    PurchaseOrder.organization_id == organization_id,
                    PurchaseOrder.deleted_at.is_(None),
                )
                .all()
            )

        po_ids = [po.id for po in purchase_orders]

        # Get Receipts linked to those POs (via reference_id)
        receipts = []
        if po_ids:
            receipts = (
                self.db.query(PurchaseReceipt)
                .filter(
                    PurchaseReceipt.reference_id.in_(po_ids),
                    PurchaseReceipt.organization_id == organization_id,
                )
                .all()
            )

        # Get Invoices linked to those POs (via reference_id)
        invoices = []
        if po_ids:
            invoices = (
                self.db.query(Invoice)
                .filter(
                    Invoice.reference_id.in_(po_ids),
                    Invoice.organization_id == organization_id,
                )
                .all()
            )

        invoice_ids = [inv.id for inv in invoices]

        # Get Payments linked to those Invoices (via extra_data or reference)
        payments = []
        if invoice_ids:
            # Payments reference invoices via party_id matching and reference
            payments = (
                self.db.query(Payment)
                .filter(
                    Payment.organization_id == organization_id,
                )
                .all()
            )
            # Filter payments that reference our invoices via extra_data
            # Since payments don't have a direct reference_id to invoices,
            # we match by party_id from the POs
            supplier_ids = list({po.party_id for po in purchase_orders})
            if supplier_ids:
                payments = (
                    self.db.query(Payment)
                    .filter(
                        Payment.party_id.in_(supplier_ids),
                        Payment.organization_id == organization_id,
                    )
                    .all()
                )

        return {
            "material_request": self._to_response(mr),
            "rfqs": [
                {
                    "id": rfq.id,
                    "status": rfq.status.value
                    if hasattr(rfq.status, "value")
                    else rfq.status,
                    "closing_date": rfq.closing_date,
                    "created_at": rfq.created_at,
                }
                for rfq in rfqs
            ],
            "purchase_orders": [
                {
                    "id": po.id,
                    "status": po.status.value
                    if hasattr(po.status, "value")
                    else po.status,
                    "party_id": po.party_id,
                    "grand_total": po.grand_total,
                    "created_at": po.created_at,
                }
                for po in purchase_orders
            ],
            "receipts": [
                {
                    "id": r.id,
                    "purchase_receipt_no": r.purchase_receipt_no,
                    "receipt_date": r.receipt_date,
                    "status": r.status.value
                    if hasattr(r.status, "value")
                    else r.status,
                }
                for r in receipts
            ],
            "invoices": [
                {
                    "id": inv.id,
                    "invoice_no": inv.invoice_no,
                    "status": inv.status.value
                    if hasattr(inv.status, "value")
                    else inv.status,
                    "grand_total": inv.grand_total,
                }
                for inv in invoices
            ],
            "payments": [
                {
                    "id": p.id,
                    "payment_no": p.payment_no,
                    "amount": p.amount,
                    "status": p.status.value
                    if hasattr(p.status, "value")
                    else p.status,
                    "posting_date": p.posting_date,
                }
                for p in payments
            ],
        }

    @staticmethod
    def _to_response(mr) -> dict:
        """Convert Material Request model to response dict"""
        return {
            "id": mr.id,
            "organization_id": mr.organization_id,
            "request_no": mr.request_no,
            "type": mr.type.value if mr.type else "purchase",
            "priority": mr.priority.value if mr.priority else "medium",
            "status": mr.status.value if mr.status else None,
            "target_warehouse_id": mr.target_warehouse_id,
            "requested_by": mr.requested_by,
            "department": mr.department,
            "notes": mr.notes,
            "created_by": mr.created_by,
            "updated_by": mr.updated_by,
            "created_at": mr.created_at,
            "updated_at": mr.updated_at,
            "line_items": [
                {
                    "id": line.id,
                    "organization_id": line.organization_id,
                    "material_request_id": line.material_request_id,
                    "item_id": line.item_id,
                    "quantity": line.quantity,
                    "uom": line.uom,
                    "required_date": line.required_date,
                    "description": line.description,
                    "estimated_unit_cost": line.estimated_unit_cost,
                    "requested_for": line.requested_for,
                    "requested_for_department": line.requested_for_department,
                    "created_at": line.created_at,
                    "updated_at": line.updated_at,
                }
                for line in mr.line_items
            ],
        }

    def _to_list_item(self, mr) -> dict:
        """Convert Material Request model to list item dict"""
        line_items_count = self.repo.get_line_items_count(mr.id)
        return {
            "id": mr.id,
            "organization_id": mr.organization_id,
            "request_no": mr.request_no,
            "type": mr.type.value if mr.type else "purchase",
            "priority": mr.priority.value if mr.priority else "medium",
            "status": mr.status.value if mr.status else None,
            "department": mr.department,
            "created_at": mr.created_at,
            "created_by": mr.created_by,
            "line_items_count": line_items_count,
        }
