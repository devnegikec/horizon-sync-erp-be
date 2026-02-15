"""Tax Template API endpoints"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, require_permission
from app.schemas.tax_template import (
    TaxTemplateCreate,
    TaxTemplateListResponse,
    TaxTemplateResponse,
    TaxTemplateUpdate,
)
from app.services.tax_template_service import TaxTemplateService

router = APIRouter()

# Permission constants
TAX_TEMPLATE_CREATE = "tax_template.create"
TAX_TEMPLATE_READ = "tax_template.read"
TAX_TEMPLATE_UPDATE = "tax_template.update"
TAX_TEMPLATE_DELETE = "tax_template.delete"


@router.post(
    "",
    response_model=TaxTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new tax template",
)
def create_tax_template(
    template_data: TaxTemplateCreate,
    current_user: CurrentUser = Depends(require_permission(TAX_TEMPLATE_CREATE)),
    db: Session = Depends(get_db),
):
    """
    Create a new tax template with tax rules.
    
    Requires permission: tax_template.create
    """
    service = TaxTemplateService(db)
    data = template_data.model_dump()
    data["organization_id"] = current_user.organization_id
    template = service.create_template(data, current_user.id)
    return template


@router.get(
    "",
    response_model=TaxTemplateListResponse,
    summary="List tax templates",
)
def list_tax_templates(
    tax_category: Optional[str] = Query(None, description="Filter by tax category (Input/Output)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_default: Optional[bool] = Query(None, description="Filter by default status"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(require_permission(TAX_TEMPLATE_READ)),
    db: Session = Depends(get_db),
):
    """
    List all tax templates for the current organization with pagination and filtering.
    
    Requires permission: tax_template.read
    """
    filters = {
        "page": page,
        "page_size": limit,
    }
    if tax_category is not None:
        filters["tax_category"] = tax_category
    if is_active is not None:
        filters["is_active"] = is_active
    if is_default is not None:
        filters["is_default"] = is_default
    
    service = TaxTemplateService(db)
    templates, pagination = service.list_templates(
        current_user.organization_id,
        filters
    )
    
    return {
        "templates": templates,
        "pagination": pagination
    }


@router.get(
    "/applicable",
    response_model=dict,
    summary="Get applicable tax template",
)
def get_applicable_tax_template(
    item_id: Optional[UUID] = Query(None, description="Item ID"),
    transaction_type: str = Query(..., description="Transaction type (Sales/Purchase)"),
    customer_id: Optional[UUID] = Query(None, description="Customer ID"),
    supplier_id: Optional[UUID] = Query(None, description="Supplier ID"),
    current_user: CurrentUser = Depends(require_permission(TAX_TEMPLATE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get the applicable tax template for a given context.
    
    Returns the template based on inheritance hierarchy:
    1. Item-level template
    2. Item group-level template
    3. Organization default template
    
    Requires permission: tax_template.read
    """
    from app.services.tax_template_service import TaxContext
    
    context = TaxContext(
        organization_id=current_user.organization_id,
        transaction_type=transaction_type,
        item_id=item_id,
        customer_id=customer_id,
        supplier_id=supplier_id,
    )
    
    service = TaxTemplateService(db)
    result = service.get_applicable_template(context)
    
    if result is None:
        return {
            "template": None,
            "source": None
        }
    
    template, source = result
    return {
        "template": template,
        "source": source
    }


@router.get(
    "/{template_id}",
    response_model=TaxTemplateResponse,
    summary="Get tax template by ID",
)
def get_tax_template(
    template_id: UUID,
    current_user: CurrentUser = Depends(require_permission(TAX_TEMPLATE_READ)),
    db: Session = Depends(get_db),
):
    """
    Get a specific tax template by ID.
    
    Requires permission: tax_template.read
    """
    service = TaxTemplateService(db)
    template = service.get_template(template_id, current_user.organization_id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax template not found"
        )
    
    return template


@router.put(
    "/{template_id}",
    response_model=TaxTemplateResponse,
    summary="Update tax template",
)
def update_tax_template(
    template_id: UUID,
    template_data: TaxTemplateUpdate,
    current_user: CurrentUser = Depends(require_permission(TAX_TEMPLATE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Update an existing tax template.
    
    Requires permission: tax_template.update
    """
    service = TaxTemplateService(db)
    data = template_data.model_dump(exclude_unset=True)
    data["organization_id"] = current_user.organization_id
    template = service.update_template(template_id, data, current_user.id)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax template not found"
        )
    
    return template


@router.delete(
    "/{template_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete tax template",
)
def delete_tax_template(
    template_id: UUID,
    current_user: CurrentUser = Depends(require_permission(TAX_TEMPLATE_DELETE)),
    db: Session = Depends(get_db),
):
    """
    Soft delete a tax template.
    
    Will fail if the template is referenced by items, item groups, or active transactions.
    
    Requires permission: tax_template.delete
    """
    service = TaxTemplateService(db)
    success = service.delete_template(template_id, current_user.organization_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax template not found"
        )
    
    return None


@router.post(
    "/{template_id}/set-default",
    response_model=TaxTemplateResponse,
    summary="Set template as default",
)
def set_as_default(
    template_id: UUID,
    current_user: CurrentUser = Depends(require_permission(TAX_TEMPLATE_UPDATE)),
    db: Session = Depends(get_db),
):
    """
    Mark a tax template as the default for its tax category.
    
    This will unmark any existing default template for the same organization and tax category.
    
    Requires permission: tax_template.update
    """
    service = TaxTemplateService(db)
    
    # Get the template to find its tax_category
    template = service.get_template(template_id, current_user.organization_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax template not found"
        )
    
    success = service.set_as_default(
        template_id,
        current_user.organization_id,
        template["tax_category"]
    )
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to set template as default"
        )
    
    # Return the updated template
    updated_template = service.get_template(template_id, current_user.organization_id)
    return updated_template
