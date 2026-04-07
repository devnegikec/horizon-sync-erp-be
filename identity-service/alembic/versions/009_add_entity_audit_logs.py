"""Add entity audit logs table for CRUD tracking on organizations and users.

Revision ID: 009
Revises: 008
Create Date: 2026-04-07
"""
from alembic import op
import sqlalchemy as sa


revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "entity_audit_logs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), nullable=True, index=True),
        sa.Column("organization_id", sa.Uuid(), nullable=True, index=True),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("table_name", sa.String(100), nullable=False),
        sa.Column("record_id", sa.Uuid(), nullable=False),
        sa.Column("old_values", sa.JSON(), nullable=True),
        sa.Column("new_values", sa.JSON(), nullable=True),
        sa.Column("changed_fields", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=True,
        ),
    )
    op.create_index(
        "idx_entity_audit_table_record",
        "entity_audit_logs",
        ["table_name", "record_id"],
    )
    op.create_index(
        "idx_entity_audit_action", "entity_audit_logs", ["action"]
    )
    op.create_index(
        "idx_entity_audit_created_at", "entity_audit_logs", ["created_at"]
    )
