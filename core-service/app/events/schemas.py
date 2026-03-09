"""Event schemas for entity changes"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Event types for entity changes"""

    CREATED = "entity.created"
    UPDATED = "entity.updated"
    DELETED = "entity.deleted"


class EntityEvent(BaseModel):
    """Event schema for entity changes"""

    event_type: EventType
    entity_type: str = Field(
        ..., description="Type of entity (items, customers, suppliers, etc.)"
    )
    entity_id: str = Field(..., description="Unique identifier of the entity")
    organization_id: str = Field(..., description="Organization ID")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: dict[str, Any] = Field(
        default_factory=dict,
        description="Full entity data for created/updated, minimal for deleted",
    )

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat(), UUID: lambda v: str(v)}
