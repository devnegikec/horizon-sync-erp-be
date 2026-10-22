"""Notification coverage for QSeal product lifecycle events."""

from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError

from app.models.base import NotificationType
from app.schemas.qr_product import QRProductCreate, QRProductUpdate
from app.services.qr_product_service import QRProductService


def _service() -> QRProductService:
    service = QRProductService.__new__(QRProductService)
    service.db = Mock()
    service.product_repo = Mock()
    service.product_setting_repo = Mock()
    return service


def _product(*, is_active: bool = True):
    return SimpleNamespace(
        id=uuid4(),
        organization_id=uuid4(),
        name="Test Product",
        is_active=is_active,
    )


def _assert_notification(notification_service, notification_type):
    kwargs = notification_service.create.call_args.kwargs
    assert kwargs["type"] == notification_type.value
    assert kwargs["entity_type"] == "qr_product"
    assert kwargs["entity_no"] == "Test Product"


def test_create_product_notifies_creator():
    service = _service()
    product = _product()
    shelf_life = SimpleNamespace(id=uuid4(), setting_type="shelf_life", is_active=True)
    serial_prefix = SimpleNamespace(
        id=uuid4(), setting_type="serial_prefix", is_active=True
    )
    service.product_setting_repo.get_by_id.side_effect = [shelf_life, serial_prefix]
    service.product_repo.create.return_value = product
    service._create_linked_item = Mock()

    with patch(
        "app.services.notification_service.NotificationService"
    ) as notification_cls:
        service.create_product(
            QRProductCreate(
                name=product.name,
                shelf_life_setting_id=shelf_life.id,
                serial_prefix_setting_id=serial_prefix.id,
            ),
            product.organization_id,
            uuid4(),
        )

    _assert_notification(notification_cls.return_value, NotificationType.PRODUCT_CREATED)


def test_update_product_notifies_creator():
    service = _service()
    product = _product()
    service.product_repo.get_by_id.return_value = product
    service.product_repo.update.return_value = product
    user_id = uuid4()

    with patch(
        "app.services.notification_service.NotificationService"
    ) as notification_cls:
        service.update_product(
            product.id,
            QRProductUpdate(name="Renamed Product"),
            product.organization_id,
            user_id,
        )

    _assert_notification(notification_cls.return_value, NotificationType.PRODUCT_UPDATED)
    assert notification_cls.return_value.create.call_args.kwargs["user_id"] == user_id


def test_deactivating_product_notifies_creator():
    service = _service()
    product = _product()
    service.product_repo.get_by_id.return_value = product
    service.product_repo.update.return_value = product

    with patch(
        "app.services.notification_service.NotificationService"
    ) as notification_cls:
        service.update_product(
            product.id,
            QRProductUpdate(is_active=False),
            product.organization_id,
            uuid4(),
        )

    _assert_notification(
        notification_cls.return_value, NotificationType.PRODUCT_DEACTIVATED
    )


def test_activating_product_notifies_creator():
    service = _service()
    product = _product(is_active=False)
    service.product_repo.get_by_id.return_value = product
    service.product_repo.update.return_value = product

    with patch(
        "app.services.notification_service.NotificationService"
    ) as notification_cls:
        service.update_product(
            product.id,
            QRProductUpdate(is_active=True),
            product.organization_id,
            uuid4(),
        )

    _assert_notification(
        notification_cls.return_value, NotificationType.PRODUCT_ACTIVATED
    )


def test_soft_delete_product_notifies_creator():
    service = _service()
    product = _product()
    service.product_repo.get_by_id.return_value = product
    service.product_repo.soft_delete.return_value = product

    with patch(
        "app.services.notification_service.NotificationService"
    ) as notification_cls:
        service.delete_product(product.id, product.organization_id, uuid4())

    _assert_notification(
        notification_cls.return_value, NotificationType.PRODUCT_DEACTIVATED
    )


def test_notification_database_failure_does_not_break_product_update():
    service = _service()
    product = _product()
    service.product_repo.get_by_id.return_value = product
    service.product_repo.update.return_value = product

    with patch(
        "app.services.notification_service.NotificationService"
    ) as notification_cls:
        notification_cls.return_value.create.side_effect = SQLAlchemyError(
            "notification enum is not migrated"
        )

        updated = service.update_product(
            product.id,
            QRProductUpdate(name="Renamed Product"),
            product.organization_id,
            uuid4(),
        )

    assert updated is product
    service.db.rollback.assert_called_once()


def test_update_product_converts_packaging_decimals_before_jsonb_update():
    service = _service()
    product = _product()
    service.product_repo.get_by_id.return_value = product
    service.product_repo.update.return_value = product
    service.db.query.return_value.filter.return_value.first.return_value = None

    service.update_product(
        product.id,
        QRProductUpdate(
            packaging_details={
                "unit_name": "Each",
                "conversion_factor": Decimal("1"),
                "length_mm": Decimal("10.5"),
            }
        ),
        product.organization_id,
        uuid4(),
    )

    update_data = service.product_repo.update.call_args.args[1]
    packaging = update_data["extra_data"]["packaging_details"]
    assert packaging["conversion_factor"] == 1.0
    assert packaging["length_mm"] == 10.5
