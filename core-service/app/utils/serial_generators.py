"""
Serial number generation utilities and QR signing/URL helpers.

Provides:
- R6DAN: 6-char random alphanumeric (uppercase + digits)
- R4DAN: 4-char random alphanumeric (uppercase + digits)
- S8DN: zero-padded 8-digit sequential
- S10DN: zero-padded 10-digit sequential
- sign_qr_item: signs a serial number with ECDSA, returns (signature_b64, timestamp_ms)
- build_qr_url: constructs a QR verification URL

Requirements: 7.1, 7.2, 7.3, 7.4
"""

import secrets
import string
import time
from typing import Generator

from cryptography.hazmat.primitives.asymmetric import ec

# Character set for random alphanumeric generators
_ALPHANUMERIC = string.ascii_uppercase + string.digits


def generate_r6dan() -> str:
    """Generate a 6-character random alphanumeric serial (uppercase letters + digits)."""
    return "".join(secrets.choice(_ALPHANUMERIC) for _ in range(6))


def generate_r4dan() -> str:
    """Generate a 4-character random alphanumeric serial (uppercase letters + digits)."""
    return "".join(secrets.choice(_ALPHANUMERIC) for _ in range(4))


def sequential_s8dn(start: int = 1) -> Generator[str, None, None]:
    """Yield zero-padded 8-digit sequential serial numbers starting from `start`.

    Example: start=1 → "00000001", "00000002", ...
    """
    current = start
    while True:
        yield f"{current:08d}"
        current += 1


def sequential_s10dn(start: int = 1) -> Generator[str, None, None]:
    """Yield zero-padded 10-digit sequential serial numbers starting from `start`.

    Example: start=1 → "0000000001", "0000000002", ...
    """
    current = start
    while True:
        yield f"{current:010d}"
        current += 1


def sign_qr_item(
    key_service,
    private_key: ec.EllipticCurvePrivateKey,
    serial_number: str,
) -> tuple[str, int]:
    """Sign a QR item and return (base64_signature, timestamp_ms).

    Builds the message as ``{serial_number}~{timestamp_ms}``, signs it via
    ``key_service.sign_message()``, and returns the signature with the
    timestamp used.

    Args:
        key_service: A KeyService instance with a ``sign_message`` method.
        private_key: The decrypted ECDSA P-256 private key.
        serial_number: The serial number to include in the signed message.

    Returns:
        A tuple of (base64-encoded signature string, timestamp in milliseconds).
    """
    timestamp_ms = int(time.time() * 1000)
    message = f"{serial_number}~{timestamp_ms}"
    signature_b64 = key_service.sign_message(private_key, message)
    return signature_b64, timestamp_ms


def build_qr_url(
    org_short_code: str,
    domain: str,
    gtin: str,
    serial_number: str,
    timestamp: int,
    signature: str,
) -> str:
    """Build a QR verification URL.

    Returns:
        URL in the format:
        ``https://{org_short_code}.{domain}/g/{gtin}/s/{serial_number}/{timestamp}?c={signature}``
    """
    return (
        f"https://{org_short_code}.{domain}"
        f"/g/{gtin}/s/{serial_number}/{timestamp}?c={signature}"
    )
