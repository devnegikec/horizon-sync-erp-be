"""Add system admin permissions for B2B billing management

Revision ID: 006_system_admin_permissions
Revises: 005_add_master_org_and_billing
Create Date: 2024-12-20 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Session
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision = '006'
down_revision = '005'
branch_labels = None
depends_on = None


def upgrade():
    """Add system admin permissions for B2B billing management (Task 1C-1)"""
    
    connection = op.get_bind()
    session = Session(bind=connection)
    
    # Define the new system admin permissions using existing enum values
    permissions_data = [
        {
            'code': 'system_admin.master',
            'name': 'Master System Administrator',
            'description': 'Full system access with all permissions (*.*)',
            'resource': 'all',
            'action': 'manage',
            'module': 'admin',
            'category': 'system_admin'
        },
        {
            'code': 'system_admin.users',
            'name': 'Cross-Organization User Management',
            'description': 'User management across all organizations',
            'resource': 'user',
            'action': 'manage',
            'module': 'admin',
            'category': 'system_admin'
        },
        {
            'code': 'system_admin.organizations',
            'name': 'Organization Management',
            'description': 'Full organization management including deactivation',
            'resource': 'organization',
            'action': 'manage',
            'module': 'admin',
            'category': 'system_admin'
        },
        {
            'code': 'system_admin.billing',
            'name': 'Billing & Invoice Management', 
            'description': 'Cross-org invoice and payment management',
            'resource': 'all',  # Use 'all' resource for billing permissions
            'action': 'manage',
            'module': 'admin',
            'category': 'system_admin'
        },
        {
            'code': 'system_admin.reporting',
            'name': 'Analytics & Reporting',
            'description': 'System-wide analytics and reporting access',
            'resource': 'report',  # Use existing report resource
            'action': 'manage',
            'module': 'admin',
            'category': 'system_admin'
        }
    ]
    
    # Insert permissions
    for perm_data in permissions_data:
        # Check if permission already exists
        existing_perm = session.execute(
            text("SELECT id FROM permissions WHERE code = :code"),
            {'code': perm_data['code']}
        ).fetchone()
        
        if not existing_perm:
            session.execute(
                text("""
                    INSERT INTO permissions (
                        id, code, name, description, resource, action, module, category, 
                        is_active, extra_data, created_at, updated_at
                    ) VALUES (
                        gen_random_uuid(), :code, :name, :description, :resource, :action, 
                        :module, :category, true, '{}', NOW(), NOW()
                    )
                """),
                perm_data
            )
            print(f"✓ Created permission: {perm_data['name']}")
    
    # Get system_admin role ID for permission assignments
    system_admin_role = session.execute(
        text("SELECT id FROM roles WHERE code = 'system_admin' LIMIT 1")
    ).fetchone()
    
    if system_admin_role:
        role_id = system_admin_role[0]
        
        # Assign new permissions to system_admin role
        for perm_data in permissions_data:
            # Get permission ID
            perm_result = session.execute(
                text("SELECT id FROM permissions WHERE code = :code"),
                {'code': perm_data['code']}
            ).fetchone()
            
            if perm_result:
                perm_id = perm_result[0]
                
                # Check if assignment already exists
                existing_assignment = session.execute(
                    text("SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"),
                    {'role_id': role_id, 'perm_id': perm_id}
                ).fetchone()
                
                if not existing_assignment:
                    session.execute(
                        text("""
                            INSERT INTO role_permissions (id, role_id, permission_id) 
                            VALUES (gen_random_uuid(), :role_id, :perm_id)
                        """),
                        {'role_id': role_id, 'perm_id': perm_id}
                    )
                    print(f"✓ Assigned {perm_data['code']} to system_admin role")
    
    session.commit()
    session.close()


def downgrade():
    """Remove system admin permissions"""
    
    bind = op.get_bind()
    session = Session(bind=bind)
    
    # Remove role_permissions assignments
    permission_codes = [
        'system_admin.master',
        'system_admin.users', 
        'system_admin.organizations',
        'system_admin.billing',
        'system_admin.reporting'
    ]
    
    for code in permission_codes:
        session.execute(
            text("""
                DELETE FROM role_permissions 
                WHERE permission_id IN (
                    SELECT id FROM permissions WHERE code = :code
                )
            """),
            {'code': code}
        )
    
    # Remove permissions
    for code in permission_codes:
        session.execute(
            text("DELETE FROM permissions WHERE code = :code"),
            {'code': code}
        )
    
    session.commit()
    session.close()
    
    # Note: We don't remove the enum values as they might be used elsewhere
    # If needed, enum values would need to be dropped carefully