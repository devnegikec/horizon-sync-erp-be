"""Unit tests for QR product SKU normalisation and bulk import/export parsing.

Only the database-free logic is covered here: SKU normalisation, per-row
parsing/validation, and CSV/XLSX rendering + reading. The upsert path itself is
exercised through ``QRProductService`` against a real database.
"""

import io
from decimal import Decimal
from uuid import uuid4

import pytest

from app.services.qr_product_bulk_service import (
    PRODUCT_COLUMNS,
    QRProductBulkService,
    parse_row,
)
from app.services.qr_product_service import normalize_sku


class TestNormalizeSku:
    def test_trims_and_treats_blank_as_unset(self):
        assert normalize_sku("  ABC-1  ") == "ABC-1"
        assert normalize_sku("   ") is None
        assert normalize_sku("") is None
        assert normalize_sku(None) is None


class TestParseRow:
    def test_requires_name(self):
        with pytest.raises(ValueError, match="name is required"):
            parse_row({"sku": "ABC-1"}, 2)

    def test_omits_blank_fields_and_normalises_sku(self):
        payload = parse_row({"name": " Widget ", "sku": "  abc-1 "}, 2)
        assert payload["name"] == "Widget"
        assert payload["sku"] == "abc-1"
        # Unprovided columns are absent (so an upsert never blanks them).
        assert "generic_name" not in payload

    def test_rejects_invalid_activation_method(self):
        with pytest.raises(ValueError, match="activation_method"):
            parse_row({"name": "W", "activation_method": "sometimes"}, 2)

    def test_rejects_invalid_brand_id(self):
        with pytest.raises(ValueError, match="brand_id"):
            parse_row({"name": "W", "brand_id": "not-a-uuid"}, 2)

    def test_keeps_a_valid_brand_id(self):
        brand_id = uuid4()
        payload = parse_row({"name": "W", "brand_id": str(brand_id)}, 2)
        assert payload["brand_id"] == brand_id

    def test_rejects_fractional_integer_field(self):
        # ``int(Decimal("1.9"))`` used to truncate to 1 silently.
        with pytest.raises(ValueError, match="items_per_master_pack"):
            parse_row({"name": "W", "items_per_master_pack": "1.9"}, 2)
        with pytest.raises(ValueError, match="warranty_period_months"):
            parse_row({"name": "W", "warranty_period_months": "2.5"}, 2)

    def test_settings_accept_id_or_value(self):
        setting_id = uuid4()
        by_id = parse_row({"name": "W", "shelf_life_setting_id": str(setting_id)}, 2)
        assert by_id["shelf_life_setting_id"] == setting_id

        by_value = parse_row({"name": "W", "serial_prefix_setting_value": "PH"}, 2)
        assert by_value["serial_prefix_setting_value"] == "PH"

        # A code placed in the *_id column is tolerated as a value.
        tolerated = parse_row({"name": "W", "shelf_life_setting_id": "12"}, 2)
        assert tolerated["shelf_life_setting_value"] == "12"

    def test_packaging_defaults_when_any_field_present(self):
        payload = parse_row({"name": "W", "items_per_master_pack": "8"}, 2)
        assert payload["packaging"] == {
            "items_per_master_pack": 8,
            "unit_name": "Each",
            "conversion_factor": Decimal("1"),
        }

    def test_packaging_absent_when_no_fields(self):
        assert "packaging" not in parse_row({"name": "W"}, 2)

    def test_rejects_non_positive_conversion_factor(self):
        with pytest.raises(ValueError, match="conversion_factor"):
            parse_row({"name": "W", "conversion_factor": "0"}, 2)


class TestRenderAndRead:
    def _service(self):
        # db is unused by the pure rendering/reading helpers.
        return QRProductBulkService(db=None)

    def test_csv_export_has_header_and_rows(self):
        svc = self._service()
        content, filename = svc._render(
            [{"name": "Widget", "sku": "ABC-1"}], PRODUCT_COLUMNS, "csv", "exp"
        )
        assert filename.endswith(".csv")
        text = content.decode("utf-8-sig")
        header = text.splitlines()[0]
        assert header.split(",")[0] == "name"
        assert "Widget" in text
        assert "ABC-1" in text

    def test_xlsx_export_round_trips_headers(self):
        from openpyxl import load_workbook

        svc = self._service()
        content, filename = svc._render(
            [{"name": "Widget", "sku": "ABC-1"}], PRODUCT_COLUMNS, "xlsx", "exp"
        )
        assert filename.endswith(".xlsx")
        wb = load_workbook(io.BytesIO(content), read_only=True)
        rows = list(wb.active.iter_rows(values_only=True))
        assert rows[0] == tuple(PRODUCT_COLUMNS)
        assert rows[1][0] == "Widget"

    def test_read_rows_csv_skips_empty_rows(self):
        svc = self._service()
        csv_bytes = (
            b"name,sku\n"
            b"Widget,ABC-1\n"
            b",\n"  # blank row must be ignored
            b"Gadget,ABC-2\n"
        )
        rows = svc._read_rows(csv_bytes, "products.csv")
        assert [row["name"] for row in rows] == ["Widget", "Gadget"]

    def test_read_rows_xlsx_skips_empty_rows(self):
        svc = self._service()
        content, _ = svc._render(
            [{"name": "Widget", "sku": "ABC-1"}], PRODUCT_COLUMNS, "xlsx", "t"
        )
        rows = svc._read_rows(content, "products.xlsx")
        assert len(rows) == 1 and rows[0]["name"] == "Widget"

    def test_read_rows_rejects_unknown_extension(self):
        with pytest.raises(ValueError, match="Unsupported file type"):
            self._service()._read_rows(b"data", "products.pdf")

    def test_read_rows_rejects_empty_file(self):
        with pytest.raises(ValueError, match="empty"):
            self._service()._read_rows(b"", "products.csv")

    def test_create_kwargs_include_brand_id(self):
        brand_id = uuid4()
        kwargs = QRProductBulkService._create_kwargs(
            {"name": "W", "sku": "ABC-1", "brand_id": brand_id}
        )
        assert kwargs["brand_id"] == brand_id

    def test_export_neutralises_formula_injection(self):
        svc = self._service()
        content, _ = svc._render(
            [{"name": '=HYPERLINK("http://evil")', "sku": "+cmd|calc"}],
            PRODUCT_COLUMNS,
            "csv",
            "exp",
        )
        text = content.decode("utf-8-sig")
        assert "'=HYPERLINK" in text
        assert "'+cmd|calc" in text

    def test_export_leaves_ordinary_text_untouched(self):
        svc = self._service()
        content, _ = svc._render(
            [{"name": "Widget", "sku": "ABC-1"}], PRODUCT_COLUMNS, "csv", "exp"
        )
        assert "Widget" in content.decode("utf-8-sig")
