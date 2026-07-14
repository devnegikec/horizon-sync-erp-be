"""
Unit tests for CountryValidator

Tests country-specific banking validation rules for US, GB, DE, IN, and AU.
"""

import pytest
from app.services.country_validator import (
    CountryValidator,
    ValidationResult,
    COUNTRY_BANKING_RULES,
    get_country_validator
)


class TestCountryValidator:
    """Test suite for CountryValidator"""
    
    # US Validation Tests
    
    def test_us_routing_number_valid(self):
        """Test US routing number validation with valid input"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('US', {
            'routing_number': '123456789',
            'account_number': '1234567890'
        })
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_us_routing_number_invalid_too_short(self):
        """Test US routing number validation with too short input"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('US', {
            'routing_number': '12345',  # Too short
            'account_number': '1234567890'
        })
        
        assert result.is_valid is False
        assert any('routing_number' in error for error in result.errors)
        assert any('pattern' in error.lower() for error in result.errors)
    
    def test_us_routing_number_invalid_too_long(self):
        """Test US routing number validation with too long input"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('US', {
            'routing_number': '1234567890',  # Too long (10 digits)
            'account_number': '1234567890'
        })
        
        assert result.is_valid is False
        assert any('routing_number' in error for error in result.errors)
    
    def test_us_routing_number_invalid_non_numeric(self):
        """Test US routing number validation with non-numeric input"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('US', {
            'routing_number': '12345678A',  # Contains letter
            'account_number': '1234567890'
        })
        
        assert result.is_valid is False
        assert any('routing_number' in error for error in result.errors)
    
    def test_us_missing_routing_number(self):
        """Test US validation fails when routing_number is missing"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('US', {
            'account_number': '1234567890'
        })
        
        assert result.is_valid is False
        assert any('routing_number' in error for error in result.errors)
        assert any('Missing' in error for error in result.errors)
    
    def test_us_missing_account_number(self):
        """Test US validation fails when account_number is missing"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('US', {
            'routing_number': '123456789'
        })
        
        assert result.is_valid is False
        assert any('account_number' in error for error in result.errors)
        assert any('Missing' in error for error in result.errors)
    
    # GB (UK) Validation Tests
    
    def test_gb_sort_code_valid(self):
        """Test GB sort code validation with valid input"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('GB', {
            'sort_code': '12-34-56',
            'account_number': '12345678'
        })
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_gb_sort_code_invalid_format(self):
        """Test GB sort code validation with invalid format"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('GB', {
            'sort_code': '123456',  # Missing dashes
            'account_number': '12345678'
        })
        
        assert result.is_valid is False
        assert any('sort_code' in error for error in result.errors)
    
    def test_gb_sort_code_invalid_wrong_dashes(self):
        """Test GB sort code validation with wrong dash positions"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('GB', {
            'sort_code': '1-23-456',  # Wrong dash positions
            'account_number': '12345678'
        })
        
        assert result.is_valid is False
        assert any('sort_code' in error for error in result.errors)
    
    def test_gb_missing_sort_code(self):
        """Test GB validation fails when sort_code is missing"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('GB', {
            'account_number': '12345678'
        })
        
        assert result.is_valid is False
        assert any('sort_code' in error for error in result.errors)
        assert any('Missing' in error for error in result.errors)
    
    # DE (Germany/EU) Validation Tests
    
    def test_de_iban_valid(self):
        """Test DE IBAN validation with valid input"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('DE', {
            'iban': 'DE89370400440532013456',
            'swift_code': 'COBADEFF'
        })
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_de_iban_valid_with_branch_code(self):
        """Test DE IBAN validation with SWIFT code including branch"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('DE', {
            'iban': 'DE89370400440532013456',
            'swift_code': 'COBADEFFXXX'  # With branch code
        })
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_de_iban_invalid_format(self):
        """Test DE IBAN validation with invalid format"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('DE', {
            'iban': 'DE8937040044',  # Too short
            'swift_code': 'COBADEFF'
        })
        
        assert result.is_valid is False
        assert any('iban' in error.lower() for error in result.errors)
    
    def test_de_iban_invalid_starts_with_lowercase(self):
        """Test DE IBAN validation rejects lowercase country code"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('DE', {
            'iban': 'de89370400440532013456',  # Lowercase
            'swift_code': 'COBADEFF'
        })
        
        assert result.is_valid is False
        assert any('iban' in error.lower() for error in result.errors)
    
    def test_de_swift_code_invalid_format(self):
        """Test DE SWIFT code validation with invalid format"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('DE', {
            'iban': 'DE89370400440532013456',
            'swift_code': 'COBA'  # Too short
        })
        
        assert result.is_valid is False
        assert any('swift_code' in error for error in result.errors)
    
    def test_de_missing_iban(self):
        """Test DE validation fails when IBAN is missing"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('DE', {
            'swift_code': 'COBADEFF'
        })
        
        assert result.is_valid is False
        assert any('iban' in error.lower() for error in result.errors)
        assert any('Missing' in error for error in result.errors)
    
    def test_de_missing_swift_code(self):
        """Test DE validation fails when SWIFT code is missing"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('DE', {
            'iban': 'DE89370400440532013456'
        })
        
        assert result.is_valid is False
        assert any('swift_code' in error for error in result.errors)
        assert any('Missing' in error for error in result.errors)
    
    # IN (India) Validation Tests
    
    def test_in_ifsc_code_valid(self):
        """Test IN IFSC code validation with valid input"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('IN', {
            'ifsc_code': 'SBIN0001234',
            'account_number': '12345678901234'
        })
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_in_ifsc_code_invalid_fifth_char_not_zero(self):
        """Test IN IFSC code validation rejects non-zero fifth character"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('IN', {
            'ifsc_code': 'SBIN1001234',  # Fifth char should be 0
            'account_number': '12345678901234'
        })
        
        assert result.is_valid is False
        assert any('ifsc_code' in error for error in result.errors)
    
    def test_in_ifsc_code_invalid_too_short(self):
        """Test IN IFSC code validation with too short input"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('IN', {
            'ifsc_code': 'SBIN0001',  # Too short
            'account_number': '12345678901234'
        })
        
        assert result.is_valid is False
        assert any('ifsc_code' in error for error in result.errors)
    
    def test_in_ifsc_code_invalid_lowercase(self):
        """Test IN IFSC code validation rejects lowercase"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('IN', {
            'ifsc_code': 'sbin0001234',  # Lowercase
            'account_number': '12345678901234'
        })
        
        assert result.is_valid is False
        assert any('ifsc_code' in error for error in result.errors)
    
    def test_in_missing_ifsc_code(self):
        """Test IN validation fails when IFSC code is missing"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('IN', {
            'account_number': '12345678901234'
        })
        
        assert result.is_valid is False
        assert any('ifsc_code' in error for error in result.errors)
        assert any('Missing' in error for error in result.errors)
    
    # AU (Australia) Validation Tests
    
    def test_au_bsb_number_valid(self):
        """Test AU BSB number validation with valid input"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('AU', {
            'bsb_number': '123-456',
            'account_number': '123456789'
        })
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_au_bsb_number_invalid_format(self):
        """Test AU BSB number validation with invalid format"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('AU', {
            'bsb_number': '123456',  # Missing dash
            'account_number': '123456789'
        })
        
        assert result.is_valid is False
        assert any('bsb_number' in error for error in result.errors)
    
    def test_au_bsb_number_invalid_wrong_dash_position(self):
        """Test AU BSB number validation with wrong dash position"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('AU', {
            'bsb_number': '12-3456',  # Wrong dash position
            'account_number': '123456789'
        })
        
        assert result.is_valid is False
        assert any('bsb_number' in error for error in result.errors)
    
    def test_au_missing_bsb_number(self):
        """Test AU validation fails when BSB number is missing"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('AU', {
            'account_number': '123456789'
        })
        
        assert result.is_valid is False
        assert any('bsb_number' in error for error in result.errors)
        assert any('Missing' in error for error in result.errors)
    
    # Unsupported Country Tests
    
    def test_unsupported_country_code(self):
        """Test validation fails for unsupported country code"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('XX', {
            'account_number': '123456789'
        })
        
        assert result.is_valid is False
        assert any('not supported' in error for error in result.errors)
        assert any('XX' in error for error in result.errors)
    
    # Helper Method Tests
    
    def test_get_required_fields_us(self):
        """Test get_required_fields returns correct fields for US"""
        validator = CountryValidator()
        
        fields = validator.get_required_fields('US')
        
        assert 'routing_number' in fields
        assert 'account_number' in fields
        assert len(fields) == 2
    
    def test_get_required_fields_gb(self):
        """Test get_required_fields returns correct fields for GB"""
        validator = CountryValidator()
        
        fields = validator.get_required_fields('GB')
        
        assert 'sort_code' in fields
        assert 'account_number' in fields
        assert len(fields) == 2
    
    def test_get_required_fields_de(self):
        """Test get_required_fields returns correct fields for DE"""
        validator = CountryValidator()
        
        fields = validator.get_required_fields('DE')
        
        assert 'iban' in fields
        assert 'swift_code' in fields
        assert len(fields) == 2
    
    def test_get_required_fields_in(self):
        """Test get_required_fields returns correct fields for IN"""
        validator = CountryValidator()
        
        fields = validator.get_required_fields('IN')
        
        assert 'ifsc_code' in fields
        assert 'account_number' in fields
        assert len(fields) == 2
    
    def test_get_required_fields_au(self):
        """Test get_required_fields returns correct fields for AU"""
        validator = CountryValidator()
        
        fields = validator.get_required_fields('AU')
        
        assert 'bsb_number' in fields
        assert 'account_number' in fields
        assert len(fields) == 2
    
    def test_get_required_fields_unsupported_country(self):
        """Test get_required_fields returns empty list for unsupported country"""
        validator = CountryValidator()
        
        fields = validator.get_required_fields('XX')
        
        assert fields == []
    
    def test_get_field_patterns_us(self):
        """Test get_field_patterns returns correct patterns for US"""
        validator = CountryValidator()
        
        patterns = validator.get_field_patterns('US')
        
        assert 'routing_number' in patterns
        assert patterns['routing_number'] == r'^\d{9}$'
    
    def test_get_field_patterns_de(self):
        """Test get_field_patterns returns correct patterns for DE"""
        validator = CountryValidator()
        
        patterns = validator.get_field_patterns('DE')
        
        assert 'iban' in patterns
        assert 'swift_code' in patterns
        assert len(patterns) == 2
    
    def test_get_field_patterns_unsupported_country(self):
        """Test get_field_patterns returns empty dict for unsupported country"""
        validator = CountryValidator()
        
        patterns = validator.get_field_patterns('XX')
        
        assert patterns == {}
    
    def test_get_supported_countries(self):
        """Test get_supported_countries returns all supported countries"""
        validator = CountryValidator()
        
        countries = validator.get_supported_countries()
        
        assert 'US' in countries
        assert 'GB' in countries
        assert 'DE' in countries
        assert 'IN' in countries
        assert 'AU' in countries
        assert len(countries) == 5
    
    # Singleton Tests
    
    def test_get_country_validator_singleton(self):
        """Test get_country_validator returns singleton instance"""
        validator1 = get_country_validator()
        validator2 = get_country_validator()
        
        assert validator1 is validator2
    
    # Edge Cases
    
    def test_empty_banking_details(self):
        """Test validation with empty banking details"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('US', {})
        
        assert result.is_valid is False
        assert len(result.errors) >= 2  # Missing both required fields
    
    def test_none_values_in_banking_details(self):
        """Test validation with None values"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('US', {
            'routing_number': None,
            'account_number': None
        })
        
        assert result.is_valid is False
        assert len(result.errors) >= 2
    
    def test_extra_fields_ignored(self):
        """Test that extra fields don't affect validation"""
        validator = CountryValidator()
        
        result = validator.validate_banking_info('US', {
            'routing_number': '123456789',
            'account_number': '1234567890',
            'extra_field': 'should be ignored',
            'another_field': 'also ignored'
        })
        
        assert result.is_valid is True
        assert len(result.errors) == 0
    
    def test_validation_result_dataclass(self):
        """Test ValidationResult dataclass structure"""
        result = ValidationResult(is_valid=True, errors=[])
        
        assert result.is_valid is True
        assert result.errors == []
        assert isinstance(result.errors, list)
    
    def test_country_banking_rules_structure(self):
        """Test COUNTRY_BANKING_RULES has expected structure"""
        assert 'US' in COUNTRY_BANKING_RULES
        assert 'required_fields' in COUNTRY_BANKING_RULES['US']
        assert 'patterns' in COUNTRY_BANKING_RULES['US']
        assert isinstance(COUNTRY_BANKING_RULES['US']['required_fields'], list)
        assert isinstance(COUNTRY_BANKING_RULES['US']['patterns'], dict)
