"""Admin endpoints for subscription plans, contracts and credit adjustments."""

from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.authorization import (
    SYSTEM_ADMIN_BILLING_CREATE,
    SYSTEM_ADMIN_BILLING_READ,
    SYSTEM_ADMIN_BILLING_UPDATE,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.subscription import (
    CreditAdjustmentRequest,
    ExposureResponse,
    PlanCreateRequest,
    PlanDetailResponse,
    PlanListResponse,
    PlanPublishRequest,
    PlanResponse,
    PlanRetireRequest,
    PlanVersionCreateRequest,
    PlanVersionResponse,
    PlanVersionUpdateRequest,
    ReconciliationResponse,
    SubscriptionCreateRequest,
    SubscriptionReasonRequest,
    SubscriptionResponse,
    SubscriptionUpdateRequest,
)
from app.services.credit_engine_service import CreditEngineService
from app.services.subscription_plan_service import SubscriptionPlanService
from app.services.subscription_service import SubscriptionService

router = APIRouter()


# ── Plan catalog ────────────────────────────────────────────────────────────


@router.get(
    "/subscription-plans",
    response_model=PlanListResponse,
    summary="List subscription plans",
)
def list_plans(
    organization_id: UUID | None = Query(None),
    active: bool | None = Query(None),
    q: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_READ)),
    db: Session = Depends(get_db),
):
    return SubscriptionPlanService(db).list_plans(
        organization_id=organization_id,
        active=active,
        q=q,
        page=page,
        page_size=page_size,
    )


@router.post(
    "/subscription-plans",
    response_model=PlanResponse,
    status_code=201,
    summary="Create a subscription plan",
)
def create_plan(
    payload: PlanCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(
        require_permission(SYSTEM_ADMIN_BILLING_CREATE)
    ),
    db: Session = Depends(get_db),
):
    return SubscriptionPlanService(db).create_plan(payload, current_user.id)


@router.get(
    "/subscription-plans/{plan_id}",
    response_model=PlanDetailResponse,
    summary="Get a plan and its versions",
)
def get_plan(
    plan_id: UUID,
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_READ)),
    db: Session = Depends(get_db),
):
    return SubscriptionPlanService(db).get_plan_detail(plan_id)


@router.post(
    "/subscription-plans/{plan_id}/versions",
    response_model=PlanVersionResponse,
    status_code=201,
    summary="Create a draft plan version",
)
def create_plan_version(
    plan_id: UUID,
    payload: PlanVersionCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(
        require_permission(SYSTEM_ADMIN_BILLING_CREATE)
    ),
    db: Session = Depends(get_db),
):
    return SubscriptionPlanService(db).create_version(plan_id, payload, current_user.id)


@router.patch(
    "/subscription-plans/{plan_id}/versions/{version_id}",
    response_model=PlanVersionResponse,
    summary="Edit a draft plan version",
)
def update_plan_version(
    plan_id: UUID,
    version_id: UUID,
    payload: PlanVersionUpdateRequest,
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_UPDATE)),
    db: Session = Depends(get_db),
):
    return SubscriptionPlanService(db).update_version(plan_id, version_id, payload)


@router.post(
    "/subscription-plans/{plan_id}/versions/{version_id}/approve",
    response_model=PlanVersionResponse,
    summary="Approve a draft plan version",
)
def approve_plan_version(
    plan_id: UUID,
    version_id: UUID,
    current_user: CurrentUser = Depends(
        require_permission(SYSTEM_ADMIN_BILLING_UPDATE)
    ),
    db: Session = Depends(get_db),
):
    return SubscriptionPlanService(db).approve_version(
        plan_id, version_id, current_user.id
    )


@router.post(
    "/subscription-plans/{plan_id}/versions/{version_id}/publish",
    response_model=PlanVersionResponse,
    summary="Publish an approved plan version",
)
def publish_plan_version(
    plan_id: UUID,
    version_id: UUID,
    payload: PlanPublishRequest,
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_UPDATE)),
    db: Session = Depends(get_db),
):
    return SubscriptionPlanService(db).publish_version(plan_id, version_id, payload)


@router.post(
    "/subscription-plans/{plan_id}/versions/{version_id}/retire",
    response_model=PlanVersionResponse,
    summary="Retire a published plan version",
)
def retire_plan_version(
    plan_id: UUID,
    version_id: UUID,
    payload: PlanRetireRequest,
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_UPDATE)),
    db: Session = Depends(get_db),
):
    return SubscriptionPlanService(db).retire_version(plan_id, version_id, payload)


