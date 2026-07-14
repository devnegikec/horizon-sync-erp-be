# Implementation Plan: Sourcing Flow (Procure-to-Pay)

## Overview

This implementation plan breaks down the sourcing flow feature into discrete coding tasks. The implementation will be done in Python, building new Material Request and RFQ APIs while integrating with existing Suppliers, Purchase Receipt, Invoice, and Payment APIs. The shared Transaction Engine will handle calculations for both purchase and sales documents.

## Tasks

- [x] 1. Set up project structure and database schema
  - Create database migration files for all new tables (material_requests, material_request_lines, rfqs, rfq_lines, rfq_suppliers, supplier_quotes, purchase_orders, purchase_order_lines, status_transitions)
  - Define SQLAlchemy models for all entities
  - Create indexes on status and foreign key columns
  - Set up Alembic for database migrations
  - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8_

- [x] 2. Implement Transaction Engine
  - [x] 2.1 Create Transaction Engine service class
    - Implement calculate() method accepting transaction_type, line_items, tax_rate, discount_amount
    - Calculate line_totals as quantity × unit_price for each line
    - Calculate subtotal as sum of line_totals
    - Calculate tax_amount as subtotal × tax_rate
    - Calculate grand_total as subtotal + tax_amount - discount_amount
    - Return TransactionEngineOutput with all calculated values
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
  
  - [ ]* 2.2 Write property tests for Transaction Engine
    - **Property 10: Line total calculation** - For any line item, line_total equals quantity × unit_price
    - **Property 11: Subtotal calculation** - For any set of line items, subtotal equals sum of line_totals
    - **Property 12: Tax calculation** - For any subtotal and tax_rate, tax_amount equals subtotal × tax_rate
    - **Property 13: Grand total calculation** - For any transaction, grand_total equals subtotal + tax_amount - discount_amount
    - **Property 14: Output completeness** - For any calculation, output contains all required fields
    - _Requirements: 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 3. Implement Material Request API
  - [x] 3.1 Create Material Request models and schemas
    - Define MaterialRequest and MaterialRequestLine SQLAlchemy models
    - Create Pydantic schemas for request/response validation
    - Implement status enum with values: DRAFT, SUBMITTED, PARTIALLY_QUOTED, FULLY_QUOTED, CANCELLED
    - _Requirements: 1.1, 1.5, 11.1, 11.2_
  
  - [x] 3.2 Implement Material Request service layer
    - Implement create() method with validation
    - Implement update() method (DRAFT only)
    - Implement submit() method with status transition
    - Implement cancel() method
    - Validate positive quantities and valid item references
    - Prevent modifications after submission
    - _Requirements: 1.1, 1.2, 1.3, 1.4_
  
  - [x] 3.3 Create Material Request API endpoints
    - POST /api/material-requests - Create new Material Request
    - GET /api/material-requests/:id - Retrieve Material Request
    - PUT /api/material-requests/:id - Update Material Request
    - DELETE /api/material-requests/:id - Delete Material Request
    - POST /api/material-requests/:id/submit - Submit Material Request
    - POST /api/material-requests/:id/cancel - Cancel Material Request
    - GET /api/material-requests - List with pagination
    - _Requirements: 10.1, 10.2, 10.6_
  
  - [ ]* 3.4 Write property tests for Material Request
    - **Property 1: Material Request initialization** - For any creation request, generate unique ID and set status to DRAFT
    - **Property 3: Positive quantity validation** - For any line item, quantity must be greater than zero
    - **Property 4: Document immutability** - For any submitted Material Request, modifications should be rejected
    - _Requirements: 1.1, 1.3, 1.4_
  
  - [ ]* 3.5 Write unit tests for Material Request
    - Test creation with valid data
    - Test rejection of zero/negative quantities
    - Test status transitions
    - Test modification prevention after submission
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 4. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement RFQ API
  - [x] 5.1 Create RFQ models and schemas
    - Define RFQ, RFQLine, RFQSupplier, and SupplierQuote SQLAlchemy models
    - Create Pydantic schemas for request/response validation
    - Implement status enum with values: DRAFT, SENT, PARTIALLY_RESPONDED, FULLY_RESPONDED, CLOSED
    - _Requirements: 2.5, 11.3, 11.4_
  
  - [x] 5.2 Implement RFQ service layer
    - Implement create_from_material_request() method
    - Copy all line items from source Material Request
    - Set reference_type as MATERIAL_REQUEST and reference_id
    - Validate Material Request exists and has status SUBMITTED
    - Implement add_suppliers() method with supplier validation
    - Implement send() method to change status to SENT
    - Implement record_quote() method to store supplier quotes
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6, 9.1_
  
  - [x] 5.3 Create RFQ API endpoints
    - POST /api/rfqs - Create new RFQ
    - GET /api/rfqs/:id - Retrieve RFQ
    - PUT /api/rfqs/:id - Update RFQ
    - DELETE /api/rfqs/:id - Delete RFQ
    - POST /api/rfqs/:id/send - Send RFQ to suppliers
    - POST /api/rfqs/:id/quotes - Record supplier quote
    - POST /api/rfqs/:id/close - Close RFQ
    - GET /api/rfqs - List with pagination
    - _Requirements: 10.1, 10.2, 10.6_
  
  - [ ]* 5.4 Write property tests for RFQ
    - **Property 5: Line item preservation** - For any Material Request, creating RFQ preserves all line items
    - **Property 6: Reference field consistency** - For any RFQ, reference fields correctly identify source Material Request
    - **Property 8: Supplier validation** - For any supplier_id, supplier must exist in Suppliers API
    - **Property 17: Status transition on send** - For any RFQ in DRAFT, sending changes status to SENT
    - **Property 29: Reference integrity** - For any RFQ, referenced Material Request must exist and be SUBMITTED
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 9.1_
  
  - [ ]* 5.5 Write unit tests for RFQ
    - Test creation from Material Request
    - Test line item copying
    - Test supplier validation
    - Test quote recording
    - Test status transitions
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.6_

