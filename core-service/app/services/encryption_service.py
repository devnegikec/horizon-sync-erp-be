"""
Encryption Service for Bank Integration Module

Provides AES-256 encryption for sensitive banking fields using Fernet symmetric encryption
with PBKDF2 key derivation. Also provides field masking methods for display purposes.

Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8
"""

import base64
import os
from typing import Optional

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


class EncryptionService:
    """
    Service for encrypting and decrypting sensitive banking information.
    
    Uses AES-256 encryption via Fernet with PBKDF2 key derivation from a master key.
    The master key should be stored in environment variables (BANK_ENCRYPTION_KEY).
    
    Encrypted fields:
    - account_number
    - iban
    - routing_number
    - swift_code
    - ifsc_code
    - sort_code
    - bsb_number
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize the encryption service.
        
        Args:
            master_key: Master encryption key. If not provided, reads from 
                       BANK_ENCRYPTION_KEY environment variable.
        
        Raises:
            ValueError: If master_key is not provided and BANK_ENCRYPTION_KEY 
                       environment variable is not set.
        """
        if master_key is None:
            master_key = os.getenv('BANK_ENCRYPTION_KEY')
            if not master_key:
                raise ValueError(
                    "Master encryption key not provided. Set BANK_ENCRYPTION_KEY "
                    "environment variable or pass master_key parameter."
                )
        
        # Use a fixed salt for key derivation
        # In production, this should be from configuration
        salt = b'banking_encryption_salt_v1'
        
        # Derive encryption key from master key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # 32 bytes = 256 bits for AES-256
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.cipher = Fernet(key)
    
    def encrypt_field(self, plaintext: str) -> str:
        """
        Encrypt a field value using AES-256.
        
        Args:
            plaintext: The plain text value to encrypt
            
        Returns:
            Base64-encoded encrypted value
            
        Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
        """
        if not plaintext:
            return ""
        
        # Encrypt the plaintext
        encrypted = self.cipher.encrypt(plaintext.encode())
        
        # Return base64-encoded encrypted value
        return base64.b64encode(encrypted).decode()
    
    def decrypt_field(self, ciphertext: str) -> str:
        """
        Decrypt a field value.
        
        Args:
            ciphertext: Base64-encoded encrypted value
            
        Returns:
            Decrypted plain text value
            
        Requirements: 15.1, 15.2, 15.3, 15.4, 15.5
        """
        if not ciphertext:
            return ""
        
        # Decode from base64
        encrypted = base64.b64decode(ciphertext.encode())
        
        # Decrypt and return
        decrypted = self.cipher.decrypt(encrypted)
        return decrypted.decode()
    
    def mask_account_number(self, account_number: str) -> str:
        """
        Mask account number showing only the last 4 digits.
        
        Args:
            account_number: The account number to mask
            
        Returns:
            Masked account number (e.g., "******1234")
            
        Example:
            >>> service.mask_account_number("1234567890")
            "******1234"
            
        Requirements: 15.7
        """
        if not account_number:
            return ""
        
        if len(account_number) <= 4:
            return "*" * len(account_number)
        
        return "*" * (len(account_number) - 4) + account_number[-4:]
    
    def mask_iban(self, iban: str) -> str:
        """
        Mask IBAN showing only the first 4 and last 4 characters.
        
        Args:
            iban: The IBAN to mask
            
        Returns:
            Masked IBAN (e.g., "DE89************3456")
            
        Example:
            >>> service.mask_iban("DE89370400440532013456")
            "DE89**************3456"
            
        Requirements: 15.8
        """
        if not iban:
            return ""
        
        if len(iban) <= 8:
            return "*" * len(iban)
        
        return iban[:4] + "*" * (len(iban) - 8) + iban[-4:]


# Singleton instance for application-wide use
_encryption_service_instance: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """
    Get the singleton encryption service instance.
    
    Returns:
        EncryptionService instance
        
    Raises:
        ValueError: If BANK_ENCRYPTION_KEY environment variable is not set
    """
    global _encryption_service_instance
    
    if _encryption_service_instance is None:
        _encryption_service_instance = EncryptionService()
    
    return _encryption_service_instance
