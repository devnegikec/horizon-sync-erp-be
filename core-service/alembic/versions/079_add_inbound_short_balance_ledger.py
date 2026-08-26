"""Add ASN short-balance ledger linked to the latest receiving receipt.

Revision ID: 079_add_inbound_short_balance_ledger
Revises: 078_add_inbound_exception_hold_quarantine
Create Date: 2026-08-25
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "079_add_inbound_short_balance_ledger"
down_revision: str | Sequence[str] | None = "078_add_inbound_exception_hold_quarantine"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inbound_short_balances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "asn_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asn_orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asn_order_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asn_order_items.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "receiving_slip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("receiving_slips.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("sku", sa.String(100), nullable=False),
        sa.Column("expected_qty", sa.Numeric(15, 3), nullable=False),
        sa.Column("received_qty", sa.Numeric(15, 3), nullable=False),
        sa.Column("short_qty", sa.Numeric(15, 3), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "organization_id",
            "asn_order_item_id",
            name="uq_inbound_short_balance_asn_item",
        ),
    )
    for column in (
        "organization_id",
        "asn_order_id",
        "asn_order_item_id",
        "receiving_slip_id",
        "status",
    ):
        op.create_index(
            f"ix_inbound_short_balances_{column}", "inbound_short_balances", [column]
        )


def downgrade() -> None:
    op.drop_table("inbound_short_balances")
