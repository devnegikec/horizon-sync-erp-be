# Requirements Document: Warehouse Bin Management

## Introduction

This document specifies the requirements for extending the existing warehouse management system to support a full warehouse layout hierarchy (Zone → Aisle → Bay → Level → Bin), bin-level stock tracking, capacity rollup, optimized put-away and pick routing, and worker task tracking with QR scan-based time measurement.

The system currently uses a `warehouses_extended` table with parent-child relationships via `parent_warehouse_id` and tracks stock at the warehouse level via `stock_levels`. This feature extends granularity down to the bin level, introduces location-aware routing for put-away and pick operations, and adds worker time tracking through QR code scanning at physical locations.

## Glossary

- **Warehouse_Layout**: The physical hierarchy of a warehouse: Zone → Aisle → Bay → Level → Bin
- **Zone**: Top-level subdivision of a warehouse (e.g., Receiving, Bulk Storage, Cold Storage)
- **Aisle**: A corridor within a zone containing bays on either side
- **Bay**: A vertical section within an aisle (a shelving unit or rack)
- **Level**: A horizontal shelf within a bay (numbered bottom to top)
- **Bin**: The smallest addressable storage location within a level; holds physical items
- **Bin_Location**: A structured address code identifying a bin (e.g., Z01-A03-B02-L04-B01)
- **Capacity_Rollup**: The process of computing a parent location's total capacity as the sum of all its children's capacities
- **Put_Away_List**: An ordered list of bin assignments for incoming stock, optimized for minimal travel distance
- **Pick_List**: An ordered list of bin locations from which items must be retrieved, optimized for minimal travel distance
- **Routing_Optimizer**: The service that determines the optimal sequence of bin visits to minimize worker travel time
- **Worker_Task**: A trackable unit of work (put-away or pick) assigned to a warehouse worker
- **QR_Location_Code**: A QR code physically affixed at a bin or aisle location that workers scan to record start/finish of tasks
- **Task_Timer**: The mechanism that records elapsed time between a worker's start-scan and finish-scan at locations
- **Bin_Stock_Level**: The quantity of a specific item currently stored in a specific bin
- **Available_Capacity**: The remaining storage capacity of a bin, level, bay, aisle, zone, or warehouse
- **Location_Allocation**: A reservation of a specific location (bin, level, or bay) for a particular item group, ensuring that only items from that group are stored there
- **Fast_Moving_Item**: An item with high turnover that should be placed in easily accessible locations (near docks, lower levels)
- **Slow_Moving_Item**: An item with low turnover that can be placed in less accessible locations (higher levels, farther zones)

## Requirements

### Requirement 1: Warehouse Layout Hierarchy

**User Story:** As a warehouse manager, I want to define the physical layout of my warehouse as a hierarchy of zones, aisles, bays, levels, and bins, so that I can track exactly where items are stored.

#### Acceptance Criteria

1. THE Layout_Service SHALL support creating location nodes of types: zone, aisle, bay, level, and bin
2. WHEN a location node is created, THE Layout_Service SHALL enforce the parent-child hierarchy: warehouse → zone → aisle → bay → level → bin
3. WHEN a location node is created with an invalid parent type, THE Layout_Service SHALL return a validation error specifying the allowed parent type
4. WHEN a location node is created, THE Layout_Service SHALL generate a structured Bin_Location code by concatenating ancestor codes (e.g., Z01-A03-B02-L04-B01)
5. THE Layout_Service SHALL store each location node with fields: id, warehouse_id, parent_location_id, location_type, code, name, capacity, capacity_uom, position_x, position_y, is_active
6. WHEN a location node is deactivated, THE Layout_Service SHALL prevent new stock from being assigned to that location or any of its descendants
7. THE Layout_Service SHALL provide a tree endpoint that returns the full hierarchy for a given warehouse

### Requirement 2: Bin Capacity and Capacity Rollup

**User Story:** As a warehouse manager, I want the system to automatically calculate the total capacity of each level in the hierarchy based on its children, so that I always have an accurate picture of available space.

#### Acceptance Criteria

1. WHEN a bin's capacity is set or updated, THE Capacity_Service SHALL recalculate the capacity of all ancestor locations up to the warehouse level
2. THE Capacity_Service SHALL compute a parent location's total_capacity as the sum of all direct children's total_capacity values
3. WHEN a new bin is added to a level, THE Capacity_Service SHALL update the total_capacity of the level, bay, aisle, zone, and warehouse
4. WHEN a bin is removed or deactivated, THE Capacity_Service SHALL subtract that bin's capacity from all ancestor total_capacity values
5. THE Capacity_Service SHALL compute available_capacity for any location as total_capacity minus the sum of current stock quantities within that location's subtree
6. WHEN a warehouse has children (zones), THE Capacity_Service SHALL set the warehouse's total_capacity to the sum of all children's capacities rather than allowing manual override

### Requirement 3: Bin-Level Stock Tracking

**User Story:** As a warehouse operator, I want to track stock quantities at the bin level, so that I know exactly which bin contains which items and how much space remains.

#### Acceptance Criteria

