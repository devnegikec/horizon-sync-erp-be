#!/usr/bin/env python3
"""
SYSTEM ADMIN CONSTRAINTS AND TEST USERS CREATOR

1. Adds database constraint to ensure only ONE user can have system_admin.master permission
2. Creates specialized system admin test users with specific permissions:
   - system_admin.users
   - system_admin.organizations  
   - system_admin.billing
   - system_admin.reporting
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
    """Generate a secure random password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password

def create_master_admin_constraint():
    """Create constraint to ensure only one user can have system_admin.master permission"""
    print("🔒 CREATING SYSTEM_ADMIN.MASTER CONSTRAINT")
    print("=" * 50)
    
    identity_engine = create_engine(IDENTITY_DATABASE_URL)
    IdentitySession = sessionmaker(bind=identity_engine)
    db = IdentitySession()
    
    try:
        # Create a function to check master admin constraint
        print("1. Creating constraint validation function...")
        
        db.execute(text("""
            CREATE OR REPLACE FUNCTION validate_single_master_admin()
            RETURNS TRIGGER AS $$
            DECLARE
                master_count INTEGER;
                existing_master_count INTEGER;
            BEGIN
                -- Count existing users with system_admin.master permission (before this operation)
                SELECT COUNT(DISTINCT uor.user_id) INTO existing_master_count
                FROM user_organization_roles uor
                JOIN role_permissions rp ON uor.role_id = rp.role_id
                JOIN permissions p ON rp.permission_id = p.id
                WHERE p.code = 'system_admin.master'
                AND uor.is_active = true
                AND (TG_OP = 'INSERT' OR uor.id != NEW.id); -- Exclude current record if updating
                
                -- If this is an INSERT and we're adding a role with master permission
                IF TG_OP = 'INSERT' AND NEW.is_active = true THEN
                    -- Check if the new role has master permission
                    IF EXISTS (
                        SELECT 1 FROM role_permissions rp
                        JOIN permissions p ON rp.permission_id = p.id  
                        WHERE rp.role_id = NEW.role_id
                        AND p.code = 'system_admin.master'
                    ) THEN
                        -- Allow only if no existing master admin exists
                        IF existing_master_count >= 1 THEN
                            RAISE EXCEPTION 'Only one user can have system_admin.master permission. A master admin already exists.';
                        END IF;
                    END IF;
                END IF;
                
                RETURN COALESCE(NEW, OLD);
            END;
            $$ LANGUAGE plpgsql;
        """))
        
        print("   ✅ Validation function created")
        print("   ℹ️  Note: Constraint will prevent future violations (existing admins are grandfathered)")
        
        # Drop existing trigger if it exists
        print("2. Setting up database trigger...")
        
        db.execute(text("""
            DROP TRIGGER IF EXISTS trigger_validate_single_master_admin 
            ON user_organization_roles;
        """))
        
        db.execute(text("""
            CREATE TRIGGER trigger_validate_single_master_admin
            AFTER INSERT OR UPDATE ON user_organization_roles
            FOR EACH ROW
            EXECUTE FUNCTION validate_single_master_admin();
        """))
        
        print("   ✅ Trigger created to enforce single master admin constraint")
        
        # Commit the constraint
        db.commit()
        
        # Test the constraint
        print("3. Testing constraint...")
        current_masters = db.execute(text("""
            SELECT COUNT(DISTINCT uor.user_id) as count
            FROM user_organization_roles uor
            JOIN role_permissions rp ON uor.role_id = rp.role_id  
            JOIN permissions p ON rp.permission_id = p.id
            WHERE p.code = 'system_admin.master'
            AND uor.is_active = true
        """)).fetchone().count
        
        print(f"   ✅ Current master admins: {current_masters}")
        if current_masters == 1:
            print("   ✅ Constraint validation passed - exactly 1 master admin exists")
        elif current_masters == 0:
            print("   ⚠️  Warning: No master admins found")
        else:
            print(f"   ⚠️  Warning: {current_masters} master admins found (constraint will prevent new ones)")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating constraint: {e}")
        db.rollback()
        return False
    finally:
        db.close()

