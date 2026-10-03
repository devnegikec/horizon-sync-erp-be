"""Pydantic schemas for the returns module.

Shapes follow ``RETURNS_WEB_APP_INTEGRATION.md`` and
``RETURNS_HANDHELD_INTEGRATION.md`` (R-01 → R-08).
"""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field

# ===========================================
# R-02 — REFERENCE LOOKUP
# ===========================================


class ReferenceParty(BaseModel):
    id: UUID | None = None
    type: str | None = None
    name: str | None = None


class ReferenceWarehouse(BaseModel):
    id: UUID
    name: str


class ReferenceDocument(BaseModel):
    """The dispatch/return reference the registration is built against."""

    id: UUID
    invoice_no: str = Field(..., description="Document number (series-prefixed)")
    invoice_type: str = Field(
        ...,
        description="'sales' | 'delivery_note' | 'outbound_order' | ... — discriminator",
    )
    posting_date: datetime | None = None
    status: str | None = None
    grand_total: float | None = None
    currency: str | None = None
    party: ReferenceParty | None = None
    warehouse: ReferenceWarehouse | None = None


class ReferenceLine(BaseModel):
    line_id: UUID | None = None
    item_id: UUID | None = None
    sku: str
    item_name: str | None = None
    uom: str
    invoiced_qty: float
    already_returned_qty: float = 0
    returnable_qty: float


class ReferenceLookupResponse(BaseModel):
    """``GET /returns/references`` — resolves invoice → party → warehouse → lines."""

    invoice: ReferenceDocument
    lines: list[ReferenceLine] = []
    suggested_warehouse_id: UUID | None = None


# ===========================================
# R-01 — REGISTRATIONS
# ===========================================


class RegistrationLineInput(BaseModel):
    sku: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0)
    uom: str = Field("NOS", max_length=50)
    serials: list[str] | None = None


class CreateRegistrationRequest(BaseModel):
    reference_type: str = Field(
        "invoice", description="invoice | dealer | warehouse | delivery_note"
    )
    invoice_no: str | None = Field(None, max_length=100)
    reference_id: UUID | None = None
    party_id: UUID | None = None
    warehouse_id: UUID
    return_reason_code: str | None = Field(None, max_length=80)
    return_date: date | None = None
    note: str | None = None
    lines: list[RegistrationLineInput] = Field(..., min_length=1)


class PartyRef(BaseModel):
    id: UUID | None = None
    name: str | None = None


class RegistrationLineResponse(BaseModel):
    id: UUID
    sku: str
    item_name: str | None = None
    uom: str
    expected_qty: float
    received_qty: float
    serials: list[str] | None = None
    conditions: dict[str, float] = {}


class RegistrationSessionRef(BaseModel):
    id: UUID
    status: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    worker_id: UUID | None = None


class RegistrationListItem(BaseModel):
    id: UUID
    registration_no: str
    status: str
    reference_type: str | None = None
    invoice_no: str | None = None
    return_reason_code: str | None = None
    party_name: str | None = None
    warehouse_name: str | None = None
    warehouse_id: UUID | None = None
    expected_qty: float
    received_qty: float
    created_at: datetime | None = None