# ── Organization subscriptions ──────────────────────────────────────────────


@router.get(
    "/organizations/{org_id}/subscription",
    response_model=SubscriptionResponse,
    summary="Get an organization subscription",
)
def get_organization_subscription(
    org_id: UUID,
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_READ)),
    db: Session = Depends(get_db),
):
    return SubscriptionService(db).get_snapshot(org_id)


@router.post(
    "/organizations/{org_id}/subscription",
    response_model=SubscriptionResponse,
    status_code=201,
    summary="Create an organization subscription",
)
def create_organization_subscription(
    org_id: UUID,
    payload: SubscriptionCreateRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(
        require_permission(SYSTEM_ADMIN_BILLING_CREATE)
    ),
    db: Session = Depends(get_db),
):
    return SubscriptionService(db).create_subscription(org_id, payload, current_user.id)


@router.patch(
    "/organizations/{org_id}/subscription",
    response_model=SubscriptionResponse,
    summary="Update an organization subscription (effective-dated version change)",
)
def update_organization_subscription(
    org_id: UUID,
    payload: SubscriptionUpdateRequest,
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_UPDATE)),
    db: Session = Depends(get_db),
):
    return SubscriptionService(db).update_subscription(org_id, payload)


@router.post(
    "/organizations/{org_id}/subscription/activate",
    response_model=SubscriptionResponse,
    summary="Mark activation paid after a verified payment",
)
def activate_organization_subscription(
    org_id: UUID,
    reference: str | None = Query(None),
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_UPDATE)),
    db: Session = Depends(get_db),
):
    return SubscriptionService(db).activate(org_id, reference=reference)


@router.post(
    "/organizations/{org_id}/subscription/suspend",
    response_model=SubscriptionResponse,
    summary="Suspend an organization subscription",
)
def suspend_organization_subscription(
    org_id: UUID,
    payload: SubscriptionReasonRequest,
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_UPDATE)),
    db: Session = Depends(get_db),
):
    return SubscriptionService(db).suspend(org_id, payload.reason)


@router.post(
    "/organizations/{org_id}/subscription/reinstate",
    response_model=SubscriptionResponse,
    summary="Reinstate a suspended organization subscription",
)
def reinstate_organization_subscription(
    org_id: UUID,
    payload: SubscriptionReasonRequest,
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_UPDATE)),
    db: Session = Depends(get_db),
):
    return SubscriptionService(db).reinstate(org_id, payload.reason)


@router.post(
    "/organizations/{org_id}/subscription/close",
    response_model=SubscriptionResponse,
    summary="Close an organization subscription",
)
def close_organization_subscription(
    org_id: UUID,
    payload: SubscriptionReasonRequest,
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_UPDATE)),
    db: Session = Depends(get_db),
):
    return SubscriptionService(db).close(org_id, payload.reason)


# ── Credits and reporting ───────────────────────────────────────────────────


@router.post(
    "/credits/adjustments",
    status_code=201,
    summary="Apply a positive or negative credit adjustment",
)
def create_credit_adjustment(
    payload: CreditAdjustmentRequest,
    idempotency_key: str = Header(..., alias="Idempotency-Key"),
    current_user: CurrentUser = Depends(
        require_permission(SYSTEM_ADMIN_BILLING_UPDATE)
    ),
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).adjust(
        organization_id=payload.organization_id,
        direction=payload.direction,
        quantity=payload.quantity,
        reason=payload.reason,
        expires_at=payload.expires_at,
        actor_id=current_user.id,
        idempotency_key=idempotency_key,
    )


@router.get(
    "/subscriptions/exposure",
    response_model=ExposureResponse,
    summary="Cross-organization credit exposure",
)
def subscription_exposure(
    expiring_within_days: int = Query(30, ge=1, le=180),
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_READ)),
    db: Session = Depends(get_db),
):
    return SubscriptionService(db).get_exposure(expiring_within_days)


@router.get(
    "/subscriptions/reconciliation",
    response_model=ReconciliationResponse,
    summary="Invoice / credit grant reconciliation findings",
)
def subscription_reconciliation(
    _user: CurrentUser = Depends(require_permission(SYSTEM_ADMIN_BILLING_READ)),
    db: Session = Depends(get_db),
):
    return SubscriptionService(db).get_reconciliation()