- [x] 6. Implement Purchase Order API
  - [x] 6.1 Create Purchase Order models and schemas
    - Define PurchaseOrder and PurchaseOrderLine SQLAlchemy models
    - Create Pydantic schemas for request/response validation
    - Implement status enum with values: DRAFT, SUBMITTED, PARTIALLY_RECEIVED, FULLY_RECEIVED, CLOSED, CANCELLED
    - _Requirements: 3.5, 11.5, 11.6_
  
  - [x] 6.2 Implement Purchase Order service layer
    - Implement create_from_rfq() method
    - Copy selected line items with supplier-quoted prices
    - Set party_type to SUPPLIER and party_id to selected supplier
    - Validate supplier exists in Suppliers API
    - Invoke Transaction Engine to calculate totals
    - Implement submit() method with validation
    - Prevent modifications after submission
    - Implement cancel() and close() methods with state validation
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6, 9.2_
  
  - [x] 6.3 Create Purchase Order API endpoints
    - POST /api/purchase-orders - Create new Purchase Order
    - GET /api/purchase-orders/:id - Retrieve Purchase Order
    - PUT /api/purchase-orders/:id - Update Purchase Order
    - DELETE /api/purchase-orders/:id - Delete Purchase Order
    - POST /api/purchase-orders/:id/submit - Submit Purchase Order
    - POST /api/purchase-orders/:id/cancel - Cancel Purchase Order
    - POST /api/purchase-orders/:id/close - Close Purchase Order
    - GET /api/purchase-orders - List with pagination
    - _Requirements: 10.1, 10.2, 10.6_
  
  - [ ]* 6.4 Write property tests for Purchase Order
    - **Property 7: Line item preservation in PO** - For any RFQ with quotes, creating PO preserves selected line items with quoted prices
    - **Property 9: Party type consistency** - For any Purchase Order, party_type should be SUPPLIER
    - **Property 15: Calculation consistency** - For any Purchase Order, stored totals match Transaction Engine calculations
    - **Property 19: Close precondition** - For any Purchase Order transitioning to CLOSED, status must be FULLY_RECEIVED
    - **Property 30: Reference integrity** - For any Purchase Order, referenced RFQ must exist and have quotes
    - _Requirements: 3.1, 3.2, 3.3, 8.3, 9.2_
  
  - [ ]* 6.5 Write unit tests for Purchase Order
    - Test creation from RFQ
    - Test line item and price copying
    - Test Transaction Engine integration
    - Test supplier validation
    - Test status transitions
    - Test modification prevention after submission
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.6_

- [x] 7. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. Implement state machine and validation
  - [x] 8.1 Create state machine service
    - Define state transition maps for each document type (Material Request, RFQ, Purchase Order)
    - Implement can_transition() method to check if transition is valid
    - Implement validate_transition() method to enforce state machine rules
    - _Requirements: 8.1_
  
  - [x] 8.2 Implement status transition logging
    - Create status_transitions table insert logic
    - Log all status changes with timestamp, user_id, previous_status, new_status
    - _Requirements: 8.5_
  
  - [x] 8.3 Implement terminal state validation
    - Prevent any status transitions from terminal states (CLOSED, CANCELLED, PAID)
    - _Requirements: 8.4_
  
  - [ ]* 8.4 Write property tests for state machine
    - **Property 16: Valid state transitions** - For any document, only valid transitions should succeed
    - **Property 18: Material Request fully quoted precondition** - For any Material Request transitioning to FULLY_QUOTED, all line items must have quotes
    - **Property 20: Terminal state immutability** - For any document in terminal state, transitions should be rejected
    - **Property 32: Status transition logging** - For any status transition, log entry should be created
    - _Requirements: 8.1, 8.2, 8.4, 8.5_
  
  - [ ]* 8.5 Write unit tests for state machine
    - Test valid transitions for each document type
    - Test invalid transition rejection
    - Test terminal state immutability
    - Test transition logging
    - _Requirements: 8.1, 8.4, 8.5_

