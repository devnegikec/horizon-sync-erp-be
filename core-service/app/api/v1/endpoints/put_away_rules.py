"""Put away rules API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.put_away_rule import (
    PutAwayRuleCreate,
    PutAwayRuleListItem,
    PutAwayRuleListResponse,
    PutAwayRuleResponse,
    PutAwayRuleUpdate,
)
from app.services.put_away_rule_service import PutAwayRuleService

router = APIRouter()


@router.post(
    "", response_model=PutAwayRuleResponse, status_code=status.HTTP_201_CREATED
)
async def create_put_away_rule(
    data: PutAwayRuleCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Create a put away rule."""
    svc = PutAwayRuleService(db)
    r = svc.create(data, current_user.organization_id, current_user.id)
    return PutAwayRuleResponse.model_validate(r)


@router.get("", response_model=PutAwayRuleListResponse)
async def list_put_away_rules(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    warehouse_id: UUID | None = Query(None),
    item_id: UUID | None = Query(None),
    item_group_id: UUID | None = Query(None),
    is_active: bool | None = Query(None),
    search: str | None = None,
    sort_by: str = Query("priority"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List put away rules with filters."""
    svc = PutAwayRuleService(db)
    items, pagination = svc.get_list(
        organization_id=current_user.organization_id,
        warehouse_id=warehouse_id,
        item_id=item_id,
        item_group_id=item_group_id,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
    )
    return PutAwayRuleListResponse(
        put_away_rules=[PutAwayRuleListItem.model_validate(r) for r in items],
        pagination=PaginationMeta(**pagination),
    )


@router.get("/{rule_id}", response_model=PutAwayRuleResponse)
async def get_put_away_rule(
    rule_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Get put away rule by ID."""
    svc = PutAwayRuleService(db)
    return PutAwayRuleResponse.model_validate(
        svc.get_by_id(rule_id, current_user.organization_id)
    )


@router.put("/{rule_id}", response_model=PutAwayRuleResponse)
async def update_put_away_rule(
    rule_id: UUID,
    data: PutAwayRuleUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update a put away rule."""
    svc = PutAwayRuleService(db)
    r = svc.update(rule_id, data, current_user.organization_id, current_user.id)
    return PutAwayRuleResponse.model_validate(r)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_put_away_rule(
    rule_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Delete a put away rule."""
    PutAwayRuleService(db).delete(rule_id, current_user.organization_id)
    return None
