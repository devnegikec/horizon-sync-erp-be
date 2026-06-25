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


async def ensure_warehouse_work_user_role(
    organization_id: UUID,
    auth_token: str,
) -> bool:
    """
    Ensure the warehouse_work_user role exists in the identity service
    for the given organization.  Idempotent — safe to call on every
    warehouse creation.

    Returns True if the role was created or already existed.
    """
    url = (
        f"{settings.identity_service_url.rstrip('/')}"
        f"/api/v1/identity/roles"
    )

    payload = {**_WAREHOUSE_WORK_USER_PAYLOAD, "organization_id": str(organization_id)}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"Authorization": f"Bearer {auth_token}"},
            )

        if response.status_code in (200, 201):
            logger.info(
                "Created warehouse_work_user role for org %s", organization_id
            )
            return True

        if response.status_code == 409:
            # Role already exists — this is expected on subsequent warehouse creations
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

    except httpx.RequestError as exc:
        logger.error(
            "Failed to contact identity service for role seeding: %s", exc
        )
        return False
