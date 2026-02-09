"""
Standalone CLI script to sync data from core-service to search-service.
This version includes the SyncService inline to avoid import issues.

Usage:
    python sync_standalone.py
"""

import asyncio
import sys
import httpx
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import List, Dict, Any

from app.config import settings
from app.logging_config import get_logger
from app.models.database import SearchDocument

logger = get_logger(__name__)


class SyncService:
    """Service to synchronize data from core-service to search index"""
    
    def __init__(self, db: AsyncSession, auth_token: str = None):
        self.db = db
        self.auth_token = auth_token
        self.core_service_url = settings.core_service_url
    
    async def sync_all_entities(self) -> Dict[str, int]:
        """Sync all entity types from core-service."""
        results = {}
        
        items_count = await self.sync_items()
        results["items"] = items_count
        
        customers_count = await self.sync_customers()
        results["customers"] = customers_count
        
        suppliers_count = await self.sync_suppliers()
        results["suppliers"] = suppliers_count
        
        warehouses_count = await self.sync_warehouses()
        results["warehouses"] = warehouses_count
        
        logger.info(f"Sync completed: {results}")
        return results
    
    async def sync_items(self) -> int:
        """Sync items from core-service."""
        logger.info("Starting items sync...")
        try:
            items = await self._fetch_from_core_service("/api/v1/items")
            if not items:
                logger.warning("No items found")
                return 0
            
            await self.db.execute(delete(SearchDocument).where(SearchDocument.entity_type == "items"))
            
            count = 0
            for item in items:
                search_doc = self._create_item_search_document(item)
                self.db.add(search_doc)
                count += 1
            
            await self.db.commit()
            logger.info(f"Synced {count} items")
            return count
        except Exception as e:
            logger.error(f"Error syncing items: {e}", exc_info=True)
            await self.db.rollback()
            return 0
    
    async def sync_customers(self) -> int:
        """Sync customers from core-service."""
        logger.info("Starting customers sync...")
        try:
            customers = await self._fetch_from_core_service("/api/v1/customers")
            if not customers:
                logger.warning("No customers found")
                return 0
            
            await self.db.execute(delete(SearchDocument).where(SearchDocument.entity_type == "customers"))
            
            count = 0
            for customer in customers:
                search_doc = self._create_customer_search_document(customer)
                self.db.add(search_doc)
                count += 1
            
            await self.db.commit()
            logger.info(f"Synced {count} customers")
            return count
        except Exception as e:
            logger.error(f"Error syncing customers: {e}", exc_info=True)
            await self.db.rollback()
            return 0
    
    async def sync_suppliers(self) -> int:
        """Sync suppliers from core-service."""
        logger.info("Starting suppliers sync...")
        try:
            suppliers = await self._fetch_from_core_service("/api/v1/suppliers")
            if not suppliers:
                logger.warning("No suppliers found")
                return 0
            
            await self.db.execute(delete(SearchDocument).where(SearchDocument.entity_type == "suppliers"))
            
            count = 0
            for supplier in suppliers:
                search_doc = self._create_supplier_search_document(supplier)
                self.db.add(search_doc)
                count += 1
            
            await self.db.commit()
            logger.info(f"Synced {count} suppliers")
            return count
        except Exception as e:
            logger.error(f"Error syncing suppliers: {e}", exc_info=True)
            await self.db.rollback()
            return 0
    
    async def sync_warehouses(self) -> int:
        """Sync warehouses from core-service."""
        logger.info("Starting warehouses sync...")
        try:
            warehouses = await self._fetch_from_core_service("/api/v1/warehouses")
            if not warehouses:
                logger.warning("No warehouses found")
                return 0
            
            await self.db.execute(delete(SearchDocument).where(SearchDocument.entity_type == "warehouses"))
            
            count = 0
            for warehouse in warehouses:
                search_doc = self._create_warehouse_search_document(warehouse)
                self.db.add(search_doc)
                count += 1
            
            await self.db.commit()
            logger.info(f"Synced {count} warehouses")
            return count
        except Exception as e:
            logger.error(f"Error syncing warehouses: {e}", exc_info=True)
            await self.db.rollback()
            return 0
    
    async def _fetch_from_core_service(self, endpoint: str) -> List[Dict[str, Any]]:
        """Fetch data from core-service API."""
        url = f"{self.core_service_url}{endpoint}"
        headers = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict) and "items" in data:
                        return data["items"]
                    elif isinstance(data, dict) and "data" in data:
                        return data["data"]
                    else:
                        return []
                else:
                    logger.error(f"Failed to fetch from {url}: {response.status_code}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching from {url}: {e}", exc_info=True)
            return []
    
    def _create_item_search_document(self, item: Dict[str, Any]) -> SearchDocument:
        """Create search document from item data."""
        item_id = str(item.get("id", ""))
        item_code = item.get("item_code", "")
        item_name = item.get("item_name", "")
        description = item.get("description", "")
        item_group = item.get("item_group", "")
        
        title = f"{item_code} - {item_name}" if item_code else item_name
        content = " ".join(filter(None, [item_code, item_name, description, item_group]))
        
        metadata = {
            "item_code": item_code,
            "item_name": item_name,
            "item_group": item_group,
            "uom": item.get("default_uom", ""),
            "is_stock_item": item.get("is_stock_item", False),
            "is_sales_item": item.get("is_sales_item", False),
            "is_purchase_item": item.get("is_purchase_item", False),
        }
        
        return SearchDocument(
            entity_id=item_id,
            entity_type="items",
            title=title,
            content=content,
            metadata_=metadata
        )
    
    def _create_customer_search_document(self, customer: Dict[str, Any]) -> SearchDocument:
        """Create search document from customer data."""
        customer_id = str(customer.get("id", ""))
        customer_name = customer.get("customer_name", "")
        customer_code = customer.get("customer_code", "")
        email = customer.get("email", "")
        phone = customer.get("phone", "")
        
        title = f"{customer_code} - {customer_name}" if customer_code else customer_name
        content = " ".join(filter(None, [customer_code, customer_name, email, phone]))
        
        metadata = {
            "customer_code": customer_code,
            "customer_name": customer_name,
            "email": email,
            "phone": phone,
            "customer_type": customer.get("customer_type", ""),
        }
        
        return SearchDocument(
            entity_id=customer_id,
            entity_type="customers",
            title=title,
            content=content,
            metadata_=metadata
        )
    
    def _create_supplier_search_document(self, supplier: Dict[str, Any]) -> SearchDocument:
        """Create search document from supplier data."""
        supplier_id = str(supplier.get("id", ""))
        supplier_name = supplier.get("supplier_name", "")
        supplier_code = supplier.get("supplier_code", "")
        email = supplier.get("email", "")
        phone = supplier.get("phone", "")
        
        title = f"{supplier_code} - {supplier_name}" if supplier_code else supplier_name
        content = " ".join(filter(None, [supplier_code, supplier_name, email, phone]))
        
        metadata = {
            "supplier_code": supplier_code,
            "supplier_name": supplier_name,
            "email": email,
            "phone": phone,
            "supplier_type": supplier.get("supplier_type", ""),
        }
        
        return SearchDocument(
            entity_id=supplier_id,
            entity_type="suppliers",
            title=title,
            content=content,
            metadata_=metadata
        )
    
    def _create_warehouse_search_document(self, warehouse: Dict[str, Any]) -> SearchDocument:
        """Create search document from warehouse data."""
        warehouse_id = str(warehouse.get("id", ""))
        warehouse_name = warehouse.get("warehouse_name", "")
        warehouse_code = warehouse.get("warehouse_code", "")
        
        title = f"{warehouse_code} - {warehouse_name}" if warehouse_code else warehouse_name
        content = " ".join(filter(None, [warehouse_code, warehouse_name]))
        
        metadata = {
            "warehouse_code": warehouse_code,
            "warehouse_name": warehouse_name,
            "is_active": warehouse.get("is_active", True),
        }
        
        return SearchDocument(
            entity_id=warehouse_id,
            entity_type="warehouses",
            title=title,
            content=content,
            metadata_=metadata
        )


async def main():
    """Main sync function"""
    logger.info("Starting data synchronization...")
    logger.info(f"Core Service URL: {settings.core_service_url}")
    logger.info(f"Database URL: {settings.database_url}")
    
    # Fix database URL for async driver
    db_url = settings.database_url
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    
    engine = create_async_engine(db_url, echo=False, pool_pre_ping=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    try:
        async with async_session() as session:
            # Use token from environment or command line argument
            auth_token = sys.argv[1] if len(sys.argv) > 1 else None
            sync_service = SyncService(session, auth_token=auth_token)
            
            logger.info("Syncing all entities...")
            results = await sync_service.sync_all_entities()
            
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
