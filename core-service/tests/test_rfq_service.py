"""Unit tests for RFQ service"""

import uuid
from datetime import date, timedelta

import pytest

from app.core.exceptions import ResourceNotFoundException, ValidationException
from app.models.base import MaterialRequestStatus, RFQStatus
from app.models.material_request import MaterialRequest, MaterialRequestLine
from app.models.rfq import RFQ, RFQLine, RFQSupplier
from app.repositories.material_request_repository import MaterialRequestRepository
from app.repositories.rfq_repository import RFQRepository
from app.services.rfq_service import RFQService


@pytest.fixture
def rfq_service(db_session):
    """Create RFQ service instance"""
    return RFQService(db_session)


@pytest.fixture
def material_request_repo(db_session):
    """Create Material Request repository instance"""
    return MaterialRequestRepository(db_session)


@pytest.fixture
def rfq_repo(db_session):
    """Create RFQ repository instance"""
    return RFQRepository(db_session)


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
def test_supplier_ids():
    """Test supplier IDs"""
    return [uuid.uuid4(), uuid.uuid4()]


@pytest.fixture
def submitted_material_request(
    db_session, test_organization_id, test_user_id, test_item_id
):
    """Create a submitted Material Request for testing"""
    mr = MaterialRequest(
        organization_id=test_organization_id,
        status=MaterialRequestStatus.SUBMITTED,
        notes="Test MR",
        created_by=test_user_id,
        updated_by=test_user_id,
    )
    db_session.add(mr)
    db_session.commit()
    db_session.refresh(mr)

    # Add line items
    line = MaterialRequestLine(
        organization_id=test_organization_id,
        material_request_id=mr.id,
        item_id=test_item_id,
        quantity=10,
        required_date=date.today() + timedelta(days=30),
        description="Test item",
    )
    db_session.add(line)
    db_session.commit()
    db_session.refresh(mr)

    return mr


