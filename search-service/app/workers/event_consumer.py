"""Event consumer for real-time search index updates"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

import redis.asyncio as aioredis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import AsyncSessionLocal
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)


class SearchIndexEventConsumer:
    """
    Consumes entity change events from Redis Streams and updates search index in real-time.
    
    This worker listens to the Redis Stream for entity create/update/delete events
    and immediately updates the search documents table.
    """
    
    def __init__(self):
        """Initialize the event consumer"""
        self.redis_url = settings.redis_url
        self.stream_name = getattr(settings, 'redis_stream_name', 'search:events')
        self.consumer_group = 'search-service'
        self.consumer_name = 'search-worker-1'
        self.redis: Optional[aioredis.Redis] = None
        self.running = False
        self.last_id = '0'  # Start from beginning
        
    async def connect(self):
        """Establish Redis connection"""
        try:
            self.redis = await aioredis.from_url(
                self.redis_url,
                encoding='utf-8',
                decode_responses=True
            )
            logger.info(f"Connected to Redis at {self.redis_url}")
            
            # Create consumer group if it doesn't exist
            try:
                await self.redis.xgroup_create(
                    name=self.stream_name,
                    groupname=self.consumer_group,
                    id='0',
                    mkstream=True
                )
                logger.info(f"Created consumer group '{self.consumer_group}' for stream '{self.stream_name}'")
            except Exception as e:
                # Group might already exist, which is fine
                if 'BUSYGROUP' not in str(e):
                    logger.warning(f"Consumer group creation warning: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def disconnect(self):
        """Close Redis connection"""
        if self.redis:
            await self.redis.close()
            logger.info("Disconnected from Redis")
    
    async def process_event(self, event_id: str, event_data: Dict[str, str]):
        """
        Process a single event and update search index.
        
        Args:
            event_id: Redis stream message ID
            event_data: Event data from Redis
        """
        try:
            # Extract event fields
            event_type = event_data.get('event_type', '')
            entity_type = event_data.get('entity_type', '')
            entity_id = event_data.get('entity_id', '')
            data_json = event_data.get('data', '{}')
            
            # Parse entity data
            entity_data = json.loads(data_json) if data_json else {}
            
            logger.info(f"Processing {event_type} for {entity_type}:{entity_id}")
            
            # Get database session
            async with AsyncSessionLocal() as db:
                sync_service = SyncService(db)
                
                if event_type == 'entity.created' or event_type == 'entity.updated':
                    # Upsert search document
                    await sync_service.upsert_search_document(entity_type, entity_data)
                    logger.info(f"Upserted search document for {entity_type}:{entity_id}")
                    
                elif event_type == 'entity.deleted':
                    # Delete search document
                    await sync_service.delete_search_document(entity_type, entity_id)
                    logger.info(f"Deleted search document for {entity_type}:{entity_id}")
                    
                else:
                    logger.warning(f"Unknown event type: {event_type}")
            
            # Acknowledge the message
            if self.redis:
                await self.redis.xack(self.stream_name, self.consumer_group, event_id)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event data JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to process event {event_id}: {e}", exc_info=True)
            # Don't acknowledge - will be retried
    
    async def consume_events(self):
        """
        Main event consumption loop using consumer groups.
        
        Continuously reads events from Redis Stream and processes them.
        """
        logger.info(f"Starting event consumer for stream '{self.stream_name}'")
        self.running = True
        
        while self.running:
            try:
                if not self.redis:
                    await self.connect()
                
                # Read from consumer group (pending and new messages)
                messages = await self.redis.xreadgroup(
                    groupname=self.consumer_group,
                    consumername=self.consumer_name,
                    streams={self.stream_name: '>'},
                    count=10,
                    block=5000  # Block for 5 seconds
                )
                
                if messages:
                    for stream_name, stream_messages in messages:
                        for message_id, message_data in stream_messages:
                            await self.process_event(message_id, message_data)
                
            except asyncio.CancelledError:
                logger.info("Event consumer cancelled")
                break
            except RedisError as e:
                logger.error(f"Redis error in consumer loop: {e}")
                await asyncio.sleep(5)  # Wait before reconnecting
                try:
                    await self.disconnect()
                    await self.connect()
                except Exception as reconnect_error:
                    logger.error(f"Failed to reconnect: {reconnect_error}")
            except Exception as e:
                logger.error(f"Unexpected error in consumer loop: {e}", exc_info=True)
                await asyncio.sleep(1)  # Brief pause before continuing
    
    async def start(self):
        """Start the event consumer"""
        try:
            await self.connect()
            await self.consume_events()
        except Exception as e:
            logger.error(f"Failed to start event consumer: {e}", exc_info=True)
        finally:
            await self.disconnect()
    
    async def stop(self):
        """Stop the event consumer"""
        logger.info("Stopping event consumer...")
        self.running = False
        await self.disconnect()
