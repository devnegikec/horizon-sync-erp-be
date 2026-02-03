### Requirement 3: Warehouse Management

**User Story:** As a warehouse manager, I want to organize inventory across multiple locations and bins, so that I can efficiently track where items are stored and optimize picking operations.

#### Acceptance Criteria

1. WHEN a user creates a warehouse, THE ERP_System SHALL define location code, name, address, and operational parameters
2. WHEN a user creates bins within a warehouse, THE ERP_System SHALL establish hierarchical storage locations with capacity limits
3. WHEN a user moves stock between bins, THE ERP_System SHALL update location records and maintain movement history
4. WHEN a user views warehouse capacity, THE ERP_System SHALL display utilization percentages and available space
5. WHEN a user performs stock transfers between warehouses, THE ERP_System SHALL create transfer documents and update stock levels
6. WHEN a user sets bin-specific item assignments, THE ERP_System SHALL suggest optimal picking routes

### Requirement 4: Supplier Management

**User Story:** As a procurement manager, I want to maintain supplier relationships and purchase terms, so that I can efficiently manage purchasing and track supplier performance.

#### Acceptance Criteria

1. WHEN a user creates a supplier record, THE ERP_System SHALL capture contact details, payment terms, and delivery preferences
2. WHEN a user assigns items to suppliers, THE ERP_System SHALL maintain supplier-item relationships with lead times and minimum order quantities
3. WHEN a user views supplier performance, THE ERP_System SHALL display delivery reliability, quality metrics, and price history
4. WHEN a user creates purchase orders, THE ERP_System SHALL suggest preferred suppliers based on item assignments and performance
5. WHEN a user receives goods, THE ERP_System SHALL match deliveries against purchase orders and update stock levels
6. WHEN a user processes supplier invoices, THE ERP_System SHALL validate against received quantities and agreed prices

### Requirement 8: Stock Management

**User Story:** As an inventory controller, I want to monitor stock levels and movements in real-time, so that I can prevent stockouts, optimize inventory levels, and maintain accurate records.

#### Acceptance Criteria

1. WHEN stock levels change, THE ERP_System SHALL update quantities in real-time across all affected locations
2. WHEN stock falls below reorder points, THE ERP_System SHALL generate purchase requisitions and alert procurement
3. WHEN a user performs stock counts, THE ERP_System SHALL compare physical counts with system records and identify variances
4. WHEN a user adjusts stock levels, THE ERP_System SHALL require authorization and maintain audit trails
5. WHEN a user views stock reports, THE ERP_System SHALL provide aging analysis, turnover rates, and valuation summaries
6. WHEN stock movements occur, THE ERP_System SHALL record transaction details including user, timestamp, and reason codes

- [ ] 6. Implement Warehouse and Stock Management modules

  - [ ] 6.1 Create Warehouse Management UI with Core Service integration

    - Connect to Core Service `/api/v1/warehouses` endpoints
    - Implement warehouse CRUD operations using existing APIs
    - Add bin management using warehouse hierarchy features
    - _Backend API: Core Service warehouses endpoints_
    - _Requirements: 3.1, 3.2_

  - [ ] 6.2 Implement Stock Management integration

    - Connect to Core Service stock management endpoints:
      - `/api/v1/stock-levels` for current stock queries
      - `/api/v1/stock-movements` for movement tracking
      - `/api/v1/stock-entries` for stock transactions
    - Implement real-time stock level displays
    - Add stock movement tracking with audit trails
    - _Backend API: Core Service stock management endpoints_
    - _Requirements: 8.1, 8.6_

  - [ ]\* 6.3 Write property test for stock consistency

    - **Property 7: Stock Consistency Across Transactions**
    - **Validates: Requirements 3.3, 3.5, 6.3, 8.1**

  - [ ] 6.4 Implement stock operations UI
    - Create stock inquiry and movement screens
    - Build stock transfer interfaces using `/api/v1/stock-movements`
    - Add stock reconciliation using `/api/v1/stock-reconciliations`
    - Implement capacity utilization dashboards
    - _Requirements: 3.3, 3.4, 3.5, 8.3, 8.5_

- [ ] 7. Implement Supplier Management module
  - [ ] 7.1 Create Supplier Management UI with Core Service integration
    - Connect to Core Service `/api/v1/suppliers` endpoints
    - Implement supplier CRUD operations using existing APIs
    - Add supplier-item relationships management
    - _Backend API: Core Service suppliers endpoints_
    - _Requirements: 4.1, 4.2_

#### Stock Movements

```http
# List stock movements
GET /stock-movements?item_id=uuid&warehouse_id=uuid&date_from=2024-01-01

# Create stock movement
POST /stock-movements
{
  "item_id": "uuid",
  "warehouse_id": "uuid",
  "movement_type": "receipt",
  "quantity": 100,
  "reference_document": "PO001",
  "reason_code": "purchase_receipt"
}

# Get movement details
GET /stock-movements/{id}
```

#### Stock Entries

```http
GET /stock-entries
POST /stock-entries
GET /stock-entries/{id}
PUT /stock-entries/{id}
DELETE /stock-entries/{id}
```

