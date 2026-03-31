#!/usr/bin/env python3
"""
CREATE SYSTEM ADMINISTRATOR USER

Creates a new system administrator user with system_admin.master permission.
Generates secure credentials and assigns proper roles and organization relationships.
"""

import os
import uuid
import secrets
import string
import bcrypt
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection
IDENTITY_DATABASE_URL = os.getenv(
    "IDENTITY_DATABASE_URL", 
    "postgresql://horizon_user:horizon_pass@localhost:5432/identity_db"
)

def generate_secure_password(length=12):
    """Generate a secure random password (shorter to avoid bcrypt 72-byte limit)"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def create_system_admin_user():
    """
    Create a new system administrator user with system_admin.master permission
    """
    print("🔐 CREATING SYSTEM ADMINISTRATOR USER")
    print("=" * 50)
    
    # Generate secure credentials
    username = "system_admin"
    password = generate_secure_password(12)  # Shorter to avoid bcrypt limit
    email = f"{username}@horizonsync.com"
    
    print(f"📋 Generated Credentials:")
    print(f"   → Username: {username}")
    print(f"   → Email: {email}")
    print(f"   → Password: {password}")
    print(f"   → Password Length: {len(password)} characters")
    
    # Create database connection
    identity_engine = create_engine(IDENTITY_DATABASE_URL)
    IdentitySession = sessionmaker(bind=identity_engine)
    db = IdentitySession()
    
    try:
        # Step 1: Get system admin role from the organization where it exists
        print(f"\n1. Getting system admin role from the correct organization...")
        
        system_admin_role = db.execute(text("""
            SELECT r.id, r.name, r.organization_id, o.name as org_name, o.organization_type
            FROM roles r
            JOIN organizations o ON r.organization_id = o.id
            WHERE r.code = 'system_admin'
        """)).fetchone()
        
        if not system_admin_role:
            print("   ❌ System Administrator role not found!")
            return None
            
        print(f"   ✅ System Admin Role: {system_admin_role.name} ({system_admin_role.id})")
        print(f"   ✅ Role Organization: {system_admin_role.org_name} ({system_admin_role.organization_id})")
        
        # Also get master organization for reference
        master_org = db.execute(text("""
            SELECT id, name FROM organizations 
            WHERE organization_type = 'master'
        """)).fetchone()
        
        if master_org:
            print(f"   ℹ️  Master Organization: {master_org.name} ({master_org.id})")
        else:
            print("   ⚠️  Master organization not found")
        
        # Step 2: Check if user already exists
        print(f"\n2. Checking if user already exists...")
        
        existing_user = db.execute(text("""
            SELECT id, email, first_name, last_name FROM users 
            WHERE email = :email
        """), {'email': email}).fetchone()
        
        if existing_user:
            print(f"   ⚠️  User already exists: {existing_user.email}")
            print(f"   → User ID: {existing_user.id}")
            print(f"   → Name: {existing_user.first_name} {existing_user.last_name}")
            
            # Check if already has system admin role
            existing_role = db.execute(text("""
                SELECT r.name FROM user_organization_roles uor
                JOIN roles r ON uor.role_id = r.id
                WHERE uor.user_id = :user_id 
                AND uor.organization_id = :org_id
                AND r.code = 'system_admin'
            """), {
                'user_id': existing_user.id, 
                'org_id': system_admin_role.organization_id
            }).fetchone()
            
            if existing_role:
                print(f"   ✅ User already has {existing_role.name} role")
                return {
                    'username': username,
                    'email': email,
                    'password': 'EXISTING_USER - Password not changed',
                    'user_id': existing_user.id,
                    'status': 'existing'
                }
            else:
                user_id = existing_user.id
                create_new_user = False
        else:
            print(f"   ✅ User does not exist - will create new user")
            create_new_user = True
        
        # Step 3: Create new user (if needed)
        if create_new_user:
            print(f"\n3. Creating new system administrator user...")
            
            user_id = str(uuid.uuid4())
            # Hash password using bcrypt directly
            hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            current_time = datetime.now(timezone.utc)
            
            db.execute(text("""
                INSERT INTO users (
                    id, email, password_hash, first_name, last_name, 
                    display_name, user_type, status, is_active, 
                    email_verified, mfa_enabled, failed_login_attempts,
                    preferences, timezone, language, extra_data,
                    created_at, updated_at
                ) VALUES (
                    :id, :email, :password_hash, :first_name, :last_name,
                    :display_name, :user_type, :status, :is_active,
                    :email_verified, :mfa_enabled, :failed_login_attempts,
                    :preferences, :timezone, :language, :extra_data,
                    :created_at, :updated_at
                )
            """), {
                'id': user_id,
                'email': email,
                'password_hash': hashed_password,
                'first_name': 'System',
                'last_name': 'Administrator',
                'display_name': 'System Administrator',
                'user_type': 'system_admin',
                'status': 'active',
                'is_active': True,
                'email_verified': True,
                'mfa_enabled': False,
                'failed_login_attempts': 0,
                'preferences': '{}',
                'timezone': 'UTC',
                'language': 'en',
                'extra_data': '{}',
                'created_at': current_time,
                'updated_at': current_time
            })
            
            print(f"   ✅ User created successfully: {email}")
            print(f"   → User ID: {user_id}")
        
        # Step 4: Assign system admin role
        print(f"\n4. Assigning System Administrator role...")
        
        # Check if role assignment already exists
        existing_assignment = db.execute(text("""
            SELECT id FROM user_organization_roles 
            WHERE user_id = :user_id 
            AND organization_id = :org_id 
            AND role_id = :role_id
        """), {
            'user_id': user_id,
            'org_id': system_admin_role.organization_id,
            'role_id': system_admin_role.id
        }).fetchone()
        
        if existing_assignment:
            print(f"   ✅ Role assignment already exists")
        else:
            role_assignment_id = str(uuid.uuid4())
            current_time = datetime.now(timezone.utc)
            
            db.execute(text("""
                INSERT INTO user_organization_roles (
                    id, user_id, organization_id, role_id, 
                    is_primary, is_active, status,
                    created_at, updated_at
                ) VALUES (
                    :id, :user_id, :organization_id, :role_id,
                    :is_primary, :is_active, :status,
                    :created_at, :updated_at
                )
            """), {
                'id': role_assignment_id,
                'user_id': user_id,
                'organization_id': system_admin_role.organization_id,
                'role_id': system_admin_role.id,
                'is_primary': True,  # Make this the primary role
                'is_active': True,
                'status': 'active',
                'created_at': current_time,
                'updated_at': current_time
            })
            
            print(f"   ✅ System Administrator role assigned successfully")
        
        # Step 5: Verify permissions
        print(f"\n5. Verifying system admin permissions...")
        
        permissions = db.execute(text("""
            SELECT p.code, p.name 
            FROM permissions p
            JOIN role_permissions rp ON p.id = rp.permission_id
            JOIN user_organization_roles uor ON rp.role_id = uor.role_id
            WHERE uor.user_id = :user_id 
            AND uor.organization_id = :org_id
            AND p.code LIKE 'system_admin%'
            ORDER BY p.code
        """), {
            'user_id': user_id,
            'org_id': system_admin_role.organization_id
        }).fetchall()
        
        print(f"   🔐 Assigned Permissions ({len(permissions)}):")
        for perm in permissions:
            print(f"      → {perm.code}: {perm.name}")
            
        # Check specifically for system_admin.master
        master_perm = next((p for p in permissions if p.code == 'system_admin.master'), None)
        if master_perm:
            print(f"   ✅ system_admin.master permission verified!")
        else:
            print(f"   ❌ system_admin.master permission NOT found!")
        
        # Commit all changes
        db.commit()
        
        print(f"\n✅ System Administrator user created successfully!")
        print(f"\n🔑 LOGIN CREDENTIALS:")
        print(f"   Username/Email: {email}")
        print(f"   Password: {password}")
        print(f"   User ID: {user_id}")
        print(f"   Organization: {system_admin_role.org_name}")
        print(f"   Role: System Administrator (system_admin.master)")
        
        return {
            'username': username,
            'email': email,
            'password': password,
            'user_id': user_id,
            'organization_id': system_admin_role.organization_id,
            'organization_name': system_admin_role.org_name,
            'role': 'System Administrator',
            'permissions': [p.code for p in permissions],
            'status': 'created' if create_new_user else 'role_assigned'
        }
        
    except Exception as e:
        print(f"\n❌ Error creating system admin user: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    result = create_system_admin_user()
    if result:
        print(f"\n💡 Save these credentials safely - the password cannot be recovered!")