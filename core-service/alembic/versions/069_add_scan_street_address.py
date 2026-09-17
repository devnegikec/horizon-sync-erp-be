"""Add formatted street address to QR scan events.

Revision ID: 069_add_scan_street_address
Revises: 068_add_public_scan_analytics_fields
Create Date: 2026-08-14
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_column

revision: str = "069_add_scan_street_address"
down_revision: str | None = "068_add_public_scan_analytics_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_column("qr_scan_events", "street_address"):
        op.add_column(
            "qr_scan_events",
            sa.Column("street_address", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    if has_column("qr_scan_events", "street_address"):
        op.drop_column("qr_scan_events", "street_address")
