# Implementation Plan: Warehouse QR-Based Inbound/Outbound with Bin Management

## Overview

This plan implements a warehouse management system with physical layout hierarchy, bin-level stock tracking, QR code-driven inbound/outbound workflows, worker task tracking, and capacity management. Built with Python FastAPI, PostgreSQL (SQLAlchemy + Alembic), and Hypothesis for property-based tests.

## Tasks

- [x] 1. Database schema and models

  - [x] 1.1 Create Alembic migration for warehouse_locations table

    - Create `warehouse_locations` table with all columns (id, organization_id, warehouse_id, parent_location_id, location_type, code, full_path, name, capacity, total_capacity, available_capacity, capacity_uom, position_x, position_y, is_active, version)
    - Add CHECK constraint for location_type enum (zone, aisle, bay, level, bin)
    - Add all indexes (org, warehouse, parent, type, active, full_path, unique warehouse+path)
    - _Requirements: 1.1, 1.5_

  - [x] 1.2 Create Alembic migration for bin_stock_levels and location_allocations tables

    - Create `bin_stock_levels` table with unique constraint on (bin_location_id, item_id, batch_number)
    - Create `location_allocations` table with CHECK constraint on allocation_type and partial unique index for exclusive allocations
    - Add all indexes
    - _Requirements: 3.1, 20.1, 20.2_

  - [x] 1.3 Create Alembic migration for scan_sessions and scan_session_items tables

    - Create `scan_sessions` table with CHECK constraints for session_type and status
    - Create `scan_session_items` table with unique constraint on (session_id, qr_identifier)
    - Add all indexes
    - _Requirements: 5.1, 5.2_

  - [x] 1.4 Create Alembic migration for receiving_slips and receiving_slip_items tables

    - Create `receiving_slips` table with CHECK constraint for status enum
    - Create `receiving_slip_items` table with CHECK constraint for flag enum
    - Add all indexes
    - _Requirements: 6.1, 7.1_

  - [x] 1.5 Create Alembic migration for gate_verification_sessions, gate_verification_items, and dispatch_records tables

    - Create `gate_verification_sessions` with CHECK constraints for status
    - Create `gate_verification_items` with CHECK constraints and unique constraint on (gate_session_id, qr_identifier)
    - Create `dispatch_records` with all indexes
    - _Requirements: 12.1, 12.6, 13.1_

  - [x] 1.6 Create Alembic migration for worker_tasks and location_scans tables

    - Create `worker_tasks` with CHECK constraints for task_type and status
    - Create `location_scans` with CHECK constraint for scan_type
    - Add all indexes
    - _Requirements: 16.1, 16.2, 17.5_

  - [x] 1.7 Create Alembic migration to extend existing pick_lists, pick_list_items, and put_away_list_items tables

    - ALTER pick_lists: add invoice_reference, invoice_data, dispatch_record_id columns
    - ALTER pick_list_items: add picked_qty, bin_location_id, sort_order columns
    - ALTER put_away_list_items: add bin_location_id, sort_order, status columns
    - _Requirements: 9.1, 9.4, 8.4_

  - [x] 1.8 Create SQLAlchemy models for all new tables
    - Create `WarehouseLocation` model in `core-service/app/models/warehouse_location.py`
    - Create `BinStockLevel` model in `core-service/app/models/bin_stock_level.py`
    - Create `LocationAllocation` model in `core-service/app/models/location_allocation.py`
    - Create `ScanSession` and `ScanSessionItem` models in `core-service/app/models/scan_session.py`
    - Create `ReceivingSlip` and `ReceivingSlipItem` models in `core-service/app/models/receiving_slip.py`
    - Create `GateVerificationSession` and `GateVerificationItem` models in `core-service/app/models/gate_verification.py`
    - Create `DispatchRecord` model in `core-service/app/models/dispatch_record.py`
    - Create `WorkerTask` model in `core-service/app/models/worker_task.py`
    - Create `LocationScan` model in `core-service/app/models/location_scan.py`
    - _Requirements: 1.5, 3.1, 5.1, 6.1, 12.1, 13.1, 16.2, 17.5_

- [x] 2. Checkpoint - Verify database migrations

  - Ensure all migrations run cleanly, ask the user if questions arise.

