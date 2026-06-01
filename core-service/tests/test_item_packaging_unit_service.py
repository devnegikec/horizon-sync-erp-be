"""Unit tests for ItemPackagingUnitService.

Covers:
- create_packaging_unit: happy path, duplicate unit_name (409), conversion_factor <= 0 (422),
  item not found (404)
- soft_delete_packaging_unit: sets is_active = False, not-found (404)
- resolve_by_qr_identifier: returns unit when active, None when inactive, None when not found

Requirements: 2.4, 2.5, 2.6
"""

import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.models.item import Item
from app.models.item_packaging_unit import ItemPackagingUnit
from app.schemas.item_packaging_unit import ItemPackagingUnitCreate
from app.services.item_packaging_unit_service import ItemPackagingUnitService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def org_id():
    return uuid.uuid4()


@pytest.fixture
def service():
    """Return a bare ItemPackagingUnitService (no db injected — passed per call)."""
    return ItemPackagingUnitService()


def _create_item(db_session, org_id) -> Item:
    """Helper: insert a minimal Item row and return it."""
    item = Item(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_code=f"ITEM-{uuid.uuid4().hex[:6].upper()}",
        item_name="Test Item",
        item_type="stock",
        uom="Nos",
    )
    db_session.add(item)
    db_session.flush()
    return item


def _create_packaging_unit(
    db_session,
    org_id,
    item_id,
    unit_name: str = "Box of 12",
    conversion_factor: Decimal = Decimal("12"),
    qr_identifier: str | None = None,
    is_active: bool = True,
) -> ItemPackagingUnit:
    """Helper: insert an ItemPackagingUnit row and return it."""
    pu = ItemPackagingUnit(
        id=uuid.uuid4(),
        organization_id=org_id,
        item_id=item_id,
        unit_name=unit_name,
        conversion_factor=conversion_factor,
        qr_identifier=qr_identifier,
        is_base_unit=False,
        is_active=is_active,
    )
    db_session.add(pu)
    db_session.flush()
    return pu


def _make_create_payload(
    unit_name: str = "Box of 12",
    conversion_factor: Decimal = Decimal("12"),
    qr_identifier: str | None = None,
) -> ItemPackagingUnitCreate:
    """Helper: build a valid ItemPackagingUnitCreate schema."""
    return ItemPackagingUnitCreate(
        unit_name=unit_name,
        conversion_factor=conversion_factor,
        qr_identifier=qr_identifier,
        is_base_unit=False,
        is_active=True,
    )


# ---------------------------------------------------------------------------
# create_packaging_unit
# ---------------------------------------------------------------------------


