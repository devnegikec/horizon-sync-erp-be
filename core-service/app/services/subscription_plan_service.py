"""Plan catalog service: create plans, version, approve, publish, retire."""

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.subscription import (
    PLAN_VERSION_STATUS_APPROVED,
    PLAN_VERSION_STATUS_DRAFT,
    PLAN_VERSION_STATUS_PUBLISHED,
    PLAN_VERSION_STATUS_RETIRED,
    SubscriptionPlanVersion,
)
from app.repositories.subscription_repository import SubscriptionRepository


def conflict(code: str, message: str, http_status: int = status.HTTP_409_CONFLICT):
    return HTTPException(
        status_code=http_status, detail={"code": code, "message": message}
    )


def _aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


class SubscriptionPlanService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SubscriptionRepository(db)

    # ── Plans ───────────────────────────────────────────────────────────────

    def create_plan(self, payload, actor_id: UUID | None = None) -> dict:
        code = payload.code.strip().upper()
        if self.repo.get_plan_by_code(payload.organization_id, code):
            raise conflict(
                "PLAN_CODE_EXISTS",
                f"Plan code '{code}' already exists for this scope",
            )
        plan = self.repo.create_plan(
            {
                "organization_id": payload.organization_id,
                "code": code,
                "name": payload.name.strip(),
                "description": payload.description,
                "currency": payload.currency.upper(),
                "is_active": True,
            }
        )
        self.db.commit()
        return self._plan_dict(plan)

    def list_plans(
        self,
        *,
        organization_id: UUID | None = None,
        active: bool | None = None,
        q: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict:
        items, total = self.repo.list_plans(
            organization_id=organization_id,
            active=active,
            q=q,
            page=page,
            page_size=page_size,
        )
        return {
            "items": [self._plan_dict(plan) for plan in items],
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_items": total,
                "total_pages": max(1, (total + page_size - 1) // page_size),
            },
        }

    def get_plan_detail(self, plan_id: UUID) -> dict:
        plan = self.repo.get_plan(plan_id)
        if plan is None:
            raise conflict(
                "PLAN_NOT_FOUND", "Plan not found", status.HTTP_404_NOT_FOUND
            )
        data = self._plan_dict(plan)
        data["versions"] = [
            self._version_dict(version) for version in self.repo.list_versions(plan_id)
        ]
        return data

    # ── Versions ────────────────────────────────────────────────────────────

    def create_version(
        self, plan_id: UUID, payload, actor_id: UUID | None = None
    ) -> dict:
        # Row-lock the plan so concurrent creates cannot read the same max
        # version and collide on uq_plan_versions_plan_version.
        plan = self.repo.get_plan(plan_id, for_update=True)
        if plan is None:
            raise conflict(
                "PLAN_NOT_FOUND", "Plan not found", status.HTTP_404_NOT_FOUND
            )
        version = self.repo.create_version(
            {
                "plan_id": plan_id,
                "version": self.repo.next_version_number(plan_id),
                "billing_cadence": payload.billing_cadence,
                "base_price": payload.base_price,
                "tax_rate": payload.tax_rate,
                "included_credits": payload.included_credits,
                "id_weight": payload.id_weight,
                "topup_allowed": payload.topup_allowed,
                "effective_from": payload.effective_from,
                "status": PLAN_VERSION_STATUS_DRAFT,
                "created_by": actor_id,
            }
        )
        self.db.commit()
        return self._version_dict(version)

    def update_version(self, plan_id: UUID, version_id: UUID, payload) -> dict:
        version = self._get_version_for_plan(plan_id, version_id)
        if version.status != PLAN_VERSION_STATUS_DRAFT:
            raise conflict(
                "VERSION_NOT_DRAFT",
                "Only draft versions can be edited; create a new version",
            )
        for field in (
            "billing_cadence",
            "base_price",
            "tax_rate",
            "included_credits",
            "id_weight",
            "topup_allowed",
            "effective_from",
        ):
            value = getattr(payload, field, None)
            if value is not None:
                setattr(version, field, value)
        self.db.commit()
        return self._version_dict(version)

    def approve_version(
        self, plan_id: UUID, version_id: UUID, actor_id: UUID | None = None
    ) -> dict:
        version = self._get_version_for_plan(plan_id, version_id)
        if version.status != PLAN_VERSION_STATUS_DRAFT:
            raise conflict("VERSION_NOT_DRAFT", "Only draft versions can be approved")
        version.status = PLAN_VERSION_STATUS_APPROVED
        version.approved_by = actor_id
        version.approved_at = datetime.now(UTC)
        self.db.commit()
        return self._version_dict(version)

    def publish_version(self, plan_id: UUID, version_id: UUID, payload) -> dict:
        # Lock the plan so the overlap check and status flip are serialized;
        # two concurrent publishes cannot both pass the overlap check.
        self.repo.get_plan(plan_id, for_update=True)
        version = self._get_version_for_plan(plan_id, version_id)
        if version.status != PLAN_VERSION_STATUS_APPROVED:
            raise conflict(
                "VERSION_NOT_APPROVED",
                "Approve the version before publishing it",
            )
        effective_from = _aware(
            payload.effective_from or version.effective_from or datetime.now(UTC)
        )
        if version.effective_to and effective_from >= _aware(version.effective_to):
            raise conflict(
                "EFFECTIVE_RANGE_INVALID",
                "effective_from must be before effective_to",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        overlap = self.repo.find_published_overlap(
            plan_id,
            effective_from,
            _aware(version.effective_to),
            exclude_version_id=version.id,
        )
        if overlap:
            raise conflict(
                "EFFECTIVE_RANGE_OVERLAP",
                f"Version {overlap.version} already covers this effective period",
            )
        version.effective_from = effective_from
        version.status = PLAN_VERSION_STATUS_PUBLISHED
        self.db.commit()
        return self._version_dict(version)

    def retire_version(self, plan_id: UUID, version_id: UUID, payload) -> dict:
        version = self._get_version_for_plan(plan_id, version_id)
        if version.status != PLAN_VERSION_STATUS_PUBLISHED:
            raise conflict(
                "VERSION_NOT_PUBLISHED", "Only published versions can be retired"
            )
        if version.effective_from and _aware(payload.effective_to) <= _aware(
            version.effective_from
        ):
            raise conflict(
                "EFFECTIVE_RANGE_INVALID",
                "effective_to must be after effective_from",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        version.effective_to = payload.effective_to
        version.status = PLAN_VERSION_STATUS_RETIRED
        self.db.commit()
        return self._version_dict(version)

    # ── Helpers ─────────────────────────────────────────────────────────────

    def _get_version_for_plan(
        self, plan_id: UUID, version_id: UUID
    ) -> SubscriptionPlanVersion:
        version = self.repo.get_version(version_id)
        if version is None or version.plan_id != plan_id:
            raise conflict(
                "PLAN_VERSION_NOT_FOUND",
                "Plan version not found",
                status.HTTP_404_NOT_FOUND,
            )
        return version

    def _plan_dict(self, plan) -> dict:
        published = self.repo.get_published_version(plan.id)
        return {
            "id": plan.id,
            "organization_id": plan.organization_id,
            "code": plan.code,
            "name": plan.name,
            "description": plan.description,
            "currency": plan.currency,
            "is_active": plan.is_active,
            "created_at": plan.created_at,
            "published_version": (self._version_dict(published) if published else None),
        }

    def _version_dict(self, version) -> dict:
        return {
            "id": version.id,
            "plan_id": version.plan_id,
            "version": version.version,
            "billing_cadence": version.billing_cadence,
            "base_price": version.base_price,
            "tax_rate": version.tax_rate,
            "included_credits": version.included_credits,
            "id_weight": version.id_weight,
            "topup_allowed": version.topup_allowed,
            "effective_from": version.effective_from,
            "effective_to": version.effective_to,
            "status": version.status,
            "approved_by": version.approved_by,
            "approved_at": version.approved_at,
            "created_at": version.created_at,
        }
