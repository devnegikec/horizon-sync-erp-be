#!/usr/bin/env python3
"""
Test the system_admin.master constraint
"""

import os
import uuid
import bcrypt
from datetime import datetime, timezone
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

IDENTITY_DATABASE_URL = os.getenv(
    "IDENTITY_DATABASE_URL", 
    "postgresql://horizon_user:horizon_pass@localhost:5432/identity_db"
)

def test_constraint():
    print("🧪 TESTING SYSTEM_ADMIN.MASTER CONSTRAINT")
    print("=" * 50)
    print("This should FAIL due to constraint violation...")
    
    identity_engine = create_engine(IDENTITY_DATABASE_URL)
    IdentitySession = sessionmaker(bind=identity_engine)
    db = IdentitySession()
    
    try:
        # Get the system admin role (which has master permission)
        system_admin_role = db.execute(text("""
            SELECT r.id, r.organization_id, r.name
            FROM roles r
            WHERE r.code = 'system_admin'
        """)).fetchone()
        
        if not system_admin_role:
            print("❌ System admin role not found")
            return
        
        print(f"1. Found system admin role: {system_admin_role.name}")
        
        # Create a test user
        test_user_id = str(uuid.uuid4())
        current_time = datetime.now(timezone.utc)
        
        print("2. Creating test user...")
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
            'id': test_user_id,
            'email': 'constraint_test@horizonsync.com',
            'password_hash': bcrypt.hashpw('test123'.encode('utf-8'), bcrypt.gensalt()).decode('utf-8'),
            'first_name': 'Constraint',
            'last_name': 'Test',
            'display_name': 'Constraint Test User',
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
        
        print("   ✅ Test user created")
        
        # Try to assign system admin role (this should fail due to constraint)
        print("3. Attempting to assign system admin role (should FAIL)...")
        
        assignment_id = str(uuid.uuid4())
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
            'user_id': test_user_id,
            'organization_id': system_admin_role.organization_id,
            'role_id': system_admin_role.id,
            'is_primary': True,
            'is_active': True,
            'status': 'active',
            'created_at': current_time,
            'updated_at': current_time
        })
        
        db.commit()
        print("   ❌ CONSTRAINT FAILED - Role assignment succeeded when it should have failed!")
        
        # Clean up the test user
        db.execute(text("DELETE FROM user_organization_roles WHERE user_id = :user_id"), {'user_id': test_user_id})
        db.execute(text("DELETE FROM users WHERE id = :user_id"), {'user_id': test_user_id})
        db.commit()
        
    except Exception as e:
        print(f"   ✅ CONSTRAINT WORKING - Role assignment failed as expected: {str(e)[:100]}...")
        db.rollback()
        
        # Clean up test user if it was created
        try:
            db.execute(text("DELETE FROM users WHERE email = 'constraint_test@horizonsync.com'"))
            db.commit()
        except:
            pass
    finally:
        db.close()

if __name__ == "__main__":
    test_constraint()