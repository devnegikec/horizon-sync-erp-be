"""Rule registry for the layout document compiler.

Every diagnostic code the compiler can emit is declared here exactly once, with
its severity. Consequences that matter:

1. **Severity is policy, declared centrally.** Call sites report a *code*; they
   cannot declare the same rule as a warning in one place and an error in
   another.
2. **The registry is the contract.** The frontend engine mirrors this file in
   ``apps/inventory/src/app/features/layout-designer/layout-core/rules.ts`` and
   the shared fixtures assert the same codes on both sides.

Errors block ``apply``; warnings do not.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md section 3.2
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

RuleSeverity = Literal["error", "warning"]


@dataclass(frozen=True)
class RuleDefinition:
    """A single diagnostic rule."""

    code: str
    severity: RuleSeverity
    description: str


def _error(code: str, description: str) -> RuleDefinition:
    return RuleDefinition(code=code, severity="error", description=description)


def _warning(code: str, description: str) -> RuleDefinition:
    return RuleDefinition(code=code, severity="warning", description=description)


# --- Document structure ------------------------------------------------------
NO_RACK_TYPES_DEFINED = _error(
    "NO_RACK_TYPES_DEFINED", "Aisles have lanes but the document defines no rack types."
)
AISLE_CODE_DUPLICATE = _error(
    "AISLE_CODE_DUPLICATE", "Two aisles share a code, which breaks bin-code uniqueness."
)
LANE_UNKNOWN_RACK_TYPE = _error(
    "LANE_UNKNOWN_RACK_TYPE",
    "A lane references a rackTypeId that is not in the document.",
)
ZONE_CODE_DUPLICATE = _error(
    "ZONE_CODE_DUPLICATE",
    "Two zones share a code, so their location paths would collide.",
)
SCHEMA_VERSION_UNSUPPORTED = _error(
    "SCHEMA_VERSION_UNSUPPORTED",
    "The document's schemaVersion is not supported by this build.",
)
LAYOUT_DOC_INVALID = _error(
    "LAYOUT_DOC_INVALID",
    "The document does not match the layout schema (missing or malformed fields).",
)

# --- Aisle geometry ----------------------------------------------------------
AISLE_ZERO_LENGTH = _error(
    "AISLE_ZERO_LENGTH", "Aisle centerline start and end coincide."
)
AISLE_NOT_AXIS_ALIGNED = _error(
    "AISLE_NOT_AXIS_ALIGNED",
    "Aisle runs diagonally; v1 supports only exactly X or Z aligned aisles.",
)
AISLE_ORIENTATION_MISMATCH = _error(
    "AISLE_ORIENTATION_MISMATCH",
    "Declared orientation contradicts the centerline direction.",
)
AISLE_OUT_OF_FOOTPRINT = _error(
    "AISLE_OUT_OF_FOOTPRINT",
    "The clear corridor extends beyond the warehouse footprint.",
)
AISLE_OBSTACLE_OVERLAP = _error(
    "AISLE_OBSTACLE_OVERLAP",
    "The clear corridor passes through a column, wall or other obstacle.",
)
AISLE_TOO_NARROW = _warning(
    "AISLE_TOO_NARROW",
    "Corridor is narrower than a counterbalance forklift realistically needs.",
)
AISLE_WITHOUT_LANES = _warning(
    "AISLE_WITHOUT_LANES", "Aisle has no rack rows, so it stores nothing."
)

# --- Lane geometry -----------------------------------------------------------
LANE_RUN_EXCEEDS_AISLE = _error(
    "LANE_RUN_EXCEEDS_AISLE", "A lane run starts or ends beyond the aisle centerline."
)
LANE_OVERLAP = _error(
    "LANE_OVERLAP",
    "Two lanes occupy the same floor space, which usually means aisles are too close.",
)
LANE_ZERO_BAYS = _warning(
    "LANE_ZERO_BAYS", "A lane is shorter than one bay, so it yields no bins."
)
LANE_HAS_NO_RACK_SEGMENT = _warning(
    "LANE_HAS_NO_RACK_SEGMENT",
    "Every segment of a lane is a GAP, so it yields no bins.",
)
LEVEL_DEPTH_EXCEEDS_RACK = _warning(
    "LEVEL_DEPTH_EXCEEDS_RACK",
    "A level is configured deeper than the structural rack frame.",
)
LEVEL_STACK_EXCEEDS_HEIGHT = _error(
    "LEVEL_STACK_EXCEEDS_HEIGHT",
    "The level stack (beams plus clear heights) is taller than the building.",
)

# --- Bins --------------------------------------------------------------------
BIN_OUT_OF_FOOTPRINT = _error(
    "BIN_OUT_OF_FOOTPRINT", "A bay extends beyond the warehouse footprint."
)
BAY_OBSTACLE_OVERLAP = _error(
    "BAY_OBSTACLE_OVERLAP", "A bay collides with a column, wall or other obstacle."
)
BIN_CODE_DUPLICATE = _error(
    "BIN_CODE_DUPLICATE",
    "Two bins resolve to the same code; the bin code pattern is not unique enough.",
)
LOCATION_PATH_ALREADY_EXISTS = _error(
    "LOCATION_PATH_ALREADY_EXISTS",
    "A generated location path already exists in this warehouse with a different type.",
)

# --- Meta --------------------------------------------------------------------
DIAGNOSTICS_TRUNCATED = _warning(
    "DIAGNOSTICS_TRUNCATED",
    "Further instances of a repeated issue were suppressed to avoid flooding.",
)


RULES: dict[str, RuleDefinition] = {
    rule.code: rule
    for rule in (
        NO_RACK_TYPES_DEFINED,
        AISLE_CODE_DUPLICATE,
        LANE_UNKNOWN_RACK_TYPE,
        ZONE_CODE_DUPLICATE,
        SCHEMA_VERSION_UNSUPPORTED,
        LAYOUT_DOC_INVALID,
        AISLE_ZERO_LENGTH,
        AISLE_NOT_AXIS_ALIGNED,
        AISLE_ORIENTATION_MISMATCH,
        AISLE_OUT_OF_FOOTPRINT,
        AISLE_OBSTACLE_OVERLAP,
        AISLE_TOO_NARROW,
        AISLE_WITHOUT_LANES,
        LANE_RUN_EXCEEDS_AISLE,
        LANE_OVERLAP,
        LANE_ZERO_BAYS,
        LANE_HAS_NO_RACK_SEGMENT,
        LEVEL_DEPTH_EXCEEDS_RACK,
        LEVEL_STACK_EXCEEDS_HEIGHT,
        BIN_OUT_OF_FOOTPRINT,
        BAY_OBSTACLE_OVERLAP,
        BIN_CODE_DUPLICATE,
        LOCATION_PATH_ALREADY_EXISTS,
        DIAGNOSTICS_TRUNCATED,
    )
}

BLOCKING_RULE_CODES: frozenset[str] = frozenset(
    code for code, rule in RULES.items() if rule.severity == "error"
)


class UnknownRuleError(ValueError):
    """Raised when a call site reports a code that is not in the registry."""


def get_rule(code: str) -> RuleDefinition:
    """Return the definition for ``code``.

    Raises:
        UnknownRuleError: If the code is not registered. A typo must be a loud
            failure rather than a silently dead rule.
    """
    try:
        return RULES[code]
    except KeyError as exc:  # pragma: no cover - developer error
        raise UnknownRuleError(f"Unknown layout rule code: {code!r}") from exc


def rule_registry_payload() -> list[dict[str, str]]:
    """The registry as JSON-serialisable rows, ordered by code."""
    return [
        {"code": rule.code, "severity": rule.severity, "description": rule.description}
        for rule in sorted(RULES.values(), key=lambda r: r.code)
    ]
