"""
Key Service for ECDSA P-256 key pair generation, encryption, signing, and verification.

Provides:
- ECDSA P-256 key pair generation with Fernet-encrypted private keys
- Private key decryption for signing operations
- Message signing with ECDSA P-256 + SHA-256
- Signature verification using public key hex

Requirements: 1.2, 1.3, 1.4, 12.1, 12.2, 12.4, 12.5
"""

import base64

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature


class KeyService:
    """
    Stateless utility for ECDSA P-256 key pair generation,
    Fernet encryption of private keys, signing, and verification.
    """

    def __init__(self, encryption_secret: str):
        """
        Initialize KeyService with a Fernet encryption key.

        Args:
            encryption_secret: A valid Fernet key (base64-encoded 32-byte key)
                             used to encrypt/decrypt private keys at rest.

        Raises:
            ValueError: If encryption_secret is empty or invalid.
        """
        if not encryption_secret:
            raise ValueError(
                "encryption_secret must be provided. "
                "Set BRAND_KEY_ENCRYPTION_SECRET in environment."
            )
        self._fernet = Fernet(encryption_secret.encode() if isinstance(encryption_secret, str) else encryption_secret)

    def generate_key_pair(self) -> tuple[str, str]:
        """
        Generate an ECDSA P-256 key pair.

        Returns:
            Tuple of (encrypted_private_key, public_key_hex):
            - encrypted_private_key: Fernet-encrypted hex of the private key scalar
            - public_key_hex: Uncompressed X9.62 hex string (starts with "04", 130 chars)
        """
        private_key = ec.generate_private_key(ec.SECP256R1())

        # Serialize private key as raw hex of the private scalar
        private_numbers = private_key.private_numbers()
        private_hex = format(private_numbers.private_value, '064x')

        # Encrypt the private key hex with Fernet
        encrypted_private = self._fernet.encrypt(private_hex.encode()).decode()

        # Serialize public key as uncompressed X9.62 hex
        public_key_bytes = private_key.public_key().public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint,
        )
        public_key_hex = public_key_bytes.hex()

        return encrypted_private, public_key_hex

    def decrypt_private_key(self, encrypted_private: str) -> ec.EllipticCurvePrivateKey:
        """
        Decrypt a Fernet-encrypted private key and reconstruct the EC private key.

        Args:
            encrypted_private: Fernet-encrypted hex string of the private scalar.

        Returns:
            An ec.EllipticCurvePrivateKey object ready for signing.

        Raises:
            cryptography.fernet.InvalidToken: If decryption fails.
            ValueError: If the decrypted data is not a valid private key.
        """
        private_hex = self._fernet.decrypt(encrypted_private.encode()).decode()
        private_value = int(private_hex, 16)

        private_key = ec.derive_private_key(private_value, ec.SECP256R1())
        return private_key

    def sign_message(self, private_key: ec.EllipticCurvePrivateKey, message: str) -> str:
        """
        Sign a message with ECDSA P-256 + SHA-256.

        Args:
            private_key: The ECDSA P-256 private key to sign with.
            message: The plaintext message to sign.

        Returns:
            Base64-encoded DER signature string.
        """
        signature_bytes = private_key.sign(
            message.encode(),
            ec.ECDSA(hashes.SHA256()),
        )
        return base64.b64encode(signature_bytes).decode()

    def verify_signature(self, public_key_hex: str, message: str, signature_b64: str) -> bool:
        """
        Verify an ECDSA signature against a public key and message.

        Args:
            public_key_hex: Uncompressed X9.62 hex-encoded public key.
            message: The original plaintext message that was signed.
            signature_b64: Base64-encoded DER signature.

        Returns:
            True if the signature is valid, False otherwise.
        """
        try:
            public_key_bytes = bytes.fromhex(public_key_hex)
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(
                ec.SECP256R1(), public_key_bytes
            )
            signature_bytes = base64.b64decode(signature_b64)
            public_key.verify(
                signature_bytes,
                message.encode(),
                ec.ECDSA(hashes.SHA256()),
            )
            return True
        except Exception:
            return False
