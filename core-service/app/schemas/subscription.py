"""API contracts for subscription plans, subscriptions and credit ledger."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

CADENCES = ("monthly", "quarterly", "annually")


# ── Plan catalog ────────────────────────────────────────────────────────────


class PlanCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=60)
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = Field(None, max_length=2000)
    currency: str = Field("USD", min_length=3, max_length=3)
    organization_id: UUID | None = Field(
        None, description="NULL creates a global catalog plan"
    )


class PlanVersionCreateRequest(BaseModel):
    billing_cadence: str
    base_price: Decimal = Field(Decimal("0"), ge=0)
    tax_rate: Decimal = Field(Decimal("0"), ge=0, le=100)
    included_credits: Decimal = Field(Decimal("0"), ge=0)
    id_weight: Decimal = Field(Decimal("1"), gt=0)
    topup_allowed: bool = True
    effective_from: datetime | None = None

    @field_validator("billing_cadence")
    @classmethod
    def _cadence(cls, value: str) -> str:
        value = value.lower()
        if value not in CADENCES:
            raise ValueError(f"billing_cadence must be one of {CADENCES}")
        return value


class PlanVersionUpdateRequest(BaseModel):
    billing_cadence: str | None = None
    base_price: Decimal | None = Field(None, ge=0)
    tax_rate: Decimal | None = Field(None, ge=0, le=100)
    included_credits: Decimal | None = Field(None, ge=0)
    id_weight: Decimal | None = Field(None, gt=0)
    topup_allowed: bool | None = None
    effective_from: datetime | None = None

    @field_validator("billing_cadence")
    @classmethod
    def _cadence(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.lower()
        if value not in CADENCES:
            raise ValueError(f"billing_cadence must be one of {CADENCES}")
        return value


class PlanPublishRequest(BaseModel):
    effective_from: datetime | None = None


class PlanRetireRequest(BaseModel):
    effective_to: datetime


class PlanVersionResponse(BaseModel):
    id: UUID
    plan_id: UUID
    version: int
    billing_cadence: str
    base_price: Decimal
    tax_rate: Decimal
    included_credits: Decimal
    id_weight: Decimal
    topup_allowed: bool
    effective_from: datetime | None
    effective_to: datetime | None
    status: str
    approved_by: UUID | None
    approved_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class PlanResponse(BaseModel):
    id: UUID
    organization_id: UUID | None
    code: str
    name: str
    description: str | None
    currency: str
    is_active: bool
    created_at: datetime
    published_version: PlanVersionResponse | None = None

    model_config = {"from_attributes": True}


class PlanDetailResponse(PlanResponse):
    versions: list[PlanVersionResponse] = []


class PlanListResponse(BaseModel):
    items: list[PlanResponse]
    pagination: dict


# ── Organization subscription ───────────────────────────────────────────────


class SubscriptionCreateRequest(BaseModel):
    plan_version_id: UUID
    billing_anchor_day: int = Field(1, ge=1, le=28)
    billing_timezone: str = Field("UTC", min_length=1, max_length=64)
    activation_fee: Decimal = Field(Decimal("0"), ge=0)
    activation_fee_required: bool = False
    annual_release_policy: str = Field(
        "monthly_tranches", pattern="^(monthly_tranches|upfront)$"
    )


class SubscriptionUpdateRequest(BaseModel):
    plan_version_id: UUID | None = None
    billing_anchor_day: int | None = Field(None, ge=1, le=28)
    billing_timezone: str | None = Field(None, min_length=1, max_length=64)
    effective_from: datetime | None = None
    reason: str | None = Field(None, min_length=3, max_length=500)


class SubscriptionReasonRequest(BaseModel):
    reason: str = Field(..., min_length=3, max_length=500)


class PlanSummaryResponse(BaseModel):
    id: UUID
    code: str
    name: str


class PlanVersionSummaryResponse(BaseModel):
    id: UUID
    version: int
    billing_cadence: str
    base_price: Decimal
    currency: str | None = None
    tax_rate: Decimal
    included_credits: Decimal
    id_weight: Decimal
    effective_from: datetime | None


class SubscriptionResponse(BaseModel):
    """Admin + account view of the organization's contract."""

    organization_id: UUID
    plan: PlanSummaryResponse
    plan_version: PlanVersionSummaryResponse
    status: str
    billing_cadence: str
    billing_anchor_day: int
    billing_timezone: str
    activation_fee: Decimal
    activation_fee_status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    next_invoice_date: date | None
    renewal_date: date | None = None
    id_weight: Decimal
    included_credits_per_period: Decimal
    payment_status: str
    grace_until: datetime | None = None
    can_top_up: bool
    activated_at: datetime | None
    suspended_at: datetime | None
    closed_at: datetime | None


# ── Credits ─────────────────────────────────────────────────────────────────


