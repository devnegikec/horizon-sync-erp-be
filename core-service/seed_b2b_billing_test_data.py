#!/usr/bin/env python3
"""
Seed test data for B2B billing system validation.

Creates:
1. Master organization (if not exists)
2. Multiple customer organizations linked to master
3. Sample subscription invoices for customer organizations
4. System admin users in master organization
"""

import os
import sys
import uuid
from datetime import datetime, timedelta
from decimal import Decimal

# Add app to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database connection settings - adjust as needed
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/horizon_sync_core")
IDENTITY_DB_URL = os.getenv("IDENTITY_DATABASE_URL", "postgresql://postgres:password@localhost:5433/horizon_sync_identity")

# Test data configuration
MASTER_ORG_DATA = {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Master Billing Organization",
    "slug": "master-billing-org",
    "display_name": "Master Billing Org",
    "organization_type": "master",
    "status": "active"
}

CUSTOMER_ORGANIZATIONS = [
    {
        "id": "550e8400-e29b-41d4-a716-446655440011",
        "name": "Acme Corp",
        "slug": "acme-corp",
        "display_name": "Acme Corporation",
        "parent_organization_id": "550e8400-e29b-41d4-a716-446655440001"
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440012", 
        "name": "TechStart Inc",
        "slug": "techstart-inc",
        "display_name": "TechStart Incorporated",
        "parent_organization_id": "550e8400-e29b-41d4-a716-446655440001"
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440013",
        "name": "Global Solutions",
        "slug": "global-solutions",
        "display_name": "Global Solutions Ltd",
        "parent_organization_id": "550e8400-e29b-41d4-a716-446655440001"
    }
]

SYSTEM_ADMIN_USER = {
    "id": "550e8400-e29b-41d4-a716-446655440099",
    "email": "admin@master-billing-org.com",
    "first_name": "System",
    "last_name": "Administrator",
    "organization_id": "550e8400-e29b-41d4-a716-446655440001"
}