- [x] 3. Layout Service and Capacity Rollup

  - [x] 3.1 Implement LayoutService with hierarchy enforcement

    - Create `core-service/app/services/layout_service.py`
    - Implement `create_location` with parent-child hierarchy validation (VALID_PARENT_TYPES mapping)
    - Implement `generate_location_code` to concatenate ancestor codes into full_path
    - Implement `update_location`, `deactivate_location` (cascade to descendants)
    - Implement `get_tree` returning full hierarchy for a warehouse
    - Implement `list_locations` with filters (location_type, parent_location_id, is_active, has_stock)
    - Implement `get_location_summary` for subtree stats
    - Implement `search_locations` matching code or name
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.6, 1.7, 19.1, 19.2, 19.3, 19.4, 19.5, 19.6_

  - [ ]\* 3.2 Write property test for location hierarchy enforcement

    - **Property 1: Location Hierarchy Enforcement**
    - **Validates: Requirements 1.2, 1.3**

  - [ ]\* 3.3 Write property test for location code generation

    - **Property 2: Location Code Generation**
    - **Validates: Requirements 1.4**

  - [x] 3.4 Implement CapacityService with rollup algorithm

    - Create `core-service/app/services/capacity_service.py`
    - Implement `recalculate_ancestors` walking up the tree and summing children capacities
    - Implement `compute_available_capacity` (total_capacity minus stock in subtree)
    - Implement `get_capacity_summary` for any location node
    - Use optimistic locking (version column) for concurrent updates
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 18.3, 18.4, 18.5_

  - [ ]\* 3.5 Write property test for capacity rollup consistency

    - **Property 3: Capacity Rollup Consistency**
    - **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.6**

  - [ ]\* 3.6 Write property test for available capacity invariant

    - **Property 4: Available Capacity Invariant**
    - **Validates: Requirements 2.5**

  - [x] 3.7 Implement LocationRepository

    - Create `core-service/app/repositories/location_repository.py`
    - CRUD operations for warehouse_locations
    - Tree query with recursive CTE for hierarchy
    - Filtered list with pagination
    - _Requirements: 1.7, 19.1, 19.6_

  - [x] 3.8 Create Pydantic schemas for layout and capacity endpoints

    - Create `core-service/app/schemas/warehouse_location.py`
    - CreateLocationRequest, UpdateLocationRequest, LocationResponse, LocationTree, LocationSummary, LocationFilters, PaginatedLocations
    - _Requirements: 1.5, 19.2_

  - [x] 3.9 Implement layout and capacity API endpoints
    - Create `core-service/app/api/v1/endpoints/warehouse_locations.py`
    - POST /warehouse-locations, GET /warehouse-locations/tree/{warehouse_id}, GET /warehouse-locations, GET /warehouse-locations/{id}, PATCH /warehouse-locations/{id}, POST /warehouse-locations/{id}/deactivate, GET /warehouse-locations/{id}/summary, GET /warehouse-locations/search
    - Register router in main app
    - _Requirements: 1.1, 1.7, 19.1, 19.5_

- [x] 4. Bin Stock Service and Location Allocations

  - [x] 4.1 Implement BinStockService

    - Create `core-service/app/services/bin_stock_service.py`
    - Implement `add_stock` with capacity check, bin stock increment, warehouse stock_levels sync, and capacity rollup trigger
    - Implement `remove_stock` with on-hand check, bin stock decrement, warehouse stock_levels sync, and capacity rollup trigger
    - Implement `get_bins_for_item` and `get_bin_stock`
    - Reject stock operations on deactivated locations
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 18.1, 18.2_

  - [ ]\* 4.2 Write property test for deactivated location stock prevention

    - **Property 5: Deactivated Location Stock Prevention**
    - **Validates: Requirements 1.6**

  - [ ]\* 4.3 Write property test for bin stock addition and removal consistency

    - **Property 6: Bin Stock Addition and Removal Consistency**
    - **Validates: Requirements 3.2, 3.3, 3.4**

  - [ ]\* 4.4 Write property test for bin capacity overflow prevention

    - **Property 7: Bin Capacity Overflow Prevention**
    - **Validates: Requirements 3.5**

  - [ ]\* 4.5 Write property test for real-time capacity update on stock change

    - **Property 28: Real-Time Capacity Update on Stock Change**
    - **Validates: Requirements 18.1, 18.2, 18.3, 18.4**

  - [x] 4.6 Implement AllocationService

    - Create `core-service/app/services/allocation_service.py`
    - Implement `create_allocation` with exclusive overlap check
    - Implement `update_allocation`, `deactivate_allocation`, `list_allocations`
    - Implement `check_exclusive_overlap` validation
    - _Requirements: 20.1, 20.2, 20.7, 20.8_

  - [ ]\* 4.7 Write property test for no overlapping exclusive allocations

    - **Property 30: No Overlapping Exclusive Allocations**
    - **Validates: Requirements 20.8**

  - [x] 4.8 Create Pydantic schemas and API endpoints for bin stock and allocations
    - Create `core-service/app/schemas/bin_stock.py` and `core-service/app/schemas/location_allocation.py`
    - Create `core-service/app/api/v1/endpoints/bin_stock.py` (GET /bin-stock/{bin_id}, GET /bin-stock/item/{item_id}, POST /bin-stock/add, POST /bin-stock/remove)
    - Create `core-service/app/api/v1/endpoints/location_allocations.py` (POST, GET list, GET detail, PATCH, POST deactivate)
    - Register routers
    - _Requirements: 3.6, 20.7_

