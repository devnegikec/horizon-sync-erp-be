"""Banking Security and Validation Enhancements

This file contains additional security and validation utilities for the banking integration.
"""

import hashlib
import hmac
import re


class BankingValidator:
    """Advanced validation for banking data"""

    # IBAN country code length mapping (partial list)
    IBAN_LENGTHS = {
        "AD": 24,
        "AE": 23,
        "AL": 28,
        "AT": 20,
        "AZ": 28,
        "BA": 20,
        "BE": 16,
        "BG": 22,
        "BH": 22,
        "BR": 29,
        "BY": 28,
        "CH": 21,
        "CR": 22,
        "CY": 28,
        "CZ": 24,
        "DE": 22,
        "DK": 18,
        "DO": 28,
        "EE": 20,
        "EG": 29,
        "ES": 24,
        "FI": 18,
        "FO": 18,
        "FR": 27,
        "GB": 22,
        "GE": 22,
        "GI": 23,
        "GL": 18,
        "GR": 27,
        "GT": 28,
        "HR": 21,
        "HU": 28,
        "IE": 22,
        "IL": 23,
        "IS": 26,
        "IT": 27,
        "JO": 30,
        "KW": 30,
        "KZ": 20,
        "LB": 28,
        "LC": 32,
        "LI": 21,
        "LT": 20,
        "LU": 20,
        "LV": 21,
        "MC": 27,
        "MD": 24,
        "ME": 22,
        "MK": 19,
        "MR": 27,
        "MT": 31,
        "MU": 30,
        "NL": 18,
        "NO": 15,
        "PK": 24,
        "PL": 28,
        "PS": 29,
        "PT": 25,
        "QA": 29,
        "RO": 24,
        "RS": 22,
        "SA": 24,
        "SE": 24,
        "SI": 19,
        "SK": 24,
        "SM": 27,
        "TN": 24,
        "TR": 26,
        "UA": 29,
        "VG": 24,
        "XK": 20,
    }

    @classmethod
    def validate_iban_checksum(cls, iban: str) -> bool:
        """Validate IBAN using mod-97 checksum algorithm"""
        if not iban:
            return False

        # Remove spaces and convert to uppercase
        iban = iban.replace(" ", "").upper()

        # Check country code and length
        if len(iban) < 4:
            return False

        country_code = iban[:2]
        if country_code not in cls.IBAN_LENGTHS:
            return False

        if len(iban) != cls.IBAN_LENGTHS[country_code]:
            return False

        # Move first 4 characters to end
        rearranged = iban[4:] + iban[:4]

        # Convert letters to numbers (A=10, B=11, ..., Z=35)
        numeric_string = ""
        for char in rearranged:
            if char.isdigit():
                numeric_string += char
            else:
                numeric_string += str(ord(char) - ord("A") + 10)

        # Check mod 97
        return int(numeric_string) % 97 == 1

    @classmethod
    def validate_swift_code_format(cls, swift: str) -> bool:
        """Enhanced SWIFT code validation"""
        if not swift:
            return False

        swift = swift.upper().replace(" ", "")

        # SWIFT format: 4 chars bank + 2 chars country + 2 chars location + 3 chars branch (optional)
        if len(swift) not in [8, 11]:
            return False

        # Check format
        if not re.match(r"^[A-Z]{4}[A-Z]{2}[A-Z0-9]{2}([A-Z0-9]{3})?$", swift):
            return False

        # Additional validations can be added here (e.g., country code validation)
        return True

    @classmethod
    def validate_routing_number_checksum(cls, routing_number: str) -> bool:
        """Validate US routing number using checksum algorithm"""
        if not routing_number or len(routing_number) != 9:
            return False

        if not routing_number.isdigit():
            return False

        # ABA routing number checksum algorithm
        weights = [3, 7, 1, 3, 7, 1, 3, 7, 1]
        total = sum(
            int(digit) * weight for digit, weight in zip(routing_number, weights)
        )

        return total % 10 == 0

    @classmethod
    def mask_sensitive_data(cls, data: str, visible_chars: int = 4) -> str:
        """Mask sensitive data showing only last few characters"""
        if not data:
            return ""

        if len(data) <= visible_chars:
            return "*" * len(data)

        return "*" * (len(data) - visible_chars) + data[-visible_chars:]

    @classmethod
    def validate_account_number_format(
        cls, account_number: str, country_code: str | None = None
    ) -> bool:
        """Validate account number format based on country"""
        if not account_number:
            return False

        # Remove spaces and special characters for validation
        clean_number = re.sub(r"[^A-Za-z0-9]", "", account_number)

        if not clean_number:
            return False

        # Basic length validation (most account numbers are 8-20 characters)
        if len(clean_number) < 4 or len(clean_number) > 34:
            return False

        # Country-specific validations can be added here
        if country_code:
            if country_code == "US":
                # US account numbers are typically 8-17 digits
                return clean_number.isdigit() and 8 <= len(clean_number) <= 17
            elif country_code == "GB":
                # UK account numbers are typically 8 digits
                return clean_number.isdigit() and len(clean_number) == 8
            elif country_code == "DE":
                # German account numbers can be alphanumeric, up to 10 characters
                return len(clean_number) <= 10

        return True


