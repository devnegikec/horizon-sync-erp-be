"""WMS Device service"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.wms_device import WMSDevice
from app.schemas.common import PaginationMeta


class WMSDeviceService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, organization_id: uuid.UUID, created_by: uuid.UUID | None = None) -> WMSDevice:
        payload = dict(data)
        payload["organization_id"] = organization_id
        if created_by:
            payload["created_by"] = created_by

        device = WMSDevice(**payload)
        self.db.add(device)
        self.db.flush()
        self.db.commit()
        self.db.refresh(device)
        return device

    def get_by_id(self, device_id: uuid.UUID, organization_id: uuid.UUID) -> WMSDevice:
        device = (
            self.db.query(WMSDevice)
            .filter(WMSDevice.id == device_id, WMSDevice.organization_id == organization_id)
            .first()
        )
        if not device:
            raise ResourceNotFoundException("WMSDevice", str(device_id))
        return device

    def get_list(
        self,
        organization_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[WMSDevice], PaginationMeta]:
        query = self.db.query(WMSDevice).filter(
            WMSDevice.organization_id == organization_id,
        )

        if warehouse_id:
            query = query.filter(WMSDevice.warehouse_id == warehouse_id)
        if status:
            query = query.filter(WMSDevice.status == status)
        if search:
            query = query.filter(
                (WMSDevice.name.ilike(f"%{search}%"))
                | (WMSDevice.device_code.ilike(f"%{search}%"))
                | (WMSDevice.serial_number.ilike(f"%{search}%"))
            )

        total = query.count()
        results = (
            query.order_by(WMSDevice.name)
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
        return results, pagination

    def update(
        self,
        device_id: uuid.UUID,
        data: dict,
        organization_id: uuid.UUID,
    ) -> WMSDevice:
        device = self.get_by_id(device_id, organization_id)
        payload = {k: v for k, v in data.items() if v is not None}
        for key, value in payload.items():
            if hasattr(device, key):
                setattr(device, key, value)
        self.db.flush()
        self.db.commit()
        self.db.refresh(device)
        return device

    def delete(self, device_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        device = self.get_by_id(device_id, organization_id)
        self.db.delete(device)
        self.db.flush()
        self.db.commit()
