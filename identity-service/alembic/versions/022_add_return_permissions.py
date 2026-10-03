"""Add returns module permissions + ``return`` resource type.

Revision ID: 022
Revises: 021
Create Date: 2026-09-20

Backlog ``R-10`` / ``X-02``: the returns MVP introduces its own permission codes
instead of borrowing the receiving ones, so the dock and the back office can be
granted independently:

    return.read      — list/read registrations, sessions and receipt notes
    return.register  — create/cancel a registration (back office only)
    return.receive   — open a dock session, scan, end the session
    return.classify  — capture the condition of a returned unit
    return.approve   — approve/reject a Return Receipt Note
    return.dispose   — set the per-line disposition

``resourcetype`` and ``actiontype`` are Postgres enums. ``return`` has to be
added to ``resourcetype``; the actions reuse existing enum labels (the distinct
codes are what ``has_permission`` matches on), matching how
``inbound_exception.dispose`` is stored with action ``update``.
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import op

revision = "022"
down_revision = "021"
branch_labels = None
depends_on = None

# (code, name, description, action) — resource is always 'return'.
PERMISSIONS = [
    (
        "return.read",
        "Read Returns",
        "View return registrations, dock sessions and return receipt notes",
        "read",
    ),
    (
        "return.register",
        "Register Return",
        "Create and cancel a customer return registration (back office)",
        "create",
    ),
    (
        "return.receive",
        "Receive Return",
        "Open a return receiving session, scan units and end the session (dock)",
        "scan",
    ),
    (
        "return.classify",
        "Classify Returned Unit",
        "Capture the condition (good/damaged/hold/quarantine) of a returned unit",
        "update",
    ),
    (
        "return.approve",
        "Approve Return Note",
        "Approve or reject a Return Receipt Note (warehouse manager)",
        "manage",
    ),
    (
        "return.dispose",
        "Dispose Returned Line",
        "Set the final disposition of a returned line (warehouse manager)",
        "manage",
    ),
]

# Which preloaded role codes get each permission. The dock roles receive and
# classify but never approve (contract §6); the back office registers.
ASSIGNMENTS = {
    "return.read": [
        "super_admin",
        "org_admin",
        "organization_admin",
        "owner",
        "wms_admin",
        "wms_manager",
        "wms_operator",
        "asn_coordinator",
        "warehouse_work_user",
        "warehouse_staff",
    ],
    "return.register": [
        "super_admin",
        "org_admin",
        "organization_admin",
        "owner",
        "wms_admin",
        "wms_manager",
    ],
    "return.receive": [
        "super_admin",
        "org_admin",
        "organization_admin",
        "owner",
        "wms_admin",
        "wms_manager",
        "wms_operator",
        "warehouse_work_user",
        "warehouse_staff",
    ],
    "return.classify": [
        "super_admin",
        "org_admin",
        "organization_admin",
        "owner",
        "wms_admin",
        "wms_manager",
        "wms_operator",
        "warehouse_work_user",
        "warehouse_staff",
    ],
    "return.approve": [
        "super_admin",
        "org_admin",
        "organization_admin",
        "owner",
        "wms_admin",
        "wms_manager",
    ],
    "return.dispose": [
        "super_admin",
        "org_admin",
        "organization_admin",
        "owner",
        "wms_admin",
        "wms_manager",
    ],
}

_INSERT_PERMISSION = text(
    """
    INSERT INTO permissions (
        id, code, name, description, resource, action, module, category,
        is_active, extra_data, created_at, updated_at
    )
    SELECT gen_random_uuid(), :code, :name, :description,
           CAST('return' AS resourcetype),
           CAST(:action AS actiontype),
           'wms', 'returns', true, '{}', now(), now()
    WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = :code)
    """
)

_INSERT_ROLE_PERMISSION = text(
    """
    INSERT INTO role_permissions (id, role_id, permission_id)
    SELECT gen_random_uuid(), roles.id, permissions.id
    FROM roles, permissions
    WHERE roles.code = :role_code AND permissions.code = :permission_code
    AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_permissions.role_id = roles.id
          AND role_permissions.permission_id = permissions.id
    )
    """
)


def _bind_engine(bind):
    """Return a raw Engine from an Alembic bind (Connection or Engine)."""
    return getattr(bind, "engine", bind)


def upgrade():
    bind = op.get_bind()
    engine = _bind_engine(bind)

    # ``ALTER TYPE ... ADD VALUE`` cannot be used in the same transaction that
    # subsequently casts to the new label unless the type itself was created in
    # that transaction (fresh install). Same split as migration 020.
    with engine.connect() as probe:
        type_committed = (
            probe.execute(
                text("SELECT 1 FROM pg_type WHERE typname = 'resourcetype'")
            ).scalar()
            is not None
        )

    if type_committed:
        with engine.execution_options(isolation_level="AUTOCOMMIT").connect() as conn:
            conn.execute(
                text("ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'return'")
            )
    else:
        op.execute(text("ALTER TYPE resourcetype ADD VALUE IF NOT EXISTS 'return'"))

    session = Session(bind=bind)
    try:
        for code, name, description, action in PERMISSIONS:
            session.execute(
                _INSERT_PERMISSION,
                {
                    "code": code,
                    "name": name,
                    "description": description,
                    "action": action,
                },
            )

        for permission_code, role_codes in ASSIGNMENTS.items():
            for role_code in role_codes:
                session.execute(
                    _INSERT_ROLE_PERMISSION,
                    {"role_code": role_code, "permission_code": permission_code},
                )
        session.commit()
    finally:
        session.close()


def downgrade():
    session = Session(bind=op.get_bind())
    try:
        # Do not delete role_permissions: seed data may have granted these to
        # the same roles independently. Only drop the permission rows once
        # nothing references them (mirrors migration 019).
        session.execute(
            text(
                "DELETE FROM permissions "
                "WHERE code LIKE 'return.%' "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM role_permissions rp "
                "  WHERE rp.permission_id = permissions.id"
                ")"
            )
        )
        session.commit()
    finally:
        session.close()
