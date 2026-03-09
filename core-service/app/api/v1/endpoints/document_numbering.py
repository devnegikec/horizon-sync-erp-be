"""Document Numbering Series API (Settings)."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.document_numbering import (
    DocumentNumberingConfigItem,
    DocumentNumberingConfigUpdate,
)
from app.services.document_numbering_service import DocumentNumberingService

router = APIRouter()


@router.get(
    "",
    response_model=list[DocumentNumberingConfigItem],
    summary="List document numbering config",
    description="Return numbering config for all document types (Settings > Document Numbering Series).",
)
async def list_document_numbering(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """List document numbering configuration for the current organization."""
    service = DocumentNumberingService(db)
    items = service.list_config(current_user.organization_id)
    return [DocumentNumberingConfigItem.model_validate(x) for x in items]


@router.put(
    "/{document_type}",
    response_model=DocumentNumberingConfigItem,
    summary="Update document numbering config",
    description="Update prefix, padding, include_year, or separator for one document type.",
)
async def update_document_numbering(
    document_type: str,
    data: DocumentNumberingConfigUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update one document type's numbering config."""
    try:
        service = DocumentNumberingService(db)
        updated = service.update_config(
            organization_id=current_user.organization_id,
            document_type=document_type,
            prefix=data.prefix,
            padding=data.padding,
            include_year=data.include_year,
            separator=data.separator,
        )
        return DocumentNumberingConfigItem.model_validate(updated)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
