"""ERP sync outbound queue service (PR-13 / T-13, WF-022, ALT-009).

- ``enqueue`` queues an outbound status-update message for the ERP (SAP),
  deduplicating against an existing pending message for the same entity/operation.
- ``flush_pending`` delivers all due pending messages; success marks them
  ``sent``, a transient failure schedules an exponential-backoff retry, and
  exhausting the retry budget marks the message ``failed`` and raises a
  best-effort in-app failure alert (ALT-009, ``NotificationType.ERP_SYNC_FAILED``).
- The transport is a pluggable callable. The default no-op transport logs and
  succeeds (dequeues) — the real SAP transport is a documented extension point.

Retry budget and backoff are configurable per organization via
``pick.erp_sync_max_retries`` / ``pick.erp_sync_retry_backoff_minutes`` (and
overridable at construction for tests).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.erp_sync_message import ErpSyncMessage, ErpSyncStatus

logger = logging.getLogger(__name__)

DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_MINUTES = 5

#: Transport signature: callable(ErpSyncMessage) -> None (raises on failure).
ErpTransport = Callable[[ErpSyncMessage], None]


def _noop_transport(message: ErpSyncMessage) -> None:
    """Default transport: no SAP wire-up yet — log and dequeue as a no-op."""
    logger.info(
        "ERP sync transport not configured; dequeueing %s as no-op",
        message.id,
    )


class ErpSyncService:
    def __init__(
        self,
        db: Session,
        transport: ErpTransport | None = None,
        max_retries: int | None = None,
        backoff_minutes: int | None = None,
    ):
        self.db = db
        self._transport = transport or _noop_transport
        self._max_retries = max_retries
        self._backoff_minutes = backoff_minutes

    # -- config -------------------------------------------------------------

    def _max_retries_for(self, org_id: UUID) -> int:
        if self._max_retries is not None:
            return self._max_retries
        from app.services.pick_settings_service import PickConfigResolver

        return PickConfigResolver.from_org(self.db, org_id).get_int(
            "erp_sync_max_retries"
        )

    def _backoff_for(self, org_id: UUID) -> int:
        if self._backoff_minutes is not None:
            return self._backoff_minutes
        from app.services.pick_settings_service import PickConfigResolver

        return PickConfigResolver.from_org(self.db, org_id).get_int(
            "erp_sync_retry_backoff_minutes"
        )

    # -- enqueue ------------------------------------------------------------

    def enqueue(
        self,
        org_id: UUID,
        entity_type: str,
        entity_id: UUID,
        operation: str,
        payload: dict[str, Any] | None = None,
        user_id: UUID | None = None,
        pick_list_id: UUID | None = None,
        dispatch_record_id: UUID | None = None,
    ) -> ErpSyncMessage:
        """Queue an outbound sync message (dedup against pending messages).

        Returns the existing pending message when one already exists for the
        same (entity_type, entity_id, operation) so repeated triggers do not
        duplicate the queue.
        """
        existing = (
            self.db.query(ErpSyncMessage)
            .filter(
                ErpSyncMessage.organization_id == org_id,
                ErpSyncMessage.entity_type == entity_type,
                ErpSyncMessage.entity_id == entity_id,
                ErpSyncMessage.operation == operation,
                ErpSyncMessage.status == ErpSyncStatus.PENDING.value,
            )
            .first()
        )
        if existing is not None:
            return existing

        message = ErpSyncMessage(
            organization_id=org_id,
            entity_type=entity_type,
            entity_id=entity_id,
            operation=operation,
            payload=payload or {},
            pick_list_id=pick_list_id,
            dispatch_record_id=dispatch_record_id,
            created_by=user_id,
            status=ErpSyncStatus.PENDING.value,
            attempt_count=0,
            max_attempts=self._max_retries_for(org_id),
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    # -- flush --------------------------------------------------------------

    def flush_pending(self, org_id: UUID, now: datetime | None = None) -> dict:
        """Deliver all due pending messages; returns a summary dict.

        ``now`` is injectable so retry/backoff timing is deterministic in tests.
        """
        now = now or datetime.now(UTC)
        messages = (
            self.db.query(ErpSyncMessage)
            .filter(
                ErpSyncMessage.organization_id == org_id,
                ErpSyncMessage.status == ErpSyncStatus.PENDING.value,
            )
            .all()
        )
        due = [
            m
            for m in messages
            if m.next_attempt_at is None
            or (
                m.next_attempt_at.tzinfo is None
                and m.next_attempt_at.replace(tzinfo=UTC) <= now
            )
            or m.next_attempt_at <= now
        ]

        sent = 0
        failed = 0
        retried = 0
        for message in due:
            outcome = self._attempt(message, now)
            if outcome == "sent":
                sent += 1
            elif outcome == "retried":
                retried += 1
            else:
                failed += 1

        if due:
            self.db.commit()
        return {
            "processed": len(due),
            "sent": sent,
            "retried": retried,
            "failed": failed,
        }

    def _attempt(self, message: ErpSyncMessage, now: datetime) -> str:
        try:
            self._transport(message)
        except Exception as exc:  # noqa: BLE001 - integration failure (ALT-009)
            message.attempt_count = (message.attempt_count or 0) + 1
            message.last_error = str(exc)
            if message.attempt_count >= (message.max_attempts or DEFAULT_MAX_RETRIES):
                message.status = ErpSyncStatus.FAILED.value
                self._alert(message)
                return "failed"
            backoff = self._backoff_for(message.organization_id)
            message.next_attempt_at = now + timedelta(
                minutes=backoff * (2 ** (message.attempt_count - 1))
            )
            return "retried"
        else:
            message.status = ErpSyncStatus.SENT.value
            message.sent_at = now
            message.next_attempt_at = None
            return "sent"

    def _alert(self, message: ErpSyncMessage) -> None:
        """Best-effort in-app failure alert (ALT-009). Never raises."""
        try:
            from app.models.base import NotificationType
            from app.services.notification_service import NotificationService

            if message.created_by is None:
                logger.warning(
                    "ERP sync message %s failed but has no created_by; "
                    "skipping in-app alert",
                    message.id,
                )
                return

            NotificationService(self.db).create(
                organization_id=message.organization_id,
                user_id=message.created_by,
                type=NotificationType.ERP_SYNC_FAILED.value,
                title="ERP sync failed",
                message=(
                    f"Outbound sync '{message.operation}' for "
                    f"{message.entity_type} failed after "
                    f"{message.attempt_count} attempt(s): {message.last_error}"
                ),
                entity_type="erp_sync_message",
                entity_id=message.id,
                sender_id=message.created_by,
            )
        except Exception:  # pragma: no cover - defensive
            logger.warning(
                "Failed to deliver ERP sync failure alert for message %s",
                message.id,
                exc_info=True,
            )

    # -- query --------------------------------------------------------------

    def list_messages(
        self,
        org_id: UUID,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ErpSyncMessage], int]:
        q = self.db.query(ErpSyncMessage).filter(
            ErpSyncMessage.organization_id == org_id
        )
        if status is not None:
            q = q.filter(ErpSyncMessage.status == status)
        total = q.count()
        messages = (
            q.order_by(ErpSyncMessage.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return messages, total
