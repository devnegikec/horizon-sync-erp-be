"""Database access for subscription plans, versions and contracts."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.subscription import (
    OrganizationSubscription,
    SubscriptionPlan,
    SubscriptionPlanVersion,
)


def _aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    # ── Plans ───────────────────────────────────────────────────────────────

    def get_plan(
        self, plan_id: UUID, *, for_update: bool = False
    ) -> SubscriptionPlan | None:
        query = self.db.query(SubscriptionPlan).filter(SubscriptionPlan.id == plan_id)
        if for_update:
            query = query.with_for_update()
        return query.first()

    def get_plan_by_code(
        self, organization_id: UUID | None, code: str
    ) -> SubscriptionPlan | None:
        query = self.db.query(SubscriptionPlan).filter(
            SubscriptionPlan.code == code.upper()
        )
        if organization_id is None:
            query = query.filter(SubscriptionPlan.organization_id.is_(None))
        else:
            query = query.filter(SubscriptionPlan.organization_id == organization_id)
        return query.first()

    def list_plans(
        self,
        *,
        organization_id: UUID | None = None,
        active: bool | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[list[SubscriptionPlan], int]:
        query = self.db.query(SubscriptionPlan)
        if organization_id is not None:
            # Org-specific plans plus the shared global catalog.
            query = query.filter(
                or_(
                    SubscriptionPlan.organization_id == organization_id,
                    SubscriptionPlan.organization_id.is_(None),
                )
            )
        if active is not None:
            query = query.filter(SubscriptionPlan.is_active.is_(active))
        if q:
            pattern = f"%{q.strip()}%"
            query = query.filter(
                or_(
                    SubscriptionPlan.code.ilike(pattern),
                    SubscriptionPlan.name.ilike(pattern),
                )
            )
        total = query.count()
        items = (
            query.order_by(SubscriptionPlan.code.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return items, total

    def create_plan(self, data: dict) -> SubscriptionPlan:
        plan = SubscriptionPlan(**data)
        self.db.add(plan)
        self.db.flush()
        return plan

    # ── Plan versions ───────────────────────────────────────────────────────

    def get_version(self, version_id: UUID) -> SubscriptionPlanVersion | None:
        return (
            self.db.query(SubscriptionPlanVersion)
            .filter(SubscriptionPlanVersion.id == version_id)
            .first()
        )

    def list_versions(self, plan_id: UUID) -> list[SubscriptionPlanVersion]:
        return (
            self.db.query(SubscriptionPlanVersion)
            .filter(SubscriptionPlanVersion.plan_id == plan_id)
            .order_by(SubscriptionPlanVersion.version.desc())
            .all()
        )

    def next_version_number(self, plan_id: UUID) -> int:
        current = (
            self.db.query(func.max(SubscriptionPlanVersion.version))
            .filter(SubscriptionPlanVersion.plan_id == plan_id)
            .scalar()
        )
        return int(current or 0) + 1

    def get_published_version(self, plan_id: UUID) -> SubscriptionPlanVersion | None:
        return (
            self.db.query(SubscriptionPlanVersion)
            .filter(
                SubscriptionPlanVersion.plan_id == plan_id,
                SubscriptionPlanVersion.status == "published",
            )
            .order_by(SubscriptionPlanVersion.version.desc())
            .first()
        )

    def find_published_overlap(
        self,
        plan_id: UUID,
        effective_from: datetime,
        effective_to: datetime | None,
        *,
        exclude_version_id: UUID | None = None,
    ) -> SubscriptionPlanVersion | None:
        """Return a published version whose effective window overlaps."""
        query = self.db.query(SubscriptionPlanVersion).filter(
            SubscriptionPlanVersion.plan_id == plan_id,
            SubscriptionPlanVersion.status == "published",
            SubscriptionPlanVersion.effective_from.isnot(None),
        )
        if exclude_version_id:
            query = query.filter(SubscriptionPlanVersion.id != exclude_version_id)
        overlap = []
        for version in query.all():
            other_start = _aware(version.effective_from)
            other_end = _aware(version.effective_to)
            if other_start is None:
                continue
            if effective_to is None or _aware(effective_to) > other_start:
                if other_end is None or other_end > _aware(effective_from):
                    overlap.append(version)
        return overlap[0] if overlap else None

    def create_version(self, data: dict) -> SubscriptionPlanVersion:
        version = SubscriptionPlanVersion(**data)
        self.db.add(version)
        self.db.flush()
        return version

    # ── Organization subscriptions ──────────────────────────────────────────

    def get_subscription(
        self, organization_id: UUID, *, for_update: bool = False
    ) -> OrganizationSubscription | None:
        query = self.db.query(OrganizationSubscription).filter(
            OrganizationSubscription.organization_id == organization_id
        )
        if for_update:
            query = query.with_for_update()
        return query.first()

    def create_subscription(self, data: dict) -> OrganizationSubscription:
        subscription = OrganizationSubscription(**data)
        self.db.add(subscription)
        self.db.flush()
        return subscription

    def list_due_subscriptions(self, as_of: datetime) -> list[OrganizationSubscription]:
        return (
            self.db.query(OrganizationSubscription)
            .filter(
                OrganizationSubscription.status.in_(
                    ("active", "overdue", "pending_activation_payment")
                ),
                OrganizationSubscription.next_invoice_date.isnot(None),
                OrganizationSubscription.next_invoice_date <= as_of.date(),
            )
            .all()
        )

    def list_active_subscriptions(self) -> list[OrganizationSubscription]:
        return (
            self.db.query(OrganizationSubscription)
            .filter(OrganizationSubscription.status.in_(("active", "overdue")))
            .all()
        )

    def utcnow(self) -> datetime:
        return datetime.now(UTC)
