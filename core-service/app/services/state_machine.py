"""State machine service for document status transitions"""


from app.models.base import MaterialRequestStatus, PurchaseOrderStatus, RFQStatus


class StateMachine:
    """State machine for validating document status transitions"""

    # Define valid state transitions for each document type
    MATERIAL_REQUEST_TRANSITIONS: dict[
        MaterialRequestStatus, set[MaterialRequestStatus]
    ] = {
        MaterialRequestStatus.DRAFT: {
            MaterialRequestStatus.SUBMITTED,
            MaterialRequestStatus.CANCELLED,
        },
        MaterialRequestStatus.SUBMITTED: {
            MaterialRequestStatus.PARTIALLY_QUOTED,
            MaterialRequestStatus.FULLY_QUOTED,
            MaterialRequestStatus.CANCELLED,
        },
        MaterialRequestStatus.PARTIALLY_QUOTED: {
            MaterialRequestStatus.FULLY_QUOTED,
        },
        MaterialRequestStatus.FULLY_QUOTED: set(),  # Terminal state
        MaterialRequestStatus.CANCELLED: set(),  # Terminal state
    }

    RFQ_TRANSITIONS: dict[RFQStatus, set[RFQStatus]] = {
        RFQStatus.DRAFT: {
            RFQStatus.SENT,
            RFQStatus.CLOSED,
        },
        RFQStatus.SENT: {
            RFQStatus.PARTIALLY_RESPONDED,
            RFQStatus.FULLY_RESPONDED,
            RFQStatus.CLOSED,
        },
        RFQStatus.PARTIALLY_RESPONDED: {
            RFQStatus.FULLY_RESPONDED,
        },
        RFQStatus.FULLY_RESPONDED: {
            RFQStatus.CLOSED,
        },
        RFQStatus.CLOSED: set(),  # Terminal state
    }

    PURCHASE_ORDER_TRANSITIONS: dict[PurchaseOrderStatus, set[PurchaseOrderStatus]] = {
        PurchaseOrderStatus.DRAFT: {
            PurchaseOrderStatus.SUBMITTED,
            PurchaseOrderStatus.CANCELLED,
        },
        PurchaseOrderStatus.SUBMITTED: {
            PurchaseOrderStatus.PARTIALLY_RECEIVED,
            PurchaseOrderStatus.FULLY_RECEIVED,
            PurchaseOrderStatus.CANCELLED,
        },
        PurchaseOrderStatus.PARTIALLY_RECEIVED: {
            PurchaseOrderStatus.FULLY_RECEIVED,
        },
        PurchaseOrderStatus.FULLY_RECEIVED: {
            PurchaseOrderStatus.CLOSED,
        },
        PurchaseOrderStatus.CLOSED: set(),  # Terminal state
        PurchaseOrderStatus.CANCELLED: set(),  # Terminal state
    }

    def __init__(self, document_type: str):
        """
        Initialize state machine for a specific document type

        Args:
            document_type: Type of document (MATERIAL_REQUEST, RFQ, PURCHASE_ORDER)
        """
        self.document_type = document_type.upper()

        # Select the appropriate transition map
        if self.document_type == "MATERIAL_REQUEST":
            self.transitions = self.MATERIAL_REQUEST_TRANSITIONS
        elif self.document_type == "RFQ":
            self.transitions = self.RFQ_TRANSITIONS
        elif self.document_type == "PURCHASE_ORDER":
            self.transitions = self.PURCHASE_ORDER_TRANSITIONS
        else:
            raise ValueError(f"Unknown document type: {document_type}")

    def can_transition(self, from_status: str, to_status: str) -> bool:
        """
        Check if a status transition is valid

        Args:
            from_status: Current status
            to_status: Target status

        Returns:
            True if transition is valid, False otherwise
        """
        # Convert string statuses to enum values
        try:
            if self.document_type == "MATERIAL_REQUEST":
                from_enum = MaterialRequestStatus(from_status.lower())
                to_enum = MaterialRequestStatus(to_status.lower())
            elif self.document_type == "RFQ":
                from_enum = RFQStatus(from_status.lower())
                to_enum = RFQStatus(to_status.lower())
            elif self.document_type == "PURCHASE_ORDER":
                from_enum = PurchaseOrderStatus(from_status.lower())
                to_enum = PurchaseOrderStatus(to_status.lower())
            else:
                return False
        except (ValueError, KeyError):
            return False

        # Check if transition is allowed
        allowed_transitions = self.transitions.get(from_enum, set())
        return to_enum in allowed_transitions

    def validate_transition(self, from_status: str, to_status: str) -> None:
        """
        Validate a status transition and raise an exception if invalid

        Args:
            from_status: Current status
            to_status: Target status

        Raises:
            ValueError: If transition is not valid
        """
        # Check if current status is a terminal state
        if self.is_terminal_state(from_status):
            raise ValueError(
                f"Cannot transition from terminal state '{from_status}' for {self.document_type}. "
                f"Terminal states do not allow any further status transitions."
            )

        if not self.can_transition(from_status, to_status):
            # Get allowed transitions for error message
            try:
                if self.document_type == "MATERIAL_REQUEST":
                    from_enum = MaterialRequestStatus(from_status.lower())
                elif self.document_type == "RFQ":
                    from_enum = RFQStatus(from_status.lower())
                elif self.document_type == "PURCHASE_ORDER":
                    from_enum = PurchaseOrderStatus(from_status.lower())
                else:
                    from_enum = None

                if from_enum:
                    allowed = self.transitions.get(from_enum, set())
                    allowed_str = (
                        ", ".join([s.value for s in allowed]) if allowed else "none"
                    )
                else:
                    allowed_str = "unknown"
            except (ValueError, KeyError):
                allowed_str = "unknown"

            raise ValueError(
                f"Invalid status transition for {self.document_type}: "
                f"cannot transition from '{from_status}' to '{to_status}'. "
                f"Allowed transitions from '{from_status}': {allowed_str}"
            )

    def get_allowed_transitions(self, from_status: str) -> set[str]:
        """
        Get all allowed transitions from a given status

        Args:
            from_status: Current status

        Returns:
            Set of allowed target statuses
        """
        try:
            if self.document_type == "MATERIAL_REQUEST":
                from_enum = MaterialRequestStatus(from_status.lower())
            elif self.document_type == "RFQ":
                from_enum = RFQStatus(from_status.lower())
            elif self.document_type == "PURCHASE_ORDER":
                from_enum = PurchaseOrderStatus(from_status.lower())
            else:
                return set()

            allowed = self.transitions.get(from_enum, set())
            return {s.value for s in allowed}
        except (ValueError, KeyError):
            return set()

    def is_terminal_state(self, status: str) -> bool:
        """
        Check if a status is a terminal state (no further transitions allowed)

        Args:
            status: Status to check

        Returns:
            True if status is terminal, False otherwise
        """
        allowed = self.get_allowed_transitions(status)
        return len(allowed) == 0
