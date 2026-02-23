"""Client for communicating with Identity Service to update organization settings"""

import logging
from typing import Any
from uuid import UUID

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class OrganizationClient:
    """Client for interacting with Identity Service organization endpoints"""

    def __init__(self):
        self.base_url = settings.identity_service_url.rstrip("/")
        self.timeout = 10.0

    async def update_naming_series(
        self,
        organization_id: UUID,
        document_type: str,
        current_number: int,
        auth_token: str,
    ) -> bool:
        """
        Update the naming series current_number for a specific document type.

        Args:
            organization_id: Organization UUID
            document_type: Document type (e.g., 'quotation', 'sales_order', 'invoice')
            current_number: New current number to set
            auth_token: JWT token for authentication

        Returns:
            True if update was successful, False otherwise

        Example:
            await client.update_naming_series(
                organization_id=UUID("..."),
                document_type="quotation",
                current_number=36,
                auth_token="Bearer ..."
            )
        """
        url = f"{self.base_url}/api/v1/identity/organizations/{organization_id}"

        # Prepare the payload to update naming_series
        payload = {"naming_series": {document_type: {"current_number": current_number}}}

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.patch(url, json=payload, headers=headers)

                if response.status_code == 200:
                    logger.info(
                        f"Successfully updated naming series for {document_type} "
                        f"in organization {organization_id} to {current_number}"
                    )
                    return True
                else:
                    logger.error(
                        f"Failed to update naming series: {response.status_code} - {response.text}"
                    )
                    return False

        except httpx.TimeoutException:
            logger.error(
                f"Timeout while updating naming series for organization {organization_id}"
            )
            return False
        except httpx.RequestError as e:
            logger.error(f"Request error while updating naming series: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error while updating naming series: {e}")
            return False

    async def get_organization_settings(
        self, organization_id: UUID, auth_token: str
    ) -> dict[str, Any] | None:
        """
        Get organization settings including naming series.

        Args:
            organization_id: Organization UUID
            auth_token: JWT token for authentication

        Returns:
            Organization settings dict or None if failed
        """
        url = f"{self.base_url}/api/v1/identity/organizations/{organization_id}"

        headers = {
            "Authorization": f"Bearer {auth_token}",
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(
                        f"Failed to get organization settings: {response.status_code}"
                    )
                    return None

        except Exception as e:
            logger.error(f"Error getting organization settings: {e}")
            return None


# Global instance
organization_client = OrganizationClient()
