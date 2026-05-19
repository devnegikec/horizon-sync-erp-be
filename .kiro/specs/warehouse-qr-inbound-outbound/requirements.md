# Requirements Document

## Introduction

This document specifies the unified requirements for a warehouse management system combining physical layout hierarchy, bin-level stock tracking, QR code-driven inbound/outbound workflows, worker task tracking, and capacity management. The system enables workers to scan QR codes on boxes/items during receiving (inbound) to create receiving slips, generate optimized put-away lists grouped by zone and aisle, and during dispatch (outbound) to fulfill pick lists triggered by SAP sales invoices using FIFO bin resolution, and verify items at the security gate before vehicle loading.

The system supports a full warehouse layout hierarchy (Zone → Aisle → Bay → Level → Bin), bin-level stock tracking with capacity rollup, optimized routing for put-away and pick operations, worker task assignment with QR scan-based time measurement, and a complete audit trail for all scan events.

QR codes are self-contained with embedded payload (SKU, quantity, batch number) and work offline. The system integrates with the existing warehouse infrastructure, purchase receipt model, SAP invoice integration, and QR scan event tracking. Built as a Python FastAPI backend with PostgreSQL.

## Glossary

- **Warehouse_Layout**: The physical hierarchy of a warehouse: Zone → Aisle → Bay → Level → Bin
- **Zone**: Top-level subdivision of a warehouse (e.g., Receiving, Bulk Storage, Cold Storage)
- **Aisle**: A corridor within a zone containing bays on either side
- **Bay**: A vertical section within an aisle (a shelving unit or rack)
- **Level**: A horizontal shelf within a bay (numbered bottom to top)
- **Bin**: The smallest addressable storage location within a level; holds physical items
- **Bin_Location**: A structured address code identifying a bin (e.g., Z01-A03-B02-L04-B01)
- **Capacity_Rollup**: The process of computing a parent location's total capacity as the sum of all its children's capacities
- **Bin_Stock_Level**: The quantity of a specific item currently stored in a specific bin
- **Available_Capacity**: The remaining storage capacity of a bin, level, bay, aisle, zone, or warehouse
- **Location_Allocation**: A reservation of a specific location (bin, level, or bay) for a particular item group
- **Fast_Moving_Item**: An item with high turnover that should be placed in easily accessible locations
- **Slow_Moving_Item**: An item with low turnover that can be placed in less accessible locations
- **Inbound_Service**: The service responsible for processing goods arriving at the warehouse dock
- **QR_Payload**: The self-contained data embedded in a box/item QR code containing SKU, quantity, and batch number
- **Receiving_Slip**: A document created from scanned QR data that records what items arrived at the warehouse
- **Put_Away_Service**: The service that generates grouped put-away assignments based on warehouse bin positions
- **Outbound_Service**: The service responsible for processing goods leaving the warehouse
- **Pick_List_Service**: The service that generates and manages pick lists triggered by SAP sales invoices
- **Gate_Verification_Service**: The service used by security personnel to scan and verify items being loaded onto vehicles
- **Scan_Session**: A time-bounded grouping of QR scans performed by a worker during a single inbound or outbound operation
- **Box_QR**: A QR code affixed to a box containing embedded SKU, quantity, and batch information
- **SAP_Invoice**: A sales invoice received from SAP that triggers outbound pick list generation
- **Vehicle_Loading**: The process of scanning items at the gate and associating them with a departing vehicle
- **Dock_Worker**: A warehouse worker who scans boxes during inbound receiving at the dock
- **Picker**: A warehouse worker who scans items to fulfill a pick list during outbound operations
- **Gate_Security**: Security personnel who verify items at the gate before vehicle departure
- **Routing_Optimizer**: The service that determines the optimal sequence of bin visits to minimize worker travel time
- **Worker_Task**: A trackable unit of work (put-away or pick) assigned to a warehouse worker
- **QR_Location_Code**: A QR code physically affixed at a bin or aisle location that workers scan to record start/finish of tasks
- **Task_Timer**: The mechanism that records elapsed time between a worker's start-scan and finish-scan at locations
- **Layout_Service**: The service responsible for managing the warehouse location hierarchy
- **Capacity_Service**: The service responsible for computing and maintaining capacity rollups
- **Bin_Stock_Service**: The service responsible for tracking stock at the bin level
- **Task_Service**: The service responsible for managing worker task assignments
- **QR_Scan_Service**: The service responsible for recording QR location scans for time tracking
- **Allocation_Service**: The service responsible for managing location-to-item-group allocations

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

