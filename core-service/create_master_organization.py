#!/usr/bin/env python3
"""
Step 1, 2 & 3: Complete Master Organization and B2B Customer Setup

Step 1: Ensures that exactly one "Master Organization" exists in the identity database.
Step 2: Makes all non-master organizations become customers of the master organization.
Step 3: Creates customer records in core service for all customer organizations.

Prevents creation of duplicate master organizations and ensures proper B2B hierarchy
with synchronized customer data across services.

Usage:
    python create_master_organization.py
"""

import os
import sys
import uuid
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Load .env from core-service directory
_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)

# Database connection settings from .env
IDENTITY_DATABASE_URL = os.getenv("IDENTITY_DATABASE_URL")
CORE_DATABASE_URL = os.getenv("DATABASE_URL")

if not IDENTITY_DATABASE_URL:
    raise RuntimeError("IDENTITY_DATABASE_URL is not set in .env")
if not CORE_DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")

# Master Organization Configuration
MASTER_ORG_CONFIG = {
    "id": "550e8400-e29b-41d4-a716-446655440001",
    "name": "Master Organization",
    "slug": "master-organization", 
    "display_name": "Master Organization",
    "organization_type": "master",
    "status": "active",
    "email": "master@horizonsync.com",
    "website": "https://horizonsync.com",
    "city": "San Francisco",
    "state": "CA",
    "country": "USA",
    "base_currency": "USD"
}


