"""Add ``topup_orders.provider_payment_id`` for verified Razorpay payments.

Stores the provider payment id (``pay_...``) separately from the provider order
id (``provider_ref`` / ``order_...``) so the webhook and the checkout callback
can both be idempotent and auditable.

Revision ID: 137_topup_provider_payment_id
Revises: 136_subscription_billing
Create Date: 2026-10-20
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_constraint, has_table

revision: str = "137_topup_provider_payment_id"
down_revision: str | Sequence[str] | None = "136_subscription_billing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID_TYPE = postgresql.UUID(as_uuid=True)


def upgrade() -> None:
    if not has_table("topup_orders"):
        return
    if not has_column("topup_orders", "provider_payment_id"):
        op.add_column(
            "topup_orders",
            sa.Column("provider_payment_id", sa.String(191), nullable=True),
        )
    if not has_constraint("topup_orders", "uq_topup_orders_provider_payment_id"):
        op.create_unique_constraint(
            "uq_topup_orders_provider_payment_id",
            "topup_orders",
            ["provider_payment_id"],
        )


def downgrade() -> None:
    if not has_table("topup_orders"):
        return
    if has_constraint("topup_orders", "uq_topup_orders_provider_payment_id"):
        op.drop_constraint(
            "uq_topup_orders_provider_payment_id",
            "topup_orders",
            type_="unique",
        )
    if has_column("topup_orders", "provider_payment_id"):
        op.drop_column("topup_orders", "provider_payment_id")