### Requirement 4: QR Code Scanning and Payload Extraction

**User Story:** As a dock worker, I want to scan a QR code on a box and have the system automatically extract the SKU, quantity, and batch information, so that I do not need to manually enter item details.

#### Acceptance Criteria

1. WHEN a QR code is scanned, THE Inbound_Service SHALL decode the QR_Payload and extract the SKU identifier, item quantity, and batch number
2. IF the QR_Payload does not contain a valid SKU identifier, THEN THE Inbound_Service SHALL reject the scan and return an error indicating the missing field
3. IF the QR_Payload does not contain a valid quantity (positive integer), THEN THE Inbound_Service SHALL reject the scan and return an error indicating an invalid quantity
4. WHEN a QR code is scanned, THE Inbound_Service SHALL record a scan event with the worker ID, timestamp, location, and decoded payload data
5. THE Inbound_Service SHALL support scanning QR codes without network connectivity by storing scan data locally and syncing when connectivity is restored

### Requirement 5: Inbound Scan Session Management

**User Story:** As a dock worker, I want to start a scan session when unloading begins and scan all boxes sequentially, so that the system groups all scans into a single receiving operation.

#### Acceptance Criteria

1. WHEN a dock worker initiates an inbound session, THE Inbound_Service SHALL create a Scan_Session record with status OPEN, the worker ID, warehouse ID, dock location, and start timestamp
2. WHILE a Scan_Session is OPEN, THE Inbound_Service SHALL associate each subsequent QR scan with that session
3. WHEN a QR code is scanned within a session, THE Inbound_Service SHALL aggregate the item quantity by SKU and batch number within the session
4. IF the same QR code is scanned twice within the same session, THEN THE Inbound_Service SHALL reject the duplicate scan and return a warning indicating the box was already scanned
5. WHEN a dock worker ends the session, THE Inbound_Service SHALL set the session status to CLOSED and record the end timestamp
6. THE Inbound_Service SHALL provide a real-time count of total boxes scanned and total item quantities per SKU within the active session

### Requirement 6: Receiving Slip Generation

**User Story:** As a dock worker, I want the system to generate a receiving slip from my completed scan session, so that I have a formal record of what arrived at the warehouse.

#### Acceptance Criteria

1. WHEN a Scan_Session is closed, THE Inbound_Service SHALL generate a Receiving_Slip containing all scanned items grouped by SKU and batch number
2. THE Inbound_Service SHALL assign a unique receiving slip number following the organization's document numbering sequence
3. WHEN a Receiving_Slip is generated, THE Inbound_Service SHALL create a corresponding purchase receipt record with line items matching the scanned quantities
4. THE Inbound_Service SHALL record the total box count, total item count, and per-SKU breakdown on the Receiving_Slip
5. WHEN a Receiving_Slip is generated, THE Inbound_Service SHALL set the slip status to PENDING_REVIEW
6. THE Inbound_Service SHALL store the raw QR scan data as an audit trail linked to the Receiving_Slip

### Requirement 7: Receiving Slip Validation

**User Story:** As a warehouse manager, I want to review the receiving slip and confirm that all expected items have arrived safely, so that I can identify shortages or damages before accepting the shipment.

#### Acceptance Criteria

1. WHEN a Receiving_Slip is generated, THE Inbound_Service SHALL set the slip to PENDING_REVIEW status before proceeding to put-away
2. THE Inbound_Service SHALL provide an endpoint to retrieve the Receiving_Slip with a full breakdown of scanned items, quantities, and batch numbers
3. WHEN a warehouse manager approves the Receiving_Slip, THE Inbound_Service SHALL transition the status to PENDING_PUTAWAY and trigger put-away list generation
4. WHEN a warehouse manager rejects the Receiving_Slip, THE Inbound_Service SHALL transition the status to REJECTED and record the rejection reason
5. IF a warehouse manager identifies a discrepancy, THEN THE Inbound_Service SHALL allow adding notes or flagging specific line items as SHORT or DAMAGED