def ensure_single_master_organization():
    """
    THREAD-SAFE: Ensures exactly one master organization exists and sets up complete B2B system.
    
    Step 1 - Master Organization Setup:
    1. Only one organization with name "Master Organization" can exist
    2. Only one organization with organization_type "master" can exist
    3. Uses atomic UPSERT operations to prevent race conditions
    4. Database constraints prevent duplicates at schema level
    
    Step 2 - Customer Relationship Setup:
    5. All non-master organizations become customers of master organization
    6. Preserves existing hierarchies among customer organizations
    7. Ensures proper B2B billing hierarchy
    
    Step 3 - Core Service Customer Sync:
    8. Creates customer records in core service for all customer organizations
    9. Syncs organization data to customers table for billing operations
    10. Maintains data consistency across microservices
    """
    print("🔧 ENSURING COMPLETE B2B SETUP: MASTER ORG + CUSTOMERS + CORE SYNC (THREAD-SAFE)")
    print("=" * 80)
    
    identity_engine = create_engine(IDENTITY_DATABASE_URL)
    IdentitySession = sessionmaker(bind=identity_engine)
    db = IdentitySession()
    
    try:
        # Step 1: Add constraints FIRST to prevent any duplicates
        print("\n1. Adding database constraints to prevent duplicates...")
        add_master_organization_constraints(db)
        
        # Step 2: Use advisory lock for additional safety during setup
        print("\n2. Acquiring advisory lock for safe setup...")
        advisory_lock_id = 12345  # Arbitrary consistent number for master org setup
        
        lock_acquired = db.execute(text("""
            SELECT pg_try_advisory_xact_lock(:lock_id) AS acquired
        """), {'lock_id': advisory_lock_id}).fetchone().acquired
        
        if not lock_acquired:
            print("   ⚠️  Another process is setting up master organization. Waiting...")
            db.execute(text("SELECT pg_advisory_xact_lock(:lock_id)"), {'lock_id': advisory_lock_id})
        
        print("   ✓ Advisory lock acquired")
        
        # Step 3: Idempotent master organization setup - thread safe
        print("\n3. Performing master organization setup...")

        # A master organization may already exist with a DIFFERENT id than the
        # configured one (e.g. created by an Alembic migration). Relying solely on
        # ON CONFLICT (id) would attempt to INSERT a second master org in that case,
        # which the check_single_master_org() trigger rejects. So we first look up
        # any existing master org by organization_type and update it in place,
        # preserving its id (and any child FK references that point to it).
        existing_master = db.execute(text("""
            SELECT id FROM organizations
            WHERE organization_type = 'master'
              AND deleted_at IS NULL
            ORDER BY created_at
            LIMIT 1
        """)).fetchone()

        if existing_master:
            result = db.execute(text("""
                UPDATE organizations SET
                    name = :name,
                    slug = :slug,
                    display_name = :display_name,
                    status = :status,
                    email = :email,
                    website = :website,
                    city = :city,
                    state = :state,
                    country = :country,
                    updated_at = :updated_at
                WHERE id = :existing_id
                RETURNING id, name, organization_type
            """), {
                **MASTER_ORG_CONFIG,
                'existing_id': existing_master.id,
                'updated_at': datetime.now()
            }).fetchone()
        else:
            result = db.execute(text("""
                INSERT INTO organizations (
                    id, name, slug, display_name, organization_type, status, is_active,
                    email, website, city, state, country, billing_status,
                    base_currency, max_users, max_credits, created_at, updated_at
                ) VALUES (
                    :id, :name, :slug, :display_name, :org_type, :status, true,
                    :email, :website, :city, :state, :country, 'active',
                    'USD', 10000, 1000000, :created_at, :updated_at
                )
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    slug = EXCLUDED.slug,
                    display_name = EXCLUDED.display_name,
                    organization_type = EXCLUDED.organization_type,
                    status = EXCLUDED.status,
                    email = EXCLUDED.email,
                    website = EXCLUDED.website,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    country = EXCLUDED.country,
                    updated_at = EXCLUDED.updated_at
                RETURNING id, name, organization_type
            """), {
                **MASTER_ORG_CONFIG,
                'org_type': MASTER_ORG_CONFIG["organization_type"],
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }).fetchone()

        print(f"   ✓ Master organization ready: {result.name} (ID: {result.id})")
        
        # Step 4: Clean up any duplicate masters that might exist from before constraints
        print("\n4. Cleaning up any pre-existing duplicates...")
        cleanup_duplicate_masters(db, str(result.id))
        
        # Step 5: Make all non-master organizations customers of master organization (Step 2)
        print("\n5. Setting up customer relationships...")
        setup_customer_relationships(db, str(result.id))
        
        # Step 6: Create customer records in core service for all customer organizations (Step 3)
        print("\n6. Syncing customer organizations to core service...")
        sync_customer_records_to_core(str(result.id))
        
        db.commit()
        print("\n✅ Thread-safe master organization, customer relationships, and core sync completed!")
        
        # Verify final state
        verify_complete_setup(str(result.id))
        
    except Exception as e:
        print(f"\n❌ Error setting up master organization: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def cleanup_duplicate_masters(db, keep_master_id):
    """Clean up any duplicate master organizations (thread-safe cleanup)"""
    duplicates = db.execute(text("""
        SELECT id, name FROM organizations 
        WHERE (name = 'Master Organization' OR organization_type = 'master') 
        AND id != :keep_id
        ORDER BY created_at
    """), {'keep_id': keep_master_id}).fetchall()
    
    if not duplicates:
        print("   → No duplicate masters found")
        return
        
    print(f"   → Found {len(duplicates)} duplicate masters to remove")
    
    for duplicate in duplicates:
        # Migrate child organizations to the primary master
        updated_count = db.execute(text("""
            UPDATE organizations 
            SET parent_organization_id = :keep_id, updated_at = :updated_at
            WHERE parent_organization_id = :duplicate_id
        """), {
            'keep_id': keep_master_id,
            'duplicate_id': duplicate.id,
            'updated_at': datetime.now()
        }).rowcount
        
        if updated_count > 0:
            print(f"   → Migrated {updated_count} child org(s) from {duplicate.name}")
        
        # Delete the duplicate master
        db.execute(text("DELETE FROM organizations WHERE id = :id"), {'id': duplicate.id})
        print(f"   ✓ Removed duplicate: {duplicate.name} ({duplicate.id})")


def update_master_organization(db, master_id):
    """Update existing master organization to ensure correct configuration"""
    db.execute(text("""
        UPDATE organizations 
        SET 
            name = :name,
            slug = :slug,
            display_name = :display_name,
            organization_type = :org_type,
            status = :status,
            email = :email,
            website = :website,
            city = :city,
            state = :state,
            country = :country,
            updated_at = :updated_at
        WHERE id = :master_id
    """), {
        **MASTER_ORG_CONFIG,
        'org_type': MASTER_ORG_CONFIG["organization_type"],
        'master_id': master_id,
        'updated_at': datetime.now()
    })
    print(f"   ✓ Updated master organization: {MASTER_ORG_CONFIG['name']}")


def consolidate_master_organizations(db, by_name, by_type):
    """Consolidate multiple master organizations into one"""
    
    # Collect all unique master org IDs
    all_master_ids = set()
    if by_name:
        all_master_ids.update([row.id for row in by_name])
    if by_type:
        all_master_ids.update([row.id for row in by_type])
    
    master_ids_list = sorted(list(all_master_ids))
    
    if len(master_ids_list) <= 1:
        if master_ids_list:
            update_master_organization(db, master_ids_list[0])
        return
    
    # Keep the first one as the primary master
    primary_master_id = master_ids_list[0]
    duplicate_ids = master_ids_list[1:]
    
    print(f"   → Keeping primary master: {primary_master_id}")
    print(f"   → Removing {len(duplicate_ids)} duplicate masters: {duplicate_ids}")
    
    # Update primary master to correct configuration
    update_master_organization(db, primary_master_id)
    
    # Handle child organizations that reference duplicate masters
    for duplicate_id in duplicate_ids:
        print(f"   → Migrating child organizations from {duplicate_id} to {primary_master_id}")
        db.execute(text("""
            UPDATE organizations 
            SET parent_organization_id = :primary_id, updated_at = :updated_at
            WHERE parent_organization_id = :duplicate_id
        """), {
            'primary_id': primary_master_id,
            'duplicate_id': duplicate_id,
            'updated_at': datetime.now()
        })
        
        # Delete duplicate master
        db.execute(text("DELETE FROM organizations WHERE id = :duplicate_id"), {
            'duplicate_id': duplicate_id
        })
        print(f"   ✓ Removed duplicate master: {duplicate_id}")


def add_master_organization_constraints(db):
    """Add database constraints to prevent multiple master organizations (idempotent)"""
    
    # Create partial unique index on organization_type = 'master' (PostgreSQL syntax)
    try:
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_master_org_type 
            ON organizations (organization_type) 
            WHERE organization_type = 'master'
        """))
        print("   ✓ Database constraint ready: unique master organization type")
    except Exception as e:
        print(f"   → Constraint exists or error: {e}")
    
    # Create partial unique index on name = 'Master Organization'
    try:
        db.execute(text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_unique_master_org_name 
            ON organizations (name) 
            WHERE name = 'Master Organization'
        """))
        print("   ✓ Database constraint ready: unique master organization name")
    except Exception as e:
        print(f"   → Index exists or error: {e}")
    
    # Commit constraints before proceeding
    db.commit()
    print("   ✓ Database constraints are active")


