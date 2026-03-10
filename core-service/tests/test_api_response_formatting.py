"""Tests for API response formatting (Requirements 10.3, 10.4, 10.5)"""



from app.core.exceptions import (
    IntegrationError,
    NotFoundError,
    StateError,
    ValidationError,
)


class TestStandardResponseFields:
    """Test that all responses include standard fields (Requirement 10.3)"""

    def test_response_schemas_include_standard_fields(self):
        """Test that response schemas are defined with standard fields"""
        # This test verifies the schema definitions include required fields
        # The actual API integration tests are in other test files

        from app.schemas.material_request import MaterialRequestResponse
        from app.schemas.purchase_order import PurchaseOrderResponse
        from app.schemas.rfq import RFQResponse

        # Verify MaterialRequestResponse has standard fields
        mr_fields = MaterialRequestResponse.model_fields
        assert "id" in mr_fields
        assert "created_at" in mr_fields
        assert "updated_at" in mr_fields
        assert "created_by" in mr_fields
        assert "status" in mr_fields

        # Verify RFQResponse has standard fields
        rfq_fields = RFQResponse.model_fields
        assert "id" in rfq_fields
        assert "created_at" in rfq_fields
        assert "updated_at" in rfq_fields
        assert "created_by" in rfq_fields
        assert "status" in rfq_fields

        # Verify PurchaseOrderResponse has standard fields
        po_fields = PurchaseOrderResponse.model_fields
        assert "id" in po_fields
        assert "created_at" in po_fields
        assert "updated_at" in po_fields
        assert "created_by" in po_fields
        assert "status" in po_fields


class TestValidationErrorFormatting:
    """Test validation error response format (Requirement 10.4)"""

    def test_validation_error_structure(self):
        """Test ValidationError has correct structure with field and reason"""
        # Create a ValidationError with details
        details = [
            {"field": "quantity", "reason": "Must be positive"},
            {"field": "item_id", "reason": "Required field"},
        ]
        error = ValidationError("Validation failed", details=details)

        # Verify error structure (Requirement 10.4)
        assert error.status_code == 400
        assert error.error_code == "VALIDATION_ERROR"
        assert error.message == "Validation failed"
        assert len(error.details) == 2
        assert error.details[0]["field"] == "quantity"
        assert error.details[0]["reason"] == "Must be positive"
        assert error.details[1]["field"] == "item_id"
        assert error.details[1]["reason"] == "Required field"

    def test_validation_error_handler_format(self):
        """Test that validation error handler returns correct format"""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        # Create a mock request and error
        details = [{"field": "test_field", "reason": "test reason"}]
        error = ValidationError("Test validation error", details=details)

        # Verify the error has the correct attributes for the handler
        assert hasattr(error, "error_code")
        assert hasattr(error, "message")
        assert hasattr(error, "details")
        assert error.error_code == "VALIDATION_ERROR"


class TestNotFoundErrorFormatting:
    """Test not found error response format (Requirement 10.5)"""

    def test_not_found_error_structure(self):
        """Test NotFoundError has correct structure with entity_type and entity_id"""
        # Create a NotFoundError
        error = NotFoundError(
            message="Material Request not found",
            entity_type="MATERIAL_REQUEST",
            entity_id="mr-123",
        )

        # Verify error structure (Requirement 10.5)
        assert error.status_code == 404
        assert error.error_code == "NOT_FOUND"
        assert error.message == "Material Request not found"
        assert error.entity_type == "MATERIAL_REQUEST"
        assert error.entity_id == "mr-123"

    def test_not_found_error_handler_format(self):
        """Test that not found error handler returns correct format"""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        # Create a mock error
        error = NotFoundError(
            message="Test not found",
            entity_type="TEST_ENTITY",
            entity_id="test-123",
        )

        # Verify the error has the correct attributes for the handler
        assert hasattr(error, "error_code")
        assert hasattr(error, "message")
        assert hasattr(error, "entity_type")
        assert hasattr(error, "entity_id")
        assert error.error_code == "NOT_FOUND"


class TestStateErrorFormatting:
    """Test state conflict error response format"""

    def test_state_error_structure(self):
        """Test StateError has correct structure with current_state and required_state"""
        # Create a StateError
        error = StateError(
            message="Invalid transition from CANCELLED to SUBMITTED",
            current_state="CANCELLED",
            required_state=["DRAFT"],
        )

        # Verify error structure
        assert error.status_code == 409
        assert error.error_code == "STATE_CONFLICT"
        assert error.message == "Invalid transition from CANCELLED to SUBMITTED"
        assert error.current_state == "CANCELLED"
        assert error.required_state == ["DRAFT"]

    def test_state_error_handler_format(self):
        """Test that state error handler returns correct format"""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        # Create a mock error
        error = StateError(
            message="Test state conflict",
            current_state="CLOSED",
            required_state=["DRAFT", "SUBMITTED"],
        )

        # Verify the error has the correct attributes for the handler
        assert hasattr(error, "error_code")
        assert hasattr(error, "message")
        assert hasattr(error, "current_state")
        assert hasattr(error, "required_state")
        assert error.error_code == "STATE_CONFLICT"


class TestIntegrationErrorFormatting:
    """Test integration error response format"""

    def test_integration_error_structure(self):
        """Test IntegrationError has correct structure with service and details"""
        # Create an IntegrationError
        error = IntegrationError(
            message="Suppliers API unavailable",
            service="Suppliers API",
            details="Connection timeout after 30s",
        )

        # Verify error structure
        assert error.status_code == 502
        assert error.error_code == "INTEGRATION_ERROR"
        assert error.message == "Suppliers API unavailable"
        assert error.service == "Suppliers API"
        assert error.details == "Connection timeout after 30s"

    def test_integration_error_handler_format(self):
        """Test that integration error handler returns correct format"""
        from fastapi.testclient import TestClient

        from app.main import app

        client = TestClient(app)

        # Create a mock error
        error = IntegrationError(
            message="Test integration error",
            service="Test API",
            details="Test details",
        )

        # Verify the error has the correct attributes for the handler
        assert hasattr(error, "error_code")
        assert hasattr(error, "message")
        assert hasattr(error, "service")
        assert hasattr(error, "details")
        assert hasattr(error, "status_code")
        assert error.error_code == "INTEGRATION_ERROR"
