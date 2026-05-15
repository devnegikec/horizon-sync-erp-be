# Implementation Plan: Warehouse QR-Based Inbound/Outbound Workflow

## Overview

Implement a QR code-driven warehouse inbound and outbound workflow on top of the existing warehouse bin management system. The implementation covers: scan sessions, receiving slips with review workflow, put-away list generation, SAP invoice-triggered pick lists with QR-based fulfillment, gate verification, dispatch records, and a unified scan event audit trail. All built with Python FastAPI, SQLAlchemy, PostgreSQL, and Alembic migrations.

## Tasks

- [ ] 1. Database models and migrations

  - [ ] 1.1 Create Alembic migration for new tables (scan_sessions, scan_session_items, receiving_slips, receiving_slip_items, gate_verification_sessions, gate_verification_items, dispatch_records) and ALTER existing tables (pick_lists, pick_list_items)

    - Add all columns, constraints, indexes as specified in the design
    - Add CHECK constraints for status and type enums
    - Add UNIQUE constraint on (session_id, qr_identifier) for scan_session_items
    - Add UNIQUE constraint on (gate_session_id, qr_identifier) for gate_verification_items
    - ALTER pick_lists: add invoice_reference, invoice_data, dispatch_record_id columns
    - ALTER pick_list_items: add picked_qty column with default 0
    - _Requirements: 2.1, 3.1, 7.1, 11.1_

  - [ ] 1.2 Create SQLAlchemy models for ScanSession, ScanSessionItem, ReceivingSlip, ReceivingSlipItem, GateVerificationSession, GateVerificationItem, DispatchRecord

    - Define enums: SessionType, SessionStatus, ReceivingSlipStatus, LineItemFlag, GateSessionStatus, GateItemStatus
    - Set up relationships (session ↔ items, slip ↔ items, gate_session ↔ items)
    - _Requirements: 2.1, 3.1, 7.1, 11.1_

  - [ ] 1.3 Update existing PickList and PickListItem models to include new columns (invoice_reference, invoice_data, dispatch_record_id, picked_qty)
    - _Requirements: 5.1, 6.3, 11.2_

- [ ] 2. Inbound service — scan sessions and QR decoding

  - [ ] 2.1 Implement QR payload decoding utility (decode_qr_payload)

    - Parse JSON payload extracting sku, quantity, batch_number, qr_identifier
    - Validate sku is present and non-empty
    - Validate quantity is a positive integer
    - Validate batch_number is present
    - Raise ValidationError with specific field messages on failure
    - _Requirements: 1.1, 1.2, 1.3_

  - [ ]\* 2.2 Write property test for QR payload round-trip

    - **Property 1: QR Payload Round-Trip**
    - **Validates: Requirements 1.1**

  - [ ]\* 2.3 Write property test for invalid quantity rejection

    - **Property 2: Invalid Quantity Rejection**
    - **Validates: Requirements 1.3**

  - [ ] 2.4 Implement InboundService.start_session

    - Create ScanSession with status OPEN, worker_id, warehouse_id, dock_location, organization_id
    - Record start timestamp
    - _Requirements: 2.1_

  - [ ] 2.5 Implement InboundService.record_scan

    - Decode QR payload
    - Check session is OPEN (reject if closed)
    - Check for duplicate qr_identifier in session (reject with warning)
    - Create ScanSessionItem record
    - Increment total_boxes_scanned on session
    - Record scan event via ScanEventService
    - _Requirements: 1.1, 1.4, 2.2, 2.3, 2.4_

  - [ ]\* 2.6 Write property test for duplicate scan rejection

    - **Property 3: Duplicate Scan Rejection**
    - **Validates: Requirements 2.4**

  - [ ]\* 2.7 Write property test for session aggregation correctness

    - **Property 4: Session Aggregation Correctness**
    - **Validates: Requirements 2.3, 2.6**

  - [ ] 2.8 Implement InboundService.end_session and get_session_summary
    - Set session status to CLOSED, record end timestamp
    - Generate receiving slip from session items (grouped by SKU + batch)
    - Return session summary with per-SKU counts
    - _Requirements: 2.5, 2.6, 3.1_