def setup_customer_relationships(db, master_org_id):
    """
    STEP 2: Make all non-master organizations customers of the master organization.
    
    Business Rules:
    1. All organizations with organization_type != 'master' become customers
    2. Set their parent_organization_id to the master organization
    3. Preserve existing parent-child relationships among non-master orgs
    4. Thread-safe operation with proper error handling
    """
    print("   🔗 Setting up B2B customer relationships...")
    
    # Find all non-master organizations without a parent or with incorrect parent
    orphan_orgs = db.execute(text("""
        SELECT id, name, organization_type, parent_organization_id 
        FROM organizations 
        WHERE organization_type != 'master' 
        AND (parent_organization_id IS NULL OR parent_organization_id != :master_id)
        ORDER BY created_at
    """), {'master_id': master_org_id}).fetchall()
    
    if not orphan_orgs:
        print("   → All non-master organizations already linked to master")
        return
    
    print(f"   → Found {len(orphan_orgs)} organizations to link as customers")
    
    # Update organizations to be customers of master organization
    updated_count = 0
    for org in orphan_orgs:
        # Skip if this org already has a non-master parent (preserve existing hierarchies)
        if org.parent_organization_id:
            # Check if parent is also non-master (preserve sub-hierarchies)
            parent_type = db.execute(text("""
                SELECT organization_type FROM organizations 
                WHERE id = :parent_id
            """), {'parent_id': org.parent_organization_id}).fetchone()
            
            if parent_type and parent_type.organization_type != 'master':
                print(f"   → Preserving existing hierarchy: {org.name} under {org.parent_organization_id}")
                continue
        
        # Set master organization as parent
        db.execute(text("""
            UPDATE organizations 
            SET 
                parent_organization_id = :master_id,
                updated_at = :updated_at
            WHERE id = :org_id
        """), {
            'master_id': master_org_id,
            'org_id': org.id,
            'updated_at': datetime.now()
        })
        
        updated_count += 1
        print(f"   ✓ Linked customer: {org.name} ({org.organization_type})")
    
    print(f"   ✅ Successfully linked {updated_count} organizations as customers")
    
    # Handle existing hierarchies - ensure root organizations point to master
    print("   🔍 Checking for root organizations in existing hierarchies...")
    
    root_orgs = db.execute(text("""
        WITH RECURSIVE org_hierarchy AS (
            -- Start with organizations that have parents
            SELECT id, name, organization_type, parent_organization_id, 1 as level
            FROM organizations 
            WHERE parent_organization_id IS NOT NULL 
            AND organization_type != 'master'
            
            UNION ALL
            
            -- Recursively find their parents
            SELECT o.id, o.name, o.organization_type, o.parent_organization_id, oh.level + 1
            FROM organizations o
            JOIN org_hierarchy oh ON o.id = oh.parent_organization_id
            WHERE o.organization_type != 'master'
        )
        -- Find root organizations (non-master orgs at the top of hierarchies)
        SELECT DISTINCT o.id, o.name, o.organization_type, o.parent_organization_id
        FROM organizations o
        WHERE o.organization_type != 'master'
        AND o.id NOT IN (
            SELECT DISTINCT parent_organization_id 
            FROM org_hierarchy 
            WHERE parent_organization_id IS NOT NULL
        )
        AND (o.parent_organization_id IS NULL OR o.parent_organization_id != :master_id)
    """), {'master_id': master_org_id}).fetchall()
    
    hierarchy_updated = 0
    for root_org in root_orgs:
        db.execute(text("""
            UPDATE organizations 
            SET 
                parent_organization_id = :master_id,
                updated_at = :updated_at
            WHERE id = :root_id
        """), {
            'master_id': master_org_id,
            'root_id': root_org.id,
            'updated_at': datetime.now()
        })
        
        hierarchy_updated += 1
        print(f"   ✓ Root organization linked to master: {root_org.name}")
    
    if hierarchy_updated > 0:
        print(f"   ✅ Linked {hierarchy_updated} root organizations to master")
    else:
        print("   → No additional root organizations found")


