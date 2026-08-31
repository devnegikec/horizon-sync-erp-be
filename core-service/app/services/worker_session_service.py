"""Worker login session service (PR-14 / T-14, WF-009).

``start_session`` / ``touch`` / ``end_session`` track a worker's handheld
login session and enforce the idle timeout (``pick.session_timeout_minutes``).

Login lockout (``login_lockout_attempts``) is enforced on the identity
``users`` table, so it no longer lives here.

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
from app.models.worker_session import WorkerSession, WorkerSessionStatus


class WorkerSessionService:
    def __init__(
        self,
        db: Session,
        timeout_minutes: int | None = None,
    ):
        self.db = db
        self._timeout_minutes = timeout_minutes

    # -- config -------------------------------------------------------------

    def _timeout_for(self, org_id: UUID) -> int:
        if self._timeout_minutes is not None:
            return self._timeout_minutes
        from app.services.pick_settings_service import PickConfigResolver

        return PickConfigResolver.from_org(self.db, org_id).get_int(
            "session_timeout_minutes"
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
