"""Subscription, plan and credit-ledger models.

Implements the Phase 1 data model from ``SUBSCRIPTION_PLAN_API_IMPLEMENTATION.md``:

- ``subscription_plans`` / ``subscription_plan_versions``: versioned commercial
  catalog. Published versions are immutable; edits create a new version.
- ``organization_subscriptions``: per-organization contract lifecycle.
- ``credit_batches`` / ``credit_ledger``: batch-expiring, weighted credits with
  an append-only ledger (FEFO consumption).
- ``generation_operations``: idempotent reserve → commit/release for ID
  generation.
- ``topup_quotes`` / ``topup_orders``: self-service credit purchases.
- ``billing_provider_events`` / ``billing_outbox_events``: webhook dedupe and
  durable event publication.

All credit quantities are stored as ``NUMERIC(20, 6)`` credits (fixed point).
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)

from app.database import Base
from app.models.types import JSONB, UUID

# ── Constants (kept as plain strings to avoid extra Postgres enum types) ────

SUBSCRIPTION_STATUS_DRAFT = "draft"
SUBSCRIPTION_STATUS_PENDING_ACTIVATION = "pending_activation_payment"
SUBSCRIPTION_STATUS_ACTIVE = "active"
SUBSCRIPTION_STATUS_OVERDUE = "overdue"
SUBSCRIPTION_STATUS_SUSPENDED = "suspended"
SUBSCRIPTION_STATUS_CLOSED = "closed"

SUBSCRIPTION_STATUSES = (
    SUBSCRIPTION_STATUS_DRAFT,
    SUBSCRIPTION_STATUS_PENDING_ACTIVATION,
    SUBSCRIPTION_STATUS_ACTIVE,
    SUBSCRIPTION_STATUS_OVERDUE,
    SUBSCRIPTION_STATUS_SUSPENDED,
    SUBSCRIPTION_STATUS_CLOSED,
)

PLAN_VERSION_STATUS_DRAFT = "draft"
PLAN_VERSION_STATUS_APPROVED = "approved"
PLAN_VERSION_STATUS_PUBLISHED = "published"
PLAN_VERSION_STATUS_RETIRED = "retired"

PLAN_VERSION_STATUSES = (
    PLAN_VERSION_STATUS_DRAFT,
    PLAN_VERSION_STATUS_APPROVED,
    PLAN_VERSION_STATUS_PUBLISHED,
    PLAN_VERSION_STATUS_RETIRED,
)

CREDIT_BATCH_STATUS_ACTIVE = "active"
CREDIT_BATCH_STATUS_EXHAUSTED = "exhausted"
CREDIT_BATCH_STATUS_EXPIRED = "expired"

GENERATION_STATUS_RESERVED = "reserved"
GENERATION_STATUS_COMMITTED = "committed"
GENERATION_STATUS_RELEASED = "released"
GENERATION_STATUS_FAILED = "failed"

#: Ledger transaction types (architecture §6).
LEDGER_GRANT = "grant"
LEDGER_CONSUME = "consume"
LEDGER_RESERVE = "reserve"
LEDGER_RELEASE = "release"
LEDGER_EXPIRE = "expire"
LEDGER_ADJUST_POSITIVE = "adjust_positive"
LEDGER_ADJUST_NEGATIVE = "adjust_negative"
LEDGER_REVERSAL = "reversal"


def _utcnow() -> datetime:
    return datetime.now(UTC)


class SubscriptionPlan(Base):
    """Plan shell. ``organization_id`` NULL means a global catalog plan."""

    __tablename__ = "subscription_plans"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "code", name="uq_subscription_plans_org_code"
        ),
        Index(
            "uq_subscription_plans_global_code",
            "code",
            unique=True,
            postgresql_where=text("organization_id IS NULL"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    code = Column(String(60), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    currency = Column(String(3), nullable=False, default="USD")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<SubscriptionPlan(code={self.code}, org={self.organization_id})>"


class SubscriptionPlanVersion(Base):
    """Immutable commercial terms. Only ``draft`` rows may be edited."""

    __tablename__ = "subscription_plan_versions"
    __table_args__ = (
        UniqueConstraint("plan_id", "version", name="uq_plan_versions_plan_version"),
        Index("ix_plan_versions_plan_status", "plan_id", "status"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version = Column(Integer, nullable=False)
    billing_cadence = Column(String(20), nullable=False)  # monthly|quarterly|annually
    base_price = Column(Numeric(15, 2), nullable=False, default=0)
    tax_rate = Column(Numeric(7, 4), nullable=False, default=0)
    included_credits = Column(Numeric(20, 6), nullable=False, default=0)
    id_weight = Column(Numeric(20, 6), nullable=False, default=1)
    topup_allowed = Column(Boolean, nullable=False, default=True)
    effective_from = Column(DateTime(timezone=True), nullable=True)
    effective_to = Column(DateTime(timezone=True), nullable=True)
    status = Column(
        String(20), nullable=False, default=PLAN_VERSION_STATUS_DRAFT, index=True
    )
    approved_by = Column(UUID(as_uuid=True), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<PlanVersion(plan={self.plan_id}, v={self.version}, status={self.status})>"


class OrganizationSubscription(Base):
    """Per-organization contract and billing schedule."""

    __tablename__ = "organization_subscriptions"
    __table_args__ = (
        UniqueConstraint("organization_id", name="uq_organization_subscriptions_org"),
        Index(
            "ix_org_subscriptions_status_next_invoice", "status", "next_invoice_date"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    plan_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plans.id"),
        nullable=False,
        index=True,
    )
    plan_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plan_versions.id"),
        nullable=False,
    )
    status = Column(
        String(30), nullable=False, default=SUBSCRIPTION_STATUS_DRAFT, index=True
    )
    billing_cadence = Column(String(20), nullable=False)
    billing_anchor_day = Column(Integer, nullable=False, default=1)
    billing_timezone = Column(String(64), nullable=False, default="UTC")
    activation_fee = Column(Numeric(15, 2), nullable=False, default=0)
    activation_fee_status = Column(
        String(20), nullable=False, default="not_required"
    )  # not_required|pending|paid
    annual_release_policy = Column(
        String(30), nullable=False, default="monthly_tranches"
    )  # monthly_tranches|upfront
    current_period_start = Column(DateTime(timezone=True), nullable=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    next_invoice_date = Column(Date, nullable=True)
    activated_at = Column(DateTime(timezone=True), nullable=True)
    suspended_at = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    suspended_reason = Column(Text, nullable=True)
    #: Future-effective contract change applied lazily on the effective date.
    pending_plan_version_id = Column(
        UUID(as_uuid=True),
        ForeignKey("subscription_plan_versions.id"),
        nullable=True,
    )
    pending_effective_from = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<OrganizationSubscription(org={self.organization_id}, "
            f"status={self.status})>"
        )


class CreditBatch(Base):
    """A grant of credits with one expiry instant (FEFO unit)."""

    __tablename__ = "credit_batches"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "source_type",
            "source_id",
            name="uq_credit_batches_org_source",
        ),
        Index(
            "ix_credit_batches_org_status_expiry",
            "organization_id",
            "status",
            "expires_at",
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    source_type = Column(String(30), nullable=False)
    source_id = Column(UUID(as_uuid=True), nullable=True)
    granted_qty = Column(Numeric(20, 6), nullable=False)
    consumed_qty = Column(Numeric(20, 6), nullable=False, default=0)
    expired_qty = Column(Numeric(20, 6), nullable=False, default=0)
    reversed_qty = Column(Numeric(20, 6), nullable=False, default=0)
    reserved_qty = Column(Numeric(20, 6), nullable=False, default=0)
    issued_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    status = Column(
        String(20), nullable=False, default=CREDIT_BATCH_STATUS_ACTIVE, index=True
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    @property
    def available_qty(self) -> Decimal:
        return (
            self.granted_qty
            - self.consumed_qty
            - self.reserved_qty
            - self.expired_qty
            - self.reversed_qty
        )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<CreditBatch(org={self.organization_id}, granted={self.granted_qty})>"


class CreditLedger(Base):
    """Append-only credit ledger. ``qty`` is the signed change on availability."""

    __tablename__ = "credit_ledger"
    __table_args__ = (
        Index(
            "uq_credit_ledger_org_idempotency",
            "organization_id",
            "idempotency_key",
            unique=True,
            postgresql_where=text("idempotency_key IS NOT NULL"),
        ),
        Index("ix_credit_ledger_org_occurred", "organization_id", "occurred_at"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    batch_id = Column(
        UUID(as_uuid=True),
        ForeignKey("credit_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type = Column(String(20), nullable=False, index=True)
    qty = Column(Numeric(20, 6), nullable=False)
    balance_after = Column(Numeric(20, 6), nullable=False)
    operation_id = Column(
        UUID(as_uuid=True),
        ForeignKey("generation_operations.id", ondelete="SET NULL"),
        nullable=True,
    )
    reference_type = Column(String(30), nullable=True)
    reference_id = Column(UUID(as_uuid=True), nullable=True)
    idempotency_key = Column(String(120), nullable=True)
    actor_id = Column(UUID(as_uuid=True), nullable=True)
    reason = Column(Text, nullable=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<CreditLedger(org={self.organization_id}, type={self.type}, qty={self.qty})>"


class GenerationOperation(Base):
    """Idempotent unit of credit consumption for ID/QR generation."""

    __tablename__ = "generation_operations"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "operation_key",
            name="uq_generation_operations_org_key",
        ),
        Index(
            "ix_generation_operations_status_reserved_until", "status", "reserved_until"
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    operation_key = Column(String(120), nullable=False)
    id_count = Column(Integer, nullable=False)
    id_weight = Column(Numeric(20, 6), nullable=False)
    debit_qty = Column(Numeric(20, 6), nullable=False)
    status = Column(
        String(20), nullable=False, default=GENERATION_STATUS_RESERVED, index=True
    )
    reserved_until = Column(DateTime(timezone=True), nullable=True)
    generated_count = Column(Integer, nullable=False, default=0)
    #: ``[{batch_id, quantity, expires_at}]`` snapshot used by commit/release.
    allocations = Column(JSONB, nullable=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<GenerationOperation(key={self.operation_key}, status={self.status})>"


class TopupQuote(Base):
    """Short-lived server-side price quote for a credit top-up."""

    __tablename__ = "topup_quotes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    plan_version_id = Column(UUID(as_uuid=True), nullable=True)
    credits = Column(Numeric(20, 6), nullable=False)
    subtotal = Column(Numeric(15, 2), nullable=False)
    tax_amount = Column(Numeric(15, 2), nullable=False, default=0)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    credit_expires_at = Column(DateTime(timezone=True), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    consumed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class TopupOrder(Base):
    """Idempotent checkout order for a top-up."""

    __tablename__ = "topup_orders"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "idempotency_key", name="uq_topup_orders_org_idem"
        ),
        UniqueConstraint("provider_ref", name="uq_topup_orders_provider_ref"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("topup_quotes.id"), nullable=False)
    invoice_id = Column(UUID(as_uuid=True), nullable=True)
    credits = Column(Numeric(20, 6), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(20), nullable=False, default="created", index=True)
    provider = Column(String(30), nullable=True)
    provider_ref = Column(String(191), nullable=True)
    checkout_url = Column(Text, nullable=True)
    idempotency_key = Column(String(120), nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow
    )


class BillingProviderEvent(Base):
    """Deduplicated provider webhook event (never processed twice)."""

    __tablename__ = "billing_provider_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    provider = Column(String(30), nullable=False)
    provider_event_id = Column(String(191), nullable=False, unique=True)
    event_type = Column(String(60), nullable=False)
    payload = Column(JSONB, nullable=True)
    signature_verified = Column(Boolean, nullable=False, default=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)


class BillingOutboxEvent(Base):
    """Transactional outbox for dashboard/notification events."""

    __tablename__ = "billing_outbox_events"
    __table_args__ = (Index("ix_billing_outbox_published", "published_at", "attempts"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    event_type = Column(String(60), nullable=False)
    payload = Column(JSONB, nullable=True)
    attempts = Column(Integer, nullable=False, default=0)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
