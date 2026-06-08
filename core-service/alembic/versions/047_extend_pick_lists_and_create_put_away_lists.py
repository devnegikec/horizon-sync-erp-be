"""Extend pick_lists, pick_list_items and create put_away_lists/put_away_list_items tables

Revision ID: 047_extend_pick_lists_and_create_put_away_lists
Revises: 046_add_worker_tasks_and_location_scans
Create Date: 2025-07-14

Extends existing pick_lists and pick_list_items tables with columns needed
for the SAP invoice-triggered outbound workflow (invoice reference, bin
location tracking, dispatch linkage).

Creates put_away_lists and put_away_list_items tables for the inbound
put-away workflow with bin location assignments, sort ordering, and
item-level status tracking.

Requirements: 9.1, 9.4, 8.4
"""

import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision = "047_extend_pick_lists_and_create_put_away_lists"
down_revision = "046_add_worker_tasks_and_location_scans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ══════════════════════════════════════════════════════════════════
    # ALTER pick_lists: add invoice_reference, invoice_data,
    #                   dispatch_record_id columns
    # ══════════════════════════════════════════════════════════════════
    inspector = inspect(op.get_bind())

    def _has_index(table_name: str, index_name: str) -> bool:
        return any(i['name'] == index_name for i in inspector.get_indexes(table_name))

    op.add_column(
        "pick_lists",
        sa.Column("invoice_reference", sa.String(255), nullable=True),
    )
    op.add_column(
        "pick_lists",
        sa.Column("invoice_data", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "pick_lists",
        sa.Column(
            "dispatch_record_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("dispatch_records.id"),
            nullable=True,
        ),
    )

    # ══════════════════════════════════════════════════════════════════
    # ALTER pick_list_items: add bin_location_id column
    # (picked_qty and sort_order already exist on this table)
    # ══════════════════════════════════════════════════════════════════
    op.add_column(
        "pick_list_items",
        sa.Column(
            "bin_location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouse_locations.id"),
            nullable=True,
        ),
    )

    # ══════════════════════════════════════════════════════════════════
    # CREATE put_away_lists table
    # ══════════════════════════════════════════════════════════════════
    op.create_table(
        "put_away_lists",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "warehouse_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouses_extended.id"),
            nullable=False,
        ),
        sa.Column("put_away_list_no", sa.String(100), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("reference_type", sa.String(50), nullable=True),
        sa.Column(
            "reference_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "receiving_slip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("receiving_slips.id"),
            nullable=True,
        ),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column(
            "assigned_to",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'cancelled')",
            name="chk_put_away_list_status",
        ),
    )

    # Indexes for put_away_lists
    op.create_index("idx_pal_org", "put_away_lists", ["organization_id"])
    op.create_index("idx_pal_warehouse", "put_away_lists", ["warehouse_id"])
    op.create_index("idx_pal_status", "put_away_lists", ["status"])
    op.create_index("idx_pal_receiving_slip", "put_away_lists", ["receiving_slip_id"])

    # ══════════════════════════════════════════════════════════════════
    # CREATE put_away_list_items table (with bin_location_id, sort_order,
    # and status columns included from the start)
    # ══════════════════════════════════════════════════════════════════
    op.create_table(
        "put_away_list_items",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "put_away_list_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("put_away_lists.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id"),
            nullable=False,
        ),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("batch_number", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Numeric(15, 3), nullable=False),
        sa.Column(
            "bin_location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouse_locations.id"),
            nullable=True,
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0"),
        sa.Column(
            "status",
            sa.String(20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'completed', 'skipped')",
            name="chk_put_away_item_status",
        ),
    )

    # Indexes for put_away_list_items
    op.create_index("idx_pali_list", "put_away_list_items", ["put_away_list_id"])
    op.create_index("idx_pali_bin", "put_away_list_items", ["bin_location_id"])
    op.create_index("idx_pali_item", "put_away_list_items", ["item_id"])
    op.create_index("idx_pali_status", "put_away_list_items", ["status"])


def downgrade() -> None:
    # Drop put_away_list_items indexes and table
    op.drop_index("idx_pali_status", table_name="put_away_list_items")
    op.drop_index("idx_pali_item", table_name="put_away_list_items")
    op.drop_index("idx_pali_bin", table_name="put_away_list_items")
    op.drop_index("idx_pali_list", table_name="put_away_list_items")
    op.drop_table("put_away_list_items")

    # Drop put_away_lists indexes and table
    op.drop_index("idx_pal_receiving_slip", table_name="put_away_lists")
    op.drop_index("idx_pal_status", table_name="put_away_lists")
    op.drop_index("idx_pal_warehouse", table_name="put_away_lists")
    op.drop_index("idx_pal_org", table_name="put_away_lists")
    op.drop_table("put_away_lists")

    # Remove added columns from pick_list_items
    op.drop_column("pick_list_items", "bin_location_id")

    # Remove added columns from pick_lists
    op.drop_column("pick_lists", "dispatch_record_id")
    op.drop_column("pick_lists", "invoice_data")
    op.drop_column("pick_lists", "invoice_reference")
