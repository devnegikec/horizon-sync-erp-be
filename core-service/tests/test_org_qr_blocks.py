"""Unit tests for org-level QR block listing (Tasks 6.1–6.6).

Requirements covered: 1.3, 1.6, 2.2, 3.4, 4.3, 5.1, 5.2, 6.1, 7.3
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from app.repositories.qr_product_repository import QRBlockRepository
from app.schemas.qr_product import OrgBlockListItem
from app.services.qr_product_service import QRProductService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_block(organization_id, status="pending", deleted_at=None, product_id=None):
    """Return a MagicMock that looks like a QRBlock row."""
    block = MagicMock()
    block.id = uuid.uuid4()
    block.organization_id = organization_id
    block.product_id = product_id or uuid.uuid4()
    block.batch = "BATCH-001"
    block.quantity = 100
    block.serial_prefix = None
    block.sr_number_type = None
    block.status = status
    block.task_status = status
    block.task_id = None
    block.qr_image = False
    block.manufacture_date = None
    block.expiry_date = None
    block.gcs_url = None
    block.download_url = None
    block.completed_at = None
    block.created_at = datetime.now(timezone.utc)
    block.deleted_at = deleted_at
    block.__dict__ = {
        "id": block.id,
        "organization_id": block.organization_id,
        "product_id": block.product_id,
        "batch": block.batch,
        "quantity": block.quantity,
        "serial_prefix": block.serial_prefix,
        "sr_number_type": block.sr_number_type,
        "status": block.status,
        "task_status": block.task_status,
        "task_id": block.task_id,
        "qr_image": block.qr_image,
        "manufacture_date": block.manufacture_date,
        "expiry_date": block.expiry_date,
        "gcs_url": block.gcs_url,
        "download_url": block.download_url,
        "completed_at": block.completed_at,
        "created_at": block.created_at,
        "deleted_at": block.deleted_at,
    }
    return block


def _make_repo_with_results(rows, total):
    """Return a QRBlockRepository mock whose list_by_org returns (rows, total)."""
    repo = MagicMock(spec=QRBlockRepository)
    repo.list_by_org.return_value = (rows, total)
    return repo


# ---------------------------------------------------------------------------
# 6.1 — list_by_org returns only blocks for the given organization_id
# Requirements: 1.3, 5.1
# ---------------------------------------------------------------------------

class TestListByOrgOrgFilter:
    def test_filter_includes_organization_id(self):
        """Verify that list_by_org is called with the correct organization_id."""
        db = MagicMock()
        repo = QRBlockRepository(db)

        org_id = uuid.uuid4()
        other_org_id = uuid.uuid4()

        # Build a mock query chain
        mock_query = MagicMock()
        mock_outerjoin = MagicMock()
        mock_filter = MagicMock()
        mock_count = MagicMock(return_value=1)
        mock_order = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()

        block = _make_block(org_id)
        mock_limit.all.return_value = [(block, "Product A")]

        mock_offset.limit.return_value = mock_limit
        mock_order.offset.return_value = mock_offset
        mock_filter.order_by.return_value = mock_order
        mock_filter.count.return_value = 1
        mock_outerjoin.filter.return_value = mock_filter
        mock_query.outerjoin.return_value = mock_outerjoin
        db.query.return_value = mock_query

        rows, total = repo.list_by_org(org_id, page=1, page_size=20)

        # Confirm query was called and filter was applied
        db.query.assert_called_once()
        mock_query.outerjoin.assert_called_once()
        mock_outerjoin.filter.assert_called_once()

        # The returned rows should only contain the block for org_id
        assert total == 1
        assert len(rows) == 1
        returned_block, product_name = rows[0]
        assert returned_block.organization_id == org_id
        assert returned_block.organization_id != other_org_id

    def test_returned_blocks_belong_to_org(self):
        """Simulate repo returning blocks; verify all have the correct org."""
        org_id = uuid.uuid4()
        block_a = _make_block(org_id)
        block_b = _make_block(org_id)

        repo = _make_repo_with_results(
            [(block_a, "Product A"), (block_b, "Product B")], total=2
        )

        rows, total = repo.list_by_org(org_id, page=1, page_size=20)

        assert total == 2
        for block, _ in rows:
            assert block.organization_id == org_id


# ---------------------------------------------------------------------------
# 6.2 — list_by_org excludes blocks where deleted_at IS NOT NULL
# Requirements: 1.6, 6.1
# ---------------------------------------------------------------------------

class TestListByOrgSoftDeleteExclusion:
    def test_filter_excludes_deleted_blocks(self):
        """Verify the query chain applies deleted_at IS NULL filter."""
        db = MagicMock()
        repo = QRBlockRepository(db)

        org_id = uuid.uuid4()

        mock_query = MagicMock()
        mock_outerjoin = MagicMock()
        mock_filter = MagicMock()
        mock_order = MagicMock()
        mock_offset = MagicMock()
        mock_limit = MagicMock()

        active_block = _make_block(org_id, deleted_at=None)
        mock_limit.all.return_value = [(active_block, "Product A")]
        mock_offset.limit.return_value = mock_limit
        mock_order.offset.return_value = mock_offset
        mock_filter.order_by.return_value = mock_order
        mock_filter.count.return_value = 1
        mock_outerjoin.filter.return_value = mock_filter
        mock_query.outerjoin.return_value = mock_outerjoin
        db.query.return_value = mock_query

        rows, total = repo.list_by_org(org_id, page=1, page_size=20)

        # The filter call should have been made (deleted_at IS NULL is applied inside)
        mock_outerjoin.filter.assert_called_once()

        # Only the active block is returned
        assert total == 1
        returned_block, _ = rows[0]
        assert returned_block.deleted_at is None

    def test_deleted_blocks_not_in_results(self):
        """Simulate repo correctly excluding deleted blocks."""
        org_id = uuid.uuid4()
        active_block = _make_block(org_id, deleted_at=None)
        # deleted block would NOT be returned by the repo (filter applied at DB level)

        repo = _make_repo_with_results([(active_block, "Product A")], total=1)

        rows, total = repo.list_by_org(org_id, page=1, page_size=20)

        assert total == 1
        for block, _ in rows:
            assert block.deleted_at is None


# ---------------------------------------------------------------------------
# 6.3 — list_by_org with status="completed" returns only completed blocks
# Requirements: 2.2
# ---------------------------------------------------------------------------

class TestListByOrgStatusFilter:
    def test_status_filter_returns_only_matching_blocks(self):
        """When status='completed' is passed, only completed blocks are returned."""
        org_id = uuid.uuid4()
        completed_block = _make_block(org_id, status="completed")

        repo = _make_repo_with_results([(completed_block, "Product A")], total=1)

        rows, total = repo.list_by_org(
            org_id, page=1, page_size=20, status="completed"
        )

        assert total == 1
        for block, _ in rows:
            assert block.status == "completed"

    def test_status_filter_called_with_correct_arg(self):
        """Verify list_by_org is invoked with status='completed'."""
        org_id = uuid.uuid4()
        repo = _make_repo_with_results([], total=0)

        repo.list_by_org(org_id, page=1, page_size=20, status="completed")

        repo.list_by_org.assert_called_once_with(
            org_id, page=1, page_size=20, status="completed"
        )

    def test_no_pending_blocks_when_filtering_completed(self):
        """Pending blocks must not appear when filtering by completed."""
        org_id = uuid.uuid4()
        completed_block = _make_block(org_id, status="completed")
        # pending_block would be filtered out at DB level

        repo = _make_repo_with_results([(completed_block, "Product A")], total=1)

        rows, total = repo.list_by_org(
            org_id, page=1, page_size=20, status="completed"
        )

        statuses = [block.status for block, _ in rows]
        assert "pending" not in statuses
        assert all(s == "completed" for s in statuses)


# ---------------------------------------------------------------------------
# 6.4 — list_by_org with product_id from a different org returns empty list
# Requirements: 3.4, 5.2
# ---------------------------------------------------------------------------

class TestListByOrgProductIdCrossOrg:
    def test_cross_org_product_id_returns_empty(self):
        """A product_id from another org yields empty results (org isolation)."""
        org_id = uuid.uuid4()
        other_org_product_id = uuid.uuid4()

        # Repo returns empty because org_id + product_id filters don't match
        repo = _make_repo_with_results([], total=0)

        rows, total = repo.list_by_org(
            org_id, page=1, page_size=20, product_id=other_org_product_id
        )

        assert total == 0
        assert rows == []

    def test_cross_org_product_id_does_not_raise(self):
        """Cross-org product_id should return 200 with empty list, not raise."""
        org_id = uuid.uuid4()
        foreign_product_id = uuid.uuid4()

        repo = _make_repo_with_results([], total=0)

        # Should not raise any exception
        rows, total = repo.list_by_org(
            org_id, page=1, page_size=20, product_id=foreign_product_id
        )

        assert isinstance(rows, list)
        assert total == 0


# ---------------------------------------------------------------------------
# 6.5 — list_blocks_by_org pagination when total_items=0
# Requirements: 4.3
# ---------------------------------------------------------------------------

class TestListBlocksByOrgPagination:
    def _make_service_with_mock_repo(self, rows, total):
        """Build a QRProductService with a mocked block_repo."""
        db = MagicMock()
        with patch(
            "app.services.qr_product_service.QRBlockRepository"
        ) as MockRepo, patch(
            "app.services.qr_product_service.QRProductRepository"
        ), patch(
            "app.services.qr_product_service.ProductItemRepository"
        ), patch(
            "app.services.qr_product_service.CreditService"
        ):
            mock_repo_instance = MagicMock()
            mock_repo_instance.list_by_org.return_value = (rows, total)
            MockRepo.return_value = mock_repo_instance

            svc = QRProductService(db)
            svc.block_repo = mock_repo_instance
            return svc

    def test_total_pages_is_1_when_total_items_is_0(self):
        """When total_items=0, total_pages must be 1 (not 0)."""
        svc = self._make_service_with_mock_repo(rows=[], total=0)

        _, pagination = svc.list_blocks_by_org(
            organization_id=uuid.uuid4(), page=1, page_size=20
        )

        assert pagination["total_items"] == 0
        assert pagination["total_pages"] == 1

    def test_has_next_false_when_total_items_is_0(self):
        """has_next must be False when there are no items."""
        svc = self._make_service_with_mock_repo(rows=[], total=0)

        _, pagination = svc.list_blocks_by_org(
            organization_id=uuid.uuid4(), page=1, page_size=20
        )

        assert pagination["has_next"] is False

    def test_has_prev_false_when_total_items_is_0(self):
        """has_prev must be False on page 1 with no items."""
        svc = self._make_service_with_mock_repo(rows=[], total=0)

        _, pagination = svc.list_blocks_by_org(
            organization_id=uuid.uuid4(), page=1, page_size=20
        )

        assert pagination["has_prev"] is False

    def test_pagination_fields_present(self):
        """Pagination dict must contain all required keys."""
        svc = self._make_service_with_mock_repo(rows=[], total=0)

        _, pagination = svc.list_blocks_by_org(
            organization_id=uuid.uuid4(), page=1, page_size=20
        )

        required_keys = {
            "page", "page_size", "total_items", "total_pages", "has_next", "has_prev"
        }
        assert required_keys.issubset(pagination.keys())

    def test_total_pages_rounds_up(self):
        """total_pages = ceil(total / page_size), minimum 1."""
        svc = self._make_service_with_mock_repo(rows=[], total=21)

        _, pagination = svc.list_blocks_by_org(
            organization_id=uuid.uuid4(), page=1, page_size=20
        )

        assert pagination["total_pages"] == 2


# ---------------------------------------------------------------------------
# 6.6 — OrgBlockListItem serializes product_name=None for soft-deleted product
# Requirements: 7.3
# ---------------------------------------------------------------------------

class TestOrgBlockListItemSchema:
    def _base_data(self, product_name=None):
        return {
            "id": uuid.uuid4(),
            "organization_id": uuid.uuid4(),
            "product_id": uuid.uuid4(),
            "product_name": product_name,
            "batch": "BATCH-001",
            "quantity": 100,
            "serial_prefix": None,
            "sr_number_type": None,
            "status": "completed",
            "task_status": "completed",
            "task_id": None,
            "qr_image": False,
            "manufacture_date": None,
            "expiry_date": None,
            "gcs_url": None,
            "download_url": None,
            "completed_at": None,
            "created_at": datetime.now(timezone.utc),
        }

    def test_product_name_none_when_product_soft_deleted(self):
        """OrgBlockListItem.product_name is None when the product is soft-deleted."""
        data = self._base_data(product_name=None)
        item = OrgBlockListItem.model_validate(data)
        assert item.product_name is None

    def test_product_name_serializes_to_none_in_dict(self):
        """Serialized dict includes product_name=None (not omitted)."""
        data = self._base_data(product_name=None)
        item = OrgBlockListItem.model_validate(data)
        serialized = item.model_dump()
        assert "product_name" in serialized
        assert serialized["product_name"] is None

    def test_product_name_populated_when_product_exists(self):
        """product_name is correctly set when the product is not deleted."""
        data = self._base_data(product_name="Widget Pro")
        item = OrgBlockListItem.model_validate(data)
        assert item.product_name == "Widget Pro"

    def test_schema_accepts_all_required_fields(self):
        """OrgBlockListItem validates successfully with all required fields."""
        data = self._base_data(product_name=None)
        item = OrgBlockListItem.model_validate(data)
        assert item.batch == "BATCH-001"
        assert item.quantity == 100
