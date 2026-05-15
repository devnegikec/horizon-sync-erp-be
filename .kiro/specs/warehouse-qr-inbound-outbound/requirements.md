# Requirements Document: Warehouse QR-Based Inbound/Outbound Workflow

## Introduction

This document specifies the requirements for a QR code-driven warehouse inbound and outbound workflow system. The system enables workers to scan QR codes on boxes/items during receiving (inbound) to create receiving slips, generate optimized put-away lists, and during dispatch (outbound) to fulfill pick lists triggered by SAP sales invoices and verify items at the security gate before vehicle loading.

QR codes are self-contained with embedded payload (SKU, quantity, batch number) and work offline. The system integrates with the existing warehouse bin management hierarchy, pick list infrastructure, purchase receipt model, and QR scan event tracking.

## Glossary

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

## Requirements

### Requirement 1: QR Code Scanning and Payload Extraction

**User Story:** As a dock worker, I want to scan a QR code on a box and have the system automatically extract the SKU, quantity, and batch information, so that I do not need to manually enter item details.

#### Acceptance Criteria

1. WHEN a QR code is scanned, THE Inbound_Service SHALL decode the QR_Payload and extract the SKU identifier, item quantity, and batch number
2. IF the QR_Payload does not contain a valid SKU identifier, THEN THE Inbound_Service SHALL reject the scan and return an error indicating the missing field
3. IF the QR_Payload does not contain a valid quantity (positive integer), THEN THE Inbound_Service SHALL reject the scan and return an error indicating an invalid quantity
4. WHEN a QR code is scanned, THE Inbound_Service SHALL record a scan event with the worker ID, timestamp, location, and decoded payload data
5. THE Inbound_Service SHALL support scanning QR codes without network connectivity by storing scan data locally and syncing when connectivity is restored

### Requirement 2: Inbound Scan Session Management

**User Story:** As a dock worker, I want to start a scan session when unloading begins and scan all boxes sequentially, so that the system groups all scans into a single receiving operation.

#### Acceptance Criteria

1. WHEN a dock worker initiates an inbound session, THE Inbound_Service SHALL create a Scan_Session record with status OPEN, the worker ID, warehouse ID, dock location, and start timestamp
2. WHILE a Scan_Session is OPEN, THE Inbound_Service SHALL associate each subsequent QR scan with that session
3. WHEN a QR code is scanned within a session, THE Inbound_Service SHALL aggregate the item quantity by SKU and batch number within the session
4. IF the same QR code is scanned twice within the same session, THEN THE Inbound_Service SHALL reject the duplicate scan and return a warning indicating the box was already scanned
5. WHEN a dock worker ends the session, THE Inbound_Service SHALL set the session status to CLOSED and record the end timestamp
6. THE Inbound_Service SHALL provide a real-time count of total boxes scanned and total item quantities per SKU within the active session

### Requirement 3: Receiving Slip Generation

**User Story:** As a dock worker, I want the system to generate a receiving slip from my completed scan session, so that I have a formal record of what arrived at the warehouse.

#### Acceptance Criteria

1. WHEN a Scan_Session is closed, THE Inbound_Service SHALL generate a Receiving_Slip containing all scanned items grouped by SKU and batch number
2. THE Inbound_Service SHALL assign a unique receiving slip number following the organization's document numbering sequence
3. WHEN a Receiving_Slip is generated, THE Inbound_Service SHALL create a corresponding purchase receipt record with line items matching the scanned quantities
4. THE Inbound_Service SHALL record the total box count, total item count, and per-SKU breakdown on the Receiving_Slip
5. WHEN a Receiving_Slip is generated, THE Inbound_Service SHALL set the slip status to PENDING_PUTAWAY
6. THE Inbound_Service SHALL store the raw QR scan data as an audit trail linked to the Receiving_Slip

### Requirement 4: Put-Away List Generation from Receiving Slip

**User Story:** As a warehouse manager, I want the system to automatically generate a put-away list grouped by warehouse position when a receiving slip is created, so that workers can efficiently store items with minimal travel.

