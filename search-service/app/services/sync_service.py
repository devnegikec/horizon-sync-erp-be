"""Service to sync entities from core-service to search-service"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.database import SearchDocument

logger = logging.getLogger("sync_service")


class SyncService:
    """
    Service to sync entities from core-service to search-service search_documents table.
    """

    def __init__(self, db: AsyncSession, auth_token: Optional[str] = None):
        self.db = db
        # Use provided token, or fall back to SYNC_SERVICE_TOKEN from config
        self.auth_token = auth_token or settings.sync_service_token or None
        self.core_base_url = settings.core_service_url.rstrip("/")
        self.identity_base_url = settings.identity_service_url.rstrip("/")

    async def ensure_token(self):
        """Ensure self.auth_token is set, fetching from identity-service if needed."""
        if self.auth_token:
            return
        email = settings.sync_service_username
        password = settings.sync_service_password
        if not email or not password:
            logger.error("No sync service credentials provided for automated token retrieval.")
            return
        login_url = f"{self.identity_base_url}/api/v1/identity/login"
        payload = {"email": email, "password": password}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(login_url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                # Expecting {"access_token": "..."}
                self.auth_token = data.get("access_token")
                if not self.auth_token:
                    logger.error("No access_token in identity-service login response.")
        except Exception as e:
            logger.error(f"Failed to retrieve sync token from identity-service: {e}")

    async def fetch_entities(self, entity: str) -> List[Dict[str, Any]]:
        """Fetch all entities of a type from core-service."""
        await self.ensure_token()
        url = f"{self.core_base_url}/api/v1/{entity}"
        headers = {"Authorization": f"Bearer {self.auth_token}"} if self.auth_token else {}
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                logger.info(f"Fetching {entity} from {url}")
                resp = await client.get(url, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                # Try to extract list from common response keys
                if isinstance(data, dict):
                    for key in ("items", "data", "results"):
                        if key in data and isinstance(data[key], list):
                            return data[key]
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            logger.error(f"Error fetching {entity} from {url}: {type(e).__name__}: {e}")
            raise

    async def upsert_search_document(self, entity_type: str, entity: Dict[str, Any]):
        """Insert or update a SearchDocument for an entity."""
        # Extract entity_id based on entity type
        if entity_type == "tax_templates":
            entity_id = str(entity.get("id", ""))
            title = entity.get("template_name") or entity.get("template_code") or entity_id
            content = entity.get("description") or ""
        elif entity_type == "charge_templates":
            entity_id = str(entity.get("id", ""))
            title = entity.get("template_name") or entity.get("template_code") or entity_id
            content = entity.get("description") or ""
        else:
            # Default handling for other entity types
            entity_id = str(entity.get("id") or entity.get("item_code") or entity.get("code") or "")
            title = entity.get("item_name") or entity.get("name") or entity.get("title") or entity_id
            content = entity.get("description") or ""
        
        if not entity_id:
            logger.error(f"Cannot upsert search document: missing entity_id for {entity_type}")
            return
        
        # Build metadata excluding fields already used
        excluded_fields = {"id", "item_code", "item_name", "name", "title", "description", "template_name", "template_code"}
        metadata = {
            k: v
            for k, v in entity.items()
            if k not in excluded_fields
        }
        
        # Upsert logic
        stmt = select(SearchDocument).where(
            SearchDocument.entity_id == entity_id, SearchDocument.entity_type == entity_type
        )
        result = await self.db.execute(stmt)
        doc = result.scalar_one_or_none()
        if doc:
            doc.title = title
            doc.content = content
            doc.metadata_ = metadata
        else:
            doc = SearchDocument(
                entity_id=entity_id,
                entity_type=entity_type,
                title=title,
                content=content,
                metadata_=metadata,
            )
            self.db.add(doc)
        await self.db.commit()

    async def delete_search_document(self, entity_type: str, entity_id: str):
        """
        Delete a SearchDocument for an entity.
        
        Args:
            entity_type: Type of entity (items, customers, etc.)
            entity_id: Entity unique identifier
        """
        try:
            stmt = delete(SearchDocument).where(
                SearchDocument.entity_id == entity_id,
                SearchDocument.entity_type == entity_type
            )
            await self.db.execute(stmt)
            await self.db.commit()
            logger.info(f"Deleted search document for {entity_type}:{entity_id}")
        except Exception as e:
            logger.error(f"Failed to delete search document for {entity_type}:{entity_id}: {e}")
            await self.db.rollback()
            raise

    async def sync_all_entities(self) -> Dict[str, int]:
        """Sync all supported entity types from core-service."""
        entity_types = ["items", "customers", "suppliers", "warehouses"]
        results = {}
        for entity_type in entity_types:
            try:
                entities = await self.fetch_entities(entity_type)
                count = 0
                for entity in entities:
                    await self.upsert_search_document(entity_type, entity)
                    count += 1
                results[entity_type] = count
            except Exception as e:
                logger.error(f"Failed to sync {entity_type}: {e}")
                results[entity_type] = 0
        return results


# Background auto-sync task (module-level, not in class)
_auto_sync_task = None


def start_auto_sync(app, db_factory, interval_seconds: int = 3600):
    """
    Start background task for periodic auto-sync.
    
    Note: With event-driven sync, this is now a fallback mechanism
    that runs less frequently (default: every hour).
    """
    global _auto_sync_task
    if _auto_sync_task:
        return  # Already running

    async def auto_sync_loop():
        # Wait 30 seconds on startup to let core-service fully initialize
        await asyncio.sleep(30)
        
        while True:
            try:
                async with db_factory() as db:
                    service = SyncService(db)
                    await service.sync_all_entities()
                    logger.info("Periodic fallback sync completed.")
            except Exception as e:
                logger.error(f"Periodic fallback sync failed: {e}")
            await asyncio.sleep(interval_seconds)

    loop = asyncio.get_event_loop()
    _auto_sync_task = loop.create_task(auto_sync_loop())
