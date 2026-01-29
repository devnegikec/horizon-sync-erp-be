"""Repository for quality inspection templates and inspections"""

from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.quality_inspection import (
    QualityInspection,
    QualityInspectionParameter,
    QualityInspectionReading,
    QualityInspectionTemplate,
)


class QualityInspectionTemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, parameters: list[dict]) -> QualityInspectionTemplate:
        template = QualityInspectionTemplate(**data)
        self.db.add(template)
        self.db.flush()
        for p in parameters:
            p["template_id"] = template.id
            p["organization_id"] = template.organization_id
            self.db.add(QualityInspectionParameter(**p))
        self.db.commit()
        self.db.refresh(template)
        return template

    def get_by_id(
        self, template_id: UUID, organization_id: UUID, load_parameters: bool = True
    ) -> QualityInspectionTemplate | None:
        q = self.db.query(QualityInspectionTemplate).filter(
            QualityInspectionTemplate.id == template_id,
            QualityInspectionTemplate.organization_id == organization_id,
        )
        template = q.first()
        if template and load_parameters:
            _ = template.parameters
        return template

    def get_by_code(
        self, code: str, organization_id: UUID
    ) -> QualityInspectionTemplate | None:
        return (
            self.db.query(QualityInspectionTemplate)
            .filter(
                QualityInspectionTemplate.code == code,
                QualityInspectionTemplate.organization_id == organization_id,
            )
            .first()
        )

    def list_templates(
        self,
        organization_id: UUID,
        page: int = 1,
        page_size: int = 20,
        inspection_type: str | None = None,
        is_active: bool | None = None,
        search: str | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[QualityInspectionTemplate], int]:
        q = self.db.query(QualityInspectionTemplate).filter(
            QualityInspectionTemplate.organization_id == organization_id
        )
        if inspection_type is not None:
            q = q.filter(QualityInspectionTemplate.inspection_type == inspection_type)
        if is_active is not None:
            q = q.filter(QualityInspectionTemplate.is_active == is_active)
        if search:
            term = f"%{search}%"
            q = q.filter(
                or_(
                    QualityInspectionTemplate.name.ilike(term),
                    QualityInspectionTemplate.code.ilike(term),
                )
            )
        total = q.count()
        col = getattr(
            QualityInspectionTemplate, sort_by, QualityInspectionTemplate.created_at
        )
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(
        self, template: QualityInspectionTemplate, data: dict
    ) -> QualityInspectionTemplate:
        for k, v in data.items():
            if hasattr(template, k):
                setattr(template, k, v)
        self.db.commit()
        self.db.refresh(template)
        return template

    def delete(self, template: QualityInspectionTemplate) -> None:
        self.db.delete(template)
        self.db.commit()


class QualityInspectionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict, readings: list[dict]) -> QualityInspection:
        inspection = QualityInspection(**data)
        self.db.add(inspection)
        self.db.flush()
        for r in readings:
            r["inspection_id"] = inspection.id
            r["organization_id"] = inspection.organization_id
            self.db.add(QualityInspectionReading(**r))
        self.db.commit()
        self.db.refresh(inspection)
        return inspection

    def get_by_id(
        self, inspection_id: UUID, organization_id: UUID, load_readings: bool = True
    ) -> QualityInspection | None:
        q = self.db.query(QualityInspection).filter(
            QualityInspection.id == inspection_id,
            QualityInspection.organization_id == organization_id,
        )
        inspection = q.first()
        if inspection and load_readings:
            _ = inspection.readings
        return inspection

    def get_by_no(
        self, inspection_no: str, organization_id: UUID
    ) -> QualityInspection | None:
        return (
            self.db.query(QualityInspection)
            .filter(
                QualityInspection.inspection_no == inspection_no,
                QualityInspection.organization_id == organization_id,
            )
            .first()
        )

    def list_inspections(
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
    ) -> tuple[list[QualityInspection], int]:
        q = self.db.query(QualityInspection).filter(
            QualityInspection.organization_id == organization_id
        )
        if item_id is not None:
            q = q.filter(QualityInspection.item_id == item_id)
        if status is not None:
            q = q.filter(QualityInspection.status == status)
        if inspection_type is not None:
            q = q.filter(QualityInspection.inspection_type == inspection_type)
        if search:
            term = f"%{search}%"
            q = q.filter(QualityInspection.inspection_no.ilike(term))
        total = q.count()
        col = getattr(QualityInspection, sort_by, QualityInspection.inspection_date)
        q = q.order_by(col.desc() if sort_order == "desc" else col.asc())
        items = q.offset((page - 1) * page_size).limit(page_size).all()
        return items, total

    def update(self, inspection: QualityInspection, data: dict) -> QualityInspection:
        for k, v in data.items():
            if hasattr(inspection, k):
                setattr(inspection, k, v)
        self.db.commit()
        self.db.refresh(inspection)
        return inspection

    def delete(self, inspection: QualityInspection) -> None:
        self.db.delete(inspection)
        self.db.commit()
