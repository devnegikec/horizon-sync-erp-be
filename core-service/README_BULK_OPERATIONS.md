# 📌 Bulk Import/Export - Complete Documentation Index

## 🎯 Start Here

Pick based on your needs:

### I want to test the API right now
👉 **[QUICK_START_POSTMAN.md](QUICK_START_POSTMAN.md)** (5 minutes)
- Import collection in Postman
- Set up environment variables
- Upload sample CSV
- Download exported file

### I need complete setup and reference
👉 **[POSTMAN_COLLECTION_README.md](POSTMAN_COLLECTION_README.md)** (15 minutes)
- Detailed step-by-step setup
- All endpoint documentation
- Request/response examples
- Troubleshooting guide
- Tips and tricks

### I'm a DBA or need database details
👉 **[BULK_OPERATIONS_TABLES.md](BULK_OPERATIONS_TABLES.md)**
- Table structure
- Column definitions
- Indexes
- Sample queries
- Data retention

### I just want an overview
👉 **[POSTMAN_COLLECTION_SUMMARY.txt](POSTMAN_COLLECTION_SUMMARY.txt)**
- What's included
- Quick reference
- Learning path
- Deployment checklist

---

## 📂 File Structure

```
core-service/
├── 📋 Horizon_Sync_Bulk_Import_Export.postman_collection.json ← Import this into Postman
├── 📄 QUICK_START_POSTMAN.md ← Read this first (5 min)
├── 📄 POSTMAN_COLLECTION_README.md ← Detailed guide (15 min)
├── 📄 BULK_OPERATIONS_TABLES.md ← Database structure
├── 📄 POSTMAN_COLLECTION_SUMMARY.txt ← Overview
├── 📊 sample_import_data.csv ← Ready-to-use test data
├── 🔧 scripts/
│   └── create_bulk_import_export_tables.sql ← Already executed
└── 📋 app/
    ├── 📁 api/v1/endpoints/
    │   ├── bulk_import.py ← Import endpoints
    │   └── bulk_export.py ← Export endpoints
    ├── 📁 services/
    │   ├── bulk_import_service.py ← Business logic
    │   └── bulk_export_service.py ← Business logic
    ├── 📁 repositories/
    │   ├── bulk_import_repository.py ← Database ops
    │   └── bulk_export_repository.py ← Database ops
    ├── 📁 models/
    │   ├── bulk_import_job.py ← ORM model
    │   └── bulk_export_job.py ← ORM model
    └── 📁 schemas/
        └── bulk_operations.py ← Request/Response models
```

---

## 🚀 5-Minute Quick Start

### 1. Import Postman Collection
```
File → Import → Horizon_Sync_Bulk_Import_Export.postman_collection.json
```

### 2. Set Environment
```
Environment Variables:
- base_url = http://localhost:8001/api/v1
- access_token = <your JWT token>
- organization_id = <your org UUID>
```

### 3. Test Upload
```
Collection → Bulk Import Operations → 1. Upload CSV File
Select sample_import_data.csv → Send
```

### 4. Check Status
```
Collection → Bulk Import Operations → 2. Get Import Job Status → Send
```

### 5. Test Export
```
Collection → Bulk Export Operations → 1. Create Export Job → Send
Collection → Bulk Export Operations → 5. Download Exported File → Send
```

✅ **Done!** Your API is working.

---

## 📊 Endpoints at a Glance

### Import Endpoints (6)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/bulk-import/upload` | Upload file for import |
| GET | `/bulk-import/{job_id}/status` | Get import status |
| GET | `/bulk-import/{job_id}/errors` | Get error details |
| GET | `/bulk-import` | List import jobs |
| GET | `/bulk-import/template/csv` | CSV template |
| GET | `/bulk-import/template/xlsx` | XLSX template |

### Export Endpoints (5)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/bulk-export` | Create export job |
| GET | `/bulk-export/{job_id}/status` | Get export status |
| GET | `/bulk-export/{job_id}/download` | Download file |
| GET | `/bulk-export` | List export jobs |
| POST | `/bulk-export/quick` | Quick export |

---

## 💾 Database Tables

### `bulk_import_jobs`
Tracks import operations:
- Job status (PENDING, PROCESSING, COMPLETED, FAILED)
- File information (name, path, MIME type)
- Statistics (total, successful, failed rows)
- Error details (JSON with row-level errors)

### `bulk_export_jobs`
Tracks export operations:
- Job status
- File format (CSV, XLSX, JSON)
- Export filters (item_type, status, etc.)
- Column selection
- Expiration timestamp (24 hours default)

See [BULK_OPERATIONS_TABLES.md](BULK_OPERATIONS_TABLES.md) for full schema.

---

## 🔑 Key Features

### Supported Formats
- ✅ CSV
- ✅ XLSX (Excel)
- ✅ JSON

