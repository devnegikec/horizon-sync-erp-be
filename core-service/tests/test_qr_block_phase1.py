"""Phase 1 tests for QR block contracts and generation integrity."""

from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from app.schemas.qr_product import (
    QRBlockCreate,
    QRType,
    SerialNumberType,
)
from app.services.qr_product_service import QRProductService


def make_service() -> QRProductService:
    service = QRProductService.__new__(QRProductService)
    service.db = Mock()
    service.db.query.return_value.join.return_value.filter.return_value.all.return_value = []
    service.product_repo = Mock()
    service.block_repo = Mock()
    service.item_repo = Mock()
    service.sku_repo = Mock()
    service.credit_service = Mock()
    service.key_service = None
    return service


@pytest.mark.parametrize(
    ("legacy_value", "expected"),
    [
        ("D", QRType.DYNAMIC),
        ("C", QRType.DYNAMIC),
        ("S", QRType.STATIC),
        ("B", QRType.DUAL),
        ("SC", QRType.SECURE_CODE),
        ("O", QRType.ONE_TIME),
        ("N", QRType.POST_ACTIVATION),
    ],
)
def test_block_schema_normalizes_legacy_qr_types(legacy_value, expected):
    data = QRBlockCreate(
        batch="BATCH-001",
        quantity=1,
        qr_type=legacy_value,
    )
    assert data.qr_type == expected


def test_block_schema_limits_quantity_to_5000():
    with pytest.raises(ValidationError, match="less than or equal to 5000"):
        QRBlockCreate(batch="BATCH-001", quantity=5001)


def test_static_block_requires_quantity_one():
    with pytest.raises(
        ValidationError, match="Static QR generation requires quantity=1"
    ):
        QRBlockCreate(batch="STATIC-001", quantity=2, qr_type="static")


@pytest.mark.parametrize(
    ("serial_type", "starting_serial", "message"),
    [
        ("S8DN", None, "starting_serial is required"),
        ("S8DN", "ABC", "digits only"),
        ("S8DN", "123456789", "at most 8 digits"),
        ("S10DN", "12345678901", "at most 10 digits"),
    ],
)
def test_sequential_starting_serial_validation(serial_type, starting_serial, message):
    with pytest.raises(ValidationError, match=message):
        QRBlockCreate(
            batch="BATCH-001",
            quantity=1,
            sr_number_type=serial_type,
            starting_serial=starting_serial,
        )


def test_generate_block_rejects_duplicate_batch_in_same_organization():
    service = make_service()
    organization_id = uuid4()
    product = SimpleNamespace(
        id=uuid4(),
        qr_type="D",
        sr_number_type="R6DAN",
        serial_prefix="MODEL",
    )
    service.product_repo.get_by_id.return_value = product
    service.block_repo.batch_exists.return_value = True

    with pytest.raises(HTTPException) as exc_info:
        service.generate_block(
            product.id,
            QRBlockCreate(batch="Existing", quantity=1),
            organization_id,
            uuid4(),
        )

    assert exc_info.value.status_code == 409
    service.block_repo.batch_exists.assert_called_once_with("Existing", organization_id)
    service.block_repo.create.assert_not_called()


def test_generate_block_rejects_sku_from_another_product_or_tenant():
    service = make_service()
    product = SimpleNamespace(
        id=uuid4(),
        qr_type="D",
        sr_number_type="R6DAN",
        serial_prefix="MODEL",
    )
    sku_id = uuid4()
    organization_id = uuid4()
    service.product_repo.get_by_id.return_value = product
    service.block_repo.batch_exists.return_value = False
    service.sku_repo.get_by_id.return_value = None

    with pytest.raises(HTTPException) as exc_info:
        service.generate_block(
            product.id,
            QRBlockCreate(
                batch="BATCH-001",
                quantity=1,
                sku_id=sku_id,
            ),
            organization_id,
            uuid4(),
        )

    assert exc_info.value.status_code == 404
    service.sku_repo.get_by_id.assert_called_once_with(sku_id, organization_id)
    service.block_repo.create.assert_not_called()


def test_generate_block_maps_batch_uniqueness_race_to_conflict():
    service = make_service()
    product = SimpleNamespace(
        id=uuid4(),
        qr_type="D",
        sr_number_type="R6DAN",
        serial_prefix="MODEL",
    )
    service.product_repo.get_by_id.return_value = product
    service.block_repo.batch_exists.return_value = False
    service.block_repo.create.side_effect = IntegrityError(
        "insert", {}, Exception("unique violation")
    )

    with pytest.raises(HTTPException) as exc_info:
        service.generate_block(
            product.id,
            QRBlockCreate(batch="BATCH-001", quantity=1),
            uuid4(),
            uuid4(),
        )

    assert exc_info.value.status_code == 409
    service.db.rollback.assert_called_once()