#### Stock Reconciliations

```http
GET /stock-reconciliations
POST /stock-reconciliations
GET /stock-reconciliations/{id}
PUT /stock-reconciliations/{id}
DELETE /stock-reconciliations/{id}
```

## warehouse Get api (http://localhost:8001/api/v1/warehouses?page=1&page_size=20&sort_by=created_at&sort_order=desc)

## response

````{
    "warehouses": [
        {
            "id": "cbf290a6-91cb-4c93-b9a6-db408bb3c274",
            "name": "Main Warehouse",
            "code": "WH-MAIN",
            "warehouse_type": "warehouse",
            "parent_warehouse_id": null,
            "city": "Mumbai",
            "is_active": true,
            "is_default": true,
            "created_at": "2026-01-26T15:47:10.155932Z"
        },
        {
            "id": "3c7956f3-d57a-4a01-936b-6d6cf98de665",
            "name": "Retail Store",
            "code": "WH-STORE",
            "warehouse_type": "store",
            "parent_warehouse_id": null,
            "city": "Mumbai",
            "is_active": true,
            "is_default": false,
            "created_at": "2026-01-26T15:47:10.155932Z"
        },
        {
            "id": "c5a6fa4d-becf-4365-a241-5b122f77dc7f",
            "name": "Goods in Transit",
            "code": "WH-TRANSIT",
            "warehouse_type": "transit",
            "parent_warehouse_id": "cbf290a6-91cb-4c93-b9a6-db408bb3c274",
            "city": null,
            "is_active": true,
            "is_default": false,
            "created_at": "2026-01-26T15:47:10.155932Z"
        }
    ],
    "pagination": {
        "page": 1,
        "page_size": 20,
        "total_items": 3,
        "total_pages": 1,
        "has_next": false,
        "has_prev": false
    }
}```

## Warehose post (http://localhost:8001/api/v1/warehouses)

## payload
```{
  "name": "string",
  "code": "string",
  "description": "string",
  "parent_warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "warehouse_type": "warehouse",
  "address_line1": "string",
  "address_line2": "string",
  "city": "string",
  "state": "string",
  "postal_code": "string",
  "country": "string",
  "contact_name": "string",
  "contact_phone": "string",
  "contact_email": "string",
  "total_capacity": 0,
  "capacity_uom": "string",
  "stock_account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "is_active": true,
  "is_default": false,
  "extra_data": {}
}``

## response
```{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "string",
  "code": "string",
  "description": "string",
  "parent_warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "parent": {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "code": "string",
    "name": "string"
  },
  "warehouse_type": "string",
  "address_line1": "string",
  "address_line2": "string",
  "city": "string",
  "state": "string",
  "postal_code": "string",
  "country": "string",
  "contact_name": "string",
  "contact_phone": "string",
  "contact_email": "string",
  "total_capacity": 0,
  "capacity_uom": "string",
  "stock_account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "is_active": true,
  "is_default": true,
  "extra_data": {},
  "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "updated_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "created_at": "2026-02-02T16:39:19.415Z",
  "updated_at": "2026-02-02T16:39:19.415Z"
}``


## Stock  Levels GET API (http://localhost:8001/api/v1/stock-levels?page=1&page_size=20&sort_by=updated_at&sort_order=desc)

## Response
````

{
"stock_levels": [
{
"id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
"product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
"warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
"quantity_on_hand": 0,
"quantity_reserved": 0,
"quantity_available": 0,
"last_counted_at": "2026-02-02T16:41:09.258Z",
"updated_at": "2026-02-02T16:41:09.258Z"
}
],
"pagination": {
"page": 0,
"page_size": 0,
"total_items": 0,
"total_pages": 0,
"has_next": true,
"has_prev": true
}
}```

## Stock Levels Post API (http://localhost:8001/api/v1/stock-levels)

## paylaod

````{
  "item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "quantity_on_hand": 0,
  "quantity_reserved": 0,
  "quantity_available": 0,
  "last_counted_at": "2026-02-02T16:42:55.305Z"
}```
## Response
```{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "quantity_on_hand": 0,
  "quantity_reserved": 0,
  "quantity_available": 0,
  "last_counted_at": "2026-02-02T16:42:57.220Z",
  "created_at": "2026-02-02T16:42:57.220Z",
  "updated_at": "2026-02-02T16:42:57.220Z"
}```

## Response
````

## Stock Movements GET API (/api/v1/stock-movements)

## Response

````{
  "stock_movements": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "movement_type": "string",
      "quantity": 0,
      "performed_at": "2026-02-02T16:47:39.291Z",
      "created_at": "2026-02-02T16:47:39.291Z"
    }
  ],
  "pagination": {
    "page": 0,
    "page_size": 0,
    "total_items": 0,
    "total_pages": 0,
    "has_next": true,
    "has_prev": true
  }
}```

## Stock Movements POST API (/api/v1/stock-movements)

## payload
```{
  "item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "movement_type": "string",
  "quantity": 0,
  "unit_cost": 0,
  "reference_type": "string",
  "reference_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "notes": "string",
  "performed_at": "2026-02-02T16:48:03.416Z"
}```

