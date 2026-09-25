"""Accepting a short delivery by closing a partially delivered ASN.

The database fixtures in this suite are disabled (see ``conftest.py`` — the
SQLite fixture cannot compile the app's PostgreSQL UUID columns), so these tests
exercise the closure rules and the service orchestration against a stubbed
session instead of a real database.
"""

import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import StateError, ValidationError
from app.models.base import AsnOrderStatus
from app.schemas.asn_order import (
    AsnOrderCloseRequest,
    AsnOrderListItem,
    AsnOrderResponse,
)
from app.services.asn_order_service import AsnOrderService

#: Columns the closure is expected to persist on ``asn_orders``.
CLOSE_FIELDS = (
    "short_closed",
    "short_closed_qty",
    "close_reason_code",
    "close_note",
    "closed_by",
    "closed_at",
)


# ── helpers ─────────────────────────────────────────────────────────────────


def _service():
    """An AsnOrderService over a stubbed session."""
    svc = AsnOrderService(MagicMock())
    svc.repo = MagicMock()
    # ``_to_response`` walks the whole ORM graph; the closure rules are what
    # these tests are about.
    svc._to_response = lambda asn: {"id": str(asn.id), "status": asn.status.value}
    return svc


def _asn(status=AsnOrderStatus.PARTIALLY_DELIVERED, **overrides):
    asn = SimpleNamespace(
        id=uuid.uuid4(),
        asn_order_no="ASN-0001",
        status=status,
        warehouse_id_to=uuid.uuid4(),
        warehouse_id_from=uuid.uuid4(),
        short_closed=False,
        short_closed_qty=None,
        close_reason_code=None,
        close_note=None,
        closed_by=None,
        closed_at=None,
        updated_by=None,
    )
    for key, value in overrides.items():
        setattr(asn, key, value)
    return asn


def _user(user_type="organization_admin", permissions=()):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        user_type=user_type,
        permissions=list(permissions),
    )


class _FakeShortBalanceService:
    """Stand-in for InboundShortBalanceService with scripted results."""

    residual = Decimal("0")
    written_off = (0, Decimal("0"))
    calls: list = []

    def __init__(self, db):
        type(self).calls = []

    def open_short_total(self, asn_order_id, organization_id):
        return type(self).residual

    def resolve_close_reason(self, reason_code, organization_id):
        if not reason_code:
            raise ValidationError(
                message="A reason code is required to close a shortage"
            )
        return SimpleNamespace(code=reason_code.strip().upper())

    def write_off_open_for_asn(self, **kwargs):
        type(self).calls.append(kwargs)
        return type(self).written_off


@pytest.fixture
def short_svc(monkeypatch):
    """Swap the shortage service the ASN closure delegates to."""
    monkeypatch.setattr(
        "app.services.inbound_short_balance_service.InboundShortBalanceService",
        _FakeShortBalanceService,
    )
    _FakeShortBalanceService.residual = Decimal("0")
    _FakeShortBalanceService.written_off = (0, Decimal("0"))
    _FakeShortBalanceService.calls = []
    return _FakeShortBalanceService


# ── transition rules ───────────────────────────────────────────────────────


def test_partially_delivered_can_be_closed_as_short():
    """The provision being added: a partially delivered ASN is closable."""
    _service()._validate_status_transition(
        AsnOrderStatus.PARTIALLY_DELIVERED, AsnOrderStatus.CLOSED
    )


def test_delivered_can_be_closed():
    _service()._validate_status_transition(
        AsnOrderStatus.DELIVERED, AsnOrderStatus.CLOSED
    )


@pytest.mark.parametrize("current", [AsnOrderStatus.DRAFT, AsnOrderStatus.CONFIRMED])
def test_open_asn_cannot_be_closed_directly(current):
    """Closing short is for received-or-partially-received orders only."""
    with pytest.raises(ValueError):
        _service()._validate_status_transition(current, AsnOrderStatus.CLOSED)


# ── closure behaviour ──────────────────────────────────────────────────────


def test_closing_a_short_requires_a_reason(short_svc):
    svc = _service()
    asn = _asn()
    svc.repo.get_by_id_with_items.return_value = asn
    short_svc.residual = Decimal("4")

    with pytest.raises(ValidationError):
        svc.close_short(asn.id, uuid.uuid4(), user=_user(), reason_code=None)

    # Nothing is committed when the reason is missing.
    assert asn.status is AsnOrderStatus.PARTIALLY_DELIVERED
    assert asn.closed_at is None


def test_closing_a_short_records_it_and_writes_off_the_balances(short_svc):
    svc = _service()
    asn = _asn()
    svc.repo.get_by_id_with_items.return_value = asn
    short_svc.residual = Decimal("4")
    short_svc.written_off = (2, Decimal("4"))
    user = _user()

    result = svc.close_short(
        asn.id,
        user.organization_id,
        user=user,
        reason_code="short_physical",
        note="Carrier short-shipped the last carton",
    )

    assert asn.status is AsnOrderStatus.CLOSED
    assert asn.short_closed is True
    assert asn.short_closed_qty == Decimal("4")
    assert asn.close_reason_code == "SHORT_PHYSICAL"
    assert asn.close_note == "Carrier short-shipped the last carton"
    assert asn.closed_by == user.id
    assert asn.closed_at is not None
    assert result["status"] == "closed"

    # The ASN's open shortages are closed with the same reason, so the short
    # ledger does not stay open behind a closed order.
    assert len(short_svc.calls) == 1
    assert short_svc.calls[0]["asn_order_id"] == asn.id
    assert short_svc.calls[0]["reason_code"] == "SHORT_PHYSICAL"
    assert short_svc.calls[0]["actor_id"] == user.id


