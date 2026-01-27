"""Chart of Accounts management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.chart_of_account import (
    ChartOfAccountCreate,
    ChartOfAccountListItem,
    ChartOfAccountListResponse,
    ChartOfAccountResponse,
    ChartOfAccountTreeNode,
    ChartOfAccountUpdate,
)
from app.schemas.common import PaginationMeta
from app.services.chart_of_account_service import ChartOfAccountService

router = APIRouter()


@router.post(
    "",
    response_model=ChartOfAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create chart of account",
    description="Create a new chart of account",
)
async def create_chart_of_account(
    data: ChartOfAccountCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a new chart of account.

    Requires authentication.

    **Request Body:**
    - **account_code**: Unique account code (required)
    - **account_name**: Account name (required)
    - **account_type**: asset, liability, equity, income, expense (required)
    - **parent_account_id**: Parent account for hierarchy
    - **level**, **is_group**: Hierarchy fields
    - **opening_balance**, **current_balance**: Balances
    - **is_active**: Active status (default: true)

    **Returns:** Created chart of account details
    """
    service = ChartOfAccountService(db)
    account = service.create(
        data=data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ChartOfAccountResponse.model_validate(account)


@router.get(
    "",
    response_model=ChartOfAccountListResponse,
    summary="List chart of accounts",
    description="Get paginated list of chart of accounts with optional filters",
)
async def list_chart_of_accounts(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page (max 100)"),
    account_type: str | None = Query(
        None,
        description="Filter by type (asset, liability, equity, income, expense)",
    ),
    parent_account_id: UUID | None = Query(
        None, description="Filter by parent account ID"
    ),
    is_active: bool | None = Query(None, description="Filter by active status"),
    is_group: bool | None = Query(None, description="Filter by is_group"),
    search: str | None = Query(None, description="Search in account code, name"),
    sort_by: str = Query("account_code", description="Field to sort by"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$", description="Sort order"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List chart of accounts with pagination and filters.

    Requires authentication.

    **Query Parameters:**
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 20, max: 100)
    - **account_type**: Filter by account type
    - **parent_account_id**: Filter by parent account
    - **is_active**, **is_group**: Filters
    - **search**: Search term for code, name
    - **sort_by**: Field to sort by (default: account_code)
    - **sort_order**: Sort order - asc or desc (default: asc)

    **Returns:** Paginated list of chart of accounts
    """
    service = ChartOfAccountService(db)

    accounts, pagination = service.get_list(
        organization_id=current_user.organization_id,
        page=page,
        page_size=page_size,
        account_type=account_type,
        parent_account_id=parent_account_id,
        is_active=is_active,
        is_group=is_group,
        search=search,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    items = [ChartOfAccountListItem.model_validate(a) for a in accounts]

    return ChartOfAccountListResponse(
        chart_of_accounts=items, pagination=PaginationMeta(**pagination)
    )


@router.get(
    "/tree",
    response_model=list[ChartOfAccountTreeNode],
    summary="Get chart of accounts tree",
    description="Get chart of accounts as a hierarchical tree structure",
)
async def get_chart_of_accounts_tree(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get chart of accounts as a tree structure.

    Requires authentication.

    **Returns:** List of root-level accounts with nested children
    """
    service = ChartOfAccountService(db)
    return service.get_tree(current_user.organization_id)


@router.get(
    "/{account_id}",
    response_model=ChartOfAccountResponse,
    summary="Get chart of account",
    description="Get chart of account details by ID",
)
async def get_chart_of_account(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get chart of account details by ID.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID

    **Returns:** Chart of account details including parent info
    """
    service = ChartOfAccountService(db)
    account = service.get_by_id(
        account_id=account_id,
        organization_id=current_user.organization_id,
        include_parent=True,
    )
    return ChartOfAccountResponse.model_validate(account)


@router.put(
    "/{account_id}",
    response_model=ChartOfAccountResponse,
    summary="Update chart of account",
    description="Update an existing chart of account",
)
async def update_chart_of_account(
    account_id: UUID,
    data: ChartOfAccountUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update an existing chart of account.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID

    **Request Body:** Fields to update (all optional)

    **Returns:** Updated chart of account details
    """
    service = ChartOfAccountService(db)
    account = service.update(
        account_id=account_id,
        data=data,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ChartOfAccountResponse.model_validate(account)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete chart of account",
    description="Soft delete a chart of account",
)
async def delete_chart_of_account(
    account_id: UUID,
    force: bool = Query(False, description="Force delete even if has children"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Soft delete a chart of account.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID

    **Query Parameters:**
    - **force**: Force delete even if has children (default: false)

    **Returns:** 204 No Content on success
    """
    service = ChartOfAccountService(db)
    service.delete(
        account_id=account_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        force=force,
    )
    return None
