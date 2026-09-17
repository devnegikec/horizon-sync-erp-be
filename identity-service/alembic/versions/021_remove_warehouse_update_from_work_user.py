"""Remove warehouse.update from the warehouse_work_user role.

``warehouse_work_user`` is the QR-login worker role and must remain limited to
scanning/operational actions. ``warehouse.update`` also gates the warehouse
record-edit endpoint (``PUT /warehouses/{id}``), location CRUD, allocations and
capacity refreshes — none of which a floor worker should hold. Workers keep
their operational access via ``wms.scan`` on the put-away/inbound endpoints.

Revision ID: 021
Revises: 020
Create Date: 2026-09-04
"""

from sqlalchemy import text
from sqlalchemy.orm import Session

from alembic import op

revision = "021"
down_revision = "020"
branch_labels = None
depends_on = None


def upgrade():
    session = Session(bind=op.get_bind())
    try:
        session.execute(
            text(
                """
                DELETE FROM role_permissions
                WHERE permission_id IN (
                    SELECT id FROM permissions WHERE code = 'warehouse.update'
                )
                  AND role_id IN (
                    SELECT id FROM roles WHERE code = 'warehouse_work_user'
                )
                """
            )
        )
        session.commit()
    finally:
        session.close()


def downgrade():
    session = Session(bind=op.get_bind())
    try:
        session.execute(
            text(
                """
                INSERT INTO role_permissions (id, role_id, permission_id)
                SELECT gen_random_uuid(), roles.id, permissions.id
                FROM roles, permissions
                WHERE roles.code = 'warehouse_work_user'
                  AND permissions.code = 'warehouse.update'
                  AND NOT EXISTS (
                    SELECT 1 FROM role_permissions
                    WHERE role_permissions.role_id = roles.id
                      AND role_permissions.permission_id = permissions.id
                  )
                """
            )
        )
        session.commit()
    finally:
        session.close()
