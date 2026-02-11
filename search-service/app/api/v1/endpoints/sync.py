"""Sync API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_active_user, require_permission
from app.models.user import UserContext
from app.services.sync_service import SyncService

router = APIRouter(prefix="/sync", tags=["Sync"])


@router.post(
    "/all",
    status_code=status.HTTP_200_OK,
    summary="Sync all entities from core-service",
    description=(
        "Synchronize all entity types (items, customers, suppliers, warehouses) "
        "from core-service to search index. "
        "Requires 'search.admin' or 'search.sync' permission."
    ),
)
async def sync_all(
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(require_permission("search.sync")),
):
    """
    Sync all entities from core-service to search index.
    
    Args:
        db: Database session
        current_user: Current authenticated user with search.sync permission
        
    Returns:
        Dictionary with sync results
        
    Raises:
        HTTPException: If sync fails
    """
    try:
        # Create sync service with user's token
        # Note: In production, you might want to use a service account token
        sync_service = SyncService(db, auth_token=None)
        
        # Sync all entities
        results = await sync_service.sync_all_entities()
        
        return {
            "status": "success",
            "message": "Sync completed successfully",
            "results": results,
            "total_synced": sum(results.values())
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Sync failed: {str(e)}", "code": "SYNC_ERROR"}
        ) from e


@router.post(
    "/items",
    status_code=status.HTTP_200_OK,
    summary="Sync items from core-service",
    description="Synchronize items from core-service to search index.",
)
async def sync_items(
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(require_permission("search.sync")),
):
    """
    Sync items from core-service.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dictionary with sync results
    """
    try:
        sync_service = SyncService(db, auth_token=None)
        count = await sync_service.sync_items()
        
        return {
            "status": "success",
            "message": f"Synced {count} items",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Sync failed: {str(e)}", "code": "SYNC_ERROR"}
        ) from e


@router.post(
    "/customers",
    status_code=status.HTTP_200_OK,
    summary="Sync customers from core-service",
    description="Synchronize customers from core-service to search index.",
)
async def sync_customers(
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(require_permission("search.sync")),
):
    """
    Sync customers from core-service.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dictionary with sync results
    """
    try:
        sync_service = SyncService(db, auth_token=None)
        count = await sync_service.sync_customers()
        
        return {
            "status": "success",
            "message": f"Synced {count} customers",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Sync failed: {str(e)}", "code": "SYNC_ERROR"}
        ) from e


@router.post(
    "/suppliers",
    status_code=status.HTTP_200_OK,
    summary="Sync suppliers from core-service",
    description="Synchronize suppliers from core-service to search index.",
)
async def sync_suppliers(
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(require_permission("search.sync")),
):
    """
    Sync suppliers from core-service.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dictionary with sync results
    """
    try:
        sync_service = SyncService(db, auth_token=None)
        count = await sync_service.sync_suppliers()
        
        return {
            "status": "success",
            "message": f"Synced {count} suppliers",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Sync failed: {str(e)}", "code": "SYNC_ERROR"}
        ) from e


@router.post(
    "/warehouses",
    status_code=status.HTTP_200_OK,
    summary="Sync warehouses from core-service",
    description="Synchronize warehouses from core-service to search index.",
)
async def sync_warehouses(
    db: AsyncSession = Depends(get_db),
    current_user: UserContext = Depends(require_permission("search.sync")),
):
    """
    Sync warehouses from core-service.
    
    Args:
        db: Database session
        current_user: Current authenticated user
        
    Returns:
        Dictionary with sync results
    """
    try:
        sync_service = SyncService(db, auth_token=None)
        count = await sync_service.sync_warehouses()
        
        return {
            "status": "success",
            "message": f"Synced {count} warehouses",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Sync failed: {str(e)}", "code": "SYNC_ERROR"}
        ) from e
