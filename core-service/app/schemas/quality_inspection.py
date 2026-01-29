"""Quality inspection template and inspection schemas"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import PaginationMeta


# ----- Template Parameter -----
class QualityInspectionParameterBase(BaseModel):
    parameter_name: str = Field(..., min_length=1, max_length=255)
    reading_type: str = Field(default="numeric", pattern="^(numeric|text|pass_fail)$")
    numeric_min: Decimal | float | None = None
    numeric_max: Decimal | float | None = None
    uom: str | None = Field(None, max_length=50)
    specification: str | None = None
    sort_order: int = 0


class QualityInspectionParameterCreate(QualityInspectionParameterBase):
    pass


class QualityInspectionParameterResponse(QualityInspectionParameterBase):
    id: UUID
    organization_id: UUID
    template_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ----- Template -----
class QualityInspectionTemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    item_id: UUID | None = None
    item_group_id: UUID | None = None
    inspection_type: str = Field(
        default="incoming", pattern="^(incoming|outgoing|in_process)$"
    )
    is_active: bool = True


class QualityInspectionTemplateCreate(QualityInspectionTemplateBase):
    parameters: list[QualityInspectionParameterCreate] = Field(default_factory=list)


class QualityInspectionTemplateUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    code: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    item_id: UUID | None = None
    item_group_id: UUID | None = None
    inspection_type: str | None = Field(
        None, pattern="^(incoming|outgoing|in_process)$"
    )
    is_active: bool | None = None


class QualityInspectionTemplateResponse(QualityInspectionTemplateBase):
    id: UUID
    organization_id: UUID
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QualityInspectionTemplateListItem(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    code: str
    inspection_type: str
    is_active: bool
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QualityInspectionTemplateListResponse(BaseModel):
    templates: list[QualityInspectionTemplateListItem]
    pagination: PaginationMeta


# ----- Inspection Reading -----
class QualityInspectionReadingBase(BaseModel):
    parameter_id: UUID
    reading_value_numeric: Decimal | float | None = None
    reading_value_text: str | None = None
    reading_value_pass_fail: bool | None = None
    result: str | None = None
    remarks: str | None = None


class QualityInspectionReadingCreate(QualityInspectionReadingBase):
    pass


class QualityInspectionReadingResponse(QualityInspectionReadingBase):
    id: UUID
    organization_id: UUID
    inspection_id: UUID
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


# ----- Inspection -----
class QualityInspectionBase(BaseModel):
    inspection_no: str = Field(..., min_length=1, max_length=100)
    item_id: UUID
    template_id: UUID | None = None
    batch_no: str | None = Field(None, max_length=100)
    serial_no: str | None = Field(None, max_length=100)
    warehouse_id: UUID | None = None
    inspection_type: str = Field(
        default="incoming", pattern="^(incoming|outgoing|in_process)$"
    )
    status: str = Field(default="pending", pattern="^(pending|accepted|rejected)$")
    inspection_date: datetime | None = None
    reference_type: str | None = Field(None, max_length=50)
    reference_id: UUID | None = None
    remarks: str | None = None


class QualityInspectionCreate(QualityInspectionBase):
    readings: list[QualityInspectionReadingCreate] = Field(default_factory=list)


class QualityInspectionUpdate(BaseModel):
    batch_no: str | None = Field(None, max_length=100)
    serial_no: str | None = Field(None, max_length=100)
    warehouse_id: UUID | None = None
    status: str | None = Field(None, pattern="^(pending|accepted|rejected)$")
    inspection_date: datetime | None = None
    remarks: str | None = None


class QualityInspectionResponse(QualityInspectionBase):
    id: UUID
    organization_id: UUID
    submitted_at: datetime | None = None
    created_by: UUID | None = None
    updated_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QualityInspectionListItem(BaseModel):
    id: UUID
    organization_id: UUID
    inspection_no: str
    item_id: UUID
    status: str
    inspection_type: str
    inspection_date: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class QualityInspectionListResponse(BaseModel):
    inspections: list[QualityInspectionListItem]
    pagination: PaginationMeta
