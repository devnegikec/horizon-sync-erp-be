"""Typed HTTP client for core-service internal APIs.

Concept: ai-service needs to fetch WMS data (stock, ASN, users, locations)
from core-service. Instead of raw `requests.get()` everywhere, we build a
small typed client that:
  1. Knows the base URL and timeout
  2. Attaches the service-to-service JWT for auth (acquired from identity-service)
  3. Returns raw dicts that MCP tool handlers normalize

This client is used by the MCP tool handlers in Step 4.
"""

import logging

import httpx

from app.config import settings
from app.clients.identity_service import identity_client

logger = logging.getLogger(__name__)


class CoreServiceClient:
    """Async HTTP client for core-service with service-token auth."""

    def __init__(self):
        self.base_url = settings.CORE_SERVICE_URL.rstrip("/")
        self.timeout = settings.CORE_SERVICE_TIMEOUT
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _get_auth_headers(self) -> dict[str, str]:
        """Fetch a service token from identity-service and return Auth header."""
        token = await identity_client.get_service_token()
        return {"Authorization": f"Bearer {token}"}

    async def _get(self, path: str, params: dict | None = None) -> dict:
        """Internal GET helper with auth + error handling."""
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        headers = await self._get_auth_headers()
        logger.debug("core-service GET %s params=%s", url, params)
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    async def get_stock(
        self, warehouse_id: str, item_id: str | None = None, bin_id: str | None = None
    ) -> dict:
        """Fetch stock levels from core-service.

        Maps to: GET /api/v1/stock-levels?warehouse_id=...&item_id=...
        """
        params: dict = {"warehouse_id": warehouse_id}
        if item_id:
            params["item_id"] = item_id
        # bin_id filter is not exposed on the stock-levels list endpoint;
        # we pass it through if the endpoint ever supports it.
        if bin_id:
            params["bin_id"] = bin_id
        return await self._get("/api/v1/stock-levels", params=params)

    async def get_asn_orders(
        self, warehouse_id: str, status: str | None = None, limit: int = 20
    ) -> dict:
        """Fetch ASN orders from core-service.

        Maps to: GET /api/v1/asn-orders?warehouse_id=...&status=...&page_size=...
        """
        params: dict = {"warehouse_id": warehouse_id, "page_size": limit}
        if status:
            params["status"] = status
        return await self._get("/api/v1/asn-orders", params=params)

    async def get_asn_order(self, asn_order_id: str) -> dict:
        """Fetch a single ASN order from core-service.

        Maps to: GET /api/v1/asn-orders/{asn_order_id}
        """
        return await self._get(f"/api/v1/asn-orders/{asn_order_id}")

    async def get_users(self, warehouse_id: str, role: str | None = None) -> dict:
        """Fetch warehouse users from core-service.

        Maps to: GET /api/v1/warehouse-users?warehouse_id=...
        Note: role filter is not yet supported by the endpoint; client-side
        filtering will be applied in the MCP tool handler if needed.
        """
        params: dict = {"warehouse_id": warehouse_id}
        return await self._get("/api/v1/warehouse-users", params=params)

    async def get_locations(
        self, warehouse_id: str, type_: str | None = None
    ) -> dict:
        """Fetch warehouse locations from core-service.

        Maps to: GET /api/v1/warehouse-locations?warehouse_id=...&location_type=...
        """
        params: dict = {"warehouse_id": warehouse_id}
        if type_:
            params["location_type"] = type_
        return await self._get("/api/v1/warehouse-locations", params=params)

    async def get_put_away(self, put_away_list_id: str) -> dict:
        """Fetch a put-away task from core-service.

        Maps to: GET /api/v1/put-away/{put_away_list_id}
        """
        return await self._get(f"/api/v1/put-away/{put_away_list_id}")

    # ── Ingestion helpers ──────────────────────────────────────────────

    async def _post(self, path: str, json_data: dict | None = None) -> dict:
        """Internal POST helper with auth + error handling."""
        client = await self._get_client()
        url = f"{self.base_url}{path}"
        headers = await self._get_auth_headers()
        logger.debug("core-service POST %s", url)
        response = await client.post(url, headers=headers, json=json_data)
        response.raise_for_status()
        return response.json()

    async def search_suppliers(
        self, name: str | None = None, organization_id: str | None = None
    ) -> list[dict]:
        """Search suppliers by name. Returns list of supplier dicts."""
        params: dict = {}
        if name:
            params["name"] = name
        if organization_id:
            params["organization_id"] = str(organization_id)
        try:
            result = await self._get("/api/v1/suppliers", params=params)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return result.get("items", result.get("data", []))
            return []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise

    async def search_items(
        self, sku: str | None = None, organization_id: str | None = None
    ) -> list[dict]:
        """Search items by SKU. Returns list of item dicts."""
        params: dict = {}
        if sku:
            params["sku"] = sku
        if organization_id:
            params["organization_id"] = str(organization_id)
        try:
            result = await self._get("/api/v1/items", params=params)
            if isinstance(result, list):
                return result
            if isinstance(result, dict):
                return result.get("items", result.get("data", []))
            return []
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return []
            raise

    async def create_asn_draft(self, payload: dict) -> dict:
        """Create a draft ASN order in core-service.

        Maps to: POST /api/v1/asn-orders
        Expects payload matching core-service AsnOrderCreate schema.
        """
        return await self._post("/api/v1/asn-orders", json_data=payload)

    async def find_purchase_order(
        self,
        po_number: str | None = None,
        supplier_id: str | None = None,
        organization_id: str | None = None,
    ) -> dict | None:
        """Find an open purchase order by PO number and supplier.

        Returns the PO dict or None if not found / not open.
        """
        params: dict = {"status": "open"}
        if po_number:
            params["po_number"] = po_number
        if supplier_id:
            params["supplier_id"] = str(supplier_id)
        if organization_id:
            params["organization_id"] = str(organization_id)
        try:
            result = await self._get("/api/v1/procurement/purchase-orders", params=params)
            if isinstance(result, list) and result:
                return result[0]
            if isinstance(result, dict):
                items = result.get("items", result.get("data", []))
                return items[0] if items else None
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise

    async def find_asn_by_number(
        self,
        asn_number: str,
        supplier_id: str | None = None,
        organization_id: str | None = None,
    ) -> dict | None:
        """Check if an ASN with this number already exists.

        Returns the existing ASN dict or None.
        """
        params: dict = {"asn_number": asn_number}
        if supplier_id:
            params["supplier_id"] = str(supplier_id)
        if organization_id:
            params["organization_id"] = str(organization_id)
        try:
            result = await self._get("/api/v1/asn-orders", params=params)
            if isinstance(result, list) and result:
                return result[0]
            if isinstance(result, dict):
                items = result.get("items", result.get("data", []))
                return items[0] if items else None
            return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise


# Singleton
core_client = CoreServiceClient()
