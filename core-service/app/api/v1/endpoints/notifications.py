"""Notifications API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.core.authorization import ASN_ORDER_READ
from app.dependencies import CurrentUser, require_permission
from app.schemas.notification import (
    NotificationCountResponse,
    NotificationListResponse,
    NotificationResponse,
    NotificationUpdate,
)
from app.services.notification_service import NotificationService

router = APIRouter()


@router.get("", response_model=NotificationListResponse)
async def list_notifications(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False, description="Filter to unread notifications only"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """List notifications for the current user."""
    svc = NotificationService(db)
    items, pagination, unread_count = svc.get_user_notifications(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        unread_only=unread_only,
        entity_type=entity_type,
    )
    return NotificationListResponse(
        notifications=[NotificationResponse.model_validate(x) for x in items],
        unread_count=unread_count,
        pagination=pagination,
    )


@router.get("/count", response_model=NotificationCountResponse)
async def get_notification_count(
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """Get total and unread notification count for the current user."""
    svc = NotificationService(db)
    total, unread = svc.get_counts(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    return NotificationCountResponse(total=total, unread=unread)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: UUID,
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    svc = NotificationService(db)
    notification = svc.mark_read(
        notification_id=notification_id,
        user_id=current_user.id,
    )
    return NotificationResponse.model_validate(notification)


@router.patch("/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    current_user: CurrentUser = Depends(require_permission(ASN_ORDER_READ)),
    db: Session = Depends(get_db),
):
    """Mark all notifications as read for the current user."""
    svc = NotificationService(db)
    svc.mark_all_read(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
    )
    return None
