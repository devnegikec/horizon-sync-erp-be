"""Add inbound exception, hold/quarantine, and non-pickable staging framework.

Revision ID: 078_add_inbound_exception_hold_quarantine
Revises: 077_link_vehicle_arrival_to_sessions_and_slips
Create Date: 2026-08-25
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

from app.alembic_guards import has_column, has_index, has_table

revision: str = "078_add_inbound_exception_hold_quarantine"
down_revision: str | Sequence[
    str
] | None = "077_link_vehicle_arrival_to_sessions_and_slips"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _ensure_column(table: str, column: sa.Column) -> None:
    """Add a column only when it does not already exist (idempotent re-run)."""
    if not has_column(table, column.name):
        op.add_column(table, column)


def _ensure_index(name: str, table: str, columns: list[str]) -> None:
    """Create an index only when it does not already exist (idempotent re-run)."""
    if not has_index(table, name):
        op.create_index(name, table, columns)


def _ensure_table(name: str, *columns: sa.Column) -> None:
    """Create a table only when it does not already exist (idempotent re-run)."""
    if not has_table(name):
        op.create_table(name, *columns)


def upgrade() -> None:
    _ensure_column(
        "warehouse_locations",
        sa.Column(
            "is_pickable", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
    )
    _ensure_index(
        "ix_warehouse_locations_is_pickable", "warehouse_locations", ["is_pickable"]
    )

    _ensure_column(
        "receiving_slip_items",
        sa.Column(
            "condition_code", sa.String(30), nullable=False, server_default="GOOD"
        ),
    )
    _ensure_column(
        "receiving_slip_items",
        sa.Column("exception_status", sa.String(30), nullable=True),
    )
    _ensure_column(
        "receiving_slip_items",
        sa.Column(
            "exception_destination_location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    _ensure_index(
        "ix_receiving_slip_items_exception_destination_location_id",
        "receiving_slip_items",
        ["exception_destination_location_id"],
    )
    _ensure_column(
        "scanned_item_tracking",
        sa.Column(
            "stock_location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )

    _ensure_table(
        "inbound_exception_reasons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(40), nullable=False),
        sa.Column("default_destination", sa.String(30), nullable=True),
        sa.Column(
            "requires_approval", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    _ensure_index(
        "ix_inbound_exception_reasons_organization_id",
        "inbound_exception_reasons",
        ["organization_id"],
    )

    _ensure_table(
        "inbound_exceptions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "warehouse_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouses_extended.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "asn_order_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("asn_orders.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scan_sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "slip_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("receiving_slips.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "slip_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("receiving_slip_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "scan_session_item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scan_session_items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "tracking_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("scanned_item_tracking.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "item_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("items.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("exception_type", sa.String(50), nullable=False),
        sa.Column("reason_code", sa.String(80), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column(
            "condition_code", sa.String(30), nullable=False, server_default="GOOD"
        ),
        sa.Column("destination", sa.String(30), nullable=True),
        sa.Column(
            "destination_location_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("warehouse_locations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("qr_identifier", sa.String(255), nullable=True),
        sa.Column("sku", sa.String(100), nullable=True),
        sa.Column("batch_number", sa.String(100), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("raw_qr_data", sa.Text(), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB(), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("disposition", sa.String(40), nullable=True),
        sa.Column("disposition_note", sa.Text(), nullable=True),
        sa.Column("disposed_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("disposed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    for column in (
        "organization_id",
        "warehouse_id",
        "asn_order_id",
        "session_id",
        "slip_id",
        "slip_item_id",
        "scan_session_item_id",
        "tracking_id",
        "item_id",
        "exception_type",
        "reason_code",
        "status",
        "destination",
        "qr_identifier",
        "sku",
        "created_by",
        "approved_by",
        "disposed_by",
        "created_at",
    ):
        _ensure_index(
            f"ix_inbound_exceptions_{column}", "inbound_exceptions", [column]
        )

    _ensure_table(
        "inbound_exception_evidence",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "exception_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inbound_exceptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("storage_key", sa.String(500), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    _ensure_index(
        "ix_inbound_exception_evidence_exception_id",
        "inbound_exception_evidence",
        ["exception_id"],
    )
    _ensure_index(
        "ix_inbound_exception_evidence_organization_id",
        "inbound_exception_evidence",
        ["organization_id"],
    )
    _ensure_index(
        "ix_inbound_exception_evidence_uploaded_by",
        "inbound_exception_evidence",
        ["uploaded_by"],
    )

    _ensure_table(
        "inbound_exception_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "exception_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("inbound_exceptions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("device_context", postgresql.JSONB(), nullable=True),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    for column in (
        "exception_id",
        "organization_id",
        "event_type",
        "actor_id",
        "created_at",
    ):
        _ensure_index(
            f"ix_inbound_exception_events_{column}",
            "inbound_exception_events",
            [column],
        )

    reason_rows = [
        ("SHORT_PHYSICAL", "Physical shortage", "short", None, False),
        ("DAMAGED", "Damaged goods", "damage", "QUARANTINE", False),
        ("EXCESS", "Excess receipt", "excess", "HOLD", True),
        (
            "UNEXPECTED_KNOWN_SKU",
            "Known SKU not on ASN",
            "unexpected_sku",
            "HOLD",
            True,
        ),
        (
            "UNKNOWN_IDENTITY",
            "Unknown SKU or identity",
            "unknown_identity",
            "QUARANTINE",
            True,
        ),
        ("HOLD", "Operational hold", "hold", "HOLD", False),
        (
            "QUARANTINE",
            "Quality or compliance quarantine",
            "quarantine",
            "QUARANTINE",
            False,
        ),
    ]
    reasons_table = sa.table(
        "inbound_exception_reasons",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("code", sa.String),
        sa.column("name", sa.String),
        sa.column("category", sa.String),
        sa.column("default_destination", sa.String),
        sa.column("requires_approval", sa.Boolean),
    )
    existing_codes = {
        row[0]
        for row in op.get_bind().execute(
            sa.text("SELECT code FROM inbound_exception_reasons")
        ).fetchall()
    }
    op.bulk_insert(
        reasons_table,
        [
            {
                "id": uuid.uuid4(),
                "code": code,
                "name": name,
                "category": category,
                "default_destination": destination,
                "requires_approval": approval,
            }
            for code, name, category, destination, approval in reason_rows
            if code not in existing_codes
        ],
    )

    # Provision standard non-pickable WMS bins for every existing warehouse.
    bind = op.get_bind()
    warehouses = bind.execute(
        sa.text("SELECT id, organization_id FROM warehouses_extended")
    ).fetchall()
    for warehouse_id, organization_id in warehouses:
        for code, name in (
            ("RECEIVING-STAGE", "Receiving Stage"),
            ("HOLD", "Hold"),
            ("QUARANTINE", "Quarantine"),
        ):
            bind.execute(
                sa.text(
                    """
                    INSERT INTO warehouse_locations (
                        id, organization_id, warehouse_id, location_type, code, full_path, name,
                        capacity, total_capacity, available_capacity, position_x, position_y, position_z,
                        is_available, is_active, is_pickable, version, created_at, updated_at
                    )
                    SELECT :id, :organization_id, :warehouse_id, 'bin', :code, :full_path, :name,
                           0, 0, 0, 0, 0, 0, true, true, false, 1, now(), now()
                    WHERE NOT EXISTS (
                        SELECT 1 FROM warehouse_locations
                        WHERE warehouse_id = :warehouse_id AND code = :code
                    )
                    """
                ),
                {
                    "id": uuid.uuid4(),
                    "organization_id": organization_id,
                    "warehouse_id": warehouse_id,
                    "code": code,
                    "full_path": code,
                    "name": name,
                },
            )


def downgrade() -> None:
    op.drop_table("inbound_exception_events")
    op.drop_table("inbound_exception_evidence")
    op.drop_table("inbound_exceptions")
    op.drop_table("inbound_exception_reasons")
    op.drop_column("scanned_item_tracking", "stock_location_id")
    op.drop_index(
        "ix_receiving_slip_items_exception_destination_location_id",
        table_name="receiving_slip_items",
    )
    op.drop_column("receiving_slip_items", "exception_destination_location_id")
    op.drop_column("receiving_slip_items", "exception_status")
    op.drop_column("receiving_slip_items", "condition_code")
    op.drop_index(
        "ix_warehouse_locations_is_pickable", table_name="warehouse_locations"
    )
    op.drop_column("warehouse_locations", "is_pickable")
