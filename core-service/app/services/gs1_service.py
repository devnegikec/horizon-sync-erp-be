"""GS1 helpers — check digit and SSCC generation.

Implements the GS1 General Specifications check-digit algorithm and SSCC
(Serial Shipping Container Code, AI ``00``) construction used by the
serialized ASN (EDI 856 / DESADV) export.
"""

# Placeholder GS1 company prefix for internal/dev use. In production this
# should come from the organization's GS1 company prefix (a settings value or
# per-organization field).
DEFAULT_COMPANY_PREFIX = "0500000"


def calculate_check_digit(digits: str) -> str:
    """Compute the GS1 mod-10 check digit for a numeric string.

    Per GS1 General Specifications: starting from the rightmost position,
    multiply alternating digits by 3/1, sum, then take (10 - sum % 10) % 10.
    """
    if not digits or not digits.isdigit():
        raise ValueError("digits must be a non-empty numeric string")
    total = 0
    for idx, ch in enumerate(reversed(digits)):
        digit = int(ch)
        total += digit * 3 if idx % 2 == 0 else digit
    return str((10 - (total % 10)) % 10)


def generate_sscc(
    serial_reference: str,
    company_prefix: str | None = None,
    extension_digit: str = "0",
) -> str:
    """Generate an 18-digit SSCC.

    Args:
        serial_reference: Unique serial reference for the logistics unit.
        company_prefix: GS1 company prefix (defaults to
            :data:`DEFAULT_COMPANY_PREFIX`).
        extension_digit: SSCC extension digit (default ``"0"``).

    Returns:
        18-digit SSCC string.
    """
    prefix = (company_prefix or DEFAULT_COMPANY_PREFIX).strip()
    if not prefix.isdigit():
        raise ValueError("company_prefix must be numeric")
    serial = serial_reference.strip() or "0"
    if not serial.isdigit():
        raise ValueError("serial_reference must be numeric")

    body = extension_digit + prefix + serial
    if len(body) > 17:
        body = body[:17]
    body = body.ljust(17, "0")
    return body + calculate_check_digit(body)
