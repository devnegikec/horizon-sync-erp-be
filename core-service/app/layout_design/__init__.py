"""JSON-driven warehouse layout designer.

A layout *document* (see :mod:`app.layout_design.schema`) is compiled by
:func:`app.layout_design.compile.build_layout` into bays, bins and diagnostics,
then materialised into ``WarehouseLocation`` rows by
:mod:`app.layout_design.materialize` using the WMS naming scheme.

Nothing in this package touches the database or FastAPI: it is metres in,
diagnostics out, so it can be unit-tested without a session.

Design ref: docs/LAYOUT_JSON_DESIGNER_PLAN.md
"""

from app.layout_design.compile import CompiledLayout, build_layout

__all__ = ["CompiledLayout", "build_layout"]
