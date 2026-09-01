"""Tests for Product-owned serial configuration."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.qr_product import QRBlockCreate, QRProductCreate, QRProductUpdate
from app.services.qr_product_service import QRProductService


def make_service() -> QRProductService:
    service = QRProductService.__new__(QRProductService)
    service.db = Mock()
    service.db.query.return_value.join.return_value.filter.return_value.all.return_value = []
    service.product_repo = Mock()
    service.product_setting_repo = Mock()
    service.block_repo = Mock()
    service.item_repo = Mock()
    service.sku_repo = Mock()
    service.credit_service = Mock()
    service.key_service = None
    return service


def setting(setting_type: str, *, active: bool = True):
    return SimpleNamespace(
        id=uuid4(),
        setting_type=setting_type,
        is_active=active,
        value="PH" if setting_type == "serial_prefix" else "12",
    )


def test_create_product_persists_tenant_scoped_serial_prefix_reference():
    service = make_service()
    organization_id = uuid4()
    shelf_life = setting("shelf_life")
    serial_prefix = setting("serial_prefix")
    service.product_setting_repo.get_by_id.side_effect = [
        shelf_life,
        serial_prefix,
    ]
    service.product_repo.create.side_effect = lambda payload: payload

    result = service.create_product(
        QRProductCreate(
            name="Test Product",
            shelf_life_setting_id=shelf_life.id,
            serial_prefix_setting_id=serial_prefix.id,
            sr_number_type="R8DAN",
        ),
        organization_id,
        uuid4(),
    )

    assert result["serial_prefix_setting_id"] == serial_prefix.id
    assert result["sr_number_type"] == "R8DAN"
    assert service.product_setting_repo.get_by_id.call_args_list[1].args == (
        serial_prefix.id,
        organization_id,
    )


@pytest.mark.parametrize(
    ("selected_setting", "status_code", "detail"),
    [
        (None, 404, "Serial prefix setting not found"),
        (
            setting("channel"),
            422,
            "Selected setting is not a serial prefix setting",
        ),
        (
            setting("serial_prefix", active=False),
            422,
            "Selected serial prefix setting is inactive",
        ),
    ],
)
def test_create_product_rejects_invalid_serial_prefix(
    selected_setting, status_code, detail
):
    service = make_service()
    shelf_life = setting("shelf_life")
    service.product_setting_repo.get_by_id.side_effect = [
        shelf_life,
        selected_setting,
    ]

    with pytest.raises(HTTPException) as exc_info:
        service.create_product(
            QRProductCreate(
                name="Test Product",
                shelf_life_setting_id=shelf_life.id,
                serial_prefix_setting_id=uuid4(),
            ),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == status_code
    assert exc_info.value.detail == detail
    service.product_repo.create.assert_not_called()


def test_update_product_rejects_clearing_serial_prefix():
    service = make_service()
    product = SimpleNamespace(id=uuid4(), serial_prefix_setting_id=uuid4())
    service.product_repo.get_by_id.return_value = product

    with pytest.raises(HTTPException) as exc_info:
        service.update_product(
            product.id,
            QRProductUpdate(serial_prefix_setting_id=None),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "Serial prefix setting is required"


def test_block_uses_product_serial_configuration_not_request_overrides():
    service = make_service()
    organization_id = uuid4()
    product = SimpleNamespace(
        id=uuid4(),
        qr_type="dynamic",
        sr_number_type="R8DAN",
        serial_prefix="PH",
    )
    service.product_repo.get_by_id.return_value = product
    service.block_repo.batch_exists.return_value = False
    service.block_repo.create.side_effect = lambda payload, commit=False: (
        SimpleNamespace(id=uuid4(), **payload)
    )
    block = service.create_block_job(
        product.id,
        QRBlockCreate(
            batch="BATCH-001",
            quantity=2,
            serial_prefix="CLIENT",
            sr_number_type="R6DAN",
        ),
        organization_id,
        uuid4(),
    )

    assert block.serial_prefix == "PH"
    assert block.sr_number_type == "R8DAN"


def test_block_rejects_product_without_serial_prefix():
    service = make_service()
    product = SimpleNamespace(
        id=uuid4(),
        qr_type="dynamic",
        sr_number_type="R8DAN",
        serial_prefix=None,
    )
    service.product_repo.get_by_id.return_value = product
    service.block_repo.batch_exists.return_value = False

    with pytest.raises(HTTPException) as exc_info:
        service.generate_block(
            product.id,
            QRBlockCreate(batch="BATCH-001", quantity=1),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 422
    assert "serial prefix is not configured" in exc_info.value.detail
