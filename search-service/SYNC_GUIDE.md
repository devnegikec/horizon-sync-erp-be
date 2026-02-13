# Search Service Data Synchronization Guide

## Overview

The search service maintains its own `search_documents` table that needs to be synchronized with data from the core-service. This guide explains how to sync data and keep the search index up-to-date.

## Why Synchronization is Needed

The search service stores denormalized copies of entities (items, customers, suppliers, warehouses) in the `search_documents` table for fast full-text search. When you create or update entities in the core-service, they need to be synced to the search index.

## Synchronization Methods

### Method 1: API Endpoints (Recommended)

Use the sync API endpoints to trigger synchronization:

#### Sync All Entities

```bash
curl -X POST http://localhost:8002/api/v1/sync/all \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

Response:
```json
{
  "status": "success",
  "message": "Sync completed successfully",
  "results": {
    "items": 150,
    "customers": 45,
    "suppliers": 30,
    "warehouses": 5
  },
  "total_synced": 230
}
```

#### Sync Specific Entity Types

```bash
# Sync only items
curl -X POST http://localhost:8002/api/v1/sync/items \
  -H 'Authorization: Bearer YOUR_TOKEN'

# Sync only customers
curl -X POST http://localhost:8002/api/v1/sync/customers \
  -H 'Authorization: Bearer YOUR_TOKEN'

# Sync only suppliers
curl -X POST http://localhost:8002/api/v1/sync/suppliers \
  -H 'Authorization: Bearer YOUR_TOKEN'

# Sync only warehouses
curl -X POST http://localhost:8002/api/v1/sync/warehouses \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### Method 2: CLI Script

Run the sync script directly:

```bash
# From the search-service directory
cd search-service
python sync_data.py
```

Or using Docker:

```bash
docker exec horizon_search python sync_data.py
```

### Method 3: Docker Exec

```bash
docker exec horizon_search python -c "
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.config import settings
from app.services.sync_service import SyncService

async def sync():
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        sync_service = SyncService(session)
        results = await sync_service.sync_all_entities()
        print(f'Synced: {results}')
    await engine.dispose()

asyncio.run(sync())
"
```

## Required Permissions

To use the sync API endpoints, you need the `search.sync` permission.

### Create the Permission

```bash
curl -X POST http://localhost:8000/api/v1/identity/permissions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ADMIN_TOKEN' \
  -d '{
    "code": "search.sync",
    "name": "Search Sync",
    "description": "Synchronize data from core-service to search index",
    "resource": "search",
    "action": "sync"
  }'
```

### Assign to Your Role

```bash
curl -X POST http://localhost:8000/api/v1/identity/roles/{ROLE_ID}/permissions \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer ADMIN_TOKEN' \
  -d '{
    "permission_codes": ["search.sync", "search.global", "search.local"]
  }'
```

## When to Sync

### Initial Setup

After deploying the search service for the first time, run a full sync:

```bash
curl -X POST http://localhost:8002/api/v1/sync/all \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### After Bulk Data Import

If you import a large number of records into the core-service, sync them:

```bash
# If you imported items
curl -X POST http://localhost:8002/api/v1/sync/items \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### Scheduled Sync (Recommended)

Set up a cron job or scheduled task to sync periodically:

```bash
# Example cron job (every hour)
0 * * * * curl -X POST http://localhost:8002/api/v1/sync/all -H 'Authorization: Bearer YOUR_TOKEN'
```

### Manual Sync

Trigger manually when you notice search results are out of date.

## How Synchronization Works

1. **Fetch Data**: The sync service calls the core-service API to fetch all entities
2. **Clear Old Data**: Existing search documents for that entity type are deleted
3. **Transform**: Entity data is transformed into search documents with:
   - `entity_id`: Original entity ID
   - `entity_type`: Type (items, customers, etc.)
   - `title`: Searchable title
   - `content`: Full-text searchable content
   - `metadata`: Additional fields for filtering
4. **Insert**: New search documents are inserted into the database
5. **Index**: PostgreSQL automatically updates the full-text search index

## Troubleshooting

### Sync Returns 0 Records

**Problem**: Sync completes but shows 0 records synced

**Possible Causes**:
1. Core-service is not running
2. Core-service has no data
3. API endpoint path is incorrect
4. Network connectivity issues

**Solution**:
```bash
# Check if core-service is accessible
curl http://localhost:8001/health

# Check if items exist
curl http://localhost:8001/api/v1/items \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

### Permission Denied (403)

**Problem**: Sync endpoint returns 403 Forbidden

**Solution**: Ensure your user has the `search.sync` permission (see "Required Permissions" above)

### Sync Fails with 500 Error

**Problem**: Sync endpoint returns 500 Internal Server Error

**Possible Causes**:
1. Database connection issues
2. Core-service API errors
3. Data transformation errors

**Solution**:
```bash
# Check search-service logs
docker logs horizon_search --tail 100

# Check database connectivity
docker exec horizon_search python -c "
from app.database import async_engine
import asyncio
async def test():
    async with async_engine.connect() as conn:
        result = await conn.execute('SELECT 1')
        print('Database OK')
asyncio.run(test())
"
```

### Search Still Returns No Results

**Problem**: After sync, search still returns no results

**Possible Causes**:
1. Sync didn't actually complete
2. Search query doesn't match any data
3. Full-text search index not updated

**Solution**:
```bash
# Verify data was synced
docker exec -it horizon_postgres psql -U horizon_user -d search_db -c "SELECT entity_type, COUNT(*) FROM search_documents GROUP BY entity_type;"

# Check if search_vector is populated
docker exec -it horizon_postgres psql -U horizon_user -d search_db -c "SELECT entity_type, title, search_vector FROM search_documents LIMIT 5;"

# Try a simple search
curl -X POST http://localhost:8002/api/v1/search/global \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer YOUR_TOKEN' \
  -d '{"query": "test", "page": 1, "page_size": 20}'
```

## Monitoring Sync Status

### Check Sync Status

```bash
# Count records in search index
docker exec -it horizon_postgres psql -U horizon_user -d search_db -c "
SELECT 
  entity_type,
  COUNT(*) as count,
  MAX(updated_at) as last_updated
FROM search_documents 
GROUP BY entity_type;
"
```

### View Recent Syncs

Check the search-service logs:

```bash
docker logs horizon_search | grep "Sync"
```

## Best Practices

1. **Initial Sync**: Always run a full sync after deployment
2. **Regular Syncs**: Schedule periodic syncs (hourly or daily)
3. **Incremental Updates**: For real-time updates, implement webhooks or event-driven sync
4. **Monitor**: Set up alerts for sync failures
5. **Backup**: Backup the search_documents table before major syncs

## Future Enhancements

- **Real-time Sync**: Implement webhooks or message queue for instant updates
- **Incremental Sync**: Only sync changed records instead of full refresh
- **Conflict Resolution**: Handle concurrent updates gracefully
- **Sync History**: Track sync operations and their results
- **Automatic Retry**: Retry failed syncs automatically

## API Documentation

For complete API documentation, visit:
- Swagger UI: http://localhost:8002/docs
- ReDoc: http://localhost:8002/redoc

Look for the "Sync" tag to see all sync endpoints.
