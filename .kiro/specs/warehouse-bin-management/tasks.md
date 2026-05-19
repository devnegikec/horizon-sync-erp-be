# Implementation Plan: Warehouse Bin Management

## Overview

Step-by-step implementation of the warehouse bin management feature extending the existing warehouse system with bin-level storage tracking, optimized put-away/pick routing, worker task assignment, and QR-based time tracking. Tasks follow the dependency order: enums/models → migrations → repositories → services → endpoints → tests. Each task builds on previous steps and ends with wiring into the existing system.

Tech stack: Python FastAPI, SQLAlchemy ORM, PostgreSQL, Pydantic schemas, Alembic migrations, Hypothesis for property-based testing.

## Tasks

- [ ] 1. Database models and migration

  - [ ] 1.1 Create enums and SQLAlchemy model for `warehouse_locations` in `core-service/app/models/warehouse_location.py`

    - Define `LocationType` enum (zone, aisle, bay, level, bin)
    - Define `PutAwayListStatus` enum (pending, in_progress, completed, cancelled)
    - Define `PutAwayListItemStatus` enum (pending, completed, skipped)
    - Define `WorkerTaskType` enum (put_away, pick)
    - Define `WorkerTaskStatus` enum (assigned, in_progress, completed, cancelled)
    - Define `ScanType` enum (start, finish)
    - Define `AllocationType` enum (exclusive, preferred)
    - Define `WarehouseLocation` model with all fields from design: id, organization_id, warehouse_id, parent_location_id, location_type, code, full_code, name, total_capacity, capacity_uom, position_x, position_y, is_active, version, timestamps, created_by, updated_by
    - Add parent self-referential relationship and warehouse relationship
    - Add UniqueConstraint on (warehouse_id, full_code)
    - Register model in `core-service/app/models/__init__.py`
    - _Requirements: 1.1, 1.5_

  - [ ] 1.2 Create SQLAlchemy models for `bin_stock_levels`, `put_away_lists`, `put_away_list_items`, `worker_tasks`, `qr_scan_records`, and `location_allocations`

    - Create `BinStockLevel` model in `core-service/app/models/bin_stock_level.py` with version column for optimistic locking, UniqueConstraint on (bin_location_id, item_id), CHECK constraint on quantity_on_hand >= 0
    - Create `PutAwayList` and `PutAwayListItem` models in `core-service/app/models/put_away_list.py`
    - Create `WorkerTask` model in `core-service/app/models/worker_task.py`
    - Create `QRScanRecord` model in `core-service/app/models/qr_scan_record.py`
    - Create `LocationAllocation` model in `core-service/app/models/location_allocation.py` with UniqueConstraint on (location_id, allocation_type) for exclusive allocations
    - Register all models in `core-service/app/models/__init__.py`
    - _Requirements: 3.1, 4.6, 7.2, 8.5, 12.1, 12.2_

  - [ ] 1.3 Add `bin_location_id` column to existing `PickListItem` model

    - Add nullable `bin_location_id` column with ForeignKey to `warehouse_locations.id`
    - _Requirements: 5.6_

  - [ ] 1.4 Create Alembic migration for all new tables and the `pick_list_items` modification
    - Generate migration with `alembic revision --autogenerate`
    - Include all indexes from design: idx_wl_org, idx_wl_warehouse, idx_wl_parent, idx_wl_type, idx_wl_active, idx_bsl_org, idx_bsl_bin, idx_bsl_item, idx_pal_org, idx_pal_warehouse, idx_pal_status, idx_pali_list, idx_pali_bin, idx_wt_org, idx_wt_worker, idx_wt_status, idx_wt_reference, idx_qsr_org, idx_qsr_task, idx_qsr_item, idx_la_org, idx_la_location, idx_la_item_group
    - Include CHECK constraints for location_type, status fields, scan_type, allocation_type
    - _Requirements: 1.5, 3.1, 4.6, 7.2, 8.5, 12.1_

