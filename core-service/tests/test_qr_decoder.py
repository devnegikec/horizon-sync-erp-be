"""Unit tests for QR payload decoding and validation.

Tests the decode_qr_payload function which parses JSON QR payloads
and validates required fields (id, sku, qty, batch).

Requirements: 4.1, 4.2, 4.3
"""

import json

import pytest

from app.core.exceptions import ValidationError
from app.services import qr_decoder
from app.services.qr_decoder import QRPayload, decode_qr_payload


class TestDecodeQRPayloadValid:
    """Tests for valid QR payloads."""

    def test_valid_payload_returns_qr_payload(self):
        """A well-formed JSON payload should return a QRPayload dataclass."""
        qr_data = json.dumps(
            {
                "id": "unique-qr-001",
                "sku": "ITEM-001",
                "qty": 50,
                "batch": "BATCH-2025-01",
            }
        )

        result = decode_qr_payload(qr_data)

        assert isinstance(result, QRPayload)
        assert result.id == "unique-qr-001"
        assert result.sku == "ITEM-001"
        assert result.qty == 50
        assert result.batch == "BATCH-2025-01"

    def test_valid_payload_with_extra_fields(self):
        """Extra fields in the payload should be ignored."""
        qr_data = json.dumps(
            {
                "id": "qr-002",
                "sku": "WIDGET-X",
                "qty": 1,
                "batch": "B001",
                "extra_field": "should be ignored",
                "another": 123,
            }
        )

        result = decode_qr_payload(qr_data)

        assert result.id == "qr-002"
        assert result.sku == "WIDGET-X"
        assert result.qty == 1
        assert result.batch == "B001"

    def test_valid_payload_strips_whitespace(self):
        """String fields should be stripped of leading/trailing whitespace."""
        qr_data = json.dumps(
            {
                "id": "  qr-003  ",
                "sku": "  SKU-PADDED  ",
                "qty": 10,
                "batch": "  BATCH-PADDED  ",
            }
        )

        result = decode_qr_payload(qr_data)

        assert result.id == "qr-003"
        assert result.sku == "SKU-PADDED"
        assert result.batch == "BATCH-PADDED"

    def test_qty_of_one_is_valid(self):
        """Quantity of 1 (minimum positive integer) should be accepted."""
        qr_data = json.dumps(
            {
                "id": "qr-min",
                "sku": "ITEM-MIN",
                "qty": 1,
                "batch": "B-MIN",
            }
        )

        result = decode_qr_payload(qr_data)

        assert result.qty == 1

    def test_large_qty_is_valid(self):
        """Large quantities should be accepted."""
        qr_data = json.dumps(
            {
                "id": "qr-large",
                "sku": "ITEM-LARGE",
                "qty": 999999,
                "batch": "B-LARGE",
            }
        )

        result = decode_qr_payload(qr_data)

        assert result.qty == 999999


