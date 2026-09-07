"""Link internal-transfer ASNs to outbound orders.

Internal-transfer ASNs now generate an ASN-type outbound order at the source
warehouse (instead of a direct pick list). This adds the order→ASN linkage on
the ASN side and the upstream-document linkage on the order side.

Revision ID: 109_link_asn_to_outbound_order
Revises: 108_add_outbound_orders_and_pick_status
Create Date: 2026-09-07
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "109_link_asn_to_outbound_order"
down_revision: str | Sequence[str] | None = "108_add_outbound_orders_and_pick_status"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "outbound_orders",
        sa.Column("reference_type", sa.String(50), nullable=True),
    )
    op.add_column(
        "outbound_orders",
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "outbound_orders",
        sa.Column("reference_no", sa.String(100), nullable=True),
    )

    op.add_column(
        "asn_orders",
        sa.Column("linked_order_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "ix_asn_orders_linked_order_id", "asn_orders", ["linked_order_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_asn_orders_linked_order_id", table_name="asn_orders")
    op.drop_column("asn_orders", "linked_order_id")
    op.drop_column("outbound_orders", "reference_no")
    op.drop_column("outbound_orders", "reference_id")
    op.drop_column("outbound_orders", "reference_type")