class Pagination(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool = False
    has_prev: bool = False


class RegistrationListResponse(BaseModel):
    items: list[RegistrationListItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool = False
    has_prev: bool = False


class RegistrationDetail(BaseModel):
    id: UUID
    registration_no: str
    status: str
    reference_type: str | None = None
    invoice_no: str | None = None
    party: PartyRef | None = None
    warehouse: ReferenceWarehouse | None = None
    return_reason_code: str | None = None
    note: str | None = None
    expected_qty: float
    received_qty: float
    created_at: datetime | None = None
    lines: list[RegistrationLineResponse] = []
    sessions: list[RegistrationSessionRef] = []


class CancelRegistrationRequest(BaseModel):
    reason: str | None = Field(None, max_length=500)


# ===========================================
# R-03 / R-04 — HANDHELD SESSIONS
# ===========================================


class StartReturnSessionRequest(BaseModel):
    dock_location: str | None = Field(None, max_length=120)
    device_id: str | None = Field(None, max_length=120)


class ReturnSessionResponse(BaseModel):
    id: UUID
    registration_id: UUID
    registration_no: str
    warehouse: ReferenceWarehouse | None = None
    status: str
    dock_location: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    expected_qty: float
    scanned_qty: float
    classified_qty: float


class SessionLineState(BaseModel):
    line_id: UUID
    sku: str
    item_name: str | None = None
    uom: str
    expected_qty: float
    scanned_qty: float
    classified_qty: float
    serials: list[str] | None = None


class SessionItemState(BaseModel):
    id: UUID
    qr_identifier: str
    sku: str | None = None
    serial_number: str | None = None
    quantity: float
    condition: str | None = None
    reason_code: str | None = None
    destination: str | None = None
    exception_id: UUID | None = None
    over_receipt: bool = False


class ReturnSessionDetail(ReturnSessionResponse):
    lines: list[SessionLineState] = []
    items: list[SessionItemState] = []


class ReturnScanRequest(BaseModel):
    qr_data: str = Field(..., min_length=1)
    device_type: str | None = Field(None, max_length=50)
    os: str | None = Field(None, max_length=80)


class ReturnScanResponse(BaseModel):
    item_id: UUID
    qr_identifier: str
    sku: str | None = None
    matched_line_id: UUID | None = None
    quantity: float
    serial_expected: bool = False
    over_receipt: bool = False
    condition: str | None = None
    scanned_qty: float
    expected_qty: float
    next_action: str


class ClassifyItemRequest(BaseModel):
    item_id: UUID
    condition: str
    reason_code: str | None = Field(None, max_length=80)
    note: str | None = None
    destination: str | None = Field(
        None, description="Optional override: HOLD | QUARANTINE | DAMAGED"
    )
    override: bool = Field(
        False, description="Re-classify an already classified unit (change reason)"
    )


class ClassifyBulkItem(BaseModel):
    item_id: UUID
    condition: str
    reason_code: str | None = None
    note: str | None = None
    destination: str | None = None


class ClassifyBulkRequest(BaseModel):
    items: list[ClassifyBulkItem] = Field(..., min_length=1)


class ClassifyResponse(BaseModel):
    item_id: UUID
    condition: str
    reason_code: str | None = None
    destination: str | None = None
    exception_id: UUID | None = None
    exception_status: str | None = None


class EndReturnSessionRequest(BaseModel):
    note: str | None = None


class ReturnUnreadableReportRequest(BaseModel):
    """Operator report of a carton whose label cannot be scanned, on a return.

    Same contract as the inbound report: nothing is decoded and no stock is
    created — the carton reference is parked as a ``QR_UNREADABLE`` HOLD
    exception and the warehouse supervisors are alerted. The operator never
    supplies an identity; ``carton_reference`` is read off the carton.
    """

    carton_reference: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description=(
            "Printed reference of the unreadable carton (serial, batch or ASN line) "
            "so a supervisor can locate it"
        ),
    )
    sku: str | None = Field(None, max_length=100)
    batch_number: str | None = Field(None, max_length=100)
    quantity: int = Field(1, ge=1)
    note: str | None = Field(None, max_length=2000)


class ReceiptNoteRef(BaseModel):
    id: UUID
    note_no: str
    status: str


class EndReturnSessionResponse(BaseModel):
    receipt_note: ReceiptNoteRef
    registration_status: str
    expected_qty: float
    received_qty: float
    short_qty: float
    conditions: dict[str, float]
    next: str


# ===========================================
# R-05 → R-08 — RETURN RECEIPT NOTES
# ===========================================


class ReceiptNoteListItem(BaseModel):
    id: UUID
    note_no: str
    status: str
    registration_no: str | None = None
    registration_id: UUID | None = None
    warehouse_name: str | None = None
    warehouse_id: UUID | None = None
    expected_qty: float
    received_qty: float
    mismatch: bool = False
    damaged_qty: float = 0
    open_exceptions: int = 0
    created_at: datetime | None = None


class ReceiptNoteListResponse(BaseModel):
    items: list[ReceiptNoteListItem]
    page: int
    page_size: int
    total_items: int
    total_pages: int


class NoteLineItem(BaseModel):
    id: UUID
    serial_number: str | None = None
    batch_number: str | None = None
    quantity: float
    uom: str
    condition: str | None = None
    reason_code: str | None = None
    note: str | None = None
    exception_id: UUID | None = None
    destination: str | None = None
    disposition: str | None = None
    disposed_at: datetime | None = None


class NoteGroup(BaseModel):
    product_name: str | None = None
    sku: str | None = None
    item_id: UUID | None = None
    expected_qty: float = 0
    received_qty: float = 0
    short_qty: float = 0
    items: list[NoteLineItem] = []


class ReceiptNoteDetail(BaseModel):
    id: UUID
    note_no: str
    status: str
    registration_id: UUID
    registration_no: str | None = None
    warehouse: ReferenceWarehouse | None = None
    expected_qty: float
    received_qty: float
    short_qty: float
    conditions: dict[str, float] = {}
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    rejection_reason: str | None = None
    put_away_generated_at: datetime | None = None
    created_at: datetime | None = None
    groups: list[NoteGroup] = []
    #: Flattened lines, so a client can address a single line without walking groups.
    lines: list[NoteLineItem] = []


class DispositionInput(BaseModel):
    line_id: UUID
    action: str
    reason_code: str | None = Field(None, max_length=80)
    note: str | None = None


class ApproveNoteRequest(BaseModel):
    note: str | None = None
    dispositions: list[DispositionInput] | None = None


class RejectNoteRequest(BaseModel):
    reason: str = Field(..., min_length=1, max_length=1000)


class DispositionRequest(BaseModel):
    line_id: UUID
    action: str
    reason_code: str | None = Field(None, max_length=80)
    note: str | None = None


class NoteActionResponse(BaseModel):
    id: UUID
    note_no: str
    status: str
    message: str


class GeneratePutAwayRequest(BaseModel):
    worker_ids: list[UUID] | None = None
    note: str | None = None


class PutAwayListRef(BaseModel):
    id: UUID
    list_no: str
    assigned_to: UUID | None = None
    item_count: int = 0


class GeneratePutAwayResponse(BaseModel):
    put_away_lists: list[PutAwayListRef] = []
    segregated_lines: int = 0
    note_status: str


class SlipLine(BaseModel):
    sku: str | None = None
    item_name: str | None = None
    expected_qty: float = 0
    received_qty: float = 0
    conditions: dict[str, float] = {}
    reason_codes: list[str] = []
    serials: list[str] = []


class SlipTotals(BaseModel):
    expected_qty: float = 0
    received_qty: float = 0
    short_qty: float = 0


class ReturnSlipResponse(BaseModel):
    slip_no: str
    generated_at: datetime
    registration_no: str | None = None
    invoice_no: str | None = None
    party: PartyRef | None = None
    warehouse: ReferenceWarehouse | None = None
    approved_by: UUID | None = None
    approved_at: datetime | None = None
    lines: list[SlipLine] = []
    totals: SlipTotals = SlipTotals()
