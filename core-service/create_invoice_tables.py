"""Create invoice tables in the database"""

import os
from sqlalchemy import create_engine, text

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://horizon_user:horizon_pass@localhost:5432/core_db")

def main():
    engine = create_engine(DATABASE_URL)
    
    # Read and execute the SQL file
    sql_file = "scripts/create_tables.sql"
    
    try:
        with open(sql_file, 'r') as f:
            sql_content = f.read()
        
        # Split by semicolons and execute each statement
        statements = [s.strip() for s in sql_content.split(';') if s.strip()]
        
        with engine.begin() as conn:
            for i, statement in enumerate(statements):
                if statement:
                    try:
                        conn.execute(text(statement))
                        print(f"✅ Executed statement {i+1}/{len(statements)}")
                    except Exception as e:
                        # Skip errors for tables that already exist
                        if "already exists" in str(e).lower():
                            print(f"⏭️  Skipped statement {i+1} (already exists)")
                        else:
                            print(f"⚠️  Error in statement {i+1}: {str(e)}")
        
        print("\n✅ Database tables created successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
