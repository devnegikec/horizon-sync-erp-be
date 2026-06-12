"""WMS Worker service"""

import secrets
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.core.security import hash_password, verify_password
from app.models.wms_worker import WMSWorker, WMSWorkerStatus
from app.schemas.common import PaginationMeta


class WMSWorkerService:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, organization_id: uuid.UUID, created_by: uuid.UUID | None = None) -> WMSWorker:
        payload = dict(data)
        payload["organization_id"] = organization_id
        if created_by:
            payload["created_by"] = created_by

        # Hash password if provided
        password = payload.pop("password", None)
        if password:
            payload["password_hash"] = hash_password(password)

        # Enforce unique employee_id per org if provided
        employee_id = payload.get("employee_id")
        if employee_id:
            existing = (
                self.db.query(WMSWorker)
                .filter(
                    WMSWorker.organization_id == organization_id,
                    WMSWorker.employee_id == employee_id,
                )
                .first()
            )
            if existing:
                from fastapi import HTTPException, status as http_status
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail=f"Employee ID '{employee_id}' is already in use by another worker in this organization.",
                )

        # Generate barcode if not provided
        if not payload.get("barcode"):
            payload["barcode"] = self._generate_barcode()

        worker = WMSWorker(**payload)
        self.db.add(worker)
        self.db.flush()
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def get_by_id(self, worker_id: uuid.UUID, organization_id: uuid.UUID) -> WMSWorker:
        worker = (
            self.db.query(WMSWorker)
            .filter(WMSWorker.id == worker_id, WMSWorker.organization_id == organization_id)
            .first()
        )
        if not worker:
            raise ResourceNotFoundException("WMSWorker", str(worker_id))
        return worker

    def get_by_barcode(self, barcode: str, organization_id: uuid.UUID | None = None) -> WMSWorker | None:
        query = self.db.query(WMSWorker).filter(WMSWorker.barcode == barcode, WMSWorker.is_active == True)
        if organization_id:
            query = query.filter(WMSWorker.organization_id == organization_id)
        return query.first()

    def get_list(
        self,
        organization_id: uuid.UUID,
        warehouse_id: uuid.UUID | None = None,
        status: str | None = None,
        search: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[WMSWorker], PaginationMeta]:
        query = self.db.query(WMSWorker).filter(
            WMSWorker.organization_id == organization_id,
        )

        if warehouse_id:
            query = query.filter(WMSWorker.warehouse_id == warehouse_id)
        if status:
            query = query.filter(WMSWorker.status == status)
        if search:
            query = query.filter(
                (WMSWorker.first_name.ilike(f"%{search}%"))
                | (WMSWorker.last_name.ilike(f"%{search}%"))
                | (WMSWorker.email.ilike(f"%{search}%"))
                | (WMSWorker.barcode.ilike(f"%{search}%"))
            )

        total = query.count()
        results = (
            query.order_by(WMSWorker.first_name, WMSWorker.last_name)
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
        worker_id: uuid.UUID,
        data: dict,
        organization_id: uuid.UUID,
    ) -> WMSWorker:
        worker = self.get_by_id(worker_id, organization_id)

        payload = {k: v for k, v in data.items() if v is not None and v != ""}

        # Hash password if provided
        password = payload.pop("password", None)
        if password:
            payload["password_hash"] = hash_password(password)

        # Enforce unique employee_id per org if it's being changed
        new_employee_id = payload.get("employee_id")
        if new_employee_id and new_employee_id != worker.employee_id:
            existing = (
                self.db.query(WMSWorker)
                .filter(
                    WMSWorker.organization_id == organization_id,
                    WMSWorker.employee_id == new_employee_id,
                    WMSWorker.id != worker_id,
                )
                .first()
            )
            if existing:
                from fastapi import HTTPException, status as http_status
                raise HTTPException(
                    status_code=http_status.HTTP_409_CONFLICT,
                    detail=f"Employee ID '{new_employee_id}' is already in use by another worker in this organization.",
                )

        for key, value in payload.items():
            if hasattr(worker, key):
                setattr(worker, key, value)

        self.db.flush()
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def delete(self, worker_id: uuid.UUID, organization_id: uuid.UUID) -> None:
        worker = self.get_by_id(worker_id, organization_id)
        worker.is_active = False
        worker.status = WMSWorkerStatus.DISABLED
        self.db.flush()
        self.db.commit()

    def authenticate_by_barcode(self, barcode: str, organization_id: uuid.UUID | None = None) -> WMSWorker | None:
        worker = self.get_by_barcode(barcode, organization_id)
        if not worker:
            return None
        if worker.status != WMSWorkerStatus.ACTIVE:
            return None
        worker.last_login_at = datetime.now(UTC)
        self.db.flush()
        self.db.commit()
        return worker

    def authenticate_by_username(self, username: str, password: str, organization_id: uuid.UUID | None = None) -> WMSWorker | None:
        query = self.db.query(WMSWorker).filter(
            WMSWorker.login_username == username,
            WMSWorker.is_active == True,
        )
        if organization_id:
            query = query.filter(WMSWorker.organization_id == organization_id)
        worker = query.first()
        if not worker or not worker.password_hash:
            return None
        if worker.status != WMSWorkerStatus.ACTIVE:
            return None
        if not verify_password(password, worker.password_hash):
            return None
        worker.last_login_at = datetime.now(UTC)
        self.db.flush()
        self.db.commit()
        return worker

    def regenerate_barcode(self, worker_id: uuid.UUID, organization_id: uuid.UUID) -> WMSWorker:
        worker = self.get_by_id(worker_id, organization_id)
        worker.barcode = self._generate_barcode()
        self.db.flush()
        self.db.commit()
        self.db.refresh(worker)
        return worker

    def _generate_barcode(self) -> str:
        """Generate a unique barcode string."""
        return f"WRK-{secrets.token_hex(6).upper()}"
