# Quick Start Guide - Bulk Import/Export Testing

## 5-Minute Setup

### Prerequisites
- Postman installed
- Running Horizon Sync backend (core-service on port 8001)
- Valid JWT token from identity-service

### Step 1: Import Collection (1 min)
1. Download `Horizon_Sync_Bulk_Import_Export.postman_collection.json`
2. Open Postman → Click **File** → **Import**
3. Select the JSON file
4. Click **Import**

### Step 2: Set Environment Variables (1 min)
In Postman, click the **Environment** dropdown (gear icon):

**Quick Setup - Add these variables:**
```
base_url = http://localhost:8001/api/v1
access_token = YOUR_JWT_TOKEN_HERE
organization_id = YOUR_ORG_UUID_HERE
```

### Step 3: Test Import (2 min)

#### 3a. Download Sample Data
Use the `sample_import_data.csv` file from the core-service folder, or copy this:

```csv
item_code,item_name,description,item_group_id,item_type,status,uom,standard_rate
ITEM001,Laptop Computer,Dell XPS 13,550e8400-e29b-41d4-a716-446655440001,Stock,Active,Nos,1299.99
ITEM002,Office Chair,Ergonomic Chair,550e8400-e29b-41d4-a716-446655440002,Stock,Active,Nos,299.99
ITEM003,Desk Lamp,LED Lamp,550e8400-e29b-41d4-a716-446655440002,Stock,Active,Nos,49.99
```

#### 3b. Upload File
1. Go to **Bulk Import Operations** → **1. Upload CSV File for Import**
2. Click **Body** tab
3. In formdata, click the **file** field
4. Select your CSV file
5. Click **Send**
6. Note the `id` in the response

#### 3c. Check Status
1. Go to **2. Get Import Job Status**
2. Click **Send**
3. Observe status change from PENDING → PROCESSING → COMPLETED

### Step 4: Test Export (1 min)

#### 4a. Create Export
1. Go to **Bulk Export Operations** → **1. Create Export Job with Filters**
2. Click **Send**
3. Note the `id` in the response

#### 4b. Download File
1. Go to **5. Download Exported File**
2. Click **Send**
3. File downloads automatically

---

## Common Test Scenarios

### Scenario 1: Import with Validation Errors

**Goal:** See how the system handles invalid data

1. Create a CSV with mixed valid/invalid data:
```csv
item_code,item_name,description
ITEM001,Valid Item,This is valid
,Missing Code,No item code - should fail
ITEM003,,Empty item name - should fail
ITEM004,Another Valid Item,This should work
```

2. Upload and check errors in **3. Get Import Job Errors**

### Scenario 2: Export with Filters

**Goal:** Export only active stock items

1. Go to **1. Create Export Job with Filters**
2. Modify the body:
```json
{
  "file_format": "csv",
  "filters": {
    "item_type": "Stock",
    "status": "Active"
  }
}
```
3. Send and download the file

### Scenario 3: Quick Export

**Goal:** Export without creating a job

1. Go to **7. Quick Export (CSV)**
2. Send - file downloads immediately

### Scenario 4: Search and Export

**Goal:** Export items matching search term

1. Go to **8. Quick Export (XLSX with Search)**
2. Send - exports items containing "widget" or modify search term

---

## Response Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Request successful |
| 202 | Accepted | Job created, processing in background |
| 400 | Bad Request | Invalid parameters - check the body/query |
| 401 | Unauthorized | Invalid/expired token - get new token |
| 403 | Forbidden | No access to this organization |
| 404 | Not Found | Job ID doesn't exist |
| 413 | Too Large | File exceeds 50MB limit |
| 422 | Validation Error | Invalid data format |
| 500 | Server Error | Check backend logs |

---

## Useful Postman Features

### 1. Auto-save Job IDs
The collection has tests that automatically save job IDs to variables:
- After import upload, `import_job_id` is auto-populated
- After export create, `export_job_id` is auto-populated

### 2. View Request History
- Click **History** on the left
- See all previous requests
- Click any to re-run

### 3. Compare Responses
- Open request in new tab
- Send again
- Use **Compare** feature to see differences

### 4. Create Test Suite
- Use **Runner** to execute multiple requests in sequence
- Tests automatically validate responses

---

## Troubleshooting

### ❌ "Authorization Header missing"
**Fix:** Ensure `access_token` is set in Environment variables

### ❌ "File size exceeds limit"
**Fix:** Use smaller sample CSV (max 50MB)

### ❌ Job stuck in PENDING
**Fix:** 
- Wait 5-10 seconds
- Refresh status
- Check backend logs: `docker logs horizon_core`

### ❌ "Item code already exists"
**Fix:** Modify item codes in CSV to be unique, or import to different organization

### ❌ 404 Job not found
**Fix:** 
- Use the correct job ID from the response
- Ensure it's the latest job

---

## File Reference

| File | Purpose |
|------|---------|
| `Horizon_Sync_Bulk_Import_Export.postman_collection.json` | Main Postman collection |
| `POSTMAN_COLLECTION_README.md` | Detailed documentation |
| `sample_import_data.csv` | 25 sample items for testing |
| `BULK_OPERATIONS_TABLES.md` | Database table documentation |
| This file | Quick start guide |

---

## Next Steps

1. **Import the collection** ✓
2. **Set environment variables** ✓
3. **Test with sample data** ✓
4. **Customize for your data** ← You are here
5. **Deploy to production** - Follow deployment guide

---

## Example Workflow

```
1. Prepare data (CSV, XLSX, or JSON)
   ↓
2. Upload via POST /bulk-import/upload
   ↓
3. Get job_id from response
   ↓
4. Poll GET /bulk-import/{job_id}/status
   ↓
5. Once COMPLETED, check for errors
   ↓
6. Items are now in database
```

---

## Support Commands

### Check if API is running
```bash
curl http://localhost:8001/docs
```

### Check database tables
```bash
docker exec horizon_postgres psql -U horizon_user -d core_db -c "\dt bulk_*"
```

### View recent import jobs
```bash
docker exec horizon_postgres psql -U horizon_user -d core_db -c "SELECT id, file_name, status, total_rows FROM bulk_import_jobs ORDER BY created_at DESC LIMIT 5;"
```

### View recent export jobs
```bash
docker exec horizon_postgres psql -U horizon_user -d core_db -c "SELECT id, file_name, file_format, status FROM bulk_export_jobs ORDER BY created_at DESC LIMIT 5;"
```

---

## Questions?

Check these resources:
- API Documentation: http://localhost:8001/docs
- PostgreSQL Tables: Run the verification queries above
- Backend Logs: `docker logs horizon_core`
- Collection Documentation: See POSTMAN_COLLECTION_README.md
