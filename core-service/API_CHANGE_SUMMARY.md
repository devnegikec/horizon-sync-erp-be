# API Change Summary - Tax Template List Endpoint

## Date: 2026-02-15

## Change Description

The Tax Template List endpoint response structure was updated to align with the Pydantic schema definition.

### Endpoint
`GET /api/v1/tax-templates`

### Change Details

**Before:**
```json
{
  "data": [...],
  "pagination": {...}
}
```

**After:**
```json
{
  "templates": [...],
  "pagination": {...}
}
```

### Reason for Change
The response field was changed from `data` to `templates` to match the `TaxTemplateListResponse` Pydantic schema defined in `core-service/app/schemas/tax_template.py`:

```python
class TaxTemplateListResponse(BaseModel):
    """Schema for paginated tax template list response"""

    templates: list[TaxTemplateListItem]
    pagination: PaginationMeta
```

This ensures consistency between the API response and the schema definition, improving type safety and API documentation accuracy.

## Files Updated

### 1. API Endpoint
**File:** `core-service/app/api/v1/endpoints/tax_templates.py`

**Change:**
```python
# Line 88
return {
    "templates": templates,  # Changed from "data"
    "pagination": pagination
}
```

### 2. Postman Collection
**File:** `core-service/Tax_Template_API.postman_collection.json`

**Change:** Updated test assertion in "4. List Tax Templates" request:
```javascript
// Before
pm.expect(response).to.have.property('data');
pm.expect(response.data).to.be.an('array');

// After
pm.expect(response).to.have.property('templates');
pm.expect(response.templates).to.be.an('array');
```

## Impact Assessment

### Breaking Change: YES
This is a breaking change for any clients consuming the list endpoint.

### Affected Endpoints
- `GET /api/v1/tax-templates` - List all tax templates
- `GET /api/v1/tax-templates?tax_category=Output&is_active=true` - List with filters

### Migration Guide for API Consumers

If you're consuming this API, update your code to use `templates` instead of `data`:

**JavaScript/TypeScript:**
```typescript
// Before
const templates = response.data;

// After
const templates = response.templates;
```

**Python:**
```python
# Before
templates = response_json['data']

# After
templates = response_json['templates']
```

## Testing Status

✅ Postman collection updated and tests passing
✅ Response schema matches Pydantic definition
✅ Documentation updated

## Related Files
- Schema definition: `core-service/app/schemas/tax_template.py`
- Service layer: `core-service/app/services/tax_template_service.py`
- Repository layer: `core-service/app/repositories/tax_template_repository.py`
- API documentation: `core-service/TAX_TEMPLATE_API_TESTING.md`

## Recommendations

1. **Frontend teams**: Update API client code to use `templates` field
2. **API documentation**: Ensure OpenAPI/Swagger docs reflect this change
3. **Version consideration**: Consider API versioning if this breaks existing integrations
4. **Communication**: Notify all API consumers of this breaking change

## Next Steps

- [ ] Update OpenAPI/Swagger documentation
- [ ] Notify frontend team of breaking change
- [ ] Update any integration tests
- [ ] Consider adding API versioning for future changes
