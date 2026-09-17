"""make_tracking_session_columns_nullable

Revision ID: 070_make_tracking_session_columns_nullable
Revises: 069_sync_item_product
Create Date: 2026-08-13

Allow scanned_item_tracking rows to exist without an inbound scan session,
so Direct Put-Away can create tracking rows standalone.
"""

from collections.abc import Sequence
from typing import Union

from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "070_make_tracking_session_columns_nullable"
down_revision: Union[str, None] = "069_sync_item_product"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "scanned_item_tracking",
        "scan_session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.alter_column(
        "scanned_item_tracking",
        "scan_session_item_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "scanned_item_tracking",
        "scan_session_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.alter_column(
        "scanned_item_tracking",
        "scan_session_item_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
