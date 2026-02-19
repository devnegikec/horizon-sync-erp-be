"""Admin endpoints for development and testing"""

import os
import subprocess
from pathlib import Path

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
    Seed sample chart of accounts data for testing.
    
    This endpoint is only available in development mode.
    It runs the seed_chart_of_accounts.py script to populate the database 
    with sample accounts including proper parent-child hierarchy.
    """
    # Check if we're in development mode
    debug_mode = os.getenv("DEBUG", "false").lower() == "true"
    if not debug_mode:
        raise HTTPException(
            status_code=403,
            detail="Seed data endpoint is only available in development mode. Set DEBUG=true in environment."
        )
    
    try:
        # Get the path to the seed script
        script_path = Path(__file__).parent.parent.parent.parent / "seed_chart_of_accounts.py"
        
        if not script_path.exists():
            raise HTTPException(
                status_code=500,
                detail=f"Seed script not found at {script_path}"
            )
        
        # Run the seed script
        result = subprocess.run(
            ["python", str(script_path)],
            capture_output=True,
            text=True,
            timeout=60  # 60 second timeout
        )
        
        if result.returncode != 0:
            raise HTTPException(
                status_code=500,
                detail=f"Seed script failed: {result.stderr}"
            )
        
        return {
            "message": "Chart of accounts seeded successfully with parent-child hierarchy",
            "output": result.stdout,
            "accounts_created": "1000+",
            "note": "Refresh the page to see the new accounts with proper hierarchy"
        }
        
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="Seed script timed out after 60 seconds"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to seed data: {str(e)}"
        )


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
            detail="Clear data endpoint is only available in development mode. Set DEBUG=true in environment."
        )
    
    try:
        from app.models.chart_of_account import Account
        
        # Delete all accounts
        deleted_count = db.query(Account).delete()
        db.commit()
        
        return {
            "message": "All accounts deleted successfully",
            "accounts_deleted": deleted_count,
            "note": "Refresh the page to see the changes"
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to clear data: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "admin-api",
        "debug_mode": os.getenv("DEBUG", "false").lower() == "true"
    }
