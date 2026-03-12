"""Tests for chart of accounts setup schemas"""

import pytest
from uuid import uuid4
from pydantic import ValidationError

from app.schemas.chart_of_accounts_setup import (
    DefaultChartSetupRequest,
    DefaultChartSetupResponse,
    ManualTriggerRequest,
    DefaultChartResult,
)


class TestDefaultChartSetupRequest:
    """Tests for DefaultChartSetupRequest schema"""

    def test_valid_request(self):
        """Test creating a valid request"""
        org_id = uuid4()
        request = DefaultChartSetupRequest(
            organization_id=org_id,
            currency="USD",
            created_by="user123"
        )
        
        assert request.organization_id == org_id
        assert request.currency == "USD"
        assert request.created_by == "user123"

    def test_currency_defaults_to_usd(self):
        """Test currency defaults to USD"""
        org_id = uuid4()
        request = DefaultChartSetupRequest(
            organization_id=org_id,
            created_by="user123"
        )
        
        assert request.currency == "USD"

    def test_currency_must_be_3_letters(self):
        """Test currency must be exactly 3 letters"""
        org_id = uuid4()
        
        with pytest.raises(ValidationError) as exc_info:
            DefaultChartSetupRequest(
                organization_id=org_id,
                currency="US",
                created_by="user123"
            )
        
        assert "Currency must be a 3-letter ISO code" in str(exc_info.value)

    def test_currency_must_be_uppercase(self):
        """Test currency must be uppercase"""
        org_id = uuid4()
        
        with pytest.raises(ValidationError) as exc_info:
            DefaultChartSetupRequest(
                organization_id=org_id,
                currency="usd",
                created_by="user123"
            )
        
        assert "Currency must be uppercase" in str(exc_info.value)

    def test_currency_must_be_letters_only(self):
        """Test currency must contain only letters"""
        org_id = uuid4()
        
        with pytest.raises(ValidationError) as exc_info:
            DefaultChartSetupRequest(
                organization_id=org_id,
                currency="U$D",
                created_by="user123"
            )
        
        assert "Currency must contain only letters" in str(exc_info.value)

    def test_created_by_cannot_be_empty(self):
        """Test created_by cannot be empty"""
        org_id = uuid4()
        
        with pytest.raises(ValidationError) as exc_info:
            DefaultChartSetupRequest(
                organization_id=org_id,
                currency="USD",
                created_by=""
            )
        
        assert "created_by cannot be empty" in str(exc_info.value)

    def test_created_by_cannot_be_whitespace(self):
        """Test created_by cannot be whitespace only"""
        org_id = uuid4()
        
        with pytest.raises(ValidationError) as exc_info:
            DefaultChartSetupRequest(
                organization_id=org_id,
                currency="USD",
                created_by="   "
            )
        
        assert "created_by cannot be empty or whitespace-only" in str(exc_info.value)

    def test_created_by_strips_whitespace(self):
        """Test created_by strips leading/trailing whitespace"""
        org_id = uuid4()
        request = DefaultChartSetupRequest(
            organization_id=org_id,
            currency="USD",
            created_by="  user123  "
        )
        
        assert request.created_by == "user123"


class TestDefaultChartSetupResponse:
    """Tests for DefaultChartSetupResponse schema"""

    def test_valid_success_response(self):
        """Test creating a valid success response"""
        org_id = uuid4()
        response = DefaultChartSetupResponse(
            success=True,
            organization_id=org_id,
            accounts_created=25,
            mappings_created=6,
            message="Default chart created successfully"
        )
        
        assert response.success is True
        assert response.organization_id == org_id
        assert response.accounts_created == 25
        assert response.mappings_created == 6
        assert response.message == "Default chart created successfully"
        assert response.errors is None

    def test_valid_error_response(self):
        """Test creating a valid error response"""
        org_id = uuid4()
        response = DefaultChartSetupResponse(
            success=False,
            organization_id=org_id,
            accounts_created=0,
            mappings_created=0,
            message="Failed to create chart",
            errors=["Database error", "Connection timeout"]
        )
        
        assert response.success is False
        assert response.accounts_created == 0
        assert response.mappings_created == 0
        assert len(response.errors) == 2

    def test_accounts_created_must_be_non_negative(self):
        """Test accounts_created must be >= 0"""
        org_id = uuid4()
        
        with pytest.raises(ValidationError):
            DefaultChartSetupResponse(
                success=True,
                organization_id=org_id,
                accounts_created=-1,
                mappings_created=0,
                message="Test"
            )


class TestManualTriggerRequest:
    """Tests for ManualTriggerRequest schema"""

    def test_valid_request_with_defaults(self):
        """Test creating a valid request with default values"""
        request = ManualTriggerRequest()
        
        assert request.currency == "USD"
        assert request.force_recreate is False

    def test_valid_request_with_custom_values(self):
        """Test creating a valid request with custom values"""
        request = ManualTriggerRequest(
            currency="EUR",
            force_recreate=True
        )
        
        assert request.currency == "EUR"
        assert request.force_recreate is True

    def test_currency_validation(self):
        """Test currency validation works"""
        with pytest.raises(ValidationError) as exc_info:
            ManualTriggerRequest(currency="us")
        
        assert "Currency must be a 3-letter ISO code" in str(exc_info.value)


class TestDefaultChartResult:
    """Tests for DefaultChartResult schema"""

    def test_valid_result_with_data(self):
        """Test creating a valid result with data"""
        result = DefaultChartResult(
            accounts=[
                {"account_code": "1000", "account_name": "Cash"},
                {"account_code": "2000", "account_name": "Payables"}
            ],
            mappings=[
                {"transaction_type": "payment", "scenario": "cash"}
            ],
            already_existed=False
        )
        
        assert len(result.accounts) == 2
        assert len(result.mappings) == 1
        assert result.already_existed is False

    def test_valid_result_already_existed(self):
        """Test creating a result for already existing chart"""
        result = DefaultChartResult(
            accounts=[],
            mappings=[],
            already_existed=True
        )
        
        assert len(result.accounts) == 0
        assert len(result.mappings) == 0
        assert result.already_existed is True

    def test_defaults_to_empty_lists(self):
        """Test that accounts and mappings default to empty lists"""
        result = DefaultChartResult()
        
        assert result.accounts == []
        assert result.mappings == []
        assert result.already_existed is False
