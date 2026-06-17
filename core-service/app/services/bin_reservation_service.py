"""Bin reservation service for concurrent worker coordination.

Prevents two workers from being directed to the same bin at the same time by
maintaining at most one active (un-released) reservation per bin. Time-to-live
(TTL) expiry is enforced here rather than in the database because NOW() is not
immutable and cannot be used in a partial-index predicate.

Key operations:
- reserve: atomically claim a bin (row-locks the bin to win races)
- release: a worker voluntarily gives up a bin
- force_release: a manager clears any reservation
- cleanup_expired: background sweep that releases timed-out reservations
- get_active_reservations / is_reserved / get_reserved_bin_ids: read helpers

Design ref: docs/3D_WAREHOUSE_VIEW_DESIGN.md sections 3.3, 8.1, 8.2
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.config import settings
from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.bin_reservation import BinReservation
from app.models.warehouse_location import WarehouseLocation
from app.models.worker_task import WorkerTask

DEFAULT_TTL_SECONDS: int = settings.bin_reservation_ttl_seconds  # default 300 s (FR-CW-02)


class BinReservationService:
    """Service for reserving, releasing, and inspecting bin reservations."""

    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # WRITE OPERATIONS
    # ------------------------------------------------------------------

    def reserve(
        self,
        bin_id: UUID,
        worker_id: UUID,
        org_id: UUID,
        task_id: UUID | None = None,
        task_type: str | None = None,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> BinReservation:
        """Atomically reserve a bin for a worker.

        Locks the bin's warehouse_locations row (``SELECT ... FOR UPDATE``) so
        that two simultaneous reservation attempts are serialized — only one
        succeeds, the other receives a StateError (handled upstream by offering
        the next-best bin). Expired reservations are auto-released inline.

        Args:
            bin_id: The bin location to reserve.
            worker_id: The worker claiming the bin.
            org_id: Organization scope.
            task_id: Optional originating worker_task id.
            task_type: 'put_away' or 'pick'.
            ttl_seconds: Reservation lifetime; clamped to a sane minimum.

        Returns:
            The active BinReservation owned by ``worker_id``.

        Raises:
            ValidationError: If ttl is non-positive or task_type is invalid.
            NotFoundError: If the bin does not exist for the org.
            StateError: If the bin is actively reserved by another worker.
        """
        if ttl_seconds <= 0:
            raise ValidationError("ttl_seconds must be positive")
        if task_type is not None and task_type not in ("put_away", "pick"):
            raise ValidationError("task_type must be 'put_away' or 'pick'")

        # Lock the bin row to serialize concurrent reservation attempts.
        bin_location = (
            self.db.query(WarehouseLocation)
            .filter(
                WarehouseLocation.id == bin_id,
                WarehouseLocation.organization_id == org_id,
            )
            .with_for_update()
            .first()
        )
        if bin_location is None:
            raise NotFoundError(
                message="Bin location not found",
                entity_type="WarehouseLocation",
                entity_id=str(bin_id),
            )
        if not bin_location.is_active:
            raise StateError(
                message=f"Bin '{bin_location.full_path}' is deactivated",
                current_state="inactive",
                required_state=["active"],
            )

        now = datetime.now(UTC)

        # Inspect the current active reservation (if any).
        active = (
            self.db.query(BinReservation)
            .filter(
                BinReservation.bin_location_id == bin_id,
                BinReservation.released_at.is_(None),
            )
            .first()
        )

        if active is not None:
            if self._is_expired(active, now):
                # Auto-release the timed-out reservation inline.
                active.released_at = now
                self.db.flush()
            elif active.worker_id == worker_id:
                # Same worker re-reserving: extend the TTL (idempotent).
                active.expires_at = now + timedelta(seconds=ttl_seconds)
                if task_id is not None:
                    active.task_id = task_id
                if task_type is not None:
                    active.task_type = task_type
                self.db.commit()
                self.db.refresh(active)
                return active
            else:
                raise StateError(
                    message=(
                        f"Bin '{bin_location.full_path}' is already reserved "
                        f"by another worker"
                    ),
                    current_state="reserved",
                    required_state=["available"],
                )

        reservation = BinReservation(
            organization_id=org_id,
            bin_location_id=bin_id,
            worker_id=worker_id,
            task_id=task_id,
            task_type=task_type,
            reserved_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )
        self.db.add(reservation)
        self.db.commit()
        self.db.refresh(reservation)
        return reservation

    def release(self, bin_id: UUID, worker_id: UUID, org_id: UUID) -> bool:
        """Release the active reservation a worker holds on a bin.

        Returns True if a reservation was released, False if the worker held no
        active reservation on the bin.
        """
        active = (
            self.db.query(BinReservation)
            .filter(
                BinReservation.bin_location_id == bin_id,
                BinReservation.organization_id == org_id,
                BinReservation.worker_id == worker_id,
                BinReservation.released_at.is_(None),
            )
            .first()
        )
        if active is None:
            return False

        active.released_at = datetime.now(UTC)
        self.db.commit()
        return True

    def release_for_worker(self, worker_id: UUID, org_id: UUID) -> int:
        """Release all active reservations held by a worker. Returns count."""
        now = datetime.now(UTC)
        actives = (
            self.db.query(BinReservation)
            .filter(
                BinReservation.organization_id == org_id,
                BinReservation.worker_id == worker_id,
                BinReservation.released_at.is_(None),
            )
            .all()
        )
        for r in actives:
            r.released_at = now
        if actives:
            self.db.commit()
        return len(actives)

    def force_release(self, bin_id: UUID, org_id: UUID) -> bool:
        """Manager override — release any active reservation on a bin (FR-CW-04)."""
        active = (
            self.db.query(BinReservation)
            .filter(
                BinReservation.bin_location_id == bin_id,
                BinReservation.organization_id == org_id,
                BinReservation.released_at.is_(None),
            )
            .first()
        )
        if active is None:
            return False

        active.released_at = datetime.now(UTC)
        self.db.commit()
        return True

    def cleanup_expired(self, org_id: UUID | None = None) -> int:
        """Release reservations whose TTL has elapsed. Returns count released.

        Edge case (§13): if a reservation has an associated task_id whose
        status is still 'in_progress', auto-extend the TTL by DEFAULT_TTL_SECONDS
        instead of releasing — the worker is still actively working.

        Intended to be run periodically (e.g. every 60s) by a background task.
        """
        now = datetime.now(UTC)
        query = self.db.query(BinReservation).filter(
            BinReservation.released_at.is_(None),
            BinReservation.expires_at <= now,
        )
        if org_id is not None:
            query = query.filter(BinReservation.organization_id == org_id)

        expired = query.all()
        released_count = 0
        for r in expired:
            if r.task_id is not None:
                task = (
                    self.db.query(WorkerTask)
                    .filter(WorkerTask.id == r.task_id)
                    .first()
                )
                if task is not None and task.status == "in_progress":
                    r.expires_at = now + timedelta(seconds=DEFAULT_TTL_SECONDS)
                    continue
            r.released_at = now
            released_count += 1
        if expired:
            self.db.commit()
        return released_count

    # ------------------------------------------------------------------
    # READ OPERATIONS
    # ------------------------------------------------------------------

    def is_reserved(self, bin_id: UUID, org_id: UUID) -> bool:
        """Return True if the bin has an active, non-expired reservation."""
        return self.get_active_reservation(bin_id, org_id) is not None

    def get_active_reservation(
        self, bin_id: UUID, org_id: UUID
    ) -> BinReservation | None:
        """Return the active, non-expired reservation for a bin, if any."""
        now = datetime.now(UTC)
        return (
            self.db.query(BinReservation)
            .filter(
                BinReservation.bin_location_id == bin_id,
                BinReservation.organization_id == org_id,
                BinReservation.released_at.is_(None),
                BinReservation.expires_at > now,
            )
            .first()
        )

    def get_active_reservations(
        self, org_id: UUID, warehouse_id: UUID | None = None
    ) -> list[BinReservation]:
        """Return all active, non-expired reservations for an org/warehouse."""
        now = datetime.now(UTC)
        query = self.db.query(BinReservation).filter(
            BinReservation.organization_id == org_id,
            BinReservation.released_at.is_(None),
            BinReservation.expires_at > now,
        )
        if warehouse_id is not None:
            query = query.join(
                WarehouseLocation,
                and_(
                    BinReservation.bin_location_id == WarehouseLocation.id,
                    WarehouseLocation.warehouse_id == warehouse_id,
                ),
            )
        return query.all()

    def get_reserved_bin_ids(
        self,
        org_id: UUID,
        warehouse_id: UUID | None = None,
        exclude_worker_id: UUID | None = None,
    ) -> set[UUID]:
        """Return the set of bin ids with an active reservation.

        ``exclude_worker_id`` omits bins the given worker already holds, so a
        worker's own reservations are not treated as obstacles to themselves.
        """
        reservations = self.get_active_reservations(org_id, warehouse_id)
        return {
            r.bin_location_id
            for r in reservations
            if exclude_worker_id is None or r.worker_id != exclude_worker_id
        }

    # ------------------------------------------------------------------
    # INTERNAL
    # ------------------------------------------------------------------

    @staticmethod
    def _is_expired(reservation: BinReservation, now: datetime) -> bool:
        expires_at = reservation.expires_at
        if expires_at is None:
            return True
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        return expires_at <= now
