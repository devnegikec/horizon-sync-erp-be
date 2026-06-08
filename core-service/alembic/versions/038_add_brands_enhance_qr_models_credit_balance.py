"""add brands, enhance qr models, credit balance

Revision ID: 038_add_brands_enhance_qr_models  
Revises: 037_add_b2b_billing_invoice_types
Create Date: 2026-03-22 10:00:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

from alembic import op

# revision identifiers, used by Alembic.
revision = "038_add_brands_enhance_qr_models"
down_revision = "037_add_b2b_billing_invoice_types"
branch_labels = None
depends_on = None


def _has_column(inspector, table_name: str, column_name: str) -> bool:
    return any(c["name"] == column_name for c in inspector.get_columns(table_name))


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i["name"] == index_name for i in inspector.get_indexes(table_name))

    def _has_constraint(table_name: str, constraint_name: str) -> bool:
        return any(c["name"] == constraint_name for c in inspector.get_unique_constraints(table_name))

    # ── brands table (NEW) ────────────────────────────────────────────────────
    if not inspector.has_table("brands"):
        op.create_table(
            "brands",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column("name", sa.String(256), nullable=True),
            sa.Column("short_code", sa.String(256), nullable=True),
            sa.Column("public_key", sa.String(512), nullable=True),
            sa.Column("private_key_encrypted", sa.Text, nullable=True),
            sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_brands_org", "brands", ["organization_id"])

    # ── qr_products: add brand_id FK ──────────────────────────────────────────
    if not _has_column(inspector, "qr_products", "brand_id"):
        op.add_column(
            "qr_products",
            sa.Column(
                "brand_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("brands.id"),
                nullable=True,
            ),
        )

    # ── qr_products: widen sr_number_type from String(12) to String(50) ──────
    if _has_column(inspector, "qr_products", "sr_number_type"):
        existing = next(c for c in inspector.get_columns("qr_products") if c["name"] == "sr_number_type")
        if existing.get("type") and str(existing["type"]) != "VARCHAR(50)":
            op.alter_column(
                "qr_products",
                "sr_number_type",
                type_=sa.String(50),
                existing_type=sa.String(12),
                existing_nullable=True,
            )

    # ── qr_blocks: add new columns ───────────────────────────────────────────
    if not _has_column(inspector, "qr_blocks", "status"):
        op.add_column("qr_blocks", sa.Column("status", sa.String(20), nullable=True))
    if not _has_column(inspector, "qr_blocks", "task_id"):
        op.add_column("qr_blocks", sa.Column("task_id", sa.String(255), nullable=True))
    if not _has_column(inspector, "qr_blocks", "download_url"):
        op.add_column("qr_blocks", sa.Column("download_url", sa.Text, nullable=True))
    if not _has_column(inspector, "qr_blocks", "completed_at"):
        op.add_column("qr_blocks", sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True))

    # ── product_items: add new columns ────────────────────────────────────────
    if not _has_column(inspector, "product_items", "qr_active"):
        op.add_column("product_items", sa.Column("qr_active", sa.Boolean, server_default="true"))
    if not _has_column(inspector, "product_items", "scan_count"):
        op.add_column("product_items", sa.Column("scan_count", sa.Integer, server_default="0"))
    if not _has_column(inspector, "product_items", "last_scanned_at"):
        op.add_column("product_items", sa.Column("last_scanned_at", sa.DateTime(timezone=True), nullable=True))

    # ── qr_credit_balance table (NEW) ─────────────────────────────────────────
    if not inspector.has_table("qr_credit_balance"):
        op.create_table(
            "qr_credit_balance",
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
                unique=True,
            ),
            sa.Column("total_credits", sa.Integer, nullable=False, server_default="0"),
            sa.Column("used_credits", sa.Integer, nullable=False, server_default="0"),
            sa.Column("balance_credits", sa.Integer, nullable=False, server_default="0"),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )
    if not _has_constraint("qr_credit_balance", "uq_qr_credit_balance_org"):
        op.create_unique_constraint(
            "uq_qr_credit_balance_org", "qr_credit_balance", ["organization_id"]
        )

    # ── qr_credit_ledger table (NEW) ──────────────────────────────────────────
    if not inspector.has_table("qr_credit_ledger"):
        op.create_table(
            "qr_credit_ledger",
            sa.Column(
                "id",
                postgresql.UUID(as_uuid=True),
                primary_key=True,
                server_default=sa.text("gen_random_uuid()"),
            ),
            sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
            sa.Column(
                "block_id",
                postgresql.UUID(as_uuid=True),
                sa.ForeignKey("qr_blocks.id"),
                nullable=True,
            ),
            sa.Column("quantity_deducted", sa.Integer, nullable=False),
            sa.Column("balance_after", sa.Integer, nullable=False),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
            ),
        )
    if not _has_index("qr_credit_ledger", "idx_qr_credit_ledger_org"):
        op.create_index("idx_qr_credit_ledger_org", "qr_credit_ledger", ["organization_id"])


def downgrade() -> None:
    # Drop new tables
    op.drop_table("qr_credit_ledger")
    op.drop_table("qr_credit_balance")

    # Remove new columns from product_items
    op.drop_column("product_items", "last_scanned_at")
    op.drop_column("product_items", "scan_count")
    op.drop_column("product_items", "qr_active")

    # Remove new columns from qr_blocks
    op.drop_column("qr_blocks", "completed_at")
    op.drop_column("qr_blocks", "download_url")
    op.drop_column("qr_blocks", "task_id")
    op.drop_column("qr_blocks", "status")

    # Revert sr_number_type column width
    op.alter_column(
        "qr_products",
        "sr_number_type",
        type_=sa.String(12),
        existing_type=sa.String(50),
        existing_nullable=True,
    )

    # Remove brand_id from qr_products
    op.drop_column("qr_products", "brand_id")

    # Drop brands table
    op.drop_table("brands")