1. THE Bin_Stock_Service SHALL maintain a bin_stock_levels record for each unique combination of item_id and bin_location_id
2. WHEN stock is added to a bin, THE Bin_Stock_Service SHALL increment the quantity_on_hand for that item in that bin
3. WHEN stock is removed from a bin, THE Bin_Stock_Service SHALL decrement the quantity_on_hand for that item in that bin
4. WHEN stock is added or removed from a bin, THE Bin_Stock_Service SHALL update the warehouse-level stock_levels record to maintain consistency
5. IF a stock addition would exceed the bin's remaining capacity, THEN THE Bin_Stock_Service SHALL reject the operation and return an error indicating the bin's available capacity
6. THE Bin_Stock_Service SHALL provide an endpoint to query all bins containing a specific item, with quantities and available capacity per bin

### Requirement 4: Put-Away List Generation

**User Story:** As a warehouse manager, I want the system to generate an optimized put-away list when new stock is received, so that workers know exactly which bins to use and in what order to minimize travel time.

#### Acceptance Criteria

1. WHEN a stock receipt is processed, THE Put_Away_Service SHALL generate a put-away list assigning each received item to one or more bins
2. WHEN assigning bins, THE Put_Away_Service SHALL consider existing put_away_rules (item-specific or item-group-specific warehouse/bin preferences, priority, min_qty, max_qty)
3. WHEN assigning bins, THE Put_Away_Service SHALL only select bins with sufficient available capacity for the assigned quantity
4. WHEN multiple bins are needed for a single item, THE Put_Away_Service SHALL split the quantity across bins respecting each bin's available capacity
5. WHEN a put-away list is generated, THE Routing_Optimizer SHALL sort the bin assignments in an order that minimizes total travel distance based on bin position coordinates
6. THE Put_Away_Service SHALL create a put_away_list record with status PENDING and individual put_away_list_items with bin assignments and sort_order

### Requirement 5: Pick List Optimization

**User Story:** As a warehouse manager, I want pick lists to include specific bin locations and be ordered to minimize worker travel time, so that order fulfillment is efficient.

#### Acceptance Criteria

1. WHEN a pick list is created, THE Pick_Service SHALL resolve each pick item to specific bin locations based on available bin-level stock
2. WHEN resolving bin locations for a pick item, THE Pick_Service SHALL prefer bins with the highest quantity of the requested item to minimize the number of bin visits
3. WHEN a single bin does not have sufficient quantity, THE Pick_Service SHALL split the pick across multiple bins
4. WHEN all bin locations are resolved, THE Routing_Optimizer SHALL sort pick_list_items in an order that minimizes total travel distance based on bin position coordinates
5. WHEN a pick list item is completed (picked), THE Bin_Stock_Service SHALL decrement the bin's quantity_on_hand and update the warehouse-level stock_levels
6. THE Pick_Service SHALL update the pick_list_items with the resolved bin_location_id and optimized sort_order

### Requirement 6: Routing Optimization

**User Story:** As a warehouse manager, I want the system to calculate the shortest path through bin locations for both put-away and pick operations, so that workers spend minimal time traveling.

#### Acceptance Criteria

1. THE Routing_Optimizer SHALL accept a list of bin locations with their position coordinates (position_x, position_y) and return them sorted by optimal traversal order
2. THE Routing_Optimizer SHALL use a nearest-neighbor heuristic starting from a configurable origin point (e.g., the receiving dock or packing station)
3. WHEN two bins are in the same aisle, THE Routing_Optimizer SHALL group them together to avoid unnecessary aisle changes
4. THE Routing_Optimizer SHALL assign a sort_order integer to each location in the optimized sequence
5. WHEN the origin point is not configured, THE Routing_Optimizer SHALL default to position (0, 0) as the starting point

### Requirement 7: Worker Task Assignment and Tracking

**User Story:** As a warehouse supervisor, I want to assign put-away and pick tasks to specific workers and track their progress, so that I can monitor productivity and identify bottlenecks.

#### Acceptance Criteria

1. THE Task_Service SHALL create a worker_task record when a put-away list or pick list is assigned to a worker
2. WHEN a worker_task is created, THE Task_Service SHALL record: task_type (put_away or pick), worker_id, reference_id (put_away_list_id or pick_list_id), status, assigned_at
3. THE Task_Service SHALL support task statuses: ASSIGNED, IN_PROGRESS, COMPLETED, CANCELLED
4. WHEN a worker starts a task, THE Task_Service SHALL set status to IN_PROGRESS and record started_at timestamp
5. WHEN a worker completes all items in a task, THE Task_Service SHALL set status to COMPLETED and record completed_at timestamp
6. THE Task_Service SHALL provide an endpoint to list all tasks for a specific worker filtered by status and date range

### Requirement 8: QR Code Location Scanning and Time Tracking

**User Story:** As a warehouse worker, I want to scan QR codes at bin locations to record when I start and finish each task step, so that my time is tracked accurately without manual entry.

#### Acceptance Criteria

