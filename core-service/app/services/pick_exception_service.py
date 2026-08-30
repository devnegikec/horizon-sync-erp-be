"""Pick exception service (PR-03 / T-02 + T-05).

- ``capture`` raises a reason-coded exception against a pick list item and
  writes the first entry in the immutable audit trail.
- ``list`` / ``get`` / ``get_audit`` expose exceptions and their append-only
  audit trail (audit rows are never mutated once written).
- Reason codes are validated against the tenant's ``pick.reason_codes`` master
  (configurable server-side, NFR-007/NFR-008).

Resolution/approval actions (the supervisor queue) land in PR-09; the audit
model and ``_append_audit`` helper already support those event types.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.pick_exception import (
    _ACTIVE_STATUSES,
    PickException,
    PickExceptionAudit,
    PickExceptionAuditEvent,
    PickExceptionSeverity,
    PickExceptionStatus,
)
from app.models.pick_list import PickList, PickListItem
from app.services.pick_settings_service import PickSettingsService

logger = logging.getLogger(__name__)


class PickExceptionService:
    """Capture and query pick exceptions + their immutable audit trail."""

    def __init__(self, db: Session):
        self.db = db

    # -- reason-code master -------------------------------------------------

    def reason_codes(self, organization_id: UUID) -> list[str]:
        """Return the effective (configurable) reason-code master for an org."""
        value = PickSettingsService(self.db).get_value(organization_id, "reason_codes")
        if isinstance(value, list):
            return [str(item) for item in value]
        return []

    # -- capture ------------------------------------------------------------

    def capture(
        self,
        organization_id: UUID,
        data: dict[str, Any],
        reported_by: UUID | None = None,
    ) -> PickException:
        """Capture a pick exception and write the immutable CAPTURED audit row.

        Raises:
            ResourceNotFoundException: pick list item not found in this org.
            ValidationError: unknown reason code, invalid severity, or an
                active exception with the same reason code already exists for
                the item (duplicate capture rejected).
        """
        pick_list_item_id = data["pick_list_item_id"]
        item = (
            self.db.query(PickListItem)
            .filter(
                PickListItem.id == pick_list_item_id,
                PickListItem.organization_id == organization_id,
            )
            .first()
        )
        if item is None:
            raise ResourceNotFoundException(
                f"Pick list item {pick_list_item_id} not found"
            )

        reason_code = str(data["reason_code"]).strip()
        master = self.reason_codes(organization_id)
        if reason_code not in master:
            allowed = ", ".join(master) if master else "(none configured)"
            raise ValidationError(
                f"Invalid reason code {reason_code!r}. Allowed: {allowed}"
            )

        severity = str(data.get("severity") or PickExceptionSeverity.WARNING.value)
        if severity not in {s.value for s in PickExceptionSeverity}:
            raise ValidationError(
                f"Invalid severity {severity!r}; must be one of "
                f"info, warning, error, critical"
            )

        # Duplicate capture: block a second active exception with the same
        # reason code for the same pick list item.
        duplicate = (
            self.db.query(PickException)
            .filter(
                PickException.organization_id == organization_id,
                PickException.pick_list_item_id == pick_list_item_id,
                PickException.reason_code == reason_code,
                PickException.status.in_(_ACTIVE_STATUSES),
            )
            .first()
        )
        if duplicate is not None:
            raise ValidationError(
                f"An active '{reason_code}' exception already exists for "
                f"pick list item {pick_list_item_id}"
            )

        quantity = data.get("quantity")
        if quantity is not None and not isinstance(quantity, Decimal):
            try:
                quantity = Decimal(str(quantity))
            except Exception:
                quantity = None

        exception = PickException(
            organization_id=organization_id,
            pick_list_id=item.pick_list_id,
            pick_list_item_id=pick_list_item_id,
            reason_code=reason_code,
            severity=severity,
            reported_by=reported_by,
            status=PickExceptionStatus.OPEN.value,
            quantity=quantity,
            note=data.get("note"),
            details=data.get("details"),
        )
        self.db.add(exception)
        self.db.flush()

        self._append_audit(
            exception,
            PickExceptionAuditEvent.CAPTURED,
            actor_id=reported_by,
            from_state=None,
            to_state=PickExceptionStatus.OPEN.value,
            details={"reason_code": reason_code, "severity": severity},
        )

        self.db.commit()
        self.db.refresh(exception)
        return exception

    # -- queries ------------------------------------------------------------

    def list_exceptions(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        pick_list_id: UUID | None = None,
        pick_list_item_id: UUID | None = None,
        reason_code: str | None = None,
        severity: str | None = None,
        status_filter: str | None = None,
        warehouse_id: UUID | None = None,
    ) -> tuple[list[PickException], dict[str, Any]]:
        """Paginated, filtered list of pick exceptions for an organization."""
        query = self.db.query(PickException).filter(
            PickException.organization_id == organization_id
        )
        if pick_list_id is not None:
            query = query.filter(PickException.pick_list_id == pick_list_id)
        if pick_list_item_id is not None:
            query = query.filter(
                PickException.pick_list_item_id == pick_list_item_id
            )
        if reason_code is not None:
            query = query.filter(PickException.reason_code == reason_code)
        if severity is not None:
            query = query.filter(PickException.severity == severity)
        if status_filter is not None:
            query = query.filter(PickException.status == status_filter)
        if warehouse_id is not None:
            query = query.join(
                PickList, PickException.pick_list_id == PickList.id
            ).filter(PickList.warehouse_id == warehouse_id)

        total = query.count()
        items = (
            query.order_by(PickException.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
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
        return items, pagination

    def get(self, organization_id: UUID, exception_id: UUID) -> PickException:
        """Return one pick exception, scoped to the organization."""
        exception = (
            self.db.query(PickException)
            .filter(
                PickException.id == exception_id,
                PickException.organization_id == organization_id,
            )
            .first()
        )
        if exception is None:
            raise ResourceNotFoundException(
                f"Pick exception {exception_id} not found"
            )
        return exception

    def get_audit(
        self, organization_id: UUID, exception_id: UUID
    ) -> list[PickExceptionAudit]:
        """Return the append-only audit trail for an exception, oldest first."""
        # Ensure the exception exists in this org (404 otherwise).
        self.get(organization_id, exception_id)
        return (
            self.db.query(PickExceptionAudit)
            .filter(
                PickExceptionAudit.exception_id == exception_id,
                PickExceptionAudit.organization_id == organization_id,
            )
            .order_by(PickExceptionAudit.created_at.asc())
            .all()
        )

    # -- supervisor actions (PR-09 / T-03) -----------------------------------

    def resolve(
        self,
        organization_id: UUID,
        exception_id: UUID,
        resolution: str,
        resolved_by: UUID | None = None,
    ) -> PickException:
        """Resolve an open/approved exception with a recorded resolution.

        Writes an immutable RESOLVED audit row and best-effort in-app alert to
        the reporter (Q11).

        Raises:
            ValidationError: if the exception is already resolved/cancelled.
        """
        exception = self.get(organization_id, exception_id)
        if exception.status in {
            PickExceptionStatus.RESOLVED.value,
            PickExceptionStatus.CANCELLED.value,
        }:
            raise ValidationError(
                f"Cannot resolve pick exception with status '{exception.status}'"
            )

        from_state = exception.status
        exception.status = PickExceptionStatus.RESOLVED.value
        exception.resolution = resolution

        self._append_audit(
            exception,
            PickExceptionAuditEvent.RESOLVED,
            actor_id=resolved_by,
            from_state=from_state,
            to_state=PickExceptionStatus.RESOLVED.value,
            details={"resolution": resolution},
        )
        self.db.commit()
        self.db.refresh(exception)
        self._notify_reporter(exception, "resolved", resolved_by)
        return exception

    def approve(
        self,
        organization_id: UUID,
        exception_id: UUID,
        approver: UUID | None,
        decision: str,
    ) -> PickException:
        """Approve or reject an exception (supervisor decision).

        Sets the approver + approved_at and moves the status to
        ``approved``/``rejected``, writing an immutable audit row and a
        best-effort in-app alert to the reporter (Q11).

        Raises:
            ValidationError: invalid decision, or exception already
                resolved/cancelled.
        """
        exception = self.get(organization_id, exception_id)

        if decision not in {
            PickExceptionStatus.APPROVED.value,
            PickExceptionStatus.REJECTED.value,
        }:
            raise ValidationError(
                f"Invalid decision {decision!r}; must be 'approved' or 'rejected'"
            )
        if exception.status in {
            PickExceptionStatus.RESOLVED.value,
            PickExceptionStatus.CANCELLED.value,
        }:
            raise ValidationError(
                f"Cannot {decision} pick exception with status '{exception.status}'"
            )

        from_state = exception.status
        exception.approver = approver
        exception.approved_at = datetime.now(UTC)
        exception.status = decision
        self._append_audit(
            exception,
            PickExceptionAuditEvent(decision),
            actor_id=approver,
            from_state=from_state,
            to_state=decision,
        )
        self.db.commit()
        self.db.refresh(exception)
        self._notify_reporter(exception, decision, approver)
        return exception

    def _notify_reporter(
        self,
        exception: PickException,
        event: str,
        actor_id: UUID | None,
    ) -> None:
        """Best-effort in-app alert to the reporter (Q11, email/notification).

        Never raises: alert delivery must not break the queue workflow.
        """
        if exception.reported_by is None:
            return
        try:
            from app.models.base import NotificationType
            from app.services.notification_service import NotificationService

            NotificationService(self.db).create(
                organization_id=exception.organization_id,
                user_id=exception.reported_by,
                type=NotificationType.PICK_EXCEPTION.value,
                title=f"Pick exception {event}",
                message=(
                    f"Your pick exception '{exception.reason_code}' was {event}."
                ),
                entity_type="pick_exception",
                entity_id=exception.id,
                sender_id=actor_id,
            )
        except Exception:  # pragma: no cover - defensive
            logger.warning(
                "Failed to deliver in-app alert for pick exception %s",
                exception.id,
                exc_info=True,
            )

    # -- audit helper (append-only) -----------------------------------------

    def _append_audit(
        self,
        exception: PickException,
        event_type: PickExceptionAuditEvent,
        actor_id: UUID | None,
        from_state: str | None,
        to_state: str | None,
        details: dict[str, Any] | None = None,
    ) -> PickExceptionAudit:
        """Insert an immutable audit row. Never updates or deletes."""
        event = PickExceptionAudit(
            organization_id=exception.organization_id,
            exception_id=exception.id,
            event_type=event_type.value,
            actor_id=actor_id,
            from_state=from_state,
            to_state=to_state,
            details=details,
        )
        self.db.add(event)
        return event

    # -- serialization ------------------------------------------------------

    @staticmethod
    def _serialize(exception: PickException) -> dict[str, Any]:
        return {
            "id": exception.id,
            "organization_id": exception.organization_id,
            "pick_list_id": exception.pick_list_id,
            "pick_list_item_id": exception.pick_list_item_id,
            "reason_code": exception.reason_code,
            "severity": exception.severity,
            "reported_by": exception.reported_by,
            "status": exception.status,
            "resolution": exception.resolution,
            "approver": exception.approver,
            "approved_at": exception.approved_at,
            "quantity": exception.quantity,
            "note": exception.note,
            "details": exception.details,
            "created_at": exception.created_at,
            "updated_at": exception.updated_at,
        }

    @staticmethod
    def _serialize_audit(event: PickExceptionAudit) -> dict[str, Any]:
        return {
            "id": event.id,
            "exception_id": event.exception_id,
            "event_type": event.event_type,
            "actor_id": event.actor_id,
            "from_state": event.from_state,
            "to_state": event.to_state,
            "details": event.details,
            "created_at": event.created_at,
        }


__all__ = ["PickExceptionService"]
