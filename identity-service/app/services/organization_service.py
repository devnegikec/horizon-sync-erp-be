"""Organization service with business logic"""

import logging
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateOrganizationSlugException,
    OrganizationNotFoundException,
)
from app.models.base import (
    ActionType,
    OrganizationStatus,
    OrganizationType,
    ResourceType,
)
from app.models.organization import Organization
from app.models.role import Permission, Role, RolePermission, UserOrganizationRole
from app.repositories.organization_repository import OrganizationRepository
from app.services.core_service_client import CoreServiceClient

logger = logging.getLogger(__name__)


class OrganizationService:
    """Service for organization operations."""

    def __init__(
        self, 
        db: Session, 
        core_client: Optional[CoreServiceClient] = None,
        retry_attempts: int = 3
    ):
        self.db = db
        self.repo = OrganizationRepository(db)
        self.core_client = core_client
        self.retry_attempts = retry_attempts

    def create(self, data: dict, owner_id: UUID) -> dict:
        """Create organization; validate slug uniqueness. Sets owner_id and assigns Owner role with *.* to creating user."""
        slug = data.get("slug", "").strip().lower()
        if self.repo.slug_exists(slug):
            raise DuplicateOrganizationSlugException(
                f"Organization with slug '{slug}' already exists"
            )
        payload = dict(data)
        payload["owner_id"] = owner_id
        if "organization_type" in payload and payload["organization_type"]:
            payload["organization_type"] = OrganizationType(
                payload["organization_type"]
            )
        if "status" in payload and payload["status"]:
            payload["status"] = OrganizationStatus(payload["status"])
        org = self.repo.create(payload)

        # Ensure creating user is always assigned as Owner with full access (*.*) in this org
        full_access = self.db.query(Permission).filter(Permission.code == "*.*").first()
        if not full_access:
            # Create *.* permission if missing (e.g. DB seeded before wildcards were added)
            full_access = Permission(
                code="*.*",
                name="Full access (all resources and actions)",
                resource=ResourceType.ALL,
                action=ActionType.MANAGE,
                module="identity",
                is_active=True,
            )
            self.db.add(full_access)
            self.db.flush()

        owner_role = Role(
            organization_id=org.id,
            name="Organization Owner",
            code="owner",
            description="User who created the organization; has full access in this org.",
            is_system=False,
            is_default=False,
            hierarchy_level=100,
            is_active=True,
        )
        self.db.add(owner_role)
        self.db.flush()
        self.db.add(
            RolePermission(
                role_id=owner_role.id,
                permission_id=full_access.id,
            )
        )
        self.db.add(
            UserOrganizationRole(
                user_id=owner_id,
                organization_id=org.id,
                role_id=owner_role.id,
                is_primary=True,
                is_active=True,
                status="active",
                joined_at=datetime.now(UTC),
            )
        )
        self.db.commit()

        # Trigger default chart of accounts creation in Core Service
        if self.core_client:
            self._trigger_chart_creation(org.id, org.base_currency or "USD", str(owner_id))

        return self._to_response(org)

    def get_by_id(self, organization_id: UUID) -> dict:
        """Get organization by ID; raise if not found."""
        org = self.repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundException(
                f"Organization with ID {organization_id} not found"
            )
        return self._to_response(org)

    def list_organizations(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        organization_type: str | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        organization_ids: list[UUID] | None = None,
    ) -> tuple[list[dict], dict]:
        """List organizations with pagination. Returns (items, pagination_meta)."""
        status_enum = None
        if status:
            try:
                status_enum = OrganizationStatus(status)
            except ValueError:
                pass
        type_enum = None
        if organization_type:
            try:
                type_enum = OrganizationType(organization_type)
            except ValueError:
                pass
        page_size = min(page_size, 100)
        items, total = self.repo.list_organizations(
            page=page,
            page_size=page_size,
            status=status_enum,
            organization_type=type_enum,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            organization_ids=organization_ids,
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return [self._to_list_item(o) for o in items], pagination

    def update(self, organization_id: UUID, data: dict) -> dict:
        """Update organization; validate slug if changed."""
        org = self.repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundException(
                f"Organization with ID {organization_id} not found"
            )
        payload = {k: v for k, v in data.items() if v is not None}
        if "slug" in payload:
            if self.repo.slug_exists(payload["slug"], exclude_id=organization_id):
                raise DuplicateOrganizationSlugException(
                    f"Organization with slug '{payload['slug']}' already exists"
                )
        if "status" in payload:
            payload["status"] = OrganizationStatus(payload["status"])
        if "organization_type" in payload:
            payload["organization_type"] = OrganizationType(
                payload["organization_type"]
            )
        updated = self.repo.update(org, payload)
        return self._to_response(updated)

    def delete(self, organization_id: UUID) -> None:
        """Soft delete organization."""
        org = self.repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundException(
                f"Organization with ID {organization_id} not found"
            )
        self.repo.soft_delete(org)

    @staticmethod
    def _to_response(org: Organization) -> dict:
        return {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "display_name": org.display_name,
            "description": org.description,
            "email": org.email,
            "phone": org.phone,
            "website": org.website,
            "address_line1": getattr(org, "address_line1", None),
            "address_line2": getattr(org, "address_line2", None),
            "city": getattr(org, "city", None),
            "state": getattr(org, "state", None),
            "postal_code": getattr(org, "postal_code", None),
            "country": getattr(org, "country", None),
            "logo_url": org.logo_url,
            "organization_type": org.organization_type.value
            if org.organization_type
            else None,
            "industry": org.industry,
            "base_currency": getattr(org, "base_currency", "USD"),
            "status": org.status.value if org.status else None,
            "is_active": org.is_active,
            "owner_id": org.owner_id,
            "settings": org.settings,
            "extra_data": org.extra_data,
            "created_at": org.created_at,
            "updated_at": org.updated_at,
        }

    @staticmethod
    def _to_list_item(org: Organization) -> dict:
        return {
            "id": org.id,
            "name": org.name,
            "slug": org.slug,
            "display_name": org.display_name,
            "status": org.status.value if org.status else None,
            "organization_type": org.organization_type.value
            if org.organization_type
            else None,
            "owner_id": org.owner_id,
            "created_at": org.created_at,
        }

    def _trigger_chart_creation(
        self, organization_id: UUID, currency: str, owner_id: str
    ) -> None:
        """Trigger default chart of accounts creation in Core Service.
        
        This method makes an async call to the Core Service to create default
        GL accounts and account mappings. Errors are logged but do not fail
        organization creation.
        
        Args:
            organization_id: UUID of the organization
            currency: ISO currency code (e.g., "USD")
            owner_id: User identifier who created the organization
        """
        try:
            import asyncio
            import threading
            
            initiation_timestamp = datetime.now(UTC).isoformat()
            
            logger.info(
                "Creating default chart of accounts",
                extra={
                    "organization_id": str(organization_id),
                    "currency": currency,
                    "created_by": owner_id,
                    "timestamp": initiation_timestamp,
                    "event": "chart_creation_initiated"
                }
            )
            
            # Run async call in a new thread to avoid event loop conflicts
            def run_async_in_thread():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        response = loop.run_until_complete(
                            self.core_client.create_with_retry(
                                organization_id=organization_id,
                                currency=currency,
                                created_by=owner_id,
                                max_retries=self.retry_attempts
                            )
                        )
                        
                        if response:
                            completion_timestamp = datetime.now(UTC).isoformat()
                            
                            logger.info(
                                "Default chart of accounts created successfully",
                                extra={
                                    "organization_id": str(organization_id),
                                    "currency": currency,
                                    "created_by": owner_id,
                                    "accounts_created": response.get("accounts_created", 0),
                                    "mappings_created": response.get("mappings_created", 0),
                                    "timestamp": completion_timestamp,
                                    "event": "chart_creation_completed"
                                }
                            )
                        else:
                            failure_timestamp = datetime.now(UTC).isoformat()
                            
                            logger.error(
                                "Failed to create default chart of accounts after all retries",
                                extra={
                                    "organization_id": str(organization_id),
                                    "currency": currency,
                                    "created_by": owner_id,
                                    "retry_attempts": self.retry_attempts,
                                    "timestamp": failure_timestamp,
                                    "event": "chart_creation_failed"
                                }
                            )
                    finally:
                        loop.close()
                except Exception as e:
                    error_timestamp = datetime.now(UTC).isoformat()
                    
                    logger.error(
                        "Failed to create default chart of accounts - thread execution error",
                        extra={
                            "organization_id": str(organization_id),
                            "currency": currency,
                            "created_by": owner_id,
                            "error_type": type(e).__name__,
                            "error": str(e),
                            "timestamp": error_timestamp,
                            "event": "chart_creation_failed"
                        }
                    )
            
            # Start the async call in a background thread
            thread = threading.Thread(target=run_async_in_thread, daemon=True)
            thread.start()
            
        except Exception as e:
            error_timestamp = datetime.now(UTC).isoformat()
            
            logger.error(
                "Failed to create default chart of accounts - unexpected error",
                extra={
                    "organization_id": str(organization_id),
                    "currency": currency,
                    "created_by": owner_id,
                    "error_type": type(e).__name__,
                    "error": str(e),
                    "timestamp": error_timestamp,
                    "event": "chart_creation_failed"
                }
            )
