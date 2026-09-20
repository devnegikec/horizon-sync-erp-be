"""Keep short-receipt history when its balance is purged (append-only audit).

``inbound_short_balance_events`` is the append-only audit trail of a shortage:
every arrival records expected/received/short, the reason code, the note and the
actor. Revision ``119_add_shortage_tracking`` created its ``balance_id`` foreign
key with ``ON DELETE CASCADE``, which contradicts that intent:

* ``inbound_short_balances`` itself cascades from ``asn_orders`` /
  ``asn_order_items``, so deleting (or purging) an ASN silently deleted the
  shortage balances **and** their entire history,
* the event rows are self-contained snapshots, so they can and must outlive the
  balance they were projected from.

This revision re-points the FK at ``ON DELETE SET NULL`` and makes ``balance_id``
nullable, so a purge nulls the link instead of erasing the evidence. Revision 119
already creates the constraint correctly for fresh databases, so this migration is
a no-op there and only repairs databases where 119 was applied beforehand.

Revision ID: 120_fix_shortage_history_fk
Revises: 119_add_shortage_tracking
Create Date: 2026-09-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from app.alembic_guards import has_table

revision: str = "120_fix_shortage_history_fk"
down_revision: str | Sequence[str] | None = "119_add_shortage_tracking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EVENTS_TABLE = "inbound_short_balance_events"

#: Auto-named FK created with the history table (``<table>_<column>_fkey``).
BALANCE_FK = "inbound_short_balance_events_balance_id_fkey"


def _balance_fk_ondelete() -> str | None:
    """Return the live ``ON DELETE`` rule of the history table's balance FK."""
    if not has_table(EVENTS_TABLE):
        return None
    for fk in sa.inspect(op.get_bind()).get_foreign_keys(EVENTS_TABLE):
        if fk.get("name") == BALANCE_FK:
            options = fk.get("options") or {}
            return (options.get("ondelete") or "").upper() or None
    return None


def _recreate_balance_fk(ondelete: str) -> None:
    """Replace the balance FK with the requested ``ON DELETE`` rule."""
    op.drop_constraint(BALANCE_FK, EVENTS_TABLE, type_="foreignkey")
    op.create_foreign_key(
        BALANCE_FK,
        EVENTS_TABLE,
        "inbound_short_balances",
        ["balance_id"],
        ["id"],
        ondelete=ondelete,
    )


def upgrade() -> None:
    rule = _balance_fk_ondelete()
    if rule is None or rule == "SET NULL":
        # Table/constraint absent, or 119 already created the safe rule.
        return

    op.alter_column(EVENTS_TABLE, "balance_id", nullable=True)
    _recreate_balance_fk("SET NULL")


def downgrade() -> None:
    rule = _balance_fk_ondelete()
    if rule is None or rule == "CASCADE":
        return

    op.alter_column(EVENTS_TABLE, "balance_id", nullable=False)
    _recreate_balance_fk("CASCADE")
