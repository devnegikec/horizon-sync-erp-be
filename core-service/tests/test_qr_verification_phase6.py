"""Phase 6 tests for public QR-type verification without scan analytics."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.api.v1.endpoints.public_qr import router as public_qr_router
from app.repositories.qr_product_repository import ProductItemRepository
from app.repositories.qr_verification_repository import QRVerificationRepository
from app.schemas.qr_verification import (
    PublicQRVerifyRequest,
    PublicQRVerifyResponse,
)
from app.services.qr_verification_service import QRVerificationService


def _request(**overrides) -> PublicQRVerifyRequest:
    values = {
        "gtin": "0123456789012",
        "serial_number": "PRO-ABC12345",
        "timestamp": "1770000000000",
        "signature": "signed-value",
    }
    values.update(overrides)
    return PublicQRVerifyRequest(**values)


def _item(*, qr_type="dynamic", active=True, scans=0):
    organization_id = uuid4()
    brand = SimpleNamespace(
        organization_id=organization_id,
        deleted_at=None,
        public_key="public-key",
        name="Demo Brand",
    )
    product = SimpleNamespace(
        organization_id=organization_id,
        deleted_at=None,
        is_active=True,
        brand=brand,
        gtin=None,
        qr_type=qr_type,
        activation_method="pre" if active else "post",
        name="Demo Product",
        generic_name="Demo Generic",
        industry="Consumer Goods",
        warranty_period_months=12,
        image_url="https://images.example/logo.png",
        banner_image_url="https://images.example/banner.png",
        email="support@example.com",
        phone_number="+91 9999999999",
        landing_page="https://example.com/product",
    )
    sku = SimpleNamespace(
        organization_id=organization_id,
        gtin="0123456789012",
        image_url="https://images.example/sku.png",
        name="Blue / Large",
        sku_code="DEMO-BLU-L",
        warranty_period_months=18,
        attribute_display={"Colour": "Blue", "Size": "Large"},
    )
    block = SimpleNamespace(
        organization_id=organization_id,
        qr_type=qr_type,
    )
    return SimpleNamespace(
        id=uuid4(),
        organization_id=organization_id,
        serial_number="PRO-ABC12345",
        secrete_code="A1B2C3D4E5F6",
        product=product,
        sku=sku,
        block=block,
        qr_active=active,
        qr_deactive=not active,
        qr_deactive_unit=not active,
        scan_count=scans,
        scans=scans,
        is_auth=False,
        is_verify=False,
        is_suspicious=False,
    )


def _service(item) -> QRVerificationService:
    service = QRVerificationService.__new__(QRVerificationService)
    service.db = Mock()
    service.repo = Mock(spec=QRVerificationRepository)
    service.key_service = Mock()
    service.repo.resolve_active_item_identity.return_value = (
        item.id,
        item.organization_id,
    )
    service.repo.get_tenant_item_for_update.return_value = item
    service.key_service.verify_signature.return_value = True
    return service


def test_public_contract_rejects_tenant_and_analytics_fields():
    with pytest.raises(ValidationError, match="organization_id"):
        _request(organization_id=str(uuid4()))
    with pytest.raises(ValidationError, match="country"):
        _request(country="India")


def test_public_contract_restores_plus_corrupted_by_legacy_query_parsing():
    request = _request(signature="MEQC ABC/DEF=")

    assert request.signature == "MEQC+ABC/DEF="


def test_public_verify_route_has_no_auth_dependency():
    route = next(route for route in public_qr_router.routes if route.path == "/verify")
    dependency_names = {
        dependency.call.__name__
        for dependency in route.dependant.dependencies
        if dependency.call
    }
    assert dependency_names == {"get_db"}


def test_dynamic_verification_is_read_only_and_returns_enterprise_details():
    item = _item()
    service = _service(item)

    result = service.verify(_request())

    assert result["verification_status"] == "authentic"
    assert result["authentic"] is True
    assert result["logo_url"].endswith("logo.png")
    assert result["banner_image_url"].endswith("banner.png")
    assert result["variant_attributes"] == {"Colour": "Blue", "Size": "Large"}
    assert result["contact_email"] == "support@example.com"
    assert PublicQRVerifyResponse(**result).verification_status == "authentic"
    assert item.scan_count == 0
    assert item.is_auth is False
    service.db.commit.assert_not_called()
    service.db.rollback.assert_called_once()
    assert not hasattr(service.repo, "add_scan_event")


def test_dynamic_repeat_scan_is_still_authentic_without_counters():
    item = _item(scans=5)
    service = _service(item)

    result = service.verify(_request())

    assert result["verification_status"] == "authentic"
    assert item.scan_count == 5
    assert item.is_suspicious is False


def test_gtin_is_validated_from_sku_without_product_item_gtin():
    item = _item()
    service = _service(item)

    result = service.verify(_request(gtin="9999999999999"))

    assert result["verification_status"] == "invalid"
    service.key_service.verify_signature.assert_not_called()
    service.db.rollback.assert_called_once()


def test_invalid_signature_is_rejected_without_scan_capture():
    item = _item()
    service = _service(item)
    service.key_service.verify_signature.return_value = False

    result = service.verify(_request())

    assert result["verification_status"] == "invalid"
    assert item.scan_count == 0
    service.db.commit.assert_not_called()


def test_post_activation_item_is_genuine_but_not_activated():
    item = _item(active=False)
    service = _service(item)

    result = service.verify(_request())

    assert result["verification_status"] == "not_activated"
    assert result["authentic"] is True
    assert item.scan_count == 0


def test_dual_overt_qr_requests_protected_qr_scan():
    item = _item(qr_type="dual")
    service = _service(item)

    result = service.verify(_request(qr_channel="overt"))

    assert result["verification_status"] == "verification_required"
    assert result["requires_action"] is True
    assert result["challenge_type"] == "scan_covert"
    assert result["authentic"] is False


def test_dual_covert_qr_completes_verification():
    item = _item(qr_type="dual")
    service = _service(item)

    result = service.verify(_request(qr_channel="covert"))

    assert result["verification_status"] == "authentic"
    assert result["qr_channel"] == "covert"


def test_secure_code_requests_challenge_then_accepts_matching_code():
    item = _item(qr_type="secure_code")
    service = _service(item)

    challenge = service.verify(_request())
    verified = service.verify(_request(secure_code="a1b2c3d4e5f6"))

    assert challenge["verification_status"] == "verification_required"
    assert challenge["challenge_type"] == "secure_code"
    assert verified["verification_status"] == "authentic"


def test_secure_code_rejects_wrong_code():
    item = _item(qr_type="secure_code")
    service = _service(item)

    result = service.verify(_request(secure_code="WRONG-CODE"))

    assert result["verification_status"] == "invalid"
    assert "protected code" in result["message"]


def test_one_time_verification_persists_only_consumption_state():
    item = _item(qr_type="one_time")
    service = _service(item)

    result = service.verify(_request())

    assert result["verification_status"] == "authentic"
    assert item.qr_active is False
    assert item.qr_deactive is True
    assert item.qr_deactive_unit is True
    assert item.is_auth is True
    assert item.is_verify is True
    assert item.scan_count == 0
    service.db.commit.assert_called_once()


def test_used_one_time_item_returns_already_used_without_scan_increment():
    item = _item(qr_type="one_time", active=False)
    item.is_verify = True
    service = _service(item)

    result = service.verify(_request())

    assert result["verification_status"] == "already_used"
    assert result["authentic"] is False
    assert item.scan_count == 0


def test_cross_organization_relationship_is_rejected():
    item = _item()
    item.product.organization_id = uuid4()
    service = _service(item)

    result = service.verify(_request())

    assert result["verification_status"] == "invalid"
    service.db.rollback.assert_called_once()


def test_global_collision_query_does_not_accept_an_organization():
    db = Mock()
    query = db.query.return_value
    query.filter.return_value = query
    query.all.return_value = [("PRO-ABC12345",)]

    result = ProductItemRepository(db).get_existing_serials_global(
        ["PRO-ABC12345"]
    )

    assert result == {"PRO-ABC12345"}
    filters = query.filter.call_args.args
    assert not any("organization_id" in str(expression) for expression in filters)
    assert any("deleted_at" in str(expression) for expression in filters)


def test_repository_locks_the_resolved_item_inside_tenant_boundary():
    db = Mock()
    item_id = uuid4()
    organization_id = uuid4()
    query = db.query.return_value
    query.filter.return_value = query
    query.with_for_update.return_value = query
    query.first.return_value = object()

    QRVerificationRepository(db).get_tenant_item_for_update(
        item_id,
        "PRO-ABC12345",
        organization_id,
    )

    filters = query.filter.call_args.args
    assert any("product_items.organization_id" in str(value) for value in filters)
    assert any("product_items.serial_number" in str(value) for value in filters)
    query.with_for_update.assert_called_once_with()


migration_path = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "047_make_product_item_serial_global.py"
)
spec = importlib.util.spec_from_file_location("global_item_serial_migration", migration_path)
assert spec and spec.loader
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def test_global_serial_migration_replaces_tenant_unique_index(monkeypatch):
    bind = Mock()
    bind.execute.return_value.first.return_value = None
    drop_index = Mock()
    create_index = Mock()
    monkeypatch.setattr(migration.op, "get_bind", Mock(return_value=bind))
    monkeypatch.setattr(migration.op, "drop_index", drop_index)
    monkeypatch.setattr(migration.op, "create_index", create_index)

    migration.upgrade()

    drop_index.assert_called_once_with(
        "uq_product_items_org_serial_active",
        table_name="product_items",
    )
    assert create_index.call_args.args[:3] == (
        "uq_product_items_serial_active",
        "product_items",
        ["serial_number"],
    )
    assert create_index.call_args.kwargs["unique"] is True
    duplicate_sql = str(bind.execute.call_args.args[0])
    assert "GROUP BY serial_number" in duplicate_sql
    assert "organization_id" not in duplicate_sql


def test_global_serial_migration_stops_when_duplicates_exist(monkeypatch):
    bind = Mock()
    bind.execute.return_value.first.return_value = ("DUPLICATE",)
    create_index = Mock()
    monkeypatch.setattr(migration.op, "get_bind", Mock(return_value=bind))
    monkeypatch.setattr(migration.op, "create_index", create_index)

    with pytest.raises(RuntimeError, match="DUPLICATE"):
        migration.upgrade()

    create_index.assert_not_called()
