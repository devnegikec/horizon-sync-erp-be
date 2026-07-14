#!/usr/bin/env python3
"""
Database Cleanup Script - Accounts and Default Accounts Tables
==============================================================

This script safely cleans up the accounts and default_accounts tables
with optional backup and confirmation prompts.

Usage:
    python cleanup_accounts.py [--dry-run] [--backup] [--force]

Options:
    --dry-run   Show what would be deleted without actually deleting
    --backup    Create backup files before deletion  
    --force     Skip confirmation prompts (not recommended)
"""

import os
import sys
import json
import argparse
from datetime import datetime
from typing import Optional
import asyncio

# Add project root to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.orm import sessionmaker
from app.core.config import get_settings

class DatabaseCleanup:
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        self.metadata = MetaData()
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.session.close()
        self.engine.dispose()
        
    def check_tables_exist(self) -> dict:
        """Check if accounts and default_accounts tables exist"""
        tables_exist = {}
        
        for table_name in ['accounts', 'default_accounts']:
            result = self.session.execute(text(
                "SELECT COUNT(*) FROM information_schema.tables "
                "WHERE table_name = :table_name"
            ), {"table_name": table_name})
            
            tables_exist[table_name] = result.scalar() > 0
            
        return tables_exist
        
    def get_table_counts(self) -> dict:
        """Get row counts for each table"""
        counts = {}
        tables_exist = self.check_tables_exist()
        
        for table_name in ['accounts', 'default_accounts']:
            if tables_exist[table_name]:
                result = self.session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                counts[table_name] = result.scalar()
            else:
                counts[table_name] = 0
                
        return counts
        
    def backup_table_data(self, table_name: str, backup_dir: str = "backups") -> Optional[str]:
        """Backup table data to JSON file"""
        tables_exist = self.check_tables_exist()
        
        if not tables_exist.get(table_name, False):
            print(f"❌ Table '{table_name}' does not exist, skipping backup")
            return None
            
        # Create backup directory
        os.makedirs(backup_dir, exist_ok=True)
        
        # Generate backup filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"{table_name}_backup_{timestamp}.json")
        
        try:
            # Fetch all data
            result = self.session.execute(text(f"SELECT * FROM {table_name}"))
            columns = result.keys()
            rows = result.fetchall()
            
            # Convert to JSON-serializable format
            data = []
            for row in rows:
                row_dict = {}
                for idx, col in enumerate(columns):
                    value = row[idx]
                    # Convert datetime and UUID objects to strings
                    if hasattr(value, 'isoformat'):  # datetime
                        value = value.isoformat()
                    elif hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool, type(None))):
                        value = str(value)
                    row_dict[col] = value
                data.append(row_dict)
            
            # Save to file
            with open(backup_file, 'w') as f:
                json.dump({
                    'table': table_name,
                    'timestamp': timestamp,
                    'row_count': len(data),
                    'data': data
                }, f, indent=2, default=str)
                
            print(f"✅ Backup created: {backup_file} ({len(data)} rows)")
            return backup_file
            
        except Exception as e:
            print(f"❌ Error creating backup for {table_name}: {e}")
            return None
            
    def truncate_table(self, table_name: str, dry_run: bool = False) -> bool:
        """Safely truncate a table"""
        tables_exist = self.check_tables_exist()
        
        if not tables_exist.get(table_name, False):
            print(f"ℹ️  Table '{table_name}' does not exist, skipping")
            return True
            
        try:
            if dry_run:
                print(f"🔍 DRY RUN: Would truncate table '{table_name}'")
                return True
                
            # Use CASCADE to handle foreign key constraints
            self.session.execute(text(f"TRUNCATE TABLE {table_name} CASCADE"))
            self.session.commit()
            print(f"✅ Table '{table_name}' truncated successfully")
            return True
            
        except Exception as e:
            print(f"❌ Error truncating table {table_name}: {e}")
            self.session.rollback()
            return False
            
    def cleanup_accounts_tables(self, dry_run: bool = False, create_backup: bool = False) -> bool:
        """Main cleanup function for accounts tables"""
        print("\n" + "="*60)
        print("🧹 ACCOUNTS TABLES CLEANUP")
        print("="*60)
        
        # Check current state
        tables_exist = self.check_tables_exist()
        counts = self.get_table_counts()
        
        print(f"\n📊 Current state:")
        for table_name in ['accounts', 'default_accounts']:
            exist_status = "EXISTS" if tables_exist[table_name] else "MISSING"
            row_count = counts[table_name]
            print(f"   • {table_name}: {exist_status} ({row_count} rows)")
            
        total_rows = sum(counts.values())
        if total_rows == 0:
            print("\n✨ Tables are already clean (0 rows total)")
            return True
            
        # Create backups if requested
        if create_backup and not dry_run:
            print(f"\n💾 Creating backups...")
            for table_name in ['accounts', 'default_accounts']:
                if tables_exist[table_name] and counts[table_name] > 0:
                    self.backup_table_data(table_name)
                    
        # Perform cleanup
        print(f"\n🗑️  {'DRY RUN: ' if dry_run else ''}Cleaning up tables...")
        
        # Order matters due to foreign key constraints
        cleanup_order = ['default_accounts', 'accounts']  # default_accounts references accounts
        
        success = True
        for table_name in cleanup_order:
            if tables_exist[table_name] and counts[table_name] > 0:
                if not self.truncate_table(table_name, dry_run):
                    success = False
                    
        if success and not dry_run:
            print(f"\n✅ Cleanup completed successfully!")
        elif success and dry_run:
            print(f"\n🔍 DRY RUN completed - no changes made")
        else:
            print(f"\n❌ Cleanup failed - check errors above")
            
        return success

def main():
    parser = argparse.ArgumentParser(description="Clean up accounts and default_accounts tables")
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be deleted without actually deleting')
    parser.add_argument('--backup', action='store_true', 
                       help='Create backup files before deletion')
    parser.add_argument('--force', action='store_true', 
                       help='Skip confirmation prompts')
    
    args = parser.parse_args()
    
    try:
        # Get database settings
        settings = get_settings()
        database_url = settings.CORE_DATABASE_URL
        
        print("🔧 Horizon Sync - Database Cleanup Tool")
        print(f"📊 Target Database: {database_url.split('@')[1] if '@' in database_url else 'Local'}")
        
        with DatabaseCleanup(database_url) as cleanup:
            # Show current state
            counts = cleanup.get_table_counts()
            total_rows = sum(counts.values())
            
            if total_rows == 0:
                print("\n✨ No data to clean up - tables are already empty")
                return
                
            # Confirmation prompt (unless --force is used)
            if not args.force and not args.dry_run:
                print(f"\n⚠️  WARNING: This will delete {total_rows} rows from accounts tables")
                print(f"   • accounts: {counts['accounts']} rows")  
                print(f"   • default_accounts: {counts['default_accounts']} rows")
                
                if args.backup:
                    print("   • Backups WILL be created before deletion")
                else:
                    print("   • NO backups will be created")
                    
                response = input("\n❓ Are you sure you want to continue? (yes/no): ").lower()
                if response not in ['yes', 'y']:
                    print("❌ Operation cancelled by user")
                    return
                    
            # Perform cleanup
            success = cleanup.cleanup_accounts_tables(
                dry_run=args.dry_run,
                create_backup=args.backup
            )
            
            if not success:
                sys.exit(1)
                
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()