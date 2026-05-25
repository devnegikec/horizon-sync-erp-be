"""QR payload decoding and validation utility.

Decodes self-contained QR payloads embedded in box/item QR codes.
The payload is a JSON string containing SKU, quantity, and batch information.

QR Payload Format:
{
    "id": "unique-qr-identifier",
    "sku": "ITEM-001",
    "qty": 50,
    "batch": "BATCH-2025-01",
    "packaging_unit_qr_id": "BOX-12-WIDGET"  // optional
}

Requirements: 4.1, 4.2, 4.3, 5.3
"""

import json
from dataclasses import dataclass, field

from app.core.exceptions import ValidationError


@dataclass
class QRPayload:
    """Structured representation of a decoded QR code payload.

    Attributes:
        id: Unique QR code identifier
        sku: Stock Keeping Unit identifier (non-empty string)
        qty: Item quantity (positive integer)
        batch: Batch number (non-empty string)
        packaging_unit_qr_id: Optional QR identifier that resolves to an
            item_packaging_units.qr_identifier for multi-UOM support.
    """

    id: str
    sku: str
    qty: int
    batch: str
    packaging_unit_qr_id: str | None = field(default=None)


def decode_qr_payload(qr_data: str) -> QRPayload:  # noqa: C901
    """Decode and validate a QR payload JSON string.

    Parses the JSON string, validates all required fields are present and valid,
    and returns a structured QRPayload object.

    Args:
        qr_data: Raw JSON string from the scanned QR code.

    Returns:
        QRPayload: Validated and structured payload data.

    Raises:
        ValidationError: If the payload is not valid JSON, is missing required
            fields, or contains invalid values.
    """
    # Parse JSON
    try:
        data = json.loads(qr_data)
    except (json.JSONDecodeError, TypeError) as e:
        raise ValidationError(
            message="Invalid QR payload: not valid JSON",
            details=[{"field": "qr_data", "reason": f"JSON parse error: {str(e)}"}],
        )

    if not isinstance(data, dict):
        raise ValidationError(
            message="Invalid QR payload: expected a JSON object",
            details=[{"field": "qr_data", "reason": "Payload must be a JSON object"}],
        )

    # Validate required fields are present
    errors = []

    # Validate 'id' field
    qr_id = data.get("id")
    if qr_id is None:
        errors.append({"field": "id", "reason": "Missing required field 'id'"})
    elif not isinstance(qr_id, str) or not qr_id.strip():
        errors.append(
            {"field": "id", "reason": "Field 'id' must be a non-empty string"}
        )

    # Validate 'sku' field
    sku = data.get("sku")
    if sku is None:
        errors.append({"field": "sku", "reason": "Missing required field 'sku'"})
    elif not isinstance(sku, str) or not sku.strip():
        errors.append(
            {"field": "sku", "reason": "Field 'sku' must be a non-empty string"}
        )

    # Validate 'qty' field
    qty = data.get("qty")
    if qty is None:
        errors.append({"field": "qty", "reason": "Missing required field 'qty'"})
    elif not isinstance(qty, int) or isinstance(qty, bool):
        errors.append({"field": "qty", "reason": "Field 'qty' must be an integer"})
    elif qty <= 0:
        errors.append(
            {"field": "qty", "reason": "Field 'qty' must be a positive integer"}
        )

    # Validate 'batch' field
    batch = data.get("batch")
    if batch is None:
        errors.append({"field": "batch", "reason": "Missing required field 'batch'"})
    elif not isinstance(batch, str) or not batch.strip():
        errors.append(
            {"field": "batch", "reason": "Field 'batch' must be a non-empty string"}
        )

    if errors:
        raise ValidationError(
            message="Invalid QR payload: validation failed",
            details=errors,
        )

    return QRPayload(
        id=qr_id.strip(),
        sku=sku.strip(),
        qty=qty,
        batch=batch.strip(),
        packaging_unit_qr_id=data.get("packaging_unit_qr_id") or None,
    )