- [x] 5. Checkpoint - Verify layout, capacity, stock, and allocation services

  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Inbound Service (Scan Sessions, Receiving Slips, QR Decoding)

  - [x] 6.1 Implement QR payload decoding and validation

    - Add `decode_qr_payload` method to InboundService
    - Parse JSON payload extracting id, sku, qty, batch
    - Validate SKU is non-empty, quantity is positive integer, batch is non-empty
    - Return structured QRPayload dataclass
    - _Requirements: 4.1, 4.2, 4.3_

  - [ ]\* 6.2 Write property test for QR payload round-trip

    - **Property 8: QR Payload Round-Trip**
    - **Validates: Requirements 4.1**

  - [ ]\* 6.3 Write property test for invalid quantity rejection

    - **Property 9: Invalid Quantity Rejection**
    - **Validates: Requirements 4.3**

  - [x] 6.4 Implement InboundService scan session management

    - Create `core-service/app/services/inbound_service.py`
    - Implement `start_session` creating ScanSession with status OPEN
    - Implement `record_scan` with duplicate detection (unique qr_identifier per session), payload decoding, and scan event recording
    - Implement `end_session` closing session and generating receiving slip
    - Implement `get_session_summary` with per-SKU/batch aggregation and box count
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 14.1_

  - [ ]\* 6.5 Write property test for duplicate scan rejection within session

    - **Property 10: Duplicate Scan Rejection Within Session**
    - **Validates: Requirements 5.4**

  - [ ]\* 6.6 Write property test for session aggregation correctness

    - **Property 11: Session Aggregation Correctness**
    - **Validates: Requirements 5.3, 5.6**

  - [x] 6.7 Implement receiving slip generation and review workflow

    - Implement `generate_receiving_slip` from closed session (group by SKU+batch, compute totals)
    - Implement `approve_slip` transitioning to PENDING_PUTAWAY
    - Implement `reject_slip` with reason
    - Implement `flag_line_item` for SHORT/DAMAGED
    - Generate unique slip_number using document numbering service
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 7.1, 7.2, 7.3, 7.4, 7.5_

  - [ ]\* 6.8 Write property test for receiving slip generation correctness

    - **Property 12: Receiving Slip Generation Correctness**
    - **Validates: Requirements 6.1, 6.4**

  - [x] 6.9 Create Pydantic schemas and API endpoints for inbound

    - Create `core-service/app/schemas/inbound.py` (StartSessionRequest, ScanResult, SessionSummary, ReceivingSlipResponse, etc.)
    - Create `core-service/app/api/v1/endpoints/inbound.py` with all inbound endpoints
    - Register router
    - _Requirements: 5.1, 5.6, 6.1, 7.2_

  - [x] 6.10 Implement ScanSessionRepository and ReceivingSlipRepository
    - Create `core-service/app/repositories/scan_session_repository.py`
    - Create `core-service/app/repositories/receiving_slip_repository.py`
    - _Requirements: 5.1, 6.1_

