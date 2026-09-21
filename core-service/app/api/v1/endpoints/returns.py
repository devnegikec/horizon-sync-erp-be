"""Returns API endpoints — R-01 → R-08.

Two audiences share this router, mirroring the inbound split:

* **Web app / back office** — registration (R-01), reference lookup (R-02),
  note approval + disposition (R-06), put-away generation (R-07), Return Slip
  (R-08).
* **Handheld / dock** — sessions, scans and condition capture (R-03, R-04).

Contract: ``RETURNS_WEB_APP_INTEGRATION.md`` and
``RETURNS_HANDHELD_INTEGRATION.md``.
"""

from math import ceil
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    INBOUND_EXCEPTION_CREATE,
    RETURN_APPROVE,
    RETURN_CLASSIFY,
    RETURN_DISPOSE,
    RETURN_READ,
    RETURN_RECEIVE,
    RETURN_REGISTER,
    WMS_SCAN,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.inbound import InboundExceptionResponse
from app.schemas.returns import (
    ApproveNoteRequest,
    CancelRegistrationRequest,
    ClassifyBulkRequest,
    ClassifyItemRequest,
    ClassifyResponse,
    CreateRegistrationRequest,
    DispositionRequest,
    EndReturnSessionRequest,
    EndReturnSessionResponse,
    GeneratePutAwayRequest,
    GeneratePutAwayResponse,
    NoteActionResponse,
    ReceiptNoteDetail,
    ReceiptNoteListResponse,
    ReferenceLookupResponse,
    RegistrationDetail,
    RegistrationListResponse,
    RejectNoteRequest,
    ReturnScanRequest,
    ReturnScanResponse,
    ReturnSessionDetail,
    ReturnSessionResponse,
    ReturnSlipResponse,
    ReturnUnreadableReportRequest,
    StartReturnSessionRequest,
)
from app.services.inbound_exception_service import InboundExceptionService
from app.services.return_service import ReturnService

router = APIRouter()

ERR_201 = status.HTTP_201_CREATED


def _service(db: Session) -> ReturnService:
    return ReturnService(db)


# =====================================================================
# R-02 — reference lookup (web app)
# =====================================================================


@router.get(
    "/references",
    response_model=ReferenceLookupResponse,
    summary="Resolve a return reference",
    description=(
        "Resolve the invoice/dealer/warehouse triple so the operator picks from "
        "real records instead of typing free text (R-02). Read-only and safe to "
        "call on every keystroke with debounce."
    ),
)
async def lookup_reference(
    invoice_no: str | None = Query(None, max_length=100),
    party_id: UUID | None = Query(None),
    warehouse_id: UUID | None = Query(None),
    current_user: CurrentUser = Depends(
        require_permission(RETURN_READ, RETURN_REGISTER)
    ),
    db: Session = Depends(get_db),
):
    service = _service(db)
    return service.lookup_reference(
        current_user.organization_id,
        invoice_no=invoice_no,
        party_id=party_id,
        warehouse_id=warehouse_id,
    )


# =====================================================================
# R-01 — registrations (web app)
# =====================================================================