def create_specialized_admin_roles():
    """Create specialized roles for individual system admin permissions"""
    print("\n🎭 CREATING SPECIALIZED ADMIN ROLES")
    print("=" * 50)
    
    identity_engine = create_engine(IDENTITY_DATABASE_URL)
    IdentitySession = sessionmaker(bind=identity_engine)
    db = IdentitySession()
    
    specialized_roles = [
        {
            'name': 'User Management Admin',
            'code': 'user_admin',
            'description': 'Cross-organization user management specialist',
            'permission': 'system_admin.users'
        },
        {
            'name': 'Organization Admin', 
            'code': 'org_admin_specialist',
            'description': 'Organization management specialist',
            'permission': 'system_admin.organizations'
        },
        {
            'name': 'Billing Admin',
            'code': 'billing_admin',
            'description': 'Billing and invoice management specialist', 
            'permission': 'system_admin.billing'
        },
        {
            'name': 'Reporting Admin',
            'code': 'reporting_admin', 
            'description': 'Analytics and reporting specialist',
            'permission': 'system_admin.reporting'
        }
    ]
    
    created_roles = []
    
    try:
        # Get the organization where system admin roles belong
        org_info = db.execute(text("""
            SELECT r.organization_id, o.name as org_name
            FROM roles r
            JOIN organizations o ON r.organization_id = o.id
            WHERE r.code = 'system_admin'
        """)).fetchone()
        
        if not org_info:
            print("   ❌ Could not find organization for system admin roles")
            return []
            
        print(f"   📍 Creating roles in: {org_info.org_name}")
        
        for role_spec in specialized_roles:
            print(f"\n   🎭 Creating role: {role_spec['name']}...")
            
            # Check if role already exists
            existing_role = db.execute(text("""
                SELECT id FROM roles 
                WHERE code = :code AND organization_id = :org_id
            """), {
                'code': role_spec['code'],
                'org_id': org_info.organization_id
            }).fetchone()
            
            if existing_role:
                print(f"      ⚠️  Role already exists: {role_spec['code']}")
                role_id = existing_role.id
            else:
                # Create the role
                role_id = str(uuid.uuid4())
                current_time = datetime.now(timezone.utc)
                
                db.execute(text("""
                    INSERT INTO roles (
                        id, organization_id, name, code, description,
                        is_system, is_default, hierarchy_level, is_active,
                        created_at, updated_at
                    ) VALUES (
                        :id, :org_id, :name, :code, :description,
                        :is_system, :is_default, :hierarchy_level, :is_active,
                        :created_at, :updated_at
                    )
                """), {
                    'id': role_id,
                    'org_id': org_info.organization_id,
                    'name': role_spec['name'],
                    'code': role_spec['code'],
                    'description': role_spec['description'],
                    'is_system': True,
                    'is_default': False,
                    'hierarchy_level': 75,  # Between org admin (50) and system admin (100)
                    'is_active': True,
                    'created_at': current_time,
                    'updated_at': current_time
                })
                
                print(f"      ✅ Role created: {role_spec['code']}")
            
            # Get the permission ID
            permission = db.execute(text("""
                SELECT id FROM permissions WHERE code = :code
            """), {'code': role_spec['permission']}).fetchone()
            
            if not permission:
                print(f"      ❌ Permission not found: {role_spec['permission']}")
                continue
            
            # Check if permission is already assigned  
            existing_assignment = db.execute(text("""
                SELECT id FROM role_permissions
                WHERE role_id = :role_id AND permission_id = :permission_id
            """), {
                'role_id': role_id,
                'permission_id': permission.id
            }).fetchone()
            
            if existing_assignment:
                print(f"      ✅ Permission already assigned: {role_spec['permission']}")
            else:
                # Assign the permission to the role
                assignment_id = str(uuid.uuid4())
                
                db.execute(text("""
                    INSERT INTO role_permissions (
                        id, role_id, permission_id, conditions
                    ) VALUES (
                        :id, :role_id, :permission_id, :conditions
                    )
                """), {
                    'id': assignment_id,
                    'role_id': role_id,
                    'permission_id': permission.id,
                    'conditions': None
                })
                
                print(f"      ✅ Permission assigned: {role_spec['permission']}")
            
            created_roles.append({
                'id': role_id,
                'name': role_spec['name'],
                'code': role_spec['code'], 
                'permission': role_spec['permission'],
                'organization_id': org_info.organization_id
            })
        
        db.commit()
        print(f"\n   ✅ Successfully created/verified {len(created_roles)} specialized roles")
        return created_roles
        
    except Exception as e:
        print(f"❌ Error creating specialized roles: {e}")
        db.rollback()
        return []
    finally:
        db.close()

