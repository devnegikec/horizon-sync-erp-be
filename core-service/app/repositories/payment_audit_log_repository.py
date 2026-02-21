"""Payment audit log repository for database operations"""

from uuid import UUID
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.payment_audit_log import PaymentAuditLog


class PaymentAuditLogRepository:
    """Repository for payment audit log database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> PaymentAuditLog:
        """
        Create a new payment audit log entry.

        Args:
            data: Dictionary containing audit log data (must include organization_id)

        Returns:
            Created PaymentAuditLog object

        Note:
            Audit logs are append-only. No IntegrityError is expected.
        """
        audit_log = PaymentAuditLog(**data)
        self.db.add(audit_log)
        self.db.commit()
        self.db.refresh(audit_log)
        return audit_log

    def get_by_payment_id(
        self, payment_id: UUID, organization_id: UUID
    ) -> list[PaymentAuditLog]:
        """
        Get all audit log entries for a payment, ordered by timestamp DESC (newest first).

        Args:
            payment_id: Payment entry UUID
            organization_id: Organization UUID for multi-tenancy isolation

        Returns:
            List of PaymentAuditLog objects for the payment, ordered by timestamp DESC
        """
        return (
            self.db.query(PaymentAuditLog)
            .filter(
                PaymentAuditLog.payment_id == payment_id,
                PaymentAuditLog.organization_id == organization_id,
            )
            .order_by(PaymentAuditLog.timestamp.desc())
            .all()
        )

    def list_by_organization(
        self,
        organization_id: UUID,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PaymentAuditLog], int]:
        """
        List audit log entries for an organization with optional date filtering and pagination.

        Args:
            organization_id: Organization UUID for multi-tenancy isolation
            date_from: Optional start date for filtering (inclusive)
            date_to: Optional end date for filtering (inclusive)
            page: Page number (1-indexed)
            page_size: Number of records per page

        Returns:
            Tuple of (list of PaymentAuditLog objects, total count)
        """
        query = self.db.query(PaymentAuditLog).filter(
            PaymentAuditLog.organization_id == organization_id
        )

        # Apply date filtering if provided
        if date_from is not None:
            query = query.filter(PaymentAuditLog.timestamp >= date_from)
        if date_to is not None:
            query = query.filter(PaymentAuditLog.timestamp <= date_to)

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination and ordering
        offset = (page - 1) * page_size
        audit_logs = (
            query.order_by(PaymentAuditLog.timestamp.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return audit_logs, total_count
