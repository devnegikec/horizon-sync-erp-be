"""Add sourcing flow tables (Material Request, RFQ, Purchase Order)

Revision ID: 004_add_sourcing_flow_tables
Revises: 003
Create Date: 2026-02-13 00:00:00.000000

"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_add_sourcing_flow_tables"
down_revision = "003_merge_bulk_and_quotations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enum types for sourcing flow
    op.execute(
        "CREATE TYPE materialrequeststatus AS ENUM ('draft', 'submitted', 'partially_quoted', 'fully_quoted', 'cancelled')"
    )
    op.execute(
        "CREATE TYPE rfqstatus AS ENUM ('draft', 'sent', 'partially_responded', 'fully_responded', 'closed')"
    )
    op.execute(
        "CREATE TYPE purchaseorderstatus AS ENUM ('draft', 'submitted', 'partially_received', 'fully_received', 'closed', 'cancelled')"
    )

    # Create material_requests table
    op.create_table(
        "material_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "submitted",
                "partially_quoted",
                "fully_quoted",
                "cancelled",
                name="materialrequeststatus",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_material_requests_organization_id"),
        "material_requests",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_requests_status"),
        "material_requests",
        ["status"],
        unique=False,
    )

    # Create material_request_lines table
    op.create_table(
        "material_request_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_request_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column("required_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["material_request_id"],
            ["material_requests.id"],
            name="material_request_lines_material_request_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="material_request_lines_item_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("quantity > 0", name="material_request_lines_quantity_check"),
    )
    op.create_index(
        op.f("ix_material_request_lines_organization_id"),
        "material_request_lines",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_request_lines_material_request_id"),
        "material_request_lines",
        ["material_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_material_request_lines_item_id"),
        "material_request_lines",
        ["item_id"],
        unique=False,
    )

    # Create rfqs table
    op.create_table(
        "rfqs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("material_request_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "sent",
                "partially_responded",
                "fully_responded",
                "closed",
                name="rfqstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("closing_date", sa.Date(), nullable=False),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["material_request_id"],
            ["material_requests.id"],
            name="rfqs_material_request_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "reference_type IS NULL OR reference_type = 'MATERIAL_REQUEST'",
            name="rfqs_reference_type_check",
        ),
    )
    op.create_index(
        op.f("ix_rfqs_organization_id"),
        "rfqs",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rfqs_material_request_id"),
        "rfqs",
        ["material_request_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rfqs_status"),
        "rfqs",
        ["status"],
        unique=False,
    )

    # Create rfq_lines table
    op.create_table(
        "rfq_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column("required_date", sa.Date(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["rfq_id"],
            ["rfqs.id"],
            name="rfq_lines_rfq_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="rfq_lines_item_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("quantity > 0", name="rfq_lines_quantity_check"),
    )
    op.create_index(
        op.f("ix_rfq_lines_organization_id"),
        "rfq_lines",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rfq_lines_rfq_id"),
        "rfq_lines",
        ["rfq_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rfq_lines_item_id"),
        "rfq_lines",
        ["item_id"],
        unique=False,
    )

    # Create rfq_suppliers table
    op.create_table(
        "rfq_suppliers",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["rfq_id"],
            ["rfqs.id"],
            name="rfq_suppliers_rfq_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="rfq_suppliers_supplier_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("rfq_id", "supplier_id", name="unique_rfq_supplier"),
    )
    op.create_index(
        op.f("ix_rfq_suppliers_organization_id"),
        "rfq_suppliers",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rfq_suppliers_rfq_id"),
        "rfq_suppliers",
        ["rfq_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_rfq_suppliers_supplier_id"),
        "rfq_suppliers",
        ["supplier_id"],
        unique=False,
    )

    # Create supplier_quotes table
    op.create_table(
        "supplier_quotes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfq_line_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("supplier_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quoted_price", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column("quoted_delivery_date", sa.Date(), nullable=False),
        sa.Column("supplier_notes", sa.Text(), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["rfq_line_id"],
            ["rfq_lines.id"],
            name="supplier_quotes_rfq_line_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="supplier_quotes_supplier_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("rfq_line_id", "supplier_id", name="unique_quote"),
        sa.CheckConstraint("quoted_price >= 0", name="supplier_quotes_quoted_price_check"),
    )
    op.create_index(
        op.f("ix_supplier_quotes_organization_id"),
        "supplier_quotes",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_quotes_rfq_line_id"),
        "supplier_quotes",
        ["rfq_line_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_supplier_quotes_supplier_id"),
        "supplier_quotes",
        ["supplier_id"],
        unique=False,
    )

    # Create purchase_orders table
    op.create_table(
        "purchase_orders",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rfq_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("reference_type", sa.String(length=50), nullable=True),
        sa.Column("reference_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "party_type",
            sa.String(length=50),
            nullable=False,
            server_default="SUPPLIER",
        ),
        sa.Column("party_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "submitted",
                "partially_received",
                "fully_received",
                "closed",
                "cancelled",
                name="purchaseorderstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "tax_amount",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("tax_rate", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "discount_amount",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "grand_total",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
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
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["rfq_id"],
            ["rfqs.id"],
            name="purchase_orders_rfq_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["party_id"],
            ["suppliers.id"],
            name="purchase_orders_party_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "party_type = 'SUPPLIER'",
            name="purchase_orders_party_type_check",
        ),
        sa.CheckConstraint(
            "reference_type IS NULL OR reference_type = 'RFQ'",
            name="purchase_orders_reference_type_check",
        ),
    )
    op.create_index(
        op.f("ix_purchase_orders_organization_id"),
        "purchase_orders",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_orders_party_id"),
        "purchase_orders",
        ["party_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_orders_rfq_id"),
        "purchase_orders",
        ["rfq_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_orders_status"),
        "purchase_orders",
        ["status"],
        unique=False,
    )

    # Create purchase_order_lines table
    op.create_table(
        "purchase_order_lines",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("purchase_order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("item_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=15, scale=4), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column(
            "line_total",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "received_quantity",
            sa.Numeric(precision=15, scale=4),
            nullable=False,
            server_default="0",
        ),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["purchase_order_id"],
            ["purchase_orders.id"],
            name="purchase_order_lines_purchase_order_id_fkey",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["item_id"],
            ["items.id"],
            name="purchase_order_lines_item_id_fkey",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint("quantity > 0", name="purchase_order_lines_quantity_check"),
        sa.CheckConstraint(
            "unit_price >= 0", name="purchase_order_lines_unit_price_check"
        ),
        sa.CheckConstraint(
            "received_quantity >= 0",
            name="purchase_order_lines_received_quantity_check",
        ),
        sa.CheckConstraint(
            "received_quantity <= quantity",
            name="purchase_order_lines_received_quantity_limit_check",
        ),
    )
    op.create_index(
        op.f("ix_purchase_order_lines_organization_id"),
        "purchase_order_lines",
        ["organization_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_order_lines_purchase_order_id"),
        "purchase_order_lines",
        ["purchase_order_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_purchase_order_lines_item_id"),
        "purchase_order_lines",
        ["item_id"],
        unique=False,
    )

    # Create status_transitions table
    op.create_table(
        "status_transitions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("entity_type", sa.String(length=50), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("previous_status", sa.String(length=50), nullable=False),
        sa.Column("new_status", sa.String(length=50), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "transitioned_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_status_transitions_entity_type"),
        "status_transitions",
        ["entity_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_status_transitions_entity_id"),
        "status_transitions",
        ["entity_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_status_transitions_transitioned_at"),
        "status_transitions",
        ["transitioned_at"],
        unique=False,
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("status_transitions")
    op.drop_table("purchase_order_lines")
    op.drop_table("purchase_orders")
    op.drop_table("supplier_quotes")
    op.drop_table("rfq_suppliers")
    op.drop_table("rfq_lines")
    op.drop_table("rfqs")
    op.drop_table("material_request_lines")
    op.drop_table("material_requests")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS purchaseorderstatus")
    op.execute("DROP TYPE IF EXISTS rfqstatus")
    op.execute("DROP TYPE IF EXISTS materialrequeststatus")
