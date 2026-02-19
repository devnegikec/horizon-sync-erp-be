"""add communication_logs table

Revision ID: g7h8i9j0k1l2
Revises: f6g7h8i9j0k1
Create Date: 2026-02-19 11:00:00.000000

"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k1l2"
down_revision: Union[str, None] = "f6g7h8i9j0k1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create communication_logs table and related enums"""

    # Create enums
    op.execute(
        """
        CREATE TYPE communicationdoctype AS ENUM (
            'quotation', 'sales_order', 'purchase_order', 'invoice',
            'delivery_note', 'purchase_receipt', 'payment', 'rfq', 'material_request'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE communicationchannel AS ENUM (
            'email', 'whatsapp', 'sms', 'webhook'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE communicationstatus AS ENUM (
            'pending', 'sent', 'delivered', 'failed', 'bounced'
        )
        """
    )

    op.execute(
        """
        CREATE TYPE recipienttype AS ENUM (
            'customer', 'supplier', 'employee', 'other'
        )
        """
    )

    # Create table
    op.create_table(
        "communication_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False),
        sa.Column(
            "doc_type",
            sa.Enum(
                "quotation",
                "sales_order",
                "purchase_order",
                "invoice",
                "delivery_note",
                "purchase_receipt",
                "payment",
                "rfq",
                "material_request",
                name="communicationdoctype",
            ),
            nullable=False,
        ),
        sa.Column("doc_id", UUID(as_uuid=True), nullable=False),
        sa.Column("doc_no", sa.String(100), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "channel",
            sa.Enum(
                "email",
                "whatsapp",
                "sms",
                "webhook",
                name="communicationchannel",
            ),
            nullable=False,
        ),
        sa.Column(
            "recipient_type",
            sa.Enum(
                "customer",
                "supplier",
                "employee",
                "other",
                name="recipienttype",
            ),
            nullable=True,
        ),
        sa.Column("recipient", sa.String(255), nullable=False),
        sa.Column("recipient_name", sa.String(255), nullable=True),
        sa.Column("sender_id", UUID(as_uuid=True), nullable=False),
        sa.Column("sender_name", sa.String(255), nullable=True),
        sa.Column("sender_email", sa.String(255), nullable=True),
        sa.Column("subject", sa.String(500), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "sent",
                "delivered",
                "failed",
                "bounced",
                name="communicationstatus",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
    )

    # Create indexes
    op.create_index(
        "idx_communication_logs_organization_id",
        "communication_logs",
        ["organization_id"],
    )
    op.create_index(
        "idx_communication_logs_doc_id",
        "communication_logs",
        ["doc_id"],
    )
    op.create_index(
        "idx_communication_logs_doc_type",
        "communication_logs",
        ["doc_type"],
    )
    op.create_index(
        "idx_communication_logs_status",
        "communication_logs",
        ["status"],
    )
    op.create_index(
        "idx_communication_logs_channel",
        "communication_logs",
        ["channel"],
    )
    op.create_index(
        "idx_communication_logs_created_at",
        "communication_logs",
        ["created_at"],
    )
    # Composite index for common query pattern
    op.create_index(
        "idx_communication_logs_org_doc",
        "communication_logs",
        ["organization_id", "doc_type", "doc_id"],
    )


def downgrade() -> None:
    """Drop communication_logs table and related enums"""
    op.drop_table("communication_logs")
    op.execute("DROP TYPE IF EXISTS communicationdoctype")
    op.execute("DROP TYPE IF EXISTS communicationchannel")
    op.execute("DROP TYPE IF EXISTS communicationstatus")
    op.execute("DROP TYPE IF EXISTS recipienttype")