- [x] 7. Put-Away Service and Routing Optimizer

  - [x] 7.1 Implement RoutingOptimizer

    - Create `core-service/app/services/routing_optimizer.py`
    - Implement nearest-neighbor heuristic with aisle grouping
    - Group locations by aisle, sort aisle groups by distance from origin
    - Within each aisle, sort by position (nearest-neighbor)
    - Assign sequential sort_order integers
    - Default origin to (0, 0) if not configured
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5_

  - [ ]\* 7.2 Write property test for routing optimizer aisle grouping

    - **Property 26: Routing Optimizer Aisle Grouping**
    - **Validates: Requirements 15.1, 15.2, 15.3, 15.4**

  - [x] 7.3 Implement PutAwayService

    - Create `core-service/app/services/put_away_service.py`
    - Implement `generate_from_slip` that assigns bins respecting allocations (exclusive first, then preferred, then unallocated) and capacity
    - Implement `assign_bins` logic with allocation priority and capacity filtering
    - Implement `complete_item` updating bin stock and marking item COMPLETED
    - Implement `skip_item` with reason
    - Trigger capacity rollup on item completion
    - Update receiving slip to PUTAWAY_COMPLETE when all items done
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 20.3, 20.4, 20.5, 20.6_

  - [ ]\* 7.4 Write property test for put-away respects bin capacity

    - **Property 15: Put-Away Respects Bin Capacity**
    - **Validates: Requirements 8.2**

  - [ ]\* 7.5 Write property test for put-away routing groups by aisle

    - **Property 16: Put-Away Routing Groups by Aisle**
    - **Validates: Requirements 8.3, 8.4**

  - [ ]\* 7.6 Write property test for exclusive allocation enforcement

    - **Property 29: Exclusive Allocation Enforcement**
    - **Validates: Requirements 20.3, 20.5, 20.6**

  - [x] 7.7 Create Pydantic schemas and API endpoints for put-away
    - Create `core-service/app/schemas/put_away.py`
    - Create `core-service/app/api/v1/endpoints/put_away.py` (GET list, GET detail, POST complete item, POST skip item)
    - Register router
    - _Requirements: 8.5, 8.6_

- [x] 8. Checkpoint - Verify inbound flow end-to-end

  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Outbound Service (Pick Lists, FIFO Resolution, Pick Scanning)

  - [x] 9.1 Implement PickListService with SAP invoice trigger

    - Create `core-service/app/services/pick_list_service.py`
    - Implement `create_from_invoice` parsing SAP invoice payload, creating pick list with status OPEN, populating items from invoice lines
    - Implement `resolve_bin_locations` using FIFO (oldest bin_stock_levels.created_at first), splitting across bins if needed
    - Pass resolved locations through RoutingOptimizer for sort ordering
    - Set pick list warehouse from invoice data
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_

  - [ ]\* 9.2 Write property test for pick list creation from invoice

    - **Property 18: Pick List Creation from Invoice**
    - **Validates: Requirements 9.1, 9.2**

  - [ ]\* 9.3 Write property test for FIFO bin resolution

    - **Property 19: FIFO Bin Resolution**
    - **Validates: Requirements 9.3**

  - [x] 9.4 Implement pick scan recording and status transitions

    - Implement `record_pick_scan` matching scanned SKU against pick list items, incrementing picked_qty
    - Reject scans for items not on pick list
    - Reject over-picking (scanned qty would exceed required qty)
    - Transition pick list from OPEN to IN_PROGRESS on first scan
    - Implement `complete_pick_list` (only when all items fully picked)
    - Implement `cancel_pick_list` releasing reserved stock
    - Decrement bin stock on successful pick scan
    - Record scan event in qr_scan_events
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 11.1, 11.2, 11.5_

  - [ ]\* 9.5 Write property test for pick scan matching and over-pick prevention

    - **Property 20: Pick Scan Matching and Over-Pick Prevention**
    - **Validates: Requirements 10.2, 10.3, 10.4, 10.5**

  - [ ]\* 9.6 Write property test for pick list status transitions

    - **Property 21: Pick List Status Transitions**
    - **Validates: Requirements 10.6, 11.2**

  - [ ]\* 9.7 Write property test for stock release on pick list cancellation

    - **Property 22: Stock Release on Pick List Cancellation**
    - **Validates: Requirements 11.5**

  - [x] 9.8 Create Pydantic schemas and API endpoints for outbound pick lists
    - Create `core-service/app/schemas/outbound.py` (SAPInvoicePayload, PickListResponse, PickScanResult, PickListProgress, PickListFilters)
    - Create `core-service/app/api/v1/endpoints/outbound.py` with pick list endpoints (POST from-invoice, GET list, GET detail, POST scan, POST complete, POST cancel)
    - Register router
    - _Requirements: 9.1, 10.1, 11.3, 11.4_

