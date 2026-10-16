"""Worker login session endpoints (PR-14 / T-14, WF-009).

- ``POST /login`` starts a login session for a worker (after lockout check).
- ``POST /{session_id}/touch`` refreshes the idle timeout (rejects expired sessions).
- ``POST /{session_id}/end`` explicitly ends a session.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.worker_session import (
    WorkerSessionLoginRequest,
    WorkerSessionResponse,
)
from app.services.worker_session_service import (
    WorkerSessionService,
    _to_dict,
)

router = APIRouter()


def _worker_exists(worker_id: UUID) -> bool:
    """Check a ``warehouse_worker`` exists in the identity-service ``users`` table.

    ``users`` lives in the identity database, not the core database, so the
    check runs against a read-only identity engine.
    """
    from sqlalchemy import create_engine

    from app.config import settings

    if not settings.identity_database_url:
        return False
    engine = create_engine(settings.identity_database_url, pool_size=2, max_overflow=0)
    try:
        with engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT 1 FROM users "
                    "WHERE id=:id AND user_type='warehouse_worker'"
                ),
                {"id": worker_id},
            ).fetchone()
        return row is not None
    except Exception:  # noqa: BLE001 — surface as "worker not found"
        return False
    finally:
        engine.dispose()


@router.post(
    "/login",
    response_model=WorkerSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a worker login session",
    description="Start a handheld login session for a worker (WF-009)",
)
async def start_worker_session(
    data: WorkerSessionLoginRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Start a worker login session.

    Verifies the worker exists (as a ``users`` row) and creates an active
    session with the org's idle timeout. Lockout is enforced on the identity
    side at login.

    Requirements: WF-009
    """
    org_id = current_user.organization_id
    if not _worker_exists(data.worker_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found"
        )

    service = WorkerSessionService(db)
    session = service.start_session(org_id, data.worker_id)
    timeout = service._timeout_for(org_id)
    return WorkerSessionResponse(**_to_dict(session, timeout))


@router.post(
    "/{session_id}/touch",
    response_model=WorkerSessionResponse,
    summary="Refresh a worker session",
    description="Refresh the idle timeout; rejects an expired session (WF-009)",
)
async def touch_worker_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Refresh a worker session's idle timeout.

    Returns HTTP 401 when the session has expired (idle time exceeded the
    org's ``session_timeout_minutes``) or is no longer active.

    Requirements: WF-009
    """
    service = WorkerSessionService(db)
    try:
        session = service.touch(session_id, current_user.organization_id)
    except Exception as exc:  # noqa: BLE001 - surface as 401
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))

    timeout = service._timeout_for(current_user.organization_id)
    return WorkerSessionResponse(**_to_dict(session, timeout))


@router.post(
    "/{session_id}/end",
    response_model=WorkerSessionResponse,
    summary="End a worker session",
    description="Explicitly end a worker login session (WF-009)",
)
async def end_worker_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Explicitly end a worker login session.

    Requirements: WF-009
    """
    service = WorkerSessionService(db)
    session = service.end_session(session_id, current_user.organization_id)
    timeout = service._timeout_for(current_user.organization_id)
    return WorkerSessionResponse(**_to_dict(session, timeout))
