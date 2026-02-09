"""Simple database test to verify setup"""

import pytest
import uuid


@pytest.mark.asyncio
async def test_simple_insert(test_db):
    """Test that we can insert a document into the database"""
    from app.models.database import SearchDocument
    from sqlalchemy import select
    
    # Create a simple document
    doc = SearchDocument(
        entity_id="test-123",
        entity_type="items",
        title="Test Item",
        content="Test Content",
        metadata_={"key": "value"}
    )
    
    test_db.add(doc)
    await test_db.commit()
    await test_db.refresh(doc)
    
    # Query it back
    result = await test_db.execute(
        select(SearchDocument).where(SearchDocument.entity_id == "test-123")
    )
    retrieved = result.scalar_one_or_none()
    
    assert retrieved is not None
    assert retrieved.title == "Test Item"
    assert retrieved.content == "Test Content"
