"""Chart of Accounts management API endpoints"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.chart_of_account import (
    AccountBalanceHistoryResponse,
    AccountBalanceResponse,
    AccountBalancesRequest,
    ChartOfAccountCreate,
    ChartOfAccountHierarchyResponse,
    ChartOfAccountListItem,
    ChartOfAccountListResponse,
    ChartOfAccountMoveParentRequest,
    ChartOfAccountParentInfo,
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
    page_size: int = Query(20, ge=1, le=1000, description="Items per page (max 1000)"),
    account_type: str | None = Query(
        None,
        description="Filter by type (asset, liability, equity, income, expense)",
    ),
    parent_account_id: UUID | None = Query(
        None, description="Filter by parent account ID"
    ),
    is_active: bool | None = Query(None, description="Filter by active status"),
    is_group: bool | None = Query(None, description="Filter by is_group"),
    currency: str | None = Query(None, description="Filter by currency code"),
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
    - **page_size**: Items per page (default: 20, max: 1000)
    - **account_type**: Filter by account type
    - **parent_account_id**: Filter by parent account
    - **is_active**, **is_group**: Filters
    - **currency**: Filter by currency code
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
        currency=currency,
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


@router.put(
    "/{account_id}/activate",
    response_model=ChartOfAccountResponse,
    summary="Activate account",
    description="Activate an account to allow transaction postings",
)
async def activate_account(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Activate an account.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID

    **Returns:** Updated chart of account with ACTIVE status
    """
    service = ChartOfAccountService(db)
    account = service.activate_account(
        account_id=account_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ChartOfAccountResponse.model_validate(account)


@router.put(
    "/{account_id}/deactivate",
    response_model=ChartOfAccountResponse,
    summary="Deactivate account",
    description="Deactivate an account to prevent transaction postings",
)
async def deactivate_account(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Deactivate an account.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID

    **Returns:** Updated chart of account with INACTIVE status
    """
    service = ChartOfAccountService(db)
    account = service.deactivate_account(
        account_id=account_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ChartOfAccountResponse.model_validate(account)


@router.put(
    "/{account_id}/archive",
    response_model=ChartOfAccountResponse,
    summary="Archive account",
    description="Archive an account for historical purposes",
)
async def archive_account(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Archive an account.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID

    **Returns:** Updated chart of account with ARCHIVED status
    """
    service = ChartOfAccountService(db)
    account = service.archive_account(
        account_id=account_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ChartOfAccountResponse.model_validate(account)


# Hierarchy endpoints

@router.get(
    "/{account_id}/hierarchy",
    response_model=ChartOfAccountHierarchyResponse,
    summary="Get account hierarchy",
    description="Get complete hierarchy information for an account including ancestors, children, and descendants count",
)
async def get_account_hierarchy(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get account hierarchy information.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID

    **Returns:** Account with ancestors, children, and descendants count
    """
    service = ChartOfAccountService(db)
    
    # Get the account
    account = service.get_by_id(
        account_id=account_id,
        organization_id=current_user.organization_id,
        include_parent=True,
    )
    
    # Get hierarchy information
    ancestors = service.get_ancestors(account_id, current_user.organization_id)
    children = service.get_children(account_id, current_user.organization_id)
    descendants = service.get_descendants(account_id, current_user.organization_id)
    
    return ChartOfAccountHierarchyResponse(
        account=ChartOfAccountResponse.model_validate(account),
        ancestors=[ChartOfAccountParentInfo.model_validate(a) for a in ancestors],
        children=[ChartOfAccountParentInfo.model_validate(c) for c in children],
        descendants_count=len(descendants),
    )


@router.get(
    "/{account_id}/children",
    response_model=list[ChartOfAccountListItem],
    summary="Get child accounts",
    description="Get all direct child accounts of a parent account",
)
async def get_child_accounts(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get child accounts.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Parent account UUID

    **Returns:** List of direct child accounts
    """
    service = ChartOfAccountService(db)
    children = service.get_children(account_id, current_user.organization_id)
    return [ChartOfAccountListItem.model_validate(c) for c in children]


@router.get(
    "/{account_id}/ancestors",
    response_model=list[ChartOfAccountParentInfo],
    summary="Get ancestor accounts",
    description="Get all ancestor accounts from the account up to the root",
)
async def get_ancestor_accounts(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get ancestor accounts.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Account UUID

    **Returns:** List of ancestor accounts ordered from immediate parent to root
    """
    service = ChartOfAccountService(db)
    ancestors = service.get_ancestors(account_id, current_user.organization_id)
    return [ChartOfAccountParentInfo.model_validate(a) for a in ancestors]


@router.get(
    "/{account_id}/descendants",
    response_model=list[ChartOfAccountListItem],
    summary="Get descendant accounts",
    description="Get all descendant accounts recursively (children, grandchildren, etc.)",
)
async def get_descendant_accounts(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get descendant accounts.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Account UUID

    **Returns:** List of all descendant accounts
    """
    service = ChartOfAccountService(db)
    descendants = service.get_descendants(account_id, current_user.organization_id)
    return [ChartOfAccountListItem.model_validate(d) for d in descendants]


@router.put(
    "/{account_id}/parent",
    response_model=ChartOfAccountResponse,
    summary="Move account to new parent",
    description="Move an account to a new parent in the hierarchy",
)
async def move_account_to_parent(
    account_id: UUID,
    data: ChartOfAccountMoveParentRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Move account to a new parent.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Account UUID to move

    **Request Body:**
    - **new_parent_id**: New parent account UUID

    **Returns:** Updated account with new parent
    """
    service = ChartOfAccountService(db)
    account = service.move_account(
        account_id=account_id,
        new_parent_id=data.new_parent_id,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return ChartOfAccountResponse.model_validate(account)


# Integration endpoints for other modules

@router.post(
    "/{account_id}/validate-posting",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Validate account for posting",
    description="Validate that an account can receive transaction postings (for integration with other modules)",
)
async def validate_posting_account(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Validate that an account can receive transaction postings.

    This endpoint is used by other ERP modules (inventory, sourcing, etc.) to validate
    accounts before posting transactions.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID to validate

    **Returns:** 
    - 204 No Content if account is valid for posting
    - 404 Not Found if account doesn't exist
    - 422 Unprocessable Entity if account is inactive or not a posting account

    **Validation Rules:**
    - Account must exist
    - Account must be ACTIVE
    - Account must be a posting account (is_posting_account=true)
    - Parent accounts with children cannot receive postings
    """
    service = ChartOfAccountService(db)
    service.validate_posting_account(
        account_id=account_id,
        organization_id=current_user.organization_id,
    )
    return None



# Balance endpoints

@router.get(
    "/{account_id}/balance",
    response_model=ChartOfAccountResponse,
    summary="Get account balance",
    description="Get current or historical balance for an account",
)
async def get_account_balance(
    account_id: UUID,
    as_of_date: str | None = Query(None, description="Date to calculate balance as of (YYYY-MM-DD format)"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get account balance.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID

    **Query Parameters:**
    - **as_of_date**: Optional date to calculate balance as of (YYYY-MM-DD). Defaults to today.

    **Returns:** Account balance information including debit/credit totals and net balance
    """
    from datetime import date
    from app.services.balance_calculator import BalanceCalculator
    from app.schemas.chart_of_account import AccountBalanceResponse
    
    # Parse date if provided
    balance_date = None
    if as_of_date:
        try:
            balance_date = date.fromisoformat(as_of_date)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    # Calculate balance
    calculator = BalanceCalculator(db)
    balance_data = calculator.calculate_balance(account_id, balance_date)
    
    if not balance_data:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {account_id}"
        )
    
    return AccountBalanceResponse(**balance_data)


@router.post(
    "/balances",
    response_model=list[AccountBalanceResponse],
    summary="Get multiple account balances",
    description="Get balances for multiple accounts at once",
)
async def get_multiple_account_balances(
    data: AccountBalancesRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get balances for multiple accounts.

    Requires authentication.

    **Request Body:**
    - **account_ids**: List of account UUIDs
    - **as_of_date**: Optional date to calculate balances as of (YYYY-MM-DD)

    **Returns:** List of account balance information
    """
    from datetime import date
    from app.services.balance_calculator import BalanceCalculator
    from app.schemas.chart_of_account import AccountBalanceResponse
    
    # Parse date if provided
    balance_date = None
    if data.as_of_date:
        try:
            balance_date = date.fromisoformat(data.as_of_date)
        except ValueError:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    # Calculate balances
    calculator = BalanceCalculator(db)
    balances = []
    
    for account_id in data.account_ids:
        balance_data = calculator.calculate_balance(account_id, balance_date)
        if balance_data:
            balances.append(AccountBalanceResponse(**balance_data))
    
    return balances


@router.get(
    "/{account_id}/balance/history",
    response_model=AccountBalanceHistoryResponse,
    summary="Get account balance history",
    description="Get balance history for an account over a date range",
)
async def get_account_balance_history(
    account_id: UUID,
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get account balance history.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID

    **Query Parameters:**
    - **start_date**: Start date (YYYY-MM-DD) - required
    - **end_date**: End date (YYYY-MM-DD) - required

    **Returns:** Balance history with daily snapshots
    """
    from datetime import date
    from app.services.balance_calculator import BalanceCalculator
    from app.schemas.chart_of_account import AccountBalanceResponse, AccountBalanceHistoryResponse
    
    # Parse dates
    try:
        start = date.fromisoformat(start_date)
        end = date.fromisoformat(end_date)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid date format. Use YYYY-MM-DD"
        )
    
    # Validate date range
    if start > end:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date must be before or equal to end_date"
        )
    
    # Calculate history
    calculator = BalanceCalculator(db)
    history_data = calculator.get_balance_history(account_id, start, end)
    
    history_items = [AccountBalanceResponse(**item) for item in history_data]
    
    return AccountBalanceHistoryResponse(
        account_id=str(account_id),
        start_date=start_date,
        end_date=end_date,
        history=history_items
    )


# Audit trail endpoints

@router.get(
    "/{account_id}/audit-trail",
    response_model=dict,
    summary="Get account audit trail",
    description="Get audit history for an account with optional filtering",
)
async def get_account_audit_trail(
    account_id: UUID,
    action: str | None = Query(None, description="Filter by action type (CREATE, UPDATE, DELETE, STATUS_CHANGE)"),
    start_date: str | None = Query(None, description="Filter by start date (ISO format)"),
    end_date: str | None = Query(None, description="Filter by end date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Items per page"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get audit trail for an account.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Chart of account UUID

    **Query Parameters:**
    - **action**: Filter by action type (optional)
    - **start_date**: Filter by start date in ISO format (optional)
    - **end_date**: Filter by end date in ISO format (optional)
    - **page**: Page number (default: 1)
    - **page_size**: Items per page (default: 50, max: 100)

    **Returns:** Paginated audit trail entries ordered by timestamp (newest first)
    """
    from datetime import datetime
    from fastapi import HTTPException
    from app.services.audit_logger import AuditLogger
    from app.schemas.audit_log import AuditLogEntryResponse, AuditTrailResponse
    
    # Verify account exists
    service = ChartOfAccountService(db)
    try:
        service.get_by_id(account_id, current_user.organization_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account not found: {str(e)}"
        )
    
    # Parse dates if provided
    start_datetime = None
    end_datetime = None
    
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    if end_date:
        try:
            end_datetime = datetime.fromisoformat(end_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
            )
    
    # Get audit trail
    audit_logger = AuditLogger(db)
    
    # Calculate offset for pagination
    offset = (page - 1) * page_size
    
    # Get audit entries
    entries = audit_logger.get_audit_trail(
        account_id=account_id,
        action_filter=action,
        start_date=start_datetime,
        end_date=end_datetime,
        limit=page_size,
        offset=offset,
    )
    
    # Get total count for pagination
    total = audit_logger.get_audit_count(
        account_id=account_id,
        action_filter=action,
        start_date=start_datetime,
        end_date=end_datetime,
    )
    
    # Convert to response models
    items = [AuditLogEntryResponse.model_validate(entry) for entry in entries]
    
    # Calculate pagination metadata
    total_pages = (total + page_size - 1) // page_size
    
    return AuditTrailResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1,
    )
