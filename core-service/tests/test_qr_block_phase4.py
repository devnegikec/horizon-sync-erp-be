"""Phase 4 tests for queued QR generation and tenant-safe retries."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

from fastapi.routing import APIRoute

from app.api.v1.endpoints.qr_products import router
from app.repositories.credit_repository import CreditRepository
from app.services import qr_block_queue
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


def block(status: str = "pending") -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        organization_id=uuid4(),
        product_id=uuid4(),
        created_by=uuid4(),
        status=status,
        task_status=status,
        task_id="current-task",
        quantity=3,
        progress=0,
        generated_count=0,
        completed_at=None,
        error_code=None,
        error_message=None,
        artifact_object_key=None,
        artifact_size_bytes=None,
        artifact_checksum_sha256=None,
        artifact_generated_at=None,
    )


def test_worker_ignores_a_stale_task_id():
    service = make_service()
    queued_block = block()
    service.block_repo.get_by_id_for_update.return_value = queued_block
    service._generate_product_items = Mock()

    result = service.process_block(
        queued_block.id,
        queued_block.organization_id,
        task_id="stale-task",
    )

    assert result is queued_block
    service.product_repo.get_by_id.assert_not_called()
    service._generate_product_items.assert_not_called()


def test_worker_completes_block_and_consumes_its_reservation():
    service = make_service()
    queued_block = block()
    product = SimpleNamespace(id=queued_block.product_id)
    service.block_repo.get_by_id_for_update.return_value = queued_block
    service.block_repo.get_by_id.return_value = queued_block
    service.product_repo.get_by_id.return_value = product
    service._generate_product_items = Mock(return_value=[{}, {}, {}])
    service._store_block_artifact = Mock(return_value="tenant/block.xlsx")

    result = service.process_block(
        queued_block.id,
        queued_block.organization_id,
        task_id="current-task",
    )

    assert result.status == "completed"
    assert result.task_status == "completed"
    assert result.progress == 100
    assert result.generated_count == 3
    service.credit_service.consume_reserved_credits.assert_called_once_with(
        queued_block.organization_id,
        queued_block.id,
        queued_block.created_by,
    )


def test_retry_lookup_and_credit_reservation_are_tenant_scoped():
    service = make_service()
    failed_block = block("failed")
    service.block_repo.get_by_id_for_update.return_value = failed_block

    result = service.retry_block_job(
        failed_block.id,
        failed_block.organization_id,
    )

    service.block_repo.get_by_id_for_update.assert_called_once_with(
        failed_block.id,
        failed_block.organization_id,
    )
    service.credit_service.reserve_credits.assert_called_once_with(
        failed_block.organization_id,
        failed_block.id,
        failed_block.quantity,
        commit=False,
    )
    assert result.status == "pending"
    assert result.task_id is None


def test_credit_reservation_query_is_organization_scoped():
    db = Mock()
    query = db.query.return_value
    query.filter.return_value = query
    query.first.return_value = None
    organization_id = uuid4()
    block_id = uuid4()

    CreditRepository(db).get_reservation_by_block(
        block_id,
        organization_id,
    )

    filters = query.filter.call_args.args
    assert any(
        "qr_credit_reservations.block_id" in str(expression)
        for expression in filters
    )
    assert any(
        "qr_credit_reservations.organization_id" in str(expression)
        for expression in filters
    )


def test_generation_and_retry_endpoints_return_accepted():
    routes = {
        route.path: route
        for route in router.routes
        if isinstance(route, APIRoute) and "POST" in route.methods
    }

    assert routes["/{product_id}/blocks"].status_code == 202
    assert routes["/blocks/{block_id}/retry"].status_code == 202


def test_queue_adapter_uses_durable_task_identity(monkeypatch):
    apply_async = Mock()
    monkeypatch.setattr(
        qr_block_queue.generate_qr_block_task,
        "apply_async",
        apply_async,
    )
    block_id = uuid4()
    organization_id = uuid4()

    qr_block_queue.enqueue_qr_block(
        block_id,
        organization_id,
        "task-123",
    )

    apply_async.assert_called_once_with(
        args=[str(block_id), str(organization_id)],
        task_id="task-123",
        queue="qr-generation",
    )


def test_credit_reservation_migration_has_required_tenant_contracts():
    migration = Path(
        "alembic/versions/046_add_qr_credit_reservations.py"
    ).read_text()

    assert '"reserved_credits"' in migration
    assert '"qr_credit_reservations"' in migration
    assert '"organization_id"' in migration
    assert '"block_id"' in migration
    assert "uq_qr_credit_reservations_block" in migration