class BankingSecurityUtils:
    """Security utilities for banking operations"""

    @staticmethod
    def generate_audit_hash(data: dict, secret_key: str) -> str:
        """Generate HMAC hash for audit trail integrity"""
        # Create canonical representation of data
        sorted_data = {k: v for k, v in sorted(data.items()) if v is not None}
        data_string = "|".join(f"{k}:{v}" for k, v in sorted_data.items())

        # Generate HMAC-SHA256 hash
        return hmac.new(
            secret_key.encode("utf-8"), data_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()

    @staticmethod
    def verify_audit_hash(data: dict, secret_key: str, expected_hash: str) -> bool:
        """Verify audit trail hash integrity"""
        calculated_hash = BankingSecurityUtils.generate_audit_hash(data, secret_key)
        return hmac.compare_digest(calculated_hash, expected_hash)

    @staticmethod
    def sanitize_banking_data(data: dict) -> dict:
        """Sanitize banking data for logging/audit (remove/mask sensitive fields)"""
        sensitive_fields = {
            "account_number",
            "iban",
            "swift_code",
            "routing_number",
            "sort_code",
            "bsb_number",
            "bank_api_credentials_id",
        }

        sanitized = {}
        for key, value in data.items():
            if key in sensitive_fields and value:
                if key in ["account_number", "iban"]:
                    sanitized[key] = BankingValidator.mask_sensitive_data(str(value))
                else:
                    sanitized[key] = "***REDACTED***"
            else:
                sanitized[key] = value

        return sanitized

    @staticmethod
    def validate_organization_access(user_org_id: str, resource_org_id: str) -> bool:
        """Validate that user can access resources from their organization only"""
        return user_org_id == resource_org_id

    @staticmethod
    def check_banking_permissions(user_roles: list, required_permission: str) -> bool:
        """Check if user has required banking permissions"""
        banking_permissions = {
            "view:banking_summary": [
                "accountant",
                "finance_manager",
                "treasurer",
                "admin",
            ],
            "view:banking_details": ["finance_manager", "treasurer", "admin"],
            "edit:banking_details": ["finance_manager", "treasurer", "admin"],
            "delete:banking_links": ["treasurer", "admin"],
            "manage:banking_api": ["treasurer", "admin"],
        }

        allowed_roles = banking_permissions.get(required_permission, [])
        return any(role in allowed_roles for role in user_roles)


class BankingDataEncryption:
    """Placeholder for banking data encryption utilities

    In a production environment, you would integrate with:
    - AWS KMS, Azure Key Vault, or HashiCorp Vault for key management
    - Field-level encryption libraries like SQLAlchemy-Utils' EncryptedType
    - Application-level encryption using Fernet (symmetric) or RSA (asymmetric)
    """

    @staticmethod
    def encrypt_field(value: str, encryption_key: str) -> str:
        """Placeholder for field encryption"""
        # TODO: Implement actual encryption
        # This is just a placeholder - do NOT use in production
        return f"ENCRYPTED:{value}"

    @staticmethod
    def decrypt_field(encrypted_value: str, encryption_key: str) -> str:
        """Placeholder for field decryption"""
        # TODO: Implement actual decryption
        # This is just a placeholder - do NOT use in production
        if encrypted_value.startswith("ENCRYPTED:"):
            return encrypted_value[10:]
        return encrypted_value


# Example usage and configuration
BANKING_SECURITY_CONFIG = {
    "encryption": {
        "algorithm": "AES-256-GCM",
        "key_rotation_days": 90,
        "backup_encryption": True,
    },
    "audit": {
        "hash_algorithm": "HMAC-SHA256",
        "integrity_checks": True,
        "retention_years": 7,
    },
    "validation": {
        "strict_iban_validation": True,
        "swift_code_verification": True,
        "routing_number_checksum": True,
        "account_format_validation": True,
    },
    "access_control": {
        "require_mfa_for_banking": True,
        "session_timeout_minutes": 30,
        "max_failed_attempts": 3,
    },
}
