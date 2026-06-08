"""Typed HTTP client for identity-service internal APIs.

Handles machine-to-machine token acquisition using the OAuth2
client-credentials flow. The token is cached in memory and refreshed
automatically when it expires or core-service returns 401.
"""

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class IdentityServiceClient:
    """Async client for identity-service M2M token endpoint."""

    def __init__(self):
        self.base_url = settings.IDENTITY_SERVICE_URL.rstrip("/")
        self.timeout = settings.IDENTITY_SERVICE_TIMEOUT
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def get_service_token(self) -> str:
        """Obtain a machine-to-machine JWT via client-credentials.

        Returns:
            The access_token string from identity-service.

        Raises:
            httpx.HTTPStatusError: If identity-service rejects the credentials.
        """
        client = await self._get_client()
        url = f"{self.base_url}/api/v1/identity/auth/token"
        payload = {
            "grant_type": "client_credentials",
            "client_id": settings.SERVICE_CLIENT_ID,
            "client_secret": settings.SERVICE_CLIENT_SECRET,
        }
        logger.debug("Requesting service token from identity-service")
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
        token = data.get("access_token")
        if not token:
            raise ValueError("identity-service returned empty access_token")
        logger.debug("Service token acquired successfully")
        return token


# Singleton
identity_client = IdentityServiceClient()
