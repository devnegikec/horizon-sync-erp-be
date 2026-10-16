"""Reference layout documents served to the designer as import templates.

These are part of the contract, not decoration: ``tests/test_layout_design_examples.py``
compiles every document here and requires **zero** diagnostics, so an example can
never teach a shape the compiler rejects.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md section 6 (``GET /layout-design/example``)
"""

from __future__ import annotations

from typing import Any

LEVEL_5_1_4 = [
    {"clearHeightM": 1.4, "binDepthM": 1.0, "beamHeightM": 0.08, "maxWeightKg": 800}
    for _ in range(5)
]


def _aisle(code: str, center_z: float) -> dict[str, Any]:
    """Build one aisle with two racks split by a 2-bay cross-aisle."""
    segments = [
        {"kind": "RACK", "startM": 0, "endM": 10.8, "label": "front"},
        {"kind": "GAP", "startM": 10.8, "endM": 16.2, "label": "cross-aisle"},
        {"kind": "RACK", "startM": 16.2, "endM": 27.0, "label": "back"},
    ]
    return {
        "code": code,
        "orientation": "X",
        "centerline": {"x1": 4, "z1": center_z, "x2": 31, "z2": center_z},
        "widthM": 3.4,
        "travelDirection": "BOTH",
        "lanes": [
            {
                "code": f"{code}-L",
                "side": "LEFT",
                "rackTypeId": "rt-std",
                "startOffsetM": 0,
                "lengthM": 27,
                "levels": LEVEL_5_1_4,
                "segments": segments,
                "metadata": {"skuClass": "A"},
            },
            {
                "code": f"{code}-R",
                "side": "RIGHT",
                "rackTypeId": "rt-std",
                "startOffsetM": 0,
                "lengthM": 27,
                "levels": LEVEL_5_1_4,
                "segments": segments,
            },
        ],
    }


#: Three aisles along X, both sides racked, one 2-bay cross-aisle through every
#: lane, three column lines, a pillar, a wall and an office.
#: 3 aisles x 2 lanes x (10 bays - 2 in the cross-aisle) x 5 levels = 240 bins.
CROSS_AISLE_TWO_WAY: dict[str, Any] = {
    "schemaVersion": 1,
    "layout": {"namingScheme": "wms_typed", "defaultZoneCode": "01"},
    "warehouse": {
        "code": "WH-A",
        "name": "Two-way warehouse with a central cross-aisle",
        "lengthM": 40,
        "widthM": 32,
        "heightM": 9,
        "origin": {"x": 0, "z": 0},
        "metadata": {"site": "reference example"},
    },
    "rackTypes": [
        {
            "id": "rt-std",
            "code": "STD",
            "name": "Standard pallet rack",
            "bayWidthM": 2.7,
            "depthM": 1.1,
            "uprightWidthM": 0.12,
            "uprightDepthM": 0.12,
            "metadata": {"beamProfile": "100x50"},
        }
    ],
    "obstacles": [
        {
            "id": "col-1",
            "kind": "COLUMN",
            "x": 6,
            "z": 11.2,
            "widthM": 0.6,
            "depthM": 0.6,
            "heightM": 6,
        },
        {
            "id": "col-2",
            "kind": "COLUMN",
            "x": 16,
            "z": 11.2,
            "widthM": 0.6,
            "depthM": 0.6,
            "heightM": 6,
        },
        {
            "id": "col-3",
            "kind": "COLUMN",
            "x": 26,
            "z": 11.2,
            "widthM": 0.6,
            "depthM": 0.6,
            "heightM": 6,
        },
        {
            "id": "pil-1",
            "kind": "PILLAR",
            "x": 10,
            "z": 28.5,
            "widthM": 0.8,
            "depthM": 0.8,
            "heightM": 9,
            "metadata": {"structure": "roof support"},
        },
        {
            "id": "office-1",
            "kind": "OFFICE",
            "x": 33,
            "z": 24,
            "widthM": 6,
            "depthM": 5,
            "heightM": 3.5,
            "metadata": {"purpose": "goods-in desk"},
        },
    ],
    "aisles": [
        _aisle("A01", 7.5),
        _aisle("A02", 15.5),
        _aisle("A03", 23.5),
    ],
}


#: The smallest valid document: one aisle, one lane, one bay, one level.
MINIMAL: dict[str, Any] = {
    "schemaVersion": 1,
    "warehouse": {"code": "WH-MIN", "lengthM": 8, "widthM": 8, "heightM": 6},
    "rackTypes": [
        {"id": "rt-std", "code": "STD", "bayWidthM": 2.7, "depthM": 1.1},
    ],
    "aisles": [
        {
            "code": "A01",
            "orientation": "X",
            "centerline": {"x1": 1, "z1": 4, "x2": 7, "z2": 4},
            "widthM": 3.0,
            "lanes": [
                {
                    "code": "A01-L",
                    "side": "LEFT",
                    "rackTypeId": "rt-std",
                    "lengthM": 5.4,
                    "levels": [
                        {"clearHeightM": 1.4, "binDepthM": 1.0, "beamHeightM": 0.08},
                        {"clearHeightM": 1.4, "binDepthM": 1.0, "beamHeightM": 0.08},
                    ],
                }
            ],
        }
    ],
}

#: Import templates offered by the designer, keyed by a stable identifier.
EXAMPLE_DOCUMENTS: dict[str, dict[str, Any]] = {
    "cross-aisle-two-way": CROSS_AISLE_TWO_WAY,
    "minimal": MINIMAL,
}


def get_example(name: str) -> dict[str, Any] | None:
    """Return an example document by name, or ``None``."""
    return EXAMPLE_DOCUMENTS.get(name)