def test_closing_without_a_short_needs_no_reason(short_svc):
    svc = _service()
    asn = _asn(status=AsnOrderStatus.DELIVERED)
    svc.repo.get_by_id_with_items.return_value = asn
    short_svc.residual = Decimal("0")

    svc.close_short(asn.id, uuid.uuid4(), user=_user(), reason_code=None)

    assert asn.status is AsnOrderStatus.CLOSED
    assert asn.short_closed is False
    assert asn.short_closed_qty == Decimal("0")
    # Nothing to write off.
    assert short_svc.calls == []


# ── authority ──────────────────────────────────────────────────────────────


def test_closing_a_short_requires_manager_authority(short_svc):
    svc = _service()
    asn = _asn()
    svc.repo.get_by_id_with_items.return_value = asn
    # Not an admin, no wildcard permission, and no manager assignment.
    svc.db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(StateError) as excinfo:
        svc.close_short(
            asn.id, uuid.uuid4(), user=_user(user_type="user"), reason_code="X"
        )

    assert excinfo.value.code == "ASN_CLOSE_APPROVAL_REQUIRED"
    assert asn.status is AsnOrderStatus.PARTIALLY_DELIVERED


@pytest.mark.parametrize(
    "user_type,permissions",
    [
        ("organization_admin", ()),
        ("system_admin", ()),
        ("user", ("warehouse.manage",)),
        ("user", ("*.*",)),
    ],
)
def test_manager_or_admin_authority_is_accepted(short_svc, user_type, permissions):
    svc = _service()
    asn = _asn()
    svc.repo.get_by_id_with_items.return_value = asn
    short_svc.residual = Decimal("2")
    short_svc.written_off = (1, Decimal("2"))

    svc.close_short(
        asn.id,
        uuid.uuid4(),
        user=_user(user_type=user_type, permissions=permissions),
        reason_code="SHORT_PHYSICAL",
    )

    assert asn.status is AsnOrderStatus.CLOSED


# ── refusal paths ──────────────────────────────────────────────────────────


def test_a_draft_asn_cannot_be_closed_short(short_svc):
    svc = _service()
    asn = _asn(status=AsnOrderStatus.DRAFT)
    svc.repo.get_by_id_with_items.return_value = asn

    with pytest.raises(StateError) as excinfo:
        svc.close_short(asn.id, uuid.uuid4(), user=_user(), reason_code=None)

    assert excinfo.value.code == "ASN_NOT_CLOSABLE"


@pytest.mark.parametrize("status", [AsnOrderStatus.CLOSED, AsnOrderStatus.CANCELLED])
def test_a_finished_asn_cannot_be_closed_again(short_svc, status):
    svc = _service()
    asn = _asn(status=status)
    svc.repo.get_by_id_with_items.return_value = asn

    with pytest.raises(StateError) as excinfo:
        svc.close_short(asn.id, uuid.uuid4(), user=_user(), reason_code=None)

    assert excinfo.value.code == "ASN_ALREADY_CLOSED"


def test_close_authority_does_not_fall_back_to_the_source_warehouse(short_svc):
    """A missing destination warehouse must not let the origin manager approve."""
    svc = _service()
    asn = _asn(warehouse_id_to=None)
    svc.repo.get_by_id_with_items.return_value = asn
    short_svc.residual = Decimal("2")
    short_svc.written_off = (1, Decimal("2"))
    # The stub would happily report "manager" for the source warehouse.
    svc.db.query.return_value.filter.return_value.first.return_value = None

    with pytest.raises(StateError) as excinfo:
        svc.close_short(
            asn.id, uuid.uuid4(), user=_user(user_type="user"), reason_code="X"
        )

    assert excinfo.value.code == "ASN_CLOSE_APPROVAL_REQUIRED"
    assert asn.status is AsnOrderStatus.PARTIALLY_DELIVERED


def test_generic_status_endpoint_cannot_close_an_asn(short_svc):
    """Closing must go through close_short (approval + reason + write-off)."""
    svc = _service()
    asn = _asn()
    svc.repo.get_by_id_with_items.return_value = asn

    with pytest.raises(StateError) as excinfo:
        svc.update_status(asn.id, "closed", uuid.uuid4(), uuid.uuid4())

    assert excinfo.value.code == "ASN_CLOSE_REQUIRES_APPROVAL"
    assert asn.status is AsnOrderStatus.PARTIALLY_DELIVERED


# ── persistence / API contract ─────────────────────────────────────────────


def test_asn_order_model_has_the_closure_columns():
    from app.models.asn_order import AsnOrder

    for name in CLOSE_FIELDS:
        assert name in AsnOrder.__table__.columns, name


def test_asn_response_exposes_the_closure_fields():
    for name in CLOSE_FIELDS:
        assert name in AsnOrderResponse.model_fields, name
    assert AsnOrderResponse.model_fields["short_closed"].default is False


def test_asn_list_item_flags_short_closure():
    assert "short_closed" in AsnOrderListItem.model_fields
    assert AsnOrderListItem.model_fields["short_closed"].default is False


def test_close_request_accepts_a_reason_and_note():
    request = AsnOrderCloseRequest(
        reason_code="SHORT_PHYSICAL", note="Carrier short-shipped"
    )

    assert request.reason_code == "SHORT_PHYSICAL"
    assert request.note == "Carrier short-shipped"


def test_close_request_allows_an_empty_body():
    """A fully delivered ASN closes without a reason."""
    request = AsnOrderCloseRequest()

    assert request.reason_code is None
    assert request.note is None


def test_close_request_rejects_an_over_long_reason():
    with pytest.raises(PydanticValidationError):
        AsnOrderCloseRequest(reason_code="x" * 81)
