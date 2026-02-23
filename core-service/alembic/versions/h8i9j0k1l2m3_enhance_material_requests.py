"""enhance material requests

Revision ID: h8i9j0k1l2m3
Revises: g7h8i9j0k1l2
Create Date: 2026-02-19 15:30:00.000000

"""
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "h8i9j0k1l2m3"
down_revision = "g7h8i9j0k1l2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create new enum types
    material_request_type_enum = postgresql.ENUM(
        "purchase", "transfer", "issue", name="materialrequesttype", create_type=True
    )
    material_request_type_enum.create(op.get_bind(), checkfirst=True)

    material_request_priority_enum = postgresql.ENUM(
        "low",
        "medium",
        "high",
        "urgent",
        name="materialrequestpriority",
        create_type=True,
    )
    material_request_priority_enum.create(op.get_bind(), checkfirst=True)

    # Add columns to material_requests table
    op.add_column(
        "material_requests", sa.Column("request_no", sa.String(50), nullable=True)
    )
    op.add_column(
        "material_requests",
        sa.Column(
            "type",
            sa.Enum(
                "purchase",
                "transfer",
                "issue",
                name="materialrequesttype",
                create_type=False,
            ),
            nullable=False,
            server_default="purchase",
        ),
    )
    op.add_column(
        "material_requests",
        sa.Column(
            "priority",
            sa.Enum(
                "low",
                "medium",
                "high",
                "urgent",
                name="materialrequestpriority",
                create_type=False,
            ),
            nullable=False,
            server_default="medium",
        ),
    )
    op.add_column(
        "material_requests",
        sa.Column("target_warehouse_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "material_requests",
        sa.Column("requested_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "material_requests", sa.Column("department", sa.String(100), nullable=True)
    )

    # Note: Foreign key for target_warehouse_id will be added when warehouses table is created
    # For now, we'll just store the UUID without FK constraint

    # Add index for request_no
    op.create_index(
        "ix_material_requests_request_no", "material_requests", ["request_no"]
    )

    # Add columns to material_request_lines table
    op.add_column(
        "material_request_lines", sa.Column("uom", sa.String(50), nullable=True)
    )
    op.add_column(
        "material_request_lines",
        sa.Column("estimated_unit_cost", sa.Numeric(15, 4), nullable=True),
    )
    op.add_column(
        "material_request_lines",
        sa.Column("requested_for", sa.String(255), nullable=True),
    )
    op.add_column(
        "material_request_lines",
        sa.Column("requested_for_department", sa.String(100), nullable=True),
    )


def downgrade() -> None:
    # Remove columns from material_request_lines
    op.drop_column("material_request_lines", "requested_for_department")
    op.drop_column("material_request_lines", "requested_for")
    op.drop_column("material_request_lines", "estimated_unit_cost")
    op.drop_column("material_request_lines", "uom")

    # Remove index and columns from material_requests
    op.drop_index("ix_material_requests_request_no", "material_requests")
    # Note: No FK to drop since warehouses table may not exist

    # Remove columns from material_requests
    op.drop_column("material_requests", "department")
    op.drop_column("material_requests", "requested_by")
    op.drop_column("material_requests", "target_warehouse_id")
    op.drop_column("material_requests", "priority")
    op.drop_column("material_requests", "type")
    op.drop_column("material_requests", "request_no")

    # Drop enum types
    sa.Enum(name="materialrequestpriority").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="materialrequesttype").drop(op.get_bind(), checkfirst=True)
