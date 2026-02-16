"""Tests for status transition logging"""

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.orm import Session

from app.models.base import MaterialRequestStatus, PurchaseOrderStatus, RFQStatus
from app.models.material_request import MaterialRequest, MaterialRequestLine
from app.models.purchase_order import PurchaseOrder, PurchaseOrderLine
from app.models.rfq import RFQ, RFQLine, RFQSupplier
from app.models.status_transition import StatusTransition
from app.models.supplier import Supplier
from app.services.material_request_service import MaterialRequestService
from app.services.purchase_order_service import PurchaseOrderService
from app.services.rfq_service import RFQService


@pytest.fixture
def test_organization_id():
    """Test organization ID"""
    return uuid.uuid4()


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return uuid.uuid4()


@pytest.fixture
def test_item_id():
    """Test item ID"""
    return uuid.uuid4()


@pytest.fixture
def test_supplier_id(db_session: Session, test_organization_id, test_user_id):
    """Create a test supplier"""
    supplier = Supplier(
        organization_id=test_organization_id,
        supplier_name="Test Supplier",
        supplier_code="SUP-001",
        email="supplier@test.com",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(supplier)
    db_session.commit()
    db_session.refresh(supplier)
    return supplier.id


class TestMaterialRequestStatusTransitionLogging:
    """Test status transition logging for Material Requests"""

    def test_submit_logs_transition(
        self, db_session: Session, test_organization_id, test_user_id, test_item_id
    ):
        """Test that submitting a Material Request logs the status transition"""
        # Create a Material Request in DRAFT status
        mr = MaterialRequest(
            organization_id=test_organization_id,
            status=MaterialRequestStatus.DRAFT,
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(mr)
        db_session.flush()

        # Add line item
        line = MaterialRequestLine(
            organization_id=test_organization_id,
            material_request_id=mr.id,
            item_id=test_item_id,
            quantity=10,
            required_date=date.today() + timedelta(days=30),
        )
        db_session.add(line)
        db_session.commit()

        # Submit the Material Request
        service = MaterialRequestService(db_session)
        service.submit(mr.id, test_organization_id, test_user_id)

        # Verify status transition was logged
        transition = (
            db_session.query(StatusTransition)
            .filter_by(entity_type="MATERIAL_REQUEST", entity_id=mr.id)
            .first()
        )

        assert transition is not None
        assert transition.previous_status == MaterialRequestStatus.DRAFT.value
        assert transition.new_status == MaterialRequestStatus.SUBMITTED.value
        assert transition.user_id == test_user_id
        assert transition.transitioned_at is not None

    def test_cancel_logs_transition(
        self, db_session: Session, test_organization_id, test_user_id, test_item_id
    ):
        """Test that cancelling a Material Request logs the status transition"""
        # Create a Material Request in SUBMITTED status
        mr = MaterialRequest(
            organization_id=test_organization_id,
            status=MaterialRequestStatus.SUBMITTED,
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(mr)
        db_session.flush()

        # Add line item
        line = MaterialRequestLine(
            organization_id=test_organization_id,
            material_request_id=mr.id,
            item_id=test_item_id,
            quantity=10,
            required_date=date.today() + timedelta(days=30),
        )
        db_session.add(line)
        db_session.commit()

        # Cancel the Material Request
        service = MaterialRequestService(db_session)
        service.cancel(mr.id, test_organization_id, test_user_id)

        # Verify status transition was logged
        transition = (
            db_session.query(StatusTransition)
            .filter_by(entity_type="MATERIAL_REQUEST", entity_id=mr.id)
            .first()
        )

        assert transition is not None
        assert transition.previous_status == MaterialRequestStatus.SUBMITTED.value
        assert transition.new_status == MaterialRequestStatus.CANCELLED.value
        assert transition.user_id == test_user_id


class TestRFQStatusTransitionLogging:
    """Test status transition logging for RFQs"""

    def test_send_logs_transition(
        self,
        db_session: Session,
        test_organization_id,
        test_user_id,
        test_item_id,
        test_supplier_id,
    ):
        """Test that sending an RFQ logs the status transition"""
        # Create a Material Request
        mr = MaterialRequest(
            organization_id=test_organization_id,
            status=MaterialRequestStatus.SUBMITTED,
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(mr)
        db_session.flush()

        # Create an RFQ in DRAFT status
        rfq = RFQ(
            organization_id=test_organization_id,
            material_request_id=mr.id,
            status=RFQStatus.DRAFT,
            closing_date=date.today() + timedelta(days=30),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(rfq)
        db_session.flush()

        # Add line item
        line = RFQLine(
            organization_id=test_organization_id,
            rfq_id=rfq.id,
            item_id=test_item_id,
            quantity=10,
            required_date=date.today() + timedelta(days=30),
        )
        db_session.add(line)

        # Add supplier
        rfq_supplier = RFQSupplier(
            organization_id=test_organization_id,
            rfq_id=rfq.id,
            supplier_id=test_supplier_id,
        )
        db_session.add(rfq_supplier)
        db_session.commit()

        # Send the RFQ
        service = RFQService(db_session)
        service.send(rfq.id, test_organization_id, test_user_id)

        # Verify status transition was logged
        transition = (
            db_session.query(StatusTransition)
            .filter_by(entity_type="RFQ", entity_id=rfq.id)
            .first()
        )

        assert transition is not None
        assert transition.previous_status == RFQStatus.DRAFT.value
        assert transition.new_status == RFQStatus.SENT.value
        assert transition.user_id == test_user_id

    def test_close_logs_transition(
        self, db_session: Session, test_organization_id, test_user_id, test_item_id
    ):
        """Test that closing an RFQ logs the status transition"""
        # Create a Material Request
        mr = MaterialRequest(
            organization_id=test_organization_id,
            status=MaterialRequestStatus.SUBMITTED,
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(mr)
        db_session.flush()

        # Create an RFQ in SENT status
        rfq = RFQ(
            organization_id=test_organization_id,
            material_request_id=mr.id,
            status=RFQStatus.SENT,
            closing_date=date.today() + timedelta(days=30),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(rfq)
        db_session.commit()

        # Close the RFQ
        service = RFQService(db_session)
        service.close(rfq.id, test_organization_id, test_user_id)

        # Verify status transition was logged
        transition = (
            db_session.query(StatusTransition)
            .filter_by(entity_type="RFQ", entity_id=rfq.id)
            .first()
        )

        assert transition is not None
        assert transition.previous_status == RFQStatus.SENT.value
        assert transition.new_status == RFQStatus.CLOSED.value
        assert transition.user_id == test_user_id


class TestPurchaseOrderStatusTransitionLogging:
    """Test status transition logging for Purchase Orders"""

    def test_submit_logs_transition(
        self,
        db_session: Session,
        test_organization_id,
        test_user_id,
        test_item_id,
        test_supplier_id,
    ):
        """Test that submitting a Purchase Order logs the status transition"""
        # Create a Purchase Order in DRAFT status
        po = PurchaseOrder(
            organization_id=test_organization_id,
            party_id=test_supplier_id,
            status=PurchaseOrderStatus.DRAFT,
            subtotal=100.00,
            tax_amount=10.00,
            discount_amount=0.00,
            grand_total=110.00,
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(po)
        db_session.flush()

        # Add line item
        line = PurchaseOrderLine(
            organization_id=test_organization_id,
            purchase_order_id=po.id,
            item_id=test_item_id,
            quantity=10,
            unit_price=10.00,
            line_total=100.00,
        )
        db_session.add(line)
        db_session.commit()

        # Submit the Purchase Order
        service = PurchaseOrderService(db_session)
        service.submit(po.id, test_organization_id, test_user_id)

        # Verify status transition was logged
        transition = (
            db_session.query(StatusTransition)
            .filter_by(entity_type="PURCHASE_ORDER", entity_id=po.id)
            .first()
        )

        assert transition is not None
        assert transition.previous_status == PurchaseOrderStatus.DRAFT.value
        assert transition.new_status == PurchaseOrderStatus.SUBMITTED.value
        assert transition.user_id == test_user_id

    def test_cancel_logs_transition(
        self,
        db_session: Session,
        test_organization_id,
        test_user_id,
        test_item_id,
        test_supplier_id,
    ):
        """Test that cancelling a Purchase Order logs the status transition"""
        # Create a Purchase Order in SUBMITTED status
        po = PurchaseOrder(
            organization_id=test_organization_id,
            party_id=test_supplier_id,
            status=PurchaseOrderStatus.SUBMITTED,
            subtotal=100.00,
            tax_amount=10.00,
            discount_amount=0.00,
            grand_total=110.00,
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(po)
        db_session.commit()

        # Cancel the Purchase Order
        service = PurchaseOrderService(db_session)
        service.cancel(po.id, test_organization_id, test_user_id)

        # Verify status transition was logged
        transition = (
            db_session.query(StatusTransition)
            .filter_by(entity_type="PURCHASE_ORDER", entity_id=po.id)
            .first()
        )

        assert transition is not None
        assert transition.previous_status == PurchaseOrderStatus.SUBMITTED.value
        assert transition.new_status == PurchaseOrderStatus.CANCELLED.value
        assert transition.user_id == test_user_id

    def test_close_logs_transition(
        self,
        db_session: Session,
        test_organization_id,
        test_user_id,
        test_item_id,
        test_supplier_id,
    ):
        """Test that closing a Purchase Order logs the status transition"""
        # Create a Purchase Order in FULLY_RECEIVED status
        po = PurchaseOrder(
            organization_id=test_organization_id,
            party_id=test_supplier_id,
            status=PurchaseOrderStatus.FULLY_RECEIVED,
            subtotal=100.00,
            tax_amount=10.00,
            discount_amount=0.00,
            grand_total=110.00,
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(po)
        db_session.commit()

        # Close the Purchase Order
        service = PurchaseOrderService(db_session)
        service.close(po.id, test_organization_id, test_user_id)

        # Verify status transition was logged
        transition = (
            db_session.query(StatusTransition)
            .filter_by(entity_type="PURCHASE_ORDER", entity_id=po.id)
            .first()
        )

        assert transition is not None
        assert transition.previous_status == PurchaseOrderStatus.FULLY_RECEIVED.value
        assert transition.new_status == PurchaseOrderStatus.CLOSED.value
        assert transition.user_id == test_user_id
