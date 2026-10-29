"""Tests for QR product GTIN length-only validation."""

from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.qr_product import QRProductCreate, QRProductUpdate


def test_gtin_accepts_non_numeric_values_within_length_limit():
    product = QRProductCreate(
        name="Test Product",
        gtin="ABC-1",
        shelf_life_setting_id=uuid4(),
        serial_prefix_setting_id=uuid4(),
    )

    assert product.gtin == "ABC-1"


@pytest.mark.parametrize("schema", [QRProductCreate, QRProductUpdate])
def test_gtin_rejects_values_longer_than_20_characters(schema):
    values = {
        "gtin": "X" * 21,
    }
    if schema is QRProductCreate:
        values.update(
            {
                "name": "Test Product",
                "shelf_life_setting_id": uuid4(),
                "serial_prefix_setting_id": uuid4(),
            }
        )

    with pytest.raises(ValidationError):
        schema(**values)