- [x] 9. Implement Receipt Note integration
  - [x] 9.1 Create Receipt Note service wrapper
    - Implement create_receipt_note() method using existing Purchase Receipt API
    - Set reference_type as PURCHASE_ORDER
    - Validate Purchase Order exists and has status SUBMITTED or PARTIALLY_RECEIVED
    - _Requirements: 5.1, 5.2_
  
  - [x] 9.2 Implement Purchase Order status update logic
    - Calculate total received quantities for each line item
    - Update Purchase Order status to PARTIALLY_RECEIVED when some items received
    - Update Purchase Order status to FULLY_RECEIVED when all items received
    - _Requirements: 5.4, 5.5_
  
  - [x] 9.3 Implement stock increment integration
    - Trigger Stock_Increment for each received line item
    - _Requirements: 5.3_
  
  - [ ]* 9.4 Write property tests for Receipt Note integration
    - **Property 21: Receipt-driven PO status updates** - For any Purchase Order, status should be FULLY_RECEIVED when all items received, PARTIALLY_RECEIVED otherwise
    - **Property 23: Receipt Note reference validation** - For any Receipt Note, referenced PO must exist and be in valid state
    - **Property 24: Stock increment on receipt** - For any Receipt Note, stock should increase by received quantities
    - _Requirements: 5.2, 5.3, 5.4, 5.5_
  
  - [ ]* 9.5 Write unit tests for Receipt Note integration
    - Test Receipt Note creation with valid Purchase Order
    - Test rejection with invalid Purchase Order status
    - Test partial receipt status update
    - Test full receipt status update
    - Test stock increment
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 10. Implement Purchase Invoice integration
  - [x] 10.1 Create Purchase Invoice service wrapper
    - Implement create_purchase_invoice() method using existing Invoice API
    - Set invoice_type as PURCHASE
    - Set reference_type as PURCHASE_ORDER and reference_id
    - Validate Purchase Order exists and has valid status
    - Invoke Transaction Engine with transaction_type PURCHASE
    - _Requirements: 6.1, 6.2, 6.3, 6.4_
  
  - [x] 10.2 Implement three-way matching validation
    - Validate invoiced quantities do not exceed received quantities
    - Compare Purchase Order, Receipt Note, and Purchase Invoice line items
    - _Requirements: 6.5_
  
  - [ ]* 10.3 Write property tests for Purchase Invoice integration
    - **Property 25: Purchase Invoice reference validation** - For any Purchase Invoice, referenced PO must exist and be in valid state
    - **Property 26: Three-way matching** - For any Purchase Invoice line item, invoiced quantity should not exceed received quantity
    - _Requirements: 6.3, 6.5_
  
  - [ ]* 10.4 Write unit tests for Purchase Invoice integration
    - Test Purchase Invoice creation with valid Purchase Order
    - Test rejection with invalid Purchase Order status
    - Test Transaction Engine integration
    - Test three-way matching validation
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

