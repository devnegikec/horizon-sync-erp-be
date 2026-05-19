"""Gate verification service for outbound gate workflow.

Manages gate verification sessions where security personnel scan items
being loaded onto vehicles and validate them against a completed pick list.

Provides:
- start_session: Create a gate session linked to a completed pick list
- record_gate_scan: Validate scanned item against pick list (VERIFIED or UNAUTHORIZED)
- get_session_progress: Show scanned vs expected counts
- verify_session: Transition to VERIFIED when all items scanned

Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.7
"""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.base import PickListStatus
from app.models.gate_verification import GateVerificationItem, GateVerificationSession
from app.models.pick_list import PickList
from app.models.qr_scan_event import QRScanEvent
from app.services.qr_decoder import decode_qr_payload


class GateVerificationService:
    """Service for managing gate verification sessions and dispatch authorization."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # START SESSION
    # ------------------------------------------------------------------

    def start_session(
        self,
        pick_list_id: UUID,
        worker_id: UUID,
        org_id: UUID,
        vehicle_number: str | None = None,
        driver_name: str | None = None,
        driver_contact: str | None = None,
    ) -> dict:
        """Create a gate verification session linked to a completed pick list.

        Validates that the pick list exists, belongs to the organization,
        and is in COMPLETED status before creating the gate session.

        Args:
            pick_list_id: UUID of the completed pick list to verify against.
            worker_id: UUID of the security worker starting the session.
            org_id: Organization UUID for tenant isolation.
            vehicle_number: Optional vehicle registration number.
            driver_name: Optional driver name.
            driver_contact: Optional driver contact number.

        Returns:
            Dictionary representation of the created GateVerificationSession.

        Raises:
            NotFoundError: If pick list is not found.
            StateError: If pick list is not in COMPLETED status.

        Requirements: 12.1
        """
        # Validate pick list exists and belongs to the organization
        pick_list = (
            self.db.query(PickList)
            .filter(
                PickList.id == pick_list_id,
                PickList.organization_id == org_id,
            )
            .first()
        )

        if pick_list is None:
            raise NotFoundError(
                message="Pick list not found",
                entity_type="PickList",
                entity_id=str(pick_list_id),
            )

        # Validate pick list is in COMPLETED status
        if pick_list.status != PickListStatus.COMPLETED:
            raise StateError(
                message="Pick list must be in 'completed' status to start gate verification",
                current_state=pick_list.status.value,
                required_state=["completed"],
            )

        # Create the gate verification session
        gate_session = GateVerificationSession(
            organization_id=org_id,
            pick_list_id=pick_list_id,
            warehouse_id=pick_list.warehouse_id,
            worker_id=worker_id,
            vehicle_number=vehicle_number,
            driver_name=driver_name,
            driver_contact=driver_contact,
            status="open",
        )
        self.db.add(gate_session)
        self.db.commit()
        self.db.refresh(gate_session)

        return self._session_to_dict(gate_session)

    # ------------------------------------------------------------------
    # RECORD GATE SCAN
    # ------------------------------------------------------------------

    def record_gate_scan(
        self,
        session_id: UUID,
        qr_payload: str,
        worker_id: UUID,
        org_id: UUID,
        device_type: str | None = None,
        os: str | None = None,
    ) -> dict:
        """Record a QR scan at the gate and validate against the pick list.

        Decodes the QR payload, checks if the scanned item belongs to the
        associated pick list. If it matches, marks as VERIFIED; otherwise
        marks as UNAUTHORIZED.

        Args:
            session_id: UUID of the active gate verification session.
            qr_payload: Raw QR payload JSON string.
            worker_id: UUID of the security worker performing the scan.
            org_id: Organization UUID for tenant isolation.
            device_type: Optional device type info.
            os: Optional operating system info.

        Returns:
            Dictionary with scan result including verification status.

        Raises:
            NotFoundError: If gate session is not found.
            StateError: If gate session is not in OPEN status.
            ValidationError: If QR payload is invalid or duplicate scan detected.

        Requirements: 12.2, 12.3, 12.4
        """
        # Fetch and validate gate session
        gate_session = (
            self.db.query(GateVerificationSession)
            .filter(
                GateVerificationSession.id == session_id,
                GateVerificationSession.organization_id == org_id,
            )
            .first()
        )

        if gate_session is None:
            raise NotFoundError(
                message="Gate verification session not found",
                entity_type="GateVerificationSession",
                entity_id=str(session_id),
            )

        if gate_session.status != "open":
            raise StateError(
                message="Cannot record scan on a gate session that is not open",
                current_state=gate_session.status,
                required_state=["open"],
            )

        # Decode QR payload (raises ValidationError if invalid)
        payload = decode_qr_payload(qr_payload)

        # Check for duplicate scan within this session
        existing_item = (
            self.db.query(GateVerificationItem)
            .filter(
                GateVerificationItem.gate_session_id == session_id,
                GateVerificationItem.qr_identifier == payload.id,
            )
            .first()
        )

        if existing_item is not None:
            raise ValidationError(
                message="Duplicate scan: this item has already been scanned in this gate session",
                details=[
                    {
                        "field": "qr_identifier",
                        "reason": f"QR identifier '{payload.id}' already exists in gate session",
                    }
                ],
            )

        # Validate scanned item against the pick list
        pick_list = gate_session.pick_list
        item_status = self._validate_against_pick_list(payload, pick_list, org_id)

        # Create gate verification item
        gate_item = GateVerificationItem(
            organization_id=org_id,
            gate_session_id=session_id,
            qr_identifier=payload.id,
            sku=payload.sku,
            quantity=payload.qty,
            status=item_status,
            scanned_at=datetime.now(UTC),
        )
        self.db.add(gate_item)

        # Record scan event in qr_scan_events with gate context
        scan_event = QRScanEvent(
            organization_id=org_id,
            serial_number=payload.id,
            scan_timestamp=datetime.now(UTC),
            device_type=device_type,
            os=os,
            extra_data={
                "scan_context": "gate",
                "gate_session_id": str(session_id),
                "pick_list_id": str(gate_session.pick_list_id),
                "worker_id": str(worker_id),
                "verification_status": item_status,
                "decoded_payload": {
                    "id": payload.id,
                    "sku": payload.sku,
                    "qty": payload.qty,
                    "batch": payload.batch,
                },
            },
        )
        self.db.add(scan_event)

        self.db.commit()
        self.db.refresh(gate_item)

        return {
            "gate_item_id": str(gate_item.id),
            "gate_session_id": str(session_id),
            "qr_identifier": payload.id,
            "sku": payload.sku,
            "quantity": payload.qty,
            "batch": payload.batch,
            "status": item_status,
            "scanned_at": gate_item.scanned_at.isoformat()
            if gate_item.scanned_at
            else None,
        }

    # ------------------------------------------------------------------
    # GET SESSION PROGRESS
    # ------------------------------------------------------------------

    def get_session_progress(
        self,
        session_id: UUID,
        org_id: UUID,
    ) -> dict:
        """Get the progress of a gate verification session.

        Shows scanned items vs expected items from the pick list,
        including counts of verified and unauthorized items.

        Args:
            session_id: UUID of the gate verification session.
            org_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary with progress information including scanned vs expected counts.

        Raises:
            NotFoundError: If gate session is not found.

        Requirements: 12.7
        """
        gate_session = (
            self.db.query(GateVerificationSession)
            .filter(
                GateVerificationSession.id == session_id,
                GateVerificationSession.organization_id == org_id,
            )
            .first()
        )

        if gate_session is None:
            raise NotFoundError(
                message="Gate verification session not found",
                entity_type="GateVerificationSession",
                entity_id=str(session_id),
            )

        # Get all scanned items in this session
        scanned_items = (
            self.db.query(GateVerificationItem)
            .filter(GateVerificationItem.gate_session_id == session_id)
            .all()
        )

        # Count verified and unauthorized items
        verified_count = sum(1 for item in scanned_items if item.status == "verified")
        unauthorized_count = sum(
            1 for item in scanned_items if item.status == "unauthorized"
        )
        total_scanned = len(scanned_items)

        # Calculate verified quantity
        verified_qty = sum(
            item.quantity for item in scanned_items if item.status == "verified"
        )

        # Get expected total quantity from the pick list
        pick_list = gate_session.pick_list
        expected_total_qty = sum(
            float(Decimal(str(item.qty))) for item in pick_list.items
        )

        # Determine if all items are verified (verified qty >= expected qty)
        all_verified = verified_qty >= expected_total_qty and unauthorized_count == 0

        # Build scanned items breakdown
        scanned_breakdown = []
        for item in scanned_items:
            scanned_breakdown.append(
                {
                    "id": str(item.id),
                    "qr_identifier": item.qr_identifier,
                    "sku": item.sku,
                    "quantity": item.quantity,
                    "status": item.status,
                    "scanned_at": item.scanned_at.isoformat()
                    if item.scanned_at
                    else None,
                }
            )

        return {
            "session_id": str(gate_session.id),
            "pick_list_id": str(gate_session.pick_list_id),
            "status": gate_session.status,
            "vehicle_number": gate_session.vehicle_number,
            "driver_name": gate_session.driver_name,
            "expected_total_qty": expected_total_qty,
            "total_scanned": total_scanned,
            "verified_count": verified_count,
            "verified_qty": verified_qty,
            "unauthorized_count": unauthorized_count,
            "all_verified": all_verified,
            "scanned_items": scanned_breakdown,
        }

    # ------------------------------------------------------------------
    # VERIFY SESSION
    # ------------------------------------------------------------------

    def verify_session(
        self,
        session_id: UUID,
        org_id: UUID,
    ) -> dict:
        """Mark a gate verification session as VERIFIED and create a dispatch record.

        Validates that all expected items from the pick list have been
        scanned and verified, and that no unauthorized items are present,
        before transitioning the session status. Once verified, atomically
        creates a dispatch record via OutboundService which decrements
        warehouse stock levels and generates a unique dispatch number.

        All operations (session verification, dispatch record creation,
        stock deduction, dispatch number generation) happen within the
        same database transaction for atomicity.

        Args:
            session_id: UUID of the gate verification session to verify.
            org_id: Organization UUID for tenant isolation.

        Returns:
            Dictionary representation of the verified GateVerificationSession
            with an additional 'dispatch' key containing the dispatch record.

        Raises:
            NotFoundError: If gate session is not found.
            StateError: If gate session is not in OPEN status.
            ValidationError: If not all pick list items have been verified
                or unauthorized items are present.

        Requirements: 12.5, 12.6, 13.1, 13.4, 13.5
        """
        gate_session = (
            self.db.query(GateVerificationSession)
            .filter(
                GateVerificationSession.id == session_id,
                GateVerificationSession.organization_id == org_id,
            )
            .first()
        )

        if gate_session is None:
            raise NotFoundError(
                message="Gate verification session not found",
                entity_type="GateVerificationSession",
                entity_id=str(session_id),
            )

        if gate_session.status != "open":
            raise StateError(
                message="Gate session must be in 'open' status to verify",
                current_state=gate_session.status,
                required_state=["open"],
            )

        # Get all gate items for this session
        gate_items = (
            self.db.query(GateVerificationItem)
            .filter(GateVerificationItem.gate_session_id == session_id)
            .all()
        )

        # Check for unauthorized items
        unauthorized_items = [
            item for item in gate_items if item.status == "unauthorized"
        ]
        if unauthorized_items:
            raise ValidationError(
                message=(
                    f"Cannot verify session: {len(unauthorized_items)} unauthorized "
                    f"item(s) detected. All unauthorized items must be resolved "
                    f"before verification."
                ),
                details=[
                    {
                        "field": "unauthorized_items",
                        "reason": (
                            f"Found {len(unauthorized_items)} unauthorized item(s): "
                            + ", ".join(item.sku for item in unauthorized_items)
                        ),
                    }
                ],
            )

        # Check that all pick list items have been verified
        pick_list = gate_session.pick_list
        total_expected_qty = sum(Decimal(str(item.qty)) for item in pick_list.items)

        # Sum verified quantities from gate items
        verified_items = [item for item in gate_items if item.status == "verified"]
        total_verified_qty = sum(Decimal(str(item.quantity)) for item in verified_items)

        if total_verified_qty < total_expected_qty:
            raise ValidationError(
                message=(
                    f"Cannot verify session: verified quantity ({total_verified_qty}) "
                    f"is less than expected quantity ({total_expected_qty}). "
                    f"All pick list items must be scanned and verified."
                ),
                details=[
                    {
                        "field": "verified_qty",
                        "reason": (
                            f"Expected {total_expected_qty}, "
                            f"verified {total_verified_qty}"
                        ),
                    }
                ],
            )

        # Transition to VERIFIED and record departure timestamp
        gate_session.status = "verified"
        gate_session.verified_at = datetime.now(UTC)

        # Flush the status change so OutboundService sees it in the same session
        self.db.flush()

        # Create dispatch record atomically within the same transaction.
        # This decrements warehouse stock levels and generates a unique
        # dispatch number via the document numbering service.
        # Requirements: 12.6, 13.1, 13.4, 13.5
        from app.services.outbound_service import OutboundService

        outbound_service = OutboundService(self.db)
        dispatch_result = outbound_service.create_dispatch(session_id, org_id)

        # Refresh the gate session after the commit in create_dispatch
        self.db.refresh(gate_session)

        result = self._session_to_dict(gate_session)
        result["dispatch"] = dispatch_result
        return result

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _validate_against_pick_list(
        self,
        payload,
        pick_list: PickList,
        org_id: UUID,
    ) -> str:
        """Validate a scanned QR payload against the pick list items.

        Checks if the scanned SKU matches any item on the pick list.
        Returns 'verified' if it matches, 'unauthorized' if it doesn't.

        Args:
            payload: Decoded QRPayload with sku, qty, batch.
            pick_list: The PickList to validate against.
            org_id: Organization UUID for item lookup.

        Returns:
            'verified' if item belongs to pick list, 'unauthorized' otherwise.
        """
        from app.models.item import Item

        # Look up the item by SKU
        item = (
            self.db.query(Item)
            .filter(
                Item.item_code == payload.sku,
                Item.organization_id == org_id,
            )
            .first()
        )

        if item is None:
            return "unauthorized"

        # Check if this item is on the pick list
        for pick_item in pick_list.items:
            if pick_item.item_id == item.id:
                return "verified"

        return "unauthorized"

    def _session_to_dict(self, session: GateVerificationSession) -> dict:
        """Convert a GateVerificationSession model to a dictionary."""
        items = []
        if session.items:
            for item in session.items:
                items.append(
                    {
                        "id": str(item.id),
                        "qr_identifier": item.qr_identifier,
                        "sku": item.sku,
                        "quantity": item.quantity,
                        "status": item.status,
                        "scanned_at": item.scanned_at.isoformat()
                        if item.scanned_at
                        else None,
                    }
                )

        return {
            "id": str(session.id),
            "organization_id": str(session.organization_id),
            "pick_list_id": str(session.pick_list_id),
            "warehouse_id": str(session.warehouse_id),
            "worker_id": str(session.worker_id),
            "vehicle_number": session.vehicle_number,
            "driver_name": session.driver_name,
            "driver_contact": session.driver_contact,
            "status": session.status,
            "verified_at": session.verified_at.isoformat()
            if session.verified_at
            else None,
            "items": items,
            "created_at": session.created_at.isoformat()
            if session.created_at
            else None,
            "updated_at": session.updated_at.isoformat()
            if session.updated_at
            else None,
        }