#### Acceptance Criteria

1. WHEN a Receiving_Slip status is set to PENDING_PUTAWAY, THE Put_Away_Service SHALL generate a put-away list assigning each received item to target bin locations
2. WHEN assigning bin locations, THE Put_Away_Service SHALL consider existing put-away rules, item-group allocations, and available bin capacity
3. WHEN a put-away list is generated, THE Put_Away_Service SHALL group items by their target zone and aisle to minimize worker travel distance
4. WHEN a put-away list is generated, THE Put_Away_Service SHALL sort items within each group by optimal traversal order using bin position coordinates
5. WHEN a put-away item is completed (worker scans at the bin), THE Put_Away_Service SHALL update the bin stock level and mark the put-away item as COMPLETED
6. WHEN all put-away items are completed, THE Put_Away_Service SHALL update the Receiving_Slip status to PUTAWAY_COMPLETE

### Requirement 5: SAP Invoice-Triggered Pick List Generation

**User Story:** As a warehouse manager, I want the system to automatically generate a pick list when a sales invoice is received from SAP, so that outbound fulfillment begins immediately without manual intervention.

#### Acceptance Criteria

1. WHEN a SAP_Invoice is received, THE Pick_List_Service SHALL create a new pick list with status OPEN and link it to the invoice reference
2. WHEN a pick list is created from a SAP_Invoice, THE Pick_List_Service SHALL populate pick list items with the SKUs and quantities specified in the invoice
3. WHEN pick list items are created, THE Pick_List_Service SHALL resolve each item to specific bin locations based on available bin-level stock using FIFO (first-in, first-out) logic
4. WHEN bin locations are resolved, THE Pick_List_Service SHALL sort pick list items by optimal traversal order to minimize worker travel distance
5. THE Pick_List_Service SHALL set the pick list warehouse based on the invoice delivery warehouse or the default outbound warehouse

### Requirement 6: Pick List Fulfillment via QR Scanning

**User Story:** As a picker, I want to scan boxes or items to add them to an open pick list, so that I can fulfill the pick list accurately and the system tracks what has been picked.

#### Acceptance Criteria

1. WHILE a pick list has status OPEN, THE Pick_List_Service SHALL allow workers to scan QR codes to record picked items
2. WHEN a QR code is scanned against a pick list, THE Pick_List_Service SHALL match the scanned SKU and quantity against the pick list items
3. WHEN a scanned item matches a pick list item, THE Pick_List_Service SHALL increment the picked_qty for that item
4. IF a scanned item does not match any pending pick list item, THEN THE Pick_List_Service SHALL reject the scan and return an error indicating the item is not on the pick list
5. IF the scanned quantity would exceed the required quantity for a pick list item, THEN THE Pick_List_Service SHALL reject the scan and return an error indicating over-picking
6. WHEN all pick list items have picked_qty equal to the required qty, THE Pick_List_Service SHALL allow the user to mark the pick list as COMPLETED
7. WHEN a pick list is marked as COMPLETED, THE Pick_List_Service SHALL update the pick list status and record the completion timestamp

### Requirement 7: Gate Verification and Vehicle Loading

**User Story:** As gate security, I want to scan items at the gate and associate them with a vehicle, so that I can verify all dispatched items are accounted for before the vehicle departs.

#### Acceptance Criteria

1. WHEN a security person initiates a gate verification session, THE Gate_Verification_Service SHALL create a session record with the vehicle number, driver details, and associated pick list reference
2. WHILE a gate verification session is OPEN, THE Gate_Verification_Service SHALL allow scanning of QR codes on boxes or items
3. WHEN a QR code is scanned at the gate, THE Gate_Verification_Service SHALL validate that the scanned item belongs to the associated completed pick list
4. IF a scanned item does not belong to the associated pick list, THEN THE Gate_Verification_Service SHALL flag the item as UNAUTHORIZED and alert the security person
5. WHEN all items from the pick list are scanned at the gate, THE Gate_Verification_Service SHALL mark the gate session as VERIFIED
6. WHEN a gate session is marked as VERIFIED, THE Gate_Verification_Service SHALL record the vehicle departure timestamp and create a dispatch record linking the pick list, vehicle, and scanned items
7. THE Gate_Verification_Service SHALL provide a real-time count of scanned items versus expected items from the pick list

