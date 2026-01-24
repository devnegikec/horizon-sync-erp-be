"""Error response schemas"""

from datetime import datetime

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response schema"""

    error: str
    message: str
    details: dict | None = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ValidationErrorDetail(BaseModel):
    """Validation error detail"""

    field: str
    message: str


class ValidationErrorResponse(BaseModel):
    """Validation error response"""

    error: str = "VALIDATION_ERROR"
    message: str = "Invalid input data"
    details: list[ValidationErrorDetail]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
