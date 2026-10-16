"""Axis-aligned 2D geometry on the ground plane (X/Z), in metres.

The document format restricts every structure to axis-aligned rectangles with
orientation 0 or 90 degrees, which makes collision detection cheap rectangle
overlap rather than a full 3D separating-axis test. Height (Y in the document,
``position_z`` in the WMS) is tracked separately by the compiler.

All comparisons are inclusive within :data:`EPS`.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md section 3.1
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ===========================================
# UNITS AND TOLERANCES
# ===========================================

#: Geometry comparison tolerance: 0.1 mm.
EPS = 1e-4

#: Decimals retained when rounding derived coordinates.
PRECISION = 6

#: Share of a bin's raw volume considered usable (honeycombing, handling clearance).
DEFAULT_UTILIZATION = 0.85

#: Below this clear corridor width we warn - a counterbalance forklift needs ~2.5 m.
MIN_AISLE_WIDTH_M = 2.5

#: Cap repeated diagnostics so one bad parameter cannot emit 10k messages.
MAX_DIAGNOSTICS_PER_CODE = 25

#: Cubic centimetres per cubic metre (bin limits are stored in cc).
CC_PER_M3 = 1_000_000

#: Grams per kilogram (bin weight limits are stored in grams).
G_PER_KG = 1000

Vec2 = tuple[float, float]


@dataclass(frozen=True)
class AABB:
    """Axis-aligned bounding box on the ground plane."""

    min_x: float
    min_z: float
    max_x: float
    max_z: float

    @property
    def width(self) -> float:
        return self.max_x - self.min_x

    @property
    def depth(self) -> float:
        return self.max_z - self.min_z


def aabb(min_x: float, min_z: float, max_x: float, max_z: float) -> AABB:
    """Build an AABB from its minimum and maximum corners."""
    return AABB(min_x=min_x, min_z=min_z, max_x=max_x, max_z=max_z)


def overlap_area(a: AABB, b: AABB) -> float:
    """Overlap area of two rectangles; zero when they only touch."""
    dx = min(a.max_x, b.max_x) - max(a.min_x, b.min_x)
    dz = min(a.max_z, b.max_z) - max(a.min_z, b.min_z)
    if dx <= EPS or dz <= EPS:
        return 0.0
    return dx * dz


def overlaps(a: AABB, b: AABB) -> bool:
    """True when the two rectangles share real area (touching is not overlapping)."""
    return overlap_area(a, b) > 0.0


def contains(outer: AABB, inner: AABB, eps: float = EPS) -> bool:
    """True when ``inner`` lies inside ``outer`` within ``eps``."""
    return (
        inner.min_x >= outer.min_x - eps
        and inner.max_x <= outer.max_x + eps
        and inner.min_z >= outer.min_z - eps
        and inner.max_z <= outer.max_z + eps
    )


def normalize2(x: float, z: float) -> Vec2 | None:
    """Unit vector, or ``None`` when the input is degenerate (zero length)."""
    length = math.hypot(x, z)
    if length <= EPS:
        return None
    return (x / length, z / length)


def is_axis_aligned(forward: Vec2) -> bool:
    """True when the direction runs exactly along X or Z."""
    return abs(forward[0]) <= EPS or abs(forward[1]) <= EPS


def perpendicular_left(forward: Vec2) -> Vec2:
    """Left-hand perpendicular when walking along ``forward`` (Y-up frame).

    For forward = +X this yields -Z.
    """
    return (forward[1], -forward[0])


def perpendicular_right(forward: Vec2) -> Vec2:
    """Right-hand perpendicular when walking along ``forward``."""
    return (-forward[1], forward[0])


def oriented_rect_aabb(
    origin: Vec2,
    forward: Vec2,
    perp: Vec2,
    s0: float,
    s1: float,
    t0: float,
    t1: float,
) -> AABB:
    """AABB of an oriented rectangle in (along, perpendicular) lane-local space.

    Rotation of 0/90 degrees is handled naturally because both basis vectors are
    axis-aligned.
    """
    corners = [
        (
            origin[0] + forward[0] * s + perp[0] * t,
            origin[1] + forward[1] * s + perp[1] * t,
        )
        for s in (s0, s1)
        for t in (t0, t1)
    ]
    xs = [c[0] for c in corners]
    zs = [c[1] for c in corners]
    return AABB(min_x=min(xs), min_z=min(zs), max_x=max(xs), max_z=max(zs))


def nearly_zero(value: float, eps: float = EPS) -> bool:
    """True when ``value`` is zero within ``eps``."""
    return abs(value) <= eps


def nearly_equal(a: float, b: float, eps: float = EPS) -> bool:
    """True when ``a`` and ``b`` are equal within ``eps``."""
    return abs(a - b) <= eps


def round_metric(value: float, decimals: int = PRECISION) -> float:
    """Round a metric value, normalising negative zero."""
    rounded = round(value, decimals)
    return 0.0 if rounded == 0 else rounded
