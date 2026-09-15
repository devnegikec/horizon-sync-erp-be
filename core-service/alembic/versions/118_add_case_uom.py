"""Add the missing 'Case' UOM, link the Case packaging type, and merge heads.

The UOM master seeded 'Carton' (CTN) and 'Box' (BOX) but never 'Case', even
though ``packaging_types`` ships a 'Case' row (seed_packaging_types.py). This
migration:

1. Inserts a count UOM 'Case' (CS) for every organization that lacks one.
2. Points the existing 'Case' packaging type at that UOM (it previously fell
   back to a generic count UOM such as PCS/EA in migration 086).

It is also a mergepoint: ``078_add_qseal_activation_requests`` (qseal-
activation-hardening) was left as an orphan head, so it is folded into the
single lineage here alongside ``117_merge_receiving_slip_status_head``.

Revision ID: 118_add_case_uom
Revises: 117_merge_receiving_slip_status_head, 078_add_qseal_activation_requests
Create Date: 2026-09-15
"""

from collections.abc import Sequence
import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "118_add_case_uom"
down_revision: str | Sequence[str] | None = (
    "117_merge_receiving_slip_status_head",
    "078_add_qseal_activation_requests",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # Organizations live in the identity service, so derive the org set from
    # rows already present in core (uoms).
    org_ids = [
        row[0]
        for row in bind.execute(
            sa.text("SELECT DISTINCT organization_id FROM uoms WHERE deleted_at IS NULL")
        ).fetchall()
    ]

    for org_id in org_ids:
        bind.execute(
            sa.text(
                """
                INSERT INTO uoms (
                    id, organization_id, name, abbreviation, uom_type,
                    precision, description, is_active, created_at, updated_at
                )
                SELECT :id, :org, 'Case', 'CS', 'count', 0, 'Case packaging',
                       true, now(), now()
                WHERE NOT EXISTS (
                    SELECT 1 FROM uoms
                    WHERE organization_id = :org
                      AND deleted_at IS NULL
                      AND (LOWER(name) = 'case'
                           OR LOWER(abbreviation) IN ('cs', 'case'))
                )
                """
            ),
            {"id": uuid.uuid4(), "org": org_id},
        )

    # Point the 'Case' packaging type at the new Case UOM.
    bind.execute(
        sa.text(
            """
            UPDATE packaging_types pt
            SET uom_id = u.id
            FROM uoms u
            WHERE pt.uom_id IS DISTINCT FROM u.id
              AND LOWER(pt.code) = 'case'
              AND u.organization_id = pt.organization_id
              AND u.deleted_at IS NULL
              AND (LOWER(u.name) = 'case'
                   OR LOWER(u.abbreviation) IN ('cs', 'case'))
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Detach only the 'Case' packaging type that this migration pointed at the
    # Case UOM (it previously fell back to a generic count UOM such as PCS/EA).
    # The FK on packaging_types.uom_id has no ON DELETE action.
    bind.execute(
        sa.text(
            """
            UPDATE packaging_types pt
            SET uom_id = NULL
            FROM uoms u
            WHERE pt.uom_id = u.id
              AND LOWER(pt.code) = 'case'
              AND (LOWER(u.name) = 'case'
                   OR LOWER(u.abbreviation) IN ('cs', 'case'))
            """
        )
    )

    # Delete only the Case UOMs this migration inserted — Case/CS count UOMs
    # that are no longer referenced by any packaging type. This avoids removing
    # pre-existing Case UOMs or any still referenced by other packaging types.
    bind.execute(
        sa.text(
            """
            DELETE FROM uoms u
            WHERE LOWER(u.name) = 'case'
              AND LOWER(u.abbreviation) = 'cs'
              AND u.uom_type = 'count'
              AND u.deleted_at IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM packaging_types pt
                  WHERE pt.uom_id = u.id
              )
            """
        )
    )
