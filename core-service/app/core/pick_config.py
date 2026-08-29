"""Pick configuration catalog (PR-02 / T-17, NFR-008).

Single source of truth for every ``pick.*`` config key: its value type, default,
allowed values (for enums), and human-facing labels/descriptions. The
``pick_settings`` table only stores per-organization *overrides*; the defaults
defined here are always the fallback when no override exists.

Keys are addressed without the ``pick.`` prefix internally and normalized on
input so callers may send either ``require_bin_scan`` or
``pick.require_bin_scan``.
"""

from __future__ import annotations

from typing import Any

PICK_KEY_PREFIX = "pick."

# Value types
BOOL = "bool"
INT = "int"
NUMERIC = "numeric"
ENUM = "enum"
LIST = "list"

# Standard reason-code master (T-02 uses this list; kept minimal here).
DEFAULT_REASON_CODES = [
    "bin_empty",
    "insufficient_quantity",
    "wrong_item",
    "damaged",
    "expired",
    "serial_missing",
    "serial_consumed",
    "other",
]

#: Every pick.* config key, its type, default, allowed enum values and labels.
#: This is the contract used for validation, fallback and the settings editor.
PICK_CONFIG_CATALOG: dict[str, dict[str, Any]] = {
    "allocation_strategy": {
        "type": ENUM,
        "default": "fefo_fifo",
        "allowed": ["fefo_fifo", "fifo", "fixed_bin", "zone"],
        "label": "Allocation strategy",
        "description": "Order in which bin stock is suggested for picking.",
    },
    "require_bin_scan": {
        "type": BOOL,
        "default": True,
        "label": "Require bin scan",
        "description": "Picker must scan the source bin before picking (WF-012 hard stop).",
    },
    "require_sku_scan": {
        "type": BOOL,
        "default": True,
        "label": "Require SKU scan",
        "description": "Picker must scan the SKU/item before picking (WF-013).",
    },
    "require_serial": {
        "type": ENUM,
        "default": "per_item",
        "allowed": ["per_item", "always", "never"],
        "label": "Serial capture",
        "description": "per_item = follow item has_serial_no; always = force; never = disable.",
    },
    "over_pick_tolerance": {
        "type": NUMERIC,
        "default": 0,
        "label": "Over-pick tolerance",
        "description": "Allowed quantity over the requested line before an exception (EX-021).",
    },
    "allow_short_pick": {
        "type": BOOL,
        "default": True,
        "label": "Allow short pick",
        "description": "Allow completing a line with less than requested quantity (EX-002).",
    },
    "short_pick_approval_threshold": {
        "type": NUMERIC,
        "default": 0,
        "label": "Short-pick approval threshold",
        "description": "Short-pick variance above this requires supervisor approval.",
    },
    "require_stage_scan": {
        "type": BOOL,
        "default": False,
        "label": "Require staging scan",
        "description": "Picker must scan the staging lane before completing (WF-020).",
    },
    "enable_handling_unit": {
        "type": BOOL,
        "default": False,
        "label": "Enable handling units",
        "description": "Allow associating trolley/carton/pallet during pick (WF-018).",
    },
    "aging_threshold_minutes": {
        "type": INT,
        "default": 120,
        "label": "Aging threshold (minutes)",
        "description": "Age at which an open task is flagged as aging (ALT-011).",
    },
    "login_lockout_attempts": {
        "type": INT,
        "default": 5,
        "label": "Login lockout attempts",
        "description": "Failed task-login attempts before lockout (WF-009).",
    },
    "session_timeout_minutes": {
        "type": INT,
        "default": 30,
        "label": "Session timeout (minutes)",
        "description": "Idle session timeout for handheld execution (WF-009).",
    },
    "reason_codes": {
        "type": LIST,
        "default": DEFAULT_REASON_CODES,
        "label": "Reason codes",
        "description": "Master list of pick exception reason codes (T-02).",
    },
    "priority_fields": {
        "type": LIST,
        "default": [],
        "label": "Priority fields",
        "description": "Fields that drive task prioritization (cutoff/wave/route, WF-007).",
    },
    "backorder_rule": {
        "type": ENUM,
        "default": "partial",
        "allowed": ["partial", "full", "cancel"],
        "label": "Backorder rule",
        "description": "Shortage rule: partial = ship what is available; full = hold; cancel = cancel line.",
    },
    "inventory_statuses_pickable": {
        "type": LIST,
        "default": ["available"],
        "label": "Pickable inventory statuses",
        "description": "Bin-stock statuses eligible for FEFO/FIFO allocation (WF-003).",
    },
}


def full_key(key: str) -> str:
    """Return the fully-qualified ``pick.`` key."""
    return key if key.startswith(PICK_KEY_PREFIX) else f"{PICK_KEY_PREFIX}{key}"


def normalize_key(key: str) -> str:
    """Strip the ``pick.`` prefix if present and validate the key exists."""
    key = key.strip()
    if key.startswith(PICK_KEY_PREFIX):
        key = key[len(PICK_KEY_PREFIX):]
    return key


def is_valid_key(key: str) -> bool:
    """Return True if ``key`` (with or without prefix) is a known config key."""
    try:
        return normalize_key(key) in PICK_CONFIG_CATALOG
    except Exception:
        return False


def default_value(key: str) -> Any:
    """Return the default value for a (normalized) config key."""
    return PICK_CONFIG_CATALOG[normalize_key(key)]["default"]


def validate_value(key: str, value: Any) -> Any:
    """Validate and lightly coerce ``value`` for ``key``.

    Returns the validated value. Raises ``ValueError`` for unknown keys,
    wrong types, or (for enums) values outside the allowed set.
    """
    key = normalize_key(key)
    if key not in PICK_CONFIG_CATALOG:
        raise ValueError(f"Unknown pick config key: {key!r}")

    spec = PICK_CONFIG_CATALOG[key]
    value_type = spec["type"]

    if value_type == BOOL:
        _validate_bool(key, value)
    elif value_type == INT:
        _validate_int(key, value)
    elif value_type == NUMERIC:
        _validate_numeric(key, value)
    elif value_type == ENUM:
        _validate_enum(key, value, spec.get("allowed", []))
    elif value_type == LIST:
        _validate_list(key, value)
    else:
        raise ValueError(f"Unsupported type {value_type!r} for pick.{key}")

    return value


def _validate_bool(key: str, value: Any) -> None:
    if not isinstance(value, bool):
        raise ValueError(f"pick.{key} must be a boolean")


def _validate_int(key: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"pick.{key} must be an integer")


def _validate_numeric(key: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"pick.{key} must be a number")


def _validate_enum(key: str, value: Any, allowed: list[str]) -> None:
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"pick.{key} must be one of {allowed!r}")


def _validate_list(key: str, value: Any) -> None:
    if not isinstance(value, list) or not all(
        isinstance(item, str) for item in value
    ):
        raise ValueError(f"pick.{key} must be a list of strings")


def catalog_entry(key: str) -> dict[str, Any]:
    """Return a UI-facing catalog entry for ``key``."""
    key = normalize_key(key)
    spec = PICK_CONFIG_CATALOG[key]
    return {
        "key": key,
        "type": spec["type"],
        "default": spec["default"],
        "allowed": spec.get("allowed"),
        "label": spec["label"],
        "description": spec["description"],
    }


def catalog_entries() -> list[dict[str, Any]]:
    """Return the full catalog as an ordered list for the settings editor."""
    return [catalog_entry(key) for key in PICK_CONFIG_CATALOG]
