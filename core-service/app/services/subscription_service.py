"""Organization subscription lifecycle and contract snapshots."""

import calendar
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.subscription import (
    PLAN_VERSION_STATUS_PUBLISHED,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_CLOSED,
    SUBSCRIPTION_STATUS_DRAFT,
    SUBSCRIPTION_STATUS_OVERDUE,
    SUBSCRIPTION_STATUS_PENDING_ACTIVATION,
    SUBSCRIPTION_STATUS_SUSPENDED,
)
from app.repositories.credit_ledger_repository import CreditLedgerRepository
from app.repositories.subscription_repository import SubscriptionRepository


def billing_error(code: str, message: str, http_status: int):
    return HTTPException(
        status_code=http_status, detail={"code": code, "message": message}
    )


def add_months(value: datetime, months: int) -> datetime:
    """Add calendar months, clamping the day to the target month's length."""
    month_index = value.month - 1 + months
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


CADENCE_MONTHS = {"monthly": 1, "quarterly": 3, "annually": 12, "yearly": 12}


def _aware(value: datetime | None) -> datetime | None:
    """SQLite returns naive datetimes; treat them as UTC."""
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def period_end(start: datetime, cadence: str) -> datetime:
    return add_months(_aware(start), CADENCE_MONTHS.get(cadence, 1))