def seed_identity_data():
    """Seed organizations and users in identity database."""
    print("🔑 Seeding identity service data...")
    
    identity_engine = create_engine(IDENTITY_DB_URL)
    IdentitySession = sessionmaker(autocommit=False, autoflush=False, bind=identity_engine)
    identity_db = IdentitySession()
    
    try:
        # Check if master org already exists
        existing_master = identity_db.execute(
            text("SELECT id FROM organizations WHERE organization_type = 'master' LIMIT 1")
        ).fetchone()
        
        if not existing_master:
            # Create master organization
            identity_db.execute(text("""
                INSERT INTO organizations (
                    id, name, slug, display_name, organization_type, 
                    status, billing_status, seat_limit, credit_limit,
                    created_at, updated_at
                ) VALUES (:id, :name, :slug, :display_name, :org_type, :status, :billing_status, :seat_limit, :credit_limit, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """), {
                'id': MASTER_ORG_DATA["id"],
                'name': MASTER_ORG_DATA["name"],
                'slug': MASTER_ORG_DATA["slug"], 
                'display_name': MASTER_ORG_DATA["display_name"],
                'org_type': MASTER_ORG_DATA["organization_type"],
                'status': MASTER_ORG_DATA["status"],
                'billing_status': "active",
                'seat_limit': 100,
                'credit_limit': 10000.00,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            print(f"✅ Created master organization: {MASTER_ORG_DATA['name']}")
        else:
            print(f"✅ Master organization already exists: {existing_master['id']}")
            
        # Create customer organizations
        for org in CUSTOMER_ORGANIZATIONS:
            identity_db.execute(text("""
                INSERT INTO organizations (
                    id, name, slug, display_name, organization_type,
                    status, billing_status, parent_organization_id,
                    seat_limit, credit_limit, subscription_start_date,
                    created_at, updated_at
                ) VALUES (:id, :name, :slug, :display_name, :org_type, :status, :billing_status, :parent_id, :seat_limit, :credit_limit, :sub_start, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """), {
                'id': org["id"],
                'name': org["name"],
                'slug': org["slug"],
                'display_name': org["display_name"], 
                'org_type': "customer",
                'status': "active",
                'billing_status': "active",
                'parent_id': org["parent_organization_id"],
                'seat_limit': 25,
                'credit_limit': 5000.00,
                'sub_start': datetime.now() - timedelta(days=30),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            print(f"✅ Created customer organization: {org['name']}")
            
        # Create system admin user
        identity_db.execute(text("""
            INSERT INTO users (
                id, email, first_name, last_name, user_type,
                is_active, created_at, updated_at
            ) VALUES (:id, :email, :first_name, :last_name, :user_type, :is_active, :created_at, :updated_at)
            ON CONFLICT (id) DO NOTHING
        """), {
            'id': SYSTEM_ADMIN_USER["id"],
            'email': SYSTEM_ADMIN_USER["email"],
            'first_name': SYSTEM_ADMIN_USER["first_name"],
            'last_name': SYSTEM_ADMIN_USER["last_name"], 
            'user_type': "SYSTEM_ADMIN",
            'is_active': True,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        print(f"✅ Created system admin user: {SYSTEM_ADMIN_USER['email']}")
        
        identity_db.commit()
        
    except Exception as e:
        print(f"❌ Error seeding identity data: {e}")
        identity_db.rollback()
        raise
    finally:
        identity_db.close()


def seed_invoice_data():
    """Seed subscription invoices in core database."""
    print("🧾 Seeding subscription invoices...")
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        billing_cycles = ['monthly', 'quarterly', 'yearly']
        
        for i, org in enumerate(CUSTOMER_ORGANIZATIONS):
            org_id = org["id"]
            cycle = billing_cycles[i % len(billing_cycles)]
            
            # Create subscription invoice manually
            invoice_id = str(uuid.uuid4())
            invoice_no = f"SUB-{datetime.now().strftime('%Y%m')}-{str(uuid.uuid4())[:8]}"
            
            seat_count = 10 + (i * 5)
            base_amount = Decimal(str(seat_count * 15.00))  # $15 per seat
            credit_usage = Decimal(str(50.00 + (i * 25.00)))
            credit_amount = credit_usage * Decimal("0.02")  # $0.02 per credit
            grand_total = base_amount + credit_amount
            
            db.execute(text("""
                INSERT INTO invoices (
                    id, organization_id, invoice_no, invoice_type, 
                    status, posting_date, due_date, grand_total,
                    billing_cycle, subscription_period_start, subscription_period_end,
                    seat_count, credit_usage, created_at, updated_at
                ) VALUES (:id, :org_id, :invoice_no, :invoice_type, :status, :posting_date, :due_date, 
                         :grand_total, :billing_cycle, :period_start, :period_end, :seat_count, :credit_usage, 
                         :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """), {
                'id': invoice_id,
                'org_id': org_id,
                'invoice_no': invoice_no,
                'invoice_type': 'subscription',
                'status': 'draft',
                'posting_date': datetime.now(),
                'due_date': datetime.now() + timedelta(days=30),
                'grand_total': float(grand_total),
                'billing_cycle': cycle,
                'period_start': datetime.now() - timedelta(days=30),
                'period_end': datetime.now(),
                'seat_count': seat_count,
                'credit_usage': float(credit_usage),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            
            print(f"✅ Created {cycle} subscription invoice for {org['name']}: {invoice_no}")
            
            # Create an overdue invoice for first organization
            if i == 0:
                overdue_id = str(uuid.uuid4())
                overdue_no = f"SUB-{datetime.now().strftime('%Y%m')}-{str(uuid.uuid4())[:8]}"
                
                db.execute(text("""
                    INSERT INTO invoices (
                        id, organization_id, invoice_no, invoice_type, 
                        status, posting_date, due_date, grand_total,
                        billing_cycle, subscription_period_start, subscription_period_end,
                        seat_count, credit_usage, created_at, updated_at
                    ) VALUES (:id, :org_id, :invoice_no, :invoice_type, :status, :posting_date, :due_date, 
                             :grand_total, :billing_cycle, :period_start, :period_end, :seat_count, :credit_usage,
                             :created_at, :updated_at)
                    ON CONFLICT (id) DO NOTHING
                """), {
                    'id': overdue_id,
                    'org_id': org_id,
                    'invoice_no': overdue_no,
                    'invoice_type': 'subscription',
                    'status': 'sent',
                    'posting_date': datetime.now() - timedelta(days=60),
                    'due_date': datetime.now() - timedelta(days=15),  # Overdue
                    'grand_total': 200.00,
                    'billing_cycle': 'monthly',
                    'period_start': datetime.now() - timedelta(days=90),
                    'period_end': datetime.now() - timedelta(days=60),
                    'seat_count': 10,
                    'credit_usage': 25.00,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
                
                print(f"✅ Created overdue invoice for {org['name']}: {overdue_no}")
                
        db.commit()
        
    except Exception as e:
        print(f"❌ Error seeding invoice data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def validate_implementation():
    """Validate that the B2B billing implementation works correctly."""
    print("🔍 Validating B2B billing implementation...")
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check that invoices exist for customer organizations
        result = db.execute(text("""
            SELECT 
                i.organization_id,
                i.invoice_no,
                i.billing_cycle,
                i.seat_count,
                i.grand_total,
                i.status
            FROM invoices i 
            WHERE i.organization_id IN (
                '550e8400-e29b-41d4-a716-446655440011',
                '550e8400-e29b-41d4-a716-446655440012', 
                '550e8400-e29b-41d4-a716-446655440013'
            )
            ORDER BY i.created_at DESC
        """))
        
        invoices = result.fetchall()
        print(f"✅ Found {len(invoices)} subscription invoices for customer organizations")
        
        for invoice in invoices:
            print(f"  - {invoice.invoice_no}: {invoice.billing_cycle} | {invoice.seat_count} seats | ${invoice.grand_total}")
            
        # Check overdue invoices
        overdue_result = db.execute(text("""
            SELECT COUNT(*) as count
            FROM invoices i 
            WHERE i.due_date < NOW() AND i.status != 'paid'
        """))
        
        overdue_count = overdue_result.scalar()
        print(f"✅ Found {overdue_count} overdue invoices")
        
    except Exception as e:
        print(f"❌ Error validating implementation: {e}")
        raise
    finally:
        db.close()


def main():
    """Main seeding function."""
    print("🚀 Starting B2B billing test data seeding...")
    
    try:
        seed_identity_data()
        seed_invoice_data() 
        validate_implementation()
        
        print("\n🎉 B2B billing test data seeded successfully!")
        print("\n📋 Test Data Summary:")
        print(f"  • Master Organization: {MASTER_ORG_DATA['name']}")
        print(f"  • Customer Organizations: {len(CUSTOMER_ORGANIZATIONS)}")
        print(f"  • System Admin User: {SYSTEM_ADMIN_USER['email']}")
        print(f"  • Subscription Invoices: {len(CUSTOMER_ORGANIZATIONS) + 1}")
        
        print("\n🔗 Organization Relationships:")
        for org in CUSTOMER_ORGANIZATIONS:
            print(f"  • {org['name']} → linked to Master Organization")
            
        print("\n🧪 To test system admin functionality:")
        print("  1. Login with system admin credentials")  
        print("  2. Navigate to Admin Portal → Invoices")
        print("  3. Verify only master organization invoices are displayed")
        print("  4. Check filtering and organization relationships work correctly")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        return 1
        
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code if exit_code else 0)