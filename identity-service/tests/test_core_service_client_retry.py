"""Tests for CoreServiceClient retry logic."""

import pytest
import httpx
from uuid import uuid4
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.core_service_client import CoreServiceClient


@pytest.mark.asyncio
async def test_create_with_retry_success_first_attempt():
    """Test successful chart creation on first attempt."""
    client = CoreServiceClient(base_url="http://test-service:8000", timeout=10)
    organization_id = uuid4()
    
    expected_response = {
        "success": True,
        "organization_id": str(organization_id),
        "accounts_created": 25,
        "mappings_created": 6,
        "message": "Default chart of accounts created successfully"
    }
    
    with patch.object(
        client, 
        'create_default_chart_of_accounts', 
        new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = expected_response
        
        result = await client.create_with_retry(
            organization_id=organization_id,
            currency="USD",
            created_by="test-user",
            max_retries=3
        )
        
        assert result == expected_response
        assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_create_with_retry_success_after_retries():
    """Test successful chart creation after transient failures."""
    client = CoreServiceClient(base_url="http://test-service:8000", timeout=10)
    organization_id = uuid4()
    
    expected_response = {
        "success": True,
        "organization_id": str(organization_id),
        "accounts_created": 25,
        "mappings_created": 6,
        "message": "Default chart of accounts created successfully"
    }
    
    with patch.object(
        client, 
        'create_default_chart_of_accounts', 
        new_callable=AsyncMock
    ) as mock_create:
        # Fail twice, then succeed
        mock_create.side_effect = [
            httpx.RequestError("Connection failed"),
            httpx.RequestError("Connection failed"),
            expected_response
        ]
        
        result = await client.create_with_retry(
            organization_id=organization_id,
            currency="USD",
            created_by="test-user",
            max_retries=3
        )
        
        assert result == expected_response
        assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_create_with_retry_all_attempts_fail():
    """Test that None is returned when all retry attempts fail."""
    client = CoreServiceClient(base_url="http://test-service:8000", timeout=10)
    organization_id = uuid4()
    
    with patch.object(
        client, 
        'create_default_chart_of_accounts', 
        new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = httpx.RequestError("Connection failed")
        
        result = await client.create_with_retry(
            organization_id=organization_id,
            currency="USD",
            created_by="test-user",
            max_retries=3
        )
        
        assert result is None
        assert mock_create.call_count == 3


@pytest.mark.asyncio
async def test_create_with_retry_http_error_no_retry():
    """Test that HTTP errors (4xx, 5xx) are not retried."""
    client = CoreServiceClient(base_url="http://test-service:8000", timeout=10)
    organization_id = uuid4()
    
    # Create a mock response for HTTPStatusError
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    
    with patch.object(
        client, 
        'create_default_chart_of_accounts', 
        new_callable=AsyncMock
    ) as mock_create:
        mock_create.side_effect = httpx.HTTPStatusError(
            "Server error",
            request=MagicMock(),
            response=mock_response
        )
        
        result = await client.create_with_retry(
            organization_id=organization_id,
            currency="USD",
            created_by="test-user",
            max_retries=3
        )
        
        assert result is None
        # Should only try once, not retry on HTTP errors
        assert mock_create.call_count == 1


@pytest.mark.asyncio
async def test_create_with_retry_exponential_backoff():
    """Test that exponential backoff is applied between retries."""
    client = CoreServiceClient(base_url="http://test-service:8000", timeout=10)
    organization_id = uuid4()
    
    with patch.object(
        client, 
        'create_default_chart_of_accounts', 
        new_callable=AsyncMock
    ) as mock_create, \
         patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        
        mock_create.side_effect = httpx.RequestError("Connection failed")
        
        result = await client.create_with_retry(
            organization_id=organization_id,
            currency="USD",
            created_by="test-user",
            max_retries=3
        )
        
        assert result is None
        assert mock_create.call_count == 3
        
        # Verify exponential backoff: 1s, 2s (no sleep after last attempt)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)  # 2^0 = 1
        mock_sleep.assert_any_call(2)  # 2^1 = 2