def test_create_block_rejects_duplicate_serials_before_reserving_credits():
    service = make_service()
    organization_id = uuid4()
    product = SimpleNamespace(
        id=uuid4(),
        qr_type="dynamic",
        sr_number_type="S8DN",
        serial_prefix="PH",
    )
    service.product_repo.get_by_id.return_value = product
    service.block_repo.batch_exists.return_value = False
    service.item_repo.get_existing_serials_global.return_value = {
        "PH-00000100",
        "PH-00000101",
    }

    with pytest.raises(HTTPException) as exc_info:
        service.create_block_job(
            product.id,
            QRBlockCreate(
                batch="AUG-short-2",
                quantity=2,
                starting_serial="100",
            ),
            organization_id,
            uuid4(),
        )

    assert exc_info.value.status_code == 409
    assert "PH-00000100" in exc_info.value.detail
    service.item_repo.get_existing_serials_global.assert_called_once_with(
        ["PH-00000100", "PH-00000101"],
    )
    service.credit_service.check_balance.assert_not_called()
    service.credit_service.reserve_credits.assert_not_called()
    service.block_repo.create.assert_not_called()


def test_generate_block_persists_failed_status_after_generation_error():
    service = make_service()
    organization_id = uuid4()
    product = SimpleNamespace(
        id=uuid4(),
        qr_type="D",
        sr_number_type="R6DAN",
        serial_prefix="MODEL",
    )
    block = SimpleNamespace(
        id=uuid4(),
        status="pending",
        task_status="pending",
        error_code=None,
        error_message=None,
    )
    service.product_repo.get_by_id.return_value = product
    service.block_repo.batch_exists.return_value = False
    service.block_repo.create.return_value = block
    service.block_repo.get_by_id.return_value = block
    service._generate_product_items = Mock(
        side_effect=RuntimeError("generation failed")
    )

    with pytest.raises(RuntimeError, match="generation failed"):
        service.generate_block(
            product.id,
            QRBlockCreate(batch="BATCH-001", quantity=1),
            organization_id,
            uuid4(),
        )

    assert block.status == "failed"
    assert block.task_status == "failed"
    assert block.error_code == "generation_failed"
    assert block.error_message == "QR block generation failed"
    service.db.rollback.assert_called_once()
    service.block_repo.get_by_id.assert_called_once_with(block.id, organization_id)


def test_product_items_use_starting_serial_prefix_and_sku():
    service = make_service()
    organization_id = uuid4()
    sku_id = uuid4()
    block = SimpleNamespace(
        id=uuid4(),
        product_id=uuid4(),
        sku_id=sku_id,
        quantity=3,
        batch="BATCH-001",
        qr_type="dynamic",
        sr_number_type="S8DN",
        starting_serial="42",
        serial_prefix="MODEL",
    )
    product = SimpleNamespace(
        brand_id=None,
        gtin="012345678901",
        sr_number_type="R6DAN",
        activation_method="pre",
    )
    service.item_repo.get_existing_serials_global.return_value = set()

    service._generate_product_items(
        block,
        product,
        organization_id,
        uuid4(),
    )

    items = service.item_repo.bulk_create.call_args.args[0]
    assert [item["serial_number"] for item in items] == [
        "MODEL-00000042",
        "MODEL-00000043",
        "MODEL-00000044",
    ]
    assert {item["sku_id"] for item in items} == {sku_id}
    service.item_repo.get_existing_serials_global.assert_called_once()


def test_static_generation_creates_one_batch_serial():
    service = make_service()
    block = SimpleNamespace(
        id=uuid4(),
        product_id=uuid4(),
        sku_id=None,
        quantity=1,
        batch="STATIC-001",
        qr_type="static",
        sr_number_type="S8DN",
        starting_serial=None,
        serial_prefix="MODEL",
    )
    product = SimpleNamespace(
        brand_id=None,
        gtin="012345678901",
        sr_number_type="S8DN",
        activation_method="pre",
    )
    service.item_repo.get_existing_serials_global.return_value = set()

    service._generate_product_items(block, product, uuid4(), uuid4())

    items = service.item_repo.bulk_create.call_args.args[0]
    assert len(items) == 1
    assert items[0]["serial_number"] == "MODEL-STATIC-001"


def test_sequential_generation_rejects_existing_serial_range():
    service = make_service()
    block = SimpleNamespace(
        id=uuid4(),
        product_id=uuid4(),
        sku_id=None,
        quantity=2,
        batch="BATCH-001",
        qr_type="dynamic",
        sr_number_type=SerialNumberType.S8DN.value,
        starting_serial="1",
        serial_prefix="MODEL",
    )
    product = SimpleNamespace(
        brand_id=None,
        gtin="012345678901",
        sr_number_type="S8DN",
        activation_method="pre",
    )
    service.item_repo.get_existing_serials_global.return_value = {"MODEL-00000001"}

    with pytest.raises(HTTPException) as exc_info:
        service._generate_product_items(block, product, uuid4(), uuid4())

    assert exc_info.value.status_code == 409
    service.item_repo.bulk_create.assert_not_called()
