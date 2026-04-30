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
from collections.abc import Generator
import logging
import re
from urllib.parse import quote

import httpx
from fastapi import HTTPException, status

SERIAL_PATTERN = re.compile(r"/s/([^/?]+)")

from cryptography.hazmat.primitives.asymmetric import ec

logger = logging.getLogger(__name__)
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
    base_url: str = "",
) -> str:
    """Build a QR verification URL.

    Args:
        org_short_code: Brand short code (e.g. "amc").
        domain: QR domain (e.g. "verify.example.com"). Only used when base_url is empty.
        gtin: Product GTIN.
        serial_number: Unique serial number.
        timestamp: Unix timestamp in milliseconds.
        signature: ECDSA signature (base64).
        base_url: Optional full base URL override (scheme+host, no trailing slash).
                   When provided, used directly instead of ``https://{org_short_code}.{domain}``.

    Returns:
        URL in the format:
        ``{base_url}/g/{gtin}/s/{serial_number}/{timestamp}?c={signature}``
        or when base_url is empty:
        ``https://{org_short_code}.{domain}/g/{gtin}/s/{serial_number}/{timestamp}?c={signature}``
    """
    if base_url:
        return f"{base_url}/g/{gtin}/s/{serial_number}/{timestamp}?c={quote(signature, safe='')}"
    return (
        f"https://{org_short_code}.{domain}"
        f"/g/{gtin}/s/{serial_number}/{timestamp}?c={quote(signature, safe='')}"
    )




def build_long_qr_url(
    domain: str,
    gtin: str,
    serial_number: str,
    timestamp: int,
    signature: str,
) -> str:
    """Build a QR verification URL.

    Returns:
        URL in the format:
        ``https://{domain}/g/{gtin}/s/{serial_number}/{timestamp}?c={signature}``
    """
    return (
        f"https://{domain}"
        f"/g/{gtin}/s/{serial_number}/{timestamp}?c={signature}"
    )



async def resolve_serial_from_short_url(short_url: str) -> str:
    """
    Resolve serial number from a short QR URL.

    Strategy: read the Location header from the 301 redirect directly
    instead of following it — the redirect target may not be publicly
    reachable but the serial number is always in the Location URL.
    """
    try:
        async with httpx.AsyncClient(
            follow_redirects=False,   
            timeout=10.0,
        ) as client:
            response = await client.get(short_url)

            # Get Location header from 301/302 response
            if response.status_code in (301, 302, 307, 308):
                location = response.headers.get("location")
                if not location:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No redirect location found in response",
                    )
            else:
                # Already at final URL
                location = str(response.url)

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="URL resolution timed out",
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to reach URL: {str(e)}",
        )

    # Extract serial from /s/{serial} in the Location URL
    match = SERIAL_PATTERN.search(location)
    if not match:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Could not extract serial number from URL: {location}",
        )

    serial = match.group(1)
    return serial
