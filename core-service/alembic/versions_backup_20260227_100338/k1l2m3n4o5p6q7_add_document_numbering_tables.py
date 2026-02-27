"""add document_numbering_config and document_sequence_counter tables

Revision ID: k1l2m3n4o5p6q7
Revises: j0k1l2m3n4o5p6
Create Date: 2025-02-23

Configurable document numbering series (prefix, padding, include_year) per
organization and document type. Sequence counter for atomic next-number.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, BOOLEAN

revision = "k1l2m3n4o5p6q7"
down_revision = "j0k1l2m3n4o5p6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_numbering_config",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("document_type", sa.String(50), nullable=False, index=True),
        sa.Column("prefix", sa.String(20), nullable=False),
        sa.Column("padding", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("include_year", BOOLEAN, nullable=False, server_default="true"),
        sa.Column("separator", sa.String(5), nullable=False, server_default=sa.text("'-'")),
        sa.UniqueConstraint("organization_id", "document_type", name="uq_doc_numbering_org_type"),
    )

    op.create_table(
        "document_sequence_counter",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", UUID(as_uuid=True), nullable=False, index=True),
        sa.Column("document_type", sa.String(50), nullable=False, index=True),
        sa.Column("sequence_year", sa.Integer(), nullable=True),
        sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint(
            "organization_id",
            "document_type",
            "sequence_year",
            name="uq_doc_sequence_org_type_year",
        ),
    )


def downgrade() -> None:
    op.drop_table("document_sequence_counter")
    op.drop_table("document_numbering_config")
