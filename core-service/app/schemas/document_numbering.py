"""Pydantic schemas for Document Numbering Series (Settings)."""

from pydantic import BaseModel, Field


class DocumentNumberingConfigItem(BaseModel):
    """One document type's numbering config (for list response)."""

    document_type: str
    prefix: str
    padding: int = Field(ge=1, le=10)
    include_year: bool = True
    separator: str = "-"


class DocumentNumberingConfigUpdate(BaseModel):
    """Request body for updating one document type's config."""

    prefix: str | None = None
    padding: int | None = Field(None, ge=1, le=10)
    include_year: bool | None = None
    separator: str | None = None
