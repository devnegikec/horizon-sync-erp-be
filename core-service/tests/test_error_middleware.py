"""Tests for error handling middleware (Task 13.3)

This module tests that:
- All exceptions are caught and formatted correctly
- Appropriate HTTP status codes are returned
- Errors are logged for debugging
"""

import logging
from unittest.mock import Mock, patch

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.exceptions import (
    ValidationError,
    NotFoundError,
    StateError,
    IntegrationError,
)
from app.main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


@pytest.fixture
def mock_request():
    """Create a mock request object"""
    request = Mock(spec=Request)
    request.method = "POST"
    request.url.path = "/api/v1/test"
    return request


class TestValidationErrorMiddleware:
    """Test ValidationError exception handler middleware"""

    @pytest.mark.asyncio
    @patch("app.main.logger")
    async def test_validation_error_logs_warning(self, mock_logger, mock_request):
        """Test that ValidationError logs a warning with details"""
        from app.main import custom_validation_exception_handler
        
        # Create a validation error
        details = [
            {"field": "quantity", "reason": "Must be positive"},
            {"field": "item_id", "reason": "Required field"},
        ]
        error = ValidationError("Validation failed", details=details)
        
        # Call the handler
        response = await custom_validation_exception_handler(mock_request, error)
        
        # Verify logging was called
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        
        # Check log message
        assert "Validation error" in call_args[0][0]
        assert "POST" in call_args[0][0]
        assert "/api/v1/test" in call_args[0][0]
        
        # Check extra fields
        assert "extra" in call_args[1]
        assert call_args[1]["extra"]["details"] == details
        assert call_args[1]["extra"]["path"] == "/api/v1/test"
        assert call_args[1]["extra"]["method"] == "POST"

    @pytest.mark.asyncio
    async def test_validation_error_returns_400(self, mock_request):
        """Test that ValidationError returns HTTP 400"""
        from app.main import custom_validation_exception_handler
        
        error = ValidationError("Test error", details=[])
        response = await custom_validation_exception_handler(mock_request, error)
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_validation_error_response_format(self, mock_request):
        """Test that ValidationError response has correct format"""
        from app.main import custom_validation_exception_handler
        import json
        
        details = [{"field": "test", "reason": "test reason"}]
        error = ValidationError("Test error", details=details)
        response = await custom_validation_exception_handler(mock_request, error)
        
        body = json.loads(response.body)
        assert body["error"] == "VALIDATION_ERROR"
        assert body["message"] == "Test error"
        assert body["details"] == details


class TestNotFoundErrorMiddleware:
    """Test NotFoundError exception handler middleware"""

    @pytest.mark.asyncio
    @patch("app.main.logger")
    async def test_not_found_error_logs_info(self, mock_logger, mock_request):
        """Test that NotFoundError logs an info message with entity details"""
        from app.main import not_found_error_handler
        
        # Create a not found error
        error = NotFoundError(
            message="Material Request not found",
            entity_type="MATERIAL_REQUEST",
            entity_id="mr-123",
        )
        
        # Call the handler
        response = await not_found_error_handler(mock_request, error)
        
        # Verify logging was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args
        
        # Check log message
        assert "Entity not found" in call_args[0][0]
        assert "MATERIAL_REQUEST" in call_args[0][0]
        assert "mr-123" in call_args[0][0]
        
        # Check extra fields
        assert "extra" in call_args[1]
        assert call_args[1]["extra"]["entity_type"] == "MATERIAL_REQUEST"
        assert call_args[1]["extra"]["entity_id"] == "mr-123"

    @pytest.mark.asyncio
    async def test_not_found_error_returns_404(self, mock_request):
        """Test that NotFoundError returns HTTP 404"""
        from app.main import not_found_error_handler
        
        error = NotFoundError(
            message="Test not found",
            entity_type="TEST",
            entity_id="test-123",
        )
        response = await not_found_error_handler(mock_request, error)
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_not_found_error_response_format(self, mock_request):
        """Test that NotFoundError response has correct format"""
        from app.main import not_found_error_handler
        import json
        
        error = NotFoundError(
            message="Test not found",
            entity_type="TEST",
            entity_id="test-123",
        )
        response = await not_found_error_handler(mock_request, error)
        
        body = json.loads(response.body)
        assert body["error"] == "NOT_FOUND"
        assert body["message"] == "Test not found"
        assert body["entity_type"] == "TEST"
        assert body["entity_id"] == "test-123"


class TestStateErrorMiddleware:
    """Test StateError exception handler middleware"""

    @pytest.mark.asyncio
    @patch("app.main.logger")
    async def test_state_error_logs_warning(self, mock_logger, mock_request):
        """Test that StateError logs a warning with state details"""
        from app.main import state_error_handler
        
        # Create a state error
        error = StateError(
            message="Invalid transition",
            current_state="CANCELLED",
            required_state=["DRAFT"],
        )
        
        # Call the handler
        response = await state_error_handler(mock_request, error)
        
        # Verify logging was called
        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args
        
        # Check log message
        assert "State conflict" in call_args[0][0]
        assert "Invalid transition" in call_args[0][0]
        
        # Check extra fields
        assert "extra" in call_args[1]
        assert call_args[1]["extra"]["current_state"] == "CANCELLED"
        assert call_args[1]["extra"]["required_state"] == ["DRAFT"]

    @pytest.mark.asyncio
    async def test_state_error_returns_409(self, mock_request):
        """Test that StateError returns HTTP 409"""
        from app.main import state_error_handler
        
        error = StateError(
            message="Test conflict",
            current_state="CLOSED",
            required_state=["DRAFT"],
        )
        response = await state_error_handler(mock_request, error)
        
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_state_error_response_format(self, mock_request):
        """Test that StateError response has correct format"""
        from app.main import state_error_handler
        import json
        
        error = StateError(
            message="Test conflict",
            current_state="CLOSED",
            required_state=["DRAFT", "SUBMITTED"],
        )
        response = await state_error_handler(mock_request, error)
        
        body = json.loads(response.body)
        assert body["error"] == "STATE_CONFLICT"
        assert body["message"] == "Test conflict"
        assert body["current_state"] == "CLOSED"
        assert body["required_state"] == ["DRAFT", "SUBMITTED"]


