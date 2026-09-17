"""Add permissions for the inbound exception and hold/quarantine workflow.

Revision ID: 017
Revises: 016
Create Date: 2026-08-25
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


PERMISSIONS = [
    (
        "inbound_exception.read",
        "View Inbound Exceptions",
        "View inbound exception, hold, and quarantine queues",
        "read",
    ),
    (
        "inbound_exception.create",
        "Classify Inbound Exceptions",
        "Classify inbound lines and upload optional evidence",
        "create",
    ),
    (
        "inbound_exception.dispose",
        "Dispose Inbound Exceptions",
        "Approve and dispose hold or quarantine exceptions (also requires warehouse manager authority)",
        "update",
    ),
]


def upgrade():
    session = Session(bind=op.get_bind())
    try:
        for code, name, description, action in PERMISSIONS:
            session.execute(
                text(
                    """
                    INSERT INTO permissions (
                        id, code, name, description, resource, action, module, category,
                        is_active, extra_data, created_at, updated_at
                    )
                    SELECT gen_random_uuid(), :code, :name, :description,
                           'warehouse', :action, 'wms', 'inbound', true, '{}', now(), now()
                    WHERE NOT EXISTS (SELECT 1 FROM permissions WHERE code = :code)
                    """
                ),
                {
                    "code": code,
                    "name": name,
                    "description": description,
                    "action": action,
                },
            )
        assignments = {
            "inbound_exception.read": [
                "system_admin",
                "org_admin",
                "wms_admin",
                "wms_manager",
                "warehouse_work_user",
            ],
            "inbound_exception.create": [
                "system_admin",
                "org_admin",
                "wms_admin",
                "wms_manager",
                "warehouse_work_user",
            ],
            "inbound_exception.dispose": [
                "system_admin",
                "org_admin",
                "wms_admin",
                "wms_manager",
            ],
        }
        for permission_code, role_codes in assignments.items():
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
        session.execute(
            text(
                "DELETE FROM role_permissions WHERE permission_id IN "
                "(SELECT id FROM permissions WHERE code = ANY(:codes))"
            ),
            {"codes": [row[0] for row in PERMISSIONS]},
        )
        session.execute(
            text("DELETE FROM permissions WHERE code = ANY(:codes)"),
            {"codes": [row[0] for row in PERMISSIONS]},
        )
        session.commit()
    finally:
        session.close()
