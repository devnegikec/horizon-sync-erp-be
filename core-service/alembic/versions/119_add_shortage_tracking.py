"""Short-receipt tracking: line reason codes, shortage quantities, closure.

Closes the short-receipt gaps identified in
``INBOUND_EXCEPTION_AND_RETURNS_GAP_ANALYSIS.md`` (§3.1):

1. ``receiving_slip_items`` gains the operator's ``reason_code`` and the
   ``short_qty`` (units short against the ASN expectation) so a shortage is
   reason-coded and quantifiable at the dock instead of being dropped.
2. ``inbound_short_balances`` gains the dock ``reason_code``/``note`` plus the
   closure columns (``close_reason_code``, ``close_note``, ``closed_by``,
   ``closed_at``) so a residual short can be formally closed/written off with an
   approver and an audit trail. ``status`` additionally accepts ``written_off``.
3. New append-only ``inbound_short_balance_events`` table gives arrival-level
   traceability: every time a balance is created, changes or is closed by a
   receipt, an immutable event row records expected/received/short and the
   receipt note that caused it.
4. Seeds the shortage-closure reason codes used by the closure endpoint.

Revision ID: 119_add_shortage_tracking
Revises: 118_add_case_uom
Create Date: 2026-09-18
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_index, has_table

revision: str = "119_add_shortage_tracking"
down_revision: str | Sequence[str] | None = "118_add_case_uom"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ensure_column(table: str, column: sa.Column) -> None:
    if not has_column(table, column.name):
        op.add_column(table, column)


def _ensure_index(name: str, table: str, columns: list[str]) -> None:
    if not has_index(table, name):
        op.create_index(name, table, columns)


def upgrade() -> None:
    # ── 1. Dock-level shortage capture on receipt lines ─────────────────
    _ensure_column(
        "receiving_slip_items",
        sa.Column(
            "reason_code",
            sa.String(80),
            nullable=True,
            comment="Exception/shortage reason code selected by the operator",
        ),
    )
    _ensure_column(
        "receiving_slip_items",
        sa.Column(
            "short_qty",
            sa.Integer(),
            nullable=True,
            comment="Units short against the ASN expectation for this line",
        ),
    )
    _ensure_index(
        "ix_receiving_slip_items_reason_code",
        "receiving_slip_items",
        ["reason_code"],
    )

    # ── 2. Shortage balance closure columns ─────────────────────────────
    _ensure_column(
        "inbound_short_balances",
        sa.Column("reason_code", sa.String(80), nullable=True),
    )
    _ensure_column(
        "inbound_short_balances",
        sa.Column("note", sa.Text(), nullable=True),
    )
    _ensure_column(
        "inbound_short_balances",
        sa.Column("close_reason_code", sa.String(80), nullable=True),
    )
    _ensure_column(
        "inbound_short_balances",
        sa.Column("close_note", sa.Text(), nullable=True),
    )
    _ensure_column(
        "inbound_short_balances",
        sa.Column("closed_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    _ensure_column(
        "inbound_short_balances",
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── 3. Append-only arrival history ──────────────────────────────────
    if not has_table("inbound_short_balance_events"):
        op.create_table(
            "inbound_short_balance_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column(
                "organization_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "balance_id",
                postgresql.UUID(as_uuid=True),
                # Append-only history: a purged balance (itself cascaded from
                # ``asn_orders``) nulls the link instead of erasing evidence.
                sa.ForeignKey("inbound_short_balances.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column(
                "receiving_slip_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("receiving_slips.id", ondelete="SET NULL"),
                nullable=True,
                index=True,
            ),
            sa.Column("event_type", sa.String(30), nullable=False, index=True),
            sa.Column("from_status", sa.String(20), nullable=True),
            sa.Column("to_status", sa.String(20), nullable=False),
            sa.Column("expected_qty", sa.Numeric(15, 3), nullable=False),
            sa.Column("received_qty", sa.Numeric(15, 3), nullable=False),
            sa.Column("short_qty", sa.Numeric(15, 3), nullable=False),
            sa.Column("reason_code", sa.String(80), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "actor_id",
                postgresql.UUID(as_uuid=True),
                nullable=True,
                index=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )

    # ── 4. Shortage closure reason codes ────────────────────────────────
    reason_rows = [
        (
            "SHORTAGE_WRITE_OFF",
            "Shortage written off (approved)",
            "short",
        ),
        (
            "SHORTAGE_SUPPLIER_CLAIM",
            "Shortage claimed from supplier",
            "short",
        ),
        (
            "SHORTAGE_FOUND_LATER",
            "Shortage received later against the same ASN",
            "short",
        ),
    ]
    reasons_table = sa.table(
        "inbound_exception_reasons",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("category", sa.String),
        sa.column("default_destination", sa.String),
        sa.column("requires_approval", sa.Boolean),
    )
    existing_codes = {
        row[0]
        for row in op.get_bind()
        .execute(sa.text("SELECT code FROM inbound_exception_reasons"))
        .fetchall()
    }
    op.bulk_insert(
        reasons_table,
        [
            {
                "id": uuid.uuid4(),
                "code": code,
                "name": name,
                "category": category,
                "default_destination": None,
                "requires_approval": True,
            }
            for code, name, category in reason_rows
            if code not in existing_codes
        ],
    )


def downgrade() -> None:
    if has_table("inbound_short_balance_events"):
        op.drop_table("inbound_short_balance_events")

    for column in (
        "close_reason_code",
        "close_note",
        "closed_by",
        "closed_at",
        "reason_code",
        "note",
    ):
        if has_column("inbound_short_balances", column):
            op.drop_column("inbound_short_balances", column)

    if has_index("receiving_slip_items", "ix_receiving_slip_items_reason_code"):
        op.drop_index("ix_receiving_slip_items_reason_code", "receiving_slip_items")
    for column in ("reason_code", "short_qty"):
        if has_column("receiving_slip_items", column):
            op.drop_column("receiving_slip_items", column)
