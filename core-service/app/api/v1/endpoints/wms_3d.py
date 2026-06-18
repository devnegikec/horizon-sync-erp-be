"""3D Warehouse View & Smart Location Engine API endpoints.

Exposes:
- GET  /wms-3d/layout    — procedural 3D geometry tree
- GET  /wms-3d/status    — live bin fill/reservation snapshot (polling fallback)
- POST /wms-3d/suggest   — ranked optimal-bin suggestions (put-away / pick)
- POST /wms-3d/reserve   — atomically reserve a bin for a worker
- POST /wms-3d/release   — release a worker's reservation
- POST /wms-3d/force-release/{bin_id} — manager override
- WS   /wms-3d/ws        — real-time bin events via Redis Pub/Sub (Phase 3)

Design ref: docs/3D_WAREHOUSE_VIEW_DESIGN.md section 5
"""

import asyncio
import logging
from datetime import UTC, datetime
from uuid import UUID

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from app.core.authorization import (
    WAREHOUSE_CREATE,
    WAREHOUSE_MANAGE,
    WAREHOUSE_READ,
)
from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.wms_3d import (
    BinStockDetailResponse,
    LayoutResponse,
    ReleaseRequest,
    ReleaseResponse,
    ReservationResponse,
    ReserveRequest,
    StatusResponse,
    SuggestRequest,
    SuggestResponse,
)
from app.services.bin_reservation_service import BinReservationService
from app.services.location_suggestion_service import LocationSuggestionService
from app.services.warehouse_3d_service import Warehouse3DService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/layout", response_model=LayoutResponse, summary="Get 3D layout")
async def get_layout(
    warehouse_id: UUID = Query(...),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Return the full procedural geometry tree for a warehouse."""
    service = Warehouse3DService(db)
    return service.get_layout(warehouse_id, current_user.organization_id)


@router.get("/status", response_model=StatusResponse, summary="Get live bin status")
async def get_status(
    warehouse_id: UUID = Query(...),
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Return current bin fill/reservation status (polling fallback)."""
    service = Warehouse3DService(db)
    return service.get_status(warehouse_id, current_user.organization_id)


@router.get(
    "/bin/{bin_id}/stock",
    response_model=BinStockDetailResponse,
    summary="Get bin stock details",
)
async def get_bin_stock_detail(
    bin_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Return individual item records stored in a specific bin (FR-3D-04).

    Shows item names, SKUs, quantities, batch numbers, and expiry dates
    for all stock currently held in the requested bin.
    """
    service = Warehouse3DService(db)
    return service.get_bin_stock_detail(bin_id, current_user.organization_id)


@router.post("/suggest", response_model=SuggestResponse, summary="Suggest bins")
async def suggest_locations(
    body: SuggestRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_READ)),
    db: Session = Depends(get_db),
):
    """Return ranked optimal-bin suggestions for a put-away or pick task."""
    service = LocationSuggestionService(db)
    worker_position = None
    if body.worker_position is not None:
        worker_position = (
            body.worker_position.x,
            body.worker_position.y,
            body.worker_position.z,
        )
    return service.suggest(
        task_type=body.task_type,
        item_id=body.item_id,
        quantity=body.quantity,
        warehouse_id=body.warehouse_id,
        worker_id=body.worker_id,
        org_id=current_user.organization_id,
        batch_number=body.batch_number,
        exclude_bin_ids=body.exclude_bin_ids,
        worker_position=worker_position,
        limit=body.limit,
    )


@router.post("/reserve", response_model=ReservationResponse, summary="Reserve a bin")
async def reserve_bin(
    body: ReserveRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """Atomically reserve a bin for a worker (TTL-bound)."""
    service = BinReservationService(db)
    reservation = service.reserve(
        bin_id=body.bin_id,
        worker_id=body.worker_id,
        org_id=current_user.organization_id,
        task_id=body.task_id,
        task_type=body.task_type,
        ttl_seconds=body.ttl_seconds,
    )
    return _reservation_to_response(reservation)


@router.post("/release", response_model=ReleaseResponse, summary="Release a bin")
async def release_bin(
    body: ReleaseRequest,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_CREATE)),
    db: Session = Depends(get_db),
):
    """Release a worker's reservation on a bin (e.g. 'Skip')."""
    service = BinReservationService(db)
    released = service.release(
        bin_id=body.bin_id,
        worker_id=body.worker_id,
        org_id=current_user.organization_id,
    )
    return ReleaseResponse(released=released, bin_id=body.bin_id)


@router.post(
    "/force-release/{bin_id}",
    response_model=ReleaseResponse,
    summary="Force-release a bin (manager)",
)
async def force_release_bin(
    bin_id: UUID,
    current_user: CurrentUser = Depends(require_permission(WAREHOUSE_MANAGE)),
    db: Session = Depends(get_db),
):
    """Manager override — clear any active reservation on a bin (FR-CW-04)."""
    service = BinReservationService(db)
    released = service.force_release(bin_id, current_user.organization_id)
    return ReleaseResponse(released=released, bin_id=bin_id)


@router.websocket("/ws")
async def warehouse_realtime_ws(
    websocket: WebSocket,
    warehouse_id: UUID = Query(...),
    token: str = Query(...),
):
    """WebSocket endpoint — streams real-time bin events to connected clients.

    Authentication: pass the Bearer access token as the ``token`` query param
    (standard browsers cannot set custom headers on WebSocket upgrades).

    Each message is a JSON object:
      {"type": "bin_reserved"|"bin_released", "bin_id": "...", "warehouse_id": "...", ...}

    Clients should merge incoming events into their local status state instead
    of waiting for the 5-second polling interval.
    """
    from app.config import settings
    from app.core.security import decode_token

    # Authenticate before accepting (close with 4001 on failure)
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        await websocket.close(code=4001)
        return

    await websocket.accept()

    channel = f"warehouse:3d:{warehouse_id}"
    redis_client = aioredis.from_url(settings.redis_warehouse_url, decode_responses=True)
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(channel)
    logger.info("WS client connected to channel %s", channel)

    async def _forward_redis_to_ws() -> None:
        """Read Redis Pub/Sub messages and forward them to the WebSocket."""
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    await websocket.send_text(message["data"])
                except Exception:
                    return  # client gone — exit the loop

    forward_task = asyncio.create_task(_forward_redis_to_ws())
    try:
        # Keep the handler alive; detect client disconnect via receive_text()
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, Exception):
        pass
    finally:
        forward_task.cancel()
        try:
            await forward_task
        except asyncio.CancelledError:
            pass
        await pubsub.unsubscribe(channel)
        await pubsub.aclose()
        await redis_client.aclose()
        logger.info("WS client disconnected from channel %s", channel)


def _reservation_to_response(reservation) -> ReservationResponse:
    now = datetime.now(UTC)
    expires_at = reservation.expires_at
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    expires_in = max(0, int((expires_at - now).total_seconds())) if expires_at else 0
    return ReservationResponse(
        id=reservation.id,
        bin_id=reservation.bin_location_id,
        worker_id=reservation.worker_id,
        task_id=reservation.task_id,
        task_type=reservation.task_type,
        reserved_at=reservation.reserved_at.isoformat()
        if reservation.reserved_at
        else "",
        expires_at=expires_at.isoformat() if expires_at else "",
        expires_in_seconds=expires_in,
    )
