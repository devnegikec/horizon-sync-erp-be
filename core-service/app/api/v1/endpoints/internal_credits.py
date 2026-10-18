"""Internal credit operations for ID/QR generation workers."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import require_internal_service
from app.schemas.subscription import (
    CommitRequest,
    RateRequest,
    RateResponse,
    ReleaseRequest,
    ReserveRequest,
    ReserveResponse,
)
from app.services.credit_engine_service import CreditEngineService

router = APIRouter(dependencies=[Depends(require_internal_service)])


@router.post(
    "/rate",
    response_model=RateResponse,
    summary="Quote the weighted debit for an ID count",
)
def rate_generation(
    payload: RateRequest,
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).rate(payload.organization_id, payload.id_count)


@router.post(
    "/reserve",
    response_model=ReserveResponse,
    summary="Reserve credits for a generation operation (idempotent)",
)
def reserve_credits(
    payload: ReserveRequest,
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).reserve(
        payload.organization_id,
        payload.operation_key,
        payload.id_count,
    )


@router.post(
    "/commit",
    response_model=ReserveResponse,
    summary="Commit generated IDs against a reservation",
)
def commit_credits(
    payload: CommitRequest,
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).commit(
        payload.organization_id,
        payload.operation_id,
        payload.generated_count,
    )


@router.post(
    "/release",
    response_model=ReserveResponse,
    summary="Release an unused or failed reservation",
)
def release_credits(
    payload: ReleaseRequest,
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).release(
        payload.organization_id,
        payload.operation_id,
        payload.reason,
    )


@router.post(
    "/expire",
    summary="Run the credit expiry sweep (worker/cron)",
)
def expire_credits(
    organization_id: UUID | None = Query(
        None, description="Reserved for a future org-scoped sweep"
    ),
    db: Session = Depends(get_db),
):
    return CreditEngineService(db).expire_due_batches()