### Requirement 8: Scan Event Audit Trail

**User Story:** As a warehouse manager, I want every QR scan to be recorded with full context (who, when, where, what), so that I have a complete audit trail for compliance and dispute resolution.

#### Acceptance Criteria

1. WHEN any QR code is scanned (inbound, pick, or gate), THE System SHALL create a scan event record with: worker ID, scan timestamp, scan location, session ID, scan context (inbound/pick/gate), and decoded QR payload
2. THE System SHALL store scan events in the existing qr_scan_events infrastructure with appropriate context in the extra_data field
3. THE System SHALL provide an endpoint to query scan events filtered by session ID, worker ID, date range, and scan context
4. WHEN a scan event is created, THE System SHALL record the device information (device type, OS) when available
5. THE System SHALL retain scan event records for a minimum of 12 months

### Requirement 9: Receiving Slip Validation

**User Story:** As a warehouse manager, I want to review the receiving slip and confirm that all expected items have arrived safely, so that I can identify shortages or damages before accepting the shipment.

#### Acceptance Criteria

1. WHEN a Receiving_Slip is generated, THE Inbound_Service SHALL set the slip to PENDING_REVIEW status before proceeding to put-away
2. THE Inbound_Service SHALL provide an endpoint to retrieve the Receiving_Slip with a full breakdown of scanned items, quantities, and batch numbers
3. WHEN a warehouse manager approves the Receiving_Slip, THE Inbound_Service SHALL transition the status to PENDING_PUTAWAY and trigger put-away list generation
4. WHEN a warehouse manager rejects the Receiving_Slip, THE Inbound_Service SHALL transition the status to REJECTED and record the rejection reason
5. IF a warehouse manager identifies a discrepancy, THEN THE Inbound_Service SHALL allow adding notes or flagging specific line items as SHORT or DAMAGED

### Requirement 10: Pick List Status Tracking

**User Story:** As a warehouse manager, I want to see the real-time status of all pick lists including how many items have been picked, so that I can monitor outbound progress and identify delays.

#### Acceptance Criteria

1. THE Pick_List_Service SHALL support pick list statuses: OPEN, IN_PROGRESS, COMPLETED, CANCELLED
2. WHEN the first item is scanned against an OPEN pick list, THE Pick_List_Service SHALL transition the status to IN_PROGRESS
3. THE Pick_List_Service SHALL provide an endpoint to list all pick lists filtered by status, date range, and invoice reference
4. THE Pick_List_Service SHALL include progress information (total items, picked items, remaining items) in the pick list response
5. WHEN a pick list is CANCELLED, THE Pick_List_Service SHALL release any reserved stock back to available inventory

### Requirement 11: Dispatch Record and Outbound Completion

**User Story:** As a warehouse manager, I want a complete dispatch record linking the invoice, pick list, gate verification, and vehicle details, so that I have end-to-end traceability for every outbound shipment.

#### Acceptance Criteria

1. WHEN a gate verification session is marked as VERIFIED, THE Outbound_Service SHALL create a dispatch record containing: pick list ID, invoice reference, vehicle number, driver name, gate session ID, and dispatch timestamp
2. THE Outbound_Service SHALL update the pick list with a reference to the dispatch record
3. THE Outbound_Service SHALL provide an endpoint to retrieve dispatch records filtered by date range, vehicle number, and invoice reference
4. WHEN a dispatch record is created, THE Outbound_Service SHALL decrement the warehouse stock levels for all dispatched items
5. THE Outbound_Service SHALL generate a unique dispatch number following the organization's document numbering sequence
