"""Dispatch → inbound serial match: merge heads + Phase 0 schema.

Merges the three outstanding heads into a single line and applies the Phase 0
schema changes for the dispatch-slip serial-match work:

* ``asn_orders.serialization_mode`` — makes the verification mode
  (``serialized`` | ``quantity_only``) explicit on the ASN (T0.1).
* Unique index on ``serial_nos (organization_id, item_id, serial_no)`` (T0.5).
* Seeds ``UNEXPECTED_SERIAL``, ``MISSING_SERIAL`` and ``WRONG_ITEM`` inbound
  exception reason codes (T0.3 / T0.6).

All operations are idempotent and guarded against objects that may already
exist (see ``app/alembic_guards.py``). The ``serial_nos`` unique index is
skipped with a loud warning when pre-existing duplicate rows would make it fail
to build — duplicates must be reconciled out-of-band rather than silently
deleted (``serial_no_history`` references ``serial_nos`` with CASCADE).

Revision ID: 126_dispatch_serial_match
Revises: 116_add_qseal_suspicion_fields, 120_add_master_carton_estimation_fields, 125_bin_stock_status_unique
Create Date: 2026-09-23
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_constraint, has_table

revision: str = "126_dispatch_serial_match"
down_revision: str | Sequence[str] | None = (
    "116_add_qseal_suspicion_fields",
    "120_add_master_carton_estimation_fields",
    "125_bin_stock_status_unique",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: (code, name, category, default_destination, requires_approval)
NEW_REASONS = (
    (
        "UNEXPECTED_SERIAL",
        "Serial not expected on the transfer ASN",
        "unexpected_sku",
        "HOLD",
        True,
    ),
    (
        "MISSING_SERIAL",
        "Serial dispatched but not received",
        "short",
        None,
        True,
    ),
    (
        "WRONG_ITEM",
        "Serial belongs to a different item on the ASN",
        "unexpected_sku",
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

SERIAL_NOS_UNIQUE = "uq_serial_nos_org_item_serial_no"


def _existing_reason_codes() -> set[str]:
    return {
        row[0]
        for row in op.get_bind()
        .execute(sa.text("SELECT code FROM inbound_exception_reasons"))
        .fetchall()
    }


def upgrade() -> None:
    # ── T0.1: asn_orders.serialization_mode ────────────────────────────
    if has_table("asn_orders") and not has_column("asn_orders", "serialization_mode"):
        op.add_column(
            "asn_orders",
            sa.Column("serialization_mode", sa.String(20), nullable=True),
        )

    # ── T0.5: unique index on serial_nos ───────────────────────────────
    if has_table("serial_nos") and not has_constraint("serial_nos", SERIAL_NOS_UNIQUE):
        conn = op.get_bind()
        duplicate = conn.execute(
            sa.text(
                """
                SELECT 1
                  FROM (
                    SELECT organization_id, item_id, serial_no
                      FROM serial_nos
                     GROUP BY organization_id, item_id, serial_no
                    HAVING COUNT(*) > 1
                  ) d
                 LIMIT 1
                """
            )
        ).scalar()
        if duplicate:
            print(
                "WARNING: serial_nos has duplicate (organization_id, item_id, "
                "serial_no) rows — skipping unique index creation. Reconcile "
                "duplicates and re-run this migration."
            )
        else:
            op.create_unique_constraint(
                SERIAL_NOS_UNIQUE,
                "serial_nos",
                ["organization_id", "item_id", "serial_no"],
            )

    # ── T0.3 / T0.6: inbound exception reason codes ────────────────────
    if has_table("inbound_exception_reasons"):
        existing = _existing_reason_codes()
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


def downgrade() -> None:
    # Drop the unique index (idempotent).
    if has_table("serial_nos") and has_constraint("serial_nos", SERIAL_NOS_UNIQUE):
        op.drop_constraint(SERIAL_NOS_UNIQUE, "serial_nos", type_="unique")

    # Drop the column (idempotent).
    if has_table("asn_orders") and has_column("asn_orders", "serialization_mode"):
        op.drop_column("asn_orders", "serialization_mode")

    # Remove only the reason rows this migration seeded, matching the exact
    # seeded signature so an operator-renamed row is left untouched.
    if has_table("inbound_exception_reasons"):
        for code, name, category, destination, requires_approval in NEW_REASONS:
            op.execute(
                sa.text(
                    """
                    DELETE FROM inbound_exception_reasons
                     WHERE code = :code
                       AND name = :name
                       AND category = :category
                       AND default_destination IS NOT DISTINCT FROM :destination
                       AND requires_approval = :requires_approval
                    """
                ).bindparams(
                    code=code,
                    name=name,
                    category=category,
                    destination=destination,
                    requires_approval=requires_approval,
                )
            )
