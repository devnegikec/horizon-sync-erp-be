"""Accept a short delivery by closing a partially delivered ASN.

A warehouse manager can now formally close a ``partially_delivered`` ASN whose
outstanding quantity will never arrive. The closure records *why* (reason code
+ note), *who* and *when*, and the residual short is snapshotted onto the ASN so
the shortage stays visible after any later receipt edit.

The ASN keeps the existing ``closed`` status rather than gaining a new enum
value: ``short_closed`` distinguishes "closed with a shortfall" from "closed
fully received", so existing status filters and counts keep working.

Also merges the two divergent heads carried on this branch
(``116_add_qseal_suspicion_fields`` and ``128_audit_log_record_id_nullable``)
into a single head.

Revision ID: 129_asn_short_delivery_close
Revises: 116_add_qseal_suspicion_fields, 128_audit_log_record_id_nullable
Create Date: 2026-09-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_table

revision: str = "129_asn_short_delivery_close"
down_revision: str | Sequence[str] | None = (
    "116_add_qseal_suspicion_fields",
    "128_audit_log_record_id_nullable",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE = "asn_orders"

#: (column name, type) added to ``asn_orders`` for the short-delivery closure.
#: ``short_closed`` is backfilled to ``false`` so existing rows stay valid.
NEW_COLUMNS: tuple[tuple[str, sa.types.TypeEngine], ...] = (
    (
        "short_closed",
        sa.Boolean(),
    ),
    ("short_closed_qty", sa.Numeric(15, 3)),
    ("close_reason_code", sa.String(80)),
    ("close_note", sa.Text()),
    ("closed_by", postgresql.UUID(as_uuid=True)),
    ("closed_at", sa.DateTime(timezone=True)),
)


def upgrade() -> None:
    if not has_table(TABLE):
        return

    for name, type_ in NEW_COLUMNS:
        if has_column(TABLE, name):
            continue
        if name == "short_closed":
            # NOT NULL with a server default so existing rows are backfilled
            # atomically with the column addition.
            op.add_column(
                TABLE,
                sa.Column(name, type_, nullable=False, server_default=sa.text("false")),
            )
            continue
        op.add_column(TABLE, sa.Column(name, type_, nullable=True))


def downgrade() -> None:
    if not has_table(TABLE):
        return

    for name, _ in reversed(NEW_COLUMNS):
        if has_column(TABLE, name):
            op.drop_column(TABLE, name)
