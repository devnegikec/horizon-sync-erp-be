"""Add org_admin invitation permissions

Revision ID: 011
Revises: 010_add_missing_resourcetype_enum_values
Create Date: 2026-05-19 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    """Add invitation permissions and assign them to org_admin roles."""
    connection = op.get_bind()
    session = Session(bind=connection)

    permissions_data = [
        {
            'code': 'user.invite',
            'name': 'Invite User',
            'description': 'Invite users to the organization',
            'resource': 'user',
            'action': 'invite',
            'module': 'identity',
            'category': 'user_management',
        },
        {
            'code': 'invitation.create',
            'name': 'Create Invitation',
            'description': 'Create invitation records for new users',
            'resource': 'invitation',
            'action': 'create',
            'module': 'identity',
            'category': 'user_management',
        },
    ]

    for perm_data in permissions_data:
        existing_perm = session.execute(
            text("SELECT id FROM permissions WHERE code = :code"),
            {'code': perm_data['code']},
        ).fetchone()

        if not existing_perm:
            session.execute(
                text("""
                    INSERT INTO permissions (
                        id, code, name, description, resource, action, module,
                        category, is_active, extra_data, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), :code, :name, :description,
                        :resource, :action, :module, :category, true, '{}', NOW(), NOW()
                    )
                """),
                perm_data,
            )

    org_admin_roles = session.execute(
        text("SELECT id FROM roles WHERE code = 'org_admin'")
    ).fetchall()

    for role_row in org_admin_roles:
        role_id = role_row[0]
        for perm_data in permissions_data:
            perm_result = session.execute(
                text("SELECT id FROM permissions WHERE code = :code"),
                {'code': perm_data['code']},
            ).fetchone()
            if not perm_result:
                continue
            perm_id = perm_result[0]
            existing_assignment = session.execute(
                text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"
                ),
                {'role_id': role_id, 'perm_id': perm_id},
            ).fetchone()
            if not existing_assignment:
                session.execute(
                    text(
                        "INSERT INTO role_permissions (id, role_id, permission_id) VALUES (gen_random_uuid(), :role_id, :perm_id)"
                    ),
                    {'role_id': role_id, 'perm_id': perm_id},
                )

    session.commit()
    session.close()


def downgrade():
    """Remove org_admin invitation permissions."""
    bind = op.get_bind()
    session = Session(bind=bind)

    permission_codes = ['user.invite', 'invitation.create']

    for code in permission_codes:
        session.execute(
            text("""
                DELETE FROM role_permissions
                WHERE permission_id IN (
                    SELECT id FROM permissions WHERE code = :code
                )
            """),
            {'code': code},
        )
        session.execute(text("DELETE FROM permissions WHERE code = :code"), {'code': code})

    session.commit()
    session.close()