- [ ] 3. Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Receiving slip generation and review workflow

  - [ ] 4.1 Implement receiving slip generation logic

    - Group scan session items by (SKU, batch_number)
    - Create ReceivingSlip with slip_number (auto-generated), total_box_count, total_item_count
    - Create ReceivingSlipItem records for each group
    - Set status to PENDING_REVIEW
    - Store raw QR scan data as audit trail
    - _Requirements: 3.1, 3.2, 3.4, 3.5, 3.6_

  - [ ]\* 4.2 Write property test for receiving slip generation correctness

    - **Property 5: Receiving Slip Generation Correctness**
    - **Validates: Requirements 3.1, 3.4**

  - [ ] 4.3 Implement InboundService.approve_slip

    - Validate slip is in PENDING_REVIEW status
    - Transition to PENDING_PUTAWAY
    - Create corresponding purchase receipt record
    - Trigger put-away list generation via PutAwayService
    - _Requirements: 9.3, 3.3_

  - [ ]\* 4.4 Write property test for receiving slip to purchase receipt consistency

    - **Property 6: Receiving Slip to Purchase Receipt Consistency**
    - **Validates: Requirements 3.3**

  - [ ] 4.5 Implement InboundService.reject_slip

    - Validate slip is in PENDING_REVIEW status
    - Transition to REJECTED, record rejection reason
    - _Requirements: 9.4_

  - [ ] 4.6 Implement InboundService.flag_line_item

    - Allow flagging specific line items as SHORT or DAMAGED with notes
    - _Requirements: 9.5_

  - [ ]\* 4.7 Write property test for approval triggers put-away generation
    - **Property 17: Approval Triggers Put-Away Generation**
    - **Validates: Requirements 9.3**

- [ ] 5. Put-away list generation integration

  - [ ] 5.1 Implement put-away list generation from receiving slip

    - For each slip item, assign target bin locations using existing put-away rules and item-group allocations
    - Check available bin capacity
    - Group items by target zone/aisle for minimal travel
    - Sort within groups by bin position coordinates (optimal traversal)
    - Use existing PutAwayService and RoutingOptimizer
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [ ]\* 5.2 Write property test for put-away assignment completeness

    - **Property 7: Put-Away Assignment Completeness**
    - **Validates: Requirements 4.1, 4.2**

  - [ ]\* 5.3 Write property test for put-away routing grouping

    - **Property 8: Put-Away Routing Grouping**
    - **Validates: Requirements 4.3, 4.4**

  - [ ] 5.4 Implement put-away item completion handler

    - When worker scans at bin: update bin_stock_levels, mark put-away item COMPLETED
    - When all items completed: update receiving slip status to PUTAWAY_COMPLETE
    - _Requirements: 4.5, 4.6_

  - [ ]\* 5.5 Write property test for put-away completion updates stock
    - **Property 9: Put-Away Completion Updates Stock**
    - **Validates: Requirements 4.5, 4.6**

- [ ] 6. Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Outbound — SAP invoice-triggered pick list

  - [ ] 7.1 Implement PickListService.create_from_invoice

    - Parse SAP invoice payload (validate required fields)
    - Create pick list with status OPEN, link invoice_reference and invoice_data
    - Populate pick list items with SKUs and quantities from invoice
    - Set warehouse from invoice delivery warehouse or default
    - _Requirements: 5.1, 5.2, 5.5_

  - [ ]\* 7.2 Write property test for pick list creation from invoice

    - **Property 10: Pick List Creation from Invoice**
    - **Validates: Requirements 5.1, 5.2**

  - [ ] 7.3 Implement PickListService.resolve_bin_locations

    - For each pick list item, query bin_stock_levels ordered by created_at ASC (FIFO)
    - Allocate from oldest bins first, split across bins if needed
    - Sort resolved items by optimal traversal order using RoutingOptimizer
    - _Requirements: 5.3, 5.4_

  - [ ]\* 7.4 Write property test for FIFO bin resolution
    - **Property 11: FIFO Bin Resolution**
    - **Validates: Requirements 5.3**

