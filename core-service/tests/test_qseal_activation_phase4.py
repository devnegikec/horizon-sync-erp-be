"""Phase 4 contract checks for the QSeal mobile activation APIs."""

from uuid import uuid4
from unittest.mock import Mock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.config import settings
from app.models.qseal_activation_request import QSealActivationRequest
from app.schemas.qseal_activation import ActivationSettingsInput, SerialActivationRequest
from app.services.qseal_activation_service import QSealActivationService


def test_activation_settings_trim_whitespace():
    payload = ActivationSettingsInput(
        dispatch_batch="  DB-001  ",
        batch_size=2,
        manufacturing_date="2026-09-08",
        manufacturing_unit="  Plant-A  ",
        destination_market="  USA  ",
        mrp="499.00",
    )

    assert payload.dispatch_batch == "DB-001"
    assert payload.manufacturing_unit == "Plant-A"
    assert payload.destination_market == "USA"


@pytest.mark.parametrize("serials", [["SER-1", " SER-1 "], ["SER-1", ""]])
def test_activation_request_rejects_duplicate_or_blank_serials(serials):
    with pytest.raises(ValidationError):
        SerialActivationRequest(product_id=uuid4(), serial_numbers=serials)


def test_activation_request_normalizes_serials_and_keeps_idempotency_key():
    request = SerialActivationRequest(
        product_id=uuid4(),
        serial_numbers=[" SER-1 ", "SER-2"],
        idempotency_key="mobile-retry-001",
    )

    assert request.serial_numbers == ["SER-1", "SER-2"]
    assert request.idempotency_key == "mobile-retry-001"


def test_activation_request_rejects_blank_idempotency_key():
    with pytest.raises(ValidationError):
        SerialActivationRequest(
            product_id=uuid4(), serial_numbers=["SER-1"], idempotency_key="   "
        )


def test_scan_accepts_trusted_qr_domain():
    service = QSealActivationService(None)

    assert service.resolve_serial(f"https://{settings.qr_domain}/g/123/s/SER-1/") == "SER-1"


def test_scan_rejects_untrusted_qr_domain():
    service = QSealActivationService(None)

    with pytest.raises(HTTPException) as error:
        service.resolve_serial("https://example.invalid/qr/SER-1")

    assert error.value.status_code == 400
    assert error.value.detail["code"] == "INVALID_REQUEST"


def test_scan_rejects_blank_serial():
    service = QSealActivationService(None)

    with pytest.raises(HTTPException) as error:
        service.resolve_serial("   ")

    assert error.value.status_code == 400
    assert error.value.detail["code"] == "INVALID_REQUEST"


def test_legacy_scan_parses_long_url_without_network_request():
    db = Mock()
    db.query.return_value.filter.return_value.first.return_value = None
    service = QSealActivationService(db)

    serial = service.resolve_serial(
        f"https://{settings.qr_domain}/g/123/s/SER-1/", uuid4()
    )

    assert serial == "SER-1"


def test_activation_request_hash_is_stable_for_serial_order():
    product_id = uuid4()
    settings_id = uuid4()

    first = QSealActivationService._activation_request_hash(
        product_id, ["SER-2", "SER-1"], settings_id
    )
    retry = QSealActivationService._activation_request_hash(
        product_id, ["SER-1", "SER-2"], settings_id
    )

    assert first == retry


def test_activation_request_has_tenant_scoped_unique_key():
    constraint = next(
        constraint
        for constraint in QSealActivationRequest.__table__.constraints
        if constraint.name == "uq_qseal_activation_request_org_key"
    )

    assert [column.name for column in constraint.columns] == [
        "organization_id",
        "idempotency_key",
    ]


def test_completed_activation_request_replays_original_response():
    product_id = uuid4()
    request = QSealActivationRequest(
        request_hash="a" * 64,
        status="completed",
        response_payload={
            "message": "QR codes activated successfully",
            "product_id": str(product_id),
            "activated_count": 1,
        },
    )

    replay = QSealActivationService(None)._existing_idempotent_response(
        request, "a" * 64
    )

    assert replay["product_id"] == product_id
    assert replay["activated_count"] == 1


def test_activation_request_rejects_same_key_with_different_payload():
    request = QSealActivationRequest(
        request_hash="a" * 64,
        status="completed",
        response_payload={"message": "ok"},
    )

    with pytest.raises(HTTPException) as error:
        QSealActivationService(None)._existing_idempotent_response(
            request, "b" * 64
        )

    assert error.value.status_code == 409
    assert error.value.detail["code"] == "IDEMPOTENCY_KEY_REUSED"
