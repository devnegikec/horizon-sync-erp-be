"""HTTP client for communicating with Core Service."""

import asyncio
import logging
from uuid import UUID

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class CoreServiceClient:
    """HTTP client for communicating with Core Service.

    Handles service-to-service communication for:
    - Triggering default chart of accounts creation
    - Seeding default master data (currency, UOMs, tax templates, item groups)
    """

    def __init__(self, base_url: str, timeout: int = 10):
        """Initialize the Core Service client.

        Args:
            base_url: Base URL of the Core Service (e.g., "http://core-service:8000")
            timeout: Request timeout in seconds (default: 10)
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _internal_headers(self) -> dict:
        """Shared-secret header required by core-service internal endpoints."""
        return {"X-Internal-Secret": settings.core_service_secret}

    async def assign_user_to_warehouse(
        self,
        user_id: UUID,
        organization_id: UUID,
        warehouse_id: UUID,
        role: str = "operator",
        is_primary: bool = False,
    ) -> dict:
        """Create a warehouse-user assignment in Core Service.

        Calls POST /api/v1/internal/warehouse-users on the Core Service to assign
        a user to a specific warehouse with a given operational role.
        This is a service-to-service endpoint that does not require user auth.
        Idempotent: an existing active assignment for the same user+warehouse is
        updated rather than duplicated.

        Args:
            user_id: UUID of the user to assign
            organization_id: UUID of the organization
            warehouse_id: UUID of the warehouse
            role: Warehouse role (supervisor, manager, operator, coordinator)
            is_primary: If True the user sees every warehouse (mother warehouse)

        Returns:
            dict: Response from Core Service

        Raises:
            httpx.RequestError: If the request fails due to connection issues
            httpx.HTTPStatusError: If the response status code indicates an error
        """
        url = f"{self.base_url}/api/v1/internal/warehouse-users"
        payload = {
            "user_id": str(user_id),
            "organization_id": str(organization_id),
            "warehouse_id": str(warehouse_id),
            "role": role,
            "is_primary": is_primary,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url, json=payload, headers=self._internal_headers()
            )
            response.raise_for_status()
            return response.json()

    async def get_warehouse_assignments(
        self,
        organization_id: UUID | None = None,
        user_ids: list[UUID] | None = None,
        warehouse_id: UUID | None = None,
        is_active: bool = True,
    ) -> list[dict]:
        """Read warehouse<->user assignments from Core Service.

        Calls GET /api/v1/internal/warehouse-users. The ``warehouse_users`` table
        lives in the Core Service database, so this is the only supported way for
        the Identity Service to read a worker's assigned warehouses.

        Args:
            organization_id: UUID of the organization (optional; required by the
                endpoint only when the caller has an organization scope)
            user_ids: Optional list of user UUIDs to restrict the result to
            warehouse_id: Optional warehouse UUID to restrict the result to
            is_active: Filter on the assignment's is_active flag

        Returns:
            list[dict]: Assignments with user_id, warehouse_id, role,
            is_primary and is_active. Ordered primary-first.

        Raises:
            httpx.RequestError: If the request fails due to connection issues
            httpx.HTTPStatusError: If the response status code indicates an error
        """
        url = f"{self.base_url}/api/v1/internal/warehouse-users"
        params: dict[str, str] = {"is_active": str(is_active).lower()}
        if organization_id:
            params["organization_id"] = str(organization_id)
        if user_ids:
            params["user_ids"] = ",".join(str(u) for u in user_ids)
        if warehouse_id:
            params["warehouse_id"] = str(warehouse_id)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(
                url, params=params, headers=self._internal_headers()
            )
            response.raise_for_status()
            return response.json().get("users", [])

    # ------------------------------------------------------------------
    # Chart of Accounts
    # ------------------------------------------------------------------

    async def create_default_chart_of_accounts(
        self,
        organization_id: UUID,
        currency: str,
        created_by: str,
    ) -> dict:
        """Trigger default chart of accounts creation in Core Service.

        Args:
            organization_id: UUID of the organization
            currency: ISO currency code (e.g., "USD", "EUR")
            created_by: User identifier who created the organization

        Returns:
            dict: Response from Core Service

        Raises:
            httpx.RequestError: If the request fails due to connection issues
            httpx.HTTPStatusError: If the response status code indicates an error
        """
        url = f"{self.base_url}/api/v1/setup/default-chart-of-accounts"
        payload = {
            "organization_id": str(organization_id),
            "currency": currency,
            "created_by": created_by,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url, json=payload, headers=self._internal_headers()
            )
            response.raise_for_status()
            return response.json()

    async def create_with_retry(
        self,
        organization_id: UUID,
        currency: str,
        created_by: str,
        max_retries: int = 3,
    ) -> dict | None:
        """Attempt to create default chart of accounts with exponential backoff retry.

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
                    created_by=created_by,
                )
                if attempt > 0:
                    logger.info(
                        f"Chart creation succeeded on attempt {attempt + 1}",
                        extra={
                            "organization_id": str(organization_id),
                            "attempt": attempt + 1,
                            "event": "chart_creation_retry_success",
                        },
                    )
                return response

            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # 1s, 2s, 4s
                    logger.warning(
                        f"Chart creation attempt {attempt + 1} failed, retrying in {wait_time}s",
                        extra={
                            "organization_id": str(organization_id),
                            "attempt": attempt + 1,
                            "wait_time": wait_time,
                            "error": str(e),
                            "event": "chart_creation_retry_attempt",
                        },
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"All {max_retries} chart creation attempts failed",
                        extra={
                            "organization_id": str(organization_id),
                            "max_retries": max_retries,
                            "error": str(e),
                            "event": "chart_creation_retry_exhausted",
                        },
                    )
                    return None

            except httpx.HTTPStatusError as e:
                # Don't retry on HTTP errors (4xx, 5xx) — not transient
                logger.error(
                    f"Chart creation failed with HTTP error on attempt {attempt + 1}",
                    extra={
                        "organization_id": str(organization_id),
                        "attempt": attempt + 1,
                        "status_code": e.response.status_code,
                        "error": str(e),
                        "event": "chart_creation_http_error",
                    },
                )
                return None

        return None

    # ------------------------------------------------------------------
    # Organization Defaults (currency, UOMs, tax templates, item groups)
    # ------------------------------------------------------------------

    async def seed_organization_defaults(
        self,
        organization_id: UUID,
        base_currency: str,
        created_by: str,
    ) -> dict:
        """Seed default master data for a newly created organization.

        Calls POST /api/v1/setup/organization-defaults on the Core Service to
        create the base currency, standard UOMs, default tax templates, and
        default item group hierarchy.

        Args:
            organization_id: UUID of the organization
            base_currency: ISO currency code (e.g., "USD")
            created_by: UUID string of the user who created the organization

        Returns:
            dict: Response from Core Service with seeding summary

        Raises:
            httpx.RequestError: If the request fails due to connection issues
            httpx.HTTPStatusError: If the response status code indicates an error
        """
        url = f"{self.base_url}/api/v1/setup/organization-defaults"
        payload = {
            "organization_id": str(organization_id),
            "base_currency": base_currency,
            "created_by": created_by,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url, json=payload, headers=self._internal_headers()
            )
            response.raise_for_status()
            return response.json()

    async def seed_organization_defaults_with_retry(
        self,
        organization_id: UUID,
        base_currency: str,
        created_by: str,
        max_retries: int = 3,
    ) -> dict | None:
        """Seed organization defaults with exponential backoff retry.

        Args:
            organization_id: UUID of the organization
            base_currency: ISO currency code (e.g., "USD")
            created_by: UUID string of the user who created the organization
            max_retries: Maximum number of retry attempts (default: 3)

        Returns:
            dict: Response from Core Service if successful, None if all retries fail
        """
        for attempt in range(max_retries):
            try:
                response = await self.seed_organization_defaults(
                    organization_id=organization_id,
                    base_currency=base_currency,
                    created_by=created_by,
                )
                if attempt > 0:
                    logger.info(
                        f"Org defaults seed succeeded on attempt {attempt + 1}",
                        extra={
                            "organization_id": str(organization_id),
                            "attempt": attempt + 1,
                            "event": "org_defaults_seed_retry_success",
                        },
                    )
                return response

            except httpx.RequestError as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Org defaults seed attempt {attempt + 1} failed, retrying in {wait_time}s",
                        extra={
                            "organization_id": str(organization_id),
                            "attempt": attempt + 1,
                            "wait_time": wait_time,
                            "error": str(e),
                            "event": "org_defaults_seed_retry_attempt",
                        },
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        f"All {max_retries} org defaults seed attempts failed",
                        extra={
                            "organization_id": str(organization_id),
                            "max_retries": max_retries,
                            "error": str(e),
                            "event": "org_defaults_seed_retry_exhausted",
                        },
                    )
                    return None

            except httpx.HTTPStatusError as e:
                logger.error(
                    f"Org defaults seed failed with HTTP error on attempt {attempt + 1}",
                    extra={
                        "organization_id": str(organization_id),
                        "attempt": attempt + 1,
                        "status_code": e.response.status_code,
                        "error": str(e),
                        "event": "org_defaults_seed_http_error",
                    },
                )
                return None

        return None

    # ------------------------------------------------------------------
    # Feature flags (module gating for role/permission responses)
    # ------------------------------------------------------------------

    async def list_global_feature_flags(self) -> dict[str, bool] | None:
        """Fetch every GLOBAL feature flag from the Core Service.

        Calls GET /api/v1/internal/feature-flags (protected by the shared
        ``X-Internal-Secret`` header) and returns a ``{name: enabled}`` map.

        Returns:
            dict: Flag name → enabled boolean, or ``None`` on any error. The
            ``None`` sentinel lets callers distinguish a transport failure
            (fail open) from a successful empty listing.
        """
        url = f"{self.base_url}/api/v1/internal/feature-flags"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=self._internal_headers())
                response.raise_for_status()
                payload = response.json()
            return {
                item["name"]: bool(item.get("enabled", False))
                for item in payload.get("flags", [])
                if isinstance(item, dict) and item.get("name")
            }
        except (httpx.RequestError, httpx.HTTPStatusError, ValueError) as e:
            logger.warning(
                "Failed to fetch GLOBAL feature flags from Core Service: %s",
                e,
                extra={"event": "feature_flags_fetch_error"},
            )
            return None
