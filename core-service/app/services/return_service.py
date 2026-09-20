"""Returns (customer returns) service — R-01 → R-08.

Implements the flow in ``RETURNS_WEB_APP_INTEGRATION.md`` /
``RETURNS_HANDHELD_INTEGRATION.md``:

    Registration → dock session → scan → classify → draft note → approval
    → put-away / segregation → Return Slip

The web app never scans and the handheld never approves; this service owns both
halves and enforces the split through the permission codes passed by the API
layer.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.customer import Customer
from app.models.delivery_note import DeliveryNote
from app.models.inbound_exception import InboundException, InboundExceptionReason
from app.models.item import Item
from app.models.put_away_list import PutAwayList, PutAwayListItem
from app.models.returns import (
    CANCELLABLE_REGISTRATION_STATUSES,
    CONDITION_DESTINATIONS,
    CONDITIONS,
    DISPOSITION_ALLOWED_CONDITIONS,
    DISPOSITIONS,
    RECEIVABLE_REGISTRATION_STATUSES,
    ReturnReceiptNote,
    ReturnReceiptNoteEvent,
    ReturnReceiptNoteItem,
    ReturnRegistration,
    ReturnRegistrationItem,
    ReturnSession,
    ReturnSessionItem,
)
from app.models.warehouse import Warehouse
from app.services.bin_stock_service import BinStockService
from app.services.document_numbering_service import DocumentNumberingService
from app.services.inbound_exception_service import (
    DUPLICATE_SERIAL_REASON,
    InboundExceptionService,
)
from app.services.scanned_item_tracking_service import ScannedItemTrackingService

logger = logging.getLogger(__name__)


class ReturnService:
    """Owns the return registration, dock session and approval lifecycle."""

    #: Condition → exception reason code used when the caller supplies none.
    DEFAULT_CONDITION_REASONS = {
        "good": "RETURN_GOOD",
        "damaged": "RETURN_DAMAGED",
        "hold": "HOLD",
        "quarantine": "QUARANTINE",
    }

    #: Disposition → destination bin (only for the segregating dispositions).
    DISPOSITION_DESTINATIONS = {
        "move_to_hold": "HOLD",
        "move_to_quarantine": "QUARANTINE",
    }

    #: Dispositions that take stock out of the warehouse entirely.
    STOCK_REMOVING_DISPOSITIONS = {"scrap", "return_to_dealer"}

    def __init__(self, db: Session):
        self.db = db

    # ==================================================================
    # R-02 — reference lookup
    # ==================================================================

    def lookup_reference(
        self,
        organization_id: UUID,
        *,
        invoice_no: str | None = None,
        party_id: UUID | None = None,
        warehouse_id: UUID | None = None,
    ) -> dict:
        """Resolve the invoice/dealer/warehouse triple for the registration form.

        The line source is the **delivery note** — the document that actually
        recorded what left the warehouse — because this tenant's ``invoices``
        table holds SaaS subscription billing, not customer sales invoices.
        ``invoice_no`` therefore also accepts a delivery-note number, and the
        response carries ``invoice_type='delivery_note'`` so the UI can tell the
        two apart instead of guessing.
        """
        query = self.db.query(DeliveryNote).filter(
            DeliveryNote.organization_id == organization_id
        )
        if invoice_no:
            query = query.filter(DeliveryNote.delivery_note_no == invoice_no)
        if party_id:
            query = query.filter(DeliveryNote.customer_id == party_id)
        if warehouse_id:
            query = query.filter(DeliveryNote.warehouse_id == warehouse_id)

        note = (
            query.filter(DeliveryNote.status != "cancelled")
            .order_by(DeliveryNote.delivery_date.desc())
            .first()
        )
        if note is None:
            raise NotFoundError(
                message=(
                    "No dispatched document matches that reference"
                    if invoice_no
                    else "No dispatched document found for that dealer"
                ),
                entity_type="DeliveryNote",
                entity_id=str(invoice_no or party_id or ""),
                code="RETURNS_REFERENCE_NOT_FOUND",
                hint=(
                    "Check the document number, or register the return against "
                    "the dealer without a reference."
                ),
            )

        customer = (
            self.db.query(Customer).filter(Customer.id == note.customer_id).first()
            if note.customer_id
            else None
        )
        warehouse = (
            self.db.query(Warehouse).filter(Warehouse.id == note.warehouse_id).first()
            if note.warehouse_id
            else None
        )

        lines = self._build_reference_lines(organization_id, note)

        return {
            "invoice": {
                "id": note.id,
                "invoice_no": note.delivery_note_no,
                "invoice_type": "delivery_note",
                "posting_date": note.delivery_date or note.created_at,
                "status": note.status.value
                if hasattr(note.status, "value")
                else note.status,
                "grand_total": None,
                "currency": None,
                "party": {
                    "id": note.customer_id,
                    "type": "customer",
                    "name": customer.customer_name if customer else None,
                },
                "warehouse": {"id": note.warehouse_id, "name": warehouse.name}
                if warehouse and note.warehouse_id
                else None,
            },
            "lines": lines,
            "suggested_warehouse_id": note.warehouse_id,
        }

    def _build_reference_lines(
        self, organization_id: UUID, note: DeliveryNote
    ) -> list[dict]:
        """Return each dispatched line with its remaining returnable quantity."""
        returned = self._already_returned_map(organization_id, note.id)
        lines: list[dict] = []
        for line in note.items or []:
            item = (
                self.db.query(Item).filter(Item.id == line.item_id).first()
                if line.item_id
                else None
            )
            sku = (item.sku or item.item_code) if item else None
            if not sku:
                continue
            invoiced = self._to_decimal(line.qty)
            already = returned.get(line.item_id, Decimal("0"))
            lines.append(
                {
                    "line_id": line.id,
                    "item_id": line.item_id,
                    "sku": sku,
                    "item_name": item.item_name if item else None,
                    "uom": line.uom or "NOS",
                    "invoiced_qty": float(invoiced),
                    "already_returned_qty": float(already),
                    "returnable_qty": float(max(invoiced - already, Decimal("0"))),
                }
            )
        return lines

    def _already_returned_map(
        self, organization_id: UUID, reference_id: UUID
    ) -> dict[UUID | None, Decimal]:
        """Quantity already declared for return per item on a reference."""
        rows = (
            self.db.query(
                ReturnRegistrationItem.item_id,
                ReturnRegistrationItem.expected_qty,
            )
            .join(
                ReturnRegistration,
                ReturnRegistration.id == ReturnRegistrationItem.registration_id,
            )
            .filter(
                ReturnRegistration.organization_id == organization_id,
                ReturnRegistration.reference_id == reference_id,
                ReturnRegistration.status != "cancelled",
            )
            .all()
        )
        totals: dict[UUID | None, Decimal] = {}
        for item_id, qty in rows:
            totals[item_id] = totals.get(item_id, Decimal("0")) + self._to_decimal(qty)
        return totals

    # ==================================================================
    # R-01 — registrations
    # ==================================================================

    def create_registration(
        self,
        organization_id: UUID,
        actor_id: UUID | None,
        payload,
    ) -> ReturnRegistration:
        warehouse = (
            self.db.query(Warehouse)
            .filter(
                Warehouse.id == payload.warehouse_id,
                Warehouse.organization_id == organization_id,
            )
            .first()
        )
        if warehouse is None:
            raise NotFoundError(
                "Warehouse not found",
                entity_type="Warehouse",
                entity_id=str(payload.warehouse_id),
            )

        reference = None
        if payload.invoice_no:
            reference = self._resolve_reference_for_write(
                organization_id, payload.invoice_no, payload.warehouse_id
            )

        party_name = None
        party_id = payload.party_id
        if reference is not None:
            party_id = party_id or reference.customer_id
            if reference.customer_id:
                customer = (
                    self.db.query(Customer)
                    .filter(Customer.id == reference.customer_id)
                    .first()
                )
                party_name = customer.customer_name if customer else None

        registration = ReturnRegistration(
            organization_id=organization_id,
            registration_no=DocumentNumberingService(self.db).get_next_number(
                organization_id, "return_registration"
            ),
            # Lines are validated below, so the registration is immediately
            # receivable — the contract's ``ready`` state (see module notes).
            status="ready",
            reference_type=payload.reference_type or "invoice",
            reference_id=reference.id
            if reference is not None
            else payload.reference_id,
            reference_no=(
                reference.delivery_note_no
                if reference is not None
                else payload.invoice_no
            ),
            party_id=party_id,
            party_name=party_name,
            warehouse_id=payload.warehouse_id,
            return_reason_code=payload.return_reason_code,
            return_date=(
                datetime.combine(payload.return_date, datetime.min.time(), tzinfo=UTC)
                if payload.return_date
                else datetime.now(UTC)
            ),
            note=payload.note,
            created_by=actor_id,
        )
        self.db.add(registration)
        self.db.flush()

        total = Decimal("0")
        for idx, line in enumerate(payload.lines):
            item, sku = self._resolve_item(organization_id, line.sku)
            if item is None:
                raise ValidationError(
                    f"SKU '{line.sku}' is not an active item in this organization",
                    details=[{"field": "lines", "reason": f"Unknown SKU '{line.sku}'"}],
                    code="RETURN_REFERENCE_INVALID",
                )
            qty = self._to_decimal(line.quantity)
            if qty <= 0:
                raise ValidationError(
                    "Return quantity must be greater than zero",
                    details=[
                        {
                            "field": "lines",
                            "reason": f"'{line.sku}' quantity must be ≥ 1",
                        }
                    ],
                )
            total += qty
            self.db.add(
                ReturnRegistrationItem(
                    organization_id=organization_id,
                    registration_id=registration.id,
                    item_id=item.id,
                    sku=sku,
                    item_name=item.item_name,
                    uom=(line.uom or item.uom or "NOS"),
                    expected_qty=qty,
                    received_qty=Decimal("0"),
                    serials=line.serials,
                    sort_order=idx,
                )
            )

        registration.expected_qty = total
        self.db.flush()
        return registration

    def _resolve_reference_for_write(
        self, organization_id: UUID, invoice_no: str, warehouse_id: UUID
    ) -> DeliveryNote | None:
        """Best-effort reference resolution; an unknown number is not fatal."""
        return (
            self.db.query(DeliveryNote)
            .filter(
                DeliveryNote.organization_id == organization_id,
                DeliveryNote.delivery_note_no == invoice_no,
            )
            .first()
        )

    def list_registrations(
        self,
        organization_id: UUID,
        *,
        status: str | None = None,
        warehouse_id: UUID | None = None,
        party_id: UUID | None = None,
        invoice_no: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ReturnRegistration], int]:
        query = self.db.query(ReturnRegistration).filter(
            ReturnRegistration.organization_id == organization_id
        )
        if status:
            query = query.filter(ReturnRegistration.status == status)
        if warehouse_id:
            query = query.filter(ReturnRegistration.warehouse_id == warehouse_id)
        if party_id:
            query = query.filter(ReturnRegistration.party_id == party_id)
        if invoice_no:
            query = query.filter(ReturnRegistration.reference_no == invoice_no)
        total = query.count()
        rows = (
            query.order_by(ReturnRegistration.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def get_registration(
        self, registration_id: UUID, organization_id: UUID
    ) -> ReturnRegistration:
        registration = (
            self.db.query(ReturnRegistration)
            .filter(
                ReturnRegistration.id == registration_id,
                ReturnRegistration.organization_id == organization_id,
            )
            .first()
        )
        if registration is None:
            raise NotFoundError(
                "Return registration not found",
                entity_type="ReturnRegistration",
                entity_id=str(registration_id),
                code="RETURN_REGISTRATION_NOT_FOUND",
                hint="Go back to the registration list and pick the return again.",
            )
        return registration

    def cancel_registration(
        self,
        registration_id: UUID,
        organization_id: UUID,
        actor_id: UUID | None,
        reason: str | None,
    ) -> ReturnRegistration:
        registration = self.get_registration(registration_id, organization_id)
        if registration.status == "cancelled":
            raise StateError(
                "This return registration is already cancelled",
                current_state=registration.status,
                required_state=["draft", "ready"],
                code="RETURN_REGISTRATION_ALREADY_CANCELLED",
            )
        if registration.status not in CANCELLABLE_REGISTRATION_STATUSES:
            raise StateError(
                "A return can only be cancelled before the first unit is scanned",
                current_state=registration.status,
                required_state=list(CANCELLABLE_REGISTRATION_STATUSES),
                code="RETURN_REGISTRATION_NOT_CANCELLABLE",
                hint="Units have already been received — close or reject the note instead.",
            )
        registration.status = "cancelled"
        registration.cancelled_reason = reason
        registration.cancelled_by = actor_id
        registration.cancelled_at = datetime.now(UTC)
        self.db.flush()
        return registration

    # ==================================================================
    # R-03 — dock sessions
    # ==================================================================

    def start_session(
        self,
        registration_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        dock_location: str | None,
        device_id: str | None,
    ) -> ReturnSession:
        registration = self.get_registration(registration_id, organization_id)

        open_session = self._open_session_for(registration.id)
        if open_session is not None:
            raise StateError(
                "A receiving session is already open for this return",
                current_state="receiving",
                required_state=["ready"],
                code="RETURN_SESSION_ALREADY_OPEN",
                hint=f"Resume session {open_session.id} instead of opening a new one.",
            )

        if registration.status == "cancelled":
            raise StateError(
                "This return registration was cancelled",
                current_state=registration.status,
                required_state=list(RECEIVABLE_REGISTRATION_STATUSES),
                code="RETURN_REGISTRATION_CANCELLED",
            )
        if registration.status not in RECEIVABLE_REGISTRATION_STATUSES:
            raise StateError(
                "This return is not receivable in its current state",
                current_state=registration.status,
                required_state=list(RECEIVABLE_REGISTRATION_STATUSES),
                code="RETURN_REGISTRATION_NOT_RECEIVABLE",
            )

        session = ReturnSession(
            organization_id=organization_id,
            registration_id=registration.id,
            warehouse_id=registration.warehouse_id,
            status="open",
            dock_location=dock_location,
            device_id=device_id,
            expected_qty=registration.expected_qty or Decimal("0"),
            scanned_qty=Decimal("0"),
            classified_qty=Decimal("0"),
            started_by=actor_id,
            started_at=datetime.now(UTC),
        )
        self.db.add(session)
        registration.status = "receiving"
        self.db.flush()
        return session

    def get_session(self, session_id: UUID, organization_id: UUID) -> ReturnSession:
        session = (
            self.db.query(ReturnSession)
            .filter(
                ReturnSession.id == session_id,
                ReturnSession.organization_id == organization_id,
            )
            .first()
        )
        if session is None:
            raise NotFoundError(
                "Return receiving session not found",
                entity_type="ReturnSession",
                entity_id=str(session_id),
                code="RETURN_SESSION_NOT_FOUND",
                hint="Recover the session from the registration, or start a new one.",
            )
        return session

    def record_scan(
        self,
        session_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        qr_data: str,
        device_type: str | None,
        os: str | None,
    ) -> ReturnSessionItem:
        session = self.get_session(session_id, organization_id)
        if session.status != "open":
            raise StateError(
                "This receiving session is no longer open",
                current_state=session.status,
                required_state=["open"],
                code="RETURN_SESSION_NOT_OPEN",
                hint="Return to the session picker and resume an open session.",
            )

        payload = self._decode_qr(qr_data)
        qr_identifier = str(
            payload.get("id") or payload.get("qr_identifier") or ""
        ).strip()
        if not qr_identifier:
            raise ValidationError(
                "The scanned label carries no unit identity",
                code="RETURN_QR_INVALID",
                hint="Report it as unreadable and hand the carton to the supervisor.",
            )

        registration = self.get_registration(session.registration_id, organization_id)

        # Already captured in this session → amber "already captured".
        existing = (
            self.db.query(ReturnSessionItem)
            .filter(
                ReturnSessionItem.session_id == session.id,
                ReturnSessionItem.qr_identifier == qr_identifier,
            )
            .first()
        )
        if existing is not None:
            raise StateError(
                f"Unit {qr_identifier} is already captured in this session",
                current_state="scanned",
                required_state=["pending"],
                code="RETURN_UNIT_ALREADY_SCANNED",
                hint="Open the already-captured unit instead of scanning it again.",
            )

        line = self._match_line(registration, payload)
        if line is None:
            sku = payload.get("sku")
            if sku and not self._sku_on_registration(registration, sku):
                raise NotFoundError(
                    f"SKU '{sku}' is not part of this return",
                    entity_type="ReturnRegistrationItem",
                    entity_id=str(registration.id),
                    code="RETURN_UNIT_NOT_REGISTERED",
                    hint=(
                        "Do not override this — report it as unreadable or hand the "
                        "carton to the supervisor."
                    ),
                )
            raise NotFoundError(
                "This unit is not part of the return registration",
                entity_type="ReturnRegistrationItem",
                entity_id=str(registration.id),
                code="RETURN_UNIT_NOT_REGISTERED",
                hint="Report it as unreadable or call the supervisor.",
            )

        expected_serials = [str(s) for s in (line.serials or [])]
        if expected_serials and qr_identifier not in expected_serials:
            raise StateError(
                f"Serial {qr_identifier} is not registered on this return line",
                current_state="unexpected_serial",
                required_state=list(expected_serials),
                code="RETURN_SERIAL_NOT_REGISTERED",
                hint="Do not override — report the unit to the supervisor.",
            )

        # Identity already sitting in active stock → hard stop (contract §4.1).
        active = ScannedItemTrackingService(self.db).find_active_stock(
            qr_identifier, organization_id
        )
        if active is not None:
            self._record_identity_exception(
                registration, session, actor_id, qr_identifier, payload, active
            )
            self.db.commit()
            raise StateError(
                f"Unit {qr_identifier} is already in active stock",
                current_state="in_stock",
                required_state=["dispatched"],
                code="DUPLICATE_SERIAL",
                hint=(
                    "This unit was never dispatched. Notify the supervisor — do not "
                    "accept it into stock."
                ),
            )

        quantity = self._to_decimal(payload.get("qty") or 1) or Decimal("1")
        new_total = self._to_decimal(line.received_qty) + quantity
        over_receipt = new_total > self._to_decimal(line.expected_qty)

        item = ReturnSessionItem(
            organization_id=organization_id,
            session_id=session.id,
            registration_id=registration.id,
            registration_item_id=line.id,
            item_id=line.item_id,
            sku=line.sku,
            qr_identifier=qr_identifier,
            serial_number=qr_identifier,
            batch_number=payload.get("batch"),
            quantity=quantity,
            over_receipt=over_receipt,
            device_type=device_type,
            os=os,
            scanned_by=actor_id,
            scanned_at=datetime.now(UTC),
        )
        self.db.add(item)

        line.received_qty = new_total
        registration.received_qty = (
            self._to_decimal(registration.received_qty) + quantity
        )
        session.scanned_qty = self._to_decimal(session.scanned_qty) + quantity
        self.db.flush()
        return item

    def end_session(
        self,
        session_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        note: str | None,
    ) -> tuple[ReturnSession, ReturnReceiptNote]:
        session = self.get_session(session_id, organization_id)
        if session.status != "open":
            raise StateError(
                "This receiving session is not open",
                current_state=session.status,
                required_state=["open"],
                code="RETURN_SESSION_NOT_OPEN",
            )

        items = (
            self.db.query(ReturnSessionItem)
            .filter(ReturnSessionItem.session_id == session.id)
            .all()
        )
        unclassified = [i for i in items if not i.condition]
        if unclassified:
            raise StateError(
                f"{len(unclassified)} unit(s) still need a condition",
                current_state="unclassified",
                required_state=["classified"],
                code="RETURN_SESSION_HAS_UNCLASSIFIED_ITEMS",
                hint="Jump to the first unclassified unit and capture its condition.",
            )

        registration = self.get_registration(session.registration_id, organization_id)
        note_row = self._create_note(
            registration, session, items, organization_id, actor_id
        )
        if note:
            note_row.note = note

        session.status = "ended"
        session.ended_by = actor_id
        session.ended_at = datetime.now(UTC)
        registration.status = "received"
        self.db.flush()
        return session, note_row

    # ==================================================================
    # R-04 — condition capture
    # ==================================================================

    def classify_item(
        self,
        session_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        *,
        item_id: UUID,
        condition: str,
        reason_code: str | None,
        note: str | None,
        destination: str | None,
        override: bool,
    ) -> dict:
        session = self.get_session(session_id, organization_id)
        if session.status != "open":
            raise StateError(
                "This receiving session is not open",
                current_state=session.status,
                required_state=["open"],
                code="RETURN_SESSION_NOT_OPEN",
            )

        item = (
            self.db.query(ReturnSessionItem)
            .filter(
                ReturnSessionItem.id == item_id,
                ReturnSessionItem.session_id == session.id,
            )
            .first()
        )
        if item is None:
            raise NotFoundError(
                "Scanned unit not found in this session",
                entity_type="ReturnSessionItem",
                entity_id=str(item_id),
            )

        if item.condition and not override:
            raise StateError(
                "This unit is already classified",
                current_state=item.condition,
                required_state=["pending"],
                code="RETURN_ITEM_ALREADY_CLASSIFIED",
                hint='Use "Change reason" to re-classify it.',
            )

        if condition not in CONDITIONS:
            raise ValidationError(
                f"Invalid condition '{condition}'",
                details=[
                    {
                        "field": "condition",
                        "reason": f"Must be one of: {', '.join(CONDITIONS)}",
                    }
                ],
                code="RETURN_CONDITION_INVALID",
            )

        resolved_reason, resolved_destination = self._resolve_classification(
            organization_id, condition, reason_code, destination
        )

        item.condition = condition
        item.reason_code = resolved_reason
        item.note = note
        item.destination = resolved_destination
        item.classified_by = actor_id
        item.classified_at = datetime.now(UTC)

        exception = None
        if condition != "good":
            exception = self._segregate(
                session=session,
                item=item,
                condition=condition,
                reason_code=resolved_reason,
                destination=resolved_destination,
                note=note,
                organization_id=organization_id,
                actor_id=actor_id,
            )
            item.exception_id = exception.id

        session.classified_qty = self._to_decimal(
            session.classified_qty
        ) + self._to_decimal(item.quantity)
        self.db.flush()

        return {
            "item_id": item.id,
            "condition": condition,
            "reason_code": resolved_reason,
            "destination": resolved_destination,
            "exception_id": exception.id if exception else None,
            "exception_status": exception.status if exception else None,
        }

    def classify_bulk(
        self,
        session_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        items: list,
    ) -> list[dict]:
        results = []
        for entry in items:
            results.append(
                self.classify_item(
                    session_id,
                    organization_id,
                    actor_id,
                    item_id=entry.item_id,
                    condition=entry.condition,
                    reason_code=entry.reason_code,
                    note=entry.note,
                    destination=entry.destination,
                    override=False,
                )
            )
        return results

    # ==================================================================
    # R-05 — receipt notes
    # ==================================================================

    def list_notes(
        self,
        organization_id: UUID,
        *,
        status: str | None = None,
        warehouse_id: UUID | None = None,
        registration_id: UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[ReturnReceiptNote], int]:
        query = self.db.query(ReturnReceiptNote).filter(
            ReturnReceiptNote.organization_id == organization_id
        )
        if status:
            query = query.filter(ReturnReceiptNote.status == status)
        if warehouse_id:
            query = query.filter(ReturnReceiptNote.warehouse_id == warehouse_id)
        if registration_id:
            query = query.filter(ReturnReceiptNote.registration_id == registration_id)
        total = query.count()
        rows = (
            query.order_by(ReturnReceiptNote.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return rows, total

    def get_note(self, note_id: UUID, organization_id: UUID) -> ReturnReceiptNote:
        note = (
            self.db.query(ReturnReceiptNote)
            .filter(
                ReturnReceiptNote.id == note_id,
                ReturnReceiptNote.organization_id == organization_id,
            )
            .first()
        )
        if note is None:
            raise NotFoundError(
                "Return receipt note not found",
                entity_type="ReturnReceiptNote",
                entity_id=str(note_id),
                code="RETURN_NOTE_NOT_FOUND",
            )
        return note

    # ==================================================================
    # R-06 — approval & disposition
    # ==================================================================

    def approve_note(
        self,
        note_id: UUID,
        organization_id: UUID,
        user,
        *,
        note_text: str | None,
        dispositions: list | None,
    ) -> ReturnReceiptNote:
        note = self.get_note(note_id, organization_id)
        self._assert_manager(user, note.warehouse_id)

        if note.status not in ("pending_approval", "draft"):
            raise StateError(
                "This note is not awaiting approval",
                current_state=note.status,
                required_state=["pending_approval", "draft"],
                code="RETURN_NOTE_NOT_PENDING_APPROVAL",
            )

        pending = [i for i in note.items if not i.condition]
        if pending or self._to_decimal(note.expected_qty) == 0:
            raise StateError(
                "Every line must be classified before the note can be approved",
                current_state="unclassified_lines",
                required_state=["classified"],
                code="RETURN_NOTE_HAS_UNCLASSIFIED_LINES",
                hint="Send the note back to the dock to capture condition(s).",
            )

        if dispositions:
            for entry in dispositions:
                self._apply_disposition(
                    note,
                    entry.line_id,
                    entry.action,
                    entry.reason_code,
                    entry.note,
                    user.id,
                )
        else:
            for line in note.items:
                action = self._proposed_disposition(line)
                if action:
                    self._apply_disposition(
                        note, line.id, action, line.reason_code, None, user.id
                    )

        note.status = "approved"
        note.approved_by = user.id
        note.approved_at = datetime.now(UTC)
        if note_text:
            note.note = note_text
        self._event(note, "approved", user.id, {"dispositions": bool(dispositions)})
        self.db.flush()
        return note

    def reject_note(
        self,
        note_id: UUID,
        organization_id: UUID,
        user,
        reason: str,
    ) -> ReturnReceiptNote:
        note = self.get_note(note_id, organization_id)
        self._assert_manager(user, note.warehouse_id)
        if note.status in ("approved", "rejected"):
            raise StateError(
                "This note has already been decided",
                current_state=note.status,
                required_state=["pending_approval", "draft"],
                code="RETURN_NOTE_NOT_PENDING_APPROVAL",
            )
        note.status = "rejected"
        note.rejected_by = user.id
        note.rejected_at = datetime.now(UTC)
        note.rejection_reason = reason
        self._event(note, "rejected", user.id, {"reason": reason})
        self.db.flush()
        return note

    def dispose_line(
        self,
        note_id: UUID,
        organization_id: UUID,
        user,
        *,
        line_id: UUID,
        action: str,
        reason_code: str | None,
        note: str | None,
    ) -> ReturnReceiptNoteItem:
        row = self.get_note(note_id, organization_id)
        self._assert_manager(user, row.warehouse_id)
        line = self._apply_disposition(row, line_id, action, reason_code, note, user.id)
        self.db.flush()
        return line

    def _apply_disposition(
        self,
        note: ReturnReceiptNote,
        line_id: UUID,
        action: str,
        reason_code: str | None,
        note_text: str | None,
        actor_id: UUID,
    ) -> ReturnReceiptNoteItem:
        line = next((i for i in note.items if i.id == line_id), None)
        if line is None:
            raise NotFoundError(
                "Return receipt note line not found",
                entity_type="ReturnReceiptNoteItem",
                entity_id=str(line_id),
            )
        if action not in DISPOSITIONS:
            raise ValidationError(
                f"Unknown disposition '{action}'",
                details=[
                    {
                        "field": "action",
                        "reason": f"Must be one of: {', '.join(DISPOSITIONS)}",
                    }
                ],
                code="RETURN_DISPOSITION_INVALID",
            )
        allowed = DISPOSITION_ALLOWED_CONDITIONS.get(action, ())
        if line.condition not in allowed:
            raise ValidationError(
                f"'{action}' cannot be applied to a '{line.condition}' line",
                details=[
                    {
                        "field": "action",
                        "reason": (
                            f"'{action}' applies to: {', '.join(allowed)} "
                            f"(line condition is '{line.condition}')"
                        ),
                    }
                ],
                code="RETURN_DISPOSITION_INVALID",
                hint="Pick a disposition that matches the captured condition.",
            )

        if line.disposition and line.disposition != action:
            if line.disposition in self.STOCK_REMOVING_DISPOSITIONS:
                raise StateError(
                    "This line was already disposed of and its stock taken out",
                    current_state=line.disposition,
                    required_state=list(DISPOSITIONS),
                    code="RETURN_LINE_ALREADY_DISPOSED",
                    hint=(
                        "Scrap and dealer returns cannot be re-dispositioned — the "
                        "stock has already left the warehouse."
                    ),
                )

        self._apply_disposition_stock(note, line, action)

        line.disposition = action
        line.disposition_reason_code = reason_code or line.reason_code
        line.disposition_note = note_text
        line.disposed_by = actor_id
        line.disposed_at = datetime.now(UTC)
        self._event(
            note,
            "line_disposed",
            actor_id,
            {"line_id": str(line.id), "action": action, "condition": line.condition},
        )
        return line

    def _proposed_disposition(self, line: ReturnReceiptNoteItem) -> str | None:
        """Default routing when the supervisor does not override per line."""
        condition = line.condition
        if condition == "good":
            return "release_to_stock"
        if condition == "hold":
            return "move_to_hold"
        if condition in ("damaged", "quarantine"):
            return "move_to_quarantine"
        return None

    # ==================================================================
    # R-07 — put-away generation
    # ==================================================================

    def generate_put_away(
        self,
        note_id: UUID,
        organization_id: UUID,
        user,
        worker_ids: list[UUID] | None,
    ) -> dict:
        note = self.get_note(note_id, organization_id)
        self._assert_manager(user, note.warehouse_id)

        if note.status != "approved":
            raise StateError(
                "Approve the note before generating put-away",
                current_state=note.status,
                required_state=["approved"],
                code="RETURN_NOTE_NOT_PENDING_APPROVAL",
            )
        if note.put_away_generated_at is not None:
            raise StateError(
                "Put-away has already been generated for this note",
                current_state="generated",
                required_state=["approved"],
                code="RETURN_PUTAWAY_ALREADY_GENERATED",
            )

        releasable = [
            i
            for i in note.items
            if i.disposition == "release_to_stock" and i.condition == "good"
        ]
        # Group by SKU so one SKU never spans two workers (same rule as inbound).
        groups: dict[str, list[ReturnReceiptNoteItem]] = {}
        for line in releasable:
            groups.setdefault(line.sku or "UNKNOWN", []).append(line)

        workers = [w for w in (worker_ids or []) if w]
        chunks = self._split_groups(groups, max(len(workers), 1))

        lists: list[PutAwayList] = []
        numbering = DocumentNumberingService(self.db)
        for idx, chunk in enumerate(chunks):
            if not chunk:
                continue
            worker_id = workers[idx] if idx < len(workers) else None
            put_away = PutAwayList(
                organization_id=organization_id,
                warehouse_id=note.warehouse_id,
                put_away_list_no=numbering.get_next_number(
                    organization_id, "put_away_list"
                ),
                status="pending",
                reference_type="return_receipt_note",
                reference_id=note.id,
                remarks=f"Return put-away for {note.note_no}",
                assigned_to=worker_id,
                created_by=user.id,
            )
            self.db.add(put_away)
            self.db.flush()

            for order, line in enumerate(chunk):
                self.db.add(
                    PutAwayListItem(
                        organization_id=organization_id,
                        put_away_list_id=put_away.id,
                        item_id=line.item_id,
                        sku=line.sku,
                        batch_number=line.batch_number,
                        serial_nos=[line.serial_number] if line.serial_number else None,
                        quantity=self._to_decimal(line.quantity),
                        bin_location_id=self._suggest_bin(
                            line, note.warehouse_id, organization_id
                        ),
                        sort_order=order,
                        status="pending",
                    )
                )
            self.db.flush()
            if worker_id:
                from app.services.task_service import TaskService

                TaskService(self.db).create_task(
                    task_type="put_away",
                    worker_id=worker_id,
                    reference_id=put_away.id,
                    org_id=organization_id,
                    commit=False,
                )
            lists.append(put_away)

        note.put_away_generated_at = datetime.now(UTC)
        registration = self.get_registration(note.registration_id, organization_id)
        registration.status = "closed"
        self._event(
            note,
            "put_away_generated",
            user.id,
            {"lists": [str(lst.id) for lst in lists], "lines": len(releasable)},
        )
        self.db.flush()
        return {
            "put_away_lists": [
                {
                    "id": lst.id,
                    "list_no": lst.put_away_list_no,
                    "assigned_to": lst.assigned_to,
                    "item_count": len(lst.items),
                }
                for lst in lists
            ],
            "segregated_lines": len(note.items) - len(releasable),
            "note_status": note.status,
        }

    def _split_groups(
        self, groups: dict[str, list[ReturnReceiptNoteItem]], worker_count: int
    ) -> list[list[ReturnReceiptNoteItem]]:
        """Largest-first balance of whole SKUs across workers."""
        buckets: list[list[ReturnReceiptNoteItem]] = [[] for _ in range(worker_count)]
        loads = [Decimal("0")] * worker_count
        ordered = sorted(
            groups.values(),
            key=lambda lines: sum(
                (self._to_decimal(line.quantity) for line in lines), Decimal("0")
            ),
            reverse=True,
        )
        for lines in ordered:
            idx = loads.index(min(loads))
            buckets[idx].extend(lines)
            loads[idx] += sum(
                (self._to_decimal(line.quantity) for line in lines), Decimal("0")
            )
        return buckets

    def _suggest_bin(
        self, line: ReturnReceiptNoteItem, warehouse_id: UUID, organization_id: UUID
    ) -> UUID | None:
        """Best-effort bin pre-assignment; workers may override on completion."""
        if line.item_id is None:
            return None
        try:
            item = self.db.query(Item).filter(Item.id == line.item_id).first()
            assignments = PutAwayServiceAssignBins(self.db).assign(
                item_id=line.item_id,
                item_group_id=item.item_group_id if item else None,
                quantity=self._to_decimal(line.quantity),
                warehouse_id=warehouse_id,
                org_id=organization_id,
            )
            return assignments[0]["bin_location_id"] if assignments else None
        except Exception:  # noqa: BLE001 - bin suggestion must never block approval
            logger.warning("Return put-away bin suggestion failed", exc_info=True)
            return None

    # ==================================================================
    # R-08 — return slip
    # ==================================================================

    def build_slip(self, note_id: UUID, organization_id: UUID) -> dict:
        note = self.get_note(note_id, organization_id)
        registration = self.get_registration(note.registration_id, organization_id)
        warehouse = (
            self.db.query(Warehouse).filter(Warehouse.id == note.warehouse_id).first()
        )

        by_sku: dict[str, dict] = {}
        for line in note.items:
            key = line.sku or "UNKNOWN"
            entry = by_sku.setdefault(
                key,
                {
                    "sku": line.sku,
                    "item_name": line.item_name,
                    "expected_qty": 0.0,
                    "received_qty": 0.0,
                    "conditions": {},
                    "reason_codes": [],
                    "serials": [],
                },
            )
            entry["received_qty"] += float(self._to_decimal(line.quantity))
            if line.condition:
                entry["conditions"][line.condition] = entry["conditions"].get(
                    line.condition, 0.0
                ) + float(self._to_decimal(line.quantity))
            if line.reason_code and line.reason_code not in entry["reason_codes"]:
                entry["reason_codes"].append(line.reason_code)
            if line.serial_number:
                entry["serials"].append(line.serial_number)

        for reg_line in registration.items:
            key = reg_line.sku or "UNKNOWN"
            if key in by_sku:
                by_sku[key]["expected_qty"] += float(
                    self._to_decimal(reg_line.expected_qty)
                )
            else:
                by_sku[key] = {
                    "sku": reg_line.sku,
                    "item_name": reg_line.item_name,
                    "expected_qty": float(self._to_decimal(reg_line.expected_qty)),
                    "received_qty": 0.0,
                    "conditions": {},
                    "reason_codes": [],
                    "serials": [],
                }

        return {
            "slip_no": note.note_no,
            "generated_at": datetime.now(UTC),
            "registration_no": registration.registration_no,
            "invoice_no": registration.reference_no,
            "party": {
                "id": registration.party_id,
                "name": registration.party_name,
            },
            "warehouse": {"id": note.warehouse_id, "name": warehouse.name}
            if warehouse
            else None,
            "approved_by": note.approved_by,
            "approved_at": note.approved_at,
            "lines": list(by_sku.values()),
            "totals": {
                "expected_qty": float(self._to_decimal(note.expected_qty)),
                "received_qty": float(self._to_decimal(note.received_qty)),
                "short_qty": float(self._to_decimal(note.short_qty)),
            },
        }

    # ==================================================================
    # internals
    # ==================================================================

    def _open_session_for(self, registration_id: UUID) -> ReturnSession | None:
        return (
            self.db.query(ReturnSession)
            .filter(
                ReturnSession.registration_id == registration_id,
                ReturnSession.status == "open",
            )
            .first()
        )

    def _resolve_item(self, organization_id: UUID, sku: str) -> tuple[Item | None, str]:
        item = (
            self.db.query(Item)
            .filter(
                Item.organization_id == organization_id,
                ((Item.sku == sku) | (Item.item_code == sku)),
            )
            .first()
        )
        if item is None:
            return None, sku
        return item, (item.sku or item.item_code)

    def _sku_on_registration(self, registration: ReturnRegistration, sku: str) -> bool:
        return any(line.sku == sku for line in registration.items)

    def _match_line(
        self, registration: ReturnRegistration, payload: dict
    ) -> ReturnRegistrationItem | None:
        """Match a decoded QR payload to a registration line."""
        sku = payload.get("sku")
        qr_identifier = str(payload.get("id") or payload.get("qr_identifier") or "")
        if sku:
            for line in registration.items:
                if line.sku != sku:
                    continue
                serials = [str(s) for s in (line.serials or [])]
                if not serials or qr_identifier in serials:
                    return line
            # SKU known but serial not listed → still the right line for counting.
            for line in registration.items:
                if line.sku == sku:
                    return line
            return None
        for line in registration.items:
            serials = [str(s) for s in (line.serials or [])]
            if qr_identifier and qr_identifier in serials:
                return line
        return None

    def _decode_qr(self, qr_data: str) -> dict:
        try:
            payload = json.loads(qr_data)
        except (ValueError, TypeError):
            raise ValidationError(
                "The QR payload could not be decoded",
                code="RETURN_QR_INVALID",
                hint="Report the label as unreadable and retry the camera.",
            ) from None
        if not isinstance(payload, dict):
            raise ValidationError(
                "The QR payload is not a unit label",
                code="RETURN_QR_INVALID",
                hint="Report the label as unreadable and retry the camera.",
            )
        return payload

    def _resolve_classification(
        self,
        organization_id: UUID,
        condition: str,
        reason_code: str | None,
        destination: str | None,
    ) -> tuple[str | None, str | None]:
        """Validate the reason code and derive the segregation destination."""
        if condition != "good" and not reason_code:
            raise ValidationError(
                f"A reason code is required for a '{condition}' unit",
                details=[{"field": "reason_code", "reason": "Required unless good"}],
                code="RETURN_REASON_CODE_REQUIRED",
                hint="Open the reason picker and choose why the unit is not good.",
            )

        resolved_reason = reason_code
        reason = None
        if resolved_reason:
            reason = (
                self.db.query(InboundExceptionReason)
                .filter(InboundExceptionReason.code == resolved_reason)
                .first()
            )
            if reason is None:
                raise ValidationError(
                    f"Unknown reason code '{resolved_reason}'",
                    details=[{"field": "reason_code", "reason": "Unknown code"}],
                    code="RETURN_REASON_CODE_INVALID",
                    hint="Refresh the reason list and pick again.",
                )

        if destination:
            resolved_destination = destination.strip().upper()
            if resolved_destination not in InboundExceptionService.DESTINATIONS:
                raise ValidationError(
                    f"Invalid destination '{destination}'",
                    details=[
                        {
                            "field": "destination",
                            "reason": "Must be HOLD, QUARANTINE or DAMAGED",
                        }
                    ],
                    code="RETURN_DESTINATION_INVALID",
                )
        elif condition == "good":
            resolved_destination = None
        elif reason is not None and reason.default_destination:
            resolved_destination = reason.default_destination.strip().upper()
        else:
            resolved_destination = CONDITION_DESTINATIONS.get(condition)

        if not resolved_reason and condition == "good":
            resolved_reason = self.DEFAULT_CONDITION_REASONS["good"]
        return resolved_reason, resolved_destination

    def _segregate(
        self,
        *,
        session: ReturnSession,
        item: ReturnSessionItem,
        condition: str,
        reason_code: str | None,
        destination: str | None,
        note: str | None,
        organization_id: UUID,
        actor_id: UUID,
    ) -> InboundException:
        """Create the exception and put the unit in its non-pickable bin."""
        exception = InboundException(
            organization_id=organization_id,
            warehouse_id=session.warehouse_id,
            item_id=item.item_id,
            exception_type="return_condition",
            reason_code=reason_code or condition.upper(),
            status="pending_approval",
            condition_code=condition.upper(),
            destination=destination,
            qr_identifier=item.qr_identifier,
            sku=item.sku,
            batch_number=item.batch_number,
            quantity=int(self._to_decimal(item.quantity)),
            note=note,
            created_by=actor_id,
            metadata_json={
                "source": "returns",
                "return_session_id": str(session.id),
                "registration_id": str(session.registration_id),
                "condition": condition,
            },
        )
        self.db.add(exception)
        self.db.flush()

        if destination:
            bin_location = ScannedItemTrackingService(
                self.db
            )._get_or_create_system_bin(
                session.warehouse_id, organization_id, destination
            )
            inventory_status = InboundExceptionService.inventory_status_for_destination(
                destination
            )
            if item.item_id is not None:
                BinStockService(self.db).add_stock(
                    bin_id=bin_location.id,
                    item_id=item.item_id,
                    quantity=self._to_decimal(item.quantity),
                    org_id=organization_id,
                    batch_number=item.batch_number or item.qr_identifier,
                    commit=False,
                    inventory_status=inventory_status,
                )
                item.stock_entered = True
                item.stock_location_id = bin_location.id
            exception.destination_location_id = bin_location.id

        self.db.flush()

        try:
            InboundExceptionService(self.db).notify_supervisors(
                exception, exclude_user_id=actor_id
            )
        except Exception:  # noqa: BLE001 - alerting must never lose the exception
            logger.warning("Return supervisor alert failed", exc_info=True)
        return exception

    def _record_identity_exception(
        self,
        registration: ReturnRegistration,
        session: ReturnSession,
        actor_id: UUID,
        qr_identifier: str,
        payload: dict,
        active: dict,
    ) -> None:
        """Record a duplicate identity against the return before hard-stopping."""
        self.db.add(
            InboundException(
                organization_id=registration.organization_id,
                warehouse_id=session.warehouse_id,
                exception_type="duplicate_serial",
                reason_code=DUPLICATE_SERIAL_REASON,
                status="pending_approval",
                condition_code="UNKNOWN",
                destination="HOLD",
                qr_identifier=qr_identifier,
                sku=payload.get("sku"),
                batch_number=payload.get("batch"),
                quantity=1,
                note=f"Return scan hit active stock ({active.get('source')}): {active.get('detail')}",
                created_by=actor_id,
                metadata_json={
                    "source": "returns",
                    "return_session_id": str(session.id),
                    "registration_id": str(registration.id),
                    "active_stock": active,
                },
            )
        )
        self.db.flush()

    def _create_note(
        self,
        registration: ReturnRegistration,
        session: ReturnSession,
        session_items: list[ReturnSessionItem],
        organization_id: UUID,
        actor_id: UUID | None,
    ) -> ReturnReceiptNote:
        note = ReturnReceiptNote(
            organization_id=organization_id,
            note_no=DocumentNumberingService(self.db).get_next_number(
                organization_id, "return_receipt"
            ),
            # The dock produced every line and every condition, so the note is
            # immediately reviewable — see module notes on the draft transition.
            status="pending_approval",
            registration_id=registration.id,
            session_id=session.id,
            warehouse_id=registration.warehouse_id,
            expected_qty=self._to_decimal(registration.expected_qty),
            received_qty=Decimal("0"),
            short_qty=Decimal("0"),
            created_by=actor_id,
        )
        self.db.add(note)
        self.db.flush()

        counters = {
            "good": Decimal("0"),
            "damaged": Decimal("0"),
            "hold": Decimal("0"),
            "quarantine": Decimal("0"),
        }
        total_received = Decimal("0")
        for order, item in enumerate(session_items):
            qty = self._to_decimal(item.quantity)
            total_received += qty
            if item.condition in counters:
                counters[item.condition] += qty
            self.db.add(
                ReturnReceiptNoteItem(
                    organization_id=organization_id,
                    note_id=note.id,
                    registration_item_id=item.registration_item_id,
                    session_item_id=item.id,
                    item_id=item.item_id,
                    sku=item.sku,
                    item_name=self._item_name(item.item_id),
                    uom="NOS",
                    serial_number=item.serial_number,
                    batch_number=item.batch_number,
                    quantity=qty,
                    condition=item.condition,
                    reason_code=item.reason_code,
                    note=item.note,
                    destination=item.destination,
                    exception_id=item.exception_id,
                    sort_order=order,
                )
            )

        note.received_qty = total_received
        note.short_qty = max(
            self._to_decimal(registration.expected_qty) - total_received, Decimal("0")
        )
        note.good_qty = counters["good"]
        note.damaged_qty = counters["damaged"]
        note.hold_qty = counters["hold"]
        note.quarantine_qty = counters["quarantine"]
        self._event(
            note,
            "created",
            actor_id,
            {
                "received_qty": float(total_received),
                "conditions": {k: float(v) for k, v in counters.items()},
            },
        )
        self.db.flush()
        return note

    def _item_name(self, item_id: UUID | None) -> str | None:
        if item_id is None:
            return None
        item = self.db.query(Item).filter(Item.id == item_id).first()
        return item.item_name if item else None

    def _apply_disposition_stock(
        self, note: ReturnReceiptNote, line: ReturnReceiptNoteItem, action: str
    ) -> None:
        """Move or remove the physical stock implied by a disposition."""
        if line.item_id is None:
            return
        quantity = self._to_decimal(line.quantity)

        if action == "release_to_stock":
            # Good stock is only entered by put-away completion (R-07).
            return

        source = self._location_of_exception(line.exception_id)

        destination = self.DISPOSITION_DESTINATIONS.get(action)
        if destination:
            target = ScannedItemTrackingService(self.db)._get_or_create_system_bin(
                note.warehouse_id, note.organization_id, destination
            )
            status = InboundExceptionService.inventory_status_for_destination(
                destination
            )
            if source is None:
                # Not segregated yet (e.g. a good line re-routed to hold) → enter it.
                BinStockService(self.db).add_stock(
                    bin_id=target.id,
                    item_id=line.item_id,
                    quantity=quantity,
                    org_id=note.organization_id,
                    batch_number=line.batch_number or line.serial_number,
                    commit=False,
                    inventory_status=status,
                )
            elif source != target.id:
                BinStockService(self.db).transfer_stock(
                    from_bin_id=source,
                    to_bin_id=target.id,
                    item_id=line.item_id,
                    quantity=quantity,
                    org_id=note.organization_id,
                    batch_number=line.batch_number or line.serial_number,
                    inventory_status=status,
                )
            self._retarget_exception(line.exception_id, destination, target.id)

        if action in self.STOCK_REMOVING_DISPOSITIONS:
            if source is not None:
                BinStockService(self.db).remove_stock(
                    source,
                    line.item_id,
                    quantity,
                    note.organization_id,
                    line.batch_number or line.serial_number,
                    commit=False,
                )
            exception = self._exception_for(line.exception_id)
            if exception is not None:
                exception.status = "closed"
                exception.disposition = action
                exception.disposed_by = line.disposed_by
                exception.disposed_at = datetime.now(UTC)

    def _retarget_exception(
        self, exception_id: UUID | None, destination: str, bin_id: UUID
    ) -> None:
        exception = self._exception_for(exception_id)
        if exception is None:
            return
        exception.destination = destination
        exception.destination_location_id = bin_id

    def _exception_for(self, exception_id: UUID | None) -> InboundException | None:
        if not exception_id:
            return None
        return (
            self.db.query(InboundException)
            .filter(InboundException.id == exception_id)
            .first()
        )

    def _location_of_exception(self, exception_id: UUID | None) -> UUID | None:
        exception = self._exception_for(exception_id)
        return exception.destination_location_id if exception else None

    def _event(
        self,
        note: ReturnReceiptNote,
        event_type: str,
        actor_id: UUID | None,
        details: dict | None = None,
    ) -> None:
        self.db.add(
            ReturnReceiptNoteEvent(
                note_id=note.id,
                organization_id=note.organization_id,
                event_type=event_type,
                actor_id=actor_id,
                details=details,
            )
        )

    def _assert_manager(self, user, warehouse_id: UUID) -> None:
        try:
            InboundExceptionService(self.db).assert_manager(user, warehouse_id)
        except StateError as exc:
            raise StateError(
                "Warehouse Manager approval is required for this return",
                current_state=exc.current_state,
                required_state=exc.required_state,
                code="RETURN_APPROVAL_REQUIRED",
                hint="Ask a warehouse manager to approve or dispose of this note.",
            ) from None

    @staticmethod
    def _to_decimal(value) -> Decimal:
        if value is None:
            return Decimal("0")
        if isinstance(value, Decimal):
            return value
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            return Decimal("0")

    # ==================================================================
    # aggregation helpers used by the API layer
    # ==================================================================

    def serialize_registration(self, registration: ReturnRegistration) -> dict:
        warehouse = (
            self.db.query(Warehouse)
            .filter(Warehouse.id == registration.warehouse_id)
            .first()
        )
        condition_counts: dict[UUID, dict[str, float]] = {}
        for line in registration.items:
            condition_counts[line.id] = {
                "good": 0.0,
                "damaged": 0.0,
                "hold": 0.0,
                "quarantine": 0.0,
            }
        rows = (
            self.db.query(
                ReturnSessionItem.registration_item_id,
                ReturnSessionItem.condition,
                func.sum(ReturnSessionItem.quantity),
            )
            .filter(ReturnSessionItem.registration_id == registration.id)
            .group_by(
                ReturnSessionItem.registration_item_id, ReturnSessionItem.condition
            )
            .all()
        )
        for line_id, condition, qty in rows:
            if line_id in condition_counts and condition in condition_counts[line_id]:
                condition_counts[line_id][condition] = float(self._to_decimal(qty))

        return {
            "id": registration.id,
            "registration_no": registration.registration_no,
            "status": registration.status,
            "reference_type": registration.reference_type,
            "invoice_no": registration.reference_no,
            "party": {"id": registration.party_id, "name": registration.party_name},
            "warehouse": {"id": registration.warehouse_id, "name": warehouse.name}
            if warehouse
            else None,
            "return_reason_code": registration.return_reason_code,
            "note": registration.note,
            "expected_qty": float(self._to_decimal(registration.expected_qty)),
            "received_qty": float(self._to_decimal(registration.received_qty)),
            "created_at": registration.created_at,
            "lines": [
                {
                    "id": line.id,
                    "sku": line.sku,
                    "item_name": line.item_name,
                    "uom": line.uom,
                    "expected_qty": float(self._to_decimal(line.expected_qty)),
                    "received_qty": float(self._to_decimal(line.received_qty)),
                    "serials": line.serials,
                    "conditions": condition_counts.get(line.id, {}),
                }
                for line in registration.items
            ],
            "sessions": [
                {
                    "id": s.id,
                    "status": s.status,
                    "started_at": s.started_at,
                    "ended_at": s.ended_at,
                    "worker_id": s.started_by,
                }
                for s in registration.sessions
            ],
        }

    def serialize_registration_list_item(
        self, registration: ReturnRegistration
    ) -> dict:
        warehouse = (
            self.db.query(Warehouse)
            .filter(Warehouse.id == registration.warehouse_id)
            .first()
        )
        return {
            "id": registration.id,
            "registration_no": registration.registration_no,
            "status": registration.status,
            "reference_type": registration.reference_type,
            "invoice_no": registration.reference_no,
            "return_reason_code": registration.return_reason_code,
            "party_name": registration.party_name,
            "warehouse_name": warehouse.name if warehouse else None,
            "warehouse_id": registration.warehouse_id,
            "expected_qty": float(self._to_decimal(registration.expected_qty)),
            "received_qty": float(self._to_decimal(registration.received_qty)),
            "created_at": registration.created_at,
        }

    def serialize_session(self, session: ReturnSession, detailed: bool) -> dict:
        registration = self.get_registration(
            session.registration_id, session.organization_id
        )
        warehouse = (
            self.db.query(Warehouse)
            .filter(Warehouse.id == session.warehouse_id)
            .first()
        )
        data = {
            "id": session.id,
            "registration_id": session.registration_id,
            "registration_no": registration.registration_no,
            "warehouse": {"id": session.warehouse_id, "name": warehouse.name}
            if warehouse
            else None,
            "status": session.status,
            "dock_location": session.dock_location,
            "started_at": session.started_at,
            "ended_at": session.ended_at,
            "expected_qty": float(self._to_decimal(session.expected_qty)),
            "scanned_qty": float(self._to_decimal(session.scanned_qty)),
            "classified_qty": float(self._to_decimal(session.classified_qty)),
        }
        if not detailed:
            return data

        items = (
            self.db.query(ReturnSessionItem)
            .filter(ReturnSessionItem.session_id == session.id)
            .order_by(ReturnSessionItem.scanned_at)
            .all()
        )
        per_line: dict[UUID, dict] = {}
        for line in registration.items:
            per_line[line.id] = {
                "line_id": line.id,
                "sku": line.sku,
                "item_name": line.item_name,
                "uom": line.uom,
                "expected_qty": float(self._to_decimal(line.expected_qty)),
                "scanned_qty": 0.0,
                "classified_qty": 0.0,
                "serials": line.serials,
            }
        for item in items:
            if item.registration_item_id in per_line:
                bucket = per_line[item.registration_item_id]
                bucket["scanned_qty"] += float(self._to_decimal(item.quantity))
                if item.condition:
                    bucket["classified_qty"] += float(self._to_decimal(item.quantity))

        data["lines"] = list(per_line.values())
        data["items"] = [
            {
                "id": item.id,
                "qr_identifier": item.qr_identifier,
                "sku": item.sku,
                "serial_number": item.serial_number,
                "quantity": float(self._to_decimal(item.quantity)),
                "condition": item.condition,
                "reason_code": item.reason_code,
                "destination": item.destination,
                "exception_id": item.exception_id,
                "over_receipt": bool(item.over_receipt),
            }
            for item in items
        ]
        return data

    def serialize_scan(self, item: ReturnSessionItem) -> dict:
        line = (
            self.db.query(ReturnRegistrationItem)
            .filter(ReturnRegistrationItem.id == item.registration_item_id)
            .first()
        )
        return {
            "item_id": item.id,
            "qr_identifier": item.qr_identifier,
            "sku": item.sku,
            "matched_line_id": item.registration_item_id,
            "quantity": float(self._to_decimal(item.quantity)),
            "serial_expected": bool(line.serials) if line else False,
            "over_receipt": bool(item.over_receipt),
            "condition": item.condition,
            "scanned_qty": float(self._to_decimal(line.received_qty)) if line else 0.0,
            "expected_qty": float(self._to_decimal(line.expected_qty)) if line else 0.0,
            "next_action": "classify",
        }

    def serialize_note_list_item(self, note: ReturnReceiptNote) -> dict:
        registration = self.get_registration(note.registration_id, note.organization_id)
        warehouse = (
            self.db.query(Warehouse).filter(Warehouse.id == note.warehouse_id).first()
        )
        open_exceptions = sum(1 for i in note.items if i.exception_id)
        return {
            "id": note.id,
            "note_no": note.note_no,
            "status": note.status,
            "registration_no": registration.registration_no,
            "registration_id": note.registration_id,
            "warehouse_name": warehouse.name if warehouse else None,
            "warehouse_id": note.warehouse_id,
            "expected_qty": float(self._to_decimal(note.expected_qty)),
            "received_qty": float(self._to_decimal(note.received_qty)),
            "mismatch": self._to_decimal(note.expected_qty)
            != self._to_decimal(note.received_qty),
            "damaged_qty": float(self._to_decimal(note.damaged_qty)),
            "open_exceptions": open_exceptions,
            "created_at": note.created_at,
        }

    def serialize_note_detail(self, note: ReturnReceiptNote) -> dict:
        registration = self.get_registration(note.registration_id, note.organization_id)
        warehouse = (
            self.db.query(Warehouse).filter(Warehouse.id == note.warehouse_id).first()
        )
        groups: dict[str, dict] = {}
        for line in note.items:
            key = line.sku or "UNKNOWN"
            group = groups.setdefault(
                key,
                {
                    "product_name": line.item_name,
                    "sku": line.sku,
                    "item_id": line.item_id,
                    "expected_qty": 0.0,
                    "received_qty": 0.0,
                    "short_qty": 0.0,
                    "items": [],
                },
            )
            group["received_qty"] += float(self._to_decimal(line.quantity))
            group["items"].append(
                {
                    "id": line.id,
                    "serial_number": line.serial_number,
                    "batch_number": line.batch_number,
                    "quantity": float(self._to_decimal(line.quantity)),
                    "uom": line.uom,
                    "condition": line.condition,
                    "reason_code": line.reason_code,
                    "note": line.note,
                    "exception_id": line.exception_id,
                    "destination": line.destination,
                    "disposition": line.disposition,
                    "disposed_at": line.disposed_at,
                }
            )
        for reg_line in registration.items:
            key = reg_line.sku or "UNKNOWN"
            if key in groups:
                expected = float(self._to_decimal(reg_line.expected_qty))
                groups[key]["expected_qty"] += expected
                groups[key]["short_qty"] = max(
                    expected - groups[key]["received_qty"], 0.0
                )
            else:
                expected = float(self._to_decimal(reg_line.expected_qty))
                groups[key] = {
                    "product_name": reg_line.item_name,
                    "sku": reg_line.sku,
                    "item_id": reg_line.item_id,
                    "expected_qty": expected,
                    "received_qty": 0.0,
                    "short_qty": expected,
                    "items": [],
                }

        flat = [item for group in groups.values() for item in group["items"]]
        return {
            "id": note.id,
            "note_no": note.note_no,
            "status": note.status,
            "registration_id": note.registration_id,
            "registration_no": registration.registration_no,
            "warehouse": {"id": note.warehouse_id, "name": warehouse.name}
            if warehouse
            else None,
            "expected_qty": float(self._to_decimal(note.expected_qty)),
            "received_qty": float(self._to_decimal(note.received_qty)),
            "short_qty": float(self._to_decimal(note.short_qty)),
            "conditions": {
                "good": float(self._to_decimal(note.good_qty)),
                "damaged": float(self._to_decimal(note.damaged_qty)),
                "hold": float(self._to_decimal(note.hold_qty)),
                "quarantine": float(self._to_decimal(note.quarantine_qty)),
            },
            "approved_by": note.approved_by,
            "approved_at": note.approved_at,
            "rejected_at": note.rejected_at,
            "rejection_reason": note.rejection_reason,
            "put_away_generated_at": note.put_away_generated_at,
            "created_at": note.created_at,
            "groups": list(groups.values()),
            "lines": flat,
        }


class PutAwayServiceAssignBins:
    """Thin adapter over :class:`PutAwayService` bin allocation.

    ``_assign_bins`` already owns the allocation/capacity/reservation rules and
    returns plain dicts. Routing return put-away through it keeps one
    implementation of "where does this stock go" instead of two.
    """

    def __init__(self, db: Session):
        from app.services.put_away_service import PutAwayService

        self._service = PutAwayService(db)

    def assign(
        self,
        *,
        item_id: UUID,
        item_group_id: UUID | None,
        quantity: Decimal,
        warehouse_id: UUID,
        org_id: UUID,
    ) -> list[dict]:
        return self._service._assign_bins(  # noqa: SLF001 - shared allocation rules
            item_id=item_id,
            item_group_id=item_group_id,
            quantity=quantity,
            warehouse_id=warehouse_id,
            org_id=org_id,
        )
