"""
CLI script to sync data from core-service to search-service.

Usage:
    python sync_data.py
"""

import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.services.sync_service import SyncService
from app.logging_config import get_logger

logger = get_logger(__name__)


async def main():
    """Main sync function"""
    logger.info("Starting data synchronization...")
    logger.info(f"Core Service URL: {settings.core_service_url}")
    logger.info(f"Database URL: {settings.database_url}")
    
    # Create database engine
    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )
    
    # Create session
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )
    
    try:
        async with async_session() as session:
            # Create sync service
            sync_service = SyncService(session, auth_token=None)
            
            # Sync all entities
            logger.info("Syncing all entities...")
            results = await sync_service.sync_all_entities()
            
            # Print results
            print("\n" + "="*60)
            print("SYNC RESULTS")
            print("="*60)
            for entity_type, count in results.items():
                print(f"{entity_type.capitalize()}: {count} records synced")
            print(f"\nTotal: {sum(results.values())} records synced")
            print("="*60)
            
            logger.info("Synchronization completed successfully")
            return 0
            
    except Exception as e:
        logger.error(f"Synchronization failed: {e}", exc_info=True)
        print(f"\nERROR: {e}")
        return 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
