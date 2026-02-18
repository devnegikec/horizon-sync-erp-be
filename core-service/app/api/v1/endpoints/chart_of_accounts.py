"""Chart of Accounts management API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

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
from app.schemas.default_account import (
    AccountCodeFormatUpdateRequest,
    DefaultAccountBulkUpdateRequest,
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
    lazy_load: bool = Query(False, description="Return only root nodes for lazy loading"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get chart of accounts as a tree structure.

    Requires authentication.

    **Query Parameters:**
    - **lazy_load**: If true, returns only root-level nodes without children for lazy loading

    **Returns:** List of root-level accounts with nested children (or without if lazy_load=true)
    """
    service = ChartOfAccountService(db)
    
    if lazy_load:
        # Return only root nodes without children for lazy loading
        return service.get_tree_roots(current_user.organization_id)
    
    return service.get_tree(current_user.organization_id)


@router.get(
    "/tree/{account_id}/children",
    response_model=list[ChartOfAccountTreeNode],
    summary="Get tree node children",
    description="Get immediate children of a tree node for lazy loading",
)
async def get_tree_node_children(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get immediate children of a tree node for lazy loading.

    Requires authentication.

    **Path Parameters:**
    - **account_id**: Parent account UUID

    **Returns:** List of immediate child accounts as tree nodes
    """
    service = ChartOfAccountService(db)
    return service.get_tree_children(account_id, current_user.organization_id)


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


# Bulk operations endpoints

@router.post(
    "/bulk/activate",
    response_model=dict,
    summary="Bulk activate accounts",
    description="Activate multiple accounts in a single operation",
)
async def bulk_activate_accounts(
    account_ids: list[UUID] = Query(..., description="List of account UUIDs to activate"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Activate multiple accounts in bulk.

    Requires authentication.

    **Query Parameters:**
    - **account_ids**: List of account UUIDs to activate

    **Returns:** 
    - **success_count**: Number of accounts successfully activated
    - **failed_count**: Number of accounts that failed to activate
    - **errors**: List of errors for failed activations
    - **updated_ids**: List of successfully updated account IDs
    """
    service = ChartOfAccountService(db)
    results = service.bulk_activate_accounts(
        account_ids=account_ids,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return results


@router.post(
    "/bulk/deactivate",
    response_model=dict,
    summary="Bulk deactivate accounts",
    description="Deactivate multiple accounts in a single operation",
)
async def bulk_deactivate_accounts(
    account_ids: list[UUID] = Query(..., description="List of account UUIDs to deactivate"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Deactivate multiple accounts in bulk.

    Requires authentication.

    **Query Parameters:**
    - **account_ids**: List of account UUIDs to deactivate

    **Returns:** 
    - **success_count**: Number of accounts successfully deactivated
    - **failed_count**: Number of accounts that failed to deactivate
    - **errors**: List of errors for failed deactivations
    - **updated_ids**: List of successfully updated account IDs
    """
    service = ChartOfAccountService(db)
    results = service.bulk_deactivate_accounts(
        account_ids=account_ids,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
    )
    return results


@router.delete(
    "/bulk/delete",
    response_model=dict,
    summary="Bulk delete accounts",
    description="Delete multiple accounts with validation",
)
async def bulk_delete_accounts(
    account_ids: list[UUID] = Query(..., description="List of account UUIDs to delete"),
    force: bool = Query(False, description="Force delete even if has children"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete multiple accounts in bulk with validation.

    Requires authentication.

    **Query Parameters:**
    - **account_ids**: List of account UUIDs to delete
    - **force**: If true, delete even if account has children

    **Returns:** 
    - **success_count**: Number of accounts successfully deleted
    - **failed_count**: Number of accounts that failed to delete
    - **errors**: List of errors for failed deletions (includes account_code and reason)
    - **deleted_ids**: List of successfully deleted account IDs

    **Validation:**
    - Accounts with child accounts cannot be deleted unless force=true
    - Accounts with transactions cannot be deleted
    """
    service = ChartOfAccountService(db)
    results = service.bulk_delete_accounts(
        account_ids=account_ids,
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        force=force,
    )
    return results


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
    "/validate-posting",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Validate account for posting",
    description="Validate that an account can receive transaction postings (for integration with other modules)",
)
async def validate_posting_account_by_id(
    account_id: UUID = Query(..., description="Account UUID to validate"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Validate that an account can receive transaction postings.

    This endpoint is used by other ERP modules (inventory, sourcing, etc.) to validate
    accounts before posting transactions.

    Requires authentication.

    **Query Parameters:**
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


@router.post(
    "/validate-posting/bulk",
    response_model=dict,
    summary="Bulk validate accounts for posting",
    description="Validate multiple accounts for posting in a single request",
)
async def bulk_validate_posting_accounts(
    account_ids: list[UUID] = Query(default=[], description="List of account UUIDs to validate"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Validate multiple accounts for posting in a single request.

    This endpoint is used by other ERP modules to validate multiple accounts at once.

    Requires authentication.

    **Query Parameters:**
    - **account_ids**: List of account UUIDs to validate

    **Returns:** 
    - Dictionary with validation results for each account
      - valid: List of valid account IDs
      - invalid: List of invalid account IDs with error messages

    **Validation Rules:**
    - Account must exist
    - Account must be ACTIVE
    - Account must be a posting account (is_posting_account=true)
    - Parent accounts with children cannot receive postings
    """
    service = ChartOfAccountService(db)
    
    valid = []
    invalid = []
    
    for account_id in account_ids:
        try:
            service.validate_posting_account(
                account_id=account_id,
                organization_id=current_user.organization_id,
            )
            valid.append(str(account_id))
        except Exception as e:
            invalid.append({
                "account_id": str(account_id),
                "error": str(e),
            })
    
    return {
        "valid": valid,
        "invalid": invalid,
        "valid_count": len(valid),
        "invalid_count": len(invalid),
    }


@router.get(
    "/by-code/{code}",
    response_model=ChartOfAccountResponse,
    summary="Get account by code",
    description="Get account details by account code (for lookups by other modules)",
)
async def get_account_by_code(
    code: str,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get account details by account code.

    This endpoint is used by other ERP modules to lookup accounts by their code.

    Requires authentication.

    **Path Parameters:**
    - **code**: Account code (e.g., "1000-01")

    **Returns:** Account details including parent info

    **Raises:**
    - 404 Not Found if account with the given code doesn't exist
    """
    from app.repositories.chart_of_account_repository import AccountRepository
    
    account_repo = AccountRepository(db)
    account = account_repo.get_by_code(code, current_user.organization_id)
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account with code '{code}' not found"
        )
    
    return ChartOfAccountResponse.model_validate(account)


@router.post(
    "/default/{transaction_type}",
    response_model=ChartOfAccountResponse,
    summary="Get default account for transaction type",
    description="Get the default account configured for a specific transaction type",
)
async def get_default_account_for_transaction(
    transaction_type: str,
    scenario: str | None = Query(None, description="Optional scenario for multiple defaults per type"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the default account for a transaction type.

    This endpoint is used by other ERP modules to get the configured default account
    for specific transaction types (e.g., inventory_purchase, sales_revenue).

    Requires authentication.

    **Path Parameters:**
    - **transaction_type**: Type of transaction (e.g., "inventory_purchase", "sales_revenue")

    **Query Parameters:**
    - **scenario**: Optional scenario for multiple defaults per type (e.g., "domestic", "international")

    **Returns:** Default account details

    **Raises:**
    - 404 Not Found if no default account is configured for the transaction type
    - 422 Unprocessable Entity if the configured account is invalid

    **Common Transaction Types:**
    - inventory_purchase: For inventory purchase transactions
    - inventory_sale: For inventory sale transactions
    - accounts_payable: For accounts payable
    - accounts_receivable: For accounts receivable
    - sales_revenue: For sales revenue
    - purchase_expense: For purchase expenses
    - cost_of_goods_sold: For COGS
    - inventory_asset: For inventory assets
    """
    from app.services.default_account_service import DefaultAccountService
    from app.repositories.chart_of_account_repository import AccountRepository
    from app.core.exceptions import ValidationError
    
    default_service = DefaultAccountService(db)
    account_repo = AccountRepository(db)
    
    try:
        # Get default account configuration
        default = default_service.get_default_account(
            transaction_type=transaction_type,
            organization_id=current_user.organization_id,
            scenario=scenario,
        )
        
        # Get the actual account
        account = account_repo.get_by_id(default.account_id, current_user.organization_id)
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Configured default account not found for transaction type '{transaction_type}'"
            )
        
        return ChartOfAccountResponse.model_validate(account)
    
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post(
    "/{account_id}/validate-posting",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Validate account for posting (deprecated)",
    description="Validate that an account can receive transaction postings. Use POST /validate-posting instead.",
    deprecated=True,
)
async def validate_posting_account(
    account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Validate that an account can receive transaction postings.

    **DEPRECATED:** Use POST /api/v1/accounts/validate-posting instead.

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


# Reporting and Export endpoints

@router.get(
    "/report/chart",
    response_model=dict,
    summary="Generate Chart of Accounts report",
    description="Generate a comprehensive Chart of Accounts report with balances",
)
async def generate_chart_of_accounts_report(
    account_type: str | None = Query(None, description="Filter by account type"),
    status: str | None = Query(None, description="Filter by status (active, inactive, archived)"),
    as_of_date: str | None = Query(None, description="Date to calculate balances as of (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Generate Chart of Accounts report.

    Requires authentication.

    **Query Parameters:**
    - **account_type**: Filter by account type (asset, liability, equity, income, expense) - optional
    - **status**: Filter by status (active, inactive, archived) - optional
    - **as_of_date**: Date to calculate balances as of (YYYY-MM-DD) - optional, defaults to today

    **Returns:** Report data with all accounts, their details, and current balances
    """
    from datetime import date
    from fastapi import HTTPException
    from app.models.base import AccountType, AccountStatus
    from app.services.report_service import ReportService
    
    # Parse account type
    type_enum = None
    if account_type:
        try:
            type_enum = AccountType(account_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid account_type. Must be one of: asset, liability, equity, income, expense"
            )
    
    # Parse status
    status_enum = None
    if status:
        try:
            status_enum = AccountStatus(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: active, inactive, archived"
            )
    
    # Parse date
    balance_date = None
    if as_of_date:
        try:
            balance_date = date.fromisoformat(as_of_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    # Generate report
    report_service = ReportService(db)
    report = report_service.generate_chart_of_accounts_report(
        organization_id=current_user.organization_id,
        account_type=type_enum,
        status=status_enum,
        as_of_date=balance_date,
    )
    
    return report


@router.get(
    "/report/hierarchical",
    response_model=dict,
    summary="Generate hierarchical report",
    description="Generate a hierarchical report showing accounts in tree structure",
)
async def generate_hierarchical_report(
    account_type: str | None = Query(None, description="Filter by account type"),
    status: str | None = Query(None, description="Filter by status (active, inactive, archived)"),
    as_of_date: str | None = Query(None, description="Date to calculate balances as of (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Generate hierarchical report.

    Requires authentication.

    **Query Parameters:**
    - **account_type**: Filter by account type (asset, liability, equity, income, expense) - optional
    - **status**: Filter by status (active, inactive, archived) - optional
    - **as_of_date**: Date to calculate balances as of (YYYY-MM-DD) - optional, defaults to today

    **Returns:** Report data with accounts in tree structure showing parent-child relationships
    """
    from datetime import date
    from fastapi import HTTPException
    from app.models.base import AccountType, AccountStatus
    from app.services.report_service import ReportService
    
    # Parse account type
    type_enum = None
    if account_type:
        try:
            type_enum = AccountType(account_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid account_type. Must be one of: asset, liability, equity, income, expense"
            )
    
    # Parse status
    status_enum = None
    if status:
        try:
            status_enum = AccountStatus(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: active, inactive, archived"
            )
    
    # Parse date
    balance_date = None
    if as_of_date:
        try:
            balance_date = date.fromisoformat(as_of_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    # Generate report
    report_service = ReportService(db)
    report = report_service.generate_hierarchical_report(
        organization_id=current_user.organization_id,
        account_type=type_enum,
        status=status_enum,
        as_of_date=balance_date,
    )
    
    return report


@router.get(
    "/report/trial-balance",
    response_model=dict,
    summary="Generate trial balance report",
    description="Generate a trial balance report showing posting accounts with debit/credit balances",
)
async def generate_trial_balance_report(
    account_type: str | None = Query(None, description="Filter by account type"),
    as_of_date: str | None = Query(None, description="Date to calculate balances as of (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Generate trial balance report.

    Requires authentication.

    **Query Parameters:**
    - **account_type**: Filter by account type (asset, liability, equity, income, expense) - optional
    - **as_of_date**: Date to calculate balances as of (YYYY-MM-DD) - optional, defaults to today

    **Returns:** Trial balance report with posting accounts and their debit/credit balances.
              The report includes total debits, total credits, and balance verification.
    """
    from datetime import date
    from fastapi import HTTPException
    from app.models.base import AccountType
    from app.services.report_service import ReportService
    
    # Parse account type
    type_enum = None
    if account_type:
        try:
            type_enum = AccountType(account_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid account_type. Must be one of: asset, liability, equity, income, expense"
            )
    
    # Parse date
    balance_date = None
    if as_of_date:
        try:
            balance_date = date.fromisoformat(as_of_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    # Generate report
    report_service = ReportService(db)
    report = report_service.generate_trial_balance(
        organization_id=current_user.organization_id,
        account_type=type_enum,
        as_of_date=balance_date,
    )
    
    return report


@router.get(
    "/export",
    summary="Export Chart of Accounts",
    description="Export Chart of Accounts data in various formats (CSV, JSON, XLSX, PDF)",
)
async def export_chart_of_accounts(
    format: str = Query(..., description="Export format: csv, json, xlsx, or pdf"),
    account_type: str | None = Query(None, description="Filter by account type"),
    status: str | None = Query(None, description="Filter by status (active, inactive, archived)"),
    as_of_date: str | None = Query(None, description="Date to calculate balances as of (YYYY-MM-DD)"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Export Chart of Accounts data.

    Requires authentication.

    **Query Parameters:**
    - **format**: Export format - csv, json, xlsx, or pdf (required)
    - **account_type**: Filter by account type (asset, liability, equity, income, expense) - optional
    - **status**: Filter by status (active, inactive, archived) - optional
    - **as_of_date**: Date to calculate balances as of (YYYY-MM-DD) - optional, defaults to today

    **Returns:** File download with appropriate content-type header
    """
    from datetime import date
    from fastapi import HTTPException
    from fastapi.responses import Response
    from app.models.base import AccountType, AccountStatus
    from app.services.report_service import ReportService
    from app.services.export_service import ExportService
    
    # Validate format
    valid_formats = ["csv", "json", "xlsx", "pdf"]
    if format.lower() not in valid_formats:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid format. Must be one of: {', '.join(valid_formats)}"
        )
    
    # Parse account type
    type_enum = None
    if account_type:
        try:
            type_enum = AccountType(account_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid account_type. Must be one of: asset, liability, equity, income, expense"
            )
    
    # Parse status
    status_enum = None
    if status:
        try:
            status_enum = AccountStatus(status.upper())
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: active, inactive, archived"
            )
    
    # Parse date
    balance_date = None
    if as_of_date:
        try:
            balance_date = date.fromisoformat(as_of_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid date format. Use YYYY-MM-DD"
            )
    
    # Initialize services
    report_service = ReportService(db)
    export_service = ExportService(report_service)
    
    # Generate export based on format
    format_lower = format.lower()
    
    try:
        if format_lower == "csv":
            data = export_service.export_to_csv(
                organization_id=current_user.organization_id,
                account_type=type_enum,
                status=status_enum,
                as_of_date=balance_date,
            )
            media_type = "text/csv"
            filename = f"chart_of_accounts_{date.today().isoformat()}.csv"
        
        elif format_lower == "json":
            data = export_service.export_to_json(
                organization_id=current_user.organization_id,
                account_type=type_enum,
                status=status_enum,
                as_of_date=balance_date,
            )
            media_type = "application/json"
            filename = f"chart_of_accounts_{date.today().isoformat()}.json"
        
        elif format_lower == "xlsx":
            data = export_service.export_to_xlsx(
                organization_id=current_user.organization_id,
                account_type=type_enum,
                status=status_enum,
                as_of_date=balance_date,
            )
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            filename = f"chart_of_accounts_{date.today().isoformat()}.xlsx"
        
        elif format_lower == "pdf":
            data = export_service.export_to_pdf(
                organization_id=current_user.organization_id,
                account_type=type_enum,
                status=status_enum,
                as_of_date=balance_date,
            )
            media_type = "application/pdf"
            filename = f"chart_of_accounts_{date.today().isoformat()}.pdf"
        
        # Return file download response
        return Response(
            content=data,
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    
    except Exception as e:
        logger.error(f"Export failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Export failed: {str(e)}"
        )


# ============================================================================
# Default Accounts Configuration Endpoints
# ============================================================================

@router.get(
    "/config/defaults",
    response_model=list,
    summary="Get default account mappings",
    description="Get all default account mappings for transaction types",
)
async def get_default_accounts(
    transaction_type: str | None = Query(None, description="Filter by transaction type"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all default account mappings for the organization.

    Requires authentication.

    **Query Parameters:**
    - **transaction_type**: Optional filter by transaction type

    **Returns:** List of default account mappings with account details
    """
    from app.services.default_account_service import DefaultAccountService
    from app.repositories.chart_of_account_repository import AccountRepository
    
    service = DefaultAccountService(db)
    account_repo = AccountRepository(db)
    
    # Get default accounts
    defaults = service.list_default_accounts(
        organization_id=current_user.organization_id,
        transaction_type=transaction_type,
    )
    
    # Enrich with account details
    result = []
    for default in defaults:
        account = account_repo.get_by_id(default.account_id, current_user.organization_id)
        result.append({
            "id": str(default.id),
            "organization_id": str(default.organization_id),
            "transaction_type": default.transaction_type,
            "scenario": default.scenario,
            "account_id": str(default.account_id),
            "account_code": account.account_code if account else None,
            "account_name": account.account_name if account else None,
            "account_type": account.account_type.value if account else None,
        })
    
    return result


@router.put(
    "/config/defaults",
    response_model=dict,
    summary="Update default account mappings",
    description="Create or update default account mappings for transaction types",
)
async def update_default_accounts(
    request: "DefaultAccountBulkUpdateRequest",
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create or update default account mappings.

    Requires authentication.

    **Request Body:**
    - **defaults**: List of default account mappings
      - **transaction_type**: Type of transaction (required)
      - **scenario**: Optional scenario for multiple defaults per type
      - **account_id**: UUID of the account to use as default (required)

    **Returns:** Summary of updated mappings
    """
    from app.services.default_account_service import DefaultAccountService
    from app.core.exceptions import ValidationError, ChartOfAccountNotFoundException
    
    service = DefaultAccountService(db)
    
    updated = []
    errors = []
    
    for default_data in request.defaults:
        try:
            # Set default account
            default = service.set_default_account(
                transaction_type=default_data.transaction_type,
                account_id=default_data.account_id,
                organization_id=current_user.organization_id,
                scenario=default_data.scenario,
            )
            
            updated.append({
                "transaction_type": default.transaction_type,
                "scenario": default.scenario,
                "account_id": str(default.account_id),
            })
        
        except ValidationError as e:
            errors.append({
                "error": str(e),
                "transaction_type": default_data.transaction_type,
            })
        except ChartOfAccountNotFoundException as e:
            errors.append({
                "error": str(e),
                "transaction_type": default_data.transaction_type,
            })
        except Exception as e:
            logger.error(f"Unexpected error updating default account: {str(e)}")
            errors.append({
                "error": f"Unexpected error: {str(e)}",
                "transaction_type": default_data.transaction_type,
            })
    
    return {
        "updated": updated,
        "errors": errors,
        "success_count": len(updated),
        "error_count": len(errors),
    }


@router.get(
    "/config/format",
    response_model=dict,
    summary="Get account code format pattern",
    description="Get the configured account code format pattern",
)
async def get_account_code_format(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get the configured account code format pattern.

    Requires authentication.

    **Returns:** Account code format configuration with pattern and example
    """
    from app.models.system_config import SystemConfig
    
    # Get format pattern from system config
    config = db.query(SystemConfig).filter(
        SystemConfig.key == "account_code_format"
    ).first()
    
    if not config:
        # Return default format if not configured
        return {
            "format_pattern": "^[0-9]{4}-[0-9]{2}$",
            "example": "1000-01",
        }
    
    # Generate example based on pattern
    example = None
    pattern = config.value
    
    # Simple example generation for common patterns
    if pattern == "^[0-9]{4}-[0-9]{2}$":
        example = "1000-01"
    elif pattern == "^[0-9]{4}$":
        example = "1000"
    elif pattern == "^[A-Z]{2}-[0-9]{4}$":
        example = "AS-1000"
    
    return {
        "format_pattern": pattern,
        "example": example,
    }


@router.put(
    "/config/format",
    response_model=dict,
    summary="Update account code format pattern",
    description="Update the account code format pattern",
)
async def update_account_code_format(
    format_pattern: str = Query(..., description="Regex pattern for account code format"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update the account code format pattern.

    Requires authentication.

    **Query Parameters:**
    - **format_pattern**: Regex pattern for account code format (required)

    **Returns:** Updated format configuration
    """
    from app.models.system_config import SystemConfig
    import re
    
    # Validate the pattern is a valid regex
    try:
        re.compile(format_pattern)
    except re.error as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid regex pattern: {str(e)}"
        )
    
    # Get or create system config entry
    config = db.query(SystemConfig).filter(
        SystemConfig.key == "account_code_format"
    ).first()
    
    if config:
        # Update existing
        config.value = format_pattern
        config.updated_by = str(current_user.id)
    else:
        # Create new
        config = SystemConfig(
            key="account_code_format",
            value=format_pattern,
            updated_by=str(current_user.id),
        )
        db.add(config)
    
    db.commit()
    db.refresh(config)
    
    return {
        "format_pattern": config.value,
        "updated_at": config.updated_at.isoformat(),
        "updated_by": config.updated_by,
    }
