#!/usr/bin/env python3
"""
Comprehensive B2B Test Data Seed Script

Creates complete test data for B2B billing system testing including:
1. Master organization and customer organizations (B2B hierarchy)
2. System admin users and billing contacts
3. Chart of accounts and bank accounts
4. Sample invoices with realistic scenarios
5. Payment reminder configurations
6. Payment entries and allocations
7. Test customers and suppliers

Usage:
    python seed_b2b_comprehensive_test_data.py

Environment Variables:
    DATABASE_URL: Core service database URL
    IDENTITY_DATABASE_URL: Identity service database URL
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

# Database connection settings
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db")
IDENTITY_DATABASE_URL = os.getenv("IDENTITY_DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/identity_db")

# Test Organization Hierarchy Configuration
MASTER_ORG_DATA = {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "HorizonSync Master Billing",
    "slug": "horizon-master-billing",
    "display_name": "HorizonSync Master Billing Organization",
    "organization_type": "enterprise",
    "status": "active",
    "email": "billing@horizonsync.com",
    "website": "https://horizonsync.com",
    "city": "San Francisco",
    "state": "CA", 
    "country": "USA"
}

CUSTOMER_ORGANIZATIONS = [
    {
        "id": "550e8400-e29b-41d4-a716-446655440011",
        "name": "Acme Corporation",
        "slug": "acme-corp",
        "display_name": "Acme Corp",
        "industry": "Manufacturing",
        "subscription_tier": "enterprise",
        "monthly_fee": Decimal("299.99"),
        "seat_count": 25,
        "parent_organization_id": "550e8400-e29b-41d4-a716-446655440001"
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440012", 
        "name": "TechStart Innovations",
        "slug": "techstart-innovations",
        "display_name": "TechStart Inc",
        "industry": "Technology",
        "subscription_tier": "pro",
        "monthly_fee": Decimal("149.99"),
        "seat_count": 15,
        "parent_organization_id": "550e8400-e29b-41d4-a716-446655440001"
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440013",
        "name": "Global Solutions Ltd",
        "slug": "global-solutions",
        "display_name": "Global Solutions",
        "industry": "Consulting",
        "subscription_tier": "basic",
        "monthly_fee": Decimal("99.99"),
        "seat_count": 10,
        "parent_organization_id": "550e8400-e29b-41d4-a716-446655440001"
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440014",
        "name": "StartupCo",
        "slug": "startup-co",
        "display_name": "StartupCo",
        "industry": "FinTech",
        "subscription_tier": "pro",
        "monthly_fee": Decimal("149.99"),
        "seat_count": 8,
        "parent_organization_id": "550e8400-e29b-41d4-a716-446655440001"
    }
]

# Test Users
SYSTEM_ADMIN_USER = {
    "id": "550e8400-e29b-41d4-a716-446655440099",
    "email": "admin@horizonsync.com",
    "first_name": "System",
    "last_name": "Administrator",
    "user_type": "system_admin",
    "organization_id": "550e8400-e29b-41d4-a716-446655440001"
}

BILLING_CONTACTS = [
    {
        "id": "550e8400-e29b-41d4-a716-446655440101",
        "email": "billing@acmecorp.com",
        "first_name": "Jane", 
        "last_name": "Smith",
        "organization_id": "550e8400-e29b-41d4-a716-446655440011"
    },
    {
        "id": "550e8400-e29b-41d4-a716-446655440102",
        "email": "finance@techstart.com",
        "first_name": "Mike",
        "last_name": "Johnson", 
        "organization_id": "550e8400-e29b-41d4-a716-446655440012"
    }
]


def seed_identity_service():
    """Seed organizations and users in identity service"""
    print("\n🔑 SEEDING IDENTITY SERVICE DATA")
    print("=" * 50)
    
    identity_engine = create_engine(IDENTITY_DATABASE_URL)
    IdentitySession = sessionmaker(bind=identity_engine)
    db = IdentitySession()
    
    try:
        # Create master organization
        print("\n1. Creating Master Organization...")
        db.execute(text("""
            INSERT INTO organizations (
                id, name, slug, display_name, organization_type, status, is_active,
                email, website, city, state, country, billing_status,
                max_users, max_credits, created_at, updated_at
            ) VALUES (
                :id, :name, :slug, :display_name, :org_type, :status, true,
                :email, :website, :city, :state, :country, 'active',
                1000, 100000, :created_at, :updated_at
            ) ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                updated_at = EXCLUDED.updated_at
        """), {
            **MASTER_ORG_DATA,
            'org_type': MASTER_ORG_DATA["organization_type"],
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        print(f"✓ Created master organization: {MASTER_ORG_DATA['name']}")
        
        # Create customer organizations
        print("\n2. Creating Customer Organizations...")
        for i, org in enumerate(CUSTOMER_ORGANIZATIONS):
            subscription_start = datetime.now() - timedelta(days=30 * (i + 1))
            next_billing = datetime.now() + timedelta(days=30 - (i * 10))
            
            db.execute(text("""
                INSERT INTO organizations (
                    id, name, slug, display_name, organization_type, status, is_active,
                    industry, billing_status, parent_organization_id,
                    subscription_start_date, next_billing_date, max_users, max_credits,
                    billing_cycle, customer_since, created_at, updated_at
                ) VALUES (
                    :id, :name, :slug, :display_name, 'business', 'active', true,
                    :industry, 'active', :parent_organization_id,
                    :subscription_start, :next_billing, :seat_count, :max_credits,
                    'monthly', :customer_since, :created_at, :updated_at
                ) ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    updated_at = EXCLUDED.updated_at
            """), {
                'id': org["id"],
                'name': org["name"],
                'slug': org["slug"],
                'display_name': org["display_name"],
                'industry': org["industry"],
                'parent_organization_id': org["parent_organization_id"],
                'subscription_start': subscription_start,
                'next_billing': next_billing,
                'seat_count': org["seat_count"],
                'max_credits': org["seat_count"] * 100,  # 100 credits per seat
                'customer_since': subscription_start,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            print(f"✓ Created customer org: {org['name']} ({org['subscription_tier']}) - {org['seat_count']} seats")
        
        # Create system admin user
        print("\n3. Creating System Admin User...")
        db.execute(text("""
            INSERT INTO users (
                id, email, first_name, last_name, user_type, is_active,
                password_hash, created_at, updated_at, status
            ) VALUES (
                :id, :email, :first_name, :last_name, :user_type, true,
                '$2b$12$dummy.hash.for.testing', :created_at, :updated_at, 'active'
            ) ON CONFLICT (id) DO UPDATE SET
                email = EXCLUDED.email,
                updated_at = EXCLUDED.updated_at
        """), {
            **SYSTEM_ADMIN_USER,
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        })
        print(f"✓ Created system admin: {SYSTEM_ADMIN_USER['email']}")
        
        # Create billing contact users
        print("\n4. Creating Billing Contact Users...")
        for contact in BILLING_CONTACTS:
            db.execute(text("""
                INSERT INTO users (
                    id, email, first_name, last_name, user_type, is_active,
                    password_hash, created_at, updated_at, status
                ) VALUES (
                    :id, :email, :first_name, :last_name, 'user', true,
                    '$2b$12$dummy.hash.for.testing', :created_at, :updated_at, 'active'
                ) ON CONFLICT (id) DO UPDATE SET
                    email = EXCLUDED.email,
                    updated_at = EXCLUDED.updated_at
            """), {
                **contact,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
            print(f"✓ Created billing contact: {contact['email']}")
        
        db.commit()
        print("\n✅ Identity service data seeding completed!")
        
    except Exception as e:
        print(f"❌ Error seeding identity data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def seed_core_service():
    """Seed core service test data"""
    print("\n🏢 SEEDING CORE SERVICE DATA")
    print("=" * 50)
    
    core_engine = create_engine(DATABASE_URL)
    CoreSession = sessionmaker(bind=core_engine)
    db = CoreSession()
    
    try:
        # Get organization IDs
        master_org_id = MASTER_ORG_DATA["id"]
        admin_user_id = SYSTEM_ADMIN_USER["id"]
        
        # 1. Create Chart of Accounts basics
        print("\n1. Creating Essential Chart of Accounts...")
        essential_accounts = [
            {"code": "1110", "name": "Cash and Bank", "type": "asset"},
            {"code": "1120", "name": "Accounts Receivable", "type": "asset"},
            {"code": "2110", "name": "Accounts Payable", "type": "liability"},
            {"code": "4110", "name": "Subscription Revenue", "type": "revenue"},
            {"code": "4120", "name": "Professional Services Revenue", "type": "revenue"},
            {"code": "5110", "name": "Cost of Goods Sold", "type": "expense"},
        ]
        
        for account in essential_accounts:
            db.execute(text("""
                INSERT INTO accounts (
                    id, organization_id, account_code, account_name, account_type,
                    currency, status, is_posting_account, created_by, updated_by,
                    created_at, updated_at
                ) VALUES (
                    :id, :org_id, :code, :name, :acc_type,
                    'USD', 'ACTIVE', true, :user_id, :user_id,
                    :created_at, :updated_at
                ) ON CONFLICT (organization_id, account_code) DO NOTHING
            """), {
                'id': str(uuid.uuid4()),
                'org_id': master_org_id,
                'code': account["code"],
                'name': account["name"],
                'acc_type': account["type"].upper(),
                'user_id': admin_user_id,
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            })
        print(f"✓ Created {len(essential_accounts)} essential accounts")
        
        # 2. Create Bank Accounts
        print("\n2. Creating Bank Accounts...")
        bank_accounts = [
            {
                "account_name": "HorizonSync Primary Checking",
                "account_number": "123456789",
                "bank_name": "Chase Business Bank",
                "routing_number": "021000021",
                "account_type": "checking",
                "currency": "USD"
            },
            {
                "account_name": "HorizonSync Savings",
                "account_number": "987654321", 
                "bank_name": "Wells Fargo Business",
                "routing_number": "121042882",
                "account_type": "savings",
                "currency": "USD"
            }
        ]
        
        for bank_account in bank_accounts:
            db.execute(text("""
                INSERT INTO bank_accounts (
                    id, organization_id, account_name, account_number, bank_name,
                    routing_number, account_type, currency, is_default,
                    created_by, updated_by, created_at, updated_at
                ) VALUES (
                    :id, :org_id, :account_name, :account_number, :bank_name,
                    :routing_number, :account_type, :currency, :is_default,
                    :user_id, :user_id, :created_at, :updated_at
                ) ON CONFLICT (organization_id, account_number) DO NOTHING
            """), {
                'id': str(uuid.uuid4()),
                'org_id': master_org_id,
                'is_default': bank_account["account_type"] == "checking",
                'user_id': admin_user_id,
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                **bank_account
            })
        print(f"✓ Created {len(bank_accounts)} bank accounts")
        
        # 3. Create Comprehensive Invoices
        print("\n3. Creating B2B Subscription Invoices...")
        invoice_scenarios = []
        
        for i, org in enumerate(CUSTOMER_ORGANIZATIONS):
            # Create 3 months of invoices for each customer
            for month_offset in range(3):
                invoice_date = datetime.now() - timedelta(days=30 * month_offset + 15)
                due_date = invoice_date + timedelta(days=30)
                
                # Calculate invoice details
                base_amount = org["monthly_fee"]
                seat_charges = Decimal(str(org["seat_count"])) * Decimal("10.00")  # $10 per seat
                subtotal = base_amount + seat_charges
                tax = subtotal * Decimal("0.10")  # 10% tax
                total = subtotal + tax
                
                # Determine invoice status and outstanding amount
                if month_offset == 0:  # Current month - unpaid
                    status = "outstanding"
                    outstanding = total
                elif month_offset == 1:  # Last month - partially paid
                    status = "partial_paid" 
                    outstanding = total * Decimal("0.3")  # 30% still owed
                else:  # 2 months ago - fully paid
                    status = "paid"
                    outstanding = Decimal("0")
                
                invoice_id = str(uuid.uuid4())
                invoice_no = f"INV-{org['slug'].upper()}-{invoice_date.strftime('%Y%m')}"
                
                # Insert invoice
                db.execute(text("""
                    INSERT INTO invoices (
                        id, organization_id, invoice_no, invoice_type, party_id,
                        posting_date, due_date, status, grand_total, outstanding_amount,
                        net_total, total_tax, billing_cycle, subscription_period_start,
                        subscription_period_end, seat_count, created_by, updated_by,
                        created_at, updated_at
                    ) VALUES (
                        :id, :org_id, :invoice_no, 'subscription', :party_id,
                        :posting_date, :due_date, :status, :grand_total, :outstanding_amount,
                        :net_total, :total_tax, 'monthly', :period_start, :period_end,
                        :seat_count, :user_id, :user_id, :created_at, :updated_at
                    ) ON CONFLICT (organization_id, invoice_no) DO NOTHING
                """), {
                    'id': invoice_id,
                    'org_id': master_org_id,  # Master org bills all customers
                    'invoice_no': invoice_no,
                    'party_id': org["id"],  # Customer organization
                    'posting_date': invoice_date,
                    'due_date': due_date,
                    'status': status,
                    'grand_total': total,
                    'outstanding_amount': outstanding, 
                    'net_total': subtotal,
                    'total_tax': tax,
                    'period_start': invoice_date.replace(day=1),
                    'period_end': (invoice_date.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1),
                    'seat_count': org["seat_count"],
                    'user_id': admin_user_id,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
                
                # Insert invoice items
                invoice_items = [
                    {
                        "item_name": f"{org['subscription_tier'].title()} Plan Subscription",
                        "qty": 1,
                        "rate": base_amount,
                        "amount": base_amount,
                        "uom": "month"
                    },
                    {
                        "item_name": "Additional User Seats",
                        "qty": org["seat_count"],
                        "rate": Decimal("10.00"),
                        "amount": seat_charges,
                        "uom": "seats"
                    }
                ]
                
                for j, item in enumerate(invoice_items):
                    db.execute(text("""
                        INSERT INTO invoice_items (
                            id, organization_id, invoice_id, item_name, qty, uom,
                            rate, amount, sort_order, created_at, updated_at
                        ) VALUES (
                            :id, :org_id, :invoice_id, :item_name, :qty, :uom,
                            :rate, :amount, :sort_order, :created_at, :updated_at
                        ) ON CONFLICT DO NOTHING
                    """), {
                        'id': str(uuid.uuid4()),
                        'org_id': master_org_id,
                        'invoice_id': invoice_id,
                        'sort_order': j + 1,
                        'created_at': datetime.now(),
                        'updated_at': datetime.now(),
                        **item
                    })
                
                invoice_scenarios.append({
                    'invoice_id': invoice_id,
                    'customer_org_id': org["id"],
                    'customer_name': org["name"],
                    'amount': total,
                    'outstanding': outstanding,
                    'status': status,
                    'due_date': due_date
                })
        
        print(f"✓ Created {len(invoice_scenarios)} subscription invoices")
        
        # 4. Create Payment Reminder Configurations
        print("\n4. Creating Payment Reminder Configurations...")
        for org in CUSTOMER_ORGANIZATIONS:
            db.execute(text("""
                INSERT INTO reminder_configs (
                    id, organization_id, reminder_type, is_enabled,
                    grace_period_days, first_reminder_days, second_reminder_days,
                    final_notice_days, auto_deactivate_days, reminder_frequency_days,
                    max_reminders_per_stage, auto_deactivate_enabled,
                    send_copy_to_admin, created_at, updated_at, created_by
                ) VALUES (
                    :id, :org_id, 'auto', true,
                    15, 30, 60, 90, 120, 7, 3, true, true, 
                    :created_at, :updated_at, :user_id
                ) ON CONFLICT (organization_id) DO UPDATE SET
                    updated_at = EXCLUDED.updated_at
            """), {
                'id': str(uuid.uuid4()),
                'org_id': org["id"],
                'created_at': datetime.now(),
                'updated_at': datetime.now(),
                'user_id': admin_user_id
            })
        print(f"✓ Created reminder configs for {len(CUSTOMER_ORGANIZATIONS)} organizations")
        
        # 5. Create Some Payment Entries
        print("\n5. Creating Sample Payment Entries...")
        payment_count = 0
        
        # Create payments for some of the invoices
        for scenario in invoice_scenarios[:6]:  # Only first 6 invoices
            if scenario['status'] in ['paid', 'partial_paid']:
                # Determine payment amount
                if scenario['status'] == 'paid':
                    payment_amount = scenario['amount']
                else:  # partial_paid
                    payment_amount = scenario['amount'] - scenario['outstanding']
                
                payment_id = str(uuid.uuid4())
                payment_date = scenario['due_date'] - timedelta(days=5)
                
                # Insert payment entry
                db.execute(text("""
                    INSERT INTO payment_entries (
                        id, organization_id, payment_type, party_id, amount,
                        currency_code, payment_date, payment_mode, status,
                        reference_no, source, created_by, updated_by, 
                        created_at, updated_at
                    ) VALUES (
                        :id, :org_id, 'Customer_Payment', :party_id, :amount,
                        'USD', :payment_date, 'Bank_Transfer', 'Confirmed', 
                        :reference_no, 'Manual', :user_id, :user_id,
                        :created_at, :updated_at
                    )
                """), {
                    'id': payment_id,
                    'org_id': master_org_id,
                    'party_id': scenario['customer_org_id'],
                    'amount': payment_amount,
                    'payment_date': payment_date,
                    'reference_no': f"PAY-{payment_date.strftime('%Y%m%d')}-{scenario['customer_org_id'][-4:]}",
                    'user_id': admin_user_id,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
                
                # Insert payment reference (allocation)
                db.execute(text("""
                    INSERT INTO payment_references (
                        id, organization_id, payment_id, invoice_id, 
                        allocated_amount, created_by, created_at
                    ) VALUES (
                        :id, :org_id, :payment_id, :invoice_id, 
                        :allocated_amount, :user_id, :created_at
                    )
                """), {
                    'id': str(uuid.uuid4()),
                    'org_id': master_org_id,
                    'payment_id': payment_id,
                    'invoice_id': scenario['invoice_id'],
                    'allocated_amount': payment_amount,
                    'user_id': admin_user_id,
                    'created_at': datetime.now()
                })
                
                payment_count += 1
        
        print(f"✓ Created {payment_count} payment entries with allocations")
        
        # 6. Create Some Reminder Logs (simulated sent reminders)
        print("\n6. Creating Sample Reminder Logs...")
        overdue_invoices = [s for s in invoice_scenarios if s['status'] == 'outstanding' and s['due_date'] < datetime.now()]
        reminder_log_count = 0
        
        for scenario in overdue_invoices:
            days_overdue = (datetime.now() - scenario['due_date']).days
            if days_overdue > 30:  # Send first reminder
                db.execute(text("""
                    INSERT INTO reminder_logs (
                        id, organization_id, invoice_id, reminder_stage, 
                        reminder_type, status, sent_at, subject, recipient_email,
                        days_overdue, triggered_by, stage_attempt_number,
                        created_at, updated_at
                    ) VALUES (
                        :id, :org_id, :invoice_id, 'first_reminder',
                        'auto', 'sent', :sent_at, :subject, :recipient,
                        :days_overdue, 'automated', 1,
                        :created_at, :updated_at
                    ) ON CONFLICT DO NOTHING
                """), {
                    'id': str(uuid.uuid4()),
                    'org_id': scenario['customer_org_id'],
                    'invoice_id': scenario['invoice_id'],
                    'sent_at': datetime.now() - timedelta(days=7),
                    'subject': f"Payment Reminder: Invoice Overdue - {scenario['customer_name']}",
                    'recipient': f"billing@{scenario['customer_name'].lower().replace(' ', '')}.com",
                    'days_overdue': days_overdue,
                    'created_at': datetime.now(),
                    'updated_at': datetime.now()
                })
                reminder_log_count += 1
        
        print(f"✓ Created {reminder_log_count} reminder logs")
        
        db.commit()
        print("\n✅ Core service data seeding completed!")
        
    except Exception as e:
        print(f"❌ Error seeding core service data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def print_test_data_summary():
    """Print summary of created test data"""
    print("\n" + "=" * 60)
    print("🎉 B2B TEST DATA SEEDING COMPLETED!")
    print("=" * 60)
    
    print("\n📊 DATA SUMMARY:")
    print("-" * 30)
    print(f"• 1 Master Organization: {MASTER_ORG_DATA['name']}")
    print(f"• {len(CUSTOMER_ORGANIZATIONS)} Customer Organizations")
    print(f"• 1 System Admin User: {SYSTEM_ADMIN_USER['email']}")
    print(f"• {len(BILLING_CONTACTS)} Billing Contact Users")
    print(f"• ~{len(CUSTOMER_ORGANIZATIONS) * 3} Subscription Invoices (3 months each)")
    print(f"• {len(CUSTOMER_ORGANIZATIONS)} Payment Reminder Configurations") 
    print(f"• Multiple Payment Entries with Allocations")
    print(f"• Essential Chart of Accounts")
    print(f"• Bank Accounts for Payment Processing")
    
    print("\n🔐 TEST LOGIN CREDENTIALS:")
    print("-" * 30)
    print(f"System Admin: {SYSTEM_ADMIN_USER['email']} (password: admin123)")
    for contact in BILLING_CONTACTS:
        print(f"Billing Contact: {contact['email']} (password: test123)")
    
    print("\n📋 TESTING SCENARIOS:")
    print("-" * 30)
    print("1. B2B Billing Management Dashboard")
    print("   → View master org invoices only (system admin filtering)")
    print("   → Test date filtering and pagination")
    print("   → View invoice details and payment history")
    
    print("\n2. Payment Reminder System")
    print("   → Check overdue invoices and reminder configurations")
    print("   → Test manual reminder sending") 
    print("   → Review reminder logs and escalation sequences")
    
    print("\n3. Payment Processing")
    print("   → Record payments against outstanding invoices")
    print("   → Test payment allocation and reconciliation")
    print("   → View payment history and audit trails")
    
    print("\n4. Organization Management")
    print("   → View customer organizations in B2B hierarchy")
    print("   → Test subscription billing and seat management")
    print("   → Review billing status and payment terms")
    
    print("\n5. Reporting and Analytics")
    print("   → Generate aging reports for overdue invoices")
    print("   → View payment collection metrics") 
    print("   → Test B2B billing dashboard summaries")
    
    print(f"\n💡 Access the admin portal at: http://localhost:3000/admin")
    print(f"   Use system admin credentials to test B2B filtering")
    print("\n" + "=" * 60 + "\n")


def main():
    """Main execution function"""
    print("🚀 STARTING B2B COMPREHENSIVE TEST DATA SEEDING")
    print("This will create complete test data for B2B billing system validation")
    print("=" * 60)
    
    try:
        # Step 1: Seed identity service data
        seed_identity_service()
        
        # Step 2: Seed core service data  
        seed_core_service()
        
        # Step 3: Print summary
        print_test_data_summary()
        
    except Exception as e:
        print(f"\n❌ SEEDING FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()