@router.post(
    "/registrations",
    response_model=RegistrationDetail,
    status_code=ERR_201,
    summary="Register a return",
    description="Declare a return against an invoice/dealer/warehouse reference (R-01).",
)
async def create_registration(
    data: CreateRegistrationRequest,
    current_user: CurrentUser = Depends(require_permission(RETURN_REGISTER)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    registration = service.create_registration(
        current_user.organization_id, current_user.id, data
    )
    db.commit()
    return service.serialize_registration(
        service.get_registration(registration.id, current_user.organization_id)
    )


@router.get(
    "/registrations",
    response_model=RegistrationListResponse,
    summary="List return registrations",
    description="Filter by status, warehouse, dealer or invoice (R-01).",
)
async def list_registrations(
    status_filter: str | None = Query(None, alias="status"),
    warehouse_id: UUID | None = Query(None),
    party_id: UUID | None = Query(None),
    invoice_no: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current_user: CurrentUser = Depends(require_permission(RETURN_READ)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    rows, total = service.list_registrations(
        current_user.organization_id,
        status=status_filter,
        warehouse_id=warehouse_id,
        party_id=party_id,
        invoice_no=invoice_no,
        page=page,
        page_size=page_size,
    )
    total_pages = ceil(total / page_size) if page_size else 0
    return {
        "items": [service.serialize_registration_list_item(r) for r in rows],
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }


@router.get(
    "/registrations/{registration_id}",
    response_model=RegistrationDetail,
    summary="Get a return registration",
    description="Detail used by the review screen and the handheld's expected list (R-01).",
)
async def get_registration(
    registration_id: UUID,
    current_user: CurrentUser = Depends(require_permission(RETURN_READ)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    return service.serialize_registration(
        service.get_registration(registration_id, current_user.organization_id)
    )


@router.post(
    "/registrations/{registration_id}/cancel",
    response_model=RegistrationDetail,
    summary="Cancel a return registration",
    description="Allowed until the first unit is scanned (R-01).",
)
async def cancel_registration(
    registration_id: UUID,
    data: CancelRegistrationRequest | None = None,
    current_user: CurrentUser = Depends(require_permission(RETURN_REGISTER)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    registration = service.cancel_registration(
        registration_id,
        current_user.organization_id,
        current_user.id,
        data.reason if data else None,
    )
    db.commit()
    return service.serialize_registration(registration)


# =====================================================================
# R-03 — handheld sessions
# =====================================================================


@router.post(
    "/registrations/{registration_id}/sessions",
    response_model=ReturnSessionResponse,
    status_code=ERR_201,
    summary="Open a return receiving session",
    description="One open session per registration; a second call returns 409 (R-03).",
)
async def start_session(
    registration_id: UUID,
    data: StartReturnSessionRequest | None = None,
    current_user: CurrentUser = Depends(require_permission(RETURN_RECEIVE)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    session = service.start_session(
        registration_id,
        current_user.organization_id,
        current_user.id,
        data.dock_location if data else None,
        data.device_id if data else None,
    )
    db.commit()
    return service.serialize_session(session, detailed=False)


@router.get(
    "/sessions/{session_id}",
    response_model=ReturnSessionDetail,
    summary="Resume / poll a return session",
    description=(
        "Header, per-line counters and the pending queue. "
        "``condition: null`` marks a unit that still needs classification (R-03)."
    ),
)
async def get_session(
    session_id: UUID,
    current_user: CurrentUser = Depends(require_permission(RETURN_READ)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    session = service.get_session(session_id, current_user.organization_id)
    return service.serialize_session(session, detailed=True)


@router.post(
    "/sessions/{session_id}/scans",
    response_model=ReturnScanResponse,
    status_code=ERR_201,
    summary="Scan a returned unit",
    description="Validates the identity against the registration and hard-stops duplicates (R-03).",
)
async def record_scan(
    session_id: UUID,
    data: ReturnScanRequest,
    current_user: CurrentUser = Depends(require_permission(RETURN_RECEIVE, WMS_SCAN)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    item = service.record_scan(
        session_id,
        current_user.organization_id,
        current_user.id,
        data.qr_data,
        data.device_type,
        data.os,
    )
    result = service.serialize_scan(item)
    db.commit()
    return result


@router.post(
    "/sessions/{session_id}/unreadable",
    response_model=InboundExceptionResponse,
    status_code=ERR_201,
    summary="Report an unreadable / unscannable label on a return",
    description=(
        "Record a carton whose label cannot be scanned while receiving a return "
        "(G-Q1). Nothing is decoded and no stock is created: the carton reference "
        "is parked as a `QR_UNREADABLE` HOLD exception awaiting approval, the "
        "supervisors are alerted, and no return counter moves. Reporting the same "
        "carton twice in one session returns `409 EXCEPTION_ALREADY_ACTIVE`. "
        "The operator never supplies an identity — `carton_reference` is read off "
        "the carton."
    ),
)
async def report_unreadable_return(
    session_id: UUID,
    data: ReturnUnreadableReportRequest,
    current_user: CurrentUser = Depends(
        require_permission(RETURN_RECEIVE, INBOUND_EXCEPTION_CREATE)
    ),
    db: Session = Depends(get_db),
):
    service = InboundExceptionService(db)
    exception = service.record_unreadable_qr_for_return_session(
        organization_id=current_user.organization_id,
        session_id=session_id,
        carton_reference=data.carton_reference,
        actor_id=current_user.id,
        sku=data.sku,
        batch_number=data.batch_number,
        quantity=data.quantity,
        note=data.note,
    )
    return InboundExceptionResponse(**service.serialize(exception))


@router.post(
    "/sessions/{session_id}/classify",
    response_model=ClassifyResponse,
    status_code=ERR_201,
    summary="Capture the condition of a returned unit",
    description=(
        "``good`` | ``damaged`` | ``hold`` | ``quarantine``. A non-good condition "
        "requires a reason code and segregates the stock (R-04)."
    ),
)
async def classify_item(
    session_id: UUID,
    data: ClassifyItemRequest,
    current_user: CurrentUser = Depends(require_permission(RETURN_CLASSIFY)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    result = service.classify_item(
        session_id,
        current_user.organization_id,
        current_user.id,
        item_id=data.item_id,
        condition=data.condition,
        reason_code=data.reason_code,
        note=data.note,
        destination=data.destination,
        override=data.override,
    )
    db.commit()
    return result


@router.post(
    "/sessions/{session_id}/classify/bulk",
    response_model=list[ClassifyResponse],
    status_code=ERR_201,
    summary="Bulk-classify a carton",
    description='Supports the "All good" action for a whole carton (R-04).',
)
async def classify_bulk(
    session_id: UUID,
    data: ClassifyBulkRequest,
    current_user: CurrentUser = Depends(require_permission(RETURN_CLASSIFY)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    results = service.classify_bulk(
        session_id, current_user.organization_id, current_user.id, data.items
    )
    db.commit()
    return results


@router.post(
    "/sessions/{session_id}/end",
    response_model=EndReturnSessionResponse,
    summary="End a return session",
    description="Produces the draft Return Receipt Note; fails if any unit is unclassified (R-03).",
)
async def end_session(
    session_id: UUID,
    data: EndReturnSessionRequest | None = None,
    current_user: CurrentUser = Depends(require_permission(RETURN_RECEIVE)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    session, note = service.end_session(
        session_id,
        current_user.organization_id,
        current_user.id,
        data.note if data else None,
    )
    db.commit()
    return {
        "receipt_note": {"id": note.id, "note_no": note.note_no, "status": note.status},
        "registration_status": "received",
        "expected_qty": float(note.expected_qty or 0),
        "received_qty": float(note.received_qty or 0),
        "short_qty": float(note.short_qty or 0),
        "conditions": {
            "good": float(note.good_qty or 0),
            "damaged": float(note.damaged_qty or 0),
            "hold": float(note.hold_qty or 0),
            "quarantine": float(note.quarantine_qty or 0),
        },
        "next": "Supervisor review in the web app",
    }


# =====================================================================
# R-05 → R-08 — receipt notes (web app)
# =====================================================================


@router.get(
    "/receipt-notes",
    response_model=ReceiptNoteListResponse,
    summary="Return receipt note queue",
    description="Supervisor queue with mismatch / damaged / open-exception badges (R-05).",
)
async def list_receipt_notes(
    status_filter: str | None = Query(None, alias="status"),
    warehouse_id: UUID | None = Query(None),
    registration_id: UUID | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    current_user: CurrentUser = Depends(require_permission(RETURN_READ)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    rows, total = service.list_notes(
        current_user.organization_id,
        status=status_filter,
        warehouse_id=warehouse_id,
        registration_id=registration_id,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [service.serialize_note_list_item(n) for n in rows],
        "page": page,
        "page_size": page_size,
        "total_items": total,
        "total_pages": ceil(total / page_size) if page_size else 0,
    }


@router.get(
    "/receipt-notes/{note_id}",
    response_model=ReceiptNoteDetail,
    summary="Get a return receipt note",
    description="Grouped expected-vs-received view, same shape as a receiving slip (R-05).",
)
async def get_receipt_note(
    note_id: UUID,
    current_user: CurrentUser = Depends(require_permission(RETURN_READ)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    return service.serialize_note_detail(
        service.get_note(note_id, current_user.organization_id)
    )


@router.post(
    "/receipt-notes/{note_id}/approve",
    response_model=NoteActionResponse,
    summary="Approve a return receipt note",
    description=(
        "Requires warehouse-manager authority. Omitting ``dispositions`` accepts the "
        "handheld's proposed routing (R-06)."
    ),
)
async def approve_receipt_note(
    note_id: UUID,
    data: ApproveNoteRequest | None = None,
    current_user: CurrentUser = Depends(require_permission(RETURN_APPROVE)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    note = service.approve_note(
        note_id,
        current_user.organization_id,
        current_user,
        note_text=data.note if data else None,
        dispositions=data.dispositions if data else None,
    )
    db.commit()
    return {
        "id": note.id,
        "note_no": note.note_no,
        "status": note.status,
        "message": "Return receipt note approved",
    }


@router.post(
    "/receipt-notes/{note_id}/reject",
    response_model=NoteActionResponse,
    summary="Reject a return receipt note",
    description="Requires warehouse-manager authority (R-06).",
)
async def reject_receipt_note(
    note_id: UUID,
    data: RejectNoteRequest,
    current_user: CurrentUser = Depends(require_permission(RETURN_APPROVE)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    note = service.reject_note(
        note_id, current_user.organization_id, current_user, data.reason
    )
    db.commit()
    return {
        "id": note.id,
        "note_no": note.note_no,
        "status": note.status,
        "message": "Return receipt note rejected",
    }


@router.post(
    "/receipt-notes/{note_id}/disposition",
    response_model=NoteActionResponse,
    summary="Set the disposition of a single line",
    description=(
        "``release_to_stock`` | ``move_to_hold`` | ``move_to_quarantine`` | ``scrap`` "
        "| ``return_to_dealer``. Safe to call per line (R-06)."
    ),
)
async def dispose_line(
    note_id: UUID,
    data: DispositionRequest,
    current_user: CurrentUser = Depends(
        require_permission(RETURN_DISPOSE, RETURN_APPROVE)
    ),
    db: Session = Depends(get_db),
):
    service = _service(db)
    line = service.dispose_line(
        note_id,
        current_user.organization_id,
        current_user,
        line_id=data.line_id,
        action=data.action,
        reason_code=data.reason_code,
        note=data.note,
    )
    db.commit()
    note = service.get_note(note_id, current_user.organization_id)
    return {
        "id": note.id,
        "note_no": note.note_no,
        "status": note.status,
        "message": f"Line disposed as '{line.disposition}'",
    }


@router.post(
    "/receipt-notes/{note_id}/generate-put-away",
    response_model=GeneratePutAwayResponse,
    summary="Generate put-away for released lines",
    description=(
        "Creates put-away tasks for ``release_to_stock`` lines and keeps the rest in "
        "their non-pickable bins. Repeat calls return 409 (R-07)."
    ),
)
async def generate_put_away(
    note_id: UUID,
    data: GeneratePutAwayRequest | None = None,
    current_user: CurrentUser = Depends(require_permission(RETURN_APPROVE)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    result = service.generate_put_away(
        note_id,
        current_user.organization_id,
        current_user,
        data.worker_ids if data else None,
    )
    db.commit()
    return result


@router.get(
    "/receipt-notes/{note_id}/slip",
    response_model=ReturnSlipResponse,
    summary="Return Slip document",
    description="Expected vs received, serials, conditions, reason codes, approver (R-08).",
)
async def get_return_slip(
    note_id: UUID,
    current_user: CurrentUser = Depends(require_permission(RETURN_READ)),
    db: Session = Depends(get_db),
):
    service = _service(db)
    return service.build_slip(note_id, current_user.organization_id)
