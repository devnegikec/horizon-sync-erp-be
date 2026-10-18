"""Add subscription plans, contracts and the credit ledger.

Creates the Phase 1 subscription/billing schema described in
``SUBSCRIPTION_PLAN_API_IMPLEMENTATION.md``:

* ``subscription_plans`` / ``subscription_plan_versions`` — versioned catalog.
* ``organization_subscriptions`` — per-org contract and billing schedule.
* ``credit_batches`` / ``credit_ledger`` — expiring, weighted credits.
* ``generation_operations`` — idempotent reserve/commit/release.
* ``topup_quotes`` / ``topup_orders`` — self-service top-ups.
* ``billing_provider_events`` / ``billing_outbox_events`` — webhook dedupe and
  durable event publication.

Every table is guarded with ``has_table`` so the migration is a no-op on
databases where the objects already exist.

Revision ID: 136_subscription_billing
Revises: 135_add_bin_stock_parent_qr_flag
Create Date: 2026-10-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table

revision: str = "136_subscription_billing"
down_revision: str | Sequence[str] | None = "135_add_bin_stock_parent_qr_flag"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID_TYPE = postgresql.UUID(as_uuid=True)
JSONB_TYPE = postgresql.JSONB(astext_type=sa.Text())
NUMERIC_CREDITS = sa.Numeric(20, 6)
NUMERIC_MONEY = sa.Numeric(15, 2)


def _timestamps() -> list[sa.Column]:
    return [
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
    ]


def upgrade() -> None:  # noqa: C901 - one guarded block per table
    if not has_table("subscription_plans"):
        op.create_table(
            "subscription_plans",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=True),
            sa.Column("code", sa.String(60), nullable=False),
            sa.Column("name", sa.String(200), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
            sa.Column(
                "is_active", sa.Boolean(), nullable=False, server_default=sa.true()
            ),
            *_timestamps(),
            sa.UniqueConstraint(
                "organization_id", "code", name="uq_subscription_plans_org_code"
            ),
        )
        op.create_index(
            "ix_subscription_plans_organization_id",
            "subscription_plans",
            ["organization_id"],
        )
        op.create_index(
            "uq_subscription_plans_global_code",
            "subscription_plans",
            ["code"],
            unique=True,
            postgresql_where=sa.text("organization_id IS NULL"),
        )

    if not has_table("subscription_plan_versions"):
        op.create_table(
            "subscription_plan_versions",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column(
                "plan_id",
                UUID_TYPE,
                sa.ForeignKey("subscription_plans.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("billing_cadence", sa.String(20), nullable=False),
            sa.Column("base_price", NUMERIC_MONEY, nullable=False, server_default="0"),
            sa.Column("tax_rate", sa.Numeric(7, 4), nullable=False, server_default="0"),
            sa.Column(
                "included_credits",
                NUMERIC_CREDITS,
                nullable=False,
                server_default="0",
            ),
            sa.Column("id_weight", NUMERIC_CREDITS, nullable=False, server_default="1"),
            sa.Column(
                "topup_allowed",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
            sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
            sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "status",
                sa.String(20),
                nullable=False,
                server_default="draft",
            ),
            sa.Column("approved_by", UUID_TYPE, nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", UUID_TYPE, nullable=True),
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
                "plan_id", "version", name="uq_plan_versions_plan_version"
            ),
        )
        op.create_index(
            "ix_subscription_plan_versions_plan_id",
            "subscription_plan_versions",
            ["plan_id"],
        )
        op.create_index(
            "ix_plan_versions_plan_status",
            "subscription_plan_versions",
            ["plan_id", "status"],
        )

    if not has_table("organization_subscriptions"):
        op.create_table(
            "organization_subscriptions",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column(
                "plan_id",
                UUID_TYPE,
                sa.ForeignKey("subscription_plans.id"),
                nullable=False,
            ),
            sa.Column(
                "plan_version_id",
                UUID_TYPE,
                sa.ForeignKey("subscription_plan_versions.id"),
                nullable=False,
            ),
            sa.Column(
                "status",
                sa.String(30),
                nullable=False,
                server_default="draft",
            ),
            sa.Column("billing_cadence", sa.String(20), nullable=False),
            sa.Column(
                "billing_anchor_day", sa.Integer(), nullable=False, server_default="1"
            ),
            sa.Column(
                "billing_timezone",
                sa.String(64),
                nullable=False,
                server_default="UTC",
            ),
            sa.Column(
                "activation_fee", NUMERIC_MONEY, nullable=False, server_default="0"
            ),
            sa.Column(
                "activation_fee_status",
                sa.String(20),
                nullable=False,
                server_default="not_required",
            ),
            sa.Column(
                "annual_release_policy",
                sa.String(30),
                nullable=False,
                server_default="monthly_tranches",
            ),
            sa.Column(
                "current_period_start", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_invoice_date", sa.Date(), nullable=True),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("suspended_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("suspended_reason", sa.Text(), nullable=True),
            *_timestamps(),
            sa.UniqueConstraint(
                "organization_id", name="uq_organization_subscriptions_org"
            ),
        )
        op.create_index(
            "ix_organization_subscriptions_organization_id",
            "organization_subscriptions",
            ["organization_id"],
        )
        op.create_index(
            "ix_organization_subscriptions_plan_id",
            "organization_subscriptions",
            ["plan_id"],
        )
        op.create_index(
            "ix_org_subscriptions_status_next_invoice",
            "organization_subscriptions",
            ["status", "next_invoice_date"],
        )

    if not has_table("credit_batches"):
        op.create_table(
            "credit_batches",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column("source_type", sa.String(30), nullable=False),
            sa.Column("source_id", UUID_TYPE, nullable=True),
            sa.Column("granted_qty", NUMERIC_CREDITS, nullable=False),
            sa.Column(
                "consumed_qty", NUMERIC_CREDITS, nullable=False, server_default="0"
            ),
            sa.Column(
                "expired_qty", NUMERIC_CREDITS, nullable=False, server_default="0"
            ),
            sa.Column(
                "reversed_qty", NUMERIC_CREDITS, nullable=False, server_default="0"
            ),
            sa.Column(
                "reserved_qty", NUMERIC_CREDITS, nullable=False, server_default="0"
            ),
            sa.Column(
                "issued_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(20), nullable=False, server_default="active"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
            sa.UniqueConstraint(
                "organization_id",
                "source_type",
                "source_id",
                name="uq_credit_batches_org_source",
            ),
        )
        op.create_index(
            "ix_credit_batches_organization_id", "credit_batches", ["organization_id"]
        )
        op.create_index(
            "ix_credit_batches_expires_at", "credit_batches", ["expires_at"]
        )
        op.create_index("ix_credit_batches_status", "credit_batches", ["status"])
        op.create_index(
            "ix_credit_batches_org_status_expiry",
            "credit_batches",
            ["organization_id", "status", "expires_at"],
        )

    if not has_table("generation_operations"):
        op.create_table(
            "generation_operations",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column("operation_key", sa.String(120), nullable=False),
            sa.Column("id_count", sa.Integer(), nullable=False),
            sa.Column("id_weight", NUMERIC_CREDITS, nullable=False),
            sa.Column("debit_qty", NUMERIC_CREDITS, nullable=False),
            sa.Column(
                "status", sa.String(20), nullable=False, server_default="reserved"
            ),
            sa.Column("reserved_until", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "generated_count", sa.Integer(), nullable=False, server_default="0"
            ),
            sa.Column("allocations", JSONB_TYPE, nullable=True),
            sa.Column("created_by", UUID_TYPE, nullable=True),
            *_timestamps(),
            sa.UniqueConstraint(
                "organization_id",
                "operation_key",
                name="uq_generation_operations_org_key",
            ),
        )
        op.create_index(
            "ix_generation_operations_organization_id",
            "generation_operations",
            ["organization_id"],
        )
        op.create_index(
            "ix_generation_operations_status",
            "generation_operations",
            ["status"],
        )
        op.create_index(
            "ix_generation_operations_status_reserved_until",
            "generation_operations",
            ["status", "reserved_until"],
        )

    if not has_table("credit_ledger"):
        op.create_table(
            "credit_ledger",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column(
                "batch_id",
                UUID_TYPE,
                sa.ForeignKey("credit_batches.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("type", sa.String(20), nullable=False),
            sa.Column("qty", NUMERIC_CREDITS, nullable=False),
            sa.Column("balance_after", NUMERIC_CREDITS, nullable=False),
            sa.Column(
                "operation_id",
                UUID_TYPE,
                sa.ForeignKey("generation_operations.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("reference_type", sa.String(30), nullable=True),
            sa.Column("reference_id", UUID_TYPE, nullable=True),
            sa.Column("idempotency_key", sa.String(120), nullable=True),
            sa.Column("actor_id", UUID_TYPE, nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column(
                "occurred_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_credit_ledger_organization_id", "credit_ledger", ["organization_id"]
        )
        op.create_index("ix_credit_ledger_batch_id", "credit_ledger", ["batch_id"])
        op.create_index("ix_credit_ledger_type", "credit_ledger", ["type"])
        op.create_index(
            "ix_credit_ledger_org_occurred",
            "credit_ledger",
            ["organization_id", "occurred_at"],
        )
        op.create_index(
            "uq_credit_ledger_org_idempotency",
            "credit_ledger",
            ["organization_id", "idempotency_key"],
            unique=True,
            postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        )

    if not has_table("topup_quotes"):
        op.create_table(
            "topup_quotes",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column("plan_version_id", UUID_TYPE, nullable=True),
            sa.Column("credits", NUMERIC_CREDITS, nullable=False),
            sa.Column("subtotal", NUMERIC_MONEY, nullable=False),
            sa.Column("tax_amount", NUMERIC_MONEY, nullable=False, server_default="0"),
            sa.Column("amount", NUMERIC_MONEY, nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column("credit_expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_topup_quotes_organization_id", "topup_quotes", ["organization_id"]
        )

    if not has_table("topup_orders"):
        op.create_table(
            "topup_orders",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column(
                "quote_id",
                UUID_TYPE,
                sa.ForeignKey("topup_quotes.id"),
                nullable=False,
            ),
            sa.Column("invoice_id", UUID_TYPE, nullable=True),
            sa.Column("credits", NUMERIC_CREDITS, nullable=False),
            sa.Column("amount", NUMERIC_MONEY, nullable=False),
            sa.Column("currency", sa.String(3), nullable=False),
            sa.Column(
                "status", sa.String(20), nullable=False, server_default="created"
            ),
            sa.Column("provider", sa.String(30), nullable=True),
            sa.Column("provider_ref", sa.String(191), nullable=True),
            sa.Column("checkout_url", sa.Text(), nullable=True),
            sa.Column("idempotency_key", sa.String(120), nullable=False),
            sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
            *_timestamps(),
            sa.UniqueConstraint(
                "organization_id", "idempotency_key", name="uq_topup_orders_org_idem"
            ),
            sa.UniqueConstraint("provider_ref", name="uq_topup_orders_provider_ref"),
        )
        op.create_index(
            "ix_topup_orders_organization_id", "topup_orders", ["organization_id"]
        )
        op.create_index("ix_topup_orders_status", "topup_orders", ["status"])

    if not has_table("billing_provider_events"):
        op.create_table(
            "billing_provider_events",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=True),
            sa.Column("provider", sa.String(30), nullable=False),
            sa.Column("provider_event_id", sa.String(191), nullable=False, unique=True),
            sa.Column("event_type", sa.String(60), nullable=False),
            sa.Column("payload", JSONB_TYPE, nullable=True),
            sa.Column(
                "signature_verified",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "received_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_billing_provider_events_organization_id",
            "billing_provider_events",
            ["organization_id"],
        )

    if not has_table("billing_outbox_events"):
        op.create_table(
            "billing_outbox_events",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column("event_type", sa.String(60), nullable=False),
            sa.Column("payload", JSONB_TYPE, nullable=True),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("now()"),
            ),
        )
        op.create_index(
            "ix_billing_outbox_events_organization_id",
            "billing_outbox_events",
            ["organization_id"],
        )
        op.create_index(
            "ix_billing_outbox_published",
            "billing_outbox_events",
            ["published_at", "attempts"],
        )


def downgrade() -> None:
    for table in (
        "billing_outbox_events",
        "billing_provider_events",
        "topup_orders",
        "topup_quotes",
        "credit_ledger",
        "generation_operations",
        "credit_batches",
        "organization_subscriptions",
        "subscription_plan_versions",
        "subscription_plans",
    ):
        if has_table(table):
            op.drop_table(table)
