"""Unit tests for BinReservationService (concurrent worker coordination)."""

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from app.core.exceptions import NotFoundError, StateError, ValidationError
from app.models.bin_reservation import BinReservation
from app.models.warehouse_location import WarehouseLocation
from app.services.bin_reservation_service import BinReservationService


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def warehouse_id():
    return uuid.uuid4()


@pytest.fixture
def service(db_session):
    return BinReservationService(db_session)


def _create_bin(db_session, org_id, warehouse_id, code="BIN01", is_active=True):
    loc = WarehouseLocation(
        id=uuid.uuid4(),
        organization_id=org_id,
        warehouse_id=warehouse_id,
        location_type="bin",
        code=code,
        full_path=code,
        capacity=Decimal("100"),
        is_active=is_active,
        version=1,
    )
    db_session.add(loc)
    db_session.commit()
    return loc


class TestReserve:
    def test_reserve_creates_active_reservation(
        self, db_session, service, org_id, warehouse_id
    ):
        b = _create_bin(db_session, org_id, warehouse_id)
        worker = uuid.uuid4()

        res = service.reserve(bin_id=b.id, worker_id=worker, org_id=org_id)

        assert res.bin_location_id == b.id
        assert res.worker_id == worker
        assert res.released_at is None
        assert service.is_reserved(b.id, org_id) is True

    def test_reserve_unknown_bin_raises_not_found(self, service, org_id):
        with pytest.raises(NotFoundError):
            service.reserve(bin_id=uuid.uuid4(), worker_id=uuid.uuid4(), org_id=org_id)

    def test_reserve_inactive_bin_raises_state_error(
        self, db_session, service, org_id, warehouse_id
    ):
        b = _create_bin(db_session, org_id, warehouse_id, is_active=False)
        with pytest.raises(StateError):
            service.reserve(bin_id=b.id, worker_id=uuid.uuid4(), org_id=org_id)

    def test_reserve_invalid_ttl_raises(
        self, db_session, service, org_id, warehouse_id
    ):
        b = _create_bin(db_session, org_id, warehouse_id)
        with pytest.raises(ValidationError):
            service.reserve(
                bin_id=b.id, worker_id=uuid.uuid4(), org_id=org_id, ttl_seconds=0
            )

    def test_reserve_conflict_other_worker_raises(
        self, db_session, service, org_id, warehouse_id
    ):
        b = _create_bin(db_session, org_id, warehouse_id)
        service.reserve(bin_id=b.id, worker_id=uuid.uuid4(), org_id=org_id)

        with pytest.raises(StateError):
            service.reserve(bin_id=b.id, worker_id=uuid.uuid4(), org_id=org_id)

    def test_reserve_same_worker_extends_ttl(
        self, db_session, service, org_id, warehouse_id
    ):
        b = _create_bin(db_session, org_id, warehouse_id)
        worker = uuid.uuid4()
        first = service.reserve(
            bin_id=b.id, worker_id=worker, org_id=org_id, ttl_seconds=60
        )
        first_expiry = first.expires_at

        second = service.reserve(
            bin_id=b.id, worker_id=worker, org_id=org_id, ttl_seconds=600
        )

        assert second.id == first.id
        assert second.expires_at >= first_expiry

    def test_reserve_invalid_task_type_raises(
        self, db_session, service, org_id, warehouse_id
    ):
        b = _create_bin(db_session, org_id, warehouse_id)
        with pytest.raises(ValidationError):
            service.reserve(
                bin_id=b.id,
                worker_id=uuid.uuid4(),
                org_id=org_id,
                task_type="invalid",
            )

    def test_expired_reservation_auto_released_on_reserve(
        self, db_session, service, org_id, warehouse_id
    ):
        b = _create_bin(db_session, org_id, warehouse_id)
        worker_a = uuid.uuid4()
        worker_b = uuid.uuid4()

        # Insert an already-expired reservation for worker A.
        expired = BinReservation(
            id=uuid.uuid4(),
            organization_id=org_id,
            bin_location_id=b.id,
            worker_id=worker_a,
            reserved_at=datetime.now(UTC) - timedelta(minutes=10),
            expires_at=datetime.now(UTC) - timedelta(minutes=5),
        )
        db_session.add(expired)
        db_session.commit()

        # Worker B can now claim the bin; the expired one is auto-released.
        res = service.reserve(bin_id=b.id, worker_id=worker_b, org_id=org_id)
        assert res.worker_id == worker_b
        db_session.refresh(expired)
        assert expired.released_at is not None


class TestRelease:
    def test_release_frees_bin(self, db_session, service, org_id, warehouse_id):
        b = _create_bin(db_session, org_id, warehouse_id)
        worker_a = uuid.uuid4()
        worker_b = uuid.uuid4()
        service.reserve(bin_id=b.id, worker_id=worker_a, org_id=org_id)

        released = service.release(bin_id=b.id, worker_id=worker_a, org_id=org_id)
        assert released is True
        assert service.is_reserved(b.id, org_id) is False

        # Another worker can now reserve it.
        res = service.reserve(bin_id=b.id, worker_id=worker_b, org_id=org_id)
        assert res.worker_id == worker_b

    def test_release_no_reservation_returns_false(
        self, db_session, service, org_id, warehouse_id
    ):
        b = _create_bin(db_session, org_id, warehouse_id)
        assert service.release(bin_id=b.id, worker_id=uuid.uuid4(), org_id=org_id) is False

    def test_force_release(self, db_session, service, org_id, warehouse_id):
        b = _create_bin(db_session, org_id, warehouse_id)
        service.reserve(bin_id=b.id, worker_id=uuid.uuid4(), org_id=org_id)

        assert service.force_release(b.id, org_id) is True
        assert service.is_reserved(b.id, org_id) is False


class TestCleanupAndQueries:
    def test_cleanup_expired_releases_timed_out(
        self, db_session, service, org_id, warehouse_id
    ):
        b = _create_bin(db_session, org_id, warehouse_id)
        expired = BinReservation(
            id=uuid.uuid4(),
            organization_id=org_id,
            bin_location_id=b.id,
            worker_id=uuid.uuid4(),
            reserved_at=datetime.now(UTC) - timedelta(minutes=10),
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        db_session.add(expired)
        db_session.commit()

        count = service.cleanup_expired(org_id=org_id)
        assert count == 1
        assert service.is_reserved(b.id, org_id) is False

    def test_get_reserved_bin_ids_excludes_own_worker(
        self, db_session, service, org_id, warehouse_id
    ):
        b1 = _create_bin(db_session, org_id, warehouse_id, code="BIN01")
        b2 = _create_bin(db_session, org_id, warehouse_id, code="BIN02")
        worker_a = uuid.uuid4()
        worker_b = uuid.uuid4()
        service.reserve(bin_id=b1.id, worker_id=worker_a, org_id=org_id)
        service.reserve(bin_id=b2.id, worker_id=worker_b, org_id=org_id)

        # From worker A's perspective, only B2 is an obstacle.
        reserved = service.get_reserved_bin_ids(
            org_id=org_id, exclude_worker_id=worker_a
        )
        assert reserved == {b2.id}
