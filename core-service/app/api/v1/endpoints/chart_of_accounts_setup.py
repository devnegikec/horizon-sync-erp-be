"""Chart of Accounts Setup API endpoints"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_active_user
from app.schemas.chart_of_accounts_setup import (
    DefaultChartSetupRequest,
    DefaultChartSetupResponse,
    ManualTriggerRequest,
)
from app.services.default_chart_setup_service import DefaultChartSetupService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/setup/default-chart-of-accounts",
    response_model=DefaultChartSetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Create default chart of accounts",
    description="Create default chart of accounts for an organization. This endpoint is idempotent.",
)
async def create_default_chart_of_accounts(
    request: DefaultChartSetupRequest,
    db: Session = Depends(get_db),
):
    """
    Create default chart of accounts for an organization.

    This endpoint is idempotent - calling it multiple times for the same
    organization will not create duplicate accounts.

    **Request Body:**
    - **organization_id**: UUID of the organization (required)
    - **currency**: ISO currency code (default: "USD")
    - **created_by**: User identifier (required)

    **Returns:**
    - **success**: boolean indicating operation success
    - **organization_id**: UUID of the organization
    - **accounts_created**: number of accounts created
    - **mappings_created**: number of default account mappings created
    - **message**: status message
    - **errors**: list of errors if operation failed (optional)

    **Status Codes:**
    - 200 OK: Chart created successfully or already exists
    - 422 Unprocessable Entity: Invalid request data
    - 500 Internal Server Error: Chart creation failed
    """
    service = DefaultChartSetupService(db)

    try:
        result = service.create_default_chart_of_accounts(
            organization_id=request.organization_id,
            currency=request.currency,
            created_by=request.created_by,
        )

        if result.already_existed:
            return DefaultChartSetupResponse(
                success=True,
                organization_id=request.organization_id,
                accounts_created=0,
                mappings_created=0,
                message="Default chart of accounts already exists",
            )

        return DefaultChartSetupResponse(
            success=True,
            organization_id=request.organization_id,
            accounts_created=len(result.accounts),
            mappings_created=len(result.mappings),
            message="Default chart of accounts created successfully",
        )

    except Exception as e:
        logger.error(
            "Failed to create default chart of accounts",
            extra={
                "organization_id": str(request.organization_id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create default chart of accounts: {str(e)}",
        )


@router.post(
    "/setup/default-chart-of-accounts/{organization_id}/trigger",
    response_model=DefaultChartSetupResponse,
    status_code=status.HTTP_200_OK,
    summary="Manually trigger default chart creation",
    description="Manually trigger default chart of accounts creation for an organization. Requires admin permissions.",
)
async def trigger_default_chart_creation(
    organization_id: UUID,
    request: ManualTriggerRequest,
    current_user: CurrentUser = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """
    Manually trigger default chart of accounts creation.

    This endpoint allows administrators to manually create the default
    chart of accounts for organizations where automatic creation failed.

    Requires: Authentication (admin permissions recommended but not enforced in this version)

    **Path Parameters:**
    - **organization_id**: UUID of the organization

    **Request Body:**
    - **currency**: ISO currency code (default: "USD")
    - **force_recreate**: If True, recreate even if accounts exist (default: False)

    **Returns:**
    - **success**: boolean indicating operation success
    - **organization_id**: UUID of the organization
    - **accounts_created**: number of accounts created
    - **mappings_created**: number of default account mappings created
    - **message**: status message
    - **errors**: list of errors if operation failed (optional)

    **Status Codes:**
    - 200 OK: Chart created successfully or already exists
    - 401 Unauthorized: User not authenticated
    - 422 Unprocessable Entity: Invalid request data
    - 500 Internal Server Error: Chart creation failed
    """
    service = DefaultChartSetupService(db)

    try:
        # TODO: Add force_recreate logic to delete existing accounts if requested
        # For now, we just call the standard creation method which is idempotent
        if request.force_recreate:
            logger.warning(
                "force_recreate option not yet implemented, proceeding with standard creation",
                extra={
                    "organization_id": str(organization_id),
                    "user_id": str(current_user.id),
                },
            )

        result = service.create_default_chart_of_accounts(
            organization_id=organization_id,
            currency=request.currency,
            created_by=str(current_user.id),
        )

        if result.already_existed:
            return DefaultChartSetupResponse(
                success=True,
                organization_id=organization_id,
                accounts_created=0,
                mappings_created=0,
                message="Default chart of accounts already exists",
            )

        return DefaultChartSetupResponse(
            success=True,
            organization_id=organization_id,
            accounts_created=len(result.accounts),
            mappings_created=len(result.mappings),
            message="Default chart of accounts created successfully",
        )

    except Exception as e:
        logger.error(
            "Failed to manually trigger default chart creation",
            extra={
                "organization_id": str(organization_id),
                "user_id": str(current_user.id),
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create default chart of accounts: {str(e)}",
        )
