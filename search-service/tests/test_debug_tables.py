"""Debug test to check table creation"""

import pytest


@pytest.mark.asyncio
async def test_check_tables(test_db):
    """Check what tables exist"""
    from sqlalchemy import text
    
    # Get table names
    result = await test_db.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
    tables = [row[0] for row in result.fetchall()]
    
    print(f"Tables in database: {tables}")
    
    assert len(tables) > 0, "No tables were created!"
