"""Pick exception endpoints (PR-03 / T-02 + T-05).

Reason-code & exception framework with an immutable audit trail:

- ``GET  /reason-codes``  → effective reason-code master (configurable).
- ``POST ``               → capture a pick exception (writes audit CAPTURED).
- ``GET  ``               → paginated, filterable list.
- ``GET  /{id}``          → single exception.
- ``GET  /{id}/audit``    → append-only audit trail (WF-023 / NFR-005).

Capture requires ``pick_list.update`` (picker raises an exception during pick
execution); reads require ``pick_list.read``. Resolution/approval endpoints
arrive with the supervisor queue (PR-09).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import PICK_LIST_READ, PICK_LIST_UPDATE
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.common import PaginationMeta
from app.schemas.pick_exception import (
    PickExceptionAuditItem,
    PickExceptionAuditResponse,
    PickExceptionCreate,
    PickExceptionListResponse,
    PickExceptionResponse,
    PickReasonCodesResponse,
)
from app.services.pick_exception_service import PickExceptionService

router = APIRouter()


@router.get(
    "/reason-codes",
    response_model=PickReasonCodesResponse,
    status_code=status.HTTP_200_OK,
    summary="List effective pick exception reason codes",
)
async def get_reason_codes(
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
) -> PickReasonCodesResponse:
    """Return the tenant's configurable reason-code master (pick.reason_codes)."""
    svc = PickExceptionService(db)
    return PickReasonCodesResponse(
        reason_codes=svc.reason_codes(current_user.organization_id)
    )


@router.post(
    "",
    response_model=PickExceptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Capture a pick exception",
)
async def capture_pick_exception(
    body: PickExceptionCreate,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_UPDATE)),
    db: Session = Depends(get_db),
) -> PickExceptionResponse:
    """Raise a reason-coded exception against a pick list item."""
    svc = PickExceptionService(db)
    exception = svc.capture(
        organization_id=current_user.organization_id,
        data=body.model_dump(),
        reported_by=current_user.id,
    )
    return PickExceptionResponse.model_validate(
        PickExceptionService._serialize(exception)
    )


@router.get(
    "",
    response_model=PickExceptionListResponse,
    status_code=status.HTTP_200_OK,
    summary="List pick exceptions",
)
async def list_pick_exceptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    pick_list_id: UUID | None = None,
    pick_list_item_id: UUID | None = None,
    reason_code: str | None = None,
    severity: str | None = Query(
        None, pattern="^(info|warning|error|critical)$"
    ),
    status_filter: str | None = Query(
        None,
        alias="status",
        pattern="^(open|approved|rejected|resolved|cancelled)$",
    ),
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
) -> PickExceptionListResponse:
    """Paginated, filterable list of pick exceptions for the organization."""
    svc = PickExceptionService(db)
    items, pagination = svc.list_exceptions(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        pick_list_id=pick_list_id,
        pick_list_item_id=pick_list_item_id,
        reason_code=reason_code,
        severity=severity,
        status_filter=status_filter,
    )
    return PickExceptionListResponse(
        exceptions=[
            PickExceptionResponse.model_validate(
                PickExceptionService._serialize(item)
            )
            for item in items
        ],
        pagination=PaginationMeta(**pagination),
    )


@router.get(
    "/{exception_id}/audit",
    response_model=PickExceptionAuditResponse,
    status_code=status.HTTP_200_OK,
    summary="Get the immutable audit trail for a pick exception",
)
async def get_pick_exception_audit(
    exception_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
) -> PickExceptionAuditResponse:
    """Return append-only audit events for the exception, oldest first."""
    svc = PickExceptionService(db)
    events = svc.get_audit(current_user.organization_id, exception_id)
    return PickExceptionAuditResponse(
        exception_id=exception_id,
        events=[
            PickExceptionAuditItem.model_validate(
                PickExceptionService._serialize_audit(event)
            )
            for event in events
        ],
    )


@router.get(
    "/{exception_id}",
    response_model=PickExceptionResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a pick exception",
)
async def get_pick_exception(
    exception_id: UUID,
    current_user: CurrentUser = Depends(require_permission(PICK_LIST_READ)),
    db: Session = Depends(get_db),
) -> PickExceptionResponse:
    """Return a single pick exception."""
    svc = PickExceptionService(db)
    exception = svc.get(current_user.organization_id, exception_id)
    return PickExceptionResponse.model_validate(
        PickExceptionService._serialize(exception)
    )
