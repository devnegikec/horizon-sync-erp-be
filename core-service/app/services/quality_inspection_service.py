"""Quality inspection template and inspection services"""

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import ResourceNotFoundException
from app.models.base import InspectionStatus, InspectionType, ReadingType
from app.repositories.quality_inspection_repository import (
    QualityInspectionRepository,
    QualityInspectionTemplateRepository,
)


class QualityInspectionTemplateService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QualityInspectionTemplateRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = {k: v for k, v in data.items() if k != "parameters"}
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        if payload.get("inspection_type"):
            payload["inspection_type"] = InspectionType(payload["inspection_type"])
        parameters = data.get("parameters") or []
        param_list = []
        for p in parameters:
            pp = dict(p)
            if pp.get("reading_type"):
                pp["reading_type"] = ReadingType(pp["reading_type"])
            param_list.append(pp)
        template = self.repo.create(payload, param_list)
        return self._to_response(template)

    def get_by_id(self, template_id: UUID, organization_id: UUID) -> dict:
        t = self.repo.get_by_id(template_id, organization_id)
        if not t:
            raise ResourceNotFoundException(
                f"Quality inspection template {template_id} not found"
            )
        return self._to_response(t)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        inspection_type: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_templates(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            inspection_type=inspection_type,
            is_active=is_active,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return [self._to_list_item(t) for t in items], pagination

    def update(
        self, template_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        t = self.repo.get_by_id(template_id, organization_id)
        if not t:
            raise ResourceNotFoundException(
                f"Quality inspection template {template_id} not found"
            )
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("inspection_type"):
            payload["inspection_type"] = InspectionType(payload["inspection_type"])
        payload["updated_by"] = user_id
        self.repo.update(t, payload)
        self.db.refresh(t)
        return self._to_response(t)

    def delete(self, template_id: UUID, organization_id: UUID) -> None:
        t = self.repo.get_by_id(template_id, organization_id)
        if not t:
            raise ResourceNotFoundException(
                f"Quality inspection template {template_id} not found"
            )
        self.repo.delete(t)

    @staticmethod
    def _to_response(t) -> dict:
        return {
            "id": t.id,
            "organization_id": t.organization_id,
            "name": t.name,
            "code": t.code,
            "description": t.description,
            "item_id": t.item_id,
            "item_group_id": t.item_group_id,
            "inspection_type": t.inspection_type.value if t.inspection_type else None,
            "is_active": t.is_active,
            "created_by": t.created_by,
            "updated_by": t.updated_by,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }

    @staticmethod
    def _to_list_item(t) -> dict:
        return {
            "id": t.id,
            "organization_id": t.organization_id,
            "name": t.name,
            "code": t.code,
            "inspection_type": t.inspection_type.value if t.inspection_type else None,
            "is_active": t.is_active,
            "created_at": t.created_at,
        }


class QualityInspectionService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QualityInspectionRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict:
        payload = {k: v for k, v in data.items() if k != "readings"}
        payload["organization_id"] = organization_id
        payload["created_by"] = user_id
        payload["updated_by"] = user_id
        if payload.get("inspection_type"):
            payload["inspection_type"] = InspectionType(payload["inspection_type"])
        if payload.get("status"):
            payload["status"] = InspectionStatus(payload["status"])
        readings = data.get("readings") or []
        reading_list = []
        for r in readings:
            rr = dict(r)
            reading_list.append(rr)
        inspection = self.repo.create(payload, reading_list)
        return self._to_response(inspection)

    def get_by_id(self, inspection_id: UUID, organization_id: UUID) -> dict:
        inv = self.repo.get_by_id(inspection_id, organization_id)
        if not inv:
            raise ResourceNotFoundException(
                f"Quality inspection {inspection_id} not found"
            )
        return self._to_response(inv)

    def get_list(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        item_id: UUID | None = None,
        status: str | None = None,
        inspection_type: str | None = None,
        search: str | None = None,
        sort_by: str = "inspection_date",
        sort_order: str = "desc",
    ) -> tuple[list[dict], dict]:
        items, total = self.repo.list_inspections(
            organization_id=organization_id,
            page=page,
            page_size=page_size,
            item_id=item_id,
            status=status,
            inspection_type=inspection_type,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
        )
        total_pages = (total + page_size - 1) // page_size if page_size else 0
        pagination = {
            "page": page,
            "page_size": page_size,
            "total_items": total,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        }
        return [self._to_list_item(i) for i in items], pagination

    def update(
        self, inspection_id: UUID, data: dict, organization_id: UUID, user_id: UUID
    ) -> dict:
        inv = self.repo.get_by_id(inspection_id, organization_id)
        if not inv:
            raise ResourceNotFoundException(
                f"Quality inspection {inspection_id} not found"
            )
        payload = {k: v for k, v in data.items() if v is not None}
        if payload.get("status"):
            payload["status"] = InspectionStatus(payload["status"])
        payload["updated_by"] = user_id
        self.repo.update(inv, payload)
        self.db.refresh(inv)
        return self._to_response(inv)

    def delete(self, inspection_id: UUID, organization_id: UUID) -> None:
        inv = self.repo.get_by_id(inspection_id, organization_id)
        if not inv:
            raise ResourceNotFoundException(
                f"Quality inspection {inspection_id} not found"
            )
        self.repo.delete(inv)

    @staticmethod
    def _to_response(i) -> dict:
        return {
            "id": i.id,
            "organization_id": i.organization_id,
            "inspection_no": i.inspection_no,
            "item_id": i.item_id,
            "template_id": i.template_id,
            "batch_no": i.batch_no,
            "serial_no": i.serial_no,
            "warehouse_id": i.warehouse_id,
            "inspection_type": i.inspection_type.value if i.inspection_type else None,
            "status": i.status.value if i.status else None,
            "inspection_date": i.inspection_date,
            "reference_type": i.reference_type,
            "reference_id": i.reference_id,
            "remarks": i.remarks,
            "submitted_at": i.submitted_at,
            "created_by": i.created_by,
            "updated_by": i.updated_by,
            "created_at": i.created_at,
            "updated_at": i.updated_at,
        }

    @staticmethod
    def _to_list_item(i) -> dict:
        return {
            "id": i.id,
            "organization_id": i.organization_id,
            "inspection_no": i.inspection_no,
            "item_id": i.item_id,
            "status": i.status.value if i.status else None,
            "inspection_type": i.inspection_type.value if i.inspection_type else None,
            "inspection_date": i.inspection_date,
            "created_at": i.created_at,
        }