def anchored_period_end(
    start: datetime, cadence: str, anchor_day: int | None
) -> datetime:
    """End of the period, clamped to the billing anchor day."""
    start = _aware(start)
    anchor = max(1, min(int(anchor_day or 1), 28))
    candidate = add_months(start, CADENCE_MONTHS.get(cadence, 1))
    candidate = candidate.replace(
        day=min(anchor, calendar.monthrange(candidate.year, candidate.month)[1])
    )
    while candidate <= start:
        candidate = add_months(candidate, 1)
        candidate = candidate.replace(
            day=min(anchor, calendar.monthrange(candidate.year, candidate.month)[1])
        )
    return candidate


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SubscriptionRepository(db)
        self.credit_repo = CreditLedgerRepository(db)

    # ── Lifecycle ───────────────────────────────────────────────────────────

    def create_subscription(
        self, organization_id: UUID, payload, actor_id: UUID | None = None
    ) -> dict:
        existing = self.repo.get_subscription(organization_id, for_update=True)
        if existing is not None:
            raise billing_error(
                "SUBSCRIPTION_EXISTS",
                "This organization already has a subscription",
                status.HTTP_409_CONFLICT,
            )
        version = self.repo.get_version(payload.plan_version_id)
        if version is None or version.status != PLAN_VERSION_STATUS_PUBLISHED:
            raise billing_error(
                "PLAN_VERSION_NOT_PUBLISHED",
                "A published plan version is required",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        plan = self.repo.get_plan(version.plan_id)
        if plan is None:
            raise billing_error(
                "PLAN_NOT_FOUND", "Plan not found", status.HTTP_404_NOT_FOUND
            )
        if plan.organization_id not in (None, organization_id):
            raise billing_error(
                "PLAN_NOT_AVAILABLE",
                "This plan is not available to the organization",
                status.HTTP_403_FORBIDDEN,
            )

        now = datetime.now(UTC)
        starts_active = not payload.activation_fee_required
        start = _aware(version.effective_from) or now
        end = anchored_period_end(
            start, version.billing_cadence, payload.billing_anchor_day
        )
        subscription = self.repo.create_subscription(
            {
                "organization_id": organization_id,
                "plan_id": plan.id,
                "plan_version_id": version.id,
                "status": (
                    SUBSCRIPTION_STATUS_ACTIVE
                    if starts_active
                    else SUBSCRIPTION_STATUS_PENDING_ACTIVATION
                ),
                "billing_cadence": version.billing_cadence,
                "billing_anchor_day": payload.billing_anchor_day,
                "billing_timezone": payload.billing_timezone,
                "activation_fee": payload.activation_fee,
                "activation_fee_status": (
                    "pending" if payload.activation_fee_required else "not_required"
                ),
                "annual_release_policy": payload.annual_release_policy,
                "current_period_start": start,
                "current_period_end": end,
                "next_invoice_date": end.date(),
                "activated_at": (now if starts_active and start <= now else None),
            }
        )
        self.db.commit()
        return self._snapshot(subscription, plan, version)

    def activate(self, organization_id: UUID, reference: str | None = None) -> dict:
        subscription = self._get_subscription_for_update(organization_id)
        if subscription.status == SUBSCRIPTION_STATUS_ACTIVE:
            return self._snapshot_current(subscription)
        allowed = (
            SUBSCRIPTION_STATUS_DRAFT,
            SUBSCRIPTION_STATUS_PENDING_ACTIVATION,
        )
        if subscription.status not in allowed:
            raise billing_error(
                "INVALID_STATUS_TRANSITION",
                f"Cannot activate a subscription in status '{subscription.status}'",
                status.HTTP_409_CONFLICT,
            )
        now = datetime.now(UTC)
        subscription.status = SUBSCRIPTION_STATUS_ACTIVE
        subscription.activation_fee_status = (
            "paid" if subscription.activation_fee else "not_required"
        )
        subscription.activated_at = now
        subscription.current_period_start = now
        subscription.current_period_end = anchored_period_end(
            now, subscription.billing_cadence, subscription.billing_anchor_day
        )
        subscription.next_invoice_date = subscription.current_period_end.date()
        self.db.commit()
        return self._snapshot_current(subscription, reference=reference)

    def update_subscription(self, organization_id: UUID, payload) -> dict:
        subscription = self._get_subscription_for_update(organization_id)
        if subscription.status in (SUBSCRIPTION_STATUS_CLOSED,):
            raise billing_error(
                "SUBSCRIPTION_CLOSED",
                "A closed subscription cannot be modified",
                status.HTTP_409_CONFLICT,
            )
        if payload.plan_version_id is not None:
            version = self.repo.get_version(payload.plan_version_id)
            if version is None or version.status != PLAN_VERSION_STATUS_PUBLISHED:
                raise billing_error(
                    "PLAN_VERSION_NOT_PUBLISHED",
                    "A published plan version is required",
                    status.HTTP_422_UNPROCESSABLE_ENTITY,
                )
            if version.plan_id != subscription.plan_id:
                raise billing_error(
                    "PLAN_CHANGE_NOT_ALLOWED",
                    "Create a new subscription to switch plans",
                    status.HTTP_409_CONFLICT,
                )
            effective_from = _aware(payload.effective_from)
            if effective_from and effective_from > datetime.now(UTC):
                # Effective-dated change: keep the current contract until due.
                subscription.pending_plan_version_id = version.id
                subscription.pending_effective_from = effective_from
            else:
                subscription.plan_version_id = version.id
                subscription.billing_cadence = version.billing_cadence
                subscription.pending_plan_version_id = None
                subscription.pending_effective_from = None
        elif payload.effective_from is not None:
            raise billing_error(
                "EFFECTIVE_FROM_REQUIRES_VERSION",
                "effective_from is only valid together with plan_version_id",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        if payload.billing_anchor_day is not None:
            subscription.billing_anchor_day = payload.billing_anchor_day
        if payload.billing_timezone is not None:
            subscription.billing_timezone = payload.billing_timezone
        if payload.billing_anchor_day is not None:
            start = _aware(subscription.current_period_start) or datetime.now(UTC)
            subscription.current_period_end = anchored_period_end(
                start,
                subscription.billing_cadence,
                subscription.billing_anchor_day,
            )
            subscription.next_invoice_date = subscription.current_period_end.date()
        self.db.commit()
        return self._snapshot_current(subscription)

    def suspend(self, organization_id: UUID, reason: str) -> dict:
        subscription = self._get_subscription_for_update(organization_id)
        if subscription.status == SUBSCRIPTION_STATUS_CLOSED:
            raise billing_error(
                "SUBSCRIPTION_CLOSED",
                "A closed subscription cannot be suspended",
                status.HTTP_409_CONFLICT,
            )
        subscription.status = SUBSCRIPTION_STATUS_SUSPENDED
        subscription.suspended_at = datetime.now(UTC)
        subscription.suspended_reason = reason
        self.db.commit()
        return self._snapshot_current(subscription)

    def reinstate(self, organization_id: UUID, reason: str) -> dict:
        subscription = self._get_subscription_for_update(organization_id)
        if subscription.status != SUBSCRIPTION_STATUS_SUSPENDED:
            raise billing_error(
                "INVALID_STATUS_TRANSITION",
                "Only suspended subscriptions can be reinstated",
                status.HTTP_409_CONFLICT,
            )
        now = datetime.now(UTC)
        subscription.status = SUBSCRIPTION_STATUS_ACTIVE
        subscription.suspended_at = None
        subscription.suspended_reason = None
        if (
            subscription.current_period_end
            and _aware(subscription.current_period_end) < now
        ):
            subscription.status = SUBSCRIPTION_STATUS_OVERDUE
        self.db.commit()
        return self._snapshot_current(subscription)

    def close(self, organization_id: UUID, reason: str) -> dict:
        subscription = self._get_subscription_for_update(organization_id)
        subscription.status = SUBSCRIPTION_STATUS_CLOSED
        subscription.closed_at = datetime.now(UTC)
        self.db.commit()
        return self._snapshot_current(subscription)

    # ── Reads ───────────────────────────────────────────────────────────────

    def get_snapshot(self, organization_id: UUID) -> dict:
        subscription = self.repo.get_subscription(organization_id)
        if subscription is None:
            raise billing_error(
                "SUBSCRIPTION_NOT_FOUND",
                "No subscription is configured for this organization",
                status.HTTP_404_NOT_FOUND,
            )
        if self.apply_pending_changes(subscription):
            self.db.commit()
        return self._snapshot_current(subscription)

    def apply_pending_changes(self, subscription) -> bool:
        """Promote a future-effective contract version once it is due."""
        if not subscription.pending_plan_version_id:
            return False
        due = _aware(subscription.pending_effective_from)
        if due is None or due > datetime.now(UTC):
            return False
        version = self.repo.get_version(subscription.pending_plan_version_id)
        if version is not None:
            subscription.plan_version_id = version.id
            subscription.billing_cadence = version.billing_cadence
        subscription.pending_plan_version_id = None
        subscription.pending_effective_from = None
        return True

    def get_exposure(self, expiring_within_days: int = 30) -> dict:
        from datetime import timedelta

        now = datetime.now(UTC)
        horizon = now + timedelta(days=expiring_within_days)
        items = []
        total_available = Decimal("0.000000")
        total_expiring = Decimal("0.000000")
        for subscription in self.repo.list_active_subscriptions():
            org_id = subscription.organization_id
            available = self.credit_repo.sum_available(org_id)
            expiring = self.credit_repo.expiring_between(org_id, now, horizon)
            earliest = self.credit_repo.earliest_expiring_batch(org_id, now)
            overdue, outstanding = self.credit_repo.invoice_exposure(org_id)
            total_available += available
            total_expiring += expiring
            items.append(
                {
                    "organization_id": org_id,
                    "subscription_status": subscription.status,
                    "available": available,
                    "reserved": self.credit_repo.sum_reserved(org_id),
                    "expiring_within_days": expiring,
                    "horizon_days": expiring_within_days,
                    "overdue_invoices": overdue,
                    "outstanding_amount": outstanding,
                    "earliest_expiry": earliest.expires_at if earliest else None,
                }
            )
        return {
            "items": items,
            "totals": {
                "organizations": len(items),
                "available": total_available,
                "expiring_within_days": total_expiring,
            },
        }

    def get_reconciliation(self) -> dict:
        items = []
        for (
            invoice_id,
            org_id,
            invoice_no,
        ) in self.credit_repo.paid_invoices_without_batch():
            items.append(
                {
                    "issue": "paid_invoice_without_grant",
                    "organization_id": org_id,
                    "reference_type": "invoice",
                    "reference_id": invoice_id,
                    "detail": f"Invoice {invoice_no} is paid but has no credit batch",
                }
            )
        for (
            batch_id,
            org_id,
            source_id,
            invoice_no,
            invoice_status,
        ) in self.credit_repo.grants_without_payment():
            items.append(
                {
                    "issue": "grant_without_payment",
                    "organization_id": org_id,
                    "reference_type": "credit_batch",
                    "reference_id": batch_id,
                    "detail": (
                        f"Batch for invoice {source_id} exists but the invoice is "
                        f"{invoice_status or 'missing'}"
                        + (f" ({invoice_no})" if invoice_no else "")
                    ),
                }
            )
        for operation in self.credit_repo.stuck_reservations(datetime.now(UTC)):
            items.append(
                {
                    "issue": "stuck_reservation",
                    "organization_id": operation.organization_id,
                    "reference_type": "generation_operation",
                    "reference_id": operation.id,
                    "detail": (
                        f"Reservation '{operation.operation_key}' expired at "
                        f"{operation.reserved_until} and is still held"
                    ),
                }
            )
        return {"items": items}

    # ── Serialization ───────────────────────────────────────────────────────

    def _snapshot_current(self, subscription, reference: str | None = None) -> dict:
        version = self.repo.get_version(subscription.plan_version_id)
        plan = self.repo.get_plan(subscription.plan_id)
        return self._snapshot(subscription, plan, version)

    def _snapshot(self, subscription, plan, version) -> dict:
        weight = version.id_weight if version else Decimal("0")
        can_top_up = bool(version and version.topup_allowed) and (
            subscription.status
            in (SUBSCRIPTION_STATUS_ACTIVE, SUBSCRIPTION_STATUS_OVERDUE)
        )
        return {
            "organization_id": subscription.organization_id,
            "plan": {
                "id": plan.id,
                "code": plan.code,
                "name": plan.name,
            },
            "plan_version": {
                "id": version.id,
                "version": version.version,
                "billing_cadence": version.billing_cadence,
                "base_price": version.base_price,
                "currency": plan.currency,
                "tax_rate": version.tax_rate,
                "included_credits": version.included_credits,
                "id_weight": weight,
                "effective_from": version.effective_from,
            },
            "status": subscription.status,
            "billing_cadence": subscription.billing_cadence,
            "billing_anchor_day": subscription.billing_anchor_day,
            "billing_timezone": subscription.billing_timezone,
            "activation_fee": subscription.activation_fee,
            "activation_fee_status": subscription.activation_fee_status,
            "current_period_start": subscription.current_period_start,
            "current_period_end": subscription.current_period_end,
            "next_invoice_date": subscription.next_invoice_date,
            "renewal_date": (
                subscription.current_period_end.date()
                if subscription.current_period_end
                else subscription.next_invoice_date
            ),
            "id_weight": weight,
            "included_credits_per_period": (
                version.included_credits if version else Decimal("0")
            ),
            "payment_status": self._payment_status(subscription.status),
            "grace_until": None,
            "can_top_up": can_top_up,
            "activated_at": subscription.activated_at,
            "suspended_at": subscription.suspended_at,
            "closed_at": subscription.closed_at,
        }

    @staticmethod
    def _payment_status(subscription_status: str) -> str:
        return {
            SUBSCRIPTION_STATUS_ACTIVE: "current",
            SUBSCRIPTION_STATUS_PENDING_ACTIVATION: "due",
            SUBSCRIPTION_STATUS_DRAFT: "due",
            SUBSCRIPTION_STATUS_OVERDUE: "overdue",
            SUBSCRIPTION_STATUS_SUSPENDED: "overdue",
            SUBSCRIPTION_STATUS_CLOSED: "closed",
        }.get(subscription_status, "unknown")

    def _get_subscription_for_update(self, organization_id: UUID):
        subscription = self.repo.get_subscription(organization_id, for_update=True)
        if subscription is None:
            raise billing_error(
                "SUBSCRIPTION_NOT_FOUND",
                "No subscription is configured for this organization",
                status.HTTP_404_NOT_FOUND,
            )
        return subscription