- [ ] 2. Pydantic schemas

  - [ ] 2.1 Create Pydantic schemas for location management in `core-service/app/schemas/warehouse_location.py`

    - `LocationCreate` (location_type, code, name, parent_location_id, capacity, capacity_uom, position_x, position_y)
    - `LocationUpdate` (name, capacity, capacity_uom, position_x, position_y, is_active)
    - `LocationResponse`, `LocationTreeNode` (recursive children), `LocationSummary`
    - `LocationFilters` (location_type, parent_location_id, is_active, has_stock, search, page, page_size)
    - `PaginatedLocations`
    - _Requirements: 1.1, 1.5, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ] 2.2 Create Pydantic schemas for bin stock, put-away, worker tasks, QR scans, and allocations
    - `BinStockAdd`, `BinStockRemove`, `BinStockResponse`, `BinStockInfo` in `core-service/app/schemas/bin_stock.py`
    - `PutAwayGenerateRequest` (receipt_items list), `PutAwayListResponse`, `PutAwayListItemResponse` in `core-service/app/schemas/put_away.py`
    - `WorkerTaskCreate`, `WorkerTaskResponse`, `TaskFilters` in `core-service/app/schemas/worker_task.py`
    - `ScanCreate`, `QRScanResponse`, `TimeSummaryFilters`, `TimeSummary` in `core-service/app/schemas/qr_scan.py`
    - `AllocationCreate`, `AllocationResponse`, `AllocationFilters` in `core-service/app/schemas/location_allocation.py`
    - _Requirements: 3.1, 3.6, 4.1, 4.6, 7.1, 7.2, 7.6, 8.1, 8.5, 8.6, 12.1, 12.2, 12.7_

- [ ] 3. Repository layer

  - [ ] 3.1 Create `LocationRepository` in `core-service/app/repositories/location_repository.py`

    - CRUD operations for warehouse_locations
    - `get_tree(warehouse_id, org_id)` — recursive query to build hierarchy
    - `get_children(location_id)` — direct children
    - `get_ancestors(location_id)` — walk up to root
    - `list_with_filters(warehouse_id, filters, org_id)` — filtered/paginated query
    - `get_subtree_bin_ids(location_id)` — all bin IDs in subtree (for capacity calculations)
    - _Requirements: 1.7, 2.1, 2.5, 11.1, 11.3_

  - [ ] 3.2 Create `BinStockRepository` in `core-service/app/repositories/bin_stock_repository.py`

    - `get_or_create(bin_location_id, item_id, org_id)` — upsert pattern
    - `update_with_version(bin_stock_id, quantity_delta, current_version)` — optimistic locking
    - `get_bins_for_item(item_id, warehouse_id, org_id)` — all bins containing an item
    - `get_stock_in_bin(bin_location_id, org_id)` — all items in a bin
    - `get_total_stock_in_subtree(location_id, org_id)` — sum of stock in subtree
    - _Requirements: 3.1, 3.2, 3.3, 3.6, 9.5_

  - [ ] 3.3 Create `PutAwayRepository` in `core-service/app/repositories/put_away_repository.py`

    - CRUD for put_away_lists and put_away_list_items
    - `get_list_with_items(put_away_list_id, org_id)`
    - `update_item_status(item_id, status)`
    - `count_completed_items(put_away_list_id)` and `count_total_items(put_away_list_id)`
    - _Requirements: 4.6, 10.1, 10.2, 10.3, 10.4_

  - [ ] 3.4 Create `TaskRepository` in `core-service/app/repositories/task_repository.py`

    - CRUD for worker_tasks
    - `list_by_worker(worker_id, filters, org_id)` — filtered by status and date range
    - _Requirements: 7.1, 7.6_

  - [ ] 3.5 Create `ScanRepository` in `core-service/app/repositories/scan_repository.py`

    - `create_scan(scan_data, org_id)`
    - `get_start_scan(task_item_id, worker_task_id)` — find preceding start scan
    - `get_time_summary(filters, org_id)` — aggregated time data
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.6_

  - [ ] 3.6 Create `AllocationRepository` in `core-service/app/repositories/allocation_repository.py`
    - CRUD for location_allocations
    - `get_allocations_for_location(location_id)` — check exclusive conflicts
    - `list_by_warehouse(warehouse_id, filters, org_id)`
    - `check_exclusive_conflict(location_id, item_group_id)` — verify no overlapping exclusive allocations
    - _Requirements: 12.1, 12.7, 12.8_

