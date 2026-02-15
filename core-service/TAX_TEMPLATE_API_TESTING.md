# Tax Template API Testing Guide

## Overview

A comprehensive Postman collection has been created for testing the Tax Template API endpoints. The collection includes 10 test requests covering all CRUD operations and special features like setting default templates and getting applicable templates.

## Postman Collection

**File**: `core-service/Tax_Template_API.postman_collection.json`

### Collection Contents

1. **Create Tax Template - GST 18%**: Creates a standard GST template with CGST and SGST rules
2. **Create Tax Template - GST 12%**: Creates a reduced GST rate template
3. **Create Tax Template - GST with Compound CESS**: Demonstrates compound tax calculation
4. **List Tax Templates**: Lists all templates with pagination
5. **List Tax Templates - Filter by Output**: Filtered listing example
6. **Get Tax Template by ID**: Retrieves a specific template
7. **Update Tax Template**: Updates template fields
8. **Set Template as Default**: Marks a template as organization default
9. **Get Applicable Tax Template**: Gets the applicable template based on context
10. **Delete Tax Template**: Soft deletes a template

### Environment Variables Required

The collection requires the following environment variables:

- `base_url`: Base URL for the core service (default: `http://localhost:8001`)
- `access_token`: JWT authentication token from identity service
- `organization_id`: Organization UUID
- `account_head_cgst`: Account head UUID for CGST
- `account_head_sgst`: Account head UUID for SGST
- `account_head_cess`: Account head UUID for CESS
- `item_id`: Item UUID for testing applicable template endpoint

### Auto-Generated Variables

The collection automatically sets these variables during execution:

- `tax_template_id_gst18`: ID of the GST 18% template
- `tax_template_id_gst12`: ID of the GST 12% template
- `tax_template_id_cess`: ID of the template with CESS

## API Endpoint Fixes Applied

### 1. Fixed `list_tax_templates` Endpoint

**Issue**: The endpoint was calling `service.list_templates()` with incorrect parameters.

**Fix**: Updated to pass `page` and `limit` inside the `filters` dictionary as `page` and `page_size`.

```python
filters = {
    "page": page,
    "page_size": limit,
}
# ... add other filters
templates, pagination = service.list_templates(
    current_user.organization_id,
    filters
)
```

### 2. Fixed `set_as_default` Endpoint

**Issue**: The endpoint was treating the service method return value as a boolean, but it returns a dict.

**Fix**: Removed the success check and directly return the updated template from the service.

```python
updated_template = service.set_as_default(
    template_id,
    current_user.organization_id,
    template["tax_category"]
)
return updated_template
```

### 3. Fixed `delete_tax_template` Endpoint

**Issue**: The endpoint was checking for a boolean return value, but the service method returns `None` and raises exceptions on errors.

**Fix**: Removed the success check since exceptions will be raised if there are issues.

```python
service.delete_template(template_id, current_user.organization_id)
return None
```

## Testing Instructions

### Prerequisites

1. Start the core service: `cd core-service && uvicorn app.main:app --reload --port 8001`
2. Start the identity service: `cd identity-service && uvicorn app.main:app --reload --port 8000`
3. Obtain a JWT token from the identity service
4. Set up environment variables in Postman

### Running the Collection

1. Import `Tax_Template_API.postman_collection.json` into Postman
2. Create or select the "Local Development" environment
3. Set the required environment variables
4. Run the collection in order (requests are numbered 1-10)

### Expected Results

All requests should return successful responses:

- **Create requests**: 201 Created with template details
- **List requests**: 200 OK with array of templates and pagination
- **Get requests**: 200 OK with template details
- **Update requests**: 200 OK with updated template
- **Delete requests**: 204 No Content

### Test Assertions

The collection includes automated test assertions:

- Status code validation
- Response structure validation
- Field presence checks
- Data type validation
- Business logic validation (e.g., is_default flag)

## API Endpoints Summary

| Method | Endpoint | Description | Permission Required |
|--------|----------|-------------|---------------------|
| POST | `/api/v1/tax-templates` | Create tax template | `tax_template.create` |
| GET | `/api/v1/tax-templates` | List tax templates | `tax_template.read` |
| GET | `/api/v1/tax-templates/{id}` | Get template by ID | `tax_template.read` |
| PUT | `/api/v1/tax-templates/{id}` | Update tax template | `tax_template.update` |
| DELETE | `/api/v1/tax-templates/{id}` | Delete tax template | `tax_template.delete` |
| POST | `/api/v1/tax-templates/{id}/set-default` | Set as default | `tax_template.update` |
| GET | `/api/v1/tax-templates/applicable` | Get applicable template | `tax_template.read` |

## Common Issues and Solutions

### 1. Authentication Errors (401)

**Issue**: Missing or invalid JWT token

**Solution**: Ensure `access_token` environment variable is set with a valid JWT token from the identity service.

### 2. Permission Errors (403)

**Issue**: User lacks required permissions

**Solution**: Ensure the authenticated user has the appropriate permissions (tax_template.create, tax_template.read, etc.)

### 3. Validation Errors (422)

**Issue**: Invalid request body or missing required fields

**Solution**: Check the request body matches the schema. Required fields:
- `organization_id`
- `template_name`
- `tax_category` (must be "Input" or "Output")
- `is_active`

### 4. Template Not Found (404)

**Issue**: Template ID doesn't exist or belongs to different organization

**Solution**: Verify the template ID and ensure it belongs to the authenticated user's organization.

### 5. Template In Use (409)

**Issue**: Attempting to delete a template that is referenced by items or transactions

**Solution**: Remove references before deleting, or keep the template and mark it as inactive.

## Next Steps

1. **Register the router**: Add the tax_templates router to `core-service/app/api/v1/api.py`
2. **Run migrations**: Apply database migrations for tax template tables
3. **Seed test data**: Create sample account heads and items for testing
4. **Integration testing**: Test with actual quotations and sales orders
5. **Performance testing**: Test with large datasets and concurrent requests

## Related Documentation

- Requirements: `.kiro/specs/tax-and-charges-api/requirements.md`
- Design: `.kiro/specs/tax-and-charges-api/design.md`
- Tasks: `.kiro/specs/tax-and-charges-api/tasks.md`
- Steering: `.kiro/steering/tax-and-charges-api-context.md`
