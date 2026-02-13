# Postman Collection - Bulk Import/Export Operations

## Overview
This Postman collection provides comprehensive testing for the bulk item import and export features in the Horizon Sync core-service.

## Files
- `Horizon_Sync_Bulk_Import_Export.postman_collection.json` - The complete Postman collection

## Features

### Bulk Import Operations
1. **Upload CSV File for Import** - Upload a file (CSV, XLSX, JSON) for bulk item import
2. **Get Import Job Status** - Check the current status and statistics of an import job
3. **Get Import Job Errors** - View detailed error information for failed rows
4. **List All Import Jobs** - Paginated list of import jobs for your organization
5. **Download CSV Import Template** - Get a template with sample data
6. **Download XLSX Import Template** - Get a template in Excel format

### Bulk Export Operations
1. **Create Export Job with Filters** - Create an export with item_type and status filters
2. **Create Export Job (XLSX Format)** - Export all items in XLSX format
3. **Create Export Job (JSON Format)** - Export items with search filter as JSON
4. **Get Export Job Status** - Check status of an export job
5. **Download Exported File** - Download the generated export file
6. **List All Export Jobs** - Paginated list of export jobs
7. **Quick Export (CSV)** - Direct export without job tracking
8. **Quick Export (XLSX with Search)** - Quick export with search filter

## Setup Instructions

### 1. Import Collection into Postman

**Option A: Direct Import**
1. Open Postman
2. Click **File** → **Import**
3. Select **Upload Files**
4. Choose `Horizon_Sync_Bulk_Import_Export.postman_collection.json`
5. Click **Import**

**Option B: Using Link**
1. In Postman, click the **Import** button
2. Paste the file path or content
3. Click **Import**

### 2. Set Environment Variables

After importing, you need to set the following variables in Postman:

1. **Create/Use Environment:**
   - Click **Environments** (gear icon) on the left
   - Click **Create New**
   - Name it "Horizon Sync Dev"

2. **Add Variables:**
   ```
   base_url: http://localhost:8001/api/v1
   access_token: YOUR_JWT_TOKEN_HERE
   organization_id: 550e8400-e29b-41d4-a716-446655440000
   import_job_id: (auto-filled after upload)
   export_job_id: (auto-filled after export)
   ```

3. **Get Access Token:**
   - Use your identity service to obtain a JWT token
   - Replace `access_token` with the token in the environment
   - The token should include organization_id claim

4. **Set Organization ID:**
   - Replace with your actual organization UUID

### 3. Alternative: Quick Setup (Collection Variables)

If you don't want to create an environment, you can set variables directly in the collection:

1. Right-click collection → **Edit**
2. Go to **Variables** tab
3. Update:
   - `access_token`
   - `organization_id`

## Testing Workflow

### For Import Operations

#### Step 1: Prepare Sample Data
Create a CSV file with the following content:

```csv
item_code,item_name,description,item_group_id,item_type,status,uom,standard_rate
ITEM001,Laptop Computer,Dell XPS 13 Laptop,,Stock,Active,Nos,1299.99
ITEM002,Office Chair,Ergonomic Office Chair,,Stock,Active,Nos,299.99
ITEM003,Desk Lamp,LED Desk Lamp with USB,,Stock,Active,Nos,49.99
ITEM004,Wireless Mouse,Logitech Wireless Mouse,,Stock,Active,Nos,29.99
ITEM005,USB-C Cable,3 Pack USB-C Cables,,Stock,Active,Nos,19.99
ITEM006,Keyboard,Mechanical RGB Keyboard,,Stock,Active,Nos,89.99
ITEM007,Monitor Stand,Adjustable Monitor Stand,,Stock,Active,Nos,69.99
ITEM008,Webcam,1080p HD Webcam,,Stock,Active,Nos,59.99
ITEM009,Headphones,Wireless Bluetooth Headphones,,Stock,Active,Nos,129.99
ITEM010,Screen Protector,MacBook Pro Screen Protector,,Stock,Active,Nos,9.99
```

Save as `items_import.csv`

#### Step 2: Upload File
1. Go to **Bulk Import Operations** folder
2. Click **1. Upload CSV File for Import**
3. In the **Body** tab, click the file input field
4. Select your `items_import.csv` file
5. Click **Send**
6. Save the returned `id` as the `import_job_id` (auto-filled if tests are enabled)

