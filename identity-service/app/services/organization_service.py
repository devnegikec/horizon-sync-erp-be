"""Organization service with business logic"""

import logging
from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

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
    UserType,
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

    def create(self, data: dict, owner_id: UUID, user_type: UserType = None) -> dict:
        """Create organization; validate slug uniqueness. Sets owner_id and assigns Owner role with *.* to creating user."""
        slug = data.get("slug", "").strip().lower()
        if self.repo.slug_exists(slug):
            raise DuplicateOrganizationSlugException(
                f"Organization with slug '{slug}' already exists"
            )
        
        # Master organization validation (Task 1A-1)
        org_type = data.get("organization_type")
        if org_type == OrganizationType.MASTER or org_type == "master":
            self._validate_master_org_creation(user_type)
            
        payload = dict(data)
        payload["owner_id"] = owner_id
        if "organization_type" in payload and payload["organization_type"]:
            payload["organization_type"] = OrganizationType(
                payload["organization_type"]
            )
        if "status" in payload and payload["status"]:
            payload["status"] = OrganizationStatus(payload["status"])

        # Set billing defaults for non-master organizations (Task 1A-2)
        from app.models.base import BillingStatus
        from app.config import settings as app_settings
        org_type_val = payload.get("organization_type")
        is_master = org_type_val == OrganizationType.MASTER or org_type_val == "master"
        if not is_master:
            from datetime import timedelta, UTC as _UTC
            now = datetime.now(_UTC)
            cycle = payload.get("billing_cycle", app_settings.default_billing_cycle)
            trial_days = app_settings.default_trial_days
            cycle_days = {"monthly": 30, "quarterly": 90, "yearly": 365}
            # Next billing = after trial ends, based on billing cycle
            next_bill = now + timedelta(days=trial_days + cycle_days.get(cycle, 30))
            payload.setdefault("billing_status", BillingStatus.TRIAL)
            payload.setdefault("customer_since", now)
            payload.setdefault("subscription_start_date", now.date())
            payload.setdefault("trial_end_date", (now + timedelta(days=trial_days)).date())
            payload.setdefault("next_billing_date", next_bill.date())
            payload.setdefault("max_users", app_settings.default_max_users)
            payload.setdefault("max_credits", app_settings.default_max_credits)
            payload.setdefault("billing_cycle", cycle)

        org = self.repo.create(payload)

        # ── Seed all preloaded roles for this org ──────────────────────────────
        # Import here to avoid circular imports at module load time
        from app.core.modules import PRELOADED_ORG_ROLES

        all_permissions = self.db.query(Permission).all()
        permissions_map: dict[str, Permission] = {p.code: p for p in all_permissions}

        # Ensure *.* permission exists (needed by Owner role)
        if "*.*" not in permissions_map:
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
            permissions_map["*.*"] = full_access

        created_roles: dict[str, Role] = {}
        for template in PRELOADED_ORG_ROLES:
            role = Role(
                organization_id=org.id,
                name=template.name,
                code=template.code,
                description=template.description,
                is_system=template.is_system,
                is_default=False,
                hierarchy_level=template.hierarchy_level,
                is_active=True,
            )
            self.db.add(role)
            self.db.flush()
            created_roles[template.code] = role

            for perm_code in template.permission_codes:
                perm = permissions_map.get(perm_code)
                if perm:
                    self.db.add(RolePermission(role_id=role.id, permission_id=perm.id))

        # Assign the Owner role to the creating user
        owner_role = created_roles["owner"]
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

        # Trigger default chart of accounts creation, then seed onboarding defaults.
        # Both run in a single background thread to ensure chart accounts exist
        # before tax template rules reference them.
        if self.core_client:
            self._trigger_org_onboarding(org.id, org.base_currency or "USD", str(owner_id))

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
        parent_organization_id: UUID | None = None,
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
            parent_organization_id=parent_organization_id,
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

    def update(self, organization_id: UUID, data: dict, user_type: UserType = None) -> dict:
        """Update organization; validate slug if changed. Includes master org protections."""
        org = self.repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundException(
                f"Organization with ID {organization_id} not found"
            )
        
        # Master organization validation (Task 1A-1) 
        if org.organization_type == OrganizationType.MASTER:
            self._validate_master_org_modification(user_type)
            
        payload = {k: v for k, v in data.items() if v is not None}
        if "slug" in payload:
            if self.repo.slug_exists(payload["slug"], exclude_id=organization_id):
                raise DuplicateOrganizationSlugException(
                    f"Organization with slug '{payload['slug']}' already exists"
                )
        if "status" in payload:
            payload["status"] = OrganizationStatus(payload["status"])
        if "organization_type" in payload:
            # Prevent changing TO master type unless authorized
            if payload["organization_type"] == "master" or payload["organization_type"] == OrganizationType.MASTER:
                self._validate_master_org_creation(user_type)
            payload["organization_type"] = OrganizationType(
                payload["organization_type"]
            )
        updated = self.repo.update(org, payload)
        return self._to_response(updated)

    def delete(self, organization_id: UUID, user_type: UserType = None) -> None:
        """Soft delete organization. Prevents deletion of master organization."""
        org = self.repo.get_by_id(organization_id)
        if not org:
            raise OrganizationNotFoundException(
                f"Organization with ID {organization_id} not found"
            )
        
        # Prevent deletion of master organization
        if org.organization_type == OrganizationType.MASTER:
            raise ValueError("Cannot delete master organization")
            
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
            "billing_status": org.billing_status.value if org.billing_status else None,
            "subscription_start_date": org.subscription_start_date,
            "subscription_end_date": org.subscription_end_date,
            "trial_end_date": org.trial_end_date,
            "max_users": org.max_users,
            "max_credits": org.max_credits,
            "billing_contact_email": org.billing_contact_email,
            "billing_cycle": org.billing_cycle,
            "customer_since": org.customer_since,
            "last_billed_date": org.last_billed_date,
            "next_billing_date": org.next_billing_date,
        }

    def _trigger_org_onboarding(
        self, organization_id: UUID, currency: str, owner_id: str
    ) -> None:
        """Run organization onboarding in a background thread.

        Separated into two phases:
        1. CORE ONBOARDING (always runs, no feature flag dependency):
           - Currencies, UOMs, tax templates, item groups, system_config
        2. OPTIONAL FEATURE STEPS (only if respective feature is enabled):
           - Chart of accounts (depends on book_chart_of_account_enabled flag)

        Core onboarding runs first so that critical data (base currency, UOMs)
        is available immediately. Feature-specific steps run after and are
        allowed to fail without affecting the core setup.
        """
        try:
            import asyncio
            import threading

            logger.info(
                "Starting organization onboarding",
                extra={
                    "organization_id": str(organization_id),
                    "currency": currency,
                    "event": "org_onboarding_initiated",
                },
            )

            def run_onboarding():
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        # ─── Phase 1: Core onboarding (always runs) ───
                        # Seeds: currencies, UOMs, tax templates, item groups, system_config
                        defaults_response = loop.run_until_complete(
                            self.core_client.seed_organization_defaults_with_retry(
                                organization_id=organization_id,
                                base_currency=currency,
                                created_by=owner_id,
                                max_retries=self.retry_attempts,
                            )
                        )
                        if defaults_response:
                            logger.info(
                                "Core onboarding completed successfully",
                                extra={
                                    "organization_id": str(organization_id),
                                    "summary": defaults_response.get("summary"),
                                    "event": "org_core_onboarding_completed",
                                },
                            )
                        else:
                            logger.error(
                                "Core onboarding failed after all retries",
                                extra={
                                    "organization_id": str(organization_id),
                                    "event": "org_core_onboarding_failed",
                                },
                            )

                        # ─── Phase 2: Optional feature steps ───
                        # Chart of accounts — only attempted, failure doesn't affect core setup
                        try:
                            chart_response = loop.run_until_complete(
                                self.core_client.create_with_retry(
                                    organization_id=organization_id,
                                    currency=currency,
                                    created_by=owner_id,
                                    max_retries=1,  # Single attempt — don't retry feature-flagged steps
                                )
                            )
                            if chart_response:
                                logger.info(
                                    "Chart of accounts created",
                                    extra={
                                        "organization_id": str(organization_id),
                                        "accounts_created": chart_response.get("accounts_created", 0),
                                        "event": "chart_creation_completed",
                                    },
                                )
                        except Exception as chart_err:
                            # Chart creation is optional — log and continue
                            logger.info(
                                "Chart of accounts skipped (feature may be disabled)",
                                extra={
                                    "organization_id": str(organization_id),
                                    "reason": str(chart_err),
                                    "event": "chart_creation_skipped",
                                },
                            )

                    finally:
                        loop.close()
                except Exception as e:
                    logger.error(
                        "Organization onboarding thread failed",
                        extra={
                            "organization_id": str(organization_id),
                            "error": str(e),
                            "event": "org_onboarding_failed",
                        },
                    )

            thread = threading.Thread(target=run_onboarding, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(
                "Failed to start org onboarding thread",
                extra={
                    "organization_id": str(organization_id),
                    "error": str(e),
                    "event": "org_onboarding_failed",
                },
            )

    # Master Organization Validation Methods (Task 1A-1)
    def _validate_master_org_creation(self, user_type: UserType = None) -> None:
        """Validate that only SYSTEM_ADMIN can create master organizations and only one exists."""
        # Check if master organization already exists
        if self.get_master_organization():
            raise ValueError("Master organization already exists")

        # Only SYSTEM_ADMIN can create master organizations
        if user_type != UserType.SYSTEM_ADMIN:
            raise ValueError("Only system administrators can create master organizations")
    
    def _validate_master_org_modification(self, user_type: UserType = None) -> None:
        """Validate that only SYSTEM_ADMIN can modify master organizations."""
        if user_type != UserType.SYSTEM_ADMIN:
            raise ValueError("Only system administrators can modify master organizations")
    
    def is_master_organization(self, organization_id: UUID) -> bool:
        """Check if organization is a master organization."""
        org = self.repo.get_by_id(organization_id)
        return org and org.organization_type == OrganizationType.MASTER
    
    def get_master_organization(self) -> Organization:
        """Get the master organization (there should only be one)."""
        return self.repo.get_organization_by_type(OrganizationType.MASTER)
