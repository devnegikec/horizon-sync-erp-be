"""Add durable QSeal activation idempotency records."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_constraint, has_index, has_table


revision = "078_add_qseal_activation_requests"
down_revision = "077_add_product_item_token_lookup_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not has_table("qseal_activation_requests"):
        op.create_table(
            "qseal_activation_requests",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                server_default=sa.text("gen_random_uuid()"),
                nullable=False,
            ),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("idempotency_key", sa.String(length=100), nullable=False),
            sa.Column("request_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=20), server_default="processing", nullable=False),
            sa.Column("response_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not has_constraint(
        "qseal_activation_requests", "uq_qseal_activation_request_org_key"
    ):
        op.create_unique_constraint(
            "uq_qseal_activation_request_org_key",
            "qseal_activation_requests",
            ["organization_id", "idempotency_key"],
        )
    if not has_index("qseal_activation_requests", "ix_qseal_activation_requests_product_id"):
        op.create_index(
            "ix_qseal_activation_requests_product_id",
            "qseal_activation_requests",
            ["product_id"],
            unique=False,
        )


def downgrade() -> None:
    if has_table("qseal_activation_requests"):
        if has_index("qseal_activation_requests", "ix_qseal_activation_requests_product_id"):
            op.drop_index(
                "ix_qseal_activation_requests_product_id",
                table_name="qseal_activation_requests",
            )
        if has_constraint(
            "qseal_activation_requests", "uq_qseal_activation_request_org_key"
        ):
            op.drop_constraint(
                "uq_qseal_activation_request_org_key",
                "qseal_activation_requests",
                type_="unique",
            )
        op.drop_table("qseal_activation_requests")