class CreditAdjustmentRequest(BaseModel):
    organization_id: UUID
    direction: str = Field(..., pattern="^(adjust_positive|adjust_negative)$")
    quantity: Decimal = Field(..., gt=0)
    expires_at: datetime | None = None
    reason: str = Field(..., min_length=10, max_length=1000)
    approval_id: UUID | None = None


class EarliestExpiry(BaseModel):
    batch_id: UUID
    expires_at: datetime
    quantity: Decimal


class CreditsResponse(BaseModel):
    available: Decimal
    reserved: Decimal
    used_this_period: Decimal
    expiring_30_days: Decimal
    expiring_60_days: Decimal
    expiring_90_days: Decimal
    earliest_expiry: EarliestExpiry | None
    id_weight: Decimal
    estimated_ids_available: int
    as_of: datetime


class CreditBatchItem(BaseModel):
    id: UUID
    source_type: str
    source_ref: str | None = None
    granted: Decimal
    remaining: Decimal
    issued_at: datetime
    expires_at: datetime
    status: str

    model_config = {"from_attributes": True}


class CreditBatchListResponse(BaseModel):
    items: list[CreditBatchItem]
    pagination: dict


class CreditLedgerItemResponse(BaseModel):
    id: UUID
    batch_id: UUID | None
    type: str
    qty: Decimal
    balance_after: Decimal
    operation_id: UUID | None
    reference_type: str | None
    reference_id: UUID | None
    reason: str | None
    occurred_at: datetime

    model_config = {"from_attributes": True}


class CreditLedgerListResponse(BaseModel):
    transactions: list[CreditLedgerItemResponse]
    pagination: dict


class ExpiryBucket(BaseModel):
    within_30_days: Decimal
    within_60_days: Decimal
    within_90_days: Decimal


class ExpiryTimelineItem(BaseModel):
    batch_id: UUID
    expires_at: datetime
    quantity: Decimal
    source: str


class ExpirationsResponse(BaseModel):
    buckets: ExpiryBucket
    timeline: list[ExpiryTimelineItem]


# ── Invoices (account) ──────────────────────────────────────────────────────


class AccountInvoiceItem(BaseModel):
    id: UUID
    invoice_no: str
    invoice_type: str
    posting_date: datetime
    due_date: datetime | None
    status: str
    subtotal: Decimal
    tax_total: Decimal
    grand_total: Decimal
    outstanding_amount: Decimal
    currency: str
    download_url: str | None = None

    model_config = {"from_attributes": True}


class AccountInvoiceListResponse(BaseModel):
    items: list[AccountInvoiceItem]
    pagination: dict


# ── Top-ups ─────────────────────────────────────────────────────────────────


class TopupQuoteRequest(BaseModel):
    credits: Decimal = Field(..., gt=0)


class TopupQuoteResponse(BaseModel):
    quote_id: UUID
    credits: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str
    expires_at: datetime
    credit_expires_at: datetime


class TopupOrderRequest(BaseModel):
    quote_id: UUID
    provider: str | None = Field(None, max_length=30)


class TopupOrderResponse(BaseModel):
    order_id: UUID
    status: str
    checkout_url: str | None
    amount: Decimal
    currency: str
    credits: Decimal

    model_config = {"from_attributes": True}


# ── Internal generation operations ──────────────────────────────────────────


class ReserveRequest(BaseModel):
    organization_id: UUID
    operation_key: str = Field(..., min_length=1, max_length=120)
    id_count: int = Field(..., ge=1)


class ReservationAllocation(BaseModel):
    batch_id: UUID
    quantity: Decimal
    expires_at: datetime


class ReserveResponse(BaseModel):
    operation_id: UUID
    operation_key: str
    id_weight: Decimal
    debit: Decimal
    reserved_until: datetime
    allocations: list[ReservationAllocation]


class CommitRequest(BaseModel):
    organization_id: UUID
    operation_id: UUID
    generated_count: int = Field(..., ge=0)


class ReleaseRequest(BaseModel):
    organization_id: UUID
    operation_id: UUID
    reason: str | None = Field(None, max_length=500)


class RateRequest(BaseModel):
    organization_id: UUID
    id_count: int = Field(..., ge=1)


class RateResponse(BaseModel):
    id_weight: Decimal
    debit: Decimal


# ── Admin reporting ─────────────────────────────────────────────────────────


class ExposureItem(BaseModel):
    organization_id: UUID
    subscription_status: str | None
    available: Decimal
    reserved: Decimal
    expiring_30_days: Decimal
    earliest_expiry: datetime | None


class ExposureResponse(BaseModel):
    items: list[ExposureItem]
    totals: dict


class ReconciliationItem(BaseModel):
    issue: str
    organization_id: UUID | None
    reference_type: str | None
    reference_id: UUID | None
    detail: str


class ReconciliationResponse(BaseModel):
    items: list[ReconciliationItem]