class TestIntegrationErrorMiddleware:
    """Test IntegrationError exception handler middleware"""

    @pytest.mark.asyncio
    @patch("app.main.logger")
    async def test_integration_error_logs_error(self, mock_logger, mock_request):
        """Test that IntegrationError logs an error with service details"""
        from app.main import integration_error_handler
        
        # Create an integration error
        error = IntegrationError(
            message="Suppliers API unavailable",
            service="Suppliers API",
            details="Connection timeout",
            status_code=502,
        )
        
        # Call the handler
        response = await integration_error_handler(mock_request, error)
        
        # Verify logging was called
        mock_logger.error.assert_called_once()
        call_args = mock_logger.error.call_args
        
        # Check log message
        assert "Integration error" in call_args[0][0]
        assert "Suppliers API" in call_args[0][0]
        
        # Check extra fields
        assert "extra" in call_args[1]
        assert call_args[1]["extra"]["service"] == "Suppliers API"
        assert call_args[1]["extra"]["details"] == "Connection timeout"
        assert call_args[1]["extra"]["status_code"] == 502

    @pytest.mark.asyncio
    async def test_integration_error_returns_502(self, mock_request):
        """Test that IntegrationError returns HTTP 502"""
        from app.main import integration_error_handler
        
        error = IntegrationError(
            message="Test error",
            service="Test API",
            status_code=502,
        )
        response = await integration_error_handler(mock_request, error)
        
        assert response.status_code == 502

    @pytest.mark.asyncio
    async def test_integration_error_returns_503(self, mock_request):
        """Test that IntegrationError can return HTTP 503"""
        from app.main import integration_error_handler
        
        error = IntegrationError(
            message="Service unavailable",
            service="Test API",
            status_code=503,
        )
        response = await integration_error_handler(mock_request, error)
        
        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_integration_error_response_format(self, mock_request):
        """Test that IntegrationError response has correct format"""
        from app.main import integration_error_handler
        import json
        
        error = IntegrationError(
            message="Test error",
            service="Test API",
            details="Test details",
        )
        response = await integration_error_handler(mock_request, error)
        
        body = json.loads(response.body)
        assert body["error"] == "INTEGRATION_ERROR"
        assert body["message"] == "Test error"
        assert body["service"] == "Test API"
        assert body["details"] == "Test details"


class TestGeneralExceptionMiddleware:
    """Test general exception handler middleware"""

    @pytest.mark.asyncio
    @patch("app.main.logger")
    async def test_general_exception_logs_error(self, mock_logger, mock_request):
        """Test that general exceptions are logged"""
        from app.main import general_exception_handler
        
        # Create a general exception
        error = Exception("Unexpected error")
        
        # Call the handler
        response = await general_exception_handler(mock_request, error)
        
        # Verify logging was called
        mock_logger.error.assert_called_once()
        assert "Unexpected error" in str(mock_logger.error.call_args)

    @pytest.mark.asyncio
    async def test_general_exception_returns_500(self, mock_request):
        """Test that general exceptions return HTTP 500"""
        from app.main import general_exception_handler
        
        error = Exception("Test error")
        response = await general_exception_handler(mock_request, error)
        
        assert response.status_code == 500


class TestErrorHandlerIntegration:
    """Integration tests for error handlers"""

    def test_all_error_types_have_handlers(self):
        """Test that all custom error types have registered handlers"""
        from app.main import app
        
        # Get all registered exception handlers
        handlers = app.exception_handlers
        
        # Verify our custom error types are registered
        assert ValidationError in handlers
        assert NotFoundError in handlers
        assert StateError in handlers
        assert IntegrationError in handlers

    @pytest.mark.asyncio
    async def test_error_handlers_return_json_response(self, mock_request):
        """Test that all error handlers return JSONResponse"""
        from app.main import (
            custom_validation_exception_handler,
            not_found_error_handler,
            state_error_handler,
            integration_error_handler,
        )
        from fastapi.responses import JSONResponse
        
        # Test ValidationError
        val_error = ValidationError("Test", details=[])
        val_response = await custom_validation_exception_handler(mock_request, val_error)
        assert isinstance(val_response, JSONResponse)
        
        # Test NotFoundError
        nf_error = NotFoundError("Test", "TEST", "123")
        nf_response = await not_found_error_handler(mock_request, nf_error)
        assert isinstance(nf_response, JSONResponse)
        
        # Test StateError
        state_error = StateError("Test", "CLOSED", ["DRAFT"])
        state_response = await state_error_handler(mock_request, state_error)
        assert isinstance(state_response, JSONResponse)
        
        # Test IntegrationError
        int_error = IntegrationError("Test", "Test API")
        int_response = await integration_error_handler(mock_request, int_error)
        assert isinstance(int_response, JSONResponse)