class TestDecodeQRPayloadInvalidJSON:
    """Tests for invalid JSON input."""

    def test_empty_string_raises_validation_error(self):
        """An empty string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload("")

        assert "not valid JSON" in exc_info.value.message

    def test_non_json_string_raises_validation_error(self):
        """A non-JSON string should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload("this is not json")

        assert "not valid JSON" in exc_info.value.message

    def test_json_array_raises_validation_error(self):
        """A JSON array (not object) should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload("[1, 2, 3]")

        assert "expected a JSON object" in exc_info.value.message

    def test_json_string_raises_validation_error(self):
        """A JSON string value should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload('"just a string"')

        assert "expected a JSON object" in exc_info.value.message

    def test_none_input_raises_validation_error(self):
        """None input should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(None)

        assert "not valid JSON" in exc_info.value.message


class TestDecodeQRPayloadMissingFields:
    """Tests for missing required fields."""

    def test_missing_id_raises_validation_error(self):
        """Missing 'id' field should raise ValidationError."""
        qr_data = json.dumps({"sku": "ITEM-001", "qty": 10, "batch": "B001"})

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "id" for d in exc_info.value.details)

    def test_missing_sku_raises_validation_error(self):
        """Missing 'sku' field should raise ValidationError."""
        qr_data = json.dumps({"id": "qr-001", "qty": 10, "batch": "B001"})

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "sku" for d in exc_info.value.details)

    def test_missing_qty_raises_validation_error(self):
        """Missing 'qty' field should raise ValidationError."""
        qr_data = json.dumps({"id": "qr-001", "sku": "ITEM-001", "batch": "B001"})

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "qty" for d in exc_info.value.details)

    def test_missing_batch_raises_validation_error(self):
        """Missing 'batch' field should raise ValidationError."""
        qr_data = json.dumps({"id": "qr-001", "sku": "ITEM-001", "qty": 10})

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "batch" for d in exc_info.value.details)

    def test_empty_object_reports_all_missing_fields(self):
        """An empty JSON object should report all four missing fields."""
        qr_data = json.dumps({})

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        fields = [d["field"] for d in exc_info.value.details]
        assert "id" in fields
        assert "sku" in fields
        assert "qty" in fields
        assert "batch" in fields


class TestDecodeQRPayloadInvalidValues:
    """Tests for fields with invalid values."""

    def test_empty_sku_raises_validation_error(self):
        """An empty string SKU should raise ValidationError."""
        qr_data = json.dumps({"id": "qr-001", "sku": "", "qty": 10, "batch": "B001"})

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "sku" for d in exc_info.value.details)

    def test_whitespace_only_sku_raises_validation_error(self):
        """A whitespace-only SKU should raise ValidationError."""
        qr_data = json.dumps({"id": "qr-001", "sku": "   ", "qty": 10, "batch": "B001"})

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "sku" for d in exc_info.value.details)

    def test_empty_batch_raises_validation_error(self):
        """An empty string batch should raise ValidationError."""
        qr_data = json.dumps(
            {"id": "qr-001", "sku": "ITEM-001", "qty": 10, "batch": ""}
        )

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "batch" for d in exc_info.value.details)

    def test_whitespace_only_batch_raises_validation_error(self):
        """A whitespace-only batch should raise ValidationError."""
        qr_data = json.dumps(
            {"id": "qr-001", "sku": "ITEM-001", "qty": 10, "batch": "   "}
        )

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "batch" for d in exc_info.value.details)

    def test_zero_qty_raises_validation_error(self):
        """A quantity of zero should raise ValidationError."""
        qr_data = json.dumps(
            {"id": "qr-001", "sku": "ITEM-001", "qty": 0, "batch": "B001"}
        )

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "qty" for d in exc_info.value.details)
        assert any("positive" in d["reason"] for d in exc_info.value.details)

    def test_negative_qty_raises_validation_error(self):
        """A negative quantity should raise ValidationError."""
        qr_data = json.dumps(
            {"id": "qr-001", "sku": "ITEM-001", "qty": -5, "batch": "B001"}
        )

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "qty" for d in exc_info.value.details)
        assert any("positive" in d["reason"] for d in exc_info.value.details)

    def test_float_qty_raises_validation_error(self):
        """A float quantity should raise ValidationError (must be integer)."""
        qr_data = json.dumps(
            {"id": "qr-001", "sku": "ITEM-001", "qty": 10.5, "batch": "B001"}
        )

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "qty" for d in exc_info.value.details)
        assert any("integer" in d["reason"] for d in exc_info.value.details)

    def test_string_qty_raises_validation_error(self):
        """A string quantity should raise ValidationError."""
        qr_data = json.dumps(
            {"id": "qr-001", "sku": "ITEM-001", "qty": "ten", "batch": "B001"}
        )

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "qty" for d in exc_info.value.details)

    def test_boolean_qty_raises_validation_error(self):
        """A boolean quantity should raise ValidationError (bool is not int for this purpose)."""
        qr_data = json.dumps(
            {"id": "qr-001", "sku": "ITEM-001", "qty": True, "batch": "B001"}
        )

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "qty" for d in exc_info.value.details)

    def test_null_sku_raises_validation_error(self):
        """A null SKU should raise ValidationError (treated as missing)."""
        qr_data = json.dumps({"id": "qr-001", "sku": None, "qty": 10, "batch": "B001"})

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "sku" for d in exc_info.value.details)

    def test_numeric_sku_raises_validation_error(self):
        """A numeric SKU should raise ValidationError (must be string)."""
        qr_data = json.dumps({"id": "qr-001", "sku": 12345, "qty": 10, "batch": "B001"})

        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload(qr_data)

        assert any(d["field"] == "sku" for d in exc_info.value.details)


class TestDecodeQRPayloadURLs:
    """Tests for URL-format QR payloads (including shortened CDN URLs)."""

    def test_legacy_url_recognised(self):
        """Legacy /g/{gtin}/s/{serial} URLs should be accepted."""
        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload("https://example.com/g/9283975768/s/TTK-HZ04VO/1?c=sig")

        # Reaches serial resolution (db=None) rather than "URL format not recognised".
        assert "cannot resolve serial without database" in exc_info.value.message

    def test_gs1_url_recognised(self):
        """GS1 Digital Link /01/{gtin}/21/{serial} URLs should be accepted."""
        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload("https://example.com/01/9283975768/21/TTK-HZ04VO")

        assert "cannot resolve serial without database" in exc_info.value.message

    def test_unrecognised_url_raises(self, monkeypatch):
        """Non-shortener URLs that match no pattern should be rejected."""
        monkeypatch.setattr(qr_decoder, "_is_shortened_qr_url", lambda url: False)
        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload("https://example.com/foo/bar")

        assert "URL format not recognised" in exc_info.value.message

    def test_shortened_url_resolves_via_redirect(self, monkeypatch):
        """Shortened CDN URLs should be resolved to their serial."""
        monkeypatch.setattr(qr_decoder, "_is_shortened_qr_url", lambda url: True)
        monkeypatch.setattr(
            qr_decoder,
            "_resolve_short_url",
            lambda url: "https://v0.example.com/g/9283975768/s/TTK-HZ04VO/1788009157534?c=sig",
        )
        with pytest.raises(ValidationError) as exc_info:
            decode_qr_payload("https://bwqr.me/01/9283975768/HbSdqPALqiRtmwmx")

        # Reaches serial resolution (db=None), proving the redirect was followed.
        assert "cannot resolve serial without database" in exc_info.value.message
