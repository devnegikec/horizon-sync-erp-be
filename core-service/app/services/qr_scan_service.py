"""QR Scan Service for location-based time tracking.

Records start/finish QR scans at physical bin locations to measure
how long workers spend at each location during put-away and pick tasks.

Provides:
- record_location_scan: Record a start or finish scan at a location
- get_time_summary: Retrieve aggregated time tracking data with filters

Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6
"""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, ValidationError
from app.models.location_scan import LocationScan
from app.models.worker_task import WorkerTask


class QRScanService:
    """Service for recording QR location scans and computing time tracking summaries."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # RECORD LOCATION SCAN
    # ------------------------------------------------------------------

    def record_location_scan(
        self,
        worker_id: UUID,
        task_id: UUID,
        location_code: str,
        scan_type: str,
        org_id: UUID,
        scanned_at: datetime | None = None,
    ) -> dict:
        """Record a start or finish QR scan at a physical location.

        On a 'start' scan, creates a new LocationScan record with the
        scan timestamp. On a 'finish' scan, validates that a preceding
        start scan exists for the same worker_task_id and location_code,
        then calculates elapsed_seconds as the difference between the
        finish and start timestamps.

        Args:
            worker_id: UUID of the worker performing the scan.
            task_id: UUID of the worker_task this scan belongs to.
            location_code: The location code being scanned (e.g., Z01-A03-B02-L04-B01).
            scan_type: Either 'start' or 'finish'.
            org_id: Organization UUID for tenant isolation.
            scanned_at: Optional explicit scan timestamp (defaults to now).

        Returns:
            Dictionary representation of the created LocationScan.

        Raises:
            NotFoundError: If the worker task is not found.
            ValidationError: If scan_type is invalid, or a finish scan
                is recorded without a preceding start scan.

        Requirements: 17.1, 17.2, 17.3, 17.4
        """
        # Validate scan_type
        if scan_type not in ("start", "finish"):
            raise ValidationError(
                message=f"Invalid scan_type '{scan_type}'. Must be 'start' or 'finish'.",
                details=[
                    {
                        "field": "scan_type",
                        "reason": "scan_type must be 'start' or 'finish'",
                    }
                ],
            )

        # Validate worker task exists and belongs to the organization
        worker_task = (
            self.db.query(WorkerTask)
            .filter(
                WorkerTask.id == task_id,
                WorkerTask.organization_id == org_id,
            )
            .first()
        )

        if worker_task is None:
            raise NotFoundError(
                message="Worker task not found",
                entity_type="WorkerTask",
                entity_id=str(task_id),
            )

        # Use provided timestamp or current time
        scan_timestamp = scanned_at or datetime.now(UTC)
        elapsed_seconds = None

        # On finish scan: validate preceding start scan exists and calculate elapsed
        if scan_type == "finish":
            # Find the most recent start scan for the same task and location
            start_scan = (
                self.db.query(LocationScan)
                .filter(
                    LocationScan.worker_task_id == task_id,
                    LocationScan.location_code == location_code,
                    LocationScan.scan_type == "start",
                )
                .order_by(LocationScan.scanned_at.desc())
                .first()
            )

            if start_scan is None:
                raise ValidationError(
                    message=(
                        f"Cannot record finish scan: no preceding start scan found "
                        f"for task '{task_id}' at location '{location_code}'"
                    ),
                    details=[
                        {
                            "field": "scan_type",
                            "reason": (
                                "A 'start' scan must be recorded before a 'finish' scan "
                                "for the same task and location"
                            ),
                        }
                    ],
                )

            # Calculate elapsed seconds between start and finish
            # Handle timezone-aware vs naive datetime comparison
            start_time = start_scan.scanned_at
            if start_time.tzinfo is None and scan_timestamp.tzinfo is not None:
                start_time = start_time.replace(tzinfo=UTC)
            elif start_time.tzinfo is not None and scan_timestamp.tzinfo is None:
                scan_timestamp = scan_timestamp.replace(tzinfo=UTC)

            elapsed_seconds = int((scan_timestamp - start_time).total_seconds())

        # Create the location scan record
        location_scan = LocationScan(
            organization_id=org_id,
            worker_task_id=task_id,
            location_code=location_code,
            scan_type=scan_type,
            scanned_at=scan_timestamp,
            elapsed_seconds=elapsed_seconds,
        )
        self.db.add(location_scan)
        self.db.commit()
        self.db.refresh(location_scan)

        return self._scan_to_dict(location_scan)

    # ------------------------------------------------------------------
    # GET TIME SUMMARY
    # ------------------------------------------------------------------

    def get_time_summary(
        self,
        org_id: UUID,
        worker_id: UUID | None = None,
        task_id: UUID | None = None,
        location_code: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> dict:
        """Retrieve time tracking summaries with optional filters.

        Aggregates elapsed_seconds from finish scans, grouped by worker,
        task, and location. Supports filtering by worker_id, task_id,
        location_code, and date range.

        Args:
            org_id: Organization UUID for tenant isolation.
            worker_id: Optional filter by worker UUID.
            task_id: Optional filter by worker_task UUID.
            location_code: Optional filter by location code.
            date_from: Optional start date for the date range filter.
            date_to: Optional end date for the date range filter.

        Returns:
            Dictionary with summary statistics and detailed records.

        Requirements: 17.6
        """
        # Build base query for finish scans (only finish scans have elapsed_seconds)
        query = (
            self.db.query(LocationScan)
            .join(WorkerTask, LocationScan.worker_task_id == WorkerTask.id)
            .filter(
                LocationScan.organization_id == org_id,
                LocationScan.scan_type == "finish",
                LocationScan.elapsed_seconds.isnot(None),
            )
        )

        # Apply optional filters
        if worker_id is not None:
            query = query.filter(WorkerTask.worker_id == worker_id)

        if task_id is not None:
            query = query.filter(LocationScan.worker_task_id == task_id)

        if location_code is not None:
            query = query.filter(LocationScan.location_code == location_code)

        if date_from is not None:
            query = query.filter(
                LocationScan.scanned_at
                >= datetime.combine(date_from, datetime.min.time()).replace(tzinfo=UTC)
            )

        if date_to is not None:
            query = query.filter(
                LocationScan.scanned_at
                <= datetime.combine(date_to, datetime.max.time()).replace(tzinfo=UTC)
            )

        # Get all matching finish scans
        finish_scans = query.all()

        # Compute aggregated statistics
        total_elapsed = sum(scan.elapsed_seconds for scan in finish_scans)
        scan_count = len(finish_scans)
        avg_elapsed = total_elapsed / scan_count if scan_count > 0 else 0

        # Group by location
        location_summary: dict[str, dict] = {}
        for scan in finish_scans:
            loc = scan.location_code
            if loc not in location_summary:
                location_summary[loc] = {
                    "location_code": loc,
                    "total_elapsed_seconds": 0,
                    "scan_count": 0,
                }
            location_summary[loc]["total_elapsed_seconds"] += scan.elapsed_seconds
            location_summary[loc]["scan_count"] += 1

        # Calculate average per location
        for loc_data in location_summary.values():
            loc_data["avg_elapsed_seconds"] = (
                loc_data["total_elapsed_seconds"] / loc_data["scan_count"]
                if loc_data["scan_count"] > 0
                else 0
            )

        # Build detailed records
        records = [self._scan_to_dict(scan) for scan in finish_scans]

        return {
            "total_elapsed_seconds": total_elapsed,
            "total_scans": scan_count,
            "avg_elapsed_seconds": round(avg_elapsed, 2),
            "by_location": list(location_summary.values()),
            "records": records,
        }

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _scan_to_dict(self, scan: LocationScan) -> dict:
        """Convert a LocationScan model to a dictionary."""
        return {
            "id": str(scan.id),
            "organization_id": str(scan.organization_id),
            "worker_task_id": str(scan.worker_task_id),
            "location_code": scan.location_code,
            "scan_type": scan.scan_type,
            "scanned_at": scan.scanned_at.isoformat() if scan.scanned_at else None,
            "elapsed_seconds": scan.elapsed_seconds,
            "created_at": scan.created_at.isoformat() if scan.created_at else None,
        }