def sync_customer_records_to_core(master_org_id):
    """
    STEP 3: Create customer records in core service for all customer organizations.
    
    Business Rules:
    1. Each customer organization gets a customer record in core service
    2. Customer records belong to the master organization for billing
    3. Sync organization data (name, email, address) to customer fields
    4. Generate unique customer codes based on organization slugs
    5. Handle duplicates gracefully with UPSERT operations
    """
    print("   🔄 Syncing customer organizations to core service...")
    
    # Connect to both databases
    identity_engine = create_engine(IDENTITY_DATABASE_URL)
    core_engine = create_engine(CORE_DATABASE_URL)
    
    IdentitySession = sessionmaker(bind=identity_engine)
    CoreSession = sessionmaker(bind=core_engine)
    
    identity_db = IdentitySession()
    core_db = CoreSession()
    
    try:
        # Get all customer organizations from identity service
        customer_orgs = identity_db.execute(text("""
            SELECT id, name, slug, email, website, city, state, country, 
                   display_name, industry, organization_type,
                   created_at, updated_at
            FROM organizations 
            WHERE parent_organization_id = :master_id
            AND organization_type != 'master'
            ORDER BY name
        """), {'master_id': master_org_id}).fetchall()
        
        if not customer_orgs:
            print("   → No customer organizations found to sync")
            return
        
        print(f"   → Found {len(customer_orgs)} customer organizations to sync")
        
        synced_count = 0
        updated_count = 0
        
        for org in customer_orgs:
            # Generate customer code from organization slug or name
            customer_code = org.slug if org.slug else org.name.upper().replace(' ', '_')[:20]
            
            # Ensure customer code is unique by adding suffix if needed
            base_code = customer_code
            counter = 1
            while True:
                existing = core_db.execute(text("""
                    SELECT id FROM customers 
                    WHERE customer_code = :code AND organization_id = :org_id
                """), {'code': customer_code, 'org_id': master_org_id}).fetchone()
                
                if not existing:
                    break
                    
                customer_code = f"{base_code}_{counter}"
                counter += 1
                if counter > 999:  # Prevent infinite loop
                    customer_code = f"{base_code}_{uuid.uuid4().hex[:8]}"
                    break
            
            # UPSERT customer record
            result = core_db.execute(text("""
                INSERT INTO customers (
                    organization_id, customer_name, customer_code, email,
                    city, state, country, status, is_tax_exempt,
                    credit_limit, outstanding_balance, tags, extra_data,
                    created_at, updated_at
                ) VALUES (
                    :org_id, :name, :code, :email,
                    :city, :state, :country, 'active', false,
                    0, 0, :tags, :extra_data,
                    :created_at, :updated_at
                )
                ON CONFLICT (organization_id, customer_code) DO UPDATE SET
                    customer_name = EXCLUDED.customer_name,
                    email = EXCLUDED.email,
                    city = EXCLUDED.city,
                    state = EXCLUDED.state,
                    country = EXCLUDED.country,
                    updated_at = EXCLUDED.updated_at,
                    tags = EXCLUDED.tags,
                    extra_data = EXCLUDED.extra_data
                RETURNING id, customer_name, (xmax = 0) AS was_inserted
            """), {
                'org_id': master_org_id,
                'name': org.name,
                'code': customer_code,
                'email': org.email or f"billing@{org.slug or 'customer'}.com",
                'city': org.city,
                'state': org.state,
                'country': org.country,
                'tags': f'{{"organization_id": "{org.id}", "organization_type": "{org.organization_type}", "industry": "{org.industry or ""}"}}',
                'extra_data': f'{{"original_organization_data": {{"id": "{org.id}", "slug": "{org.slug}", "website": "{org.website or ""}"}}}}',
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }).fetchone()
            
            if result.was_inserted:
                synced_count += 1
                print(f"   ✓ Created customer: {result.customer_name} (Code: {customer_code})")
            else:
                updated_count += 1
                print(f"   ↻ Updated customer: {result.customer_name} (Code: {customer_code})")
        
        core_db.commit()
        
        print(f"   ✅ Customer sync completed: {synced_count} created, {updated_count} updated")
        
    except Exception as e:
        print(f"   ❌ Error syncing customers to core service: {e}")
        core_db.rollback()
        raise
    finally:
        identity_db.close()
        core_db.close()