- [ ] 4. Checkpoint - Ensure models, schemas, and repositories compile

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Core services — LayoutService and CapacityService

  - [ ] 5.1 Implement `LayoutService` in `core-service/app/services/layout_service.py`

    - `create_location()` — validate hierarchy (warehouse→zone→aisle→bay→level→bin), generate full_code by concatenating ancestor codes, persist
    - `get_location_tree()` — return full hierarchy for a warehouse
    - `list_locations()` — filtered/paginated list with computed fields (full_path, item_count, available_capacity)
    - `get_location_summary()` — compute total_bins, occupied_bins, total_capacity, used_capacity, available_capacity for a subtree
    - `deactivate_location()` — set is_active=False, prevent new stock to location and descendants
    - `generate_location_code()` — concatenate ancestor codes with hyphens
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 1.7, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ]\* 5.2 Write property tests for hierarchy validation (Property 1) and full code concatenation (Property 2)

    - **Property 1: Hierarchy Validation** — For any location type and parent type pair, creation succeeds only when parent is the immediate predecessor in the chain
    - **Property 2: Full Code Concatenation** — For any valid hierarchy, full_code equals hyphen-joined ancestor codes
    - **Validates: Requirements 1.2, 1.3, 1.4**

  - [ ] 5.3 Implement `CapacityService` in `core-service/app/services/capacity_service.py`

    - `rollup_capacity(location_id)` — walk up tree, sum children's total_capacity at each level
    - `compute_available_capacity(location_id)` — total_capacity minus sum of stock in subtree
    - `recalculate_ancestors(bin_location_id)` — triggered on stock changes, update available_capacity for bin and all ancestors within same transaction
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 9.3, 9.4_

  - [ ]\* 5.4 Write property tests for capacity rollup invariant (Property 4) and available capacity formula (Property 5)
    - **Property 4: Capacity Rollup Invariant** — For any location with children, total_capacity equals sum of direct children's total_capacity
    - **Property 5: Available Capacity Formula** — For any location, available_capacity equals total_capacity minus sum of quantity_on_hand in subtree
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

- [ ] 6. Core services — BinStockService

  - [ ] 6.1 Implement `BinStockService` in `core-service/app/services/bin_stock_service.py`

    - `add_stock(bin_id, item_id, quantity, org_id)` — validate bin is active, check capacity, increment quantity_on_hand with optimistic locking (retry up to 3 times), update warehouse-level stock_levels, create stock_movement record, trigger capacity recalculation
    - `remove_stock(bin_id, item_id, quantity, org_id)` — validate sufficient stock, decrement with optimistic locking, update warehouse-level stock_levels, create stock_movement, trigger capacity recalculation
    - `get_bins_for_item(item_id, warehouse_id, org_id)` — return all bins with quantities and available capacity
    - `get_bin_stock(bin_id, org_id)` — return all items in a bin
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 9.1, 9.2, 9.3, 9.5_

  - [ ]\* 6.2 Write property tests for stock operations (Properties 3, 6, 7, 8)
    - **Property 3: Deactivated Location Blocks Stock** — Adding stock to deactivated location or descendants is rejected
    - **Property 6: Stock Add/Remove Round-Trip** — Adding Q then removing Q returns quantity_on_hand to original value
    - **Property 7: Bin-to-Warehouse Stock Consistency** — Warehouse-level stock equals sum of all bin stocks for that item
    - **Property 8: Capacity Overflow Rejection** — Adding stock exceeding bin capacity is rejected and stock remains unchanged
    - **Validates: Requirements 1.6, 3.2, 3.3, 3.4, 3.5**

- [ ] 7. Core services — PutAwayService and AllocationService

  - [ ] 7.1 Implement `AllocationService` in `core-service/app/services/allocation_service.py`

    - `create_allocation(data, org_id)` — validate no overlapping exclusive allocations, persist
    - `list_allocations(warehouse_id, filters, org_id)` — filtered list
    - `deactivate_allocation(allocation_id, org_id)` — set is_active=False
    - `check_exclusive_conflict(location_id, item_group_id)` — return True if conflict exists
    - `get_allocations_for_item_group(item_group_id, warehouse_id, org_id)` — get preferred/exclusive locations for an item group
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.7, 12.8_

  - [ ] 7.2 Implement `PutAwayService` in `core-service/app/services/put_away_service.py`

    - `generate_put_away_list(receipt_items, warehouse_id, org_id)` — check location_allocations first (exclusive then preferred), then put_away_rules, filter bins by active + sufficient capacity, split quantity across bins if needed, pass to RoutingOptimizer for sort_order, create put_away_list and items
    - `complete_item(put_away_list_id, item_id, org_id)` — mark item completed, call BinStockService.add_stock, update list status (PENDING→IN_PROGRESS on first, →COMPLETED when all done)
    - `skip_item(put_away_list_id, item_id, org_id)` — mark item SKIPPED, do NOT update bin stock, flag for review
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 10.1, 10.2, 10.3, 10.4, 10.5, 12.3, 12.4, 12.5, 12.6_

  - [ ]\* 7.3 Write property tests for put-away and allocation (Properties 9, 18, 19)
    - **Property 9: Put-Away Completeness and Capacity Respect** — Sum of assigned quantities equals received quantity, no bin assignment exceeds available capacity
    - **Property 18: Exclusive Allocation Enforcement** — Items from different group never assigned to exclusively allocated location
    - **Property 19: No Overlapping Exclusive Allocations** — Creating second exclusive allocation on same location is rejected
    - **Validates: Requirements 4.1, 4.3, 4.4, 12.3, 12.5, 12.6, 12.8**

