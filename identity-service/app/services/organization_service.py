"""Organization service with business logic"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    DuplicateOrganizationSlugException,
    OrganizationNotFoundException,
)
from app.models.base import OrganizationStatus, OrganizationType
from app.models.organization import Organization
from app.models.role import Permission, Role, RolePermission, UserOrganizationRole
from app.repositories.organization_repository import OrganizationRepository


class OrganizationService:
    """Service for organization operations."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = OrganizationRepository(db)

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

        # Create Owner role for this org (full access *.*) and assign to creating user
        full_access = self.db.query(Permission).filter(Permission.code == "*.*").first()
        if full_access:
            owner_role = Role(
                organization_id=org.id,
                name="Organization Owner",
                code="owner",
                description="First user who created the organization; has full access in this org.",
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
            "organization_type": org.organization_type.value
            if org.organization_type
            else None,
            "industry": org.industry,
            "status": org.status.value if org.status else None,
            "is_active": org.is_active,
            "owner_id": org.owner_id,
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
