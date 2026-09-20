"""Returns module: registration, receiving session and Return Receipt Note.

Implements backlog ``R-01`` → ``R-05`` (Phase 2 of
``docs/Exception Gap/INBOUND_EXCEPTION_AND_RETURNS_GAP_ANALYSIS.md``): the
customer-returns chain Registration → Arrival → Scan → Classification → Draft
Note, per the contract in ``RETURNS_WEB_APP_INTEGRATION.md`` /
``RETURNS_HANDHELD_INTEGRATION.md``.

Also seeds the three tenant-configurable return reason codes the registration
and the condition picker are built on (``RETURN_GOOD``, ``RETURN_DAMAGED``,
``RETURN_SCRAP``) so the UI never hard-codes codes (contract §7).

The document numbering series (``return_registration`` / ``RR`` and
``return_receipt`` / ``RRN``) is created lazily by
:class:`DocumentNumberingService` from ``DEFAULT_PREFIXES``, so no rows are
seeded here.

Every step is guarded so the migration is safe to re-run against a database
whose schema was (partly) created from the SQLAlchemy models.

Revision ID: 124_returns_module
Revises: 123_notification_inbound_exception
Create Date: 2026-09-20
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op
from app.alembic_guards import has_table

revision: str = "124_returns_module"
down_revision: str | Sequence[str] | None = "123_notification_inbound_exception"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID_TYPE = postgresql.UUID(as_uuid=True)
JSONB_TYPE = postgresql.JSONB(astext_type=sa.Text())

#: (code, name, category, default_destination, requires_approval)
NEW_REASONS = (
    ("RETURN_GOOD", "Returned in good condition", "return_good", None, False),
    (
        "RETURN_DAMAGED",
        "Returned damaged",
        "return_damage",
        "QUARANTINE",
        True,
    ),
    (
        "RETURN_SCRAP",
        "Returned for scrap",
        "return_scrap",
        "DAMAGED",
        True,
    ),
)

REASONS_TABLE = sa.table(
    "inbound_exception_reasons",
    sa.column("id", UUID_TYPE),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("category", sa.String),
    sa.column("default_destination", sa.String),
    sa.column("requires_approval", sa.Boolean),
)


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    ]


def upgrade() -> None:
    _create_return_registrations()
    _create_return_sessions()
    _create_return_receipt_notes()
    _seed_reason_codes()


def _create_return_registrations() -> None:
    if not has_table("return_registrations"):
        op.create_table(
            "return_registrations",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column("registration_no", sa.String(100), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
            sa.Column(
                "reference_type",
                sa.String(30),
                nullable=False,
                server_default="invoice",
            ),
            sa.Column("reference_id", UUID_TYPE, nullable=True),
            sa.Column("reference_no", sa.String(100), nullable=True),
            sa.Column("party_id", UUID_TYPE, nullable=True),
            sa.Column("party_name", sa.String(255), nullable=True),
            sa.Column(
                "warehouse_id",
                UUID_TYPE,
                sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("return_reason_code", sa.String(80), nullable=True),
            sa.Column("return_date", sa.DateTime(timezone=True), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "expected_qty",
                sa.Numeric(15, 3),
                nullable=False,
                server_default="0",
            ),
            sa.Column(
                "received_qty",
                sa.Numeric(15, 3),
                nullable=False,
                server_default="0",
            ),
            sa.Column("cancelled_reason", sa.Text(), nullable=True),
            sa.Column("cancelled_by", UUID_TYPE, nullable=True),
            sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_by", UUID_TYPE, nullable=True),
            *_timestamps(),
            sa.CheckConstraint(
                "status IN ('draft','ready','receiving','received','closed','cancelled')",
                name="chk_return_registration_status",
            ),
            sa.CheckConstraint(
                "reference_type IN ('invoice','dealer','warehouse','delivery_note')",
                name="chk_return_registration_reference_type",
            ),
        )
        op.create_index(
            "ix_return_registrations_org_status",
            "return_registrations",
            ["organization_id", "status"],
        )
        op.create_index(
            "ix_return_registrations_org_warehouse",
            "return_registrations",
            ["organization_id", "warehouse_id"],
        )
        op.create_index(
            "ix_return_registrations_org_reference_no",
            "return_registrations",
            ["organization_id", "reference_no"],
        )

    if not has_table("return_registration_items"):
        op.create_table(
            "return_registration_items",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column(
                "registration_id",
                UUID_TYPE,
                sa.ForeignKey("return_registrations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "item_id",
                UUID_TYPE,
                sa.ForeignKey("items.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("sku", sa.String(100), nullable=False),
            sa.Column("item_name", sa.String(255), nullable=True),
            sa.Column("uom", sa.String(50), nullable=False, server_default="NOS"),
            sa.Column("expected_qty", sa.Numeric(15, 3), nullable=False),
            sa.Column(
                "received_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column("serials", JSONB_TYPE, nullable=True),
            sa.Column("sort_order", sa.Integer(), server_default="0"),
            *_timestamps(),
        )
        op.create_index(
            "ix_return_registration_items_registration",
            "return_registration_items",
            ["registration_id"],
        )
        op.create_index(
            "ix_return_registration_items_org_sku",
            "return_registration_items",
            ["organization_id", "sku"],
        )


def _create_return_sessions() -> None:
    if not has_table("return_sessions"):
        op.create_table(
            "return_sessions",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column(
                "registration_id",
                UUID_TYPE,
                sa.ForeignKey("return_registrations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "warehouse_id",
                UUID_TYPE,
                sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("status", sa.String(20), nullable=False, server_default="open"),
            sa.Column("dock_location", sa.String(120), nullable=True),
            sa.Column("device_id", sa.String(120), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column(
                "expected_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column(
                "scanned_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column(
                "classified_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column("started_by", UUID_TYPE, nullable=True),
            sa.Column(
                "started_at",
                sa.DateTime(timezone=True),
                server_default=sa.func.now(),
            ),
            sa.Column("ended_by", UUID_TYPE, nullable=True),
            sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
            *_timestamps(),
            sa.CheckConstraint(
                "status IN ('open','ended','cancelled')",
                name="chk_return_session_status",
            ),
        )
        op.create_index(
            "ix_return_sessions_registration",
            "return_sessions",
            ["registration_id"],
        )
        op.create_index(
            "ix_return_sessions_org_status",
            "return_sessions",
            ["organization_id", "status"],
        )
        # Only one OPEN session may exist per registration (contract §2).
        op.create_index(
            "uq_return_sessions_open_registration",
            "return_sessions",
            ["registration_id"],
            unique=True,
            postgresql_where=sa.text("status = 'open'"),
        )

    if not has_table("return_session_items"):
        op.create_table(
            "return_session_items",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column(
                "session_id",
                UUID_TYPE,
                sa.ForeignKey("return_sessions.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("registration_id", UUID_TYPE, nullable=False),
            sa.Column(
                "registration_item_id",
                UUID_TYPE,
                sa.ForeignKey("return_registration_items.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "item_id",
                UUID_TYPE,
                sa.ForeignKey("items.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("sku", sa.String(100), nullable=True),
            sa.Column("qr_identifier", sa.String(255), nullable=False),
            sa.Column("serial_number", sa.String(255), nullable=True),
            sa.Column("batch_number", sa.String(100), nullable=True),
            sa.Column(
                "quantity", sa.Numeric(15, 3), nullable=False, server_default="1"
            ),
            sa.Column(
                "over_receipt", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column("condition", sa.String(20), nullable=True),
            sa.Column("reason_code", sa.String(80), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("destination", sa.String(30), nullable=True),
            sa.Column(
                "exception_id",
                UUID_TYPE,
                sa.ForeignKey("inbound_exceptions.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "stock_entered", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column(
                "stock_location_id",
                UUID_TYPE,
                sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("device_type", sa.String(50), nullable=True),
            sa.Column("os", sa.String(80), nullable=True),
            sa.Column("scanned_by", UUID_TYPE, nullable=True),
            sa.Column(
                "scanned_at", sa.DateTime(timezone=True), server_default=sa.func.now()
            ),
            sa.Column("classified_by", UUID_TYPE, nullable=True),
            sa.Column("classified_at", sa.DateTime(timezone=True), nullable=True),
            *_timestamps(),
        )
        op.create_index(
            "ix_return_session_items_session", "return_session_items", ["session_id"]
        )
        op.create_index(
            "ix_return_session_items_org_qr",
            "return_session_items",
            ["organization_id", "qr_identifier"],
        )


def _create_return_receipt_notes() -> None:
    if not has_table("return_receipt_notes"):
        op.create_table(
            "return_receipt_notes",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column("note_no", sa.String(100), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
            sa.Column(
                "registration_id",
                UUID_TYPE,
                sa.ForeignKey("return_registrations.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "session_id",
                UUID_TYPE,
                sa.ForeignKey("return_sessions.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "warehouse_id",
                UUID_TYPE,
                sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "expected_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column(
                "received_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column(
                "short_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column(
                "good_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column(
                "damaged_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column(
                "hold_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column(
                "quarantine_qty", sa.Numeric(15, 3), nullable=False, server_default="0"
            ),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("approved_by", UUID_TYPE, nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejected_by", UUID_TYPE, nullable=True),
            sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("rejection_reason", sa.Text(), nullable=True),
            sa.Column(
                "put_away_generated_at", sa.DateTime(timezone=True), nullable=True
            ),
            sa.Column("created_by", UUID_TYPE, nullable=True),
            *_timestamps(),
            sa.CheckConstraint(
                "status IN ('draft','pending_approval','approved','rejected')",
                name="chk_return_receipt_note_status",
            ),
        )
        op.create_index(
            "ix_return_receipt_notes_org_status",
            "return_receipt_notes",
            ["organization_id", "status"],
        )
        op.create_index(
            "ix_return_receipt_notes_registration",
            "return_receipt_notes",
            ["registration_id"],
        )

    if not has_table("return_receipt_note_items"):
        op.create_table(
            "return_receipt_note_items",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column(
                "note_id",
                UUID_TYPE,
                sa.ForeignKey("return_receipt_notes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column(
                "registration_item_id",
                UUID_TYPE,
                sa.ForeignKey("return_registration_items.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "session_item_id",
                UUID_TYPE,
                sa.ForeignKey("return_session_items.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column(
                "item_id",
                UUID_TYPE,
                sa.ForeignKey("items.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("sku", sa.String(100), nullable=True),
            sa.Column("item_name", sa.String(255), nullable=True),
            sa.Column("uom", sa.String(50), nullable=False, server_default="NOS"),
            sa.Column("serial_number", sa.String(255), nullable=True),
            sa.Column("batch_number", sa.String(100), nullable=True),
            sa.Column(
                "quantity", sa.Numeric(15, 3), nullable=False, server_default="1"
            ),
            sa.Column("condition", sa.String(20), nullable=True),
            sa.Column("reason_code", sa.String(80), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("destination", sa.String(30), nullable=True),
            sa.Column(
                "exception_id",
                UUID_TYPE,
                sa.ForeignKey("inbound_exceptions.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("disposition", sa.String(40), nullable=True),
            sa.Column("disposition_reason_code", sa.String(80), nullable=True),
            sa.Column("disposition_note", sa.Text(), nullable=True),
            sa.Column("disposed_by", UUID_TYPE, nullable=True),
            sa.Column("disposed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sort_order", sa.Integer(), server_default="0"),
            *_timestamps(),
        )
        op.create_index(
            "ix_return_receipt_note_items_note",
            "return_receipt_note_items",
            ["note_id"],
        )
        op.create_index(
            "ix_return_receipt_note_items_org_condition",
            "return_receipt_note_items",
            ["organization_id", "condition"],
        )

    if not has_table("return_receipt_note_events"):
        op.create_table(
            "return_receipt_note_events",
            sa.Column("id", UUID_TYPE, primary_key=True),
            sa.Column(
                "note_id",
                UUID_TYPE,
                sa.ForeignKey("return_receipt_notes.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("organization_id", UUID_TYPE, nullable=False),
            sa.Column("event_type", sa.String(60), nullable=False),
            sa.Column("actor_id", UUID_TYPE, nullable=True),
            sa.Column("details", JSONB_TYPE, nullable=True),
            sa.Column(
                "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
            ),
        )
        op.create_index(
            "ix_return_receipt_note_events_note",
            "return_receipt_note_events",
            ["note_id"],
        )


def _seed_reason_codes() -> None:
    """Seed the return reason codes the UI pickers filter on (contract §7)."""
    if not has_table("inbound_exception_reasons"):
        return
    existing = {
        row[0]
        for row in op.get_bind()
        .execute(sa.text("SELECT code FROM inbound_exception_reasons"))
        .fetchall()
    }
    rows = [
        {
            "id": uuid.uuid4(),
            "code": code,
            "name": name,
            "category": category,
            "default_destination": destination,
            "requires_approval": requires_approval,
        }
        for code, name, category, destination, requires_approval in NEW_REASONS
        if code not in existing
    ]
    if rows:
        op.bulk_insert(REASONS_TABLE, rows)


def downgrade() -> None:
    op.execute(
        sa.text(
            "DELETE FROM inbound_exception_reasons "
            "WHERE code IN ('RETURN_GOOD','RETURN_DAMAGED','RETURN_SCRAP')"
        )
    )
    for table in (
        "return_receipt_note_events",
        "return_receipt_note_items",
        "return_receipt_notes",
        "return_session_items",
        "return_sessions",
        "return_registration_items",
        "return_registrations",
    ):
        if has_table(table):
            op.drop_table(table)
