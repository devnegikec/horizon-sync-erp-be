"""Admin endpoints for development and testing"""

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import CurrentUser, get_current_user

router = APIRouter()


@router.post("/seed-data")
async def seed_sample_data(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Create default chart of accounts for organization.

    This endpoint creates a comprehensive chart of accounts with:
    - 35+ GL accounts with proper hierarchy (Assets, Liabilities, Equity, Revenue, Expenses)
    - Default account mappings for common transaction types
    - Proper validation against account code format

    This endpoint is idempotent - calling it multiple times will not create duplicates.
    This endpoint is only available in development mode.
    """
    # Check if we're in development mode
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    if not debug_mode:
        raise HTTPException(
            status_code=403,
            detail="Seed data endpoint is only available in development mode. Set DEBUG=true in environment.",
        )

    try:
        from app.services.default_chart_setup_service import DefaultChartSetupService

        # Get organization currency (default to USD for now)
        organization_currency = "USD"
        
        # Use the existing default chart setup service
        service = DefaultChartSetupService(db)
        result = service.create_default_chart_of_accounts(
            organization_id=current_user.organization_id,
            currency=organization_currency,
            created_by=str(current_user.id),
        )
        
        if result.already_existed:
            return {
                "message": "Default chart of accounts already exists",
                "accounts_created": 0,
                "mappings_created": 0,
                "accounts": result.accounts,
                "mappings": result.mappings,
                "note": "Chart of accounts already exists. No changes made."
            }
        
        return {
            "message": "Default chart of accounts created successfully",
            "accounts_created": len(result.accounts),
            "mappings_created": len(result.mappings),
            "accounts": result.accounts,
            "mappings": result.mappings,
            "note": "Chart of accounts created with proper hierarchy and default mappings."
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create chart of accounts: {str(e)}")


@router.delete("/clear-data")
async def clear_sample_data(
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    """
    Clear all chart of accounts data.

    This endpoint is only available in development mode.
    WARNING: This will delete ALL accounts in the database!
    """
    # Check if we're in development mode
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    if not debug_mode:
        raise HTTPException(
            status_code=403,
            detail="Clear data endpoint is only available in development mode. Set DEBUG=true in environment.",
        )

    try:
        from app.models.chart_of_account import Account

        # Delete all accounts
        deleted_count = db.query(Account).delete()
        db.commit()

        return {
            "message": "All accounts deleted successfully",
            "accounts_deleted": deleted_count,
            "note": "Refresh the page to see the changes",
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to clear data: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "admin-api",
        "debug_mode": os.getenv("DEBUG", "false").lower() == "true",
    }