- [x] 10. Gate Verification and Dispatch

  - [x] 10.1 Implement GateVerificationService

    - Create `core-service/app/services/gate_verification_service.py`
    - Implement `start_session` creating gate session linked to completed pick list with vehicle/driver details
    - Implement `record_gate_scan` validating scanned item against pick list (mark VERIFIED or UNAUTHORIZED)
    - Implement `get_session_progress` showing scanned vs expected counts
    - Implement `verify_session` transitioning to VERIFIED when all items scanned
    - Record scan events in qr_scan_events with gate context
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.7_

  - [ ]\* 10.2 Write property test for gate verification against pick list

    - **Property 23: Gate Verification Against Pick List**
    - **Validates: Requirements 12.3, 12.4**

  - [x] 10.3 Implement OutboundService (dispatch records)

    - Create `core-service/app/services/outbound_service.py`
    - Implement `create_dispatch` from verified gate session: create dispatch record, decrement warehouse stock_levels, generate unique dispatch_number
    - Implement `list_dispatches` with filters (date range, vehicle, invoice reference)
    - Implement `get_dispatch` detail
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_

  - [ ]\* 10.4 Write property test for gate session completion triggers dispatch

    - **Property 24: Gate Session Completion Triggers Dispatch**
    - **Validates: Requirements 12.5, 12.6, 13.1, 13.4**

  - [x] 10.5 Create Pydantic schemas and API endpoints for gate verification and dispatch
    - Create `core-service/app/schemas/gate_verification.py` (GateSessionRequest, GateScanResult, GateSessionProgress)
    - Create `core-service/app/schemas/dispatch.py` (DispatchResponse, DispatchFilters)
    - Add gate and dispatch endpoints to `core-service/app/api/v1/endpoints/outbound.py`
    - _Requirements: 12.1, 12.7, 13.3_

- [x] 11. Checkpoint - Verify outbound flow end-to-end

  - Ensure all tests pass, ask the user if questions arise.

- [x] 12. Worker Tasks and Time Tracking

  - [x] 12.1 Implement TaskService

    - Create `core-service/app/services/task_service.py`
    - Implement `create_task` with task_type (put_away/pick), worker_id, reference_id
    - Implement `start_task` (ASSIGNED → IN_PROGRESS with started_at)
    - Implement `complete_task` (IN_PROGRESS → COMPLETED with completed_at)
    - Implement `cancel_task`
    - Implement `list_worker_tasks` with filters (worker_id, status, date range)
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6_

  - [x] 12.2 Implement QRScanService (location time tracking)

    - Create `core-service/app/services/qr_scan_service.py`
    - Implement `record_location_scan` accepting worker_id, task_id, location_code, scan_type (start/finish)
    - On finish scan: validate preceding start scan exists, calculate elapsed_seconds
    - Reject finish scan without preceding start scan
    - Implement `get_time_summary` with filters (worker, task, location, date range)
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6_

  - [ ]\* 12.3 Write property test for time tracking elapsed calculation

    - **Property 27: Time Tracking Elapsed Calculation**
    - **Validates: Requirements 17.2, 17.3, 17.4**

  - [x] 12.4 Create Pydantic schemas and API endpoints for worker tasks and location scans
    - Create `core-service/app/schemas/worker_task.py` (WorkerTaskCreate, WorkerTaskResponse, TaskFilters)
    - Create `core-service/app/schemas/location_scan.py` (LocationScanRequest, TimeSummary, TimeSummaryFilters)
    - Create `core-service/app/api/v1/endpoints/worker_tasks.py` (POST, GET list, GET detail, POST start, POST complete, POST cancel)
    - Create `core-service/app/api/v1/endpoints/location_scans.py` (POST, GET summary)
    - Register routers
    - _Requirements: 16.6, 17.6_

