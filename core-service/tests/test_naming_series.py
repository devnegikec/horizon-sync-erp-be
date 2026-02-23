"""Tests for naming series utilities"""


from app.utils.naming_series import (
    extract_number_from_document_no,
    get_document_type_from_prefix,
    should_update_naming_series,
)


class TestExtractNumberFromDocumentNo:
    """Tests for extract_number_from_document_no function"""

    def test_simple_format(self):
        """Test simple format like QT-0035"""
        assert extract_number_from_document_no("QT-0035") == 35

    def test_with_year(self):
        """Test format with year like SO-2025-0042"""
        assert extract_number_from_document_no("SO-2025-0042") == 42

    def test_invoice_format(self):
        """Test invoice format"""
        assert extract_number_from_document_no("INV-0123") == 123

    def test_pick_list_format(self):
        """Test pick list format"""
        assert extract_number_from_document_no("PL-0001") == 1

    def test_leading_zeros(self):
        """Test that leading zeros are handled correctly"""
        assert extract_number_from_document_no("QT-0001") == 1
        assert extract_number_from_document_no("QT-0099") == 99

    def test_large_numbers(self):
        """Test large numbers"""
        assert extract_number_from_document_no("QT-9999") == 9999

    def test_empty_string(self):
        """Test empty string returns None"""
        assert extract_number_from_document_no("") is None

    def test_none_input(self):
        """Test None input returns None"""
        assert extract_number_from_document_no(None) is None

    def test_no_numbers(self):
        """Test string with no numbers returns None"""
        assert extract_number_from_document_no("QUOTE") is None

    def test_multiple_numbers_returns_last(self):
        """Test that last number is returned when multiple exist"""
        assert extract_number_from_document_no("QT-2025-0035") == 35


class TestGetDocumentTypeFromPrefix:
    """Tests for get_document_type_from_prefix function"""

    def test_quotation_prefix(self):
        """Test quotation prefix"""
        assert get_document_type_from_prefix("QT") == "quotation"

    def test_sales_order_prefix(self):
        """Test sales order prefix"""
        assert get_document_type_from_prefix("SO") == "sales_order"

    def test_invoice_prefix(self):
        """Test invoice prefix"""
        assert get_document_type_from_prefix("INV") == "invoice"

    def test_purchase_order_prefix(self):
        """Test purchase order prefix"""
        assert get_document_type_from_prefix("PO") == "purchase_order"

    def test_delivery_note_prefix(self):
        """Test delivery note prefix"""
        assert get_document_type_from_prefix("DN") == "delivery_note"

    def test_case_insensitive(self):
        """Test that prefix matching is case insensitive"""
        assert get_document_type_from_prefix("qt") == "quotation"
        assert get_document_type_from_prefix("Qt") == "quotation"
        assert get_document_type_from_prefix("QT") == "quotation"

    def test_unknown_prefix(self):
        """Test unknown prefix returns None"""
        assert get_document_type_from_prefix("XYZ") is None

    def test_empty_prefix(self):
        """Test empty prefix returns None"""
        assert get_document_type_from_prefix("") is None


class TestShouldUpdateNamingSeries:
    """Tests for should_update_naming_series function"""

    def test_valid_simple_format(self):
        """Test valid simple format"""
        assert should_update_naming_series("QT-0035") is True

    def test_valid_with_year(self):
        """Test valid format with year"""
        assert should_update_naming_series("SO-2025-0042") is True

    def test_valid_invoice(self):
        """Test valid invoice format"""
        assert should_update_naming_series("INV-0123") is True

    def test_invalid_no_number(self):
        """Test invalid format without number"""
        assert should_update_naming_series("QUOTE") is False

    def test_invalid_no_prefix(self):
        """Test invalid format without prefix"""
        assert should_update_naming_series("0035") is False

    def test_invalid_lowercase_prefix(self):
        """Test invalid format with lowercase prefix"""
        assert should_update_naming_series("qt-0035") is False

    def test_empty_string(self):
        """Test empty string"""
        assert should_update_naming_series("") is False

    def test_none_input(self):
        """Test None input"""
        assert should_update_naming_series(None) is False

    def test_invalid_multiple_separators(self):
        """Test invalid format with too many parts"""
        assert should_update_naming_series("QT-2025-01-0042") is False
