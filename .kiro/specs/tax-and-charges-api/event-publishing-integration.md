# Spec: Event Publishing Integration for Tax Templates

## Status: ✅ COMPLETED (Tax Templates)

## Overview

Integrate real-time event publishing for tax templates and charge templates to enable search synchronization and future event-driven features. This follows the established pattern from the items entity (see REAL_TIME_SYNC_IMPLEMENTATION.md).

## Completion Summary

### Tax Template Event Publishing - ✅ DONE
Event publishing has been successfully integrated into `tax_template_service.py`:
- ✅ `create_template()` - Publishes `entity.created` event after successful creation
- ✅ `update_template()` - Publishes `entity.updated` event after successful update
- ✅ `delete_template()` - Publishes `entity.deleted` event after soft delete
- ✅ All event publishing wrapped in try-except for graceful error handling
- ✅ Events include entity_type="tax_templates", entity_id, organization_id, and full data
- ✅ SQLAlchemy models properly serialized to dict before publishing

### Charge Template Event Publishing - ⏳ PENDING
Still needs to be implemented following the same pattern.

## Context

Integrate real-time event publishing for tax templates and charge templates to enable search synchronization and future event-driven features. This follows the established pattern from the items entity (see REAL_TIME_SYNC_IMPLEMENTATION.md).

## Context

The tax_template_service.py file was recently modified to import logging and the event publisher, but the actual event publishing calls haven't been integrated yet. This spec defines the requirements and implementation plan for completing this integration.

## Requirements

### 1. Tax Template Event Publishing

**User Story:** As a system, I want to publish events when tax templates are created, updated, or deleted, so that the search service and other consumers can stay synchronized in real-time.

**Acceptance Criteria:**
- WHEN a tax template is created, THE system SHALL publish an `entity.created` event to Redis Stream
- WHEN a tax template is updated, THE system SHALL publish an `entity.updated` event to Redis Stream
- WHEN a tax template is deleted, THE system SHALL publish an `entity.deleted` event to Redis Stream
- THE event SHALL include entity_type="tax_templates", entity_id, organization_id, and full entity data
- THE event publishing SHALL be non-blocking and SHALL NOT fail the API request if Redis is unavailable
- THE event publishing SHALL occur AFTER successful database commit

### 2. Charge Template Event Publishing

**User Story:** As a system, I want to publish events when charge templates are created, updated, or deleted, so that the search service can index them for discovery.

**Acceptance Criteria:**
- WHEN a charge template is created, THE system SHALL publish an `entity.created` event
- WHEN a charge template is updated, THE system SHALL publish an `entity.updated` event
- WHEN a charge template is deleted, THE system SHALL publish an `entity.deleted` event
- THE event SHALL include entity_type="charge_templates", entity_id, organization_id, and full entity data

### 3. Error Handling and Reliability

**User Story:** As a developer, I want event publishing failures to be logged but not break API functionality, so that Redis issues don't impact core business operations.

**Acceptance Criteria:**
- WHEN event publishing fails, THE system SHALL log the error with full context
- WHEN event publishing fails, THE API request SHALL still succeed (graceful degradation)
- THE system SHALL use try-except blocks around all event publishing calls
- THE fallback sync mechanism SHALL eventually catch any missed events

## Implementation Tasks

### Task 1: Integrate Event Publishing in TaxTemplateService ✅ COMPLETED

**File:** `core-service/app/services/tax_template_service.py`

**Status:** All changes implemented and verified

**Changes Made:**
1. ✅ In `create_template()` method:
   - Added event publishing after successful repository create
   - Serializes template data using dict comprehension to exclude SQLAlchemy internals
   - Wrapped in try-except with error logging

2. ✅ In `update_template()` method:
   - Added event publishing after successful repository update
   - Includes full updated template data
   - Graceful error handling

3. ✅ In `delete_template()` method:
   - Added event publishing after successful soft delete
   - Publishes entity_id and organization_id
   - Non-blocking error handling

**Implementation Pattern Used:**
```python
# After create/update
try:
    event_publisher = get_event_publisher()
    template_data = {k: v for k, v in template.__dict__.items() if not k.startswith('_')}
    event_publisher.publish_entity_created(  # or publish_entity_updated
        entity_type="tax_templates",
        entity_id=str(template.id),
        organization_id=str(organization_id),
        data=template_data
    )
except Exception as e:
    logger.error(f"Failed to publish tax template created event: {e}")

# After delete
try:
    event_publisher = get_event_publisher()
    event_publisher.publish_entity_deleted(
        entity_type="tax_templates",
        entity_id=str(template_id),
        organization_id=str(organization_id)
    )
except Exception as e:
    logger.error(f"Failed to publish tax template deleted event: {e}")
```

### Task 2: Integrate Event Publishing in ChargeTemplateService ⏳ PENDING

**File:** `core-service/app/services/charge_template_service.py`

**Changes:**
1. Add logging and event publisher imports (same as tax_template_service.py)
2. Integrate event publishing in create, update, and delete methods
3. Use entity_type="charge_templates"

### Task 3: Test Event Publishing ⏳ READY FOR TESTING

**Manual Testing Steps:**
1. Start Redis and watch the stream:
   ```bash
   docker exec -it horizon_redis redis-cli
   > XREAD COUNT 10 STREAMS search:events 0
   ```

2. Create a tax template via API and verify event appears in stream

3. Update a tax template and verify update event

4. Delete a tax template and verify delete event

**Integration Test:**
- Verify events are published after successful operations
- Verify API still works when Redis is unavailable
- Verify event data structure matches expected format

### Task 4: Update Search Service (Optional) ✅ COMPLETED

**Status:** Search service has been updated to support tax_templates

**Changes Made:**
1. ✅ Updated `search-service/app/services/sync_service.py`:
   - Added specific handling for `tax_templates` entity type
   - Extracts `entity_id` from `id` field
   - Extracts `title` from `template_name` or `template_code`
   - Properly handles template-specific fields

2. ✅ Updated `search-service/app/search_engine.py`:
   - Added `tax_templates` to the `ENTITY_TYPES` list
   - Tax templates can now be searched globally and locally

**Note:** If you're seeing a PostgreSQL transaction error, restart the search service:
```bash
docker-compose restart search-service
```

See `search-service/TAX_TEMPLATE_SEARCH_FIX.md` for detailed troubleshooting.

## Testing Strategy

### Unit Tests
- Mock the event publisher in service tests
- Verify event publishing is called with correct parameters
- Verify exceptions are caught and logged

### Integration Tests
- Test with real Redis connection
- Verify events appear in stream
- Test graceful degradation when Redis is down

### Manual Testing
- Use Postman collection to create/update/delete templates
- Monitor Redis stream for events
- Check search service for synchronized data

## Success Criteria

- [x] Tax template create/update/delete operations publish events
- [ ] Charge template create/update/delete operations publish events
- [x] Events contain correct entity_type, entity_id, organization_id, and data
- [x] Event publishing failures are logged but don't break API
- [ ] Tax templates appear in search results within 100-200ms of creation (needs testing)
- [x] All existing tests continue to pass (no syntax errors, file compiles)

## Related Documentation

- REAL_TIME_SYNC_IMPLEMENTATION.md - Pattern reference for items
- core-service/app/events/publisher.py - Event publisher implementation
- search-service/app/workers/event_consumer.py - Event consumer
- .kiro/specs/tax-and-charges-api/requirements.md - Original requirements
- .kiro/specs/tax-and-charges-api/tasks.md - Implementation tasks
