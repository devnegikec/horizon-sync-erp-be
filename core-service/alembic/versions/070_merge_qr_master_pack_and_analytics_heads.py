"""Merge the QR master-pack and analytics/QSeal migration branches.

Revision ID: 070_merge_qr_analytics_heads
Revises: 049_qr_block_master_pack, 069_add_scan_street_address
Create Date: 2026-08-21
"""

from collections.abc import Sequence

revision: str = "070_merge_qr_analytics_heads"
down_revision: tuple[str, str] = (
    "049_qr_block_master_pack",
    "069_add_scan_street_address",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
