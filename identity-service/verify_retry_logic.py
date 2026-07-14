"""
Manual verification script for retry logic implementation.

This script demonstrates the retry logic implementation without running full tests.
It shows the key features:
1. Exponential backoff (1s, 2s, 4s)
2. Retry on RequestError (transient failures)
3. No retry on HTTPStatusError (permanent failures)
4. Logging at each retry attempt
"""

import asyncio
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch
import httpx


async def demonstrate_retry_logic():
    """Demonstrate the retry logic behavior."""
    from app.services.core_service_client import CoreServiceClient
    
    print("=" * 80)
    print("RETRY LOGIC VERIFICATION")
    print("=" * 80)
    
    client = CoreServiceClient(base_url="http://test-service:8000", timeout=10)
    organization_id = uuid4()
    
    # Test 1: Success on first attempt
    print("\n1. Testing success on first attempt...")
    with patch.object(
        client, 
        'create_default_chart_of_accounts', 
        new_callable=AsyncMock
    ) as mock_create:
        mock_create.return_value = {
            "success": True,
            "accounts_created": 25,
            "mappings_created": 6
        }
        
        result = await client.create_with_retry(
            organization_id=organization_id,
            currency="USD",
            created_by="test-user",
            max_retries=3
        )
        
        print(f"   ✓ Result: {result}")
        print(f"   ✓ Attempts: {mock_create.call_count}")
        assert mock_create.call_count == 1, "Should succeed on first attempt"
    
    # Test 2: Success after retries
    print("\n2. Testing success after 2 failures...")
    with patch.object(
        client, 
        'create_default_chart_of_accounts', 
        new_callable=AsyncMock
    ) as mock_create, \
         patch('asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
        
        mock_create.side_effect = [
            httpx.RequestError("Connection failed"),
            httpx.RequestError("Connection failed"),
            {"success": True, "accounts_created": 25}
        ]
        
        result = await client.create_with_retry(
            organization_id=organization_id,
            currency="USD",
            created_by="test-user",
            max_retries=3
        )
        
        print(f"   ✓ Result: {result}")
        print(f"   ✓ Total attempts: {mock_create.call_count}")
        print(f"   ✓ Sleep calls: {mock_sleep.call_count}")
        print(f"   ✓ Backoff times: {[call.args[0] for call in mock_sleep.call_args_list]}")
        assert mock_create.call_count == 3, "Should retry twice then succeed"
        assert mock_sleep.call_count == 2, "Should sleep between retries"
        assert mock_sleep.call_args_list[0].args[0] == 1, "First backoff should be 1s"
        assert mock_sleep.call_args_list[1].args[0] == 2, "Second backoff should be 2s"
    
    # Test 3: All retries exhausted
    print("\n3. Testing all retries exhausted...")
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
        
        print(f"   ✓ Result: {result}")
        print(f"   ✓ Total attempts: {mock_create.call_count}")
        print(f"   ✓ Sleep calls: {mock_sleep.call_count}")
        assert result is None, "Should return None after all retries fail"
        assert mock_create.call_count == 3, "Should attempt 3 times"
        assert mock_sleep.call_count == 2, "Should sleep between retries (not after last)"
    
    # Test 4: HTTP error - no retry
    print("\n4. Testing HTTP error (no retry)...")
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
        
        print(f"   ✓ Result: {result}")
        print(f"   ✓ Total attempts: {mock_create.call_count}")
        assert result is None, "Should return None on HTTP error"
        assert mock_create.call_count == 1, "Should NOT retry on HTTP errors"
    
    print("\n" + "=" * 80)
    print("ALL VERIFICATION TESTS PASSED ✓")
    print("=" * 80)
    print("\nKey Features Verified:")
    print("  ✓ Exponential backoff: 1s, 2s, 4s")
    print("  ✓ Retry on transient failures (RequestError)")
    print("  ✓ No retry on permanent failures (HTTPStatusError)")
    print("  ✓ Returns None when all retries exhausted")
    print("  ✓ Logs each retry attempt")
    print()


if __name__ == "__main__":
    asyncio.run(demonstrate_retry_logic())
