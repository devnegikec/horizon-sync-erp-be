"""Tests for error handler classes"""

import pytest

from app.core.exceptions import (
    IntegrationError,
    NotFoundError,
    StateError,
    ValidationError,
)


class TestValidationError:
    """Tests for ValidationError"""

    def test_validation_error_with_details(self):
        """Test ValidationError with structured error details"""
        details = [
            {"field": "quantity", "reason": "Must be positive"},
            {"field": "item_id", "reason": "Required field"},
        ]
        error = ValidationError("Validation failed", details=details)

        assert error.message == "Validation failed"
        assert error.details == details
        assert error.status_code == 400
        assert error.error_code == "VALIDATION_ERROR"
        assert len(error.details) == 2

    def test_validation_error_without_details(self):
        """Test ValidationError without details defaults to empty list"""
        error = ValidationError("Validation failed")

        assert error.message == "Validation failed"
        assert error.details == []
        assert error.status_code == 400
        assert error.error_code == "VALIDATION_ERROR"

    def test_validation_error_is_exception(self):
        """Test ValidationError can be raised and caught"""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError(
                "Test error", details=[{"field": "test", "reason": "test"}]
            )

        assert exc_info.value.status_code == 400


class TestNotFoundError:
    """Tests for NotFoundError"""

    def test_not_found_error_with_entity_info(self):
        """Test NotFoundError with entity type and ID"""
        error = NotFoundError(
            message="Material Request not found",
            entity_type="MATERIAL_REQUEST",
            entity_id="mr-123",
        )

        assert error.message == "Material Request not found"
        assert error.entity_type == "MATERIAL_REQUEST"
        assert error.entity_id == "mr-123"
        assert error.status_code == 404
        assert error.error_code == "NOT_FOUND"

    def test_not_found_error_is_exception(self):
        """Test NotFoundError can be raised and caught"""
        with pytest.raises(NotFoundError) as exc_info:
            raise NotFoundError(
                message="Supplier not found",
                entity_type="SUPPLIER",
                entity_id="sup-456",
            )

        assert exc_info.value.entity_type == "SUPPLIER"
        assert exc_info.value.status_code == 404


class TestStateError:
    """Tests for StateError"""

    def test_state_error_with_conflict_details(self):
        """Test StateError with current and required states"""
        error = StateError(
            message="Invalid transition from CANCELLED to SUBMITTED",
            current_state="CANCELLED",
            required_state=["DRAFT"],
        )

        assert error.message == "Invalid transition from CANCELLED to SUBMITTED"
        assert error.current_state == "CANCELLED"
        assert error.required_state == ["DRAFT"]
        assert error.status_code == 409
        assert error.error_code == "STATE_CONFLICT"

    def test_state_error_with_multiple_required_states(self):
        """Test StateError with multiple valid states"""
        error = StateError(
            message="Cannot create receipt",
            current_state="DRAFT",
            required_state=["SUBMITTED", "PARTIALLY_RECEIVED"],
        )

        assert error.current_state == "DRAFT"
        assert len(error.required_state) == 2
        assert "SUBMITTED" in error.required_state
        assert "PARTIALLY_RECEIVED" in error.required_state

    def test_state_error_is_exception(self):
        """Test StateError can be raised and caught"""
        with pytest.raises(StateError) as exc_info:
            raise StateError(
                message="State conflict",
                current_state="CLOSED",
                required_state=["DRAFT"],
            )

        assert exc_info.value.status_code == 409


class TestIntegrationError:
    """Tests for IntegrationError"""

    def test_integration_error_with_service_info(self):
        """Test IntegrationError with service name and details"""
        error = IntegrationError(
            message="Suppliers API unavailable",
            service="Suppliers API",
            details="Connection timeout after 30s",
        )

        assert error.message == "Suppliers API unavailable"
        assert error.service == "Suppliers API"
        assert error.details == "Connection timeout after 30s"
        assert error.status_code == 502
        assert error.error_code == "INTEGRATION_ERROR"

    def test_integration_error_without_details(self):
        """Test IntegrationError without details"""
        error = IntegrationError(
            message="Purchase Receipt API error",
            service="Purchase Receipt API",
        )

        assert error.message == "Purchase Receipt API error"
        assert error.service == "Purchase Receipt API"
        assert error.details is None
        assert error.status_code == 502

    def test_integration_error_with_503_status(self):
        """Test IntegrationError with 503 status code"""
        error = IntegrationError(
            message="Service unavailable",
            service="Invoice API",
            status_code=503,
        )

        assert error.status_code == 503
        assert error.service == "Invoice API"

    def test_integration_error_defaults_invalid_status_to_502(self):
        """Test IntegrationError defaults invalid status codes to 502"""
        error = IntegrationError(
            message="Error",
            service="Test API",
            status_code=500,  # Invalid, should default to 502
        )

        assert error.status_code == 502

    def test_integration_error_is_exception(self):
        """Test IntegrationError can be raised and caught"""
        with pytest.raises(IntegrationError) as exc_info:
            raise IntegrationError(
                message="API error",
                service="External API",
                details="HTTP 500",
            )

        assert exc_info.value.service == "External API"
        assert exc_info.value.status_code == 502
