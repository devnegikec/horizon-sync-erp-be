"""
Integration tests for sourcing flow workflow connections.

Tests the complete workflow:
Material Request → RFQ → Purchase Order → Receipt Note → Purchase Invoice → Payment Made
"""

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.models.base import (
    MaterialRequestStatus,
    PurchaseOrderStatus,
    RFQStatus,
)
from app.services.material_request_service import MaterialRequestService
from app.services.purchase_order_service import PurchaseOrderService
from app.services.rfq_service import RFQService


class TestWorkflowIntegration:
    """Test workflow connections between sourcing flow components"""

    @pytest.fixture
    def organization_id(self):
        return uuid4()

    @pytest.fixture
    def user_id(self):
        return uuid4()

    @pytest.fixture
    def item_id(self):
        return uuid4()

    @pytest.fixture
    def supplier_id(self, db_session, organization_id):
        """Create a test supplier"""
        from app.models.supplier import Supplier

        supplier = Supplier(
            id=uuid4(),
            organization_id=organization_id,
            supplier_name="Test Supplier",
            supplier_code="SUP-001",
            email="supplier@test.com",
            created_by=uuid4(),
            updated_by=uuid4(),
        )
        db_session.add(supplier)
        db_session.commit()
        return supplier.id

    @pytest.fixture
    def item(self, db_session, organization_id, item_id):
        """Create a test item"""
        from app.models.item import Item

        item = Item(
            id=item_id,
            organization_id=organization_id,
            item_code="TEST-001",
            item_name="Test Item",
            item_type="product",
            created_by=uuid4(),
            updated_by=uuid4(),
        )
        db_session.add(item)
        db_session.commit()
        return item

    def test_material_request_to_rfq_workflow(
        self, db_session, organization_id, user_id, item_id, supplier_id, item
    ):
        """
        Test workflow connection: Material Request → RFQ

        When an RFQ is created from a Material Request:
        - Material Request status should be updated to PARTIALLY_QUOTED
        """
        # Create Material Request
        mr_service = MaterialRequestService(db_session)
        mr_data = {
            "notes": "Test MR",
            "line_items": [
                {
                    "item_id": item_id,
                    "quantity": 10,
                    "required_date": date.today(),
                    "description": "Test item",
                }
            ],
        }
        mr = mr_service.create(mr_data, organization_id, user_id)

        # Submit Material Request
        mr = mr_service.submit(mr["id"], organization_id, user_id)
        assert mr["status"] == MaterialRequestStatus.SUBMITTED.value

        # Create RFQ from Material Request
        rfq_service = RFQService(db_session)
        rfq = rfq_service.create_from_material_request(
            material_request_id=mr["id"],
            closing_date=date.today(),
            supplier_ids=[supplier_id],
            organization_id=organization_id,
            user_id=user_id,
        )

        # Verify RFQ was created
        assert rfq["material_request_id"] == mr["id"]
        assert rfq["status"] == RFQStatus.DRAFT.value
        assert len(rfq["line_items"]) == 1
        assert rfq["line_items"][0]["item_id"] == item_id

        # Verify Material Request status was updated to PARTIALLY_QUOTED
        mr_updated = mr_service.get_by_id(mr["id"], organization_id)
        assert mr_updated["status"] == MaterialRequestStatus.PARTIALLY_QUOTED.value

    def test_rfq_to_purchase_order_workflow(
        self, db_session, organization_id, user_id, item_id, supplier_id, item
    ):
        """
        Test workflow connection: RFQ → Purchase Order

        When a Purchase Order is created from an RFQ:
        - RFQ status should be updated to CLOSED
        """
        # Create Material Request
        mr_service = MaterialRequestService(db_session)
        mr_data = {
            "notes": "Test MR",
            "line_items": [
                {
                    "item_id": item_id,
                    "quantity": 10,
                    "required_date": date.today(),
                    "description": "Test item",
                }
            ],
        }
        mr = mr_service.create(mr_data, organization_id, user_id)
        mr = mr_service.submit(mr["id"], organization_id, user_id)

        # Create RFQ from Material Request
        rfq_service = RFQService(db_session)
        rfq = rfq_service.create_from_material_request(
            material_request_id=mr["id"],
            closing_date=date.today(),
            supplier_ids=[supplier_id],
            organization_id=organization_id,
            user_id=user_id,
        )

        # Send RFQ
        rfq = rfq_service.send(rfq["id"], organization_id, user_id)
        assert rfq["status"] == RFQStatus.SENT.value

        # Record supplier quote
        rfq_line_id = rfq["line_items"][0]["id"]
        rfq = rfq_service.record_quote(
            rfq_id=rfq["id"],
            rfq_line_id=rfq_line_id,
            supplier_id=supplier_id,
            quoted_price=100.00,
            quoted_delivery_date=date.today(),
            supplier_notes="Test quote",
            organization_id=organization_id,
        )

        # Verify RFQ status updated to FULLY_RESPONDED
        assert rfq["status"] == RFQStatus.FULLY_RESPONDED.value

        # Create Purchase Order from RFQ
        po_service = PurchaseOrderService(db_session)
        po = po_service.create_from_rfq(
            rfq_id=rfq["id"],
            supplier_id=supplier_id,
            line_items=[
                {
                    "item_id": item_id,
                    "quantity": 10,
                    "unit_price": 100.00,
                }
            ],
            tax_rate=Decimal("0.18"),
            discount_amount=Decimal("0"),
            organization_id=organization_id,
            user_id=user_id,
        )

        # Verify Purchase Order was created
        assert po["rfq_id"] == rfq["id"]
        assert po["status"] == PurchaseOrderStatus.DRAFT.value
        assert len(po["line_items"]) == 1

        # Verify RFQ status was updated to CLOSED
        rfq_updated = rfq_service.get_by_id(rfq["id"], organization_id)
        assert rfq_updated["status"] == RFQStatus.CLOSED.value

    def test_material_request_fully_quoted_status(
        self, db_session, organization_id, user_id, item_id, supplier_id, item
    ):
        """
        Test Material Request status updates to FULLY_QUOTED when all items have quotes
        """
        # Create Material Request
        mr_service = MaterialRequestService(db_session)
        mr_data = {
            "notes": "Test MR",
            "line_items": [
                {
                    "item_id": item_id,
                    "quantity": 10,
                    "required_date": date.today(),
                    "description": "Test item",
                }
            ],
        }
        mr = mr_service.create(mr_data, organization_id, user_id)
        mr = mr_service.submit(mr["id"], organization_id, user_id)

        # Create RFQ from Material Request
        rfq_service = RFQService(db_session)
        rfq = rfq_service.create_from_material_request(
            material_request_id=mr["id"],
            closing_date=date.today(),
            supplier_ids=[supplier_id],
            organization_id=organization_id,
            user_id=user_id,
        )

        # Send RFQ
        rfq = rfq_service.send(rfq["id"], organization_id, user_id)

        # Record supplier quote for all line items
        rfq_line_id = rfq["line_items"][0]["id"]
        rfq = rfq_service.record_quote(
            rfq_id=rfq["id"],
            rfq_line_id=rfq_line_id,
            supplier_id=supplier_id,
            quoted_price=100.00,
            quoted_delivery_date=date.today(),
            supplier_notes="Test quote",
            organization_id=organization_id,
        )

        # Verify Material Request status was updated to FULLY_QUOTED
        mr_updated = mr_service.get_by_id(mr["id"], organization_id)
        assert mr_updated["status"] == MaterialRequestStatus.FULLY_QUOTED.value