- [ ] 8. Core services — PickService and RoutingOptimizer

  - [ ] 8.1 Implement `RoutingOptimizer` in `core-service/app/services/routing_optimizer.py`

    - `optimize_route(locations, origin=(0,0))` — group by aisle, sort within aisle by position, order aisles by nearest-neighbor from origin, assign sequential sort_order
    - Helper methods: `_aisle_distance()`, `_aisle_exit_position()`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]\* 8.2 Write property test for routing optimizer (Property 10)

    - **Property 10: Routing Optimizer Correctness** — Output is permutation of input, sort_order is sequential 1..N, same-aisle bins are contiguous
    - **Validates: Requirements 4.5, 5.4, 6.1, 6.3, 6.4**

  - [ ] 8.3 Implement enhanced `PickService` in `core-service/app/services/pick_service.py`

    - `resolve_bin_locations(pick_list_id, org_id)` — for each pick item, query bin_stock_levels sorted by quantity descending, allocate from largest bins first, split across bins if needed, pass to RoutingOptimizer, update pick_list_items with bin_location_id and sort_order
    - `complete_pick_item(pick_list_id, item_id, bin_id, qty, org_id)` — call BinStockService.remove_stock, update picked_qty, update pick list status
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 10.6_

  - [ ]\* 8.4 Write property test for pick resolution (Property 11)
    - **Property 11: Pick Resolution Correctness** — Total resolved quantity equals requested, every resolved bin has sufficient stock, bins selected in descending quantity order
    - **Validates: Requirements 5.1, 5.2, 5.3**

- [ ] 9. Core services — TaskService and QRScanService

  - [ ] 9.1 Implement `TaskService` in `core-service/app/services/task_service.py`

    - `create_task(task_type, worker_id, reference_id, org_id)` — create worker_task with status ASSIGNED
    - `start_task(task_id, org_id)` — set status IN_PROGRESS, record started_at
    - `complete_task(task_id, org_id)` — set status COMPLETED, record completed_at
    - `cancel_task(task_id, org_id)` — set status CANCELLED
    - `list_worker_tasks(worker_id, filters, org_id)` — filtered by status and date range
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ] 9.2 Implement `QRScanService` in `core-service/app/services/qr_scan_service.py`

    - `record_scan(scan_data, org_id)` — validate finish scan has preceding start scan, compute elapsed_seconds on finish, persist record
    - `get_time_summary(filters, org_id)` — aggregate time data per worker, per task, per location
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6_

  - [ ]\* 9.3 Write property tests for scan and status (Properties 12, 13, 14, 15)
    - **Property 12: Elapsed Seconds Calculation** — elapsed_seconds equals difference between finish and start timestamps in whole seconds
    - **Property 13: Finish Without Start Rejection** — Finish scan without preceding start is rejected
    - **Property 14: Status Transition on Item Completion** — First item completion transitions list to IN_PROGRESS, all items completed transitions to COMPLETED
    - **Property 15: Skipped Items Don't Affect Stock** — Skipping an item leaves bin stock unchanged
    - **Validates: Requirements 8.3, 8.4, 10.2, 10.3, 10.5, 10.6**

