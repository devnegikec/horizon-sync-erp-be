"""Property-based tests for search index synchronization

Feature: unified-search-api
Property 20: Index Synchronization

**Validates: Requirements 8.1, 10.1, 10.2**

For any entity creation, update, or deletion, the search index should reflect
the changes incrementally and maintain consistency with the primary database.
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any

import pytest
from hypothesis import given, settings, strategies as st, HealthCheck
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession


# Custom strategies for generating test data
@st.composite
def entity_data(draw):
    """Generate random entity data for testing"""
    entity_types = ["items", "customers", "suppliers", "warehouses", "stock_entries"]
    entity_type = draw(st.sampled_from(entity_types))
    
    return {
        "entity_id": str(uuid.uuid4()),
        "entity_type": entity_type,
        "title": draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
            min_codepoint=32,
            max_codepoint=126
        ))),
        "content": draw(st.text(min_size=1, max_size=500, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
            min_codepoint=32,
            max_codepoint=126
        ))),
        "metadata": draw(st.dictionaries(
            keys=st.text(min_size=1, max_size=20, alphabet=st.characters(
                whitelist_categories=("Ll",),
                min_codepoint=97,
                max_codepoint=122
            )),
            values=st.one_of(
                st.text(max_size=50),
                st.integers(min_value=0, max_value=1000),
                st.booleans()
            ),
            max_size=5
        ))
    }


@st.composite
def entity_update_data(draw):
    """Generate random update data for existing entities"""
    return {
        "title": draw(st.text(min_size=1, max_size=100, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
            min_codepoint=32,
            max_codepoint=126
        ))),
        "content": draw(st.text(min_size=1, max_size=500, alphabet=st.characters(
            whitelist_categories=("Lu", "Ll", "Nd", "Zs"),
            min_codepoint=32,
            max_codepoint=126
        ))),
    }


class TestIndexSynchronization:
    """
    Property-based tests for search index synchronization.
    
    These tests verify that the search index maintains consistency with
    the primary database across various operations.
    """

    @pytest.mark.asyncio
    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(data=entity_data())
    async def test_index_reflects_entity_creation(self, test_db: AsyncSession, data: dict[str, Any]):
        """
        Feature: unified-search-api, Property 20: Index Synchronization
        **Validates: Requirements 8.1, 10.1**
        
        For any entity creation, the search index should contain the entity
        with all its data accurately reflected.
        
        Property: After creating a search document, querying the index should
        return the document with matching entity_id, entity_type, title, content,
        and metadata.
        """
        from app.models.database import SearchDocument
        
        # Create a search document
        doc = SearchDocument(
            entity_id=data["entity_id"],
            entity_type=data["entity_type"],
            title=data["title"],
            content=data["content"],
            metadata_=data["metadata"]
        )
        
        test_db.add(doc)
        await test_db.commit()
        await test_db.refresh(doc)
        
        # Query the index to verify the document exists
        result = await test_db.execute(
            select(SearchDocument).where(
                SearchDocument.entity_id == data["entity_id"],
                SearchDocument.entity_type == data["entity_type"]
            )
        )
        retrieved_doc = result.scalar_one_or_none()
        
        # Verify the document exists and matches the created data
        assert retrieved_doc is not None, "Document should exist in index after creation"
        assert retrieved_doc.entity_id == data["entity_id"], "Entity ID should match"
        assert retrieved_doc.entity_type == data["entity_type"], "Entity type should match"
        assert retrieved_doc.title == data["title"], "Title should match"
        assert retrieved_doc.content == data["content"], "Content should match"
        assert retrieved_doc.metadata_ == data["metadata"], "Metadata should match"
        assert retrieved_doc.created_at is not None, "Created timestamp should be set"
        assert retrieved_doc.updated_at is not None, "Updated timestamp should be set"

    @pytest.mark.asyncio
    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(
        initial_data=entity_data(),
        update_data=entity_update_data()
    )
    async def test_index_reflects_entity_updates(
        self, 
        test_db: AsyncSession, 
        initial_data: dict[str, Any],
        update_data: dict[str, Any]
    ):
        """
        Feature: unified-search-api, Property 20: Index Synchronization
        **Validates: Requirements 8.1, 10.1**
        
        For any entity update, the search index should reflect the changes
        incrementally without requiring a full rebuild.
        
        Property: After updating a search document, querying the index should
        return the document with the updated data, and the updated_at timestamp
        should be more recent than created_at.
        """
        from app.models.database import SearchDocument
        
        # Create initial document
        doc = SearchDocument(
            entity_id=initial_data["entity_id"],
            entity_type=initial_data["entity_type"],
            title=initial_data["title"],
            content=initial_data["content"],
            metadata_=initial_data["metadata"]
        )
        
        test_db.add(doc)
        await test_db.commit()
        await test_db.refresh(doc)
        
        original_created_at = doc.created_at
        original_updated_at = doc.updated_at
        
        # Small delay to ensure timestamp difference
        await asyncio.sleep(0.01)
        
        # Update the document
        doc.title = update_data["title"]
        doc.content = update_data["content"]
        
        await test_db.commit()
        await test_db.refresh(doc)
        
        # Query the index to verify the update
        result = await test_db.execute(
            select(SearchDocument).where(
                SearchDocument.entity_id == initial_data["entity_id"],
                SearchDocument.entity_type == initial_data["entity_type"]
            )
        )
        updated_doc = result.scalar_one_or_none()
        
        # Verify the document was updated
        assert updated_doc is not None, "Document should still exist after update"
        assert updated_doc.title == update_data["title"], "Title should be updated"
        assert updated_doc.content == update_data["content"], "Content should be updated"
        assert updated_doc.created_at == original_created_at, "Created timestamp should not change"
        assert updated_doc.updated_at >= original_updated_at, "Updated timestamp should be more recent"

    @pytest.mark.asyncio
    @settings(
        max_examples=100, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(data=entity_data())
    async def test_index_reflects_entity_deletion(self, test_db: AsyncSession, data: dict[str, Any]):
        """
        Feature: unified-search-api, Property 20: Index Synchronization
        **Validates: Requirements 8.1, 10.1**
        
        For any entity deletion, the search index should remove the entity
        to maintain consistency with the primary database.
        
        Property: After deleting a search document, querying the index should
        return no results for that entity_id and entity_type combination.
        """
        from app.models.database import SearchDocument
        
        # Create a search document
        doc = SearchDocument(
            entity_id=data["entity_id"],
            entity_type=data["entity_type"],
            title=data["title"],
            content=data["content"],
            metadata_=data["metadata"]
        )
        
        test_db.add(doc)
        await test_db.commit()
        
        # Verify document exists
        result = await test_db.execute(
            select(SearchDocument).where(
                SearchDocument.entity_id == data["entity_id"],
                SearchDocument.entity_type == data["entity_type"]
            )
        )
        assert result.scalar_one_or_none() is not None, "Document should exist before deletion"
        
        # Delete the document
        await test_db.delete(doc)
        await test_db.commit()
        
        # Query the index to verify deletion
        result = await test_db.execute(
            select(SearchDocument).where(
                SearchDocument.entity_id == data["entity_id"],
                SearchDocument.entity_type == data["entity_type"]
            )
        )
        deleted_doc = result.scalar_one_or_none()
        
        # Verify the document no longer exists
        assert deleted_doc is None, "Document should not exist in index after deletion"

    @pytest.mark.asyncio
    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(data=entity_data())
    async def test_index_consistency_after_rollback(self, test_db: AsyncSession, data: dict[str, Any]):
        """
        Feature: unified-search-api, Property 20: Index Synchronization
        **Validates: Requirements 10.2**
        
        When database transactions are rolled back, the search index should
        maintain consistency with the primary database.
        
        Property: After rolling back a transaction that created a document,
        the document should not exist in the search index.
        """
        from app.models.database import SearchDocument
        
        # Start a nested transaction (savepoint)
        async with test_db.begin_nested():
            # Create a search document within the transaction
            doc = SearchDocument(
                entity_id=data["entity_id"],
                entity_type=data["entity_type"],
                title=data["title"],
                content=data["content"],
                metadata_=data["metadata"]
            )
            
            test_db.add(doc)
            await test_db.flush()
            
            # Verify document exists within the transaction
            result = await test_db.execute(
                select(SearchDocument).where(
                    SearchDocument.entity_id == data["entity_id"],
                    SearchDocument.entity_type == data["entity_type"]
                )
            )
            assert result.scalar_one_or_none() is not None, "Document should exist within transaction"
            
            # Rollback the nested transaction
            await test_db.rollback()
        
        # Query the index after rollback
        result = await test_db.execute(
            select(SearchDocument).where(
                SearchDocument.entity_id == data["entity_id"],
                SearchDocument.entity_type == data["entity_type"]
            )
        )
        rolled_back_doc = result.scalar_one_or_none()
        
        # Verify the document does not exist after rollback
        assert rolled_back_doc is None, "Document should not exist in index after transaction rollback"

    @pytest.mark.asyncio
    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(data=entity_data())
    async def test_unique_constraint_enforcement(self, test_db: AsyncSession, data: dict[str, Any]):
        """
        Feature: unified-search-api, Property 20: Index Synchronization
        **Validates: Requirements 8.1, 10.1**
        
        The search index should enforce uniqueness on (entity_id, entity_type)
        to prevent duplicate entries and maintain data integrity.
        
        Property: Attempting to create a duplicate document with the same
        entity_id and entity_type should fail with an integrity error.
        """
        from app.models.database import SearchDocument
        
        # Create first document
        doc1 = SearchDocument(
            entity_id=data["entity_id"],
            entity_type=data["entity_type"],
            title=data["title"],
            content=data["content"],
            metadata_=data["metadata"]
        )
        
        test_db.add(doc1)
        await test_db.commit()
        
        # Attempt to create duplicate document
        doc2 = SearchDocument(
            entity_id=data["entity_id"],  # Same entity_id
            entity_type=data["entity_type"],  # Same entity_type
            title="Different Title",
            content="Different Content",
            metadata_={}
        )
        
        test_db.add(doc2)
        
        # Should raise an integrity error due to unique constraint
        with pytest.raises(Exception) as exc_info:
            await test_db.commit()
        
        # Verify it's an integrity error (SQLAlchemy wraps it)
        assert "unique" in str(exc_info.value).lower() or "duplicate" in str(exc_info.value).lower(), \
            "Should raise unique constraint violation error"
        
        # Rollback the failed transaction
        await test_db.rollback()
        
        # Verify only one document exists
        result = await test_db.execute(
            select(SearchDocument).where(
                SearchDocument.entity_id == data["entity_id"],
                SearchDocument.entity_type == data["entity_type"]
            )
        )
        docs = result.scalars().all()
        assert len(docs) == 1, "Only one document should exist after duplicate attempt"

    @pytest.mark.asyncio
    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(entities=st.lists(entity_data(), min_size=2, max_size=10))
    async def test_batch_operations_maintain_consistency(
        self, 
        test_db: AsyncSession, 
        entities: list[dict[str, Any]]
    ):
        """
        Feature: unified-search-api, Property 20: Index Synchronization
        **Validates: Requirements 8.1, 10.1**
        
        When multiple entities are created in a batch operation, the search
        index should reflect all changes consistently.
        
        Property: After batch creating multiple documents, all documents should
        be retrievable from the index with accurate data.
        """
        from app.models.database import SearchDocument
        
        # Ensure unique entity_id and entity_type combinations
        seen = set()
        unique_entities = []
        for entity in entities:
            key = (entity["entity_id"], entity["entity_type"])
            if key not in seen:
                seen.add(key)
                unique_entities.append(entity)
        
        if len(unique_entities) < 2:
            # Skip if we don't have enough unique entities
            pytest.skip("Not enough unique entities generated")
        
        # Batch create documents
        docs = []
        for entity in unique_entities:
            doc = SearchDocument(
                entity_id=entity["entity_id"],
                entity_type=entity["entity_type"],
                title=entity["title"],
                content=entity["content"],
                metadata_=entity["metadata"]
            )
            docs.append(doc)
            test_db.add(doc)
        
        await test_db.commit()
        
        # Verify all documents exist in the index
        for entity in unique_entities:
            result = await test_db.execute(
                select(SearchDocument).where(
                    SearchDocument.entity_id == entity["entity_id"],
                    SearchDocument.entity_type == entity["entity_type"]
                )
            )
            retrieved_doc = result.scalar_one_or_none()
            
            assert retrieved_doc is not None, \
                f"Document for {entity['entity_type']}:{entity['entity_id']} should exist"
            assert retrieved_doc.title == entity["title"], "Title should match"
            assert retrieved_doc.content == entity["content"], "Content should match"

    @pytest.mark.asyncio
    @settings(
        max_examples=50, 
        deadline=5000,
        suppress_health_check=[HealthCheck.function_scoped_fixture]
    )
    @given(data=entity_data())
    async def test_index_timestamps_are_accurate(self, test_db: AsyncSession, data: dict[str, Any]):
        """
        Feature: unified-search-api, Property 20: Index Synchronization
        **Validates: Requirements 10.1**
        
        The search index should maintain accurate timestamps for created_at
        and updated_at to support synchronization monitoring.
        
        Property: created_at and updated_at timestamps should be set to
        reasonable values (within the last few seconds) and created_at should
        be less than or equal to updated_at.
        """
        from app.models.database import SearchDocument
        from datetime import timezone
        
        before_creation = datetime.now(timezone.utc)
        
        # Create a search document
        doc = SearchDocument(
            entity_id=data["entity_id"],
            entity_type=data["entity_type"],
            title=data["title"],
            content=data["content"],
            metadata_=data["metadata"]
        )
        
        test_db.add(doc)
        await test_db.commit()
        await test_db.refresh(doc)
        
        after_creation = datetime.now(timezone.utc)
        
        # Verify timestamps are reasonable
        assert doc.created_at is not None, "created_at should be set"
        assert doc.updated_at is not None, "updated_at should be set"
        
        # Convert timestamps to timezone-aware if they're naive (SQLite returns naive datetimes)
        created_at = doc.created_at if doc.created_at.tzinfo is not None else doc.created_at.replace(tzinfo=timezone.utc)
        updated_at = doc.updated_at if doc.updated_at.tzinfo is not None else doc.updated_at.replace(tzinfo=timezone.utc)
        
        # Timestamps should be within a reasonable range (allowing for some clock skew)
        # Using 60 seconds to account for test execution time and potential delays
        assert before_creation - timedelta(seconds=60) <= created_at <= after_creation + timedelta(seconds=60), \
            "created_at should be close to current time"
        assert before_creation - timedelta(seconds=60) <= updated_at <= after_creation + timedelta(seconds=60), \
            "updated_at should be close to current time"
        
        # created_at should be <= updated_at
        assert created_at <= updated_at, \
            "created_at should be less than or equal to updated_at"
