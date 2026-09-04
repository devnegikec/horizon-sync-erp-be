"""Add WMS worker scan + receiving-slip permissions.

Revision ID: 019
Revises: 018
Create Date: 2026-09-03

The ``wms.scan`` and ``receiving_slip.*`` permissions were defined in the
role templates (``app/core/modules.py``) and in ``scripts/seed_data.py``, but
were never inserted into the ``permissions`` table by a migration.  Environments
that were seeded before those permissions existed ended up with a
``warehouse_work_user`` role missing ``receiving_slip.create``, which causes
``POST /api/v1/inbound/sessions`` to return 403 for warehouse workers.

This migration inserts the missing permissions idempotently and assigns them
to the preloaded WMS roles (matching migration 017's pattern).
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import op

revision = "019"
down_revision = "018"
branch_labels = None
depends_on = None


# (code, name, description, resource, action)
PERMISSIONS = [
    (
        "wms.scan",
        "WMS Scan",
        "Scan QR codes for inbound receiving, picking, and put-away",
        "warehouse",
        "scan",
    ),
    (
        "receiving_slip.create",
        "Create Receiving Slip",
        "Start inbound scan sessions and create receiving slips",
        "receiving_slip",
        "create",
    ),
    (
        "receiving_slip.read",
        "Read Receiving Slip",
        "View receiving slips and inbound scan summaries",
        "receiving_slip",
        "read",
    ),
    (
        "receiving_slip.update",
        "Update Receiving Slip",
        "Update receiving slips (flag/reject items, assign bins)",
        "receiving_slip",
        "update",
    ),
]

# Which preloaded roles get each permission.
ASSIGNMENTS = {
    "wms.scan": [
        "system_admin",
        "org_admin",
        "wms_admin",
        "wms_manager",
        "wms_operator",
        "asn_coordinator",
        "warehouse_work_user",
    ],
    "receiving_slip.create": [
        "system_admin",
        "org_admin",
        "wms_admin",
        "wms_manager",
        "wms_operator",
        "warehouse_work_user",
    ],
    "receiving_slip.read": [
        "system_admin",
        "org_admin",
        "wms_admin",
        "wms_manager",
        "wms_operator",
        "asn_coordinator",
        "warehouse_work_user",
    ],
    "receiving_slip.update": [
        "system_admin",
        "org_admin",
        "wms_admin",
        "wms_manager",
        "wms_operator",
        "warehouse_work_user",
    ],
}


def upgrade():
    session = Session(bind=op.get_bind())
    try:
        for code, name, description, resource, action in PERMISSIONS:
            session.execute(
                text(
                    """
                    INSERT INTO permissions (
                        id, code, name, description, resource, action, module, category,
                        is_active, extra_data, created_at, updated_at
                    )
                    SELECT gen_random_uuid(), :code, :name, :description,
                           CAST(:resource AS resourcetype),
                           CAST(:action AS actiontype),
                           'wms', 'inbound', true, '{}', now(), now()
                    WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = :code)
                    """
                ),
                {
                    "code": code,
                    "name": name,
                    "description": description,
                    "resource": resource,
                    "action": action,
                },
            )

        for permission_code, role_codes in ASSIGNMENTS.items():
            for role_code in role_codes:
                session.execute(
                    text(
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
                    ),
                    {"role_code": role_code, "permission_code": permission_code},
                )
        session.commit()
    finally:
        session.close()


def downgrade():
    session = Session(bind=op.get_bind())
    try:
        codes = [row[0] for row in PERMISSIONS]
        session.execute(
            text(
                "DELETE FROM role_permissions WHERE permission_id IN "
                "(SELECT id FROM permissions WHERE code = ANY(:codes))"
            ),
            {"codes": codes},
        )
        session.execute(
            text("DELETE FROM permissions WHERE code = ANY(:codes)"),
            {"codes": codes},
        )
        session.commit()
    finally:
        session.close()