def verify_complete_setup(master_org_id):
    """Verify the complete B2B setup across both identity and core services"""
    print("\n7. Verifying complete B2B setup...")
    
    # Connect to identity service
    identity_engine = create_engine(IDENTITY_DATABASE_URL)
    IdentitySession = sessionmaker(bind=identity_engine)
    identity_db = IdentitySession()
    
    try:
        # Verify master organization in identity service
        master_orgs = identity_db.execute(text("""
            SELECT id, name, organization_type, status
            FROM organizations 
            WHERE organization_type = 'master'
            ORDER BY created_at
        """)).fetchall()
        
        if len(master_orgs) != 1:
            print(f"   ❌ ERROR: {len(master_orgs)} master organizations found (expected exactly 1)")
            return
        
        master = master_orgs[0]
        print(f"   ✅ Master Organization (Identity): {master.name} (ID: {master.id})")
        
        # Count customer organizations in identity service
        customer_orgs = identity_db.execute(text("""
            SELECT COUNT(*) as count
            FROM organizations 
            WHERE parent_organization_id = :master_id
            AND organization_type != 'master'
        """), {'master_id': master_org_id}).fetchone()
        
        print(f"   📊 Customer Organizations (Identity): {customer_orgs.count}")
        
        # Verify customer records in core service
        core_engine = create_engine(CORE_DATABASE_URL)
        CoreSession = sessionmaker(bind=core_engine)
        core_db = CoreSession()
        
        try:
            customer_records = core_db.execute(text("""
                SELECT COUNT(*) as count
                FROM customers 
                WHERE organization_id = :org_id
            """), {'org_id': master_org_id}).fetchone()
            
            print(f"   📊 Customer Records (Core): {customer_records.count}")
            
            # Check sync consistency
            if customer_orgs.count == customer_records.count:
                print("   ✅ Identity ↔ Core sync: Perfect consistency")
            else:
                print(f"   ⚠️  Identity ↔ Core sync: Mismatch detected ({customer_orgs.count} orgs vs {customer_records.count} customers)")
            
            # Sample customer records
            if customer_records.count > 0:
                sample_customers = core_db.execute(text("""
                    SELECT customer_name, customer_code, email, city, state
                    FROM customers 
                    WHERE organization_id = :org_id
                    ORDER BY customer_name
                    LIMIT 5
                """), {'org_id': master_org_id}).fetchall()
                
                print(f"   🏢 Sample Customer Records:")
                for customer in sample_customers:
                    location = f"{customer.city or ''}, {customer.state or ''}".strip(', ') or 'No location'
                    print(f"      → {customer.customer_name} ({customer.customer_code}) - {location}")
            
            # B2B Billing readiness check
            billing_ready = customer_orgs.count > 0 and customer_records.count > 0
            if billing_ready:
                print("   🎯 B2B Billing Status: ✅ READY - Master can bill all customers")
            else:
                print("   🎯 B2B Billing Status: ❌ NOT READY - Missing customer data")
                
        except Exception as e:
            print(f"   ❌ Error verifying core service: {e}")
        finally:
            core_db.close()
        
    except Exception as e:
        print(f"   ❌ Error verifying identity service: {e}")
    finally:
        identity_db.close()
    """Verify the final state of master organization and customer relationships"""
    print("\n6. Verifying master organization and customer relationships...")
    
    # Verify master organization
    master_orgs = identity_db.execute(text("""
        SELECT id, name, organization_type, status
        FROM organizations 
        WHERE organization_type = 'master'
        ORDER BY created_at
    """)).fetchall()
    
    if len(master_orgs) != 1:
        print(f"   ❌ ERROR: {len(master_orgs)} master organizations found (expected exactly 1)")
        return
    
    master = master_orgs[0]
    print(f"   ✅ Master Organization: {master.name} (ID: {master.id})")
    
    # Count customer organizations
    customer_stats = identity_db.execute(text("""
        SELECT 
            COUNT(*) as total_customers,
            COUNT(CASE WHEN parent_organization_id = :master_id THEN 1 END) as direct_customers,
            COUNT(CASE WHEN parent_organization_id != :master_id THEN 1 END) as indirect_customers
        FROM organizations 
        WHERE organization_type != 'master'
    """), {'master_id': master.id}).fetchone()
    
    print(f"   📊 Customer Statistics:")
    print(f"      → Total Organizations: {customer_stats.total_customers}")
    print(f"      → Direct Customers: {customer_stats.direct_customers}")
    print(f"      → Sub-Organizations: {customer_stats.indirect_customers}")
    
    # Show customer organization types
    customer_types = identity_db.execute(text("""
        SELECT 
            organization_type,
            COUNT(*) as count,
            COUNT(CASE WHEN parent_organization_id = :master_id THEN 1 END) as direct_to_master
        FROM organizations 
        WHERE organization_type != 'master'
        GROUP BY organization_type
        ORDER BY count DESC
    """), {'master_id': master.id}).fetchall()
    
    if customer_types:
        print(f"   🏢 Customer Types:")
        for ctype in customer_types:
            print(f"      → {ctype.organization_type}: {ctype.count} total, {ctype.direct_to_master} direct customers")
    
    # Check for orphaned organizations
    orphaned = identity_db.execute(text("""
        SELECT COUNT(*) as count
        FROM organizations 
        WHERE organization_type != 'master' 
        AND parent_organization_id IS NULL
    """)).fetchone()
    
    if orphaned.count > 0:
        print(f"   ⚠️  WARNING: {orphaned.count} organizations still without parent")
        
        orphaned_details = identity_db.execute(text("""
            SELECT name, organization_type 
            FROM organizations 
            WHERE organization_type != 'master' 
            AND parent_organization_id IS NULL
            LIMIT 5
        """)).fetchall()
        
        for org in orphaned_details:
            print(f"      → {org.name} ({org.organization_type})")
    
    # Verify B2B hierarchy integrity
    hierarchy_check = identity_db.execute(text("""
        WITH RECURSIVE hierarchy AS (
            SELECT id, name, parent_organization_id, 1 as level
            FROM organizations 
            WHERE organization_type = 'master'
            
            UNION ALL
            
            SELECT o.id, o.name, o.parent_organization_id, h.level + 1
            FROM organizations o
            JOIN hierarchy h ON o.parent_organization_id = h.id
        )
        SELECT COUNT(*) as connected_orgs
        FROM hierarchy
        WHERE level > 1
    """)).fetchone()
    
    total_non_master = identity_db.execute(text("""
        SELECT COUNT(*) as count 
        FROM organizations 
        WHERE organization_type != 'master'
    """)).fetchone()
    
    coverage_pct = (hierarchy_check.connected_orgs / total_non_master.count * 100) if total_non_master.count > 0 else 100
    
    print(f"   🌳 Hierarchy Coverage: {hierarchy_check.connected_orgs}/{total_non_master.count} ({coverage_pct:.1f}%)")
    
    if coverage_pct >= 100:
        print("   ✅ All organizations properly connected to master hierarchy")
    elif coverage_pct >= 90:
        print("   ⚠️  Most organizations connected - minor issues detected")  
    else:
        print("   ❌ Significant hierarchy issues detected")


def main():
    """Main execution function"""
    print("🚀 STEP 1, 2 & 3: COMPLETE B2B SETUP - THREAD-SAFE")
    print("Step 1: Ensures exactly one 'Master Organization' exists in identity_db")
    print("Step 2: Makes all non-master organizations customers of master organization") 
    print("Step 3: Creates customer records in core service for all customer organizations")
    print("Includes thread-safety mechanisms: advisory locks, atomic UPSERT, constraints")
    print("=" * 85)
    
    try:
        ensure_single_master_organization()
        print(f"\n💡 Complete B2B setup ready: Master organization, customer relationships, and core sync!")
        
    except Exception as e:
        print(f"\n❌ SETUP FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()