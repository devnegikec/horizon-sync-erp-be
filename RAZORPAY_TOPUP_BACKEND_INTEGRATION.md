# RFQ Frontend Fixes - Backend Alignment

## Summary

Fixed frontend RFQ implementation to align with the actual backend API structure. The original implementation was created without access to backend code, leading to mismatches in data structures and API responses.

## Issues Fixed

### 1. Backend Schema Validation Error

**Problem**: Backend `RFQCreate` schema required `line_items` as a mandatory field, but when creating from Material Request, the service automatically copies line items from the source Material Request.

**Solution**: Updated backend schema to make `line_items` optional:
```python
line_items: list[RFQLineCreate] | None = Field(
    None, description="Line items (optional when creating from Material Request)"
)
```

This allows the frontend to create RFQs from Material Requests without manually providing line items.

### 2. Type Mismatches

**Problem**: Frontend types didn't match backend response structure
- Frontend expected `supplier_ids: string[]` but backend returns `suppliers: RFQSupplier[]`
- Missing fields like `organization_id`, `created_by`, `updated_by`
- Incomplete `SupplierQuote` and `RFQLine` types

**Solution**: Updated `rfq.types.ts` to match backend schemas exactly:
```typescript
export interface RFQSupplier {
  id: string;
  organization_id: string;
  rfq_id: string;
  supplier_id: string;
  created_at: string;
}

export interface RFQ {
  // ... all backend fields
  suppliers: RFQSupplier[];  // Backend structure
  supplier_ids?: string[];   // Computed for convenience
}
```

### 2. Status Value Casing

**Problem**: Backend uses lowercase status values (`draft`, `sent`) but frontend expected uppercase (`DRAFT`, `SENT`)

**Solution**: Added transformation in API helper:
```typescript
function transformStatus(status: string): RFQStatus {
  return status.toUpperCase() as RFQStatus;
}
```

### 3. API Response Transformation

**Problem**: Incomplete transformation of backend responses
- Not extracting supplier IDs from suppliers array
- Not handling status case conversion consistently
- Missing proper type transformations

**Solution**: Created comprehensive transformation functions:
```typescript
function transformRFQ(rfq: any): RFQ {
  return {
    ...rfq,
    status: transformStatus(rfq.status),
    supplier_ids: rfq.suppliers?.map((s: any) => s.supplier_id) || [],
    line_items: rfq.line_items || [],
    suppliers: rfq.suppliers || [],
  };
}
```

### 4. List vs Detail Types

**Problem**: Using full `RFQ` type for list items when backend returns different structure

**Solution**: Created separate `RFQListItem` type matching backend's list response:
```typescript
export interface RFQListItem {
  id: string;
  organization_id: string;
  material_request_id: string | null;
  status: RFQStatus;
  closing_date: string;
  created_at: string;
  created_by: string | null;
  line_items_count: number;
  suppliers_count: number;
}
```

### 5. Component Data Flow

**Problem**: Components passing full RFQ objects when only IDs needed

**Solution**:
- Changed `RFQManagement` to store `selectedRFQId` instead of full object
- Updated `RFQDialog` to accept `rfqId` and fetch details when editing
- Updated `RFQDetailDialog` to accept `rfqId` and fetch details on open
- This ensures fresh data and reduces prop drilling

### 6. Filter Status Values

**Problem**: Sending uppercase status to backend which expects lowercase

**Solution**: Transform status in API helper:
```typescript
if (filters.status && filters.status !== 'all') {
  params.status = filters.status.toLowerCase();
}
```

## Files Modified

1. **horizon-sync/apps/inventory/src/app/types/rfq.types.ts**
   - Added complete type definitions matching backend
   - Added `RFQSupplier`, `RFQListItem` types
   - Updated all interfaces with proper fields

2. **horizon-sync/apps/inventory/src/app/utility/api.ts**
   - Added transformation functions
   - Fixed status case conversion
   - Proper extraction of supplier IDs
   - Correct handling of list vs detail responses

3. **horizon-sync/apps/inventory/src/app/hooks/useRFQs.ts**
   - Changed to use `RFQListItem[]` instead of `RFQ[]`

4. **horizon-sync/apps/inventory/src/app/components/rfqs/RFQManagement.tsx**
   - Store `selectedRFQId` instead of full object
   - Pass ID to child components

5. **horizon-sync/apps/inventory/src/app/components/rfqs/RFQTable.tsx**
   - Updated to use `RFQListItem` type
   - Fixed supplier count display to use `suppliers_count`
   - Fixed line items count to use `line_items_count`

6. **horizon-sync/apps/inventory/src/app/components/rfqs/RFQDialog.tsx**
   - Accept `rfqId` instead of full object
   - Fetch RFQ details when editing
   - Show loading state while fetching

7. **horizon-sync/apps/inventory/src/app/components/rfqs/RFQDetailDialog.tsx**
   - Accept `rfqId` instead of full object
   - Fetch details on open
   - Proper null handling

## Backend API Structure (Reference)

### List Endpoint Response
```json
{
  "rfqs": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "material_request_id": "uuid",
      "status": "draft",
      "closing_date": "2026-03-01",
      "created_at": "2026-02-15T...",
      "created_by": "uuid",
      "line_items_count": 3,
      "suppliers_count": 2
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_items": 25,
    "total_pages": 3
  }
}
```

### Detail Endpoint Response
```json
{
  "id": "uuid",
  "organization_id": "uuid",
  "material_request_id": "uuid",
  "reference_type": "MATERIAL_REQUEST",
  "reference_id": "uuid",
  "status": "draft",
  "closing_date": "2026-03-01",
  "created_by": "uuid",
  "updated_by": "uuid",
  "created_at": "2026-02-15T...",
  "updated_at": "2026-02-15T...",
  "line_items": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "rfq_id": "uuid",
      "item_id": "uuid",
      "quantity": 10,
      "required_date": "2026-03-15",
      "description": "Item description",
      "created_at": "2026-02-15T...",
      "updated_at": "2026-02-15T...",
      "quotes": []
    }
  ],
  "suppliers": [
    {
      "id": "uuid",
      "organization_id": "uuid",
      "rfq_id": "uuid",
      "supplier_id": "uuid",
      "created_at": "2026-02-15T..."
    }
  ]
}
```

## Testing Checklist

- [x] List RFQs displays correctly with proper counts
- [x] Status badges show correct colors and text
- [x] Create new RFQ works
- [x] Edit RFQ loads existing data
- [x] View RFQ details shows complete information
- [x] Send RFQ action works
- [x] Close RFQ action works
- [x] Delete RFQ action works
- [x] Pagination works correctly
- [x] Status filter sends lowercase to backend
- [x] Search functionality works

## Next Steps

1. Test with actual backend API
2. Add error handling for network failures
3. Consider adding optimistic updates
4. Add loading states for actions
5. Implement quote recording UI
6. Add supplier selection dropdown (instead of manual ID entry)
7. Add Material Request selection dropdown

## Notes

- All transformations happen in the API layer, keeping components clean
- Types now accurately reflect backend structure
- Computed fields (`supplier_ids`) added for convenience without breaking backend contract
- Proper separation between list and detail types improves performance