class TestCreateFromMaterialRequest:
    """Tests for create_from_material_request method"""

    def test_create_rfq_from_submitted_material_request(
        self,
        rfq_service,
        submitted_material_request,
        test_supplier_ids,
        test_organization_id,
        test_user_id,
    ):
        """Test creating RFQ from a submitted Material Request"""
        closing_date = date.today() + timedelta(days=7)

        result = rfq_service.create_from_material_request(
            material_request_id=submitted_material_request.id,
            closing_date=closing_date,
            supplier_ids=test_supplier_ids,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify RFQ was created
        assert result["id"] is not None
        assert result["status"] == RFQStatus.DRAFT.value
        assert result["material_request_id"] == submitted_material_request.id
        assert result["reference_type"] == "MATERIAL_REQUEST"
        assert result["reference_id"] == submitted_material_request.id
        assert result["closing_date"] == closing_date

        # Verify line items were copied
        assert len(result["line_items"]) == len(submitted_material_request.line_items)
        for rfq_line, mr_line in zip(
            result["line_items"], submitted_material_request.line_items
        ):
            assert rfq_line["item_id"] == mr_line.item_id
            assert rfq_line["quantity"] == mr_line.quantity
            assert rfq_line["required_date"] == mr_line.required_date
            assert rfq_line["description"] == mr_line.description

        # Verify suppliers were added
        assert len(result["suppliers"]) == len(test_supplier_ids)
        supplier_ids_in_result = {s["supplier_id"] for s in result["suppliers"]}
        assert supplier_ids_in_result == set(test_supplier_ids)

    def test_create_rfq_from_nonexistent_material_request(
        self,
        rfq_service,
        test_supplier_ids,
        test_organization_id,
        test_user_id,
    ):
        """Test creating RFQ from non-existent Material Request"""
        closing_date = date.today() + timedelta(days=7)
        non_existent_id = uuid.uuid4()

        with pytest.raises(ResourceNotFoundException) as exc_info:
            rfq_service.create_from_material_request(
                material_request_id=non_existent_id,
                closing_date=closing_date,
                supplier_ids=test_supplier_ids,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert str(non_existent_id) in str(exc_info.value)

    def test_create_rfq_from_draft_material_request(
        self,
        rfq_service,
        db_session,
        test_supplier_ids,
        test_organization_id,
        test_user_id,
        test_item_id,
    ):
        """Test creating RFQ from DRAFT Material Request should fail"""
        # Create DRAFT Material Request
        mr = MaterialRequest(
            organization_id=test_organization_id,
            status=MaterialRequestStatus.DRAFT,
            notes="Test MR",
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(mr)
        db_session.commit()

        closing_date = date.today() + timedelta(days=7)

        with pytest.raises(ValidationException) as exc_info:
            rfq_service.create_from_material_request(
                material_request_id=mr.id,
                closing_date=closing_date,
                supplier_ids=test_supplier_ids,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "SUBMITTED" in str(exc_info.value)

    def test_create_rfq_without_suppliers(
        self,
        rfq_service,
        submitted_material_request,
        test_organization_id,
        test_user_id,
    ):
        """Test creating RFQ without suppliers should fail"""
        closing_date = date.today() + timedelta(days=7)

        with pytest.raises(ValidationException) as exc_info:
            rfq_service.create_from_material_request(
                material_request_id=submitted_material_request.id,
                closing_date=closing_date,
                supplier_ids=[],
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "supplier" in str(exc_info.value).lower()


class TestAddSuppliers:
    """Tests for add_suppliers method"""

    def test_add_suppliers_to_draft_rfq(
        self,
        rfq_service,
        db_session,
        test_organization_id,
        test_user_id,
    ):
        """Test adding suppliers to a DRAFT RFQ"""
        # Create DRAFT RFQ
        rfq = RFQ(
            organization_id=test_organization_id,
            status=RFQStatus.DRAFT,
            closing_date=date.today() + timedelta(days=7),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(rfq)
        db_session.commit()
        db_session.refresh(rfq)

        new_supplier_ids = [uuid.uuid4(), uuid.uuid4()]

        result = rfq_service.add_suppliers(
            rfq_id=rfq.id,
            supplier_ids=new_supplier_ids,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify suppliers were added
        assert len(result["suppliers"]) == len(new_supplier_ids)
        supplier_ids_in_result = {s["supplier_id"] for s in result["suppliers"]}
        assert supplier_ids_in_result == set(new_supplier_ids)

    def test_add_suppliers_to_sent_rfq(
        self,
        rfq_service,
        db_session,
        test_organization_id,
        test_user_id,
    ):
        """Test adding suppliers to a SENT RFQ should fail"""
        # Create SENT RFQ
        rfq = RFQ(
            organization_id=test_organization_id,
            status=RFQStatus.SENT,
            closing_date=date.today() + timedelta(days=7),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(rfq)
        db_session.commit()

        new_supplier_ids = [uuid.uuid4()]

        with pytest.raises(ValidationException) as exc_info:
            rfq_service.add_suppliers(
                rfq_id=rfq.id,
                supplier_ids=new_supplier_ids,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "DRAFT" in str(exc_info.value)


class TestSend:
    """Tests for send method"""

    def test_send_draft_rfq(
        self,
        rfq_service,
        db_session,
        test_organization_id,
        test_user_id,
        test_item_id,
    ):
        """Test sending a DRAFT RFQ"""
        # Create DRAFT RFQ with line items and suppliers
        rfq = RFQ(
            organization_id=test_organization_id,
            status=RFQStatus.DRAFT,
            closing_date=date.today() + timedelta(days=7),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(rfq)
        db_session.commit()
        db_session.refresh(rfq)

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
        supplier = RFQSupplier(
            organization_id=test_organization_id,
            rfq_id=rfq.id,
            supplier_id=uuid.uuid4(),
        )
        db_session.add(supplier)
        db_session.commit()
        db_session.refresh(rfq)

        result = rfq_service.send(
            rfq_id=rfq.id,
            organization_id=test_organization_id,
            user_id=test_user_id,
        )

        # Verify status changed to SENT
        assert result["status"] == RFQStatus.SENT.value

    def test_send_rfq_without_line_items(
        self,
        rfq_service,
        db_session,
        test_organization_id,
        test_user_id,
    ):
        """Test sending RFQ without line items should fail"""
        # Create DRAFT RFQ without line items
        rfq = RFQ(
            organization_id=test_organization_id,
            status=RFQStatus.DRAFT,
            closing_date=date.today() + timedelta(days=7),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(rfq)
        db_session.commit()

        # Add supplier
        supplier = RFQSupplier(
            organization_id=test_organization_id,
            rfq_id=rfq.id,
            supplier_id=uuid.uuid4(),
        )
        db_session.add(supplier)
        db_session.commit()

        with pytest.raises(ValidationException) as exc_info:
            rfq_service.send(
                rfq_id=rfq.id,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "line items" in str(exc_info.value).lower()

    def test_send_rfq_without_suppliers(
        self,
        rfq_service,
        db_session,
        test_organization_id,
        test_user_id,
        test_item_id,
    ):
        """Test sending RFQ without suppliers should fail"""
        # Create DRAFT RFQ without suppliers
        rfq = RFQ(
            organization_id=test_organization_id,
            status=RFQStatus.DRAFT,
            closing_date=date.today() + timedelta(days=7),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(rfq)
        db_session.commit()

        # Add line item
        line = RFQLine(
            organization_id=test_organization_id,
            rfq_id=rfq.id,
            item_id=test_item_id,
            quantity=10,
            required_date=date.today() + timedelta(days=30),
        )
        db_session.add(line)
        db_session.commit()

        with pytest.raises(ValidationException) as exc_info:
            rfq_service.send(
                rfq_id=rfq.id,
                organization_id=test_organization_id,
                user_id=test_user_id,
            )

        assert "suppliers" in str(exc_info.value).lower()


class TestRecordQuote:
    """Tests for record_quote method"""

    def test_record_quote_for_sent_rfq(
        self,
        rfq_service,
        db_session,
        test_organization_id,
        test_user_id,
        test_item_id,
    ):
        """Test recording a quote for a SENT RFQ"""
        supplier_id = uuid.uuid4()

        # Create SENT RFQ
        rfq = RFQ(
            organization_id=test_organization_id,
            status=RFQStatus.SENT,
            closing_date=date.today() + timedelta(days=7),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(rfq)
        db_session.commit()

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
        supplier = RFQSupplier(
            organization_id=test_organization_id,
            rfq_id=rfq.id,
            supplier_id=supplier_id,
        )
        db_session.add(supplier)
        db_session.commit()
        db_session.refresh(rfq)

        result = rfq_service.record_quote(
            rfq_id=rfq.id,
            rfq_line_id=line.id,
            supplier_id=supplier_id,
            quoted_price=100.50,
            quoted_delivery_date=date.today() + timedelta(days=20),
            supplier_notes="Test quote",
            organization_id=test_organization_id,
        )

        # Verify quote was recorded
        assert len(result["line_items"]) == 1
        assert len(result["line_items"][0]["quotes"]) == 1
        quote = result["line_items"][0]["quotes"][0]
        assert quote["supplier_id"] == supplier_id
        assert float(quote["quoted_price"]) == 100.50
        assert quote["supplier_notes"] == "Test quote"

    def test_record_quote_updates_rfq_status(
        self,
        rfq_service,
        db_session,
        test_organization_id,
        test_user_id,
        test_item_id,
    ):
        """Test that recording quotes updates RFQ status appropriately"""
        supplier_id = uuid.uuid4()

        # Create SENT RFQ
        rfq = RFQ(
            organization_id=test_organization_id,
            status=RFQStatus.SENT,
            closing_date=date.today() + timedelta(days=7),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(rfq)
        db_session.commit()

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
        supplier = RFQSupplier(
            organization_id=test_organization_id,
            rfq_id=rfq.id,
            supplier_id=supplier_id,
        )
        db_session.add(supplier)
        db_session.commit()
        db_session.refresh(rfq)

        # Record quote - should update status to FULLY_RESPONDED (1 supplier, 1 line)
        result = rfq_service.record_quote(
            rfq_id=rfq.id,
            rfq_line_id=line.id,
            supplier_id=supplier_id,
            quoted_price=100.50,
            quoted_delivery_date=date.today() + timedelta(days=20),
            supplier_notes=None,
            organization_id=test_organization_id,
        )

        # Verify status changed to FULLY_RESPONDED
        assert result["status"] == RFQStatus.FULLY_RESPONDED.value

    def test_record_quote_for_invalid_supplier(
        self,
        rfq_service,
        db_session,
        test_organization_id,
        test_user_id,
        test_item_id,
    ):
        """Test recording quote for supplier not associated with RFQ"""
        supplier_id = uuid.uuid4()
        invalid_supplier_id = uuid.uuid4()

        # Create SENT RFQ
        rfq = RFQ(
            organization_id=test_organization_id,
            status=RFQStatus.SENT,
            closing_date=date.today() + timedelta(days=7),
            created_by=test_user_id,
            updated_by=test_user_id,
        )
        db_session.add(rfq)
        db_session.commit()

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
        supplier = RFQSupplier(
            organization_id=test_organization_id,
            rfq_id=rfq.id,
            supplier_id=supplier_id,
        )
        db_session.add(supplier)
        db_session.commit()

        with pytest.raises(ValidationException) as exc_info:
            rfq_service.record_quote(
                rfq_id=rfq.id,
                rfq_line_id=line.id,
                supplier_id=invalid_supplier_id,
                quoted_price=100.50,
                quoted_delivery_date=date.today() + timedelta(days=20),
                supplier_notes=None,
                organization_id=test_organization_id,
            )

        assert "not associated" in str(exc_info.value).lower()
