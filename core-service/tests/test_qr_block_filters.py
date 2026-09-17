"""Tests for server-side QR Block list filters."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.repositories.qr_product_repository import QRBlockRepository
from app.services.qr_product_service import QRProductService


def make_service() -> QRProductService:
    service = QRProductService.__new__(QRProductService)
    service.block_repo = Mock()
    service.block_repo.list_by_org.return_value = ([], 0)
    return service


def test_service_passes_all_filters_with_authenticated_organization():
    service = make_service()
    organization_id = uuid4()
    product_id = uuid4()
    created_from = datetime(2026, 8, 1, tzinfo=UTC)
    created_to = datetime(2026, 8, 5, tzinfo=UTC)

    service.list_blocks_by_org(
        organization_id,
        page=2,
        page_size=20,
        block_status="completed",
        product_id=product_id,
        search="  AUG  ",
        qr_type="dynamic",
        created_from=created_from,
        created_to=created_to,
    )

    service.block_repo.list_by_org.assert_called_once_with(
        organization_id,
        2,
        20,
        "completed",
        product_id,
        "AUG",
        "dynamic",
        created_from,
        created_to,
    )


@pytest.mark.parametrize(
    ("created_from", "created_to", "message"),
    [
        (
            datetime(2026, 8, 5, tzinfo=UTC),
            datetime(2026, 8, 1, tzinfo=UTC),
            "earlier than",
        ),
        (
            datetime(2026, 8, 1),
            datetime(2026, 8, 5, tzinfo=UTC),
            "timezone offset",
        ),
    ],
)
def test_service_rejects_invalid_date_ranges(created_from, created_to, message):
    service = make_service()

    with pytest.raises(HTTPException) as exc_info:
        service.list_blocks_by_org(
            uuid4(), created_from=created_from, created_to=created_to
        )

    assert exc_info.value.status_code == 422
    assert message in exc_info.value.detail
    service.block_repo.list_by_org.assert_not_called()


def test_repository_combines_filters_and_keeps_tenant_boundary():
    db = Mock()
    query = db.query.return_value
    query.options.return_value = query
    query.outerjoin.return_value = query
    query.filter.return_value = query
    query.count.return_value = 0
    query.order_by.return_value = query
    query.offset.return_value = query
    query.limit.return_value = query
    query.all.return_value = []
    repository = QRBlockRepository(db)
    organization_id = uuid4()
    product_id = uuid4()
    created_from = datetime(2026, 8, 1, tzinfo=UTC)
    created_to = created_from + timedelta(days=4)

    rows, total = repository.list_by_org(
        organization_id,
        page=1,
        page_size=20,
        status="completed",
        product_id=product_id,
        search="AUG",
        qr_type="dual",
        created_from=created_from,
        created_to=created_to,
    )

    assert rows == []
    assert total == 0
    expressions = [
        str(expression)
        for call in query.filter.call_args_list
        for expression in call.args
    ]
    assert any("qr_blocks.organization_id" in expression for expression in expressions)
    assert any("qr_blocks.deleted_at" in expression for expression in expressions)
    assert any("qr_blocks.product_id" in expression for expression in expressions)
    assert any("lower(qr_blocks.batch) LIKE lower" in expression for expression in expressions)
    assert any("lower(qr_products.name) LIKE lower" in expression for expression in expressions)
    assert any("qr_blocks.qr_type" in expression for expression in expressions)
    assert any("qr_blocks.created_at >=" in expression for expression in expressions)
    assert any("qr_blocks.created_at <" in expression for expression in expressions)


def test_filtered_pagination_uses_filtered_total():
    service = make_service()
    service.block_repo.list_by_org.return_value = ([], 21)

    _, pagination = service.list_blocks_by_org(
        uuid4(), page=2, page_size=20, search="AUG"
    )

    assert pagination == {
        "page": 2,
        "page_size": 20,
        "total_items": 21,
        "total_pages": 2,
        "has_next": False,
        "has_prev": True,
    }
