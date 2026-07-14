#!/usr/bin/env python3
"""
Invoice Cleanup and Seeding Script
Cleans up existing invoices and seeds new invoices for master organization customers
"""

import asyncio
import psycopg2
from decimal import Decimal
from datetime import datetime, timezone, timedelta
import uuid
import random

# Database connection settings
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'user': 'horizon_user',
    'password': 'horizon_pass',
    'dbname_identity': 'identity_db',
    'dbname_core': 'core_db'
}

def get_db_connection(db_name):
    """Get database connection"""
    config = DB_CONFIG.copy()
    if db_name == 'core':
        config['database'] = config.pop('dbname_core')
    elif db_name == 'identity':
        config['database'] = config.pop('dbname_identity')
    else:
        raise ValueError(f"Unknown database name: {db_name}")
    
    # Clean up config to remove unused dbname keys
    config.pop('dbname_core', None)
    config.pop('dbname_identity', None)
    
    return psycopg2.connect(**config)

def cleanup_existing_invoices():
    """Remove all existing invoices"""
    print("🧹 Cleaning up existing invoices...")
    
    conn = None
    try:
        conn = get_db_connection('core')
        cur = conn.cursor()
        
        # Get count before deletion
        cur.execute("SELECT COUNT(*) FROM invoices;")
        count_before = cur.fetchone()[0]
        print(f"   Found {count_before} existing invoices")
        
        # Delete all invoices
        cur.execute("DELETE FROM invoices;")
        deleted_count = cur.rowcount
        
        # Reset sequence if exists
        try:
            cur.execute("SELECT setval(pg_get_serial_sequence('invoices', 'id'), 1, false);")
        except:
            pass  # Sequence might not exist
        
        conn.commit()
        print(f"   ✅ Deleted {deleted_count} invoices successfully")
        
    except Exception as e:
        print(f"   ❌ Error cleaning up invoices: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def get_master_organization():
    """Get master organization details"""
    conn = None
    try:
        conn = get_db_connection('identity')
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, name 
            FROM organizations 
            WHERE organization_type = 'master'
            LIMIT 1;
        """)
        
        result = cur.fetchone()
        if not result:
            raise Exception("Master organization not found!")
        
        return {
            'id': result[0],
            'name': result[1]
        }
        
    except Exception as e:
        print(f"❌ Error getting master organization: {e}")
        raise
    finally:
        if conn:
            conn.close()

def get_master_customers(master_org_id):
    """Get all customers belonging to master organization"""
    conn = None
    try:
        conn = get_db_connection('core')
        cur = conn.cursor()
        
        cur.execute("""
            SELECT id, customer_code, customer_name, organization_id
            FROM customers 
            WHERE organization_id = %s
            ORDER BY customer_code;
        """, (master_org_id,))
        
        customers = []
        for row in cur.fetchall():
            customers.append({
                'id': row[0],
                'customer_code': row[1],
                'customer_name': row[2],
                'organization_id': row[3]
            })
        
        return customers
        
    except Exception as e:
        print(f"❌ Error getting customers: {e}")
        raise
    finally:
        if conn:
            conn.close()

def generate_sample_invoices(customers, master_org_id):
    """Generate sample invoices for customers"""
    print("📄 Generating new invoices for master organization customers...")
    
    invoice_types = ['sales', 'purchase', 'SALES', 'PURCHASE']
    statuses = ['draft', 'pending', 'paid', 'partial', 'overdue', 'cancelled']
    currencies = ['INR', 'USD', 'EUR']
    
    invoices = []
    invoice_counter = 1
    
    # Generate 2-5 invoices per customer
    for customer in customers:
        num_invoices = random.randint(2, 5)
        
        for i in range(num_invoices):
            # Generate random dates within last 3 months
            base_date = datetime.now(timezone.utc) - timedelta(days=random.randint(1, 90))
            due_date = base_date + timedelta(days=random.randint(15, 45))
            
            # Generate random amounts
            base_amount = Decimal(str(random.uniform(100.0, 10000.0))).quantize(Decimal('0.01'))
            
            invoice_type = random.choice(invoice_types)
            status = random.choice(statuses)
            currency = random.choice(currencies)
            
            # Generate invoice number
            if invoice_type.lower() in ['sales', 'SALES']:
                prefix = "CUST"
            else:  # purchase types
                prefix = "SUPP"
            invoice_no = f"{prefix}-INV-{invoice_counter:04d}"
            
            invoice = {
                'id': str(uuid.uuid4()),
                'organization_id': master_org_id,
                'invoice_no': invoice_no,
                'invoice_type': invoice_type,
                'party_id': customer['id'],
                'party_type': 'customer',
                'posting_date': base_date,
                'due_date': due_date,
                'status': status,
                'grand_total': base_amount,
                'outstanding_amount': base_amount if status in ['draft', 'pending', 'partial', 'overdue'] else Decimal('0.00'),
                'currency': currency,
                'reference_type': 'customer_order',
                'reference_id': str(uuid.uuid4()),
                'remarks': f"Sample invoice for {customer['customer_name']} - {invoice_type.upper()} Invoice",
                'created_by': str(uuid.uuid4()),  # System admin user
                'updated_by': str(uuid.uuid4()),
                'created_at': base_date,
                'updated_at': base_date
            }
            
            invoices.append(invoice)
            invoice_counter += 1
    
    return invoices

def seed_invoices(invoices):
    """Insert new invoices into database"""
    print(f"   💾 Seeding {len(invoices)} new invoices...")
    
    conn = None
    try:
        conn = get_db_connection('core')
        cur = conn.cursor()
        
        insert_query = """
            INSERT INTO invoices (
                id, organization_id, invoice_no, invoice_type, party_id, party_type,
                posting_date, due_date, status, grand_total, outstanding_amount,
                currency, reference_type, reference_id, remarks, created_by, 
                updated_by, created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            );
        """
        
        inserted_count = 0
        for invoice in invoices:
            try:
                cur.execute(insert_query, (
                    invoice['id'],
                    invoice['organization_id'],
                    invoice['invoice_no'],
                    invoice['invoice_type'],
                    invoice['party_id'],
                    invoice['party_type'],
                    invoice['posting_date'],
                    invoice['due_date'],
                    invoice['status'],
                    invoice['grand_total'],
                    invoice['outstanding_amount'],
                    invoice['currency'],
                    invoice['reference_type'],
                    invoice['reference_id'],
                    invoice['remarks'],
                    invoice['created_by'],
                    invoice['updated_by'],
                    invoice['created_at'],
                    invoice['updated_at']
                ))
                inserted_count += 1
                
            except Exception as e:
                print(f"   ⚠️ Failed to insert invoice {invoice['invoice_no']}: {e}")
                continue
        
        conn.commit()
        print(f"   ✅ Successfully seeded {inserted_count} invoices")
        
        # Show summary
        cur.execute("""
            SELECT 
                status,
                COUNT(*) as count,
                SUM(grand_total) as total_amount
            FROM invoices 
            GROUP BY status
            ORDER BY status;
        """)
        
        print("\n📊 Invoice Summary by Status:")
        for row in cur.fetchall():
            status, count, total = row
            print(f"   {status.upper()}: {count} invoices, Total: ${total:.2f}")
        
    except Exception as e:
        print(f"   ❌ Error seeding invoices: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def main():
    """Main execution function"""
    try:
        print("🚀 Starting Invoice Cleanup and Seeding Process")
        print("=" * 60)
        
        # Step 1: Cleanup existing invoices
        cleanup_existing_invoices()
        
        # Step 2: Get master organization
        print("\n🏢 Getting master organization details...")
        master_org = get_master_organization()
        print(f"   Master Organization: {master_org['name']} ({master_org['id']})")
        
        # Step 3: Get customers
        print("\n👥 Getting master organization customers...")
        customers = get_master_customers(master_org['id'])
        print(f"   Found {len(customers)} customers")
        
        if not customers:
            print("   ⚠️ No customers found for master organization!")
            return
        
        # Show some customer names
        print("   Sample customers:")
        for customer in customers[:5]:
            print(f"     - {customer['customer_code']}: {customer['customer_name']}")
        if len(customers) > 5:
            print(f"     ... and {len(customers) - 5} more")
        
        # Step 4: Generate new invoices
        print(f"\n📄 Generating invoices for {len(customers)} customers...")
        new_invoices = generate_sample_invoices(customers, master_org['id'])
        print(f"   Generated {len(new_invoices)} sample invoices")
        
        # Step 5: Seed new invoices
        print("\n💾 Seeding new invoices into database...")
        seed_invoices(new_invoices)
        
        print("\n" + "=" * 60)
        print("✅ Invoice cleanup and seeding completed successfully!")
        print("🎉 Your billing management now has fresh invoice data for master organization customers.")
        
    except Exception as e:
        print(f"\n❌ Process failed: {e}")
        return 1
        
    return 0

if __name__ == "__main__":
    exit(main())