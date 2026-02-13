"""Verify that the migration script is valid and complete"""

import sys
import os

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def verify_migration_file():
    """Verify the migration file exists and has the correct structure"""
    migration_path = "alembic/versions/001_create_search_tables.py"
    
    if not os.path.exists(migration_path):
        print(f"❌ Migration file not found: {migration_path}")
        return False
    
    print(f"✓ Migration file exists: {migration_path}")
    
    # Read the migration file
    with open(migration_path, 'r') as f:
        content = f.read()
    
    # Check for required components
    required_components = [
        ("revision identifier", "revision: str = '001'"),
        ("upgrade function", "def upgrade() -> None:"),
        ("downgrade function", "def downgrade() -> None:"),
        ("search_documents table", "search_documents"),
        ("search_configurations table", "search_configurations"),
        ("GIN index", "postgresql_using='gin'"),
        ("tsvector column", "tsvector"),
        ("entity type seeding", "INSERT INTO search_configurations"),
        ("items configuration", "'items'"),
        ("customers configuration", "'customers'"),
        ("suppliers configuration", "'suppliers'"),
        ("warehouses configuration", "'warehouses'"),
        ("stock_entries configuration", "'stock_entries'"),
    ]
    
    all_present = True
    for component_name, search_string in required_components:
        if search_string in content:
            print(f"✓ {component_name} present")
        else:
            print(f"❌ {component_name} missing")
            all_present = False
    
    return all_present


def verify_alembic_config():
    """Verify Alembic configuration is correct"""
    alembic_ini_path = "alembic.ini"
    env_py_path = "alembic/env.py"
    
    if not os.path.exists(alembic_ini_path):
        print(f"❌ Alembic config not found: {alembic_ini_path}")
        return False
    
    print(f"✓ Alembic config exists: {alembic_ini_path}")
    
    if not os.path.exists(env_py_path):
        print(f"❌ Alembic env.py not found: {env_py_path}")
        return False
    
    print(f"✓ Alembic env.py exists: {env_py_path}")
    
    # Check env.py for async support
    with open(env_py_path, 'r') as f:
        env_content = f.read()
    
    if "async" in env_content and "asyncio" in env_content:
        print("✓ Alembic configured for async operations")
    else:
        print("⚠ Alembic may not be configured for async operations")
    
    return True


def main():
    """Run all verification checks"""
    print("=" * 60)
    print("Migration Verification")
    print("=" * 60)
    print()
    
    print("Checking migration file...")
    print("-" * 60)
    migration_ok = verify_migration_file()
    print()
    
    print("Checking Alembic configuration...")
    print("-" * 60)
    config_ok = verify_alembic_config()
    print()
    
    print("=" * 60)
    if migration_ok and config_ok:
        print("✓ All verification checks passed!")
        print()
        print("Migration Summary:")
        print("- Creates search_documents table with full-text search")
        print("- Creates search_configurations table")
        print("- Adds GIN indexes for optimal search performance")
        print("- Seeds configurations for 5 entity types:")
        print("  * items")
        print("  * customers")
        print("  * suppliers")
        print("  * warehouses")
        print("  * stock_entries")
        print()
        print("To apply the migration:")
        print("  alembic upgrade head")
        print()
        print("To rollback the migration:")
        print("  alembic downgrade -1")
        return 0
    else:
        print("❌ Some verification checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
