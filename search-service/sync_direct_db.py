"""
Direct database sync script - syncs from core_db to search_db directly.
This bypasses API authentication issues.

Usage:
    python sync_direct_db.py
"""

import asyncio
import sys
from sqlalchemy import select, delete, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any

from app.config import settings
from app.logging_config import get_logger
from app.models.database import SearchDocument

logger = get_logger(__name__)


async def main():
    """Main sync function"""
    logger.info("Starting direct database synchronization...")
    
    # Fix database URLs for async driver
    search_db_url = settings.database_url
    if search_db_url.startswith("postgresql://"):
        search_db_url = search_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    # Core database URL (same host, different database)
    core_db_url = search_db_url.replace("/search_db", "/core_db")
    
    logger.info(f"Search DB: {search_db_url}")
    logger.info(f"Core DB: {core_db_url}")
    
    # Create engines
    search_engine = create_async_engine(search_db_url, echo=False, pool_pre_ping=True)
    core_engine = create_async_engine(core_db_url, echo=False, pool_pre_ping=True)
    
    search_session_maker = sessionmaker(search_engine, class_=AsyncSession, expire_on_commit=False)
    core_session_maker = sessionmaker(core_engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with search_session_maker() as search_session, core_session_maker() as core_session:
            results = {}
            
            # Sync items
            items_count = await sync_items(search_session, core_session)
            results["items"] = items_count
            
            # Sync customers
            customers_count = await sync_customers(search_session, core_session)
            results["customers"] = customers_count
            
            # Sync suppliers
            suppliers_count = await sync_suppliers(search_session, core_session)
            results["suppliers"] = suppliers_count
            
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
        await search_engine.dispose()
        await core_engine.dispose()



async def sync_items(search_session: AsyncSession, core_session: AsyncSession) -> int:
    """Sync items from core database."""
    logger.info("Starting items sync...")
    try:
        # Fetch items from core database with item_group name via join
        result = await core_session.execute(
            text("""
                SELECT i.id, i.item_code, i.item_name, i.description, ig.name as item_group_name, i.uom
                FROM items i
                LEFT JOIN item_groups ig ON i.item_group_id = ig.id
                WHERE i.status = 'active'
            """)
        )
        items = result.fetchall()
        
        if not items:
            logger.warning("No items found in core database")
            return 0
        
        # Clear existing items in search index
        await search_session.execute(
            delete(SearchDocument).where(SearchDocument.entity_type == "items")
        )
        
        # Insert items into search index
        count = 0
        for item in items:
            item_id = str(item[0])
            item_code = item[1] or ""
            item_name = item[2] or ""
            description = item[3] or ""
            item_group = item[4] or ""
            uom = item[5] or ""
            
            title = f"{item_code} - {item_name}" if item_code else item_name
            content = " ".join(filter(None, [item_code, item_name, description, item_group]))
            
            metadata = {
                "item_code": item_code,
                "item_name": item_name,
                "item_group": item_group,
                "uom": uom,
            }
            
            search_doc = SearchDocument(
                entity_id=item_id,
                entity_type="items",
                title=title,
                content=content,
                metadata_=metadata
            )
            search_session.add(search_doc)
            count += 1
        
        await search_session.commit()
        logger.info(f"Synced {count} items")
        return count
    except Exception as e:
        logger.error(f"Error syncing items: {e}", exc_info=True)
        await search_session.rollback()
        return 0


async def sync_customers(search_session: AsyncSession, core_session: AsyncSession) -> int:
    """Sync customers from core database."""
    logger.info("Starting customers sync...")
    try:
        result = await core_session.execute(
            text("""
                SELECT id, customer_code, customer_name, email, phone, city, country
                FROM customers
                WHERE status = 'active'
            """)
        )
        customers = result.fetchall()
        
        if not customers:
            logger.warning("No customers found in core database")
            return 0
        
        await search_session.execute(
            delete(SearchDocument).where(SearchDocument.entity_type == "customers")
        )
        
        count = 0
        for customer in customers:
            customer_id = str(customer[0])
            customer_code = customer[1] or ""
            customer_name = customer[2] or ""
            email = customer[3] or ""
            phone = customer[4] or ""
            city = customer[5] or ""
            country = customer[6] or ""
            
            title = f"{customer_code} - {customer_name}" if customer_code else customer_name
            content = " ".join(filter(None, [customer_code, customer_name, email, phone, city, country]))
            
            metadata = {
                "customer_code": customer_code,
                "customer_name": customer_name,
                "email": email,
                "phone": phone,
                "city": city,
                "country": country,
            }
            
            search_doc = SearchDocument(
                entity_id=customer_id,
                entity_type="customers",
                title=title,
                content=content,
                metadata_=metadata
            )
            search_session.add(search_doc)
            count += 1
        
        await search_session.commit()
        logger.info(f"Synced {count} customers")
        return count
    except Exception as e:
        logger.error(f"Error syncing customers: {e}", exc_info=True)
        await search_session.rollback()
        return 0



async def sync_suppliers(search_session: AsyncSession, core_session: AsyncSession) -> int:
    """Sync suppliers from core database."""
    logger.info("Starting suppliers sync...")
    try:
        result = await core_session.execute(
            text("""
                SELECT id, supplier_code, supplier_name, email, phone, city, country
                FROM suppliers
                WHERE status = 'active'
            """)
        )
        suppliers = result.fetchall()
        
        if not suppliers:
            logger.warning("No suppliers found in core database")
            return 0
        
        await search_session.execute(
            delete(SearchDocument).where(SearchDocument.entity_type == "suppliers")
        )
        
        count = 0
        for supplier in suppliers:
            supplier_id = str(supplier[0])
            supplier_code = supplier[1] or ""
            supplier_name = supplier[2] or ""
            email = supplier[3] or ""
            phone = supplier[4] or ""
            city = supplier[5] or ""
            country = supplier[6] or ""
            
            title = f"{supplier_code} - {supplier_name}" if supplier_code else supplier_name
            content = " ".join(filter(None, [supplier_code, supplier_name, email, phone, city, country]))
            
            metadata = {
                "supplier_code": supplier_code,
                "supplier_name": supplier_name,
                "email": email,
                "phone": phone,
                "city": city,
                "country": country,
            }
            
            search_doc = SearchDocument(
                entity_id=supplier_id,
                entity_type="suppliers",
                title=title,
                content=content,
                metadata_=metadata
            )
            search_session.add(search_doc)
            count += 1
        
        await search_session.commit()
        logger.info(f"Synced {count} suppliers")
        return count
    except Exception as e:
        logger.error(f"Error syncing suppliers: {e}", exc_info=True)
        await search_session.rollback()
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
