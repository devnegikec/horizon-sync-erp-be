"""Tests for organization-scoped QR product settings."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.qr_product_setting import QRProductSettingCreate, QRProductSettingUpdate
from app.services.qr_product_setting_service import QRProductSettingService


def make_service() -> QRProductSettingService:
    service = QRProductSettingService.__new__(QRProductSettingService)
    service.db = Mock()
    service.repo = Mock()
    return service


def test_serial_prefix_is_trimmed_and_normalized_before_create():
    service = make_service()
    service.repo.value_exists.return_value = False
    service.repo.create.side_effect = lambda payload: payload

    result = service.create(
        QRProductSettingCreate(
            setting_type="serial_prefix",
            value="  ph  ",
            label="Pharma",
        ),
        uuid4(),
        uuid4(),
    )

    assert result["value"] == "PH"
    service.repo.value_exists.assert_called_once_with("serial_prefix", "PH", result["organization_id"])


def test_duplicate_serial_prefix_returns_conflict():
    service = make_service()
    service.repo.value_exists.return_value = True

    with pytest.raises(HTTPException) as exc_info:
        service.create(
            QRProductSettingCreate(
                setting_type="serial_prefix",
                value="ph",
                label="Pharma duplicate",
            ),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Serial prefix 'PH' already exists for this organization."
    service.repo.create.assert_not_called()


def test_duplicate_serial_prefix_returns_conflict_on_update():
    service = make_service()
    setting = SimpleNamespace(id=uuid4(), setting_type="serial_prefix", value="PH")
    service.repo.get_by_id.return_value = setting
    service.repo.value_exists.return_value = True

    with pytest.raises(HTTPException) as exc_info:
        service.update_setting(
            setting.id,
            QRProductSettingUpdate(value="ph"),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Serial prefix 'PH' already exists for this organization."
    service.repo.update.assert_not_called()


@pytest.mark.parametrize(
    ("setting_type", "value", "expected_detail"),
    [
        ("channel", "Retail", "Channel 'Retail' already exists for this organization."),
        (
            "destination",
            "India",
            "Destination 'India' already exists for this organization.",
        ),
        (
            "shelf_life",
            "24 months",
            "Shelf life value '24 months' already exists for this organization.",
        ),
    ],
)
def test_duplicate_lookup_settings_return_conflict(
    setting_type: str, value: str, expected_detail: str
):
    service = make_service()
    service.repo.value_exists.return_value = True

    with pytest.raises(HTTPException) as exc_info:
        service.create(
            QRProductSettingCreate(
                setting_type=setting_type,
                value=f"  {value}  ",
                label="Duplicate setting",
            ),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == expected_detail
    service.repo.create.assert_not_called()
