"""Bank Accounts management API endpoints for banking integration"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BankAccountNotFoundException,
    DuplicateIbanException,
    InvalidAccountStateException,
    ValidationError,
)
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.bank_account import (
    BankAccountCreate,
    BankAccountListResponse,
    BankAccountResponse,
    BankAccountUpdate,
    BankingOverviewResponse,
)
from app.services.bank_account_service import BankAccountService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/chart-of-accounts/{account_id}/bank-accounts",
    response_model=BankAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link bank account to GL account",
    description="Create a new bank account linked to a GL account",
)
async def create_bank_account(
    account_id: UUID,
    data: BankAccountCreate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Link a bank account to a GL account.
    
    This endpoint creates a new bank account record linked to an existing
    General Ledger account. The bank account will contain sensitive banking
    information that is separate from the GL account data.
    
    **Features:**
    - Link multiple bank accounts to a single GL account
    - Set one bank account as primary per GL account
    - Validate IBAN, SWIFT codes, and routing numbers
    - Encrypt sensitive banking information
    - Create audit trail for all banking operations
    
    **Business Rules:**
    - Only one primary bank account per GL account is allowed
    - IBAN must be unique within the organization
    - GL account must exist and belong to the organization
    """
    try:
        service = BankAccountService(db)
        bank_account = service.create_bank_account(
            gl_account_id=account_id,
            data=data,
            organization_id=current_user.organization_id,
            current_user=current_user.email
        )
        return BankAccountResponse.model_validate(bank_account)
    
    except ValidationError as e:
        logger.error(f"Validation error creating bank account: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    except DuplicateIbanException as e:
        logger.error(f"Duplicate IBAN error: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error creating bank account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create bank account"
        )


@router.get(
    "/chart-of-accounts/{account_id}/bank-accounts",
    response_model=list[BankAccountResponse],
    summary="Get bank accounts for GL account",
    description="Retrieve all bank accounts linked to a specific GL account",
)
async def list_bank_accounts_for_gl_account(
    account_id: UUID,
    include_inactive: bool = Query(False, description="Include inactive bank accounts"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get all bank accounts linked to a GL account.
    
    Returns all bank accounts associated with the specified GL account.
    By default, only active bank accounts are returned unless specifically
    requested to include inactive accounts.
    
    **Query Parameters:**
    - `include_inactive`: Set to true to include deactivated bank accounts
    
    **Response includes:**
    - Masked sensitive information (account numbers, IBANs)
    - Banking features and capabilities
    - Transfer limits and controls
    - Primary bank account designation
    """
    try:
        service = BankAccountService(db)
        bank_accounts = service.get_bank_accounts_by_gl_account(
            gl_account_id=account_id,
            organization_id=current_user.organization_id,
            include_inactive=include_inactive
        )
        return [BankAccountResponse.model_validate(ba) for ba in bank_accounts]
    
    except ValidationError as e:
        logger.error(f"Validation error listing bank accounts: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error listing bank accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bank accounts"
        )


@router.get(
    "/bank-accounts",
    response_model=BankAccountListResponse,
    summary="List bank accounts with pagination",
    description="Get paginated list of bank accounts with filtering options",
)
async def list_bank_accounts(
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    gl_account_id: Optional[UUID] = Query(None, description="Filter by GL account ID"),
    bank_name: Optional[str] = Query(None, description="Filter by bank name (partial match)"),
    account_purpose: Optional[str] = Query(None, description="Filter by account purpose"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    is_primary: Optional[bool] = Query(None, description="Filter by primary status"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List bank accounts with pagination and filtering.
    
    Returns a paginated list of bank accounts for the organization with
    various filtering options to help locate specific accounts.
    
    **Filtering Options:**
    - `gl_account_id`: Show only bank accounts for a specific GL account
    - `bank_name`: Search by bank name (case-insensitive partial match)
    - `account_purpose`: Filter by purpose (operating, payroll, tax, etc.)
    - `is_active`: Show only active or inactive accounts
    - `is_primary`: Show only primary or secondary accounts
    
    **Response Features:**
    - Pagination metadata (total, pages, navigation)
    - Masked sensitive information for security
    - GL account information included
    - Sorting by primary status and creation date
    """
    try:
        service = BankAccountService(db)
        return service.list_bank_accounts(
            organization_id=current_user.organization_id,
            page=page,
            page_size=page_size,
            gl_account_id=gl_account_id,
            bank_name=bank_name,
            account_purpose=account_purpose,
            is_active=is_active,
            is_primary=is_primary
        )
    
    except Exception as e:
        logger.error(f"Unexpected error listing bank accounts: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bank accounts list"
        )


@router.get(
    "/bank-accounts/{bank_account_id}",
    response_model=BankAccountResponse,
    summary="Get bank account details",
    description="Retrieve detailed information for a specific bank account",
)
async def get_bank_account(
    bank_account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get detailed information for a specific bank account.
    
    Returns complete bank account information including masked sensitive
    data, banking features, transfer limits, and linked GL account details.
    
    **Security Features:**
    - Account numbers and IBANs are masked for security
    - Only users from the same organization can access the data
    - Full audit trail is maintained for access
    """
    try:
        service = BankAccountService(db)
        bank_account = service.get_bank_account_by_id(
            bank_account_id=bank_account_id,
            organization_id=current_user.organization_id
        )
        return BankAccountResponse.model_validate(bank_account)
    
    except BankAccountNotFoundException as e:
        logger.warning(f"Bank account not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error retrieving bank account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bank account"
        )


@router.put(
    "/bank-accounts/{bank_account_id}",
    response_model=BankAccountResponse,
    summary="Update bank account",
    description="Update bank account information and settings",
)
async def update_bank_account(
    bank_account_id: UUID,
    data: BankAccountUpdate,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Update bank account information and settings.
    
    Allows updating of bank account details including banking information,
    features, limits, and settings. All changes are tracked in the audit log.
    
    **Updatable Fields:**
    - Banking details (name, holder, IBAN, SWIFT, etc.)
    - Account metadata (type, purpose, primary status)
    - Banking features (online, mobile, wire transfers, ACH)
    - Transfer limits and approval requirements
    - API integration settings
    
    **Business Rules:**
    - Only one primary bank account per GL account
    - IBAN must remain unique within organization
    - Cannot modify GL account association
    """
    try:
        service = BankAccountService(db)
        bank_account = service.update_bank_account(
            bank_account_id=bank_account_id,
            data=data,
            organization_id=current_user.organization_id,
            current_user=current_user.email
        )
        return BankAccountResponse.model_validate(bank_account)
    
    except BankAccountNotFoundException as e:
        logger.warning(f"Bank account not found for update: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    except ValidationError as e:
        logger.error(f"Validation error updating bank account: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    except DuplicateIbanException as e:
        logger.error(f"Duplicate IBAN error on update: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error updating bank account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update bank account"
        )


@router.delete(
    "/bank-accounts/{bank_account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete bank account",
    description="Remove bank account link from GL account",
)
async def delete_bank_account(
    bank_account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Delete (remove) a bank account link.
    
    Permanently removes the bank account link from the GL account.
    This action is irreversible and will remove all banking information
    while maintaining the audit trail.
    
    **Important Notes:**
    - This does NOT delete the actual bank account with the bank
    - Only removes the link between GL account and banking information
    - All audit history is preserved for compliance
    - Cannot delete if there are pending transactions (future enhancement)
    """
    try:
        service = BankAccountService(db)
        service.delete_bank_account(
            bank_account_id=bank_account_id,
            organization_id=current_user.organization_id,
            current_user=current_user.email
        )
        return  # 204 No Content
    
    except BankAccountNotFoundException as e:
        logger.warning(f"Bank account not found for deletion: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error deleting bank account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete bank account"
        )


@router.put(
    "/bank-accounts/{bank_account_id}/activate",
    response_model=BankAccountResponse,
    summary="Activate bank account",
    description="Activate a deactivated bank account",
)
async def activate_bank_account(
    bank_account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Activate a previously deactivated bank account.
    
    Reactivates a bank account that was previously deactivated, making it
    available for banking operations again.
    """
    try:
        service = BankAccountService(db)
        bank_account = service.activate_bank_account(
            bank_account_id=bank_account_id,
            organization_id=current_user.organization_id,
            current_user=current_user.email
        )
        return BankAccountResponse.model_validate(bank_account)
    
    except BankAccountNotFoundException as e:
        logger.warning(f"Bank account not found for activation: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    except InvalidAccountStateException as e:
        logger.warning(f"Invalid state for activation: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error activating bank account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate bank account"
        )


@router.put(
    "/bank-accounts/{bank_account_id}/deactivate",
    response_model=BankAccountResponse,
    summary="Deactivate bank account",
    description="Deactivate a bank account (soft delete)",
)
async def deactivate_bank_account(
    bank_account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Deactivate a bank account (soft delete).
    
    Deactivates a bank account without permanently deleting it. This is
    useful for temporary suspension of banking operations or compliance
    requirements that prevent immediate deletion.
    
    **Features:**
    - Maintains all historical data and audit trail
    - Can be reactivated later if needed
    - Removes from active banking operations
    - Preserves compliance and audit requirements
    """
    try:
        service = BankAccountService(db)
        bank_account = service.deactivate_bank_account(
            bank_account_id=bank_account_id,
            organization_id=current_user.organization_id,
            current_user=current_user.email
        )
        return BankAccountResponse.model_validate(bank_account)
    
    except BankAccountNotFoundException as e:
        logger.warning(f"Bank account not found for deactivation: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    except InvalidAccountStateException as e:
        logger.warning(f"Invalid state for deactivation: {e}")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error deactivating bank account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate bank account"
        )


@router.get(
    "/banking/overview",
    response_model=BankingOverviewResponse,
    summary="Get banking overview",
    description="Get summary statistics and overview of all banking accounts",
)
async def get_banking_overview(
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get banking overview with summary statistics.
    
    Provides a comprehensive overview of all banking accounts in the
    organization including counts, categorization, and summary metrics.
    
    **Overview Includes:**
    - Total number of bank accounts (active and inactive)
    - Count of primary bank accounts
    - Breakdown by account purpose (operating, payroll, etc.)
    - Breakdown by account type (checking, savings, etc.)
    - Banking feature adoption statistics
    
    **Use Cases:**
    - Executive dashboards and reporting
    - Banking operations monitoring
    - Compliance and audit preparation
    - Financial planning and analysis
    """
    try:
        service = BankAccountService(db)
        return service.get_banking_overview(organization_id=current_user.organization_id)
    
    except Exception as e:
        logger.error(f"Unexpected error getting banking overview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve banking overview"
        )