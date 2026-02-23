"""Utility functions and helpers"""

from .naming_series import (
    extract_number_from_document_no,
    get_document_type_from_prefix,
    should_update_naming_series,
)

__all__ = [
    "extract_number_from_document_no",
    "get_document_type_from_prefix",
    "should_update_naming_series",
]
