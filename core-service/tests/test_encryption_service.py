"""
Unit tests for EncryptionService

Tests encryption, decryption, and field masking functionality.
"""

import os
import pytest
from app.services.encryption_service import EncryptionService


class TestEncryptionService:
    """Test suite for EncryptionService"""
    
    def test_encryption_round_trip(self):
        """Test that encryption and decryption preserves data"""
        service = EncryptionService(master_key='test-key-12345')
        
        original = '1234567890'
        encrypted = service.encrypt_field(original)
        decrypted = service.decrypt_field(encrypted)
        
        assert decrypted == original
        assert encrypted != original  # Ensure it was actually encrypted
    
    def test_encrypt_empty_string(self):
        """Test encrypting empty string returns empty string"""
        service = EncryptionService(master_key='test-key-12345')
        
        encrypted = service.encrypt_field('')
        assert encrypted == ''
    
    def test_decrypt_empty_string(self):
        """Test decrypting empty string returns empty string"""
        service = EncryptionService(master_key='test-key-12345')
        
        decrypted = service.decrypt_field('')
        assert decrypted == ''
    
    def test_encryption_produces_different_output(self):
        """Test that encrypted value is different from plaintext"""
        service = EncryptionService(master_key='test-key-12345')
        
        plaintext = 'sensitive-data-123'
        encrypted = service.encrypt_field(plaintext)
        
        assert encrypted != plaintext
        assert len(encrypted) > 0
    
    def test_different_plaintexts_produce_different_ciphertexts(self):
        """Test that different inputs produce different encrypted outputs"""
        service = EncryptionService(master_key='test-key-12345')
        
        plaintext1 = 'account-number-1'
        plaintext2 = 'account-number-2'
        
        encrypted1 = service.encrypt_field(plaintext1)
        encrypted2 = service.encrypt_field(plaintext2)
        
        assert encrypted1 != encrypted2
    
    def test_mask_account_number_standard(self):
        """Test account number masking shows only last 4 digits"""
        service = EncryptionService(master_key='test-key-12345')
        
        account_number = '1234567890'
        masked = service.mask_account_number(account_number)
        
        assert masked == '******7890'
        assert len(masked) == len(account_number)
    
    def test_mask_account_number_short(self):
        """Test masking account number with 4 or fewer digits"""
        service = EncryptionService(master_key='test-key-12345')
        
        # 4 digits
        masked = service.mask_account_number('1234')
        assert masked == '****'
        
        # 3 digits
        masked = service.mask_account_number('123')
        assert masked == '***'
        
        # 1 digit
        masked = service.mask_account_number('1')
        assert masked == '*'
    
    def test_mask_account_number_empty(self):
        """Test masking empty account number"""
        service = EncryptionService(master_key='test-key-12345')
        
        masked = service.mask_account_number('')
        assert masked == ''
    
    def test_mask_iban_standard(self):
        """Test IBAN masking shows first 4 and last 4 characters"""
        service = EncryptionService(master_key='test-key-12345')
        
        iban = 'DE89370400440532013456'
        masked = service.mask_iban(iban)
        
        assert masked == 'DE89**************3456'
        assert len(masked) == len(iban)
        assert masked[:4] == iban[:4]
        assert masked[-4:] == iban[-4:]
    
    def test_mask_iban_short(self):
        """Test masking IBAN with 8 or fewer characters"""
        service = EncryptionService(master_key='test-key-12345')
        
        # 8 characters
        masked = service.mask_iban('DE891234')
        assert masked == '********'
        
        # 6 characters
        masked = service.mask_iban('DE8912')
        assert masked == '******'
        
        # 4 characters
        masked = service.mask_iban('DE89')
        assert masked == '****'
    
    def test_mask_iban_empty(self):
        """Test masking empty IBAN"""
        service = EncryptionService(master_key='test-key-12345')
        
        masked = service.mask_iban('')
        assert masked == ''
    
    def test_encryption_with_special_characters(self):
        """Test encryption handles special characters"""
        service = EncryptionService(master_key='test-key-12345')
        
        special_chars = 'ABC-123/456@789#XYZ'
        encrypted = service.encrypt_field(special_chars)
        decrypted = service.decrypt_field(encrypted)
        
        assert decrypted == special_chars
    
    def test_encryption_with_unicode(self):
        """Test encryption handles unicode characters"""
        service = EncryptionService(master_key='test-key-12345')
        
        unicode_text = 'Ñoño-Müller-北京'
        encrypted = service.encrypt_field(unicode_text)
        decrypted = service.decrypt_field(encrypted)
        
        assert decrypted == unicode_text
    
    def test_different_master_keys_produce_different_results(self):
        """Test that different master keys produce different encrypted outputs"""
        service1 = EncryptionService(master_key='key-1')
        service2 = EncryptionService(master_key='key-2')
        
        plaintext = 'test-data'
        encrypted1 = service1.encrypt_field(plaintext)
        encrypted2 = service2.encrypt_field(plaintext)
        
        assert encrypted1 != encrypted2
    
    def test_cannot_decrypt_with_wrong_key(self):
        """Test that decryption fails with wrong master key"""
        service1 = EncryptionService(master_key='key-1')
        service2 = EncryptionService(master_key='key-2')
        
        plaintext = 'test-data'
        encrypted = service1.encrypt_field(plaintext)
        
        # Attempting to decrypt with wrong key should raise an exception
        with pytest.raises(Exception):
            service2.decrypt_field(encrypted)
    
    def test_initialization_without_master_key_and_no_env_var(self):
        """Test that initialization fails without master key or env var"""
        # Temporarily remove env var if it exists
        original_key = os.environ.get('BANK_ENCRYPTION_KEY')
        if 'BANK_ENCRYPTION_KEY' in os.environ:
            del os.environ['BANK_ENCRYPTION_KEY']
        
        try:
            with pytest.raises(ValueError, match="Master encryption key not provided"):
                EncryptionService()
        finally:
            # Restore original env var if it existed
            if original_key:
                os.environ['BANK_ENCRYPTION_KEY'] = original_key
    
    def test_initialization_with_env_var(self):
        """Test that initialization works with environment variable"""
        # Set env var
        os.environ['BANK_ENCRYPTION_KEY'] = 'env-test-key'
        
        try:
            service = EncryptionService()
            
            # Test that it works
            plaintext = 'test-data'
            encrypted = service.encrypt_field(plaintext)
            decrypted = service.decrypt_field(encrypted)
            
            assert decrypted == plaintext
        finally:
            # Clean up
            if 'BANK_ENCRYPTION_KEY' in os.environ:
                del os.environ['BANK_ENCRYPTION_KEY']
    
    def test_mask_account_number_with_long_number(self):
        """Test masking very long account numbers"""
        service = EncryptionService(master_key='test-key-12345')
        
        long_account = '1234567890' * 5  # 50 digits
        masked = service.mask_account_number(long_account)
        
        assert masked.endswith('7890')
        assert masked.count('*') == len(long_account) - 4
    
    def test_mask_iban_with_various_formats(self):
        """Test IBAN masking with different country formats"""
        service = EncryptionService(master_key='test-key-12345')
        
        # German IBAN (22 chars)
        de_iban = 'DE89370400440532013456'
        masked = service.mask_iban(de_iban)
        assert masked == 'DE89**************3456'
        
        # UK IBAN (22 chars)
        gb_iban = 'GB29NWBK60161331926819'
        masked = service.mask_iban(gb_iban)
        assert masked == 'GB29**************6819'
        
        # French IBAN (27 chars)
        fr_iban = 'FR1420041010050500013M02606'
        masked = service.mask_iban(fr_iban)
        assert masked == 'FR14*******************2606'
