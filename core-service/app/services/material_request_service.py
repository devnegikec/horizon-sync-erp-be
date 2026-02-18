"""Material Request service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.core.transaction import transactional
from app.models.base import MaterialRequestStatus
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

        # Prepare Material Request data
        mr_data = {
            "organization_id": organization_id,
            "status": MaterialRequestStatus.DRAFT,
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
                "required_date": item["required_date"],
                "description": item.get("description"),
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
                    "required_date": item["required_date"],
                    "description": item.get("description"),
                }
                self.repo.create_line_item(line_data)

        # Update Material Request fields
        update_data = {
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

    @staticmethod
    def _to_response(mr) -> dict:
        """Convert Material Request model to response dict"""
        return {
            "id": mr.id,
            "organization_id": mr.organization_id,
            "status": mr.status.value if mr.status else None,
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
                    "required_date": line.required_date,
                    "description": line.description,
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
            "status": mr.status.value if mr.status else None,
            "created_at": mr.created_at,
            "created_by": mr.created_by,
            "line_items_count": line_items_count,
        }
