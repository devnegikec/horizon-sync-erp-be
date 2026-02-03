"""Customer management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.common import PaginationMeta
from app.schemas.customer import (
    CustomerCreate,
    CustomerListItem,
    CustomerListResponse,
    CustomerResponse,
    CustomerUpdate,
)
from app.services.customer_service import CustomerService

router = APIRouter()


@router.post(
    "",
    response_model=CustomerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create customer",
    description="Create a new customer",
)
async def create_customer(
    customer_data: CustomerCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new customer.

    Requires authentication.

    **Request Body:**
    - **customer_name**: Customer name (required)
    - **customer_code**: Unique customer code (required)
    - **email**, **phone**: Contact information
    - **address**, **city**, **state**, etc.: Address information
    - **tax_number**: Tax identification
    - **status**: active, inactive, blocked (default: active)
    - **credit_limit**, **outstanding_balance**: Credit information

    **Returns:** Created customer details
    """
    customer_service = CustomerService(db)
    customer = customer_service.create_customer(
        customer_data=customer_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return CustomerResponse.model_validate(customer)


@router.get(
    "",
    response_model=CustomerListResponse,
    summary="List customers",
    description="Get paginated list of customers with optional filters",
)
async def list_customers(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    status: str | None = Query(
        "active", description="Filter by status (active, inactive, blocked)"
    ),
    search: str | None = Query(None, description="Search in name, code, email, city"),
    sort_by: str = Query("created_at", description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List customers with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **status**: Filter by status (default: active)
    - **search**: Search term for name, code, email, city
    - **sort_by**: Field to sort by (default: created_at)
    - **sort_order**: Sort order - asc or desc (default: desc)

    **Returns:** Paginated list of customers
    """
    customer_service = CustomerService(db)

    customers, pagination = customer_service.get_customers(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        status=status,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    customer_items = [CustomerListItem.model_validate(c) for c in customers]

    return CustomerListResponse(
        customers=customer_items, pagination=PaginationMeta(**pagination)
    )


@router.get(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Get customer",
    description="Get customer details by ID",
)
async def get_customer(
    customer_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get customer details by ID.

    Requires authentication.

    **Path Parameters:**
    - **customer_id**: Customer UUID

    **Returns:** Customer details
    """
    customer_service = CustomerService(db)
    customer = customer_service.get_customer_by_id(
        customer_id=customer_id,
        organization_id=current_user.organization_id,
    )
    return CustomerResponse.model_validate(customer)


@router.put(
    "/{customer_id}",
    response_model=CustomerResponse,
    summary="Update customer",
    description="Update an existing customer",
)
async def update_customer(
    customer_id: UUID,
    customer_data: CustomerUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing customer.

    Requires authentication.

    **Path Parameters:**
    - **customer_id**: Customer UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated customer details
    """
    customer_service = CustomerService(db)
    customer = customer_service.update_customer(
        customer_id=customer_id,
        customer_data=customer_data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return CustomerResponse.model_validate(customer)


@router.delete(
    "/{customer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete customer",
    description="Soft delete a customer",
)
async def delete_customer(
    customer_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Soft delete a customer.

    Requires authentication.

    **Path Parameters:**
    - **customer_id**: Customer UUID

    **Returns:** 204 No Content on success
    """
    customer_service = CustomerService(db)
    customer_service.delete_customer(
        customer_id=customer_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return None
