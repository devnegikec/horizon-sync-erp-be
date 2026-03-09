"""Bank Accounts management API endpoints for banking integration"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.exceptions import (
    BankAccountNotFoundException,
    DuplicateIbanException,
    InvalidAccountStateException,
    ValidationError,
)
from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.models.bank_account import BankAccount
from app.schemas.bank_account import (
    BankAccountCreate,
    BankAccountHistoryResponse,
    BankAccountListResponse,
    BankAccountResponse,
    BankAccountUpdate,
    BankingOverviewResponse,
)
from app.schemas.bank_reconciliation import BankAccountBalanceResponse
from app.schemas.bank_transaction import (
    BankTransactionListResponse,
    BankTransactionResponse,
    ImportResultResponse,
    TransactionFilterParams,
)
from app.services.bank_account_service import BankAccountService
from app.services.transaction_importer import TransactionImporter

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
    "/bank-accounts/{bank_account_id}/history",
    response_model=list[BankAccountHistoryResponse],
    summary="Get bank account audit history",
    description="Retrieve complete audit trail for a bank account",
)
async def get_bank_account_history(
    bank_account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get complete audit history for a bank account.
    
    Returns all historical changes made to the bank account including
    creation, updates, activation, and deactivation events. Each history
    record includes old and new values, who made the change, when it was
    made, and the reason for the change.
    
    **History Includes:**
    - Action type (created, updated, activated, deactivated)
    - Old and new values (with masked sensitive data)
    - User who made the change
    - Timestamp of the change
    - Reason for the change
    
    **Use Cases:**
    - Compliance and audit requirements
    - Investigating account changes
    - Security and access reviews
    - Regulatory reporting
    
    **Requirements: 18.1-18.10**
    """
    try:
        service = BankAccountService(db)
        history = service.get_bank_account_history(
            bank_account_id=bank_account_id,
            organization_id=current_user.organization_id
        )
        return [BankAccountHistoryResponse.model_validate(h) for h in history]
    
    except BankAccountNotFoundException as e:
        logger.warning(f"Bank account not found for history: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error getting bank account history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve bank account history"
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


@router.post(
    "/organizations/{organization_id}/default-bank-account",
    response_model=BankAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create default bank account for organization",
    description="Create a default bank account during organization setup",
)
async def create_default_bank_account(
    organization_id: UUID,
    skip_on_error: bool = Query(True, description="Skip creation if error occurs"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Create a default bank account for a new organization.
    
    This endpoint is typically called during organization setup to create
    a default bank account linked to the default GL account. The account
    will be marked as primary and active.
    
    **Features:**
    - Creates or finds default GL account of type "Bank"
    - Creates bank account with placeholder details
    - Marks account as primary and active
    - Uses organization's base currency
    - Gracefully handles errors if skip_on_error=True
    
    **Business Rules:**
    - Organization must exist
    - User must have permission to create bank accounts
    - If skip_on_error=True, returns None on failure (logs error)
    - If skip_on_error=False, raises exception on failure
    
    Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8
    """
    try:
        # Verify user has access to this organization
        if current_user.organization_id != organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to create bank accounts for this organization"
            )
        
        # Get organization details to fetch currency
        # In a microservices architecture, we would make an HTTP call to identity-service
        # For now, we'll use a default currency and log a warning
        organization_currency = "USD"
        logger.warning(
            f"Using default currency USD for organization {organization_id}. "
            "In production, fetch from identity-service."
        )
        
        service = BankAccountService(db)
        bank_account = service.create_default_bank_account(
            organization_id=organization_id,
            organization_currency=organization_currency,
            created_by=current_user.email,
            skip_on_error=skip_on_error
        )
        
        if bank_account is None:
            # This happens when skip_on_error=True and creation failed
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create default bank account"
            )
        
        return BankAccountResponse.model_validate(bank_account)
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error creating default bank account: {e}")
        if skip_on_error:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create default bank account"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create default bank account: {str(e)}"
            )


# ============================================================================
# Transaction Import Endpoints
# ============================================================================

@router.post(
    "/bank-accounts/{bank_account_id}/import/csv",
    response_model=ImportResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Import transactions from CSV file",
    description="Import bank transactions from a CSV file with validation and duplicate detection",
)
async def import_transactions_csv(
    bank_account_id: UUID,
    file: UploadFile = File(..., description="CSV file with transaction data"),
    force_import: bool = Query(False, description="Force import duplicates with is_duplicate flag"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Import bank transactions from CSV file.
    
    **CSV Format:**
    ```csv
    date,amount,description,reference,type
    2024-01-15,1500.00,Customer Payment - INV-001,TXN-12345,credit
    2024-01-16,-250.50,Office Supplies,TXN-12346,debit
    ```
    
    **Required Columns:**
    - `date`: Transaction date in ISO 8601 format (YYYY-MM-DD)
    - `amount`: Transaction amount (numeric with up to 2 decimal places)
    - `description`: Transaction description (up to 500 characters)
    - `reference`: Bank reference or transaction ID (up to 100 characters)
    - `type`: Transaction type (either "debit" or "credit")
    
    **Features:**
    - Validates all required columns are present
    - Validates date format, amount format, and type values
    - Detects duplicate transactions automatically
    - Creates transactions with status "cleared"
    - Returns detailed import summary with counts and errors
    
    **Duplicate Detection:**
    By default, duplicate transactions are skipped. A transaction is considered
    duplicate if it matches an existing transaction on:
    - Bank account ID
    - Statement date
    - Transaction amount
    - Bank reference
    
    Set `force_import=true` to import duplicates with `is_duplicate` flag set.
    
    **Requirements: 11.1, 11.3-11.6, 11.11-11.15, 20.1-20.8**
    """
    # Validate file type
    if not file.filename or not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a CSV file with .csv extension"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Import transactions
        importer = TransactionImporter(db)
        result = importer.import_csv(
            bank_account_id=bank_account_id,
            file_content=file_content,
            organization_id=current_user.organization_id,
            force_import=force_import
        )
        
        return ImportResultResponse.model_validate(result)
    
    except ValidationError as e:
        logger.error(f"Validation error importing CSV: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error importing CSV: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import CSV file"
        )


@router.post(
    "/bank-accounts/{bank_account_id}/import/pdf",
    response_model=ImportResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Import transactions from PDF file",
    description="Import bank transactions from a PDF bank statement with text extraction and parsing",
)
async def import_transactions_pdf(
    bank_account_id: UUID,
    file: UploadFile = File(..., description="PDF bank statement file"),
    force_import: bool = Query(False, description="Force import duplicates with is_duplicate flag"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Import bank transactions from PDF bank statement.
    
    **Features:**
    - Extracts text from PDF using pdfplumber library
    - Parses transaction data using multiple regex patterns
    - Supports common bank statement formats
    - Handles multi-page statements
    - Detects transaction type from amount sign or column position
    - Automatic duplicate detection
    
    **Supported PDF Formats:**
    The system attempts to parse transactions using multiple patterns:
    1. Tabular format: Date | Description | Reference | Debit | Credit
    2. Linear format: Date Description +/-Amount Reference
    3. Balance format: Date | Description | Amount | Balance | Reference
    
    **Important Notes:**
    - PDF parsing may not work for all bank statement formats
    - If parsing fails, use CSV import instead
    - Contact support for custom PDF format support
    - Requires pdfplumber library to be installed
    
    **Duplicate Detection:**
    Same as CSV import - duplicates are detected and skipped by default.
    Set `force_import=true` to import duplicates with `is_duplicate` flag.
    
    **Requirements: 11.2, 11.7-11.10, 11.16-11.17**
    """
    # Validate file type
    if not file.filename or not file.filename.endswith('.pdf'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a PDF file with .pdf extension"
        )
    
    try:
        # Read file content
        file_content = await file.read()
        
        # Import transactions
        importer = TransactionImporter(db)
        result = importer.import_pdf(
            bank_account_id=bank_account_id,
            file_content=file_content,
            organization_id=current_user.organization_id,
            force_import=force_import
        )
        
        return ImportResultResponse.model_validate(result)
    
    except ValidationError as e:
        logger.error(f"Validation error importing PDF: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    except Exception as e:
        logger.error(f"Unexpected error importing PDF: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import PDF file"
        )


@router.post(
    "/bank-accounts/{bank_account_id}/import/mt940",
    response_model=ImportResultResponse,
    status_code=status.HTTP_200_OK,
    summary="Import transactions from MT940 file",
    description="Import bank transactions from MT940 SWIFT standard format file",
)
async def import_transactions_mt940(
    bank_account_id: UUID,
    file: UploadFile = File(..., description="MT940 SWIFT format file"),
    force_import: bool = Query(False, description="Force import duplicates with is_duplicate flag"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Import bank transactions from MT940 SWIFT format file.
    
    **MT940 Format:**
    MT940 is the SWIFT standard format for electronic bank statements,
    commonly used in European banking.
    
    **Format Structure:**
    - `:60F:` - Opening balance
    - `:61:` - Transaction statement (one per transaction)
    - `:86:` - Transaction details/description
    - `:62F:` - Closing balance
    
    **Example MT940:**
    ```
    :60F:C240115EUR5000,00
    :61:2401150115DR250,50NTRFNONREF//TXN-12345
    :86:Office Supplies Payment
    :61:2401160116CR1500,00NTRFNONREF//TXN-12346
    :86:Customer Payment - INV-001
    :62F:C240116EUR6250,50
    ```
    
    **Features:**
    - Parses opening and closing balances
    - Extracts transaction date, amount, type, and reference
    - Extracts transaction descriptions from :86: fields
    - Validates MT940 format structure
    - Automatic duplicate detection
    
    **Duplicate Detection:**
    Same as CSV import - duplicates are detected and skipped by default.
    Set `force_import=true` to import duplicates with `is_duplicate` flag.
    
    **Requirements: 12.1-12.11**
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(('.mt940', '.sta', '.txt')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be an MT940 file with .mt940, .sta, or .txt extension"
        )
    
    try:
        # Read file content as text
        file_content = await file.read()
        file_text = file_content.decode('utf-8')
        
        # Import transactions
        importer = TransactionImporter(db)
        result = importer.import_mt940(
            bank_account_id=bank_account_id,
            file_content=file_text,
            organization_id=current_user.organization_id,
            force_import=force_import
        )
        
        return ImportResultResponse.model_validate(result)
    
    except ValidationError as e:
        logger.error(f"Validation error importing MT940: {e}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    
    except UnicodeDecodeError:
        logger.error("Failed to decode MT940 file as UTF-8")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MT940 file must be in UTF-8 text format"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error importing MT940: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to import MT940 file"
        )


@router.get(
    "/bank-accounts/{bank_account_id}/transactions",
    response_model=BankTransactionListResponse,
    summary="List bank transactions",
    description="Get paginated list of bank transactions with filtering options",
)
async def list_bank_transactions(
    bank_account_id: UUID,
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    page_size: int = Query(20, ge=1, le=100, description="Number of items per page"),
    status: Optional[str] = Query(None, description="Filter by transaction status"),
    transaction_type: Optional[str] = Query(None, description="Filter by transaction type (debit/credit)"),
    date_from: Optional[str] = Query(None, description="Filter transactions from this date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter transactions to this date (YYYY-MM-DD)"),
    search: Optional[str] = Query(None, description="Search in description or reference"),
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    List bank transactions with pagination and filtering.
    
    Returns a paginated list of bank transactions for the specified bank account
    with various filtering options.
    
    **Filtering Options:**
    - `status`: Filter by transaction status (pending, cleared, reconciled, void)
    - `transaction_type`: Filter by type (debit or credit)
    - `date_from`: Show transactions from this date onwards
    - `date_to`: Show transactions up to this date
    - `search`: Search in transaction description or bank reference
    
    **Response Features:**
    - Pagination metadata (total, pages, navigation)
    - Transaction details including amounts, dates, and status
    - Import metadata (source, batch ID)
    - Reconciliation status and timestamp
    - Duplicate flag indication
    
    **Use Cases:**
    - Review imported transactions before reconciliation
    - Monitor transaction import batches
    - Search for specific transactions
    - Identify unreconciled transactions
    - Audit transaction history
    
    **Requirements: 3.1-3.11**
    """
    try:
        # Verify bank account exists and belongs to organization
        bank_account_service = BankAccountService(db)
        bank_account = bank_account_service.get_bank_account_by_id(
            bank_account_id=bank_account_id,
            organization_id=current_user.organization_id
        )
        
        # Build query
        from app.models.bank_transaction import BankTransaction
        from sqlalchemy import and_, or_
        from datetime import datetime
        
        query = db.query(BankTransaction).filter(
            and_(
                BankTransaction.bank_account_id == bank_account_id,
                BankTransaction.organization_id == current_user.organization_id
            )
        )
        
        # Apply filters
        if status:
            query = query.filter(BankTransaction.transaction_status == status)
        
        if transaction_type:
            query = query.filter(BankTransaction.transaction_type == transaction_type)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d').date()
                query = query.filter(BankTransaction.statement_date >= date_from_obj)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="date_from must be in YYYY-MM-DD format"
                )
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').date()
                query = query.filter(BankTransaction.statement_date <= date_to_obj)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="date_to must be in YYYY-MM-DD format"
                )
        
        if search:
            search_pattern = f"%{search}%"
            query = query.filter(
                or_(
                    BankTransaction.transaction_description.ilike(search_pattern),
                    BankTransaction.bank_reference.ilike(search_pattern)
                )
            )
        
        # Get total count
        total = query.count()
        
        # Calculate pagination
        total_pages = (total + page_size - 1) // page_size
        offset = (page - 1) * page_size
        
        # Get paginated results
        transactions = query.order_by(
            BankTransaction.statement_date.desc(),
            BankTransaction.imported_at.desc()
        ).offset(offset).limit(page_size).all()
        
        return BankTransactionListResponse(
            items=[BankTransactionResponse.model_validate(t) for t in transactions],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    
    except BankAccountNotFoundException as e:
        logger.warning(f"Bank account not found: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Unexpected error listing transactions: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve transactions"
        )



@router.get(
    "/{bank_account_id}/balance",
    response_model=BankAccountBalanceResponse,
    summary="Get bank and GL balances",
    description="Get bank balance, GL balance, and unreconciled amount for a bank account",
)
async def get_bank_account_balance(
    bank_account_id: UUID,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Get bank account balance information.
    
    Returns:
    - Bank balance (calculated from bank_transactions)
    - GL balance (calculated from journal_entries)
    - Unreconciled amount (difference between bank and GL balance)
    - Last reconciled date
    - Count of unreconciled transactions
    
    **Requirements: 16.10, 14.8, 14.9**
    """
    try:
        from app.models.bank_transaction import BankTransaction
        from app.models.bank_reconciliation import BankReconciliation
        from app.models.journal_entry import JournalEntry, JournalEntryLine
        from app.models.chart_of_account import Account
        from sqlalchemy import and_, func
        from decimal import Decimal
        
        # Verify bank account exists and belongs to organization
        bank_account = db.query(BankAccount).filter(
            and_(
                BankAccount.id == bank_account_id,
                BankAccount.organization_id == current_user.organization_id
            )
        ).first()
        
        if not bank_account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Bank account not found"
            )
        
        # Get GL account info
        gl_account = db.query(Account).filter(Account.id == bank_account.gl_account_id).first()
        gl_account_name = gl_account.account_name if gl_account else "Unknown"
        
        # Calculate bank balance from bank_transactions
        # Sum all cleared and reconciled transactions
        bank_balance_result = db.query(
            func.sum(
                func.case(
                    (BankTransaction.transaction_type == "credit", BankTransaction.transaction_amount),
                    else_=-BankTransaction.transaction_amount
                )
            )
        ).filter(
            and_(
                BankTransaction.bank_account_id == bank_account_id,
                BankTransaction.organization_id == current_user.organization_id,
                BankTransaction.transaction_status.in_(["cleared", "reconciled"])
            )
        ).scalar()
        
        bank_balance = bank_balance_result if bank_balance_result is not None else Decimal('0')
        
        # Calculate GL balance from journal_entries
        # Sum all journal entry lines for the GL account
        gl_balance_result = db.query(
            func.sum(JournalEntryLine.debit) - func.sum(JournalEntryLine.credit)
        ).join(JournalEntry).filter(
            and_(
                JournalEntryLine.account_id == bank_account.gl_account_id,
                JournalEntry.organization_id == current_user.organization_id,
                JournalEntry.status == "posted"
            )
        ).first()
        
        gl_balance = gl_balance_result[0] if gl_balance_result and gl_balance_result[0] is not None else Decimal('0')
        
        # Calculate unreconciled amount
        unreconciled_amount = bank_balance - gl_balance
        
        # Get last reconciled date
        last_reconciliation = db.query(BankReconciliation).join(BankTransaction).filter(
            and_(
                BankTransaction.bank_account_id == bank_account_id,
                BankReconciliation.organization_id == current_user.organization_id,
                BankReconciliation.reconciliation_status == "confirmed",
                BankReconciliation.is_active == True
            )
        ).order_by(BankReconciliation.reconciled_at.desc()).first()
        
        last_reconciled_date = None
        if last_reconciliation and last_reconciliation.reconciled_at:
            last_reconciled_date = last_reconciliation.reconciled_at.date()
        
        # Count unreconciled transactions
        unreconciled_count = db.query(func.count(BankTransaction.id)).filter(
            and_(
                BankTransaction.bank_account_id == bank_account_id,
                BankTransaction.organization_id == current_user.organization_id,
                BankTransaction.transaction_status == "cleared",
                BankTransaction.reconciled_at.is_(None)
            )
        ).scalar()
        
        return BankAccountBalanceResponse(
            bank_account_id=bank_account_id,
            bank_account_name=f"{bank_account.bank_name} - {bank_account.account_holder_name}",
            gl_account_id=bank_account.gl_account_id,
            gl_account_name=gl_account_name,
            currency=bank_account.currency,
            bank_balance=bank_balance,
            gl_balance=gl_balance,
            unreconciled_amount=unreconciled_amount,
            last_reconciled_date=last_reconciled_date,
            unreconciled_transaction_count=unreconciled_count or 0
        )
    
    except HTTPException:
        raise
    
    except Exception as e:
        logger.error(f"Error getting bank account balance: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get bank account balance"
        )
