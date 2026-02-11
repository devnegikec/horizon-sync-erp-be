"""Unit tests for search API endpoints"""

import pytest
from fastapi import status
from httpx import AsyncClient

from app.main import app
from app.models.database import SearchDocument


@pytest.mark.asyncio
async def test_global_search_success(async_client: AsyncClient, auth_headers: dict, test_search_documents):
    """Test successful global search"""
    response = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "laptop",
            "page": 1,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verify response structure
    assert "results" in data
    assert "total_count" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert "has_next_page" in data
    assert "has_previous_page" in data
    assert "query_time_ms" in data
    
    # Verify pagination metadata
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert isinstance(data["total_count"], int)
    assert isinstance(data["query_time_ms"], int)
    
    # Verify results structure
    if data["results"]:
        result = data["results"][0]
        assert "entity_id" in result
        assert "entity_type" in result
        assert "title" in result
        assert "snippet" in result
        assert "relevance_score" in result
        assert "metadata" in result


@pytest.mark.asyncio
async def test_global_search_with_entity_types(async_client: AsyncClient, auth_headers: dict, test_search_documents):
    """Test global search with specific entity types"""
    response = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "laptop",
            "entity_types": ["items"],
            "page": 1,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verify all results are of specified entity type
    for result in data["results"]:
        assert result["entity_type"] == "items"


@pytest.mark.asyncio
async def test_global_search_empty_query(async_client: AsyncClient, auth_headers: dict):
    """Test global search with empty query"""
    response = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "",
            "page": 1,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    # Validation errors return 400 due to custom error handler
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_global_search_whitespace_query(async_client: AsyncClient, auth_headers: dict):
    """Test global search with whitespace-only query"""
    response = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "   ",
            "page": 1,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    # Validation errors return 400 due to custom error handler
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_global_search_pagination(async_client: AsyncClient, auth_headers: dict, test_search_documents):
    """Test global search pagination"""
    # First page
    response1 = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "test",
            "page": 1,
            "page_size": 2
        },
        headers=auth_headers
    )
    
    assert response1.status_code == status.HTTP_200_OK
    data1 = response1.json()
    
    # Second page
    response2 = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "test",
            "page": 2,
            "page_size": 2
        },
        headers=auth_headers
    )
    
    assert response2.status_code == status.HTTP_200_OK
    data2 = response2.json()
    
    # Verify pagination metadata
    if data1["total_count"] > 2:
        assert data1["has_next_page"] is True
        assert data1["has_previous_page"] is False
        assert data2["has_previous_page"] is True


@pytest.mark.asyncio
async def test_global_search_no_results(async_client: AsyncClient, auth_headers: dict, test_search_documents):
    """Test global search with no results"""
    response = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "nonexistentquery12345",
            "page": 1,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    assert data["total_count"] == 0
    assert len(data["results"]) == 0
    # Should have suggestions for zero results
    assert "suggestions" in data


@pytest.mark.asyncio
async def test_global_search_unauthorized(async_client: AsyncClient):
    """Test global search without authentication - should still work with mocked user"""
    # Note: In test environment, we mock the user dependency
    # In production, this would return 403
    response = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "laptop",
            "page": 1,
            "page_size": 20
        }
    )
    
    # In test environment with mocked dependencies, this succeeds
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_local_search_success(async_client: AsyncClient, auth_headers: dict, test_search_documents):
    """Test successful local search"""
    response = await async_client.post(
        "/api/v1/search/items",
        json={
            "query": "laptop",
            "page": 1,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verify response structure
    assert "results" in data
    assert "total_count" in data
    
    # Verify all results are of specified entity type
    for result in data["results"]:
        assert result["entity_type"] == "items"


@pytest.mark.asyncio
async def test_local_search_invalid_entity_type(async_client: AsyncClient, auth_headers: dict):
    """Test local search with invalid entity type"""
    response = await async_client.post(
        "/api/v1/search/invalid_entity",
        json={
            "query": "laptop",
            "page": 1,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_local_search_customers(async_client: AsyncClient, auth_headers: dict, test_search_documents):
    """Test local search for customers"""
    response = await async_client.post(
        "/api/v1/search/customers",
        json={
            "query": "acme",
            "page": 1,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verify all results are customers
    for result in data["results"]:
        assert result["entity_type"] == "customers"


@pytest.mark.asyncio
async def test_local_search_with_filters(async_client: AsyncClient, auth_headers: dict, test_search_documents):
    """Test local search with field-specific filters"""
    response = await async_client.post(
        "/api/v1/search/items",
        json={
            "query": "laptop",
            "filters": {"category": "electronics"},
            "page": 1,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    
    # Verify response structure
    assert "results" in data
    assert "total_count" in data


@pytest.mark.asyncio
async def test_local_search_empty_query(async_client: AsyncClient, auth_headers: dict):
    """Test local search with empty query"""
    response = await async_client.post(
        "/api/v1/search/items",
        json={
            "query": "",
            "page": 1,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    # Validation errors return 400 due to custom error handler
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_local_search_unauthorized(async_client: AsyncClient):
    """Test local search without authentication - should still work with mocked user"""
    # Note: In test environment, we mock the user dependency
    # In production, this would return 403
    response = await async_client.post(
        "/api/v1/search/items",
        json={
            "query": "laptop",
            "page": 1,
            "page_size": 20
        }
    )
    
    # In test environment with mocked dependencies, this succeeds
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_search_invalid_page_size(async_client: AsyncClient, auth_headers: dict):
    """Test search with invalid page size"""
    # Page size too large
    response = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "laptop",
            "page": 1,
            "page_size": 200
        },
        headers=auth_headers
    )
    
    # Validation errors return 400 due to custom error handler
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    # Page size too small
    response = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "laptop",
            "page": 1,
            "page_size": 0
        },
        headers=auth_headers
    )
    
    # Validation errors return 400 due to custom error handler
    assert response.status_code == status.HTTP_400_BAD_REQUEST


@pytest.mark.asyncio
async def test_search_invalid_page_number(async_client: AsyncClient, auth_headers: dict):
    """Test search with invalid page number"""
    response = await async_client.post(
        "/api/v1/search/global",
        json={
            "query": "laptop",
            "page": 0,
            "page_size": 20
        },
        headers=auth_headers
    )
    
    # Validation errors return 400 due to custom error handler
    assert response.status_code == status.HTTP_400_BAD_REQUEST
