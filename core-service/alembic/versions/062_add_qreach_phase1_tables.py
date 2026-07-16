"""Add QReach Phase 1 tables and columns

Revision ID: 062
Revises: 061
Create Date: 2026-07-16

Adds:
  - New tables: lead_notes, stores, qreach_api_keys, landing_customizations
  - New columns on campaign_leads: marital_status, lead_owner_id, is_archived, is_blocklisted
"""

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID

from alembic import op

revision = "062_add_qreach_phase1_tables"
down_revision = "061_add_bin_location_and_putaway_to_receiving_slip_items"
branch_labels = None
depends_on = None


def upgrade():
    # ── New columns on campaign_leads ────────────────────────────────────
    op.add_column(
        "campaign_leads", sa.Column("marital_status", sa.String(30), nullable=True)
    )
    op.add_column(
        "campaign_leads", sa.Column("lead_owner_id", UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        "campaign_leads",
        sa.Column(
            "is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
    )
    op.add_column(
        "campaign_leads",
        sa.Column(
            "is_blocklisted",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )
    op.create_index(
        "ix_campaign_leads_lead_owner_id", "campaign_leads", ["lead_owner_id"]
    )
    op.create_index("ix_campaign_leads_is_archived", "campaign_leads", ["is_archived"])

    # ── lead_notes ───────────────────────────────────────────────────────
    op.create_table(
        "lead_notes",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "lead_id",
            UUID(as_uuid=True),
            sa.ForeignKey("campaign_leads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_lead_notes_organization_id", "lead_notes", ["organization_id"])
    op.create_index("ix_lead_notes_lead_id", "lead_notes", ["lead_id"])

    # ── stores ───────────────────────────────────────────────────────────
    op.create_table(
        "stores",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(50), nullable=True),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("city", sa.String(100), nullable=True),
        sa.Column("state", sa.String(100), nullable=True),
        sa.Column("country", sa.String(100), nullable=True),
        sa.Column("pincode", sa.String(30), nullable=True),
        sa.Column("contact_person", sa.String(255), nullable=True),
        sa.Column("contact_phone", sa.String(20), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column(
            "is_archived", sa.Boolean(), nullable=False, server_default=sa.text("false")
        ),
        sa.Column("extra_data", JSONB(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_stores_organization_id", "stores", ["organization_id"])
    op.create_index("ix_stores_code", "stores", ["code"])

    # ── qreach_api_keys ──────────────────────────────────────────────────
    op.create_table(
        "qreach_api_keys",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("prefix", sa.String(12), nullable=False),
        sa.Column("hashed_key", sa.String(255), nullable=False),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_qreach_api_keys_organization_id", "qreach_api_keys", ["organization_id"]
    )
    op.create_index("ix_qreach_api_keys_hashed_key", "qreach_api_keys", ["hashed_key"])

    # ── landing_customizations ───────────────────────────────────────────
    op.create_table(
        "landing_customizations",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "campaign_id",
            UUID(as_uuid=True),
            sa.ForeignKey("campaigns.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("form_config", JSONB(), nullable=True),
        sa.Column("theme_config", JSONB(), nullable=True),
        sa.Column(
            "is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")
        ),
        sa.Column("extra_data", JSONB(), nullable=True),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_landing_customizations_organization_id",
        "landing_customizations",
        ["organization_id"],
    )
    op.create_index(
        "ix_landing_customizations_campaign_id",
        "landing_customizations",
        ["campaign_id"],
    )


def downgrade():
    op.drop_table("landing_customizations")
    op.drop_table("qreach_api_keys")
    op.drop_table("stores")
    op.drop_table("lead_notes")

    op.drop_index("ix_campaign_leads_is_archived", table_name="campaign_leads")
    op.drop_index("ix_campaign_leads_lead_owner_id", table_name="campaign_leads")
    op.drop_column("campaign_leads", "is_blocklisted")
    op.drop_column("campaign_leads", "is_archived")
    op.drop_column("campaign_leads", "lead_owner_id")
    op.drop_column("campaign_leads", "marital_status")