### Requirement 8: Put-Away List Generation from Receiving Slip

**User Story:** As a warehouse manager, I want the system to automatically generate a put-away list grouped by warehouse position when a receiving slip is approved, so that workers can efficiently store items with minimal travel.

#### Acceptance Criteria

1. WHEN a Receiving_Slip status is set to PENDING_PUTAWAY, THE Put_Away_Service SHALL generate a put-away list assigning each received item to target bin locations
2. WHEN assigning bin locations, THE Put_Away_Service SHALL consider existing put-away rules, item-group allocations, and available bin capacity
3. WHEN a put-away list is generated, THE Put_Away_Service SHALL group items by their target zone and aisle to minimize worker travel distance
4. WHEN a put-away list is generated, THE Put_Away_Service SHALL sort items within each group by optimal traversal order using bin position coordinates
5. WHEN a put-away item is completed (worker scans at the bin), THE Put_Away_Service SHALL update the bin stock level and mark the put-away item as COMPLETED
6. WHEN all put-away items are completed, THE Put_Away_Service SHALL update the Receiving_Slip status to PUTAWAY_COMPLETE

### Requirement 9: SAP Invoice-Triggered Pick List Generation

**User Story:** As a warehouse manager, I want the system to automatically generate a pick list when a sales invoice is received from SAP, so that outbound fulfillment begins immediately without manual intervention.

#### Acceptance Criteria

1. WHEN a SAP_Invoice is received, THE Pick_List_Service SHALL create a new pick list with status OPEN and link it to the invoice reference
2. WHEN a pick list is created from a SAP_Invoice, THE Pick_List_Service SHALL populate pick list items with the SKUs and quantities specified in the invoice
3. WHEN pick list items are created, THE Pick_List_Service SHALL resolve each item to specific bin locations based on available bin-level stock using FIFO (first-in, first-out) logic
4. WHEN bin locations are resolved, THE Pick_List_Service SHALL sort pick list items by optimal traversal order to minimize worker travel distance
5. THE Pick_List_Service SHALL set the pick list warehouse based on the invoice delivery warehouse or the default outbound warehouse

### Requirement 10: Pick List Fulfillment via QR Scanning

**User Story:** As a picker, I want to scan boxes or items to add them to an open pick list, so that I can fulfill the pick list accurately and the system tracks what has been picked.

#### Acceptance Criteria

1. WHILE a pick list has status OPEN or IN_PROGRESS, THE Pick_List_Service SHALL allow workers to scan QR codes to record picked items
2. WHEN a QR code is scanned against a pick list, THE Pick_List_Service SHALL match the scanned SKU and quantity against the pick list items
3. WHEN a scanned item matches a pick list item, THE Pick_List_Service SHALL increment the picked_qty for that item
4. IF a scanned item does not match any pending pick list item, THEN THE Pick_List_Service SHALL reject the scan and return an error indicating the item is not on the pick list
5. IF the scanned quantity would exceed the required quantity for a pick list item, THEN THE Pick_List_Service SHALL reject the scan and return an error indicating over-picking
6. WHEN all pick list items have picked_qty equal to the required qty, THE Pick_List_Service SHALL allow the user to mark the pick list as COMPLETED
7. WHEN a pick list is marked as COMPLETED, THE Pick_List_Service SHALL update the pick list status and record the completion timestamp

### Requirement 11: Pick List Status Tracking

**User Story:** As a warehouse manager, I want to see the real-time status of all pick lists including how many items have been picked, so that I can monitor outbound progress and identify delays.

#### Acceptance Criteria

1. THE Pick_List_Service SHALL support pick list statuses: OPEN, IN_PROGRESS, COMPLETED, CANCELLED
2. WHEN the first item is scanned against an OPEN pick list, THE Pick_List_Service SHALL transition the status to IN_PROGRESS
3. THE Pick_List_Service SHALL provide an endpoint to list all pick lists filtered by status, date range, and invoice reference
4. THE Pick_List_Service SHALL include progress information (total items, picked items, remaining items) in the pick list response
5. WHEN a pick list is CANCELLED, THE Pick_List_Service SHALL release any reserved stock back to available inventory