- [ ] 8. Outbound — pick list fulfillment via QR scanning

  - [ ] 8.1 Implement PickListService.record_pick_scan

    - Decode QR payload
    - Validate pick list is OPEN or IN_PROGRESS
    - Match scanned SKU against pending pick list items (picked_qty < required_qty)
    - Reject if SKU not on list or would exceed required qty
    - Increment picked_qty on match
    - Transition OPEN → IN_PROGRESS on first scan
    - Record scan event for audit
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 10.2_

  - [ ]\* 8.2 Write property test for pick scanning correctness

    - **Property 12: Pick Scanning Correctness**
    - **Validates: Requirements 6.2, 6.3, 6.5**

  - [ ]\* 8.3 Write property test for pick list status transitions

    - **Property 13: Pick List Status Transitions**
    - **Validates: Requirements 6.6, 10.2**

  - [ ] 8.4 Implement PickListService.complete_pick_list

    - Validate all items have picked_qty == required_qty
    - Set status to COMPLETED, record completion timestamp
    - _Requirements: 6.6, 6.7_

  - [ ] 8.5 Implement PickListService.cancel_pick_list

    - Set status to CANCELLED
    - Release any reserved stock back to available inventory
    - _Requirements: 10.5_

  - [ ]\* 8.6 Write property test for stock release on pick list cancellation

    - **Property 18: Stock Release on Pick List Cancellation**
    - **Validates: Requirements 10.5**

  - [ ] 8.7 Implement PickListService.get_pick_list_progress and list_pick_lists
    - Return progress info (total items, picked items, remaining)
    - Support filtering by status, date range, invoice reference
    - _Requirements: 10.1, 10.3, 10.4_

- [ ] 9. Checkpoint - Ensure all tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Gate verification and dispatch

  - [ ] 10.1 Implement GateVerificationService.start_session

    - Create gate verification session with vehicle_number, driver details, pick_list_id
    - Validate pick list is COMPLETED
    - Set total_expected from pick list items
    - _Requirements: 7.1_

  - [ ] 10.2 Implement GateVerificationService.record_gate_scan

    - Decode QR payload
    - Validate session is OPEN
    - Check scanned SKU against associated pick list items
    - If match: create GateVerificationItem with status VERIFIED, increment total_verified
    - If no match: create GateVerificationItem with status UNAUTHORIZED, return alert
    - Record scan event for audit
    - _Requirements: 7.2, 7.3, 7.4_

  - [ ]\* 10.3 Write property test for gate verification against pick list

    - **Property 14: Gate Verification Against Pick List**
    - **Validates: Requirements 7.3, 7.4, 7.5**

  - [ ] 10.4 Implement GateVerificationService.verify_session

    - Validate all pick list items have been verified
    - Set session status to VERIFIED, record verified_at timestamp
    - Trigger dispatch record creation via OutboundService
    - _Requirements: 7.5, 7.6_

  - [ ] 10.5 Implement OutboundService.create_dispatch

    - Create dispatch record with pick_list_id, vehicle_number, driver, gate_session_id, dispatch timestamp
    - Generate unique dispatch number (DP-YYYY-NNNN)
    - Decrement warehouse stock_levels for all dispatched items
    - Create stock_movements records (type=OUT)
    - Update pick list with dispatch_record_id reference
    - _Requirements: 11.1, 11.2, 11.4, 11.5, 7.6_

  - [ ]\* 10.6 Write property test for dispatch record completeness and stock deduction

    - **Property 15: Dispatch Record Completeness and Stock Deduction**
    - **Validates: Requirements 7.6, 11.1, 11.4**

  - [ ] 10.7 Implement OutboundService.list_dispatches and get_dispatch
    - Support filtering by date range, vehicle number, invoice reference
    - _Requirements: 11.3_

