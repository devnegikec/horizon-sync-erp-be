"""Utility functions and helpers"""

from .naming_series import (
    extract_number_from_document_no,
    get_document_type_from_prefix,
    should_update_naming_series,
)
from .serial_generators import (
    build_qr_url,
    generate_r4dan,
    generate_r6dan,
    sequential_s8dn,
    sequential_s10dn,
    sign_qr_item,
)

__all__ = [
    "extract_number_from_document_no",
    "get_document_type_from_prefix",
    "should_update_naming_series",
    "generate_r6dan",
    "generate_r4dan",
    "sequential_s8dn",
    "sequential_s10dn",
    "sign_qr_item",
    "build_qr_url",
]
