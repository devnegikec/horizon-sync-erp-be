"""Merge the two 129 heads so the layout-document column has a single base

Revision ID: 130_merge_layout_designer_heads
Revises: 129_asn_short_delivery_close, 129_bulk_put_away_jobs
Create Date: 2026-09-27

`129_asn_short_delivery_close` and `129_bulk_put_away_jobs` both descend from the
previous history but never re-joined, so the tree had two heads. The JSON Layout
Designer needs a single linear base for its column migration, so this merge joins
them without changing any schema.
"""

revision = "130_merge_layout_designer_heads"
down_revision = ("129_asn_short_delivery_close", "129_bulk_put_away_jobs")
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Merge point only - no schema change."""


def downgrade() -> None:
    """Re-split into the two 129 heads (also no schema change)."""
