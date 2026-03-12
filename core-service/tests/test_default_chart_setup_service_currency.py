"""Unit tests for DefaultChartSetupService currency validation"""

import logging
import uuid
from unittest.mock import MagicMock, patch

import pytest

from app.services.default_chart_setup_service import DefaultChartSetupService


class TestCurrencyValidation:
    """Test currency validation in DefaultChartSetupService"""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        return MagicMock()

    @pytest.fixture
    def service(self, mock_db_session):
        """Create DefaultChartSetupService instance with mocked dependencies"""
        return DefaultChartSetupService(mock_db_session)

    def test_validate_currency_valid_uppercase(self, service):
        """Test validation with valid uppercase currency code"""
        result = service._validate_currency("USD")
        assert result == "USD"

    def test_validate_currency_valid_lowercase(self, service):
        """Test validation with valid lowercase currency code (should convert to uppercase)"""
        result = service._validate_currency("usd")
        assert result == "USD"

    def test_validate_currency_valid_mixed_case(self, service):
        """Test validation with mixed case currency code (should convert to uppercase)"""
        result = service._validate_currency("UsD")
        assert result == "USD"

    def test_validate_currency_valid_eur(self, service):
        """Test validation with EUR currency"""
        result = service._validate_currency("EUR")
        assert result == "EUR"

    def test_validate_currency_valid_gbp(self, service):
        """Test validation with GBP currency"""
        result = service._validate_currency("gbp")
        assert result == "GBP"

    def test_validate_currency_empty_string(self, service, caplog):
        """Test validation with empty string defaults to USD"""
        with caplog.at_level(logging.WARNING):
            result = service._validate_currency("")
        
        assert result == "USD"
        assert "Currency not specified, defaulting to USD" in caplog.text

    def test_validate_currency_none(self, service, caplog):
        """Test validation with None defaults to USD"""
        with caplog.at_level(logging.WARNING):
            result = service._validate_currency(None)
        
        assert result == "USD"
        assert "Currency not specified, defaulting to USD" in caplog.text

    def test_validate_currency_too_short(self, service, caplog):
        """Test validation with currency code too short (2 letters)"""
        with caplog.at_level(logging.WARNING):
            result = service._validate_currency("US")
        
        assert result == "USD"
        assert "Invalid currency code format, defaulting to USD" in caplog.text

    def test_validate_currency_too_long(self, service, caplog):
        """Test validation with currency code too long (4 letters)"""
        with caplog.at_level(logging.WARNING):
            result = service._validate_currency("USDD")
        
        assert result == "USD"
        assert "Invalid currency code format, defaulting to USD" in caplog.text

    def test_validate_currency_with_numbers(self, service, caplog):
        """Test validation with currency code containing numbers"""
        with caplog.at_level(logging.WARNING):
            result = service._validate_currency("US1")
        
        assert result == "USD"
        assert "Invalid currency code format, defaulting to USD" in caplog.text

    def test_validate_currency_with_special_chars(self, service, caplog):
        """Test validation with currency code containing special characters"""
        with caplog.at_level(logging.WARNING):
            result = service._validate_currency("US$")
        
        assert result == "USD"
        assert "Invalid currency code format, defaulting to USD" in caplog.text

    def test_validate_currency_with_spaces(self, service, caplog):
        """Test validation with currency code containing spaces"""
        with caplog.at_level(logging.WARNING):
            result = service._validate_currency("U S")
        
        assert result == "USD"
        assert "Invalid currency code format, defaulting to USD" in caplog.text

    def test_validate_currency_logs_warning_for_invalid(self, service, caplog):
        """Test that invalid currency logs appropriate warning with extra fields"""
        with caplog.at_level(logging.WARNING):
            service._validate_currency("INVALID")
        
        # Check that warning was logged
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "Invalid currency code format" in record.message
        
        # Check extra fields
        assert record.provided_currency == "INVALID"
        assert record.default_currency == "USD"
        assert record.event == "currency_validation_failed"

    def test_validate_currency_logs_debug_for_valid(self, service, caplog):
        """Test that valid currency logs debug message"""
        with caplog.at_level(logging.DEBUG):
            service._validate_currency("EUR")
        
        # Check that debug message was logged
        assert any("Currency validated: EUR" in record.message for record in caplog.records)
        
        # Check extra fields in debug log
        debug_records = [r for r in caplog.records if r.levelname == "DEBUG"]
        assert len(debug_records) > 0
        record = debug_records[0]
        assert record.currency == "EUR"
        assert record.event == "currency_validated"


class TestCurrencyValidationIntegration:
    """Integration tests for currency validation in chart creation"""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session"""
        session = MagicMock()
        session.commit = MagicMock()
        session.rollback = MagicMock()
        return session

    @pytest.fixture
    def service(self, mock_db_session):
        """Create DefaultChartSetupService with mocked dependencies"""
        service = DefaultChartSetupService(mock_db_session)
        
        # Mock the repository methods
        service.account_repo.check_default_accounts_exist = MagicMock(return_value=False)
        service.chart_service.create = MagicMock()
        service.default_account_service.set_default_account = MagicMock()
        
        return service

    @patch('app.services.default_chart_setup_service.get_default_account_structure')
    def test_create_chart_with_valid_currency(self, mock_get_structure, service):
        """Test that chart creation uses validated currency"""
        # Setup mock to return empty list to avoid actual account creation
        mock_get_structure.return_value = []
        
        organization_id = uuid.uuid4()
        
        # Call with lowercase currency
        result = service.create_default_chart_of_accounts(
            organization_id=organization_id,
            currency="eur",
            created_by="test_user"
        )
        
        # Verify the result
        assert result.already_existed is False
        assert result.accounts == []
        assert result.mappings == []

    @patch('app.services.default_chart_setup_service.get_default_account_structure')
    def test_create_chart_with_invalid_currency_defaults_to_usd(
        self, mock_get_structure, service, caplog
    ):
        """Test that chart creation defaults to USD for invalid currency"""
        # Setup mock to return empty list
        mock_get_structure.return_value = []
        
        organization_id = uuid.uuid4()
        
        with caplog.at_level(logging.WARNING):
            result = service.create_default_chart_of_accounts(
                organization_id=organization_id,
                currency="INVALID",
                created_by="test_user"
            )
        
        # Verify warning was logged
        assert "Invalid currency code format, defaulting to USD" in caplog.text
        
        # Verify the result
        assert result.already_existed is False

    @patch('app.services.default_chart_setup_service.get_default_account_structure')
    def test_create_chart_with_empty_currency_defaults_to_usd(
        self, mock_get_structure, service, caplog
    ):
        """Test that chart creation defaults to USD for empty currency"""
        # Setup mock to return empty list
        mock_get_structure.return_value = []
        
        organization_id = uuid.uuid4()
        
        with caplog.at_level(logging.WARNING):
            result = service.create_default_chart_of_accounts(
                organization_id=organization_id,
                currency="",
                created_by="test_user"
            )
        
        # Verify warning was logged
        assert "Currency not specified, defaulting to USD" in caplog.text
        
        # Verify the result
        assert result.already_existed is False
