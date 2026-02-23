"""Standalone test for naming series utilities (no dependencies)"""

import re
from typing import Optional


def extract_number_from_document_no(document_no: str) -> Optional[int]:
    """Extract the numeric part from a document number."""
    if not document_no:
        return None
    numbers = re.findall(r"\d+", document_no)
    if not numbers:
        return None
    return int(numbers[-1])


def get_document_type_from_prefix(prefix: str) -> Optional[str]:
    """Map document prefix to document type for naming series."""
    prefix_map = {
        "QT": "quotation",
        "SO": "sales_order",
        "INV": "invoice",
        "PO": "purchase_order",
        "DN": "delivery_note",
        "PR": "purchase_receipt",
        "PAY": "payment",
        "PL": "pick_list",
        "MR": "material_request",
        "RFQ": "rfq",
    }
    return prefix_map.get(prefix.upper())


def should_update_naming_series(document_no: str) -> bool:
    """Determine if the document number follows a pattern that should update naming series."""
    if not document_no:
        return False
    pattern = r"^[A-Z]+-(\d{4}-)?(\d+)$"
    return bool(re.match(pattern, document_no))


# Run tests
def test_extract_number():
    print("Testing extract_number_from_document_no...")
    assert extract_number_from_document_no("QT-0035") == 35
    assert extract_number_from_document_no("SO-2025-0042") == 42
    assert extract_number_from_document_no("INV-0123") == 123
    assert extract_number_from_document_no("PL-0001") == 1
    assert extract_number_from_document_no("") is None
    assert extract_number_from_document_no(None) is None
    print("✓ All extract_number tests passed!")


def test_get_document_type():
    print("\nTesting get_document_type_from_prefix...")
    assert get_document_type_from_prefix("QT") == "quotation"
    assert get_document_type_from_prefix("SO") == "sales_order"
    assert get_document_type_from_prefix("INV") == "invoice"
    assert get_document_type_from_prefix("qt") == "quotation"  # case insensitive
    assert get_document_type_from_prefix("XYZ") is None
    print("✓ All get_document_type tests passed!")


def test_should_update():
    print("\nTesting should_update_naming_series...")
    assert should_update_naming_series("QT-0035") is True
    assert should_update_naming_series("SO-2025-0042") is True
    assert should_update_naming_series("INV-0123") is True
    assert should_update_naming_series("QUOTE") is False
    assert should_update_naming_series("qt-0035") is False  # lowercase prefix
    assert should_update_naming_series("") is False
    print("✓ All should_update tests passed!")


if __name__ == "__main__":
    test_extract_number()
    test_get_document_type()
    test_should_update()
    print("\n✅ All tests passed successfully!")