### Requirement 12: Gate Verification and Vehicle Loading

**User Story:** As gate security, I want to scan items at the gate and associate them with a vehicle, so that I can verify all dispatched items are accounted for before the vehicle departs.

#### Acceptance Criteria

1. WHEN a security person initiates a gate verification session, THE Gate_Verification_Service SHALL create a session record with the vehicle number, driver details, and associated pick list reference
2. WHILE a gate verification session is OPEN, THE Gate_Verification_Service SHALL allow scanning of QR codes on boxes or items
3. WHEN a QR code is scanned at the gate, THE Gate_Verification_Service SHALL validate that the scanned item belongs to the associated completed pick list
4. IF a scanned item does not belong to the associated pick list, THEN THE Gate_Verification_Service SHALL flag the item as UNAUTHORIZED and alert the security person
5. WHEN all items from the pick list are scanned at the gate, THE Gate_Verification_Service SHALL mark the gate session as VERIFIED
6. WHEN a gate session is marked as VERIFIED, THE Gate_Verification_Service SHALL record the vehicle departure timestamp and create a dispatch record linking the pick list, vehicle, and scanned items
7. THE Gate_Verification_Service SHALL provide a real-time count of scanned items versus expected items from the pick list

### Requirement 13: Dispatch Record and Outbound Completion

**User Story:** As a warehouse manager, I want a complete dispatch record linking the invoice, pick list, gate verification, and vehicle details, so that I have end-to-end traceability for every outbound shipment.

#### Acceptance Criteria

1. WHEN a gate verification session is marked as VERIFIED, THE Outbound_Service SHALL create a dispatch record containing: pick list ID, invoice reference, vehicle number, driver name, gate session ID, and dispatch timestamp
2. THE Outbound_Service SHALL update the pick list with a reference to the dispatch record
3. THE Outbound_Service SHALL provide an endpoint to retrieve dispatch records filtered by date range, vehicle number, and invoice reference
4. WHEN a dispatch record is created, THE Outbound_Service SHALL decrement the warehouse stock levels for all dispatched items
5. THE Outbound_Service SHALL generate a unique dispatch number following the organization's document numbering sequence

### Requirement 14: Scan Event Audit Trail

**User Story:** As a warehouse manager, I want every QR scan to be recorded with full context (who, when, where, what), so that I have a complete audit trail for compliance and dispute resolution.

#### Acceptance Criteria

1. WHEN any QR code is scanned (inbound, pick, or gate), THE System SHALL create a scan event record with: worker ID, scan timestamp, scan location, session ID, scan context (inbound/pick/gate), and decoded QR payload
2. THE System SHALL store scan events in the existing qr_scan_events infrastructure with appropriate context in the extra_data field
3. THE System SHALL provide an endpoint to query scan events filtered by session ID, worker ID, date range, and scan context
4. WHEN a scan event is created, THE System SHALL record the device information (device type, OS) when available
5. THE System SHALL retain scan event records for a minimum of 12 months

### Requirement 15: Routing Optimization

**User Story:** As a warehouse manager, I want the system to calculate the shortest path through bin locations for both put-away and pick operations, so that workers spend minimal time traveling.

#### Acceptance Criteria

1. THE Routing_Optimizer SHALL accept a list of bin locations with their position coordinates (position_x, position_y) and return them sorted by optimal traversal order
2. THE Routing_Optimizer SHALL use a nearest-neighbor heuristic starting from a configurable origin point (e.g., the receiving dock or packing station)
3. WHEN two bins are in the same aisle, THE Routing_Optimizer SHALL group them together to avoid unnecessary aisle changes
4. THE Routing_Optimizer SHALL assign a sort_order integer to each location in the optimized sequence
5. WHEN the origin point is not configured, THE Routing_Optimizer SHALL default to position (0, 0) as the starting point

### Requirement 16: Worker Task Assignment and Tracking

**User Story:** As a warehouse supervisor, I want to assign put-away and pick tasks to specific workers and track their progress, so that I can monitor productivity and identify bottlenecks.

