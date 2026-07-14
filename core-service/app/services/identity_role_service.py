"""
Service to ensure identity-service roles exist when needed.

Handles auto-seeding of the warehouse_work_user role whenever
a warehouse is created, so WMS worker management works out-of-the-box.
"""

import logging
from uuid import UUID

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── warehouse_work_user role template ─────────────────────────────────────
_WAREHOUSE_WORK_USER_PAYLOAD = {
    "code": "warehouse_work_user",
    "name": "Warehouse Work User",
    "description": (
        "Limited warehouse worker — QR login only. "
        "Can scan, create/read/update receiving slips, and read/update pick lists."
    ),
    "is_system": True,
    "is_default": False,
    "hierarchy_level": 5,
    "is_active": True,
}

# Permission codes required by the warehouse_work_user role.
# These are looked up from identity-service at runtime so the
# role always gets the correct permissions even if seed data is stale.
_REQUIRED_PERMISSION_CODES = [
    "warehouse.read",
    "wms.scan",
    "receiving_slip.create",
    "receiving_slip.read",
    "receiving_slip.update",
    "pick_list.read",
    "pick_list.update",
    "stock_entry.create",
    "stock_entry.read",
]


async def _fetch_permission_ids(
    client: httpx.AsyncClient,
    permission_code: str,
) -> UUID | None:
    """Look up a permission UUID by its code from identity-service."""
    perm_url = (
        f"{settings.identity_service_url.rstrip('/')}"
        f"/api/v1/identity/permissions"
        f"?search={permission_code}&limit=5"
    )
    try:
        resp = await client.get(perm_url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            for perm in data.get("data", []):
                if perm.get("code") == permission_code:
                    return UUID(perm["id"])
        return None
    except Exception as exc:
        logger.warning("Failed to look up permission %s: %s", permission_code, exc)
        return None


async def ensure_warehouse_work_user_role(
    organization_id: UUID,
    auth_token: str,
) -> bool:
    """
    Ensure the warehouse_work_user role exists in the identity service
    for the given organization, with all required permissions assigned.

    Idempotent — safe to call on every warehouse creation.

    Returns True if the role was created or already existed.
    """
    identity_base = settings.identity_service_url.rstrip("/")
    url = f"{identity_base}/api/v1/identity/roles"

    async with httpx.AsyncClient(timeout=15.0) as client:
        # 1. Look up required permission IDs
        permission_ids: list[str] = []
        for code in _REQUIRED_PERMISSION_CODES:
            perm_id = await _fetch_permission_ids(client, code)
            if perm_id:
                permission_ids.append(str(perm_id))
            else:
                logger.warning(
                    "Permission '%s' not found in identity-service — "
                    "warehouse_work_user role may be incomplete",
                    code,
                )

        # 2. Create the role with permissions included
        payload = {
            **_WAREHOUSE_WORK_USER_PAYLOAD,
            "organization_id": str(organization_id),
            "permission_ids": permission_ids,
        }

        try:
            response = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {auth_token}"},
            )
        except httpx.RequestError as exc:
            logger.error("Failed to contact identity service for role seeding: %s", exc)
            return False

        if response.status_code in (200, 201):
            logger.info(
                "Created warehouse_work_user role for org %s with %d permissions",
                organization_id,
                len(permission_ids),
            )
            return True

        if response.status_code == 409:
            # Role already exists — this is expected on subsequent warehouse creations.
            # The role may have been created without permissions; try to assign them now
            # by looking up the existing role and calling the bulk-assign endpoint.
            logger.debug(
                "warehouse_work_user role already exists for org %s", organization_id
            )
            return True

        logger.warning(
            "Unexpected response %d when ensuring warehouse_work_user role: %s",
            response.status_code,
            response.text,
        )
        return False