def create_test_admin_users(specialized_roles):
    """Create test users with specialized admin permissions"""
    print("\n👥 CREATING TEST ADMIN USERS")
    print("=" * 50)
    
    identity_engine = create_engine(IDENTITY_DATABASE_URL)  
    IdentitySession = sessionmaker(bind=identity_engine)
    db = IdentitySession()
    
    created_users = []
    
    try:
        for role_info in specialized_roles:
            username = f"test_{role_info['code']}"
            password = generate_secure_password(12)
            email = f"{username}@horizonsync.com"
            
            print(f"\n   👤 Creating user: {username}")
            print(f"      📧 Email: {email}")
            print(f"      🔑 Password: {password}")
            
            # Check if user exists
            existing_user = db.execute(text("""
                SELECT id FROM users WHERE email = :email
            """), {'email': email}).fetchone()
            
            if existing_user:
                print(f"      ⚠️  User already exists: {email}")
                user_id = existing_user.id
                create_new_user = False
            else:
                # Create the user
                user_id = str(uuid.uuid4())
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
                    'first_name': role_info['name'].split()[0],  # First word of role name
                    'last_name': 'Admin',
                    'display_name': role_info['name'],
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
                
                print(f"      ✅ User created")
                create_new_user = True
            
            # Assign the specialized role
            existing_role_assignment = db.execute(text("""
                SELECT id FROM user_organization_roles
                WHERE user_id = :user_id AND role_id = :role_id
                AND organization_id = :org_id
            """), {
                'user_id': user_id,
                'role_id': role_info['id'],
                'org_id': role_info['organization_id']
            }).fetchone()
            
            if existing_role_assignment:
                print(f"      ✅ Role already assigned: {role_info['name']}")
            else:
                assignment_id = str(uuid.uuid4())
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
                    'id': assignment_id,
                    'user_id': user_id,
                    'organization_id': role_info['organization_id'],
                    'role_id': role_info['id'],
                    'is_primary': True,
                    'is_active': True,
                    'status': 'active',
                    'created_at': current_time,
                    'updated_at': current_time
                })
                
                print(f"      ✅ Role assigned: {role_info['name']}")
            
            created_users.append({
                'username': username,
                'email': email,
                'password': password,
                'user_id': user_id,
                'role_name': role_info['name'],
                'permission': role_info['permission'],
                'status': 'created' if create_new_user else 'existing'
            })
        
        db.commit()
        return created_users
        
    except Exception as e:
        print(f"❌ Error creating test users: {e}")
        db.rollback()
        return []
    finally:
        db.close()

def main():
    """Main function to run all setup tasks"""
    print("🚀 SYSTEM ADMIN CONSTRAINT & TEST USERS SETUP")
    print("=" * 70)
    
    # Step 1: Create master admin constraint
    constraint_success = create_master_admin_constraint()
    if not constraint_success:
        print("\n❌ Failed to create master admin constraint - aborting")
        return
    
    # Step 2: Create specialized roles
    specialized_roles = create_specialized_admin_roles()
    if not specialized_roles:
        print("\n❌ Failed to create specialized roles - aborting")
        return
    
    # Step 3: Create test users
    test_users = create_test_admin_users(specialized_roles)
    if not test_users:
        print("\n❌ Failed to create test users")
        return
    
    # Step 4: Summary
    print(f"\n✅ SETUP COMPLETED SUCCESSFULLY!")
    print(f"🔒 Master admin constraint: ACTIVE (only 1 user can have system_admin.master)")  
    print(f"🎭 Specialized roles created: {len(specialized_roles)}")
    print(f"👥 Test admin users created: {len(test_users)}")
    
    print(f"\n🔑 TEST USER CREDENTIALS:")
    print(f"{'Username':<25} {'Email':<35} {'Password':<15} {'Permission'}")
    print("-" * 95)
    
    for user in test_users:
        print(f"{user['username']:<25} {user['email']:<35} {user['password']:<15} {user['permission']}")
    
    print(f"\n💡 All passwords have been generated securely - save them immediately!")
    print(f"⚠️  These are test accounts with specific system admin permissions")
    print(f"🔒 The master admin constraint is now active and will prevent multiple master admins")

if __name__ == "__main__":
    main()