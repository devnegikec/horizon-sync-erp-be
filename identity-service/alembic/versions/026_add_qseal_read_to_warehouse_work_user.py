"""Grant qseal.read to the warehouse_work_user role.

Revision ID: 026
Revises: 025
Create Date: 2026-10-05

Warehouse workers scan QR codes (including QSeal QR codes), so the
``warehouse_work_user`` role needs ``qseal.read`` in addition to its existing
WMS scan / receiving-slip / pick-list permissions.

The ``qseal.read`` permission itself is created by migration 023; this
migration only adds the role-permission link for existing databases and is
idempotent (safe to re-run).
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import op

revision = "026"
down_revision = "025"
branch_labels = None
depends_on = None

_INSERT_ROLE_PERMISSION = text(
    """
    INSERT INTO role_permissions (id, role_id, permission_id)
    SELECT gen_random_uuid(), roles.id, permissions.id
    FROM roles, permissions
    WHERE roles.code = 'warehouse_work_user'
      AND permissions.code = 'qseal.read'
      AND NOT EXISTS (
        SELECT 1 FROM role_permissions
        WHERE role_permissions.role_id = roles.id
          AND role_permissions.permission_id = permissions.id
      )
    """
)

_DELETE_ROLE_PERMISSION = text(
    """
    DELETE FROM role_permissions
    WHERE permission_id IN (
        SELECT id FROM permissions WHERE code = 'qseal.read'
    )
      AND role_id IN (
        SELECT id FROM roles WHERE code = 'warehouse_work_user'
      )
    """
)


def upgrade():
    session = Session(bind=op.get_bind())
    try:
        session.execute(_INSERT_ROLE_PERMISSION)
        session.commit()
    finally:
        session.close()


def downgrade():
    session = Session(bind=op.get_bind())
    try:
        session.execute(_DELETE_ROLE_PERMISSION)
        session.commit()
    finally:
        session.close()
