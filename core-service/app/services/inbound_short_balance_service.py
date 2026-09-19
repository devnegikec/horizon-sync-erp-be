"""Maintain shortage balances against ASN lines and their latest receipt note.

Short-receipt model (see ``INBOUND_EXCEPTION_AND_RETURNS_GAP_ANALYSIS.md`` §3.1):

* only the **actual accepted** quantity is posted to stock; the ASN expectation
  (``asn_order_items.qty``) is never modified,
* the residual difference is projected into ``inbound_short_balances`` and stays
  visible against the ASN until it is received later or formally closed,
* every change is appended to ``inbound_short_balance_events`` so a shortage
  stays traceable across vehicle arrivals,
* a residual short can be closed by an authorized manager with a reason code,
  approver and timestamp.

Errors carry a stable machine-readable ``code``, a human ``message`` and an
actionable ``hint`` so the frontend can tell the operator exactly what to fix.
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.asn_order import AsnOrder
from app.models.inbound_exception import InboundExceptionReason
from app.models.inbound_short_balance import (
    BALANCE_STATUS_OPEN,
    BALANCE_STATUS_RESOLVED,
    BALANCE_STATUS_WRITTEN_OFF,
    InboundShortBalance,
    InboundShortBalanceEvent,
)

#: Closure outcomes accepted by :meth:`InboundShortBalanceService.close_balance`
CLOSE_OUTCOMES = ("written_off", "resolved_by_receipt")

#: Reason-code category used by the shortage (and closure) reason codes.
_SHORTAGE_CATEGORY = "short"


class InboundShortBalanceService:
    """Projects approved-receipt quantities into a queryable short ledger."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # PROJECTION (called on receiving-slip approval / put-away)
    # ------------------------------------------------------------------

    def refresh_for_asn(
        self,
        asn_order_id: UUID,
        organization_id: UUID,
        receiving_slip_id: UUID | None,
    ) -> None:
        """Recompute every ASN line balance and append history events.

        ``expected`` always comes from the ASN line; ``received`` only ever
        counts accepted receipts. A balance closed as ``written_off`` keeps that
        decision — the numbers refresh for traceability but the manager's
        approval is not silently undone.
        """
        asn = (
            self.db.query(AsnOrder)
            .filter(
                AsnOrder.id == asn_order_id,
                AsnOrder.organization_id == organization_id,
            )
            .first()
        )
        if asn is None:
            return

        dock_reasons = self._dock_reason_codes(receiving_slip_id, organization_id)

        for asn_item in asn.items:
            expected = Decimal(str(asn_item.qty or 0))
            received = Decimal(str(asn_item.delivered_qty or 0))
            short = max(Decimal("0"), expected - received)

            balance = (
                self.db.query(InboundShortBalance)
                .filter(
                    InboundShortBalance.organization_id == organization_id,
                    InboundShortBalance.asn_order_item_id == asn_item.id,
                )
                .first()
            )

            sku = (
                (asn_item.item.sku or asn_item.item.item_code)
                if asn_item.item
                else str(asn_item.item_id)
            )
            dock_reason = dock_reasons.get(asn_item.item_id)

            if balance is None:
                balance = InboundShortBalance(
                    organization_id=organization_id,
                    asn_order_item_id=asn_item.id,
                    asn_order_id=asn.id,
                    receiving_slip_id=receiving_slip_id,
                    item_id=asn_item.item_id,
                    sku=sku,
                    expected_qty=expected,
                    received_qty=received,
                    short_qty=short,
                    status=BALANCE_STATUS_OPEN
                    if short > 0
                    else BALANCE_STATUS_RESOLVED,
                    reason_code=dock_reason,
                )
                self.db.add(balance)
                self.db.flush()
                self._event(
                    balance,
                    event_type="created",
                    from_status=None,
                    to_status=balance.status,
                    reason_code=dock_reason,
                    actor_id=None,
                )
                continue

            previous = (
                Decimal(str(balance.expected_qty)),
                Decimal(str(balance.received_qty)),
                Decimal(str(balance.short_qty)),
                balance.status,
            )

            balance.asn_order_id = asn.id
            balance.receiving_slip_id = receiving_slip_id
            balance.item_id = asn_item.item_id
            balance.sku = sku
            balance.expected_qty = expected
            balance.received_qty = received
            balance.short_qty = short
            if dock_reason and not balance.reason_code:
                balance.reason_code = dock_reason

            if balance.status != BALANCE_STATUS_WRITTEN_OFF:
                balance.status = (
                    BALANCE_STATUS_OPEN if short > 0 else BALANCE_STATUS_RESOLVED
                )

            if (
                expected,
                received,
                short,
                balance.status,
            ) != previous:
                self._event(
                    balance,
                    event_type=(
                        "resolved"
                        if balance.status == BALANCE_STATUS_RESOLVED
                        else "updated"
                    ),
                    from_status=previous[3],
                    to_status=balance.status,
                    reason_code=balance.reason_code,
                    actor_id=None,
                )

        self.db.commit()

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    def list_for_asn(
        self, asn_order_id: UUID, organization_id: UUID
    ) -> list[InboundShortBalance]:
        return (
            self.db.query(InboundShortBalance)
            .filter(
                InboundShortBalance.asn_order_id == asn_order_id,
                InboundShortBalance.organization_id == organization_id,
            )
            .order_by(InboundShortBalance.sku)
            .all()
        )

    def list_balances(
        self,
        organization_id: UUID,
        *,
        asn_order_id: UUID | None = None,
        status: str | None = None,
        sku: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[InboundShortBalance], int]:
        """Paginated shortage ledger with optional filters."""
        if status is not None and status not in (
            BALANCE_STATUS_OPEN,
            BALANCE_STATUS_RESOLVED,
            BALANCE_STATUS_WRITTEN_OFF,
        ):
            raise ValidationError(
                message=f"Unsupported shortage status filter: '{status}'",
                details=[
                    {
                        "field": "status",
                        "reason": f"'{status}' is not a known shortage status",
                        "hint": "Use one of: open, resolved, written_off",
                    }
                ],
                code="SHORTAGE_STATUS_INVALID",
                hint="Use one of: open, resolved, written_off",
            )

        query = self.db.query(InboundShortBalance).filter(
            InboundShortBalance.organization_id == organization_id
        )
        if asn_order_id:
            query = query.filter(InboundShortBalance.asn_order_id == asn_order_id)
        if status:
            query = query.filter(InboundShortBalance.status == status)
        if sku:
            query = query.filter(InboundShortBalance.sku.ilike(f"%{sku}%"))

        total = query.count()
        items = (
            query.order_by(InboundShortBalance.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def summarize(
        self,
        organization_id: UUID,
        *,
        asn_order_id: UUID | None = None,
        sku: str | None = None,
    ) -> dict:
        """Counts and quantities per status for the supervisor worklist."""
        query = (
            self.db.query(
                InboundShortBalance.status,
                func.count(InboundShortBalance.id),
                func.coalesce(func.sum(InboundShortBalance.short_qty), 0),
            )
            .filter(InboundShortBalance.organization_id == organization_id)
            .group_by(InboundShortBalance.status)
        )
        if asn_order_id:
            query = query.filter(InboundShortBalance.asn_order_id == asn_order_id)
        if sku:
            query = query.filter(InboundShortBalance.sku.ilike(f"%{sku}%"))

        counts = dict.fromkeys(
            (BALANCE_STATUS_OPEN, BALANCE_STATUS_RESOLVED, BALANCE_STATUS_WRITTEN_OFF),
            0,
        )
        quantities = dict(counts)
        for status, count, total_short in query.all():
            counts[status] = int(count)
            quantities[status] = float(total_short or 0)

        return {
            "total": sum(counts.values()),
            "open_count": counts[BALANCE_STATUS_OPEN],
            "resolved_count": counts[BALANCE_STATUS_RESOLVED],
            "written_off_count": counts[BALANCE_STATUS_WRITTEN_OFF],
            "open_short_qty": quantities[BALANCE_STATUS_OPEN],
            "total_short_qty": sum(quantities.values()),
        }

    def get_balance(
        self, balance_id: UUID, organization_id: UUID
    ) -> InboundShortBalance:
        balance = (
            self.db.query(InboundShortBalance)
            .filter(
                InboundShortBalance.id == balance_id,
                InboundShortBalance.organization_id == organization_id,
            )
            .first()
        )
        if balance is None:
            raise NotFoundError(
                message=f"Shortage balance '{balance_id}' was not found",
                entity_type="InboundShortBalance",
                entity_id=str(balance_id),
                code="SHORT_BALANCE_NOT_FOUND",
                hint=(
                    "The balance may belong to another organization, or the "
                    "receipt for that ASN line has not been approved yet. "
                    "Refresh the shortage list."
                ),
            )
        return balance

    def list_events(
        self, balance_id: UUID, organization_id: UUID
    ) -> list[InboundShortBalanceEvent]:
        balance = self.get_balance(balance_id, organization_id)
        return (
            self.db.query(InboundShortBalanceEvent)
            .filter(
                InboundShortBalanceEvent.balance_id == balance.id,
                InboundShortBalanceEvent.organization_id == organization_id,
            )
            .order_by(InboundShortBalanceEvent.created_at.asc())
            .all()
        )

    # ------------------------------------------------------------------
    # CLOSE / WRITE-OFF
    # ------------------------------------------------------------------

    def close_balance(
        self,
        *,
        balance_id: UUID,
        organization_id: UUID,
        actor_id: UUID | None,
        user=None,
        outcome: str,
        reason_code: str | None,
        note: str | None = None,
    ) -> InboundShortBalance:
        """Formally close a residual shortage.

        ``outcome``:

        * ``written_off`` — accept the residual short as a loss (reason required),
        * ``resolved_by_receipt`` — the shortage was received later, so there is
          nothing left to write off.

        Requires warehouse-manager / org-admin authority, scoped to the ASN
        warehouse.
        """
        balance = self.get_balance(balance_id, organization_id)

        normalized_outcome = (outcome or "").strip().lower()
        if normalized_outcome not in CLOSE_OUTCOMES:
            raise ValidationError(
                message=f"Unsupported closure outcome: '{outcome}'",
                details=[
                    {
                        "field": "outcome",
                        "reason": f"'{outcome}' is not a supported closure outcome",
                        "hint": f"Use one of: {', '.join(CLOSE_OUTCOMES)}",
                    }
                ],
                code="SHORTAGE_OUTCOME_INVALID",
                hint=f"Use one of: {', '.join(CLOSE_OUTCOMES)}",
            )

        if balance.status == BALANCE_STATUS_WRITTEN_OFF:
            raise StateError(
                message=(
                    f"Shortage for SKU '{balance.sku}' was already closed as "
                    f"written off on {self._fmt_dt(balance.closed_at)}"
                ),
                current_state=balance.status,
                required_state=[BALANCE_STATUS_OPEN],
                code="SHORTAGE_ALREADY_CLOSED",
                hint=(
                    "This closure is final. Approve a new receipt for that ASN "
                    "line if further stock arrives."
                ),
            )

        short_qty = Decimal(str(balance.short_qty or 0))

        if short_qty <= 0:
            raise StateError(
                message=(
                    f"SKU '{balance.sku}' has no outstanding shortage — "
                    f"there is nothing to close"
                ),
                current_state=balance.status,
                required_state=[BALANCE_STATUS_OPEN],
                code="SHORTAGE_NOTHING_TO_CLOSE",
                hint=(
                    "The ASN line is fully received; the balance resolves "
                    "automatically once the receipt is approved."
                ),
            )

        if normalized_outcome == "resolved_by_receipt":
            raise StateError(
                message=(
                    f"SKU '{balance.sku}' is still short by "
                    f"{self._fmt_qty(short_qty)} unit(s)"
                ),
                current_state=balance.status,
                required_state=[BALANCE_STATUS_RESOLVED],
                code="SHORTAGE_STILL_OPEN",
                hint=(
                    "Approve the receipt that closes the gap, or close this "
                    "shortage as written_off if the stock will not arrive."
                ),
            )

        reason = self._resolve_reason(reason_code, organization_id)

        if user is not None:
            self._assert_can_close(user, balance)

        from_status = balance.status
        balance.status = BALANCE_STATUS_WRITTEN_OFF
        balance.close_reason_code = reason.code
        balance.close_note = note
        balance.closed_by = actor_id
        balance.closed_at = datetime.now(UTC)
        self._event(
            balance,
            event_type="written_off",
            from_status=from_status,
            to_status=BALANCE_STATUS_WRITTEN_OFF,
            reason_code=reason.code,
            note=note,
            actor_id=actor_id,
        )
        self.db.commit()
        self.db.refresh(balance)
        return balance

    # ------------------------------------------------------------------
    # HELPERS
    # ------------------------------------------------------------------

    def _resolve_reason(
        self, reason_code: str | None, organization_id: UUID
    ) -> InboundExceptionReason:
        """Validate the closure reason code with actionable feedback."""
        allowed = self._allowed_close_reasons(organization_id)
        allowed_codes = [reason.code for reason in allowed]

        if not reason_code:
            raise ValidationError(
                message="A reason code is required to close a shortage",
                details=[
                    {
                        "field": "reason_code",
                        "reason": "Missing required field 'reason_code'",
                        "hint": f"Use one of: {', '.join(allowed_codes)}",
                    }
                ],
                code="SHORTAGE_REASON_REQUIRED",
                hint=f"Pick one of: {', '.join(allowed_codes)}",
            )

        reason = next(
            (
                candidate
                for candidate in allowed
                if candidate.code.upper() == reason_code.strip().upper()
            ),
            None,
        )
        if reason is None:
            raise ValidationError(
                message=f"Unknown or inactive shortage reason code '{reason_code}'",
                details=[
                    {
                        "field": "reason_code",
                        "reason": (
                            f"'{reason_code}' is not an active shortage reason code"
                        ),
                        "hint": f"Use one of: {', '.join(allowed_codes)}",
                    }
                ],
                code="SHORTAGE_REASON_INVALID",
                hint=f"Pick one of: {', '.join(allowed_codes)}",
            )
        return reason

    def _allowed_close_reasons(
        self, organization_id: UUID
    ) -> list[InboundExceptionReason]:
        return (
            self.db.query(InboundExceptionReason)
            .filter(
                InboundExceptionReason.category == _SHORTAGE_CATEGORY,
                InboundExceptionReason.is_active.is_(True),
                (InboundExceptionReason.organization_id.is_(None))
                | (InboundExceptionReason.organization_id == organization_id),
            )
            .order_by(InboundExceptionReason.code)
            .all()
        )

    def _assert_can_close(self, user, balance: InboundShortBalance) -> None:
        """Require warehouse-manager authority, scoped to the ASN warehouse."""
        asn = (
            self.db.query(AsnOrder).filter(AsnOrder.id == balance.asn_order_id).first()
        )
        warehouse_id = (
            (asn.warehouse_id_to or asn.warehouse_id_from) if asn is not None else None
        )

        from app.services.inbound_exception_service import InboundExceptionService

        if warehouse_id is not None:
            try:
                InboundExceptionService(self.db).assert_manager(user, warehouse_id)
            except StateError as exc:
                # Re-raise with a shortage-specific code and an actionable hint so
                # the frontend can distinguish "ask a manager" from other conflicts.
                raise StateError(
                    message=exc.message,
                    current_state=exc.current_state,
                    required_state=exc.required_state,
                    code="SHORTAGE_APPROVAL_REQUIRED",
                    hint=(
                        "Ask a warehouse manager (or an organization admin) for "
                        "this warehouse to close the shortage."
                    ),
                ) from exc
            return

        permissions = getattr(user, "permissions", None) or []
        permitted = (
            getattr(user, "user_type", None) in {"system_admin", "organization_admin"}
            or "*.*" in permissions
            or "warehouse.manage" in permissions
        )
        if not permitted:
            raise StateError(
                message="Warehouse Manager approval is required to close a shortage",
                current_state="not_manager",
                required_state=["manager"],
                code="SHORTAGE_APPROVAL_REQUIRED",
                hint=(
                    "Ask a warehouse manager or an organization admin to close "
                    "this shortage."
                ),
            )

    def _dock_reason_codes(
        self, receiving_slip_id: UUID | None, organization_id: UUID
    ) -> dict[UUID, str]:
        """Reason code captured on the receipt line at the dock, keyed by item."""
        if receiving_slip_id is None:
            return {}

        from app.models.item import Item
        from app.models.receiving_slip import ReceivingSlipItem

        rows = (
            self.db.query(Item.id, ReceivingSlipItem.reason_code)
            .join(
                ReceivingSlipItem,
                or_(
                    Item.sku == ReceivingSlipItem.sku,
                    Item.item_code == ReceivingSlipItem.sku,
                    Item.gtin == ReceivingSlipItem.sku,
                ),
            )
            .filter(
                ReceivingSlipItem.slip_id == receiving_slip_id,
                ReceivingSlipItem.organization_id == organization_id,
                ReceivingSlipItem.reason_code.isnot(None),
                Item.organization_id == organization_id,
                Item.deleted_at.is_(None),
            )
            .all()
        )
        mapping: dict[UUID, str] = {}
        for item_id, reason_code in rows:
            mapping.setdefault(item_id, reason_code)
        return mapping

    def _event(
        self,
        balance: InboundShortBalance,
        *,
        event_type: str,
        from_status: str | None,
        to_status: str,
        reason_code: str | None = None,
        note: str | None = None,
        actor_id: UUID | None = None,
    ) -> None:
        self.db.add(
            InboundShortBalanceEvent(
                organization_id=balance.organization_id,
                balance_id=balance.id,
                receiving_slip_id=balance.receiving_slip_id,
                event_type=event_type,
                from_status=from_status,
                to_status=to_status,
                expected_qty=balance.expected_qty,
                received_qty=balance.received_qty,
                short_qty=balance.short_qty,
                reason_code=reason_code,
                note=note,
                actor_id=actor_id,
                created_at=datetime.now(UTC),
            )
        )

    @staticmethod
    def _fmt_qty(value: Decimal) -> str:
        return f"{value.normalize():f}"

    @staticmethod
    def _fmt_dt(value: datetime | None) -> str:
        return value.isoformat() if value else "an earlier date"

    # ------------------------------------------------------------------
    # SERIALIZATION
    # ------------------------------------------------------------------

    @staticmethod
    def serialize(balance: InboundShortBalance) -> dict:
        return {
            "id": balance.id,
            "organization_id": balance.organization_id,
            "asn_order_id": balance.asn_order_id,
            "asn_order_item_id": balance.asn_order_item_id,
            "receiving_slip_id": balance.receiving_slip_id,
            "item_id": balance.item_id,
            "sku": balance.sku,
            "expected_qty": balance.expected_qty,
            "received_qty": balance.received_qty,
            "short_qty": balance.short_qty,
            "status": balance.status,
            "reason_code": balance.reason_code,
            "note": balance.note,
            "close_reason_code": balance.close_reason_code,
            "close_note": balance.close_note,
            "closed_by": balance.closed_by,
            "closed_at": balance.closed_at,
            "created_at": balance.created_at,
            "updated_at": balance.updated_at,
        }

    @staticmethod
    def serialize_event(event: InboundShortBalanceEvent) -> dict:
        return {
            "id": event.id,
            "balance_id": event.balance_id,
            "receiving_slip_id": event.receiving_slip_id,
            "event_type": event.event_type,
            "from_status": event.from_status,
            "to_status": event.to_status,
            "expected_qty": event.expected_qty,
            "received_qty": event.received_qty,
            "short_qty": event.short_qty,
            "reason_code": event.reason_code,
            "note": event.note,
            "actor_id": event.actor_id,
            "created_at": event.created_at,
        }
