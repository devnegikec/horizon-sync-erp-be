"""
Country Validator Service for Bank Integration Module

Validates banking information according to country-specific rules and patterns.
Supports US, GB, DE (EU), IN, and AU banking standards.

Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """
    Result of banking information validation.
    
    Attributes:
        is_valid: Whether the validation passed
        errors: List of error messages describing validation failures
    """
    is_valid: bool
    errors: List[str]


# Country-specific banking rules configuration
# Maps country codes to required fields and validation patterns
COUNTRY_BANKING_RULES = {
    "US": {
        "required_fields": ["routing_number", "account_number"],
        "patterns": {
            "routing_number": r"^\d{9}$"
        }
    },
    "GB": {
        "required_fields": ["sort_code", "account_number"],
        "patterns": {
            "sort_code": r"^\d{2}-\d{2}-\d{2}$"
        }
    },
    "DE": {  # Example EU country
        "required_fields": ["iban", "swift_code"],
        "patterns": {
            "iban": r"^[A-Z]{2}\d{2}[A-Z0-9]{11,30}$",
            "swift_code": r"^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$"
        }
    },
    "IN": {
        "required_fields": ["ifsc_code", "account_number"],
        "patterns": {
            "ifsc_code": r"^[A-Z]{4}0[A-Z0-9]{6}$"
        }
    },
    "AU": {
        "required_fields": ["bsb_number", "account_number"],
        "patterns": {
            "bsb_number": r"^\d{3}-\d{3}$"
        }
    }
}


class CountryValidator:
    """
    Validator for country-specific banking information.
    
    Validates banking details according to country-specific rules including
    required fields and format patterns for routing numbers, IBANs, SWIFT codes,
    and other country-specific identifiers.
    """
    
    def __init__(self):
        """Initialize the country validator with banking rules configuration."""
        self.rules = COUNTRY_BANKING_RULES
    
    def validate_banking_info(
        self,
        country_code: str,
        banking_details: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate banking information according to country-specific rules.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code (e.g., "US", "GB", "DE")
            banking_details: Dictionary containing banking field values
            
        Returns:
            ValidationResult with is_valid flag and list of error messages
            
        Examples:
            >>> validator = CountryValidator()
            >>> result = validator.validate_banking_info('US', {
            ...     'routing_number': '123456789',
            ...     'account_number': '1234567890'
            ... })
            >>> result.is_valid
            True
            
            >>> result = validator.validate_banking_info('US', {
            ...     'routing_number': '12345',  # Invalid: too short
            ...     'account_number': '1234567890'
            ... })
            >>> result.is_valid
            False
            >>> result.errors
            ['Invalid routing_number format. Expected pattern: ^\\d{9}$']
            
        Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10
        """
        errors = []
        
        # Check if country code is supported
        if country_code not in self.rules:
            errors.append(
                f"Country code '{country_code}' is not supported. "
                f"Supported countries: {', '.join(self.rules.keys())}"
            )
            return ValidationResult(is_valid=False, errors=errors)
        
        country_rules = self.rules[country_code]
        required_fields = country_rules.get("required_fields", [])
        patterns = country_rules.get("patterns", {})
        
        # Check required fields are present
        for field in required_fields:
            if not banking_details.get(field):
                errors.append(
                    f"Missing required field '{field}' for country {country_code}"
                )
        
        # Validate field patterns
        for field, pattern in patterns.items():
            field_value = banking_details.get(field)
            
            # Skip pattern validation if field is missing (already reported above)
            if not field_value:
                continue
            
            # Validate against pattern
            if not re.match(pattern, str(field_value)):
                errors.append(
                    f"Invalid {field} format. Expected pattern: {pattern}"
                )
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors
        )
    
    def get_required_fields(self, country_code: str) -> List[str]:
        """
        Get the list of required fields for a specific country.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code
            
        Returns:
            List of required field names for the country
            
        Examples:
            >>> validator = CountryValidator()
            >>> validator.get_required_fields('US')
            ['routing_number', 'account_number']
            
            >>> validator.get_required_fields('GB')
            ['sort_code', 'account_number']
            
        Requirements: 5.10
        """
        if country_code not in self.rules:
            return []
        
        return self.rules[country_code].get("required_fields", [])
    
    def get_field_patterns(self, country_code: str) -> Dict[str, str]:
        """
        Get the validation patterns for a specific country.
        
        Args:
            country_code: ISO 3166-1 alpha-2 country code
            
        Returns:
            Dictionary mapping field names to regex patterns
            
        Examples:
            >>> validator = CountryValidator()
            >>> validator.get_field_patterns('US')
            {'routing_number': '^\\\\d{9}$'}
            
            >>> validator.get_field_patterns('DE')
            {'iban': '^[A-Z]{2}\\\\d{2}[A-Z0-9]{11,30}$', 'swift_code': '^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$'}
            
        Requirements: 5.10
        """
        if country_code not in self.rules:
            return {}
        
        return self.rules[country_code].get("patterns", {})
    
    def get_supported_countries(self) -> List[str]:
        """
        Get the list of all supported country codes.
        
        Returns:
            List of supported ISO 3166-1 alpha-2 country codes
            
        Example:
            >>> validator = CountryValidator()
            >>> validator.get_supported_countries()
            ['US', 'GB', 'DE', 'IN', 'AU']
        """
        return list(self.rules.keys())


# Singleton instance for application-wide use
_country_validator_instance: Optional[CountryValidator] = None


def get_country_validator() -> CountryValidator:
    """
    Get the singleton country validator instance.
    
    Returns:
        CountryValidator instance
    """
    global _country_validator_instance
    
    if _country_validator_instance is None:
        _country_validator_instance = CountryValidator()
    
    return _country_validator_instance
