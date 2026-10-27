"""Serial/QR uniqueness guards in the put-away flow.

A serial (QR) identifies exactly one physical unit and is unique per product,
so put-away must never queue or stock the same serial twice — neither when a
legacy receipt line repeats its batch/serial per quantity, nor when the mobile
app retries a completion whose response was lost.
"""

import uuid
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.core.exceptions import ValidationError
from app.services.put_away_service import PutAwayService


def _service():
    service = PutAwayService.__new__(PutAwayService)
    service.db = SimpleNamespace()  # replaced per test
    return service


def _slip_item(**overrides):
    values = {
        "flag": "ok",
        "sku": "PT-QR-001",
        "batch_number": "SN-A",
        "quantity": Decimal("3"),
        "packaging_unit_id": None,
        "serial_nos": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _specs(service, items, pack_size=4, mode="auto"):
    item = SimpleNamespace(id=uuid.uuid4())
    service._resolve_item_by_sku = lambda *_: item
    service._items_per_master_pack = lambda *_: pack_size
    slip = SimpleNamespace(items=items)
    specs, _warnings = service._build_put_away_specs(slip, uuid.uuid4(), mode)
    return specs


def test_legacy_line_serial_is_not_repeated_for_quantity():
    """A qty>1 line without persisted serials must not queue the same QR N times."""
    service = _service()

    specs = _specs(service, [_slip_item(quantity=Decimal("3"))])

    assert len(specs) == 1
    assert specs[0]["serial_nos"] == ["SN-A"]


def test_overlapping_serial_lists_are_deduplicated():
    """Two slip lines listing the same unit must yield one put-away entry."""
    service = _service()
    items = [
        _slip_item(serial_nos=["SN-A", "SN-B"], quantity=Decimal("2")),
        _slip_item(serial_nos=["SN-B", "SN-C"], quantity=Decimal("2")),
    ]

    specs = _specs(service, items, pack_size=4)

    serials = [serial for spec in specs for serial in spec["serial_nos"]]
    assert serials == ["SN-A", "SN-B", "SN-C"]


def test_duplicate_serial_across_packaging_units_is_dropped():
    """The same serial in two packaging-unit groups must be queued once."""
    service = _service()
    items = [
        _slip_item(
            serial_nos=["SN-A"], quantity=Decimal("1"), packaging_unit_id=uuid.uuid4()
        ),
        _slip_item(
            serial_nos=["SN-A"], quantity=Decimal("1"), packaging_unit_id=uuid.uuid4()
        ),
    ]

    specs = _specs(service, items, pack_size=4)

    serials = [serial for spec in specs for serial in spec["serial_nos"]]
    assert serials == ["SN-A"]


def _complete(item, *, stocked=None, add_stock=None, validate=None, locked=None):
    service = _service()
    service.db = type("DB", (), {})()
    query = type("Query", (), {})()
    chain = type("Chain", (), {})()
    chain.with_for_update = lambda: chain
    chain.first = lambda: item
    query.filter = lambda *args, **kwargs: chain
    service.db.query = lambda *args, **kwargs: query
    service.db.commit = lambda: None
    service.db.flush = lambda *args, **kwargs: None
    service.db.refresh = lambda *args, **kwargs: None

    service.bin_stock_service = type("Stock", (), {})()
    service.bin_stock_service.lock_serials = lambda org_id, serials: (
        locked.append(list(serials)) if locked is not None else None
    )
    service.bin_stock_service.get_stocked_serial_locations = (
        lambda org_id, serials, item_id=None: stocked or {}
    )
    if add_stock is not None:
        service.bin_stock_service.add_stock = add_stock
    if validate is not None:
        service.bin_stock_service.validate_capacity = validate
    service.reservation_service = type("Res", (), {})()
    service.reservation_service.release = lambda *args, **kwargs: None
    return service


def _pending_item(serials):
    return SimpleNamespace(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        put_away_list_id=uuid.uuid4(),
        item_id=uuid.uuid4(),
        sku="PT-QR-001",
        quantity=Decimal(str(len(serials))),
        bin_location_id=uuid.uuid4(),
        packaging_unit_id=None,
        serial_nos=list(serials),
        status="pending",
        completed_at=None,
        put_away_list=None,
    )


def test_complete_item_rejects_duplicate_serials_in_payload():
    item = _pending_item(["SN-A", "SN-A"])
    calls = []
    service = _complete(item, add_stock=lambda **kw: calls.append(kw))

    with pytest.raises(ValidationError) as exc:
        service.complete_item(item.id, uuid.uuid4(), item.organization_id)

    assert exc.value.code == "DUPLICATE_SERIAL_NUMBERS"
    assert calls == []


def test_retry_does_not_add_serials_already_in_the_target_bin():
    """A lost response makes the app retry; stock already written stays untouched."""
    item = _pending_item(["SN-A", "SN-B"])
    calls = []
    validated = []
    locked = []

    service = _complete(
        item,
        stocked={"SN-A": [(item.bin_location_id, Decimal("1"))]},
        add_stock=lambda **kw: calls.append(kw),
        validate=lambda **kw: validated.append(kw),
        locked=locked,
    )

    service.complete_item(
        item.id,
        uuid.uuid4(),
        item.organization_id,
        check_completion=False,
    )

    assert locked == [["SN-A", "SN-B"]]
    assert [call["batch_number"] for call in calls] == ["SN-B"]
    assert validated[0]["quantity"] == Decimal("1")
    assert item.status == "completed"


def test_complete_item_rejects_serial_stocked_in_another_bin():
    item = _pending_item(["SN-A"])
    service = _complete(
        item,
        stocked={"SN-A": [(uuid.uuid4(), Decimal("1"))]},
        add_stock=lambda **kw: pytest.fail("stock must not be added"),
    )

    with pytest.raises(ValidationError) as exc:
        service.complete_item(item.id, uuid.uuid4(), item.organization_id)

    assert exc.value.code == "SERIAL_ALREADY_STOCKED"


def test_complete_item_rejects_serial_found_in_target_bin_and_elsewhere():
    """Corrupt data in two bins must be reported, not silently skipped."""
    item = _pending_item(["SN-A"])
    service = _complete(
        item,
        stocked={
            "SN-A": [
                (item.bin_location_id, Decimal("1")),
                (uuid.uuid4(), Decimal("1")),
            ]
        },
        add_stock=lambda **kw: pytest.fail("stock must not be added"),
    )

    with pytest.raises(ValidationError) as exc:
        service.complete_item(item.id, uuid.uuid4(), item.organization_id)

    assert exc.value.code == "SERIAL_ALREADY_STOCKED"