- [ ] 10. Checkpoint - Ensure all services compile and unit tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. API endpoints — Location management

  - [ ] 11.1 Create location management endpoints in `core-service/app/api/v1/endpoints/warehouse_locations.py`

    - `POST /api/v1/warehouses/{warehouse_id}/locations` — create location node
    - `GET /api/v1/warehouses/{warehouse_id}/locations/tree` — full hierarchy tree
    - `GET /api/v1/warehouses/{warehouse_id}/locations` — list with filters (location_type, parent_location_id, is_active, has_stock, search, page, page_size)
    - `GET /api/v1/warehouses/{warehouse_id}/locations/{location_id}` — get detail
    - `GET /api/v1/warehouses/{warehouse_id}/locations/{location_id}/summary` — subtree summary
    - `PATCH /api/v1/warehouses/{warehouse_id}/locations/{location_id}` — update location
    - `POST /api/v1/warehouses/{warehouse_id}/locations/{location_id}/deactivate` — deactivate
    - Register router in `core-service/app/api/v1/router.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 1.7, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6_

  - [ ]\* 11.2 Write property tests for location filtering (Properties 16, 17)
    - **Property 16: Location Filtering Correctness** — Every returned location satisfies all applied filter criteria
    - **Property 17: Location Summary Accuracy** — Summary values match actual computed values from subtree traversal
    - **Validates: Requirements 11.1, 11.3, 11.4, 11.5**

- [ ] 12. API endpoints — Bin stock and put-away

  - [ ] 12.1 Create bin stock endpoints in `core-service/app/api/v1/endpoints/bin_stock.py`

    - `POST /api/v1/bin-stock/add` — add stock to bin
    - `POST /api/v1/bin-stock/remove` — remove stock from bin
    - `GET /api/v1/bin-stock/by-item/{item_id}` — all bins for an item (query param: warehouse_id)
    - `GET /api/v1/bin-stock/by-bin/{bin_location_id}` — all stock in a bin
    - Register router in `core-service/app/api/v1/router.py`
    - _Requirements: 3.1, 3.2, 3.3, 3.5, 3.6_

  - [ ] 12.2 Create put-away list endpoints in `core-service/app/api/v1/endpoints/put_away_lists.py`
    - `POST /api/v1/put-away-lists/generate` — generate put-away list from receipt items
    - `GET /api/v1/put-away-lists` — list put-away lists (filter by warehouse, status)
    - `GET /api/v1/put-away-lists/{id}` — get detail with items
    - `POST /api/v1/put-away-lists/{id}/items/{item_id}/complete` — complete item
    - `POST /api/v1/put-away-lists/{id}/items/{item_id}/skip` — skip item
    - Register router in `core-service/app/api/v1/router.py`
    - _Requirements: 4.1, 4.6, 10.1, 10.2, 10.3, 10.4, 10.5_

- [ ] 13. API endpoints — Pick list enhancement, worker tasks, QR scans, allocations

  - [ ] 13.1 Create pick list bin resolution endpoints in `core-service/app/api/v1/endpoints/pick_lists.py` (enhance existing)

    - `POST /api/v1/pick-lists/{id}/resolve-bins` — resolve pick items to bin locations
    - `POST /api/v1/pick-lists/{id}/items/{item_id}/complete` — complete pick item from bin
    - _Requirements: 5.1, 5.4, 5.5, 5.6_

  - [ ] 13.2 Create worker task endpoints in `core-service/app/api/v1/endpoints/worker_tasks.py`

    - `POST /api/v1/worker-tasks` — create/assign task
    - `GET /api/v1/worker-tasks` — list tasks (filter by worker_id, status, date range)
    - `GET /api/v1/worker-tasks/{id}` — get task detail
    - `POST /api/v1/worker-tasks/{id}/start` — start task
    - `POST /api/v1/worker-tasks/{id}/complete` — complete task
    - `POST /api/v1/worker-tasks/{id}/cancel` — cancel task
    - Register router in `core-service/app/api/v1/router.py`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

  - [ ] 13.3 Create QR scan endpoints in `core-service/app/api/v1/endpoints/qr_scans.py`

    - `POST /api/v1/qr-scans` — record scan event
    - `GET /api/v1/qr-scans/summary` — time tracking summary (filter by worker, task, location, date range)
    - Register router in `core-service/app/api/v1/router.py`
    - _Requirements: 8.1, 8.5, 8.6_

  - [ ] 13.4 Create location allocation endpoints in `core-service/app/api/v1/endpoints/location_allocations.py`
    - `POST /api/v1/location-allocations` — create allocation
    - `GET /api/v1/location-allocations` — list allocations (filter by warehouse_id, item_group_id, location_type)
    - `GET /api/v1/location-allocations/{id}` — get allocation detail
    - `POST /api/v1/location-allocations/{id}/deactivate` — deactivate allocation
    - Register router in `core-service/app/api/v1/router.py`
    - _Requirements: 12.1, 12.2, 12.7, 12.8_

- [ ] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document (19 properties total)
- Unit tests validate specific examples and edge cases
- All stock operations (bin + warehouse level) must be wrapped in a single database transaction
- Optimistic locking on `bin_stock_levels` and `warehouse_locations` via `version` column with retry logic (up to 3 retries)
- Multi-tenancy enforced via `organization_id` on all queries
