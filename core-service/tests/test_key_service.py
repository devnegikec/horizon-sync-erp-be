"""
Unit tests for KeyService.

Tests ECDSA P-256 key pair generation, Fernet encryption round-trip,
message signing, and signature verification.
"""

import base64

import pytest
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization

from app.services.key_service import KeyService


@pytest.fixture
def fernet_key() -> str:
    """Generate a valid Fernet key for testing."""
    return Fernet.generate_key().decode()


@pytest.fixture
def key_service(fernet_key: str) -> KeyService:
    """Create a KeyService instance with a test Fernet key."""
    return KeyService(encryption_secret=fernet_key)


class TestKeyServiceInit:
    """Tests for KeyService initialization."""

    def test_init_with_valid_key(self, fernet_key: str):
        service = KeyService(encryption_secret=fernet_key)
        assert service is not None

    def test_init_with_empty_secret_raises(self):
        with pytest.raises(ValueError, match="encryption_secret must be provided"):
            KeyService(encryption_secret="")

    def test_init_with_invalid_fernet_key_raises(self):
        with pytest.raises(Exception):
            ks = KeyService(encryption_secret="not-a-valid-fernet-key")
            # Fernet validates lazily on some versions, force usage
            ks.generate_key_pair()


class TestGenerateKeyPair:
    """Tests for generate_key_pair method."""

    def test_returns_tuple_of_two_strings(self, key_service: KeyService):
        encrypted_private, public_hex = key_service.generate_key_pair()
        assert isinstance(encrypted_private, str)
        assert isinstance(public_hex, str)

    def test_public_key_starts_with_04(self, key_service: KeyService):
        _, public_hex = key_service.generate_key_pair()
        assert public_hex.startswith("04")

    def test_public_key_is_130_hex_chars(self, key_service: KeyService):
        _, public_hex = key_service.generate_key_pair()
        assert len(public_hex) == 130

    def test_public_key_is_valid_hex(self, key_service: KeyService):
        _, public_hex = key_service.generate_key_pair()
        # Should not raise
        bytes.fromhex(public_hex)

    def test_encrypted_private_differs_from_plaintext(self, key_service: KeyService):
        encrypted_private, _ = key_service.generate_key_pair()
        # Encrypted form should not be a raw 64-char hex (the plaintext format)
        assert len(encrypted_private) != 64

    def test_two_key_pairs_are_different(self, key_service: KeyService):
        _, pub1 = key_service.generate_key_pair()
        _, pub2 = key_service.generate_key_pair()
        assert pub1 != pub2


class TestDecryptPrivateKey:
    """Tests for decrypt_private_key method."""

    def test_decrypt_returns_ec_private_key(self, key_service: KeyService):
        encrypted_private, _ = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_private)
        assert isinstance(private_key, ec.EllipticCurvePrivateKey)

    def test_decrypted_key_derives_same_public_key(self, key_service: KeyService):
        encrypted_private, public_hex = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_private)

        # Derive public key from decrypted private key
        derived_pub_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        derived_pub_hex = derived_pub_bytes.hex()

        assert derived_pub_hex == public_hex

    def test_decrypt_with_wrong_key_raises(self, fernet_key: str):
        service1 = KeyService(encryption_secret=fernet_key)
        encrypted_private, _ = service1.generate_key_pair()

        other_key = Fernet.generate_key().decode()
        service2 = KeyService(encryption_secret=other_key)

        with pytest.raises(Exception):
            service2.decrypt_private_key(encrypted_private)


class TestSignMessage:
    """Tests for sign_message method."""

    def test_sign_returns_base64_string(self, key_service: KeyService):
        encrypted_private, _ = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_private)

        signature = key_service.sign_message(private_key, "test~1234567890")
        assert isinstance(signature, str)
        # Should be valid base64
        base64.b64decode(signature)

    def test_sign_different_messages_produce_different_signatures(self, key_service: KeyService):
        encrypted_private, _ = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_private)

        sig1 = key_service.sign_message(private_key, "msg1~100")
        sig2 = key_service.sign_message(private_key, "msg2~200")
        assert sig1 != sig2


class TestVerifySignature:
    """Tests for verify_signature method."""

    def test_valid_signature_returns_true(self, key_service: KeyService):
        encrypted_private, public_hex = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_private)

        message = "SN12345~1718000000000"
        signature = key_service.sign_message(private_key, message)

        assert key_service.verify_signature(public_hex, message, signature) is True

    def test_tampered_message_returns_false(self, key_service: KeyService):
        encrypted_private, public_hex = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_private)

        message = "SN12345~1718000000000"
        signature = key_service.sign_message(private_key, message)

        assert key_service.verify_signature(public_hex, "TAMPERED~999", signature) is False

    def test_wrong_public_key_returns_false(self, key_service: KeyService):
        encrypted_private, _ = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_private)

        message = "SN12345~1718000000000"
        signature = key_service.sign_message(private_key, message)

        # Generate a different key pair
        _, other_public_hex = key_service.generate_key_pair()

        assert key_service.verify_signature(other_public_hex, message, signature) is False

    def test_invalid_signature_returns_false(self, key_service: KeyService):
        _, public_hex = key_service.generate_key_pair()
        bad_sig = base64.b64encode(b"not-a-real-signature").decode()

        assert key_service.verify_signature(public_hex, "msg~123", bad_sig) is False

    def test_invalid_public_key_hex_returns_false(self, key_service: KeyService):
        assert key_service.verify_signature("invalid_hex", "msg~123", "dGVzdA==") is False

    def test_sign_then_verify_round_trip(self, key_service: KeyService):
        """Full round-trip: generate, decrypt, sign, verify."""
        encrypted_private, public_hex = key_service.generate_key_pair()
        private_key = key_service.decrypt_private_key(encrypted_private)

        message = "ABC123~1718000000000"
        signature = key_service.sign_message(private_key, message)

        assert key_service.verify_signature(public_hex, message, signature) is True