class TestCreatePackagingUnit:
    """Tests for ItemPackagingUnitService.create_packaging_unit."""

    def test_happy_path_creates_and_returns_unit(self, db_session, service, org_id):
        """Happy path: creates a packaging unit and returns the persisted row."""
        item = _create_item(db_session, org_id)
        data = _make_create_payload(unit_name="Pallet of 144", conversion_factor=Decimal("144"))

        result = service.create_packaging_unit(
            item_id=item.id,
            data=data,
            org_id=org_id,
            db=db_session,
        )

        assert result.id is not None
        assert result.item_id == item.id
        assert result.organization_id == org_id
        assert result.unit_name == "Pallet of 144"
        assert result.conversion_factor == Decimal("144")
        assert result.is_active is True

    def test_happy_path_stores_qr_identifier(self, db_session, service, org_id):
        """Should persist the optional qr_identifier when provided."""
        item = _create_item(db_session, org_id)
        data = _make_create_payload(qr_identifier="QR-BOX-001")

        result = service.create_packaging_unit(
            item_id=item.id,
            data=data,
            org_id=org_id,
            db=db_session,
        )

        assert result.qr_identifier == "QR-BOX-001"

    def test_duplicate_unit_name_raises_409(self, db_session, service, org_id):
        """Duplicate (item_id, unit_name) should raise HTTP 409."""
        item = _create_item(db_session, org_id)
        _create_packaging_unit(db_session, org_id, item.id, unit_name="Box of 12")
        db_session.commit()

        data = _make_create_payload(unit_name="Box of 12")

        with pytest.raises(HTTPException) as exc_info:
            service.create_packaging_unit(
                item_id=item.id,
                data=data,
                org_id=org_id,
                db=db_session,
            )

        assert exc_info.value.status_code == 409
        assert "Box of 12" in exc_info.value.detail

    def test_zero_conversion_factor_raises_422(self, db_session, service, org_id):
        """conversion_factor = 0 should raise HTTP 422."""
        item = _create_item(db_session, org_id)

        # Bypass Pydantic validation by constructing the schema with model_construct
        data = ItemPackagingUnitCreate.model_construct(
            unit_name="Bad Unit",
            conversion_factor=Decimal("0"),
            qr_identifier=None,
            is_base_unit=False,
            is_active=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            service.create_packaging_unit(
                item_id=item.id,
                data=data,
                org_id=org_id,
                db=db_session,
            )

        assert exc_info.value.status_code == 422

    def test_negative_conversion_factor_raises_422(self, db_session, service, org_id):
        """conversion_factor < 0 should raise HTTP 422."""
        item = _create_item(db_session, org_id)

        data = ItemPackagingUnitCreate.model_construct(
            unit_name="Negative Unit",
            conversion_factor=Decimal("-5"),
            qr_identifier=None,
            is_base_unit=False,
            is_active=True,
        )

        with pytest.raises(HTTPException) as exc_info:
            service.create_packaging_unit(
                item_id=item.id,
                data=data,
                org_id=org_id,
                db=db_session,
            )

        assert exc_info.value.status_code == 422

    def test_item_not_found_raises_404(self, db_session, service, org_id):
        """Non-existent item_id should raise HTTP 404."""
        data = _make_create_payload()

        with pytest.raises(HTTPException) as exc_info:
            service.create_packaging_unit(
                item_id=uuid.uuid4(),  # random — does not exist
                data=data,
                org_id=org_id,
                db=db_session,
            )

        assert exc_info.value.status_code == 404

    def test_item_belonging_to_different_org_raises_404(
        self, db_session, service, org_id
    ):
        """Item that exists but belongs to a different org should raise HTTP 404."""
        other_org_id = uuid.uuid4()
        item = _create_item(db_session, other_org_id)  # different org
        db_session.commit()

        data = _make_create_payload()

        with pytest.raises(HTTPException) as exc_info:
            service.create_packaging_unit(
                item_id=item.id,
                data=data,
                org_id=org_id,  # caller's org — does not match item's org
                db=db_session,
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# soft_delete_packaging_unit
# ---------------------------------------------------------------------------


class TestSoftDeletePackagingUnit:
    """Tests for ItemPackagingUnitService.soft_delete_packaging_unit."""

    def test_sets_is_active_false(self, db_session, service, org_id):
        """Soft-delete should set is_active = False on the row."""
        item = _create_item(db_session, org_id)
        pu = _create_packaging_unit(db_session, org_id, item.id, is_active=True)
        db_session.commit()

        result = service.soft_delete_packaging_unit(
            item_id=item.id,
            unit_id=pu.id,
            org_id=org_id,
            db=db_session,
        )

        assert result.is_active is False

    def test_soft_delete_does_not_remove_row(self, db_session, service, org_id):
        """The row should still exist in the database after soft-delete."""
        item = _create_item(db_session, org_id)
        pu = _create_packaging_unit(db_session, org_id, item.id)
        db_session.commit()

        service.soft_delete_packaging_unit(
            item_id=item.id,
            unit_id=pu.id,
            org_id=org_id,
            db=db_session,
        )

        # Row must still be queryable
        still_exists = (
            db_session.query(ItemPackagingUnit)
            .filter(ItemPackagingUnit.id == pu.id)
            .first()
        )
        assert still_exists is not None
        assert still_exists.is_active is False

    def test_not_found_raises_404(self, db_session, service, org_id):
        """Non-existent unit_id should raise HTTP 404."""
        item = _create_item(db_session, org_id)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            service.soft_delete_packaging_unit(
                item_id=item.id,
                unit_id=uuid.uuid4(),  # does not exist
                org_id=org_id,
                db=db_session,
            )

        assert exc_info.value.status_code == 404

    def test_wrong_item_id_raises_404(self, db_session, service, org_id):
        """Unit that exists but belongs to a different item should raise HTTP 404."""
        item_a = _create_item(db_session, org_id)
        item_b = _create_item(db_session, org_id)
        pu = _create_packaging_unit(db_session, org_id, item_a.id)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            service.soft_delete_packaging_unit(
                item_id=item_b.id,  # wrong item
                unit_id=pu.id,
                org_id=org_id,
                db=db_session,
            )

        assert exc_info.value.status_code == 404

    def test_wrong_org_raises_404(self, db_session, service, org_id):
        """Unit that exists but belongs to a different org should raise HTTP 404."""
        item = _create_item(db_session, org_id)
        pu = _create_packaging_unit(db_session, org_id, item.id)
        db_session.commit()

        with pytest.raises(HTTPException) as exc_info:
            service.soft_delete_packaging_unit(
                item_id=item.id,
                unit_id=pu.id,
                org_id=uuid.uuid4(),  # different org
                db=db_session,
            )

        assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# resolve_by_qr_identifier
# ---------------------------------------------------------------------------


class TestResolveByQrIdentifier:
    """Tests for ItemPackagingUnitService.resolve_by_qr_identifier."""

    def test_returns_unit_when_active(self, db_session, service, org_id):
        """Should return the packaging unit when it is active and qr_identifier matches."""
        item = _create_item(db_session, org_id)
        pu = _create_packaging_unit(
            db_session, org_id, item.id, qr_identifier="QR-ACTIVE-001", is_active=True
        )
        db_session.commit()

        result = service.resolve_by_qr_identifier(
            qr_identifier="QR-ACTIVE-001",
            org_id=org_id,
            db=db_session,
        )

        assert result is not None
        assert result.id == pu.id
        assert result.qr_identifier == "QR-ACTIVE-001"

    def test_returns_none_when_inactive(self, db_session, service, org_id):
        """Should return None when the matching unit is inactive (soft-deleted)."""
        item = _create_item(db_session, org_id)
        _create_packaging_unit(
            db_session,
            org_id,
            item.id,
            qr_identifier="QR-INACTIVE-001",
            is_active=False,
        )
        db_session.commit()

        result = service.resolve_by_qr_identifier(
            qr_identifier="QR-INACTIVE-001",
            org_id=org_id,
            db=db_session,
        )

        assert result is None

    def test_returns_none_when_not_found(self, db_session, service, org_id):
        """Should return None when no unit matches the qr_identifier."""
        result = service.resolve_by_qr_identifier(
            qr_identifier="QR-DOES-NOT-EXIST",
            org_id=org_id,
            db=db_session,
        )

        assert result is None

    def test_returns_none_for_different_org(self, db_session, service, org_id):
        """Should return None when the unit belongs to a different organisation."""
        other_org_id = uuid.uuid4()
        item = _create_item(db_session, other_org_id)
        _create_packaging_unit(
            db_session,
            other_org_id,
            item.id,
            qr_identifier="QR-OTHER-ORG",
            is_active=True,
        )
        db_session.commit()

        result = service.resolve_by_qr_identifier(
            qr_identifier="QR-OTHER-ORG",
            org_id=org_id,  # caller's org — different from unit's org
            db=db_session,
        )

        assert result is None

    def test_active_unit_takes_precedence_over_inactive(
        self, db_session, service, org_id
    ):
        """Active unit should be returned; inactive unit with same identifier is ignored."""
        item = _create_item(db_session, org_id)
        # qr_identifier is unique per DB constraint, so we just verify active is returned
        pu = _create_packaging_unit(
            db_session, org_id, item.id, qr_identifier="QR-UNIQUE-ACTIVE", is_active=True
        )
        db_session.commit()

        result = service.resolve_by_qr_identifier(
            qr_identifier="QR-UNIQUE-ACTIVE",
            org_id=org_id,
            db=db_session,
        )

        assert result is not None
        assert result.id == pu.id
        assert result.is_active is True
