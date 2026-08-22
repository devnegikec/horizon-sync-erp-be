"""Phase 2 tests for Organization credits and Block setting metadata."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.qr_product import QRBlockCreate
from app.services.qr_product_service import QRProductService


def make_service() -> QRProductService:
    service = QRProductService.__new__(QRProductService)
    service.db = Mock()
    service.product_repo = Mock()
    service.product_setting_repo = Mock()
    service.block_repo = Mock()
    service.item_repo = Mock()
    service.sku_repo = Mock()
    service.credit_service = Mock()
    service.key_service = None
    return service


def product():
    return SimpleNamespace(
        id=uuid4(),
        qr_type="dynamic",
        sr_number_type="R8DAN",
        serial_prefix="PH",
    )


def setting(setting_type: str):
    return SimpleNamespace(
        id=uuid4(),
        setting_type=setting_type,
        is_active=True,
    )


def test_block_persists_organization_scoped_channel_and_destination():
    service = make_service()
    organization_id = uuid4()
    selected_product = product()
    channel = setting("channel")
    destination = setting("destination")
    service.product_repo.get_by_id.return_value = selected_product
    service.product_setting_repo.get_by_id.side_effect = [channel, destination]
    service.block_repo.batch_exists.return_value = False
    service.block_repo.create.side_effect = lambda payload, **_: SimpleNamespace(
        id=uuid4(), **payload
    )
    service._generate_product_items = Mock(return_value=[])
    service.block_repo.get_by_id.return_value = None

    block = service.generate_block(
        selected_product.id,
        QRBlockCreate(
            batch="BATCH-PHASE2",
            quantity=10,
            channel_setting_id=channel.id,
            destination_setting_id=destination.id,
        ),
        organization_id,
        uuid4(),
    )

    assert block.channel_setting_id == channel.id
    assert block.destination_setting_id == destination.id
    assert service.product_setting_repo.get_by_id.call_args_list[0].args == (
        channel.id,
        organization_id,
    )
    service.credit_service.check_balance.assert_called_once_with(
        organization_id, 10
    )
    service.credit_service.reserve_credits.assert_called_once_with(
        organization_id,
        block.id,
        10,
        commit=False,
    )
    service.credit_service.consume_reserved_credits.assert_called_once()


def test_block_rejects_setting_outside_authenticated_organization():
    service = make_service()
    selected_product = product()
    service.product_repo.get_by_id.return_value = selected_product
    service.product_setting_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        service.generate_block(
            selected_product.id,
            QRBlockCreate(
                batch="BATCH-PHASE2",
                quantity=1,
                channel_setting_id=uuid4(),
            ),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 404
    service.block_repo.create.assert_not_called()
    service.credit_service.check_balance.assert_not_called()


def test_block_rejects_insufficient_organization_credits_before_creation():
    service = make_service()
    selected_product = product()
    service.product_repo.get_by_id.return_value = selected_product
    service.block_repo.batch_exists.return_value = False
    service.credit_service.check_balance.side_effect = HTTPException(
        status_code=422,
        detail="Insufficient credits: available=5, required=10",
    )

    with pytest.raises(HTTPException) as exc_info:
        service.generate_block(
            selected_product.id,
            QRBlockCreate(batch="BATCH-PHASE2", quantity=10),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 422
    service.block_repo.create.assert_not_called()
