"""HTTP client for communicating with Core Service."""

import httpx
import asyncio
from uuid import UUID
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class CoreServiceClient:
    """HTTP client for communicating with Core Service.
    
    This client handles service-to-service communication for triggering
    default chart of accounts creation in the Core Service when organizations
    are registered in the Identity Service.
    """
    
    def __init__(self, base_url: str, timeout: int = 10):
        """Initialize the Core Service client.
        
        Args:
            base_url: Base URL of the Core Service (e.g., "http://core-service:8000")
            timeout: Request timeout in seconds (default: 10)
        """
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
    
    async def create_default_chart_of_accounts(
        self,
        organization_id: UUID,
        currency: str,
        created_by: str
    ) -> dict:
        """Trigger default chart of accounts creation in Core Service.
        
        Makes a POST request to the Core Service to create a standard set of
        default GL accounts and account mappings for a newly registered organization.
        
        Args:
            organization_id: UUID of the organization
            currency: ISO currency code (e.g., "USD", "EUR")
            created_by: User identifier who created the organization
            
        Returns:
            dict: Response from Core Service with the following structure:
                {
                    "success": bool,
                    "organization_id": str,
                    "accounts_created": int,
                    "mappings_created": int,
                    "message": str
                }
            
        Raises:
            httpx.RequestError: If the request fails due to connection issues
            httpx.HTTPStatusError: If the response status code indicates an error
        """
        url = f"{self.base_url}/api/v1/setup/default-chart-of-accounts"
        
        payload = {
            "organization_id": str(organization_id),
            "currency": currency,
            "created_by": created_by
        }
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return response.json()
    
    async def create_with_retry(
        self,
        organization_id: UUID,
        currency: str,
        created_by: str,
        max_retries: int = 3
    ) -> Optional[dict]:
        """Attempt to create default chart of accounts with exponential backoff retry.
        
        This method wraps create_default_chart_of_accounts with retry logic to handle
        transient failures when communicating with the Core Service. It uses exponential
        backoff between retries: 1s, 2s, 4s.
        
        Args:
            organization_id: UUID of the organization
            currency: ISO currency code (e.g., "USD", "EUR")
            created_by: User identifier who created the organization
            max_retries: Maximum number of retry attempts (default: 3)
            
        Returns:
            dict: Response from Core Service if successful, None if all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = await self.create_default_chart_of_accounts(
                    organization_id=organization_id,
                    currency=currency,
                    created_by=created_by
                )
                
                if attempt > 0:
                    logger.info(
                        f"Chart creation succeeded on attempt {attempt + 1}",
                        extra={
                            "organization_id": str(organization_id),
                            "attempt": attempt + 1,
                            "event": "chart_creation_retry_success"
                        }
                    )
                
                return response
                
            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # 1s, 2s, 4s
                    logger.warning(
                        f"Chart creation attempt {attempt + 1} failed, retrying in {wait_time}s",
                        extra={
                            "organization_id": str(organization_id),
                            "attempt": attempt + 1,
                            "wait_time": wait_time,
                            "error": str(e),
                            "event": "chart_creation_retry_attempt"
                        }
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"All {max_retries} chart creation attempts failed",
                        extra={
                            "organization_id": str(organization_id),
                            "max_retries": max_retries,
                            "error": str(e),
                            "event": "chart_creation_retry_exhausted"
                        }
                    )
                    return None
            
            except httpx.HTTPStatusError as e:
                # Don't retry on HTTP errors (4xx, 5xx) - these are not transient
                logger.error(
                    f"Chart creation failed with HTTP error on attempt {attempt + 1}",
                    extra={
                        "organization_id": str(organization_id),
                        "attempt": attempt + 1,
                        "status_code": e.response.status_code,
                        "error": str(e),
                        "event": "chart_creation_http_error"
                    }
                )
                return None
        
        return None
