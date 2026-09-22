"""Phase 1 coverage for QSeal scan-event analytics context."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.qseal import QSealScanRequest
from app.services.qseal_service import QSealService


def _query(first_value):
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = first_value
    return query


def test_qseal_child_scan_persists_product_batch_and_request_metadata():
    organization_id = uuid4()
    product_id = uuid4()
    block_id = uuid4()
    child_id = uuid4()
    item_id = uuid4()

    child = SimpleNamespace(
        id=child_id,
        product_id=product_id,
        block_id=block_id,
        parent_id=None,
        serial_number="QSL-CHILD-001",
    )
    item = SimpleNamespace(
        id=item_id,
        product_id=product_id,
        block_id=block_id,
        scan_count=2,
        last_scanned_at=None,
    )
    block = SimpleNamespace(batch="BATCH-001")
    event = SimpleNamespace(id=uuid4(), verification_status="valid")

    increment_query = _query(None)
    db = Mock()
    db.query.side_effect = [
        _query(child),  # initial QSealParameters lookup
        _query(child),  # context QSealParameters lookup
        _query(item),
        _query(block),
        increment_query,  # atomic scan_count increment
    ]
    service = QSealService(db)
    service.repo.get_by_serial = Mock(return_value=None)
    service.repo.record_scan = Mock(return_value=event)
    service.suspicion_service.assess = Mock(
        return_value={
            "is_suspicious": False,
            "risk_score": 0,
            "suspicious_reasons": [],
            "review_status": "not_flagged",
            "flagged_at": None,
        }
    )

    result = service.record_scan(
        QSealScanRequest(serial_number=child.serial_number, latitude=18.52),
        organization_id,
        request_headers={
            "user-agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
            "referer": "https://client.example/qseal",
            "accept-language": "en-IN,en;q=0.9",
        },
        client_ip="203.0.113.10",
    )

    payload = service.repo.record_scan.call_args.args[0]
    assert result["scan_event_id"] == event.id
    assert payload["product_id"] == product_id
    assert payload["block_id"] == block_id
    assert payload["batch"] == "BATCH-001"
    assert payload["qseal_parameter_id"] == child_id
    assert payload["qseal_type"] == "child_unit"
    assert payload["verification_status"] == "valid"
    assert payload["device_type"] == "mobile"
    assert payload["ip_address"] == "203.0.113.10"
    assert payload["referrer_url"] == "https://client.example/qseal"
    assert payload["language"] == "en-IN,en;q"
    # The counter is incremented atomically in the database (so concurrent
    # scans cannot lose an update) rather than on the in-memory instance.
    increment_query.update.assert_called_once()
    assert item.last_scanned_at is not None


def test_unknown_qseal_scan_is_saved_before_returning_not_found():
    organization_id = uuid4()
    event = SimpleNamespace(id=uuid4(), verification_status="not_found")

    db = Mock()
    db.query.side_effect = [
        _query(None),  # initial QSealParameters lookup
        _query(None),  # context QSealParameters lookup
        _query(None),  # ProductItem lookup
    ]
    service = QSealService(db)
    service.repo.get_by_serial = Mock(return_value=None)
    service.repo.record_scan = Mock(return_value=event)

    with pytest.raises(HTTPException) as error:
        service.record_scan(
            QSealScanRequest(serial_number="QSL-NOT-FOUND"),
            organization_id,
        )

    assert error.value.status_code == 404
    payload = service.repo.record_scan.call_args.args[0]
    assert payload["verification_status"] == "not_found"
    assert payload["qseal_type"] == "unknown"


def test_qseal_parent_scan_infers_single_product_and_batch_from_linked_units():
    organization_id = uuid4()
    parent_id = uuid4()
    product_id = uuid4()
    block_id = uuid4()
    parent = SimpleNamespace(
        id=parent_id,
        qseal_type="shipper",
        serial_number="QSL-PARENT-001",
        name="Master Pack",
        parent_id=None,
    )
    linked_param = SimpleNamespace(product_id=product_id, block_id=block_id)
    block = SimpleNamespace(batch="BATCH-002")
    event = SimpleNamespace(id=uuid4(), verification_status="valid")

    db = Mock()
    context_params = _query(None)
    context_params.all.return_value = [linked_param]
    db.query.side_effect = [
        _query(None),  # QSealParameters lookup for the parent serial
        _query(None),  # ProductItem lookup
        context_params,
        _query(block),
    ]
    service = QSealService(db)
    service.repo.get_by_serial = Mock(return_value=parent)
    service.repo.record_scan = Mock(return_value=event)
    service.repo.count_children = Mock(return_value=2)

    result = service.record_scan(
        QSealScanRequest(serial_number=parent.serial_number),
        organization_id,
    )

    payload = service.repo.record_scan.call_args.args[0]
    assert result["scan_event_id"] == event.id
    assert payload["product_id"] == product_id
    assert payload["block_id"] == block_id
    assert payload["batch"] == "BATCH-002"
    assert payload["qseal_track_id"] == parent_id
    assert payload["qseal_type"] == "shipper"
