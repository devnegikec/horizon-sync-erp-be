"""Pydantic schemas for Cascade module"""

import re
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.qr_activation import QRTypeEnum

# ── Parent QR ─────────────────────────────────────────────────────────────────

class ParentQRCreate(BaseModel):
    name: str = Field(..., max_length=20, description="Label for this parent node")
    qr_type: QRTypeEnum  = Field(..., description="Type of parent node: shipper,pallet, container etc.")
    capacity: int = Field(..., gt=0, description="Max number of child QRs this node can hold")


    @field_validator("name")
    @classmethod
    def alphanumeric_only(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9]*$", v):
            raise ValueError("Only alphanumeric characters are allowed.")
        return v


class ParentQRResponse(BaseModel):
    id: UUID
    organization_id: UUID
    qr_type:QRTypeEnum | None
    name: str | None
    capacity: int | None
    serial_number: str | None
    qr_code_link: str | None
    children_count: int = 0
    created_at: datetime

    model_config = {"from_attributes": True}


class ParentQRListResponse(BaseModel):
    nodes: list[ParentQRResponse]
    pagination: dict[str, Any]


# ── QR Activation Track ───────────────────────────────────────────────────────

class QRTrackBase(BaseModel):
    qr_type: QRTypeEnum = Field(..., description="Type of QR: shipper, pallet, container etc.")
    name: str | None = Field(None, max_length=20)
    capacity: int | None = None
    serial_number: str | None = Field(None, max_length=10)
    qr_code_link: str | None = None

    @field_validator("name")
    @classmethod
    def alphanumeric_only(cls, v):
        if v and not re.match(r"^[a-zA-Z0-9]*$", v):
            raise ValueError("Only alphanumeric characters are allowed.")
        return v


class QRTrackCreate(QRTrackBase):
    pass


class QRTrackUpdate(BaseModel):
    qr_type: QRTypeEnum | None = None
    name: str | None = Field(None, max_length=20)
    capacity: int | None = None
    qr_code_link: str | None = None


class QRTrackResponse(QRTrackBase):
    id: UUID
    organization_id: UUID
    qr_type:QRTypeEnum | None
    name: str | None
    capacity: int | None
    serial_number: str | None
   # qr_code_link: str | None
    children_count: int = 0

    model_config = {"from_attributes": True}


class QRTrackListResponse(BaseModel):
    nodes: list[QRTrackResponse]
    pagination: dict[str, Any]


# ── QR Scan Cascade ───────────────────────────────────────────────────────────

class QRScanCascadeRequest(BaseModel):
    url: str


class QRScanCascadeResponse(BaseModel):
    serial_number: str


# ── Child QR ──────────────────────────────────────────────────────────────────

class ChildQRRequest(BaseModel):
    srnumber: str                      # comma-separated child serial numbers
    parent_srnumber: str | None = None # provide this OR url
    url: str | None = None


class ChildQRResponse(BaseModel):
    total_capacity: int | None
    children: list[str]


# ── Mapping ───────────────────────────────────────────────────────────────────

class MappingChildRequest(BaseModel):
    srnumber: str        # comma-separated child serial numbers
    parent_srnumber: str


class MappingChildResponse(BaseModel):
    message: str


# ── Label Download ────────────────────────────────────────────────────────────

class QRLabelDownloadRequest(BaseModel):
    parent_srnumber: str


class QRLabelDownloadResponse(BaseModel):
    download_url: str
    view_url: str | None = None