- [x] 13. Scan Event Audit Trail

  - [x] 13.1 Implement ScanEventService

    - Create `core-service/app/services/scan_event_service.py`
    - Implement `record_event` storing scan in existing qr_scan_events table with context in extra_data (scan_context, session_id, pick_list_id, decoded_payload, device_type, os)
    - Implement `query_events` with filters (session_id, worker_id, date range, scan_context)
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [ ]\* 13.2 Write property test for scan event audit completeness

    - **Property 25: Scan Event Audit Completeness**
    - **Validates: Requirements 14.1**

  - [x] 13.3 Create Pydantic schemas and API endpoint for scan events
    - Create `core-service/app/schemas/scan_event.py` (ScanEventCreate, ScanEventFilters, PaginatedScanEvents)
    - Create `core-service/app/api/v1/endpoints/scan_events.py` (GET /scan-events with filters)
    - Register router
    - _Requirements: 14.3_

- [x] 14. Integration wiring and remaining property tests

  - [x] 14.1 Wire put-away generation into receiving slip approval flow

    - In InboundService.approve_slip: trigger PutAwayService.generate_from_slip
    - In PutAwayService.generate_from_slip: create worker task via TaskService
    - Ensure put-away list generation respects allocations and routes items
    - _Requirements: 7.3, 8.1_

  - [ ]\* 14.2 Write property test for approval triggers put-away generation

    - **Property 14: Approval Triggers Put-Away Generation**
    - **Validates: Requirements 7.3, 8.1**

  - [x] 14.3 Wire pick list creation into SAP invoice webhook

    - In PickListService.create_from_invoice: resolve bins, optimize route, create worker task
    - Ensure pick list items have bin_location_id and sort_order set
    - _Requirements: 9.3, 9.4_

  - [x] 14.4 Wire gate verification into dispatch creation

    - In GateVerificationService.verify_session: call OutboundService.create_dispatch
    - Ensure stock deduction and dispatch number generation happen atomically
    - _Requirements: 12.6, 13.1, 13.4, 13.5_

  - [ ]\* 14.5 Write property test for location filter accuracy

    - **Property 31: Location Filter Accuracy**
    - **Validates: Requirements 19.1, 19.2, 19.3**

  - [ ]\* 14.6 Write property test for location search correctness

    - **Property 32: Location Search Correctness**
    - **Validates: Requirements 19.4**

  - [ ]\* 14.7 Write property test for put-away completion updates stock and slip status
    - **Property 17: Put-Away Completion Updates Stock and Slip Status**
    - **Validates: Requirements 8.5, 8.6**

- [-] 15. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document using Hypothesis
- Unit tests validate specific examples and edge cases
- All services follow the existing project pattern: Repository → Service → API endpoint
- Existing tables (pick_lists, pick_list_items, put_away_list_items, qr_scan_events, stock_levels) are extended rather than replaced
- Optimistic locking via version column on warehouse_locations prevents concurrent capacity conflicts

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3", "1.4", "1.5", "1.6", "1.7"] },
    { "id": 1, "tasks": ["1.8"] },
    { "id": 2, "tasks": ["3.1", "3.4", "3.7", "3.8"] },
    { "id": 3, "tasks": ["3.2", "3.3", "3.5", "3.6", "3.9"] },
    { "id": 4, "tasks": ["4.1", "4.6"] },
    { "id": 5, "tasks": ["4.2", "4.3", "4.4", "4.5", "4.7", "4.8"] },
    { "id": 6, "tasks": ["6.1", "6.10"] },
    { "id": 7, "tasks": ["6.2", "6.3", "6.4"] },
    { "id": 8, "tasks": ["6.5", "6.6", "6.7"] },
    { "id": 9, "tasks": ["6.8", "6.9", "7.1"] },
    { "id": 10, "tasks": ["7.2", "7.3"] },
    { "id": 11, "tasks": ["7.4", "7.5", "7.6", "7.7"] },
    { "id": 12, "tasks": ["9.1"] },
    { "id": 13, "tasks": ["9.2", "9.3", "9.4"] },
    { "id": 14, "tasks": ["9.5", "9.6", "9.7", "9.8"] },
    { "id": 15, "tasks": ["10.1", "10.3"] },
    { "id": 16, "tasks": ["10.2", "10.4", "10.5"] },
    { "id": 17, "tasks": ["12.1", "12.2"] },
    { "id": 18, "tasks": ["12.3", "12.4", "13.1"] },
    { "id": 19, "tasks": ["13.2", "13.3"] },
    { "id": 20, "tasks": ["14.1", "14.3", "14.4"] },
    { "id": 21, "tasks": ["14.2", "14.5", "14.6", "14.7"] }
  ]
}
```
