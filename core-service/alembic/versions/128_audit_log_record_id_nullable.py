"""Allow ``audit_logs.record_id`` to be NULL.

Some audited tables use a natural, non-UUID primary key — ``system_config``
keys on a string ``key``. ``_get_record_id`` used to coerce the primary key with
``uuid.UUID(str(pk))``, which raises for those tables; the audit listeners
swallow their own errors, so every mutation of such a row was silently recorded
as *nothing at all*.

The column is now nullable so those mutations are still audited, with
``record_id = NULL``. Rows written before this migration are unaffected.

Revision ID: 128_audit_log_record_id_nullable
Revises: 127_merge_audit_role_master_carton
Create Date: 2026-09-23
"""

from collections.abc import Sequence

from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_column, has_table

revision: str = "128_audit_log_record_id_nullable"
down_revision: str | Sequence[str] | None = "127_merge_audit_role_master_carton"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not has_table("audit_logs") or not has_column("audit_logs", "record_id"):
        return

    op.alter_column(
        "audit_logs",
        "record_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )


def downgrade() -> None:
    if not has_table("audit_logs") or not has_column("audit_logs", "record_id"):
        return

    # Rows audited without a record id cannot satisfy NOT NULL, so clear them
    # rather than failing the downgrade.
    op.execute("DELETE FROM audit_logs WHERE record_id IS NULL")

    op.alter_column(
        "audit_logs",
        "record_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
