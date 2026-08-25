"""Merge the vehicle-arrival and UOM-packaging migration heads.

Revision ID: 088_merge_vehicle_arrival_heads
Revises: 077_link_vehicle_arrival_to_sessions_and_slips, 087_split_packaging_from_uoms
Create Date: 2026-08-25
"""

from collections.abc import Sequence

revision: str = "088_merge_vehicle_arrival_heads"
down_revision: tuple[str, str] = (
    "077_link_vehicle_arrival_to_sessions_and_slips",
    "087_split_packaging_from_uoms",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
