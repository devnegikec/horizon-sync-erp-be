"""WMS location codes, bin-code patterns and QR codes.

This module owns every string-identity rule for the designer:

* **Location codes.** Zone → Aisle → Bay → Level → Bin, using the WMS
  ``LayoutService`` scheme: a type prefix (``Z``/``A``/``B``/``L``/``BN``) plus a
  zero-padded ordinal, joined with ``-`` into ``full_path``. The display form
  (which dashes the last segment, ``BN-001``) is a read-time concern and is
  reproduced by :func:`format_display_path`.

* **Bin code patterns.** The document may override the bin label with a pattern
  such as ``{warehouse}/{aisle}/{side}/B{bay:03}/L{level}``. The pattern is a
  *document-level label*; the persisted identity of a bin is always its WMS
  ``full_path``.

* **QR codes.** Five characters from an alphabet without ``I``/``O``/``0``/``1``,
  matching ``LayoutService._generate_qr_code`` and
  ``FloorPlanGeneratorService._assign_bin_qr_codes``.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md section 4
"""

from __future__ import annotations

import random
import re
from typing import Any, Literal

# ===========================================
# BIN CODE PATTERNS
# ===========================================

#: Default document-level bin label, matching the reference layout documents.
DEFAULT_BIN_CODE_PATTERN = "{warehouse}/{aisle}/{side}/B{bay:03}/L{level}"

#: Placeholders a pattern may use. ``{bay:03}`` requests zero padding.
VALID_CODE_PATTERN_TOKENS: frozenset[str] = frozenset(
    {"warehouse", "aisle", "lane", "side", "bay", "level"}
)

_CODE_TOKEN_RE = re.compile(r"\{([a-z]+)(?::(\d+))?\}")


def is_valid_code_pattern(pattern: str) -> bool:
    """True when ``pattern`` has at least one placeholder and only known tokens."""
    matches = _CODE_TOKEN_RE.findall(pattern)
    if not matches:
        return False
    return all(token in VALID_CODE_PATTERN_TOKENS for token, _ in matches)


def format_bin_code(pattern: str, values: dict[str, Any]) -> str:
    """Render a bin code from a pattern and its token values.

    Unknown tokens render as an empty string; a token that is absent from
    ``values`` renders as an empty string as well, so a malformed pattern can
    never raise while compiling a large document.
    """
    if not is_valid_code_pattern(pattern):
        pattern = DEFAULT_BIN_CODE_PATTERN

    def _replace(match: re.Match[str]) -> str:
        token, padding = match.group(1), match.group(2)
        text = str(values.get(token, ""))
        if padding:
            text = text.zfill(int(padding))
        return text

    return _CODE_TOKEN_RE.sub(_replace, pattern)


# ===========================================
# WMS LOCATION CODES
# ===========================================

#: Naming schemes the materialiser can emit.
NamingScheme = Literal["wms_typed", "wms_floorplan"]

NAMING_SCHEMES: tuple[NamingScheme, ...] = ("wms_typed", "wms_floorplan")

#: ``wms_typed`` (LayoutService): every level carries its type prefix.
WMS_TYPED: NamingScheme = "wms_typed"

#: ``wms_floorplan`` (FloorPlanGeneratorService): bare aisle/bay codes, only the
#: bin segment is prefixed. Kept selectable because both schemes exist in the
#: codebase today.
WMS_FLOORPLAN: NamingScheme = "wms_floorplan"

TYPE_CODE_PREFIX: dict[str, str] = {
    "zone": "Z",
    "aisle": "A",
    "bay": "B",
    "level": "L",
    "bin": "BN",
}

SEGMENT_WIDTH = 2
BIN_SEGMENT_WIDTH = 3

#: Location types in hierarchy order, as used by ``LayoutService.VALID_PARENT_TYPES``.
LOCATION_ORDER: tuple[str, ...] = ("zone", "aisle", "bay", "level", "bin")


_TRAILING_DIGITS_RE = re.compile(r"(\d+)$")


