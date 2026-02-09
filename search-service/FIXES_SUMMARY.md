# Search Service Fixes Summary

## Date: February 9, 2026

## Issues Fixed

### 1. JSONB Metadata Filter Crash (search_engine.py)

**Problem**: The code was crashing when trying to filter by metadata fields using JSONB operators.

**Root Cause**: Incorrect SQLAlchemy syntax for accessing JSONB fields. The code was using `.astext` which doesn't exist in SQLAlchemy's JSONB API.

**Fix**: Changed from:
```python
SearchDocument.metadata_[field].astext == str(value)
```

To:
```python
SearchDocument.metadata_[field].as_string() == str(value)
```

**Location**: `search-service/app/search_engine.py` line ~330-340 in `_execute_search` method

**Test Result**: ✅ PASSED - Metadata filters now work correctly

---

### 2. PostgreSQL DISTINCT + ORDER BY Error in suggest_terms (search_engine.py)

**Problem**: Search queries were failing with SQL error:
```
ERROR: for SELECT DISTINCT, ORDER BY expressions must appear in select list
```

**Root Cause**: The `suggest_terms` method was using `SELECT DISTINCT` on `title` while ordering by `similarity()` function, which wasn't in the SELECT list. PostgreSQL requires ORDER BY expressions to appear in the SELECT list when using DISTINCT.

**Fix**: Changed from:
```python
stmt = select(SearchDocument.title).distinct()
stmt = stmt.where(
    func.similarity(SearchDocument.title, partial_query) > 0.3
).order_by(
    func.similarity(SearchDocument.title, partial_query).desc()
)
```

To:
```python
similarity_score = func.similarity(SearchDocument.title, partial_query).label('similarity_score')
stmt = select(SearchDocument.title, similarity_score).distinct()
stmt = stmt.where(
    similarity_score > 0.3
).order_by(
    similarity_score.desc()
)
```

**Location**: `search-service/app/search_engine.py` line ~240-260 in `suggest_terms` method

**Test Result**: ✅ PASSED - Search queries no longer fail with SQL errors

---

### 3. Data Synchronization Script Errors (sync_direct_db.py)

**Problem**: The sync script was failing to sync customers, suppliers, and warehouses due to SQL errors.

**Root Causes**:
1. **Customers table**: SQL query referenced non-existent column `customer_type`
2. **Suppliers table**: SQL query referenced non-existent column `supplier_type`
3. **Warehouses table**: Table doesn't exist in the database

**Fixes**:

#### Customers Sync
Changed SQL query from:
```sql
SELECT id, customer_code, customer_name, email, phone, customer_type
FROM customers
WHERE status = 'active'
```

To:
```sql
SELECT id, customer_code, customer_name, email, phone, city, country
FROM customers
WHERE status = 'active'
```

Updated metadata to include `city` and `country` instead of `customer_type`.

#### Suppliers Sync
Changed SQL query from:
```sql
SELECT id, supplier_code, supplier_name, email, phone, supplier_type
FROM suppliers
WHERE status = 'active'
```

To:
```sql
SELECT id, supplier_code, supplier_name, email, phone, city, country
FROM suppliers
WHERE status = 'active'
```

Updated metadata to include `city` and `country` instead of `supplier_type`.

#### Warehouses Sync
Removed warehouses sync entirely since the table doesn't exist in the core database.

**Location**: `search-service/sync_direct_db.py`

**Test Result**: ✅ PASSED
```
Items: 19 records synced
Customers: 1 records synced
Suppliers: 1 records synced
Total: 21 records synced
```

---

## Database Schema Verification

Verified actual column names in core_db:

### Customers Table
- ✅ Has: `customer_code`, `customer_name`, `email`, `phone`, `city`, `country`
- ❌ Does NOT have: `customer_type`

### Suppliers Table
- ✅ Has: `supplier_code`, `supplier_name`, `email`, `phone`, `city`, `country`
- ❌ Does NOT have: `supplier_type`

### Warehouses Table
- ❌ Does NOT exist in core_db

---

## Testing

Created comprehensive test script `test_search_with_filters.py` that verifies:

1. ✅ Global search without filters
2. ✅ Local search for specific entity types
3. ✅ Search with JSONB metadata filters (the critical fix)
4. ✅ Search with wildcard queries

All tests passed successfully.

---

## Files Modified

1. `search-service/app/search_engine.py` - Fixed JSONB filter syntax
2. `search-service/sync_direct_db.py` - Fixed SQL queries to match actual schema
3. `search-service/test_search_with_filters.py` - Created test script (new file)
4. `search-service/FIXES_SUMMARY.md` - This document (new file)

---

## Summary

All three critical issues have been resolved:

1. **JSONB Metadata Filter Crash**: Fixed by correcting the SQLAlchemy JSONB accessor syntax from `.astext` to `.as_string()`
2. **PostgreSQL DISTINCT + ORDER BY Error**: Fixed by including the similarity score in the SELECT list when using DISTINCT with ORDER BY
3. **Data Synchronization Failures**: Fixed by updating SQL queries to match actual database schema (removed non-existent columns, added existing columns)

The search service is now fully operational with:
- 21 searchable documents synced from core database
- Working JSONB metadata filters
- Functional global and local search endpoints
- Proper handling of entity-specific searches
- Working search term suggestions with trigram similarity

## Next Steps

1. ✅ JSONB filter crash - FIXED
2. ✅ Data synchronization - FIXED
3. ⏭️ Consider implementing automatic schema discovery to prevent future column mismatch issues
4. ⏭️ Add warehouses table to core-service if needed for search functionality
5. ⏭️ Update search engine to handle empty queries with filters (currently requires non-empty query text)

---

## Notes

- The container volume mount was not picking up file changes, so files had to be copied directly into the container using `docker cp`
- The search service is now fully functional with 21 searchable documents (19 items, 1 customer, 1 supplier)
- JSONB metadata filtering is working correctly and can be used for advanced search queries
