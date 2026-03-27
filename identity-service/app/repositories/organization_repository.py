"""Organization repository for database operations"""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.base import OrganizationStatus, OrganizationType
from app.models.organization import Organization


class OrganizationRepository:
    """Repository for organization database operations"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Organization:
        """Create a new organization."""
        org = Organization(**data)
        self.db.add(org)
        self.db.commit()
        self.db.refresh(org)
        return org

    def get_by_id(self, organization_id: UUID) -> Organization | None:
        """Get organization by ID, excluding soft-deleted."""
        return (
            self.db.query(Organization)
            .filter(
                Organization.id == organization_id,
                Organization.deleted_at.is_(None),
            )
            .first()
        )

    def get_by_slug(self, slug: str) -> Organization | None:
        """Get organization by slug, excluding soft-deleted."""
        return (
            self.db.query(Organization)
            .filter(
                Organization.slug == slug,
                Organization.deleted_at.is_(None),
            )
            .first()
        )

    def slug_exists(self, slug: str, exclude_id: UUID | None = None) -> bool:
        """Check if slug exists (optionally excluding an id for updates)."""
        query = self.db.query(Organization).filter(
            Organization.slug == slug,
            Organization.deleted_at.is_(None),
        )
        if exclude_id:
            query = query.filter(Organization.id != exclude_id)
        return query.count() > 0

    def list_organizations(
        self,
        page: int = 1,
        page_size: int = 20,
        status: OrganizationStatus | None = None,
        organization_type: OrganizationType | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        organization_ids: list[UUID] | None = None,
    ) -> tuple[list[Organization], int]:
        """
        List organizations with pagination and filters.

        If organization_ids is provided, only return those organizations.
        """
        query = self.db.query(Organization).filter(Organization.deleted_at.is_(None))

        if organization_ids is not None:
            query = query.filter(Organization.id.in_(organization_ids))

        if status is not None:
            query = query.filter(Organization.status == status)
        if organization_type is not None:
            query = query.filter(Organization.organization_type == organization_type)
        if search:
            term = f"%{search}%"
            query = query.filter(
                or_(
                    Organization.name.ilike(term),
                    Organization.slug.ilike(term),
                    Organization.display_name.ilike(term),
                )
            )
        total_count = query.count()

        sort_column = getattr(Organization, sort_by, Organization.created_at)
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())

        offset = (page - 1) * page_size
        items = query.offset(offset).limit(page_size).all()
        return items, total_count

    def update(self, org: Organization, data: dict) -> Organization:
        """Update organization fields."""
        for key, value in data.items():
            if hasattr(org, key):
                setattr(org, key, value)
        self.db.commit()
        self.db.refresh(org)
        return org

    def soft_delete(self, org: Organization) -> Organization:
        """Soft delete by setting deleted_at."""
        org.deleted_at = datetime.now(UTC)
        self.db.commit()
        self.db.refresh(org)
        return org

    def get_organization_by_type(self, organization_type: OrganizationType) -> Organization | None:
        """Get organization by type (e.g., MASTER), excluding soft-deleted."""
        return (
            self.db.query(Organization)
            .filter(
                Organization.organization_type == organization_type,
                Organization.deleted_at.is_(None),
            )
            .first()
        )
