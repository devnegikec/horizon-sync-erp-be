"""Worker login session + lockout service (PR-14 / T-14, WF-009).

- ``start_session`` / ``touch`` / ``end_session`` track a worker's handheld
  login session and enforce the idle timeout (``pick.session_timeout_minutes``).
- ``record_failed_login`` / ``record_successful_login`` / ``is_locked`` enforce
  the login lockout (``pick.login_lockout_attempts``) on ``WMSWorker`` rows.

Idle timeout semantics: a session expires when the time since
``last_active_at`` exceeds the timeout. ``touch`` rejects an expired session
("expired session rejected") and otherwise refreshes ``last_active_at``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException, ValidationError
from app.models.wms_worker import WMSWorker
from app.models.worker_session import WorkerSession, WorkerSessionStatus

#: Fixed window (minutes) a worker stays locked after exceeding failed attempts.
LOCKOUT_WINDOW_MINUTES = 15


class WorkerSessionService:
    def __init__(
        self,
        db: Session,
        timeout_minutes: int | None = None,
        lockout_attempts: int | None = None,
    ):
        self.db = db
        self._timeout_minutes = timeout_minutes
        self._lockout_attempts = lockout_attempts

    # -- config -------------------------------------------------------------

    def _timeout_for(self, org_id: UUID) -> int:
        if self._timeout_minutes is not None:
            return self._timeout_minutes
        from app.services.pick_settings_service import PickConfigResolver

        return PickConfigResolver.from_org(self.db, org_id).get_int(
            "session_timeout_minutes"
        )

    def _attempts_for(self, org_id: UUID) -> int:
        if self._lockout_attempts is not None:
            return self._lockout_attempts
        from app.services.pick_settings_service import PickConfigResolver

        return PickConfigResolver.from_org(self.db, org_id).get_int(
            "login_lockout_attempts"
        )

    # -- sessions -----------------------------------------------------------

    def start_session(
        self,
        org_id: UUID,
        worker_id: UUID,
        now: datetime | None = None,
    ) -> WorkerSession:
        """Create an active login session for a worker."""
        now = now or datetime.now(UTC)
        session = WorkerSession(
            organization_id=org_id,
            worker_id=worker_id,
            status=WorkerSessionStatus.ACTIVE.value,
            last_active_at=now,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def touch(self, session_id: UUID, org_id: UUID, now: datetime | None = None) -> WorkerSession:
        """Refresh the session if not idle-expired.

        Raises:
            ResourceNotFoundException: unknown session.
            ValidationError: session is no longer active (expired/ended) or
                idle time exceeds ``session_timeout_minutes``.
        """
        session = self._get_session(session_id, org_id)
        now = now or datetime.now(UTC)
        timeout = self._timeout_for(org_id)

        idle = now - session.last_active_at
        if idle > timedelta(minutes=timeout):
            session.status = WorkerSessionStatus.EXPIRED.value
            session.ended_at = now
            self.db.commit()
            raise ValidationError(
                f"Session expired after {timeout} minutes of inactivity"
            )

        session.last_active_at = now
        self.db.commit()
        self.db.refresh(session)
        return session

    def end_session(self, session_id: UUID, org_id: UUID) -> WorkerSession:
        """Explicitly end a session."""
        session = self._get_session(session_id, org_id)
        session.status = WorkerSessionStatus.ENDED.value
        session.ended_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(session)
        return session

    def _get_session(self, session_id: UUID, org_id: UUID) -> WorkerSession:
        session = (
            self.db.query(WorkerSession)
            .filter(
                WorkerSession.id == session_id,
                WorkerSession.organization_id == org_id,
            )
            .first()
        )
        if session is None:
            raise ResourceNotFoundException(f"Worker session {session_id} not found")
        if session.status != WorkerSessionStatus.ACTIVE.value:
            raise ValidationError(
                f"Worker session is {session.status} and cannot be used"
            )
        return session

    # -- lockout ------------------------------------------------------------

    @staticmethod
    def is_locked(worker: WMSWorker, now: datetime | None = None) -> bool:
        """Return True if the worker is currently locked out."""
        if worker.locked_until is None:
            return False
        now = now or datetime.now(UTC)
        return worker.locked_until > now

    def record_failed_login(
        self,
        org_id: UUID,
        worker: WMSWorker,
        now: datetime | None = None,
    ) -> None:
        """Increment the failed-attempt counter and lock when the threshold is hit."""
        now = now or datetime.now(UTC)
        worker.failed_login_attempts = (worker.failed_login_attempts or 0) + 1
        attempts = self._attempts_for(org_id)
        if worker.failed_login_attempts >= attempts:
            worker.locked_until = now + timedelta(minutes=LOCKOUT_WINDOW_MINUTES)
        self.db.commit()

    def record_successful_login(
        self,
        worker: WMSWorker,
        now: datetime | None = None,
    ) -> None:
        """Reset the failed-attempt counter and stamp the login time."""
        now = now or datetime.now(UTC)
        worker.failed_login_attempts = 0
        worker.locked_until = None
        worker.last_login_at = now
        self.db.commit()


def _to_dict(session: WorkerSession, timeout_minutes: int) -> dict[str, Any]:
    """Serialize a session for API responses."""
    return {
        "id": str(session.id),
        "organization_id": str(session.organization_id),
        "worker_id": str(session.worker_id),
        "status": session.status,
        "last_active_at": session.last_active_at.isoformat()
        if session.last_active_at
        else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "timeout_minutes": timeout_minutes,
    }
