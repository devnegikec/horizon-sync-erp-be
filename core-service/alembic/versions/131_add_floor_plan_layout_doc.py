"""Add warehouse_floor_plans.layout_doc for JSON-imported layouts

Revision ID: 131_add_floor_plan_layout_doc
Revises: 130_merge_layout_designer_heads
Create Date: 2026-09-27

The JSON Layout Designer stores the imported layout *document* on the plan so it can
be fetched back and re-imported. It is deliberately a separate column from `config`,
which keeps holding the form-shaped FloorPlanConfig that FloorPlanGeneratorService
writes - the two are different formats with different readers.

Nullable, and **no backfill**: plans created before this migration keep their
document in `config["layout_doc"]`, and LayoutDesignService.get_stored_document
prefers the column but falls back to that key, so old and new rows both round-trip.

Idempotency guards match the house style (app/alembic_guards.py), so running this
against a database that already has the column is a no-op rather than an error.
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_table

revision = "131_add_floor_plan_layout_doc"
down_revision = "130_merge_layout_designer_heads"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not has_table("warehouse_floor_plans"):
        return
    if not has_column("warehouse_floor_plans", "layout_doc"):
        op.add_column(
            "warehouse_floor_plans",
            sa.Column(
                "layout_doc",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=True,
                comment="Layout document v1 imported via the JSON Layout Designer",
            ),
        )


def downgrade() -> None:
    if not has_table("warehouse_floor_plans"):
        return
    if has_column("warehouse_floor_plans", "layout_doc"):
        op.drop_column("warehouse_floor_plans", "layout_doc")