#### Acceptance Criteria

1. THE Task_Service SHALL create a worker_task record when a put-away list or pick list is assigned to a worker
2. WHEN a worker_task is created, THE Task_Service SHALL record: task_type (put_away or pick), worker_id, reference_id (put_away_list_id or pick_list_id), status, assigned_at
3. THE Task_Service SHALL support task statuses: ASSIGNED, IN_PROGRESS, COMPLETED, CANCELLED
4. WHEN a worker starts a task, THE Task_Service SHALL set status to IN_PROGRESS and record started_at timestamp
5. WHEN a worker completes all items in a task, THE Task_Service SHALL set status to COMPLETED and record completed_at timestamp
6. THE Task_Service SHALL provide an endpoint to list all tasks for a specific worker filtered by status and date range

### Requirement 17: QR Code Location Scanning and Time Tracking

**User Story:** As a warehouse worker, I want to scan QR codes at bin locations to record when I start and finish each task step, so that my time is tracked accurately without manual entry.

#### Acceptance Criteria

1. THE QR_Scan_Service SHALL accept scan events containing: worker_id, task_id, location_code, scan_type (start or finish), and timestamp
2. WHEN a worker scans a start QR code at a location, THE QR_Scan_Service SHALL record the scan_timestamp as the task_item start time
3. WHEN a worker scans a finish QR code at a location, THE QR_Scan_Service SHALL record the scan_timestamp as the task_item end time and calculate elapsed_seconds
4. WHEN a finish scan is received without a preceding start scan for the same task_item, THE QR_Scan_Service SHALL return a validation error
5. THE QR_Scan_Service SHALL store scan records with: id, worker_task_id, task_item_id, location_code, scan_type, scanned_at, elapsed_seconds
6. THE QR_Scan_Service SHALL provide an endpoint to retrieve time tracking summaries per worker, per task, and per location for a given date range

### Requirement 18: Real-Time Capacity Updates

**User Story:** As a warehouse manager, I want bin and warehouse capacity to update immediately when workers add or pick items, so that capacity information is always current.

#### Acceptance Criteria

1. WHEN a put-away task item is marked as completed (item placed in bin), THE Bin_Stock_Service SHALL immediately increment the bin's quantity_on_hand
2. WHEN a pick task item is marked as completed (item removed from bin), THE Bin_Stock_Service SHALL immediately decrement the bin's quantity_on_hand
3. WHEN bin stock changes, THE Capacity_Service SHALL recalculate available_capacity for the bin and all ancestor locations up to the warehouse
4. WHEN capacity is recalculated, THE Capacity_Service SHALL update the available_capacity field on each affected location node within the same database transaction
5. IF a concurrent stock update causes a capacity conflict, THEN THE System SHALL use optimistic locking to detect the conflict and retry the operation

### Requirement 19: Location Filtering and Level-Based Views

**User Story:** As a warehouse manager, I want to filter and view the warehouse layout at any specific level of the hierarchy (zone, aisle, bay, level, or bin), so that I can inspect capacity, stock, and allocations for a particular section without navigating the full tree.

#### Acceptance Criteria

1. THE Layout_Service SHALL provide a list endpoint that accepts a location_type filter (zone, aisle, bay, level, bin) and returns all locations of that type within a warehouse
2. WHEN the location_type filter is applied, THE Layout_Service SHALL return each location with: id, code, name, full_path (ancestor codes concatenated), total_capacity, available_capacity, is_active, and item_count (number of distinct items stored)
3. THE Layout_Service SHALL support additional filters: parent_location_id (to scope within a specific parent), is_active, and has_stock (boolean to show only locations with stock > 0)
4. THE Layout_Service SHALL support a search parameter that matches against location code or name
5. WHEN a warehouse manager views a specific level (e.g., all bays in aisle A03), THE Layout_Service SHALL return a summary including: total bins within that subtree, occupied bins, total capacity, used capacity, and available capacity
6. THE Layout_Service SHALL support pagination for level-based views (page, page_size) to handle warehouses with large numbers of locations

### Requirement 20: Location Allocation for Item Groups

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
