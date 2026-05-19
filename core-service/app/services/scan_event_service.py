"""Scan Event Service for unified QR scan event recording and querying.

Provides a centralized service for recording scan events across all contexts
(inbound, pick, gate) into the existing qr_scan_events table, and querying
them with filters for audit trail purposes.

Provides:
- record_event: Store a scan event with full context in extra_data
- query_events: Query scan events with filters (session_id, worker_id, date range, scan_context)

Requirements: 14.1, 14.2, 14.3, 14.4
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.qr_scan_event import QRScanEvent


# Valid scan contexts
VALID_SCAN_CONTEXTS = ("inbound", "pick", "gate")


class ScanEventService:
    """Service for recording and querying QR scan events across all warehouse contexts."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # RECORD EVENT
    # ------------------------------------------------------------------

    def record_event(
        self,
        organization_id: UUID,
        worker_id: UUID,
        scan_context: str,
        serial_number: str | None = None,
        session_id: UUID | None = None,
        pick_list_id: UUID | None = None,
        decoded_payload: dict | None = None,
        device_type: str | None = None,
        os: str | None = None,
        product_item_id: UUID | None = None,
        ip_address: str | None = None,
        latitude: float | None = None,
        longitude: float | None = None,
        city: str | None = None,
        state: str | None = None,
        country: str | None = None,
    ) -> dict:
        """Record a scan event in the qr_scan_events table with full context.

        Stores the scan event with context information in the extra_data JSONB
        field, including scan_context, session_id, pick_list_id, decoded_payload,
        device_type, and os.

        Args:
            organization_id: Organization UUID for tenant isolation.
            worker_id: UUID of the worker performing the scan.
            scan_context: Context of the scan ('inbound', 'pick', or 'gate').
            serial_number: Serial number or QR identifier of the scanned item.
            session_id: Optional session ID (inbound or gate session).
            pick_list_id: Optional pick list ID (for pick or gate context).
            decoded_payload: Optional decoded QR payload data.
            device_type: Optional device type (e.g., 'mobile', 'tablet').
            os: Optional operating system info.
            product_item_id: Optional product item ID reference.
            ip_address: Optional IP address of the scanning device.
            latitude: Optional GPS latitude.
            longitude: Optional GPS longitude.
            city: Optional city from geo-resolution.
            state: Optional state from geo-resolution.
            country: Optional country from geo-resolution.

        Returns:
            Dictionary with the created scan event details.

        Raises:
            ValidationError: If scan_context is invalid.

        Requirements: 14.1, 14.2, 14.4
        """
        # Validate scan_context
        if scan_context not in VALID_SCAN_CONTEXTS:
            raise ValidationError(
                message=f"Invalid scan_context '{scan_context}'. Must be one of: {', '.join(VALID_SCAN_CONTEXTS)}",
                details=[
                    {
                        "field": "scan_context",
                        "reason": f"Must be one of: {', '.join(VALID_SCAN_CONTEXTS)}",
                    }
                ],
            )

        # Build extra_data with full context
        extra_data = {
            "scan_context": scan_context,
            "worker_id": str(worker_id),
        }

        if session_id is not None:
            extra_data["session_id"] = str(session_id)

        if pick_list_id is not None:
            extra_data["pick_list_id"] = str(pick_list_id)

        if decoded_payload is not None:
            extra_data["decoded_payload"] = decoded_payload

        if device_type is not None:
            extra_data["device_type"] = device_type

        if os is not None:
            extra_data["os"] = os

        # Create the scan event record
        scan_event = QRScanEvent(
            organization_id=organization_id,
            product_item_id=product_item_id,
            serial_number=serial_number,
            scan_timestamp=datetime.now(UTC),
            device_type=device_type,
            os=os,
            ip_address=ip_address,
            latitude=latitude,
            longitude=longitude,
            city=city,
            state=state,
            country=country,
            extra_data=extra_data,
        )

        self.db.add(scan_event)
        self.db.commit()
        self.db.refresh(scan_event)

        return self._event_to_dict(scan_event)

    # ------------------------------------------------------------------
    # QUERY EVENTS
    # ------------------------------------------------------------------

    def query_events(
        self,
        organization_id: UUID,
        session_id: UUID | None = None,
        worker_id: UUID | None = None,
        scan_context: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        serial_number: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """Query scan events with filters for audit trail.

        Supports filtering by session_id, worker_id, date range, and
        scan_context. Results are paginated and ordered by scan_timestamp
        descending (most recent first).

        Args:
            organization_id: Organization UUID for tenant isolation.
            session_id: Optional filter by session ID (stored in extra_data).
            worker_id: Optional filter by worker ID (stored in extra_data).
            scan_context: Optional filter by scan context ('inbound', 'pick', 'gate').
            date_from: Optional start date filter (inclusive).
            date_to: Optional end date filter (inclusive).
            serial_number: Optional filter by serial number.
            page: Page number (1-indexed).
            page_size: Number of items per page.

        Returns:
            Dictionary with scan events list and pagination info.

        Raises:
            ValidationError: If scan_context filter is invalid.

        Requirements: 14.3
        """
        # Validate scan_context filter if provided
        if scan_context and scan_context not in VALID_SCAN_CONTEXTS:
            raise ValidationError(
                message=f"Invalid scan_context filter '{scan_context}'. Must be one of: {', '.join(VALID_SCAN_CONTEXTS)}",
                details=[
                    {
                        "field": "scan_context",
                        "reason": f"Must be one of: {', '.join(VALID_SCAN_CONTEXTS)}",
                    }
                ],
            )

        # Build query filters
        filters = [
            QRScanEvent.organization_id == organization_id,
        ]

        # Filter by scan_context using JSON extraction
        # json_extract works with both SQLite and PostgreSQL (via sqlalchemy)
        if scan_context:
            filters.append(
                func.json_extract(QRScanEvent.extra_data, "$.scan_context") == scan_context
            )

        # Filter by session_id using JSON extraction
        if session_id:
            filters.append(
                func.json_extract(QRScanEvent.extra_data, "$.session_id") == str(session_id)
            )

        # Filter by worker_id using JSON extraction
        if worker_id:
            filters.append(
                func.json_extract(QRScanEvent.extra_data, "$.worker_id") == str(worker_id)
            )

        # Filter by date range
        if date_from:
            filters.append(QRScanEvent.scan_timestamp >= date_from)

        if date_to:
            filters.append(QRScanEvent.scan_timestamp <= date_to)

        # Filter by serial_number
        if serial_number:
            filters.append(QRScanEvent.serial_number == serial_number)

        # Get total count
        total_items = self.db.query(QRScanEvent).filter(and_(*filters)).count()

        # Calculate pagination
        total_pages = max(1, (total_items + page_size - 1) // page_size)
        offset = (page - 1) * page_size

        # Fetch events with pagination, ordered by most recent first
        events = (
            self.db.query(QRScanEvent)
            .filter(and_(*filters))
            .order_by(QRScanEvent.scan_timestamp.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )

        return {
            "scan_events": [self._event_to_dict(event) for event in events],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total_items,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1,
            },
        }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _event_to_dict(self, event: QRScanEvent) -> dict:
        """Convert a QRScanEvent model instance to a dictionary.

        Args:
            event: The QRScanEvent model instance.

        Returns:
            Dictionary representation of the scan event.
        """
        return {
            "id": str(event.id),
            "organization_id": str(event.organization_id),
            "product_item_id": str(event.product_item_id) if event.product_item_id else None,
            "serial_number": event.serial_number,
            "scan_timestamp": event.scan_timestamp.isoformat() if event.scan_timestamp else None,
            "device_type": event.device_type,
            "os": event.os,
            "browser": event.browser,
            "ip_address": event.ip_address,
            "latitude": float(event.latitude) if event.latitude is not None else None,
            "longitude": float(event.longitude) if event.longitude is not None else None,
            "city": event.city,
            "state": event.state,
            "country": event.country,
            "extra_data": event.extra_data,
        }