- [x] 11. Implement Payment Made integration
  - [x] 11.1 Create Payment Made service wrapper
    - Implement create_payment() method using existing Payment API
    - Set payment_type as PAY
    - Set reference_type as PURCHASE_INVOICE and reference_id
    - Validate Purchase Invoice exists and has outstanding balance > 0
    - _Requirements: 7.1, 7.2, 7.3_
  
  - [x] 11.2 Implement invoice balance update logic
    - Reduce outstanding balance by payment amount
    - Update Purchase Invoice status to PAID when balance reaches zero
    - _Requirements: 7.4, 7.5_
  
  - [ ]* 11.3 Write property tests for Payment Made integration
    - **Property 22: Payment-driven Invoice status update** - For any Purchase Invoice, status should be PAID when balance reaches zero
    - **Property 27: Payment reference validation** - For any Payment Made, referenced invoice must exist and have balance > 0
    - **Property 28: Payment balance reduction** - For any Payment Made, invoice balance should decrease by payment amount
    - _Requirements: 7.3, 7.4, 7.5_
  
  - [ ]* 11.4 Write unit tests for Payment Made integration
    - Test Payment Made creation with valid Purchase Invoice
    - Test rejection with zero balance
    - Test balance reduction
    - Test status update to PAID
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [x] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Implement error handling and API responses
  - [x] 13.1 Create error handler classes
    - Implement ValidationError with HTTP 400 and structured error details
    - Implement NotFoundError with HTTP 404 and entity information
    - Implement StateError with HTTP 409 and state conflict details
    - Implement IntegrationError with HTTP 502/503 and service information
    - _Requirements: 10.4, 10.5_
  
  - [x] 13.2 Implement API response formatting
    - Ensure all responses include standard fields: id, created_at, updated_at, created_by, status
    - Format validation errors with field and reason
    - Format not found errors with entity_type and entity_id
    - _Requirements: 10.3, 10.4, 10.5_
  
  - [x] 13.3 Add error handling middleware
    - Catch and format all exceptions
    - Return appropriate HTTP status codes
    - Log errors for debugging
    - _Requirements: 10.4, 10.5_
  
  - [ ]* 13.4 Write property tests for error handling
    - **Property 33: Standard response fields** - For any successful API response, standard fields should be present
    - **Property 34: Validation error format** - For any validation error, response should have correct format
    - **Property 35: Not found error format** - For any not found error, response should have correct format
    - _Requirements: 10.3, 10.4, 10.5_
  
  - [ ]* 13.5 Write unit tests for error handling
    - Test validation error responses
    - Test not found error responses
    - Test state conflict error responses
    - Test integration error responses
    - _Requirements: 10.4, 10.5_

- [x] 14. Implement pagination and filtering
  - [x] 14.1 Create pagination utility
    - Implement pagination logic with page, page_size parameters
    - Implement sorting with sort_by, sort_order parameters
    - Return paginated results with metadata (total_count, page, page_size)
    - _Requirements: 10.6_
  
  - [x] 14.2 Add pagination to all list endpoints
    - Apply pagination to Material Request list endpoint
    - Apply pagination to RFQ list endpoint
    - Apply pagination to Purchase Order list endpoint
    - _Requirements: 10.6_
  
  - [ ]* 14.3 Write property tests for pagination
    - **Property 36: Pagination support** - For any list endpoint, pagination parameters should return correctly paginated results
    - _Requirements: 10.6_
  
  - [ ]* 14.4 Write unit tests for pagination
    - Test pagination with various page sizes
    - Test sorting by different fields
    - Test edge cases (empty results, single page)
    - _Requirements: 10.6_

- [x] 15. Implement database transaction management
  - [x] 15.1 Add transaction decorators
    - Create @transactional decorator for service methods
    - Ensure all multi-step operations use transactions
    - Implement rollback on errors
    - _Requirements: 11.7_
  
  - [x] 15.2 Add database locking for concurrent operations
    - Use SELECT FOR UPDATE for Purchase Order status updates
    - Use SELECT FOR UPDATE for invoice balance updates
    - Prevent race conditions in status transitions
    - _Requirements: 11.7_
  
  - [ ]* 15.3 Write property tests for referential integrity
    - **Property 31: Foreign key constraint enforcement** - For any record with foreign key, referenced record must exist
    - _Requirements: 11.7_
  
  - [ ]* 15.4 Write unit tests for transaction management
    - Test transaction rollback on errors
    - Test concurrent status updates
    - Test foreign key constraint enforcement
    - _Requirements: 11.7_

- [x] 16. Integration and end-to-end wiring
  - [x] 16.1 Wire all components together
    - Connect Material Request → RFQ workflow
    - Connect RFQ → Purchase Order workflow
    - Connect Purchase Order → Receipt Note workflow
    - Connect Purchase Order → Purchase Invoice workflow
    - Connect Purchase Invoice → Payment Made workflow
    - _Requirements: All requirements_
  
  - [x] 16.2 Create API documentation
    - Document all endpoints with request/response examples
    - Document error responses
    - Document workflow sequences
    - _Requirements: 10.1, 10.2_
  
  - [ ]* 16.3 Write integration tests for complete workflow
    - Test complete flow: Material Request → RFQ → Purchase Order → Receipt → Invoice → Payment
    - Test partial flows and error scenarios
    - Test concurrent operations
    - _Requirements: All requirements_

- [x] 17. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties using Hypothesis library
- Unit tests validate specific examples and edge cases
- All property tests should run with minimum 100 iterations
- Database migrations should be created before implementing services
- Transaction Engine should be implemented first as it's used by multiple components
- Integration with existing APIs (Suppliers, Purchase Receipt, Invoice, Payment) should use wrapper services
