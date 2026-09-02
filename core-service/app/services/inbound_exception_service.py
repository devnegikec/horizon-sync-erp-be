"""Controlled exception and hold/quarantine workflow for inbound receiving."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.inbound_exception import (
    InboundException,
    InboundExceptionEvent,
    InboundExceptionEvidence,
    InboundExceptionReason,
)
from app.models.item import Item
from app.models.receiving_slip import ReceivingSlip, ReceivingSlipItem
from app.models.scanned_item_tracking import ScannedItemTracking
from app.models.warehouse_user import WarehouseUser
from app.services.bin_stock_service import BinStockService
from app.services.scanned_item_tracking_service import ScannedItemTrackingService


class InboundExceptionService:
    """Owns exception lifecycle and physical non-pickable stock routing."""

    DESTINATIONS = {"HOLD", "QUARANTINE"}
    CLASSIFICATIONS = {"short", "damaged", "excess", "hold", "quarantine"}
    FINAL_DISPOSITIONS = {
        "release_to_receiving",
        "move_to_hold",
        "move_to_quarantine",
        "return_to_sender",
        "dispose",
    }

    def __init__(self, db: Session):
        self.db = db

    def assert_manager(self, user, warehouse_id: UUID) -> None:
        """Require a warehouse manager or an organization/system-level superior."""
        if (
            user.user_type in {"system_admin", "organization_admin"}
            or "*.*" in user.permissions
            or "warehouse.manage" in user.permissions
        ):
            return
        assignment = (
            self.db.query(WarehouseUser)
            .filter(
                WarehouseUser.organization_id == user.organization_id,
                WarehouseUser.user_id == user.id,
                WarehouseUser.warehouse_id == warehouse_id,
                WarehouseUser.is_active.is_(True),
                WarehouseUser.role == "manager",
            )
            .first()
        )
        if assignment is None:
            raise StateError(
                message="Warehouse Manager approval is required for this exception disposition",
                current_state="not_manager",
                required_state=["manager"],
            )

    def list_reasons(self, organization_id: UUID) -> list[InboundExceptionReason]:
        return (
            self.db.query(InboundExceptionReason)
            .filter(
                InboundExceptionReason.is_active.is_(True),
                (InboundExceptionReason.organization_id.is_(None))
                | (InboundExceptionReason.organization_id == organization_id),
            )
            .order_by(InboundExceptionReason.category, InboundExceptionReason.code)
            .all()
        )

    def list_exceptions(
        self,
        organization_id: UUID,
        *,
        warehouse_id: UUID | None = None,
        destination: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[InboundException], int]:
        query = self.db.query(InboundException).filter(
            InboundException.organization_id == organization_id
        )
        if warehouse_id:
            query = query.filter(InboundException.warehouse_id == warehouse_id)
        if destination:
            query = query.filter(InboundException.destination == destination.upper())
        if status:
            query = query.filter(InboundException.status == status)
        total = query.count()
        items = (
            query.order_by(InboundException.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def get_exception(
        self, exception_id: UUID, organization_id: UUID
    ) -> InboundException:
        exception = (
            self.db.query(InboundException)
            .filter(
                InboundException.id == exception_id,
                InboundException.organization_id == organization_id,
            )
            .first()
        )
        if exception is None:
            raise NotFoundError(
                "Inbound exception not found",
                entity_type="InboundException",
                entity_id=str(exception_id),
            )
        return exception

    def create_scan_exception(
        self,
        *,
        organization_id: UUID,
        warehouse_id: UUID,
        session_id: UUID,
        asn_order_id: UUID | None,
        exception_type: str,
        reason_code: str,
        qr_identifier: str,
        sku: str | None,
        batch_number: str | None,
        quantity: int,
        raw_qr_data: str,
        actor_id: UUID | None,
        item_id: UUID | None = None,
        scan_session_item_id: UUID | None = None,
        tracking_id: UUID | None = None,
    ) -> InboundException:
        self._validate_reason(reason_code, organization_id)
        exception = InboundException(
            organization_id=organization_id,
            warehouse_id=warehouse_id,
            asn_order_id=asn_order_id,
            session_id=session_id,
            scan_session_item_id=scan_session_item_id,
            tracking_id=tracking_id,
            item_id=item_id,
            exception_type=exception_type,
            reason_code=reason_code,
            status="pending_approval",
            condition_code="HOLD"
            if exception_type in {"unexpected_known_sku", "unknown_identity"}
            else "QUARANTINE",
            destination="HOLD"
            if exception_type in {"unexpected_known_sku", "unknown_identity"}
            else "QUARANTINE",
            qr_identifier=qr_identifier,
            sku=sku,
            batch_number=batch_number,
            quantity=quantity,
            raw_qr_data=raw_qr_data,
            created_by=actor_id,
        )
        self.db.add(exception)
        self.db.flush()
        self._event(
            exception, "detected", actor_id, {"source": "scan", "type": exception_type}
        )
        return exception

    def classify_slip_item(
        self,
        *,
        slip_id: UUID,
        slip_item_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        classification: str,
        reason_code: str,
        destination: str | None,
        note: str | None,
    ) -> InboundException:
        if classification not in self.CLASSIFICATIONS:
            raise ValidationError(
                f"Invalid inbound exception classification: {classification}"
            )
        slip = (
            self.db.query(ReceivingSlip)
            .filter(
                ReceivingSlip.id == slip_id,
                ReceivingSlip.organization_id == organization_id,
            )
            .first()
        )
        if slip is None:
            raise NotFoundError(
                "Receiving slip not found",
                entity_type="ReceivingSlip",
                entity_id=str(slip_id),
            )
        if slip.status != "pending_review":
            raise StateError(
                "Receiving slip must be pending review before classification",
                current_state=slip.status,
                required_state=["pending_review"],
            )
        line = (
            self.db.query(ReceivingSlipItem)
            .filter(
                ReceivingSlipItem.id == slip_item_id,
                ReceivingSlipItem.slip_id == slip_id,
                ReceivingSlipItem.organization_id == organization_id,
            )
            .first()
        )
        if line is None:
            raise NotFoundError(
                "Receiving slip item not found",
                entity_type="ReceivingSlipItem",
                entity_id=str(slip_item_id),
            )

        existing = (
            self.db.query(InboundException)
            .filter(
                InboundException.slip_item_id == line.id,
                InboundException.status.notin_(["closed", "released"]),
            )
            .first()
        )
        if existing is not None:
            raise StateError(
                "This receipt line already has an active inbound exception",
                current_state=existing.status,
                required_state=["closed", "released"],
            )

        self._validate_reason(reason_code, organization_id)
        normalized_destination = (destination or "").upper() or None
        if classification in {"damaged", "hold", "quarantine", "excess"}:
            if normalized_destination not in self.DESTINATIONS:
                raise ValidationError("Destination must be HOLD or QUARANTINE")

        item = self._resolve_item(organization_id, line.sku)
        tracking = self._tracking_for_line(slip, line)
        location = None
        if normalized_destination:
            location = self._system_location(
                slip.warehouse_id, organization_id, normalized_destination
            )

        exception = InboundException(
            organization_id=organization_id,
            warehouse_id=slip.warehouse_id,
            asn_order_id=slip.asn_order_id,
            session_id=slip.session_id,
            slip_id=slip.id,
            slip_item_id=line.id,
            tracking_id=tracking.id if tracking else None,
            item_id=item.id if item else None,
            exception_type=classification,
            reason_code=reason_code,
            status="pending_approval" if normalized_destination else "open",
            condition_code=(normalized_destination or "GOOD"),
            destination=normalized_destination,
            destination_location_id=location.id if location else None,
            qr_identifier=tracking.qr_identifier if tracking else line.batch_number,
            sku=line.sku,
            batch_number=line.batch_number,
            quantity=line.quantity,
            note=note,
            created_by=actor_id,
        )
        self.db.add(exception)
        line.flag = classification
        line.condition_code = normalized_destination or (
            "DAMAGED" if classification == "damaged" else "GOOD"
        )
        line.exception_status = exception.status
        line.exception_destination_location_id = location.id if location else None
        self.db.flush()

        # Physical stock is segregated as soon as the item is classified. It
        # remains non-pickable until an authorized manager disposes it.
        if location and item and tracking and not tracking.stock_entered:
            BinStockService(self.db).add_stock(
                location.id,
                item.id,
                Decimal(str(line.quantity)),
                organization_id,
                line.batch_number,
                commit=False,
            )
            tracking.stock_entered = True
            tracking.stock_entered_at = datetime.now(UTC)
            tracking.stock_location_id = location.id
            tracking.receiving_status = (
                "hold" if normalized_destination == "HOLD" else "quarantined"
            )
            tracking.putaway_status = "blocked"
        self._event(
            exception,
            "classified",
            actor_id,
            {"classification": classification, "destination": normalized_destination},
        )
        self.db.commit()
        self.db.refresh(exception)
        return exception

    def dispose(
        self,
        *,
        exception_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        action: str,
        note: str | None = None,
        item_id: UUID | None = None,
    ) -> InboundException:
        if action not in self.FINAL_DISPOSITIONS:
            raise ValidationError(f"Invalid exception disposition: {action}")
        exception = self.get_exception(exception_id, organization_id)
        if exception.status in {"closed", "released"}:
            raise StateError(
                "Exception is already resolved",
                current_state=exception.status,
                required_state=["pending_approval", "approved", "open"],
            )

        tracking = (
            self.db.get(ScannedItemTracking, exception.tracking_id)
            if exception.tracking_id
            else None
        )
        item = (
            self.db.get(Item, item_id)
            if item_id
            else (
                self.db.get(Item, exception.item_id)
                if exception.item_id
                else self._resolve_item(organization_id, exception.sku)
            )
        )
        if item is not None and (
            item.organization_id != organization_id or item.deleted_at is not None
        ):
            raise ValidationError("The selected SKU is not active in this organization")

        if action == "release_to_receiving":
            if item is None:
                raise ValidationError(
                    "A valid, active SKU must be added or selected before release to RECEIVING-STAGE"
                )
            if tracking is None:
                tracking = self._materialize_now_active_unknown(
                    exception, item, actor_id
                )
                exception.tracking_id = tracking.id
                exception.scan_session_item_id = tracking.scan_session_item_id
            stage = self._system_location(
                exception.warehouse_id, organization_id, "RECEIVING-STAGE"
            )
            self._move_or_enter(exception, tracking, item, stage.id)
            exception.status = "released"
            exception.destination = "RECEIVING-STAGE"
            exception.destination_location_id = stage.id
            exception.condition_code = "GOOD"
            if tracking:
                tracking.item_id = item.id
                tracking.sku = item.sku or item.item_code or exception.sku or ""
                tracking.receiving_status = "approved"
                tracking.putaway_status = "pending"
            self._update_line(
                exception, flag="ok", condition_code="GOOD", status="released"
            )
        elif action in {"move_to_hold", "move_to_quarantine"}:
            code = "HOLD" if action == "move_to_hold" else "QUARANTINE"
            destination = self._system_location(
                exception.warehouse_id, organization_id, code
            )
            if item is not None:
                self._move_or_enter(exception, tracking, item, destination.id)
            exception.status = "approved"
            exception.destination = code
            exception.destination_location_id = destination.id
            exception.condition_code = code
            if tracking:
                tracking.receiving_status = "hold" if code == "HOLD" else "quarantined"
                tracking.putaway_status = "blocked"
            self._update_line(
                exception,
                flag=code.lower(),
                condition_code=code,
                status="approved",
                destination_id=destination.id,
            )
        else:
            self._remove_segregated_stock(exception, tracking, item)
            exception.status = "closed"
            exception.destination = None
            if tracking:
                tracking.receiving_status = "rejected"
                tracking.putaway_status = "blocked"
            self._update_line(
                exception, flag="rejected", condition_code="REJECTED", status="closed"
            )

        exception.item_id = item.id if item else exception.item_id
        exception.disposition = action
        exception.disposition_note = note
        exception.disposed_by = actor_id
        exception.disposed_at = datetime.now(UTC)
        exception.approved_by = actor_id
        exception.approved_at = datetime.now(UTC)
        self._event(exception, "disposed", actor_id, {"action": action, "note": note})
        if action == "release_to_receiving" and exception.slip_item_id:
            from app.services.put_away_service import PutAwayService

            PutAwayService(self.db).enqueue_released_slip_item(
                exception.slip_item_id,
                organization_id,
            )
        else:
            self.db.commit()
        self.db.refresh(exception)
        return exception

    def dispose_many(
        self,
        *,
        exception_ids: list[UUID],
        organization_id: UUID,
        actor_id: UUID,
        action: str,
        note: str | None = None,
    ) -> dict:
        """Dispose many exceptions with the same action, isolating per-item failures."""
        if action not in self.FINAL_DISPOSITIONS:
            raise ValidationError(f"Invalid exception disposition: {action}")

        results: list[dict] = []
        succeeded: list[InboundException] = []
        for exception_id in exception_ids:
            try:
                exception = self.dispose(
                    exception_id=exception_id,
                    organization_id=organization_id,
                    actor_id=actor_id,
                    action=action,
                    note=note,
                )
                succeeded.append(exception)
                results.append(
                    {"id": str(exception_id), "status": "disposed", "error": None}
                )
            except Exception as err:  # noqa: BLE001 - isolate per-item failures
                self.db.rollback()
                message = getattr(err, "message", None) or str(err)
                results.append(
                    {"id": str(exception_id), "status": "failed", "error": message}
                )

        serialized_by_id = {d["id"]: d for d in self.serialize_many(succeeded)}
        for result in results:
            if result["status"] == "disposed":
                result["exception"] = serialized_by_id.get(result["id"])
            else:
                result["exception"] = None

        return {
            "results": results,
            "disposed_count": len(succeeded),
            "failed_count": len(results) - len(succeeded),
        }

    def add_evidence(
        self,
        *,
        exception_id: UUID,
        organization_id: UUID,
        actor_id: UUID,
        filename: str,
        content_type: str,
        data: bytes,
    ) -> InboundExceptionEvidence:
        if len(data) > 10 * 1024 * 1024:
            raise ValidationError("Evidence files must not exceed 10 MB")
        from app.services.storage_service import (
            INBOUND_EVIDENCE_CONTENT_TYPES,
            store_inbound_exception_evidence,
        )

        if content_type not in INBOUND_EVIDENCE_CONTENT_TYPES:
            raise ValidationError("Evidence must be a JPEG, PNG, WEBP, or PDF")
        exception = self.get_exception(exception_id, organization_id)
        key = store_inbound_exception_evidence(
            data, content_type, organization_id, exception.id
        )
        evidence = InboundExceptionEvidence(
            exception_id=exception.id,
            organization_id=organization_id,
            storage_key=key,
            original_filename=filename[:255],
            content_type=content_type,
            size_bytes=len(data),
            uploaded_by=actor_id,
        )
        self.db.add(evidence)
        self._event(
            exception,
            "evidence_uploaded",
            actor_id,
            {"filename": evidence.original_filename, "content_type": content_type},
        )
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def serialize(
        self,
        exception: InboundException,
        *,
        item_names_by_id: dict[UUID, str] | None = None,
        item_names_by_sku: dict[str, str] | None = None,
    ) -> dict:
        item_name = None
        if exception.item_id:
            if item_names_by_id is not None:
                item_name = item_names_by_id.get(exception.item_id)
            else:
                item = self.db.get(Item, exception.item_id)
                item_name = item.item_name if item else None
        elif exception.sku:
            if item_names_by_sku is not None:
                item_name = item_names_by_sku.get(exception.sku)
            else:
                item = self._resolve_item(exception.organization_id, exception.sku)
                item_name = item.item_name if item else None
        return {
            "id": str(exception.id),
            "warehouse_id": str(exception.warehouse_id),
            "slip_id": str(exception.slip_id) if exception.slip_id else None,
            "slip_item_id": str(exception.slip_item_id)
            if exception.slip_item_id
            else None,
            "exception_type": exception.exception_type,
            "reason_code": exception.reason_code,
            "status": exception.status,
            "condition_code": exception.condition_code,
            "destination": exception.destination,
            "destination_location_id": str(exception.destination_location_id)
            if exception.destination_location_id
            else None,
            "qr_identifier": exception.qr_identifier,
            "serial_number": exception.qr_identifier,
            "sku": exception.sku,
            "item_name": item_name,
            "batch_number": exception.batch_number,
            "quantity": exception.quantity,
            "note": exception.note,
            "disposition": exception.disposition,
            "disposition_note": exception.disposition_note,
            "created_at": exception.created_at.isoformat()
            if exception.created_at
            else None,
            "approved_at": exception.approved_at.isoformat()
            if exception.approved_at
            else None,
            "disposed_at": exception.disposed_at.isoformat()
            if exception.disposed_at
            else None,
            "evidence": [
                {
                    "id": str(e.id),
                    "filename": e.original_filename,
                    "content_type": e.content_type,
                    "size_bytes": e.size_bytes,
                }
                for e in exception.evidence
            ],
        }

    def serialize_many(self, exceptions: list[InboundException]) -> list[dict]:
        """Serialize exceptions with item lookups batched to avoid N+1 queries."""
        from sqlalchemy import or_

        item_names_by_id: dict[UUID, str] = {}
        item_names_by_sku: dict[str, str] = {}

        item_ids = {e.item_id for e in exceptions if e.item_id}
        skus = {e.sku for e in exceptions if e.sku and not e.item_id}

        if item_ids:
            items = self.db.query(Item).filter(Item.id.in_(item_ids)).all()
            item_names_by_id = {item.id: item.item_name for item in items}

        if skus:
            for org_id in {e.organization_id for e in exceptions}:
                items = (
                    self.db.query(Item)
                    .filter(
                        Item.organization_id == org_id,
                        Item.deleted_at.is_(None),
                        or_(
                            Item.sku.in_(skus),
                            Item.gtin.in_(skus),
                            Item.item_code.in_(skus),
                        ),
                    )
                    .all()
                )
                for item in items:
                    for key in (item.sku, item.gtin, item.item_code):
                        if key and key not in item_names_by_sku:
                            item_names_by_sku[key] = item.item_name

        return [
            self.serialize(
                exception,
                item_names_by_id=item_names_by_id,
                item_names_by_sku=item_names_by_sku,
            )
            for exception in exceptions
        ]

    def _validate_reason(self, code: str, organization_id: UUID) -> None:
        reason = (
            self.db.query(InboundExceptionReason)
            .filter(
                InboundExceptionReason.code == code,
                InboundExceptionReason.is_active.is_(True),
            )
            .first()
        )
        if reason is None or (
            reason.organization_id and reason.organization_id != organization_id
        ):
            raise ValidationError(
                f"Unknown or inactive inbound exception reason code: {code}"
            )

    def _resolve_item(self, organization_id: UUID, sku: str | None) -> Item | None:
        if not sku:
            return None
        from sqlalchemy import or_

        return (
            self.db.query(Item)
            .filter(
                Item.organization_id == organization_id,
                Item.deleted_at.is_(None),
                or_(Item.sku == sku, Item.gtin == sku, Item.item_code == sku),
            )
            .first()
        )

    def _tracking_for_line(
        self, slip: ReceivingSlip, line: ReceivingSlipItem
    ) -> ScannedItemTracking | None:
        return (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.scan_session_id == slip.session_id,
                ScannedItemTracking.qr_identifier == line.batch_number,
            )
            .first()
        )

    def _materialize_now_active_unknown(
        self,
        exception: InboundException,
        item: Item,
        actor_id: UUID,
    ) -> ScannedItemTracking:
        """Turn a hard-stopped unknown scan into a controlled receipt scan.

        The identity was intentionally not counted when it was unknown. Once a
        manager supplies an active SKU, it is registered exactly once on the
        still-open receiving session and then released into RECEIVING-STAGE.
        A closed session is never silently rewritten; the manager must create
        a new receipt flow in that case.
        """
        if exception.session_id is None:
            raise ValidationError(
                "This unknown identity has no receiving session. Create a new controlled receipt before release."
            )

        from app.models.scan_session import ScanSession, ScanSessionItem

        session = (
            self.db.query(ScanSession)
            .filter(
                ScanSession.id == exception.session_id,
                ScanSession.organization_id == exception.organization_id,
            )
            .first()
        )
        if session is None or session.status != "open":
            raise StateError(
                "The original receiving session is closed; begin a new controlled receipt for this now-known SKU.",
                current_state=session.status if session else "missing",
                required_state=["open"],
            )

        existing_tracking = (
            self.db.query(ScannedItemTracking)
            .filter(
                ScannedItemTracking.scan_session_id == session.id,
                ScannedItemTracking.qr_identifier == exception.qr_identifier,
            )
            .first()
        )
        if existing_tracking is not None:
            return existing_tracking

        scan_item = ScanSessionItem(
            organization_id=exception.organization_id,
            session_id=session.id,
            qr_identifier=exception.qr_identifier or str(exception.id),
            sku=item.sku or item.item_code or exception.sku or "",
            raw_quantity=exception.quantity,
            batch_number=exception.batch_number,
            raw_qr_data=exception.raw_qr_data,
        )
        self.db.add(scan_item)
        session.total_boxes_scanned = (session.total_boxes_scanned or 0) + 1
        self.db.flush()

        tracking = ScannedItemTracking(
            organization_id=exception.organization_id,
            warehouse_id=exception.warehouse_id,
            scan_session_id=session.id,
            scan_session_item_id=scan_item.id,
            qr_identifier=scan_item.qr_identifier,
            item_id=item.id,
            sku=item.sku or item.item_code or exception.sku or "",
            batch_number=exception.batch_number,
            quantity=exception.quantity,
            receiving_status="scanned",
            putaway_status="pending",
            stock_entered=False,
            scanned_by=actor_id,
        )
        self.db.add(tracking)
        self.db.flush()
        return tracking

    def _system_location(self, warehouse_id: UUID, organization_id: UUID, code: str):
        return ScannedItemTrackingService(self.db)._get_or_create_system_bin(
            warehouse_id, organization_id, code
        )

    def _move_or_enter(
        self, exception: InboundException, tracking, item: Item, destination_id: UUID
    ) -> None:
        stock = BinStockService(self.db)
        quantity = Decimal(str(exception.quantity))
        if tracking and tracking.stock_entered and tracking.stock_location_id:
            stock.transfer_stock(
                from_bin_id=tracking.stock_location_id,
                to_bin_id=destination_id,
                item_id=item.id,
                quantity=quantity,
                org_id=exception.organization_id,
                batch_number=exception.batch_number,
            )
        else:
            stock.add_stock(
                destination_id,
                item.id,
                quantity,
                exception.organization_id,
                exception.batch_number,
                commit=False,
            )
            if tracking:
                tracking.stock_entered = True
                tracking.stock_entered_at = datetime.now(UTC)
        if tracking:
            tracking.stock_location_id = destination_id

    def _remove_segregated_stock(
        self, exception: InboundException, tracking, item: Item | None
    ) -> None:
        if (
            not tracking
            or not tracking.stock_entered
            or not tracking.stock_location_id
            or not item
        ):
            return
        BinStockService(self.db).remove_stock(
            tracking.stock_location_id,
            item.id,
            Decimal(str(exception.quantity)),
            exception.organization_id,
            exception.batch_number,
            commit=False,
        )
        tracking.stock_entered = False
        tracking.stock_location_id = None

    def _update_line(
        self,
        exception: InboundException,
        *,
        flag: str,
        condition_code: str,
        status: str,
        destination_id: UUID | None = None,
    ) -> None:
        if not exception.slip_item_id:
            return
        line = self.db.get(ReceivingSlipItem, exception.slip_item_id)
        if line is None:
            return
        line.flag = flag
        line.condition_code = condition_code
        line.exception_status = status
        line.exception_destination_location_id = destination_id

    def _event(
        self,
        exception: InboundException,
        event_type: str,
        actor_id: UUID | None,
        details: dict | None = None,
    ) -> None:
        self.db.add(
            InboundExceptionEvent(
                exception_id=exception.id,
                organization_id=exception.organization_id,
                event_type=event_type,
                actor_id=actor_id,
                details=details,
            )
        )