## response
```{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "movement_type": "string",
  "quantity": 0,
  "unit_cost": "string",
  "reference_type": "string",
  "reference_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "notes": "string",
  "performed_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "performed_at": "2026-02-02T16:48:03.462Z",
  "created_at": "2026-02-02T16:48:03.462Z",
  "updated_at": "2026-02-02T16:48:03.462Z"
}```

## stock entries GET API (/api/v1/stock-entries)
## Response
```{
  "stock_entries": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "stock_entry_no": "string",
      "stock_entry_type": "string",
      "from_warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "to_warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "posting_date": "2026-02-02T16:51:57.183Z",
      "status": "string",
      "created_at": "2026-02-02T16:51:57.183Z"
    }
  ],
  "pagination": {
    "page": 0,
    "page_size": 0,
    "total_items": 0,
    "total_pages": 0,
    "has_next": true,
    "has_prev": true
  }
}```

## STock Entries Post API
## paylaod
```{
  "stock_entry_no": "string",
  "stock_entry_type": "string",
  "from_warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "to_warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "posting_date": "2026-02-02T16:53:42.717Z",
  "posting_time": "string",
  "status": "draft",
  "reference_type": "string",
  "reference_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "remarks": "string",
  "total_value": 0,
  "expense_account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "cost_center_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "is_backflush": true,
  "bom_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "extra_data": {},
  "items": [
    {
      "item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "source_warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "target_warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "qty": 0,
      "uom": "string",
      "basic_rate": 0,
      "valuation_rate": 0,
      "batch_no": "string",
      "serial_nos": [
        "string"
      ],
      "description": "string",
      "extra_data": {}
    }
  ]
}```
## REsponse
```{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "stock_entry_no": "string",
  "stock_entry_type": "string",
  "from_warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "to_warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "posting_date": "2026-02-02T16:53:42.783Z",
  "posting_time": "string",
  "status": "string",
  "reference_type": "string",
  "reference_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "remarks": "string",
  "total_value": "string",
  "expense_account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "cost_center_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "is_backflush": true,
  "bom_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "extra_data": {},
  "submitted_at": "2026-02-02T16:53:42.783Z",
  "cancelled_at": "2026-02-02T16:53:42.783Z",
  "created_at": "2026-02-02T16:53:42.783Z",
  "updated_at": "2026-02-02T16:53:42.783Z",
  "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "updated_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "items": []
}```

## Stock Reconciliations GET (/api/v1/stock-reconciliations)
## Response
```{
  "stock_reconciliations": [
    {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "reconciliation_no": "string",
      "purpose": "string",
      "posting_date": "2026-02-02T16:56:05.695Z",
      "status": "string",
      "created_at": "2026-02-02T16:56:05.695Z"
    }
  ],
  "pagination": {
    "page": 0,
    "page_size": 0,
    "total_items": 0,
    "total_pages": 0,
    "has_next": true,
    "has_prev": true
  }
}```

## Stock Reconciliations POST (/api/v1/stock-reconciliations)
## Payload
```{
  "reconciliation_no": "string",
  "purpose": "string",
  "posting_date": "2026-02-02T16:57:13.873Z",
  "posting_time": "string",
  "status": "draft",
  "expense_account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "difference_account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "remarks": "string",
  "extra_data": {},
  "items": [
    {
      "item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "warehouse_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "current_qty": 0,
      "qty": 0,
      "qty_difference": 0,
      "current_valuation_rate": 0,
      "valuation_rate": 0,
      "batch_no": "string",
      "serial_nos": [
        "string"
      ],
      "extra_data": {}
    }
  ]
}```
## Response
```{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "reconciliation_no": "string",
  "purpose": "string",
  "posting_date": "2026-02-02T16:57:13.908Z",
  "posting_time": "string",
  "status": "string",
  "expense_account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "difference_account_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "remarks": "string",
  "extra_data": {},
  "submitted_at": "2026-02-02T16:57:13.908Z",
  "created_at": "2026-02-02T16:57:13.908Z",
  "updated_at": "2026-02-02T16:57:13.908Z",
  "created_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "updated_by": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "items": []
}```

 ## Item Suppliers GET (/api/v1/item-suppliers)
 ## Response
````

{
"item_suppliers": [
{
"id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
"item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
"supplier_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
"supplier_part_no": "string",
"lead_time_days": 0,
"is_default": true,
"created_at": "2026-02-02T17:01:22.435Z"
}
],
"pagination": {
"page": 0,
"page_size": 0,
"total_items": 0,
"total_pages": 0,
"has_next": true,
"has_prev": true
}
}```

## Item Suppliers POST (/api/v1/item-suppliers)

## Payload

````{
 "item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
 "supplier_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
 "supplier_part_no": "string",
 "lead_time_days": 0,
 "is_default": true,
 "extra_data": {}
}```
## Response
```{
 "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
 "organization_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
 "item_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
 "supplier_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
 "supplier_part_no": "string",
 "lead_time_days": 0,
 "is_default": true,
 "extra_data": {},
 "created_at": "2026-02-02T16:59:41.756Z",
 "updated_at": "2026-02-02T16:59:41.756Z"
}```

````
