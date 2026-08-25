"""Split measurement UOMs from physical packaging (Section 5.3).

Physical packaging units (BAG, BOX, CTN, DRM, PLT, …) do not belong in the
``uoms`` master — they are reusable containers that live in
``packaging_types``. This migration deactivates any physical-pack UOMs that
are not referenced by items / item groups / conversions, leaving measurement
UOMs active.

Rows are soft-deactivated (is_active = false), never hard-deleted, so the
change is reversible and referential integrity is preserved.

Revision ID: 087_split_packaging_from_uoms
Revises: 086_uom_scalability_closers
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "087_split_packaging_from_uoms"
down_revision: str | Sequence[str] | None = "086_uom_scalability_closers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PACK_ABBREVIATIONS = (
    "BAG", "BDL", "BOX", "BTL", "CNT", "CTN",
    "DRM", "LOT", "PCK", "PK", "PLT",
)


def upgrade() -> None:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            UPDATE uoms
            SET is_active = false
            WHERE UPPER(abbreviation) IN :abbr
              AND deleted_at IS NULL
              AND id NOT IN (
                  SELECT base_uom_id FROM items WHERE base_uom_id IS NOT NULL
                  UNION
                  SELECT default_uom_id FROM item_groups WHERE default_uom_id IS NOT NULL
                  UNION
                  SELECT from_uom_id FROM uom_conversions WHERE from_uom_id IS NOT NULL
                  UNION
                  SELECT to_uom_id FROM uom_conversions WHERE to_uom_id IS NOT NULL
              )
            RETURNING id
            """
        ).bindparams(sa.bindparam("abbr", expanding=True)),
        {"abbr": list(PACK_ABBREVIATIONS)},
    )
    deactivated = len(result.fetchall())
    print(f"[087_split_packaging_from_uoms] deactivated {deactivated} physical-pack UOM(s)")


def downgrade() -> None:
    # Best-effort reactivation of physical-pack UOMs (not perfectly reversible
    # if any were already inactive before this migration ran).
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE uoms
            SET is_active = true
            WHERE UPPER(abbreviation) IN :abbr
              AND deleted_at IS NULL
            """
        ).bindparams(sa.bindparam("abbr", expanding=True)),
        {"abbr": list(PACK_ABBREVIATIONS)},
    )
