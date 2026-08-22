"""Stock movements API endpoints (append-only log)"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.stock_entry import _resolve_asn_numbers_in_remarks
from app.schemas.stock_movement import (
    StockMovementCreate,
    StockMovementListResponse,
    StockMovementResponse,
    stock_movement_to_list_item,
    stock_movement_to_response,
)
from app.services.stock_movement_service import StockMovementService

router = APIRouter()


def _resolve_user_names(user_ids: set[str]) -> dict[str, str]:
    """Batch-resolve user_id → full name from the identity DB (read-only)."""
    if not user_ids:
        return {}
    try:
        from app.config import settings

        if not settings.identity_database_url:
            return {}
        from sqlalchemy import create_engine, text

        engine = create_engine(
            settings.identity_database_url, pool_size=2, max_overflow=0
        )
        placeholders = ", ".join(f"'{uid}'" for uid in user_ids)
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT id::text, first_name, last_name "
                    f"FROM users WHERE id::text IN ({placeholders})"
                )
            ).fetchall()
            return {r[0]: f"{r[1] or ''} {r[2] or ''}".strip() or None for r in rows}
    except Exception:
        return {}


@router.post(
    "", response_model=StockMovementResponse, status_code=status.HTTP_201_CREATED
)
async def create_stock_movement(
    data: StockMovementCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Record a stock movement (in, out, transfer, adjustment)."""
    svc = StockMovementService(db)
    m = svc.create(data, current_user.organization_id, current_user.id)
    return stock_movement_to_response(m)


@router.get("", response_model=StockMovementListResponse)
async def list_stock_movements(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    item_id: UUID | None = Query(None, description="Filter by item (product) ID"),
    warehouse_id: UUID | None = Query(None),
    movement_type: str | None = Query(
        None, description="in, out, transfer, adjustment"
    ),
    reference_type: str | None = None,
    reference_id: UUID | None = None,
    search: str | None = Query(
        None, description="Search by item name, item code or notes"
    ),
    sort_by: str = Query("performed_at"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List stock movements with filters."""
    svc = StockMovementService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        product_id=item_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        reference_type=reference_type,
        reference_id=reference_id,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    user_ids = {str(m.performed_by) for m in items if m.performed_by}
    name_map = _resolve_user_names(user_ids)

    # Resolve stock_entry reference_ids to their human-readable numbers
    entry_no_map: dict[str, str] = {}
    ref_ids = {
        m.reference_id
        for m in items
        if m.reference_type == "stock_entry" and m.reference_id
    }
    if ref_ids:
        from app.models.stock_entry import StockEntry

        rows = (
            db.query(StockEntry.id, StockEntry.stock_entry_no)
            .filter(StockEntry.id.in_(ref_ids))
            .all()
        )
        entry_no_map = {str(r[0]): r[1] for r in rows}

    return StockMovementListResponse(
        stock_movements=[
            stock_movement_to_list_item(
                m,
                performed_by_name=(
                    name_map.get(str(m.performed_by)) if m.performed_by else None
                ),
                reference_no=(
                    entry_no_map.get(str(m.reference_id))
                    if m.reference_type == "stock_entry" and m.reference_id
                    else None
                ),
                notes=_resolve_asn_numbers_in_remarks(m.notes, db),
            )
            for m in items
        ],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{movement_id}", response_model=StockMovementResponse)
async def get_stock_movement(
    movement_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get a stock movement by ID."""
    svc = StockMovementService(db)
    return stock_movement_to_response(
        svc.get_by_id(movement_id, current_user.organization_id)
    )
