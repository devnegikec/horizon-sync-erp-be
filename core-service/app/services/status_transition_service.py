"""Status Transition logging service"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.models.status_transition import StatusTransition


class StatusTransitionService:
    """Service for logging status transitions"""

    def __init__(self, db: Session):
        self.db = db

    def log_transition(
        self,
        entity_type: str,
        entity_id: UUID,
        previous_status: str,
        new_status: str,
        user_id: UUID,
    ) -> StatusTransition:
        """
        Log a status transition to the database.

        Args:
            entity_type: Type of entity (e.g., 'MATERIAL_REQUEST', 'RFQ', 'PURCHASE_ORDER')
            entity_id: ID of the entity
            previous_status: Previous status value
            new_status: New status value
            user_id: ID of the user who made the transition

        Returns:
            The created StatusTransition record
        """
        transition = StatusTransition(
            entity_type=entity_type,
            entity_id=entity_id,
            previous_status=previous_status,
            new_status=new_status,
            user_id=user_id,
        )

        self.db.add(transition)
        self.db.commit()
        self.db.refresh(transition)

        return transition
