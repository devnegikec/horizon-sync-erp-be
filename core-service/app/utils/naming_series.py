"""Utilities for handling document naming series"""

import re


def extract_number_from_document_no(document_no: str) -> int | None:
    """
    Extract the numeric part from a document number.

    Examples:
        "QT-0035" -> 35
        "SO-2025-0042" -> 42
        "INV-0123" -> 123
        "PL-0001" -> 1

    Args:
        document_no: Document number string (e.g., "QT-0035")

    Returns:
        Extracted number as int, or None if no number found
    """
    if not document_no:
        return None

    # Find all sequences of digits in the string
    numbers = re.findall(r"\d+", document_no)

    if not numbers:
        return None

    # Return the last number found (usually the sequence number)
    return int(numbers[-1])


def get_document_type_from_prefix(prefix: str) -> str | None:
    """
    Map document prefix to document type for naming series.

    Args:
        prefix: Document prefix (e.g., "QT", "SO", "INV")

    Returns:
        Document type string for naming series, or None if unknown
    """
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
    """
    Determine if the document number follows a pattern that should update naming series.

    Args:
        document_no: Document number string

    Returns:
        True if naming series should be updated, False otherwise
    """
    if not document_no:
        return False

    # Check if it matches common patterns like QT-0035, SO-2025-0042, etc.
    # Pattern: PREFIX-[OPTIONAL_YEAR-]NUMBER
    pattern = r"^[A-Z]+-(\d{4}-)?(\d+)$"
    return bool(re.match(pattern, document_no))