1. THE QR_Scan_Service SHALL accept scan events containing: worker_id, task_id, location_code, scan_type (start or finish), and timestamp
2. WHEN a worker scans a start QR code at a location, THE QR_Scan_Service SHALL record the scan_timestamp as the task_item start time
3. WHEN a worker scans a finish QR code at a location, THE QR_Scan_Service SHALL record the scan_timestamp as the task_item end time and calculate elapsed_seconds
4. WHEN a finish scan is received without a preceding start scan for the same task_item, THE QR_Scan_Service SHALL return a validation error
5. THE QR_Scan_Service SHALL store scan records with: id, worker_task_id, task_item_id, location_code, scan_type, scanned_at, elapsed_seconds
6. THE QR_Scan_Service SHALL provide an endpoint to retrieve time tracking summaries per worker, per task, and per location for a given date range

### Requirement 9: Real-Time Capacity Updates

**User Story:** As a warehouse manager, I want bin and warehouse capacity to update immediately when workers add or pick items, so that capacity information is always current.

#### Acceptance Criteria

1. WHEN a put-away task item is marked as completed (item placed in bin), THE Bin_Stock_Service SHALL immediately increment the bin's quantity_on_hand
2. WHEN a pick task item is marked as completed (item removed from bin), THE Bin_Stock_Service SHALL immediately decrement the bin's quantity_on_hand
3. WHEN bin stock changes, THE Capacity_Service SHALL recalculate available_capacity for the bin and all ancestor locations up to the warehouse
4. WHEN capacity is recalculated, THE Capacity_Service SHALL update the available_capacity field on each affected location node within the same database transaction
5. IF a concurrent stock update causes a capacity conflict, THEN THE System SHALL use optimistic locking to detect the conflict and retry the operation

### Requirement 10: Put-Away and Pick List Status Management

**User Story:** As a warehouse supervisor, I want to track the status of put-away and pick lists as workers complete individual items, so that I can monitor overall progress.

#### Acceptance Criteria

1. THE System SHALL support put_away_list statuses: PENDING, IN_PROGRESS, COMPLETED, CANCELLED
2. WHEN the first item in a put-away list is completed, THE System SHALL transition the put_away_list status from PENDING to IN_PROGRESS
3. WHEN all items in a put-away list are completed, THE System SHALL transition the put_away_list status to COMPLETED
4. THE System SHALL support put_away_list_item statuses: PENDING, COMPLETED, SKIPPED
5. WHEN a put-away list item is marked as SKIPPED, THE System SHALL not update bin stock for that item and SHALL flag it for supervisor review
6. THE System SHALL apply the same status management pattern to pick lists and pick list items

### Requirement 11: Location Filtering and Level-Based Views

**User Story:** As a warehouse manager, I want to filter and view the warehouse layout at any specific level of the hierarchy (zone, aisle, bay, level, or bin), so that I can inspect capacity, stock, and allocations for a particular section without navigating the full tree.

#### Acceptance Criteria

1. THE Layout_Service SHALL provide a list endpoint that accepts a location_type filter (zone, aisle, bay, level, bin) and returns all locations of that type within a warehouse
2. WHEN the location_type filter is applied, THE Layout_Service SHALL return each location with: id, code, name, full_path (ancestor codes concatenated), total_capacity, available_capacity, is_active, and item_count (number of distinct items stored)
3. THE Layout_Service SHALL support additional filters: parent_location_id (to scope within a specific parent), is_active, and has_stock (boolean to show only locations with stock > 0)
4. THE Layout_Service SHALL support a search parameter that matches against location code or name
5. WHEN a warehouse manager views a specific level (e.g., all bays in aisle A03), THE Layout_Service SHALL return a summary including: total bins within that subtree, occupied bins, total capacity, used capacity, and available capacity
6. THE Layout_Service SHALL support pagination for level-based views (page, page_size) to handle warehouses with large numbers of locations

### Requirement 12: Location Allocation for Item Groups

**User Story:** As a warehouse manager, I want to allocate specific bins, levels, or bays to particular item groups, so that fast-moving items are stored in easily accessible locations and slow-moving items are placed in less accessible areas.

#### Acceptance Criteria

1. THE Allocation_Service SHALL support creating location_allocation records that link a location (bin, level, or bay) to an item_group_id
2. WHEN a location_allocation is created, THE Allocation_Service SHALL record: location_id, item_group_id, priority, allocation_type (exclusive or preferred), and is_active
3. WHEN allocation_type is "exclusive", THE Put_Away_Service SHALL only assign items from the allocated item group to that location and its descendants
4. WHEN allocation_type is "preferred", THE Put_Away_Service SHALL prioritize that location for items from the allocated group but allow other items if no allocated space is available
5. WHEN a put-away list is generated, THE Put_Away_Service SHALL check location_allocations first and assign items to their allocated locations before considering unallocated bins
6. WHEN a location has an exclusive allocation and a put-away attempts to assign an item from a different group, THE Put_Away_Service SHALL skip that location and select the next available bin
7. THE Allocation_Service SHALL provide an endpoint to list all allocations for a warehouse, filterable by item_group_id and location_type
8. THE Allocation_Service SHALL prevent overlapping exclusive allocations (the same location cannot be exclusively allocated to multiple item groups)