#### Step 3: Check Status
1. Click **2. Get Import Job Status**
2. Ensure `{{import_job_id}}` is set to the job ID from step 2
3. Click **Send**
4. Observe the status (PENDING → PROCESSING → COMPLETED)

#### Step 4: View Errors (if any)
1. Click **3. Get Import Job Errors**
2. Click **Send**
3. Review any row-level errors

#### Step 5: Get Template (Optional)
1. Click **5. Download CSV Import Template**
2. Click **Send** to view the template format

### For Export Operations

#### Step 1: Create Export Job
1. Go to **Bulk Export Operations** folder
2. Click **1. Create Export Job with Filters**
3. Modify the body if needed:
   - Change `file_format` to "csv", "xlsx", or "json"
   - Adjust filters (item_type, status, item_group_id, search)
   - Select specific columns or leave null for all
4. Click **Send**
5. Save the returned `id` as `export_job_id`

#### Step 2: Check Status
1. Click **4. Get Export Job Status**
2. Click **Send**
3. Wait for status to change to "COMPLETED"

#### Step 3: Download File
1. Click **5. Download Exported File**
2. Click **Send**
3. The file will be downloaded based on the format

#### Step 4: Quick Export (Alternative)
1. Click **7. Quick Export (CSV)**
2. Modify query parameters as needed
3. Click **Send**
4. File downloads directly without creating a job

## Request Details

### Common Headers
- All requests include Bearer token authentication
- `Content-Type: application/json` (except file uploads)

### Query Parameters

#### Pagination
- `page` - Page number (default: 1)
- `page_size` - Items per page (default: 20)

#### Export Filters
- `item_type` - Filter by item type (Stock, Service, etc.)
- `status` - Filter by status (Active, Inactive)
- `item_group_id` - Filter by item group UUID
- `search` - Search by item code, name, or description

### Request Body Examples

#### Import Upload
```
Form Data:
- file: <binary file>
```

#### Export Create Job
```json
{
  "file_format": "csv",
  "file_name": "items_export",
  "filters": {
    "item_type": "Stock",
    "status": "Active"
  },
  "selected_columns": ["id", "item_code", "item_name"]
}
```

## Response Examples

### Successful Import Job Creation (202 Accepted)
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "organization_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "items_import.csv",
  "status": "PENDING",
  "total_rows": 0,
  "successful_rows": 0,
  "failed_rows": 0,
  "created_at": "2026-02-03T10:30:00Z"
}
```

### Completed Import Job (200 OK)
```json
{
  "id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "organization_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_name": "items_import.csv",
  "status": "COMPLETED",
  "total_rows": 10,
  "successful_rows": 9,
  "failed_rows": 1,
  "summary": "Import completed: 9/10 rows successful"
}
```

### Error Response (400/422)
```json
{
  "detail": "File size exceeds 50.0MB limit"
}
```

## Troubleshooting

### Issue: "Access denied" or 403 Forbidden
**Solution:** 
- Check your access token is valid and not expired
- Verify organization_id matches your user's organization
- Get a new token from identity service

### Issue: "User must belong to an organization"
**Solution:**
- The JWT token must include `organization_id` claim
- Re-authenticate with identity service

### Issue: File upload fails
**Solution:**
- Check file size (max 50MB)
- Verify file format is supported (CSV, XLSX, JSON)
- Ensure CSV headers match expected columns

### Issue: Export job stuck in PENDING
**Solution:**
- Wait a few seconds and refresh status
- Check for error message in status response
- Verify items exist matching the filters

### Issue: "Import job not found"
**Solution:**
- Verify the job_id is correct
- Ensure you're using the latest job_id from a recent upload
- Check organization_id matches

## Tips

1. **Auto-save Job IDs:** The collection has tests that auto-populate job IDs to environment variables
2. **Reuse Environment:** Save your environment settings for future use
3. **Mock Data:** Use the sample CSV data provided in the collection
4. **Test Different Formats:** Try export in CSV, XLSX, and JSON formats
5. **Monitor Status:** Regularly check job status to understand processing speed
6. **Review Errors:** Always review error details for failed imports to understand issues

## Support

For issues with:
- **API Endpoints**: Check the core-service logs: `docker logs horizon_core`
- **Database**: Verify tables exist: `docker exec horizon_postgres psql -U horizon_user -d core_db -c "\dt bulk_*"`
- **Authentication**: Verify token with identity-service

## Files Included

1. `Horizon_Sync_Bulk_Import_Export.postman_collection.json` - Main collection
2. This README file
3. Sample CSV data (in collection documentation)