### Capabilities
- ✅ Bulk import with validation
- ✅ Row-level error tracking
- ✅ Bulk export with filters
- ✅ Column selection for export
- ✅ Job status tracking
- ✅ Search functionality
- ✅ Pagination
- ✅ Multi-format support
- ✅ File size limits (50MB max)
- ✅ Row limits (10,000 max)

### Security
- ✅ JWT authentication
- ✅ Organization isolation
- ✅ User attribution
- ✅ Role-based access

---

## 🧪 Testing Guide

### Test 1: Simple Import
1. Use sample_import_data.csv
2. Upload via POST /bulk-import/upload
3. Check status via GET /bulk-import/{job_id}/status
4. Verify items in database

### Test 2: Import with Errors
1. Create CSV with duplicate item codes
2. Upload file
3. Check GET /bulk-import/{job_id}/errors
4. View row-level errors

### Test 3: Export with Filters
1. POST /bulk-export with filters
2. Monitor status
3. Download file
4. Verify content

### Test 4: Quick Export
1. POST /bulk-export/quick?file_format=csv
2. File downloads directly
3. No job tracking needed

---

## 📚 Documentation Map

```
For Quick Start →
  ├─ QUICK_START_POSTMAN.md
  └─ sample_import_data.csv

For Setup & Usage →
  ├─ POSTMAN_COLLECTION_README.md
  ├─ Endpoint documentation
  ├─ Request/Response examples
  └─ Troubleshooting guide

For Database →
  ├─ BULK_OPERATIONS_TABLES.md
  ├─ Schema information
  ├─ Sample queries
  └─ Maintenance scripts

For Overview →
  ├─ POSTMAN_COLLECTION_SUMMARY.txt
  ├─ What's included
  ├─ Learning path
  └─ Deployment checklist
```

---

## ✅ Prerequisites

Before using:
- [ ] Docker running
- [ ] core-service on port 8001
- [ ] PostgreSQL tables created
- [ ] Postman installed
- [ ] Valid JWT token
- [ ] Organization UUID

## ⚡ Verify Setup

### Check API is running
```bash
curl http://localhost:8001/docs
```

### Check database tables
```bash
docker exec horizon_postgres psql -U horizon_user -d core_db -c "\dt bulk_*"
```

### Check backend logs
```bash
docker logs horizon_core | tail -50
```

---

## 🎓 Learning Path

### Beginner (30 min)
1. Read QUICK_START_POSTMAN.md
2. Import collection
3. Upload sample CSV
4. Download exported file
5. Check job status

### Intermediate (1 hour)
1. Read POSTMAN_COLLECTION_README.md
2. Try different formats
3. Use filters
4. Review error details
5. Test pagination

### Advanced (2+ hours)
1. Study table structure
2. Query database directly
3. Create automation
4. Monitor large imports
5. Optimize performance

---

## 🔗 Quick Links

| Resource | Location |
|----------|----------|
| API Docs | http://localhost:8001/docs |
| Quick Start | [QUICK_START_POSTMAN.md](QUICK_START_POSTMAN.md) |
| Full Guide | [POSTMAN_COLLECTION_README.md](POSTMAN_COLLECTION_README.md) |
| Database | [BULK_OPERATIONS_TABLES.md](BULK_OPERATIONS_TABLES.md) |
| Collection | Horizon_Sync_Bulk_Import_Export.postman_collection.json |
| Sample Data | sample_import_data.csv |

---

## 🆘 Troubleshooting

### Common Issues

**"Authorization Header missing"**
→ Set `access_token` in Postman environment

**"File size exceeds limit"**
→ Use smaller CSV (max 50MB)

**"Job not found"**
→ Use correct job ID from response

**"Item code already exists"**
→ Use unique codes or different organization

**"Port 8001 not accessible"**
→ Start core-service: `docker-compose up core-service`

---

## 📞 Support Resources

1. **Setup Issues** - Check QUICK_START_POSTMAN.md
2. **API Issues** - Check POSTMAN_COLLECTION_README.md
3. **Database Issues** - Check BULK_OPERATIONS_TABLES.md
4. **General Overview** - Check POSTMAN_COLLECTION_SUMMARY.txt
5. **Logs** - `docker logs horizon_core`
6. **Swagger UI** - http://localhost:8001/docs

---

## 📋 Checklist for First Run

- [ ] Read QUICK_START_POSTMAN.md (5 min)
- [ ] Import Postman collection
- [ ] Set environment variables
- [ ] Verify API is running
- [ ] Upload sample_import_data.csv
- [ ] Check import job status
- [ ] Create export job
- [ ] Download exported file
- [ ] Review POSTMAN_COLLECTION_README.md
- [ ] Try different formats and filters

---

## 🎉 You're Ready!

Start with **[QUICK_START_POSTMAN.md](QUICK_START_POSTMAN.md)** and enjoy testing! 🚀

---

**Last Updated:** February 3, 2026
**Version:** 1.0.0
**Status:** ✅ Ready for Production
