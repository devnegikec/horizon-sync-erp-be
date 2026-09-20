"""Inbound exception reason codes for the remaining dock controls.

Seeds the reason codes the new dock controls require and routes damaged stock to
its own bin:

* ``QR_UNREADABLE`` (G-Q1 / E-08) — an operator could not scan a carton label;
  the carton is set aside in HOLD and a supervisor must resolve it.
* ``DUPLICATE_SERIAL`` (G-E3 / E-13) — the identity is already in active stock,
  so the scan is hard-stopped and recorded for investigation.
* ``DAMAGED.default_destination`` → ``DAMAGED`` (G-D2 / E-06) — damaged goods get
  their own non-pickable bin instead of collapsing into QUARANTINE.

The scan-time excess control (E-12) reuses the existing ``EXCESS`` reason code
(HOLD, approval required), so no new code is seeded for it.

Revision ID: 122_inbound_exception_reason_codes
Revises: 121_backfill_segregated_stock_status
Create Date: 2026-09-19
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table

revision: str = "122_inbound_exception_reason_codes"
down_revision: str | Sequence[str] | None = "121_backfill_segregated_stock_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (code, name, category, default_destination, requires_approval)
NEW_REASONS = (
    (
        "QR_UNREADABLE",
        "Unreadable or unscannable QR",
        "unreadable",
        "HOLD",
        True,
    ),
    (
        "DUPLICATE_SERIAL",
        "Duplicate identity already in stock",
        "duplicate_serial",
        "HOLD",
        True,
    ),
)

REASONS_TABLE = sa.table(
    "inbound_exception_reasons",
    sa.column("id", postgresql.UUID(as_uuid=True)),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("category", sa.String),
    sa.column("default_destination", sa.String),
    sa.column("requires_approval", sa.Boolean),
)

#: The ``DAMAGED`` row as seeded by migration 078. Used so :func:`downgrade`
#: recognises the row this migration re-pointed instead of one an operator has
#: since repurposed under the same code.
DAMAGED_SEED = ("DAMAGED", "Damaged goods", "damage")

_DELETE_SEEDED_REASON = sa.text(
    """
    DELETE FROM inbound_exception_reasons
     WHERE code = :code
       AND name = :name
       AND category = :category
       AND default_destination IS NOT DISTINCT FROM :destination
       AND requires_approval = :requires_approval
    """
)


def _existing_codes() -> set[str]:
    return {
        row[0]
        for row in op.get_bind()
        .execute(sa.text("SELECT code FROM inbound_exception_reasons"))
        .fetchall()
    }


def upgrade() -> None:
    if not has_table("inbound_exception_reasons"):
        return

    existing = _existing_codes()
    rows = [
        {
            "id": uuid.uuid4(),
            "code": code,
            "name": name,
            "category": category,
            "default_destination": destination,
            "requires_approval": requires_approval,
        }
        for code, name, category, destination, requires_approval in NEW_REASONS
        if code not in existing
    ]
    if rows:
        op.bulk_insert(REASONS_TABLE, rows)

    # Damaged goods get a dedicated bin; only rewrite the seeded default.
    op.execute(
        sa.text(
            """
            UPDATE inbound_exception_reasons
               SET default_destination = 'DAMAGED'
             WHERE code = 'DAMAGED'
               AND default_destination = 'QUARANTINE'
            """
        )
    )


def downgrade() -> None:
    """Undo the seed, touching only rows this migration is responsible for.

    A downgrade cannot tell a row it wrote from a row that already held the
    same value, so both statements are narrowed to the exact seeded signature.
    A ``DAMAGED`` reason an operator has renamed, or a ``QR_UNREADABLE`` /
    ``DUPLICATE_SERIAL`` row that pre-dates this migration (the upgrade skips
    codes that already exist), is left in place.
    """
    if not has_table("inbound_exception_reasons"):
        return

    code, name, category = DAMAGED_SEED
    op.execute(
        sa.text(
            """
            UPDATE inbound_exception_reasons
               SET default_destination = 'QUARANTINE'
             WHERE code = :code
               AND name = :name
               AND category = :category
               AND default_destination = 'DAMAGED'
            """
        ).bindparams(code=code, name=name, category=category)
    )

    for code, name, category, destination, requires_approval in NEW_REASONS:
        op.execute(
            _DELETE_SEEDED_REASON.bindparams(
                code=code,
                name=name,
                category=category,
                destination=destination,
                requires_approval=requires_approval,
            )
        )