- [ ] 11. Scan event audit trail

  - [ ] 11.1 Implement ScanEventService.record_event

    - Create qr_scan_events record with worker_id, timestamp, location, session_id, scan_context (inbound/pick/gate), decoded payload
    - Store device info in extra_data when available
    - _Requirements: 8.1, 8.2, 8.4_

  - [ ] 11.2 Implement ScanEventService.query_events

    - Support filtering by session_id, worker_id, date range, scan_context
    - _Requirements: 8.3_

  - [ ]\* 11.3 Write property test for scan event audit completeness
    - **Property 16: Scan Event Audit Completeness**
    - **Validates: Requirements 8.1**

- [ ] 12. API endpoints — Inbound

  - [ ] 12.1 Create inbound router with endpoints: POST /sessions, POST /sessions/{id}/scan, POST /sessions/{id}/end, GET /sessions/{id}

    - Wire to InboundService methods
    - Add request/response Pydantic schemas
    - _Requirements: 1.1, 2.1, 2.2, 2.5_

  - [ ] 12.2 Create receiving slip endpoints: GET /receiving-slips, GET /receiving-slips/{id}, POST /receiving-slips/{id}/approve, POST /receiving-slips/{id}/reject, PATCH /receiving-slips/{id}/items/{item_id}
    - Wire to InboundService methods
    - Add request/response Pydantic schemas
    - _Requirements: 3.1, 9.1, 9.2, 9.3, 9.4, 9.5_

- [ ] 13. API endpoints — Outbound

  - [ ] 13.1 Create pick list endpoints: POST /pick-lists/from-invoice, GET /pick-lists, GET /pick-lists/{id}, POST /pick-lists/{id}/scan, POST /pick-lists/{id}/complete, POST /pick-lists/{id}/cancel

    - Wire to PickListService methods
    - Add request/response Pydantic schemas
    - _Requirements: 5.1, 6.1, 6.6, 10.1, 10.3, 10.5_

  - [ ] 13.2 Create gate verification endpoints: POST /gate-sessions, POST /gate-sessions/{id}/scan, GET /gate-sessions/{id}, POST /gate-sessions/{id}/verify

    - Wire to GateVerificationService methods
    - Add request/response Pydantic schemas
    - _Requirements: 7.1, 7.2, 7.3, 7.5, 7.7_

  - [ ] 13.3 Create dispatch endpoints: GET /dispatches, GET /dispatches/{id}

    - Wire to OutboundService methods
    - Add request/response Pydantic schemas
    - _Requirements: 11.3_

  - [ ] 13.4 Create scan event endpoint: GET /scan-events
    - Wire to ScanEventService.query_events
    - Add request/response Pydantic schemas with filters
    - _Requirements: 8.3_

- [ ] 14. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design document
- Unit tests validate specific examples and edge cases
- The implementation reuses existing infrastructure: PutAwayService, RoutingOptimizer, BinStockService, qr_scan_events table, pick_lists/pick_list_items tables
- All services are org-scoped via organization_id from JWT
- Document numbering (receiving slip, dispatch) follows existing org naming series patterns

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3"] },
    { "id": 2, "tasks": ["2.1", "11.1"] },
    { "id": 3, "tasks": ["2.2", "2.3", "2.4", "11.2"] },
    { "id": 4, "tasks": ["2.5", "2.6", "2.7"] },
    { "id": 5, "tasks": ["2.8", "4.6"] },
    { "id": 6, "tasks": ["4.1", "4.2", "4.5"] },
    { "id": 7, "tasks": ["4.3", "4.4", "4.7"] },
    { "id": 8, "tasks": ["5.1", "7.1"] },
    { "id": 9, "tasks": ["5.2", "5.3", "5.4", "7.2", "7.3"] },
    { "id": 10, "tasks": ["5.5", "7.4", "8.1"] },
    { "id": 11, "tasks": ["8.2", "8.3", "8.4", "8.5", "8.7"] },
    { "id": 12, "tasks": ["8.6", "10.1"] },
    { "id": 13, "tasks": ["10.2", "10.3"] },
    { "id": 14, "tasks": ["10.4"] },
    { "id": 15, "tasks": ["10.5", "10.6", "10.7"] },
    { "id": 16, "tasks": ["11.3", "12.1", "12.2"] },
    { "id": 17, "tasks": ["13.1", "13.2", "13.3", "13.4"] }
  ]
}
```