def trailing_digits(raw_code: str | None) -> str:
    """Trailing digit sequence of a code, or empty.

    Mirrors ``LayoutService._extract_trailing_number``: ``"A03"`` → ``"03"``,
    ``"MAIN"`` → ``""``.
    """
    if not raw_code:
        return ""
    match = _TRAILING_DIGITS_RE.search(raw_code)
    return match.group(1) if match else ""


def wms_segment(
    location_type: str,
    ordinal: int,
    authored_code: str | None = None,
    scheme: NamingScheme = WMS_TYPED,
) -> str:
    """Build one WMS path segment, e.g. ``Z01``, ``A03``, ``B02``, ``L04``, ``BN001``.

    Follows ``LayoutService._build_raw_code``: the author's own code wins when it
    ends in digits (``"A03"`` → ``"A03"``), otherwise the positional ``ordinal``
    is used — a lane's code ``"A01-L"`` has no trailing digits, so it becomes
    ``"B01"``. Digits are zero-padded to the canonical width: 2 for zone, aisle,
    bay and level, 3 for bin.

    Args:
        location_type: One of zone, aisle, bay, level, bin.
        ordinal: 1-based position within the parent.
        authored_code: Optional code taken from the document.
        scheme: ``wms_typed`` prefixes every segment; ``wms_floorplan`` leaves the
            zone and aisle segments bare and keeps the ``B``/``L``/``BN`` prefixes.
    """
    width = SEGMENT_WIDTH
    if location_type == "bin":
        # LayoutService zero-pads bins to 3 ("BN001"); the floor-plan generator
        # pads them to 2 ("BN01"). Match whichever scheme was asked for.
        width = BIN_SEGMENT_WIDTH if scheme == WMS_TYPED else SEGMENT_WIDTH
    digits = trailing_digits(authored_code)
    numeric = digits.zfill(width) if digits else f"{ordinal:0{width}d}"

    if scheme == WMS_FLOORPLAN and location_type in ("zone", "aisle"):
        return numeric

    return f"{TYPE_CODE_PREFIX.get(location_type, '')}{numeric}"


def join_path(parent_path: str | None, code: str) -> str:
    """Append a segment to a path, mirroring ``LayoutService._generate_location_code``."""
    if not parent_path:
        return code
    return f"{parent_path}-{code}"


def format_display_path(full_path: str | None) -> str:
    """Dash the final segment for display.

    ``Z01-A03-B02-L04-BN001`` → ``Z01-A03-B02-L04-BN-001``, matching
    ``LayoutService._format_full_path``.
    """
    if not full_path:
        return ""
    segments = full_path.split("-")
    if segments:
        segments[-1] = re.sub(r"([A-Za-z]+)(\d+)", r"\1-\2", segments[-1])
    return "-".join(segments)


# ===========================================
# QR CODES
# ===========================================

#: Readable alphabet: no I, O, 0 or 1.
QR_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
QR_LENGTH = 5


def generate_qr_codes(
    count: int,
    existing: set[str] | None = None,
    rng: random.Random | None = None,
) -> list[str]:
    """Generate ``count`` unique 5-character QR codes.

    Args:
        count: How many codes to produce.
        existing: Codes already in use (the caller batch-queries once rather
            than issuing one query per bin).
        rng: Injectable random source so tests are deterministic.

    Returns:
        A list of unique codes, none of which appears in ``existing``.

    Raises:
        RuntimeError: If the alphabet is exhausted for the requested count,
            which in practice cannot happen (60M+ combinations).
    """
    if count <= 0:
        return []

    source = rng or random.SystemRandom()
    taken = set(existing or ())
    codes: list[str] = []

    for _ in range(count):
        for _attempt in range(64):
            candidate = "".join(source.choices(QR_ALPHABET, k=QR_LENGTH))
            if candidate not in taken:
                taken.add(candidate)
                codes.append(candidate)
                break
        else:  # pragma: no cover - alphabet exhaustion is not reachable
            raise RuntimeError("Failed to generate unique QR codes")
    return codes
