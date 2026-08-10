"""Add landing_page_configs table

Revision ID: 063_add_landing_page_configs
Revises: 062_add_customers_is_tax_exempt
Create Date: 2026-07-26
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table

revision = "063_add_landing_page_configs"
down_revision = "061_add_bin_location_and_putaway_to_receiving_slip_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not has_table("landing_page_configs"):
        op.create_table(
            "landing_page_configs",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column(
                "organization_id",
                postgresql.UUID(as_uuid=True),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "product_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("qr_products.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
                index=True,
            ),
            # Visuals
            sa.Column("logo_url", sa.Text(), nullable=True),
            sa.Column("banner_image_url", sa.Text(), nullable=True),
            # Branding
            sa.Column(
                "primary_color",
                sa.String(7),
                nullable=False,
                server_default=sa.text("'#1a56db'"),
            ),
            sa.Column(
                "accent_color",
                sa.String(7),
                nullable=False,
                server_default=sa.text("'#f59e0b'"),
            ),
            # Sections (JSONB)
            sa.Column(
                "product_details",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "social_links",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
            sa.Column(
                "feedback",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "warranty",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "custom_cta",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            sa.Column(
                "footer",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'{}'::jsonb"),
            ),
            # Audit
            sa.Column(
                "created_by",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
            sa.Column(
                "updated_by",
                postgresql.UUID(as_uuid=True),
                nullable=True,
            ),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.text("CURRENT_TIMESTAMP"),
            ),
        )

        # Trigger to auto-update updated_at
        op.execute(
            """
            CREATE OR REPLACE FUNCTION update_landing_page_configs_updated_at()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """
        )
        op.execute(
            """
            CREATE TRIGGER trg_landing_page_configs_updated_at
            BEFORE UPDATE ON landing_page_configs
            FOR EACH ROW
            EXECUTE FUNCTION update_landing_page_configs_updated_at();
        """
        )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_landing_page_configs_updated_at "
        "ON landing_page_configs"
    )
    op.execute("DROP FUNCTION IF EXISTS update_landing_page_configs_updated_at()")
    if has_table("landing_page_configs"):
        op.drop_table("landing_page_configs")
