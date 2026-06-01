"""Notification service for WMS/ASN in-app notifications"""

from uuid import UUID

from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.schemas.common import PaginationMeta


class NotificationService:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        organization_id: UUID,
        user_id: UUID,
        type: str,
        title: str,
        message: str,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        entity_no: str | None = None,
        warehouse_id: UUID | None = None,
        sender_id: UUID | None = None,
        sender_name: str | None = None,
        extra_data: dict | None = None,
    ) -> Notification:
        """Create a notification for a specific user."""
        notification = Notification(
            organization_id=organization_id,
            user_id=user_id,
            type=type,
            title=title,
            message=message,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_no=entity_no,
            warehouse_id=warehouse_id,
            sender_id=sender_id,
            sender_name=sender_name,
            extra_data=extra_data or {},
        )
        self.db.add(notification)
        self.db.flush()
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def create_for_warehouse_users(
        self,
        organization_id: UUID,
        warehouse_id: UUID | None,
        type: str,
        title: str,
        message: str,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        entity_no: str | None = None,
        sender_id: UUID | None = None,
        sender_name: str | None = None,
        extra_data: dict | None = None,
        exclude_user_id: UUID | None = None,
    ) -> list[Notification]:
        """Create notifications for all users assigned to a warehouse.

        If warehouse_id is None, notifications are sent to all org users
        with relevant warehouse assignments.
        """
        from app.models.warehouse_user import WarehouseUser

        query = self.db.query(WarehouseUser).filter(
            WarehouseUser.organization_id == organization_id,
            WarehouseUser.is_active == True,
        )
        if warehouse_id:
            # Notify users explicitly assigned to this warehouse OR primary users
            # (is_primary=True means access to all warehouses in the org)
            query = query.filter(
                (WarehouseUser.warehouse_id == warehouse_id)
                | (WarehouseUser.is_primary == True)
            )
        if exclude_user_id:
            query = query.filter(WarehouseUser.user_id != exclude_user_id)

        assignments = query.all()

        # Deduplicate by user_id — a primary user may also be explicitly assigned
        seen_user_ids = set()
        unique_assignments = []
        for a in assignments:
            if a.user_id not in seen_user_ids:
                seen_user_ids.add(a.user_id)
                unique_assignments.append(a)

        created = []
        for assignment in unique_assignments:
            n = self.create(
                organization_id=organization_id,
                user_id=assignment.user_id,
                type=type,
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_no=entity_no,
                warehouse_id=warehouse_id,
                sender_id=sender_id,
                sender_name=sender_name,
                extra_data=extra_data,
            )
            created.append(n)
        return created

    def create_for_role_users(
        self,
        organization_id: UUID,
        role: str,
        type: str,
        title: str,
        message: str,
        entity_type: str | None = None,
        entity_id: UUID | None = None,
        entity_no: str | None = None,
        sender_id: UUID | None = None,
        sender_name: str | None = None,
        extra_data: dict | None = None,
        exclude_user_id: UUID | None = None,
    ) -> list[Notification]:
        """Create notifications for all users with a given warehouse role.

        Used as a fallback when no users are explicitly assigned to a target
        warehouse (e.g. notify WMS Supervisors about an ASN for an unstaffed
        warehouse).
        """
        from app.models.warehouse_user import WarehouseUser
        from app.models.base import WarehouseUserRole

        try:
            role_enum = WarehouseUserRole(role)
        except ValueError:
            return []

        query = self.db.query(WarehouseUser).filter(
            WarehouseUser.organization_id == organization_id,
            WarehouseUser.role == role_enum,
            WarehouseUser.is_active == True,
        )
        if exclude_user_id:
            query = query.filter(WarehouseUser.user_id != exclude_user_id)

        assignments = query.all()
        created = []
        for assignment in assignments:
            n = self.create(
                organization_id=organization_id,
                user_id=assignment.user_id,
                type=type,
                title=title,
                message=message,
                entity_type=entity_type,
                entity_id=entity_id,
                entity_no=entity_no,
                warehouse_id=assignment.warehouse_id,
                sender_id=sender_id,
                sender_name=sender_name,
                extra_data=extra_data,
            )
            created.append(n)
        return created

    def get_user_notifications(
        self,
        user_id: UUID,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
        entity_type: str | None = None,
    ) -> tuple[list[Notification], PaginationMeta, int]:
        """Get notifications for a user with pagination."""
        query = self.db.query(Notification).filter(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
        )
        if unread_only:
            query = query.filter(Notification.is_read == False)
        if entity_type:
            query = query.filter(Notification.entity_type == entity_type)

        total = query.count()
        unread_count = (
            self.db.query(Notification)
            .filter(
                Notification.organization_id == organization_id,
                Notification.user_id == user_id,
                Notification.is_read == False,
            )
            .count()
        )

        items = (
            query.order_by(desc(Notification.created_at))
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        pagination = PaginationMeta(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size,
            has_next=page * page_size < total,
            has_prev=page > 1,
        )
        return items, pagination, unread_count

    def get_counts(self, user_id: UUID, organization_id: UUID) -> tuple[int, int]:
        """Return (total, unread) notification counts."""
        base_query = self.db.query(Notification).filter(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
        )
        total = base_query.count()
        unread = base_query.filter(Notification.is_read == False).count()
        return total, unread

    def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification:
        """Mark a notification as read."""
        from datetime import UTC, datetime

        notification = (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if not notification:
            raise ValueError("Notification not found")

        notification.is_read = True
        notification.read_at = datetime.now(UTC)
        self.db.flush()
        self.db.commit()
        self.db.refresh(notification)
        return notification

    def mark_all_read(self, user_id: UUID, organization_id: UUID) -> None:
        """Mark all notifications as read for a user."""
        from datetime import UTC, datetime

        self.db.query(Notification).filter(
            Notification.organization_id == organization_id,
            Notification.user_id == user_id,
            Notification.is_read == False,
        ).update(
            {"is_read": True, "read_at": datetime.now(UTC)},
            synchronize_session=False,
        )
        self.db.commit()
