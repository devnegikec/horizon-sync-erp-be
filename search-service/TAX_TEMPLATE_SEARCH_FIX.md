# Tax Template Search Integration Fix

## Problem
Getting 500 Internal Server Error when calling `/api/v1/search/global` with the PostgreSQL error:
```
ERROR: current transaction is aborted, commands ignored until end of transaction block
```

## Root Cause
The search service's `sync_service.py` wasn't properly handling tax_templates entity type:
1. It was trying to extract `entity_id` using fields like `item_code` or `code` which don't exist on tax templates
2. It was trying to extract `title` using fields like `item_name` or `name` instead of `template_name`
3. Tax templates weren't in the list of supported entity types in the search engine

## Changes Made

### 1. Updated `search-service/app/services/sync_service.py`
Added specific handling for `tax_templates` and `charge_templates` in the `upsert_search_document` method:
- Extracts `entity_id` from the `id` field
- Extracts `title` from `template_name` or `template_code`
- Extracts `content` from `description`
- Properly excludes template-specific fields from metadata

### 2. Updated `search-service/app/search_engine.py`
Added `tax_templates` and `charge_templates` to the `ENTITY_TYPES` list so they can be searched.

## How to Fix the Current Error

The transaction error means PostgreSQL is in a failed state. You need to:

### Option 1: Restart the Search Service (Recommended)
```bash
# Stop the search service
docker-compose stop search-service

# Start it again
docker-compose start search-service

# Or restart both services
docker-compose restart search-service core-service
```

### Option 2: Clear the Redis Stream (if events are stuck)
```bash
# Connect to Redis
docker exec -it horizon_redis redis-cli

# Delete the stream to clear any problematic events
DEL search:events

# Exit Redis
exit
```

### Option 3: Restart PostgreSQL (if transaction is stuck)
```bash
# Restart the database
docker-compose restart postgres
```

## Testing the Fix

After restarting the services:

### 1. Create a Tax Template
```bash
POST http://localhost:8001/api/v1/tax-templates
{
  "template_code": "GST_18",
  "template_name": "GST 18%",
  "description": "18% GST split into CGST and SGST",
  "tax_category": "Output",
  "is_default": false,
  "is_active": true,
  "tax_rules": [...]
}
```

### 2. Wait 100-200ms for Event Processing
The event should be published to Redis and consumed by the search service.

### 3. Search for the Tax Template
```bash
POST http://localhost:8002/api/v1/search/global
{
  "query": "GST",
  "entity_types": ["tax_templates"],
  "page": 1,
  "page_size": 20
}
```

You should see the tax template in the search results!

### 4. Verify in Redis (Optional)
```bash
# Connect to Redis
docker exec -it horizon_redis redis-cli

# Check the stream
XREAD COUNT 10 STREAMS search:events 0

# You should see events like:
# entity_type: "tax_templates"
# event_type: "entity.created"
```

## Expected Behavior

After the fix:
- ✅ Tax templates are published to Redis when created/updated/deleted
- ✅ Search service consumes the events and indexes tax templates
- ✅ Tax templates appear in global search results
- ✅ Tax templates can be searched by template_name, template_code, or description
- ✅ No more transaction errors

## Supported Entity Types in Search

The search service now supports:
- `items`
- `customers`
- `suppliers`
- `warehouses`
- `stock_entries`
- `tax_templates` ✨ NEW
- `charge_templates` ✨ NEW

## Next Steps

1. Restart the services to clear the transaction error
2. Test creating a tax template and searching for it
3. If you still see errors, check the search service logs:
   ```bash
   docker-compose logs -f search-service
   ```
4. Implement the same event publishing for charge templates (following the same pattern)
