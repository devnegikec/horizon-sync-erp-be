"""Tests for the QR Product Shelf Life setting reference."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.schemas.qr_product import QRProductCreate, QRProductUpdate
from app.services.qr_product_service import QRProductService
from app.services.qr_product_setting_service import QRProductSettingService


def make_product_service() -> QRProductService:
    service = QRProductService.__new__(QRProductService)
    service.product_repo = Mock()
    service.product_setting_repo = Mock()
    return service


def shelf_life_setting(*, active: bool = True):
    return SimpleNamespace(
        id=uuid4(),
        setting_type="shelf_life",
        is_active=active,
    )


def serial_prefix_setting():
    return SimpleNamespace(
        id=uuid4(),
        setting_type="serial_prefix",
        is_active=True,
    )


def test_create_schema_requires_shelf_life_setting_id():
    with pytest.raises(ValidationError):
        QRProductCreate(name="Test Product")


def test_create_product_persists_shelf_life_setting_reference():
    service = make_product_service()
    organization_id = uuid4()
    user_id = uuid4()
    setting = shelf_life_setting()
    prefix = serial_prefix_setting()
    service.product_setting_repo.get_by_id.side_effect = [setting, prefix]
    service.product_repo.create.side_effect = lambda payload: payload

    result = service.create_product(
        QRProductCreate(
            name="Test Product",
            shelf_life_setting_id=setting.id,
            serial_prefix_setting_id=prefix.id,
        ),
        organization_id,
        user_id,
    )

    assert result["shelf_life_setting_id"] == setting.id
    assert service.product_setting_repo.get_by_id.call_args_list[0].args == (
        setting.id,
        organization_id,
    )


@pytest.mark.parametrize(
    ("setting", "expected_status", "expected_detail"),
    [
        (None, 404, "Shelf life setting not found"),
        (
            SimpleNamespace(
                id=uuid4(),
                setting_type="channel",
                is_active=True,
            ),
            422,
            "Selected setting is not a shelf life setting",
        ),
        (
            shelf_life_setting(active=False),
            422,
            "Selected shelf life setting is inactive",
        ),
    ],
)
def test_create_product_rejects_invalid_shelf_life_setting(
    setting, expected_status, expected_detail
):
    service = make_product_service()
    service.product_setting_repo.get_by_id.return_value = setting

    with pytest.raises(HTTPException) as exc_info:
        service.create_product(
            QRProductCreate(
                name="Test Product",
                shelf_life_setting_id=uuid4(),
                serial_prefix_setting_id=uuid4(),
            ),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == expected_status
    assert exc_info.value.detail == expected_detail
    service.product_repo.create.assert_not_called()


def test_setting_lookup_is_scoped_to_authenticated_organization():
    service = make_product_service()
    setting_id = uuid4()
    authenticated_organization_id = uuid4()
    service.product_setting_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        service.create_product(
            QRProductCreate(
                name="Test Product",
                shelf_life_setting_id=setting_id,
                serial_prefix_setting_id=uuid4(),
            ),
            authenticated_organization_id,
            uuid4(),
        )

    assert exc_info.value.status_code == 404
    service.product_setting_repo.get_by_id.assert_called_once_with(
        setting_id, authenticated_organization_id
    )


def test_update_product_validates_and_changes_shelf_life_setting():
    service = make_product_service()
    product = SimpleNamespace(id=uuid4())
    organization_id = uuid4()
    setting = shelf_life_setting()
    service.product_repo.get_by_id.return_value = product
    service.product_setting_repo.get_by_id.return_value = setting
    service.product_repo.update.side_effect = lambda product, payload: payload

    result = service.update_product(
        product.id,
        QRProductUpdate(shelf_life_setting_id=setting.id),
        organization_id,
        uuid4(),
    )

    assert result["shelf_life_setting_id"] == setting.id
    service.product_setting_repo.get_by_id.assert_called_once_with(
        setting.id, organization_id
    )


def test_update_product_rejects_clearing_shelf_life_setting():
    service = make_product_service()
    product = SimpleNamespace(id=uuid4())
    service.product_repo.get_by_id.return_value = product

    with pytest.raises(HTTPException) as exc_info:
        service.update_product(
            product.id,
            QRProductUpdate(shelf_life_setting_id=None),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Shelf life setting is required"
    service.product_repo.update.assert_not_called()


def test_update_product_preserves_its_existing_inactive_shelf_life_setting():
    service = make_product_service()
    setting = shelf_life_setting(active=False)
    product = SimpleNamespace(
        id=uuid4(),
        shelf_life_setting_id=setting.id,
    )
    service.product_repo.get_by_id.return_value = product
    service.product_setting_repo.get_by_id.return_value = setting
    service.product_repo.update.side_effect = lambda product, payload: payload

    result = service.update_product(
        product.id,
        QRProductUpdate(shelf_life_setting_id=setting.id),
        uuid4(),
        uuid4(),
    )

    assert result["shelf_life_setting_id"] == setting.id


def test_referenced_setting_cannot_be_deleted():
    service = QRProductSettingService.__new__(QRProductSettingService)
    service.repo = Mock()
    setting = shelf_life_setting()
    organization_id = uuid4()
    service.repo.get_by_id.return_value = setting
    service.repo.is_referenced_by_product.return_value = True

    with pytest.raises(HTTPException) as exc_info:
        service.delete_setting(
            setting.id,
            organization_id,
            uuid4(),
        )

    assert exc_info.value.status_code == 409
    service.repo.soft_delete.assert_not_called()
