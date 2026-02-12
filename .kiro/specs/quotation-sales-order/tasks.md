# Implementation Plan: Quotation and Sales Order Management

## Overview

This implementation plan breaks down the Quotation and Sales Order feature into incremental coding tasks. The approach follows the existing ERP patterns: Models → Repositories → Services → APIs, with testing integrated throughout. Each task builds on previous work, ensuring continuous validation and integration.

## Tasks

- [x] 1. Set up database models and enums

  - Add QuotationStatus and SalesOrderStatus enums to `app/models/base.py`
  - Create `app/models/quotation.py` with Quotation and QuotationItem models
  - Create `app/models/sales_order.py` with SalesOrder and SalesOrderItem models
  - Follow existing patterns from Invoice and DeliveryNote models
  - Include all fields: UUIDs, timestamps, JSONB, relationships, cascade deletes
  - _Requirements: 1.1, 1.2, 1.8, 1.9, 2.1, 2.2, 2.6, 3.1, 3.2, 3.8, 3.9, 4.1, 4.2, 4.3, 4.7_

- [ ]\* 1.1 Write property test for line item amount calculation

  - **Property 1: Line item amount calculation invariant**
  - **Validates: Requirements 2.1, 4.1**

- [ ]\* 1.2 Write property test for required fields presence

  - **Property 4: Required fields presence**
  - **Validates: Requirements 1.2, 1.8, 3.2, 3.8**

- [x] 2. Create database migration

  - Create Alembic migration script for quotations, quotation_items, sales_orders, sales_order_items tables
  - Add indexes on organization_id, customer_id, status fields
  - Add foreign key constraints with appropriate cascade behaviors
  - Test migration up and down
  - _Requirements: 12.5_

- [x] 3. Implement Quotation repository layer

  - Create `app/repositories/quotation_repository.py`
  - Implement create, get_by_id, list_quotations, update, delete methods
  - Include pagination, filtering (customer_id, status), and sorting in list_quotations
  - Follow existing InvoiceRepository patterns
  - _Requirements: 1.1, 1.2, 1.3, 9.2_

- [ ]\* 3.1 Write property test for cascade deletion

  - **Property 3: Cascade deletion preservation**
  - **Validates: Requirements 2.5**

- [ ] 4. Implement Quotation service layer

  - [x] 4.1 Create `app/services/quotation_service.py` with basic CRUD operations

    - Implement create, get_by_id, get_list, update, delete methods
    - Calculate grand_total from line items in create and update
    - Set organization_id, created_by, updated_by from authenticated user
    - _Requirements: 1.1, 1.2, 1.3, 2.3, 11.5_

  - [ ]\* 4.2 Write property test for grand total calculation

    - **Property 2: Document grand total calculation invariant**
    - **Validates: Requirements 2.3**

  - [x] 4.3 Add status transition validation

    - Implement \_validate_status_transition method
    - Enforce DRAFT → SENT → ACCEPTED/REJECTED/EXPIRED workflow
    - Prevent transitions from terminal states
    - _Requirements: 1.6, 1.7_

  - [ ]\* 4.4 Write property test for quotation status transitions

    - **Property 6: Quotation status transition validity**
    - **Validates: Requirements 1.6, 1.7**

  - [x] 4.5 Add update_status method with validation

    - Validate status transitions before updating
    - Set submitted_at when status changes to SENT
    - Prevent line item modifications when status is SENT
    - _Requirements: 1.4, 1.6, 12.3_

  - [ ]\* 4.6 Write property test for sent quotation immutability
    - **Property 9: Sent quotation immutability**
    - **Validates: Requirements 1.4**

- [x] 5. Checkpoint - Ensure quotation service tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Implement Sales Order repository layer

  - Create `app/repositories/sales_order_repository.py`
  - Implement create, get_by_id, get_by_id_with_items, list_sales_orders, update, delete methods
  - Implement update_item_billed_qty and update_item_delivered_qty methods
  - Include pagination, filtering (customer_id, status), and sorting
  - _Requirements: 3.1, 3.2, 4.3, 6.6, 7.6, 10.2_

- [ ] 7. Implement Sales Order service layer

  - [x] 7.1 Create `app/services/sales_order_service.py` with basic CRUD operations

    - Implement create, get_by_id, get_list, update, delete methods
    - Calculate grand_total from line items
    - Initialize billed_qty and delivered_qty to 0 for new line items
    - Include pending_billing_qty and pending_delivery_qty in responses
    - _Requirements: 3.1, 3.2, 3.5, 4.3, 4.4, 8.3, 8.4_

  - [ ]\* 7.2 Write property test for quantity invariants

    - **Property 11: Sales order quantity invariants**
    - **Validates: Requirements 4.3, 8.1, 8.2**

  - [ ]\* 7.3 Write property test for pending quantity calculations

    - **Property 12: Pending quantity calculations**
    - **Validates: Requirements 8.3, 8.4**

  - [x] 7.4 Add status transition validation

    - Implement \_validate_status_transition method
    - Enforce DRAFT → CONFIRMED → PARTIALLY_DELIVERED → DELIVERED → CLOSED workflow
    - Allow CANCELLED from any state except CLOSED
    - _Requirements: 3.4, 3.7_

  - [ ]\* 7.5 Write property test for sales order status transitions

    - **Property 7: Sales order status transition validity**
    - **Validates: Requirements 3.4, 3.7**

  - [x] 7.6 Add update_status method with validation
    - Validate status transitions before updating
    - Set submitted_at when status changes to CONFIRMED
    - _Requirements: 3.4, 12.3_

- [x] 8. Checkpoint - Ensure sales order service tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement quotation to sales order conversion

  - [x] 9.1 Add convert_to_sales_order method to QuotationService

    - Validate quotation status is ACCEPTED
    - Create new sales order with status DRAFT
    - Copy customer_id, currency, remarks
    - Set reference_type to "Quotation" and reference_id to quotation id
    - Copy all line items with item_id, qty, uom, rate, amount, sort_order
    - Initialize billed_qty and delivered_qty to 0
    - Use database transaction for atomicity
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 12.6, 12.7_

  - [ ]\* 9.2 Write property test for quotation to sales order conversion

    - **Property 17: Quotation to sales order conversion**
    - **Property 18: Quotation conversion precondition**
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**

  - [ ]\* 9.3 Write property test for conversion atomicity
    - **Property 27: Document conversion atomicity**
    - **Validates: Requirements 12.6, 12.7**

- [ ] 10. Implement sales order to invoice conversion

  - [x] 10.1 Add convert_to_invoice method to SalesOrderService

    - Accept items_to_bill parameter with item_id and qty_to_bill for each item
    - Validate billing quantities don't exceed pending_billing_qty
    - Create new invoice with status DRAFT and invoice_type SALES
    - Map customer_id to party_id with party_type "Customer"
    - Copy currency and remarks
    - Set reference_type to "Sales Order" and reference_id
    - Update sales_order_item.billed_qty for each billed item
    - Use database transaction for atomicity
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.8, 8.5_

  - [ ]\* 10.2 Write property test for billing quantity validation

    - **Property 13: Billing quantity validation**
    - **Validates: Requirements 6.5, 6.6, 6.8, 8.5**

  - [ ]\* 10.3 Write property test for sales order to invoice conversion

    - **Property 19: Sales order to invoice conversion**
    - **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

  - [ ] 10.4 Add logic to check if sales order is fully billed

    - After updating billed_qty, check if all items have billed_qty = qty
    - If fully billed, allow status transition to CLOSED
    - _Requirements: 6.7_

  - [ ]\* 10.5 Write property test for fully billed closure eligibility
    - **Property 16: Fully billed closure eligibility**
    - **Validates: Requirements 6.7**

- [ ] 11. Implement sales order to delivery note conversion

  - [ ] 11.1 Add convert_to_delivery_note method to SalesOrderService

    - Accept items_to_deliver parameter with item_id and qty_to_deliver for each item
    - Validate delivery quantities don't exceed pending_delivery_qty
    - Create new delivery note with status DRAFT
    - Copy customer_id and remarks
    - Set reference_type to "Sales Order" and reference_id
    - Update sales_order_item.delivered_qty for each delivered item
    - Use database transaction for atomicity
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.9, 8.6_

  - [ ]\* 11.2 Write property test for delivery quantity validation

    - **Property 14: Delivery quantity validation**
    - **Validates: Requirements 7.5, 7.6, 7.9, 8.6**

  - [ ]\* 11.3 Write property test for sales order to delivery note conversion

    - **Property 20: Sales order to delivery note conversion**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

  - [ ] 11.4 Add automatic delivery status updates

    - After updating delivered_qty, check delivery status
    - If all items have delivered_qty = qty, set status to DELIVERED
    - If some items have delivered_qty > 0, set status to PARTIALLY_DELIVERED
    - _Requirements: 7.7, 7.8_

  - [ ]\* 11.5 Write property test for automatic delivery status updates
    - **Property 15: Automatic delivery status updates**
    - **Validates: Requirements 7.7, 7.8**

- [ ] 12. Checkpoint - Ensure conversion logic tests pass

  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Create Pydantic schemas for Quotations

  - Create `app/schemas/quotation.py`
  - Define QuotationBase, QuotationCreate, QuotationUpdate, QuotationResponse schemas
  - Define QuotationItemBase, QuotationItemCreate schemas
  - Define QuotationListItem, QuotationListResponse schemas
  - Define ConvertToSalesOrderResponse schema
  - Follow existing Invoice schema patterns
  - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.6_

- [ ] 14. Create Pydantic schemas for Sales Orders

  - Create `app/schemas/sales_order.py`
  - Define SalesOrderBase, SalesOrderCreate, SalesOrderUpdate, SalesOrderResponse schemas
  - Define SalesOrderItemBase, SalesOrderItemCreate schemas with billed_qty, delivered_qty
  - Define SalesOrderListItem, SalesOrderListResponse schemas
  - Define ConvertToInvoiceRequest, ConvertToDeliveryNoteRequest schemas
  - Include pending_billing_qty and pending_delivery_qty in item responses
  - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.6, 10.7_

- [ ] 15. Implement Quotation API endpoints

  - [ ] 15.1 Create `app/api/v1/endpoints/quotations.py`

    - Implement POST /api/v1/quotations (create)
    - Implement GET /api/v1/quotations (list with pagination, filters, sorting)
    - Implement GET /api/v1/quotations/{id} (get by id)
    - Implement PUT /api/v1/quotations/{id} (update)
    - Implement DELETE /api/v1/quotations/{id} (delete)
    - Add permission checks: quotation.create, quotation.read, quotation.update
    - Validate organization_id matches authenticated user
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.8, 9.9_

  - [ ]\* 15.2 Write property test for organization isolation

    - **Property 21: Organization isolation**
    - **Validates: Requirements 9.8, 11.1, 11.2**

  - [ ]\* 15.3 Write unit tests for quotation API endpoints

    - Test create, list, get, update, delete endpoints
    - Test pagination, filtering, and sorting
    - Test error responses (404, 403, 400)

  - [ ] 15.4 Add status update endpoint

    - Implement PUT /api/v1/quotations/{id}/status
    - Validate status transitions
    - _Requirements: 9.7_

  - [ ] 15.5 Add conversion endpoint
    - Implement POST /api/v1/quotations/{id}/convert-to-sales-order
    - Return created sales order
    - _Requirements: 9.6_

- [ ] 16. Implement Sales Order API endpoints

  - [ ] 16.1 Create `app/api/v1/endpoints/sales_orders.py`

    - Implement POST /api/v1/sales-orders (create)
    - Implement GET /api/v1/sales-orders (list with pagination, filters, sorting)
    - Implement GET /api/v1/sales-orders/{id} (get by id with quantity tracking)
    - Implement PUT /api/v1/sales-orders/{id} (update)
    - Implement DELETE /api/v1/sales-orders/{id} (delete)
    - Add permission checks: sales_order.create, sales_order.read, sales_order.update
    - Validate organization_id matches authenticated user
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.9, 10.10_

  - [ ]\* 16.2 Write property test for permission enforcement

    - **Property 23: Permission enforcement**
    - **Validates: Requirements 9.9, 10.10, 11.6**

  - [ ]\* 16.3 Write unit tests for sales order API endpoints

    - Test create, list, get, update, delete endpoints
    - Test pagination, filtering, and sorting
    - Test quantity tracking in responses
    - Test error responses

  - [ ] 16.4 Add status update endpoint

    - Implement PUT /api/v1/sales-orders/{id}/status
    - Validate status transitions
    - _Requirements: 10.8_

  - [ ] 16.5 Add invoice conversion endpoint

    - Implement POST /api/v1/sales-orders/{id}/convert-to-invoice
    - Accept items_to_bill in request body
    - Return created invoice
    - _Requirements: 10.6_

  - [ ] 16.6 Add delivery note conversion endpoint
    - Implement POST /api/v1/sales-orders/{id}/convert-to-delivery-note
    - Accept items_to_deliver in request body
    - Return created delivery note
    - _Requirements: 10.7_

- [ ] 17. Register API routers

  - Add quotations and sales_orders routers to `app/api/v1/router.py`
  - Ensure proper URL prefixes: /quotations and /sales-orders
  - Test that all endpoints are accessible

- [ ] 18. Add cross-organization reference validation

  - [ ] 18.1 Add validation in QuotationService and SalesOrderService

    - Validate customer_id belongs to same organization_id
    - Validate item_id in line items belongs to same organization_id
    - Raise appropriate errors for mismatches
    - _Requirements: 11.3, 11.4_

  - [ ]\* 18.2 Write property test for cross-organization reference validation
    - **Property 22: Cross-organization reference validation**
    - **Validates: Requirements 11.3, 11.4**

- [ ] 19. Add automatic timestamp management

  - [ ] 19.1 Verify timestamp behavior in models

    - Ensure created_at is set on creation
    - Ensure updated_at is updated on modification
    - Ensure submitted_at is set on status transitions
    - _Requirements: 12.1, 12.2, 12.3_

  - [ ]\* 19.2 Write property test for automatic timestamp management
    - **Property 25: Automatic timestamp management**
    - **Validates: Requirements 12.1, 12.2, 12.3**

- [ ] 20. Final integration testing

  - [ ]\* 20.1 Write integration test for complete quotation to sales order flow

    - Create quotation → Send → Accept → Convert to sales order
    - Verify all data is preserved and linked correctly

  - [ ]\* 20.2 Write integration test for sales order to invoice flow

    - Create sales order → Confirm → Convert to invoice (partial and full)
    - Verify billed_qty updates and status changes

  - [ ]\* 20.3 Write integration test for sales order to delivery note flow

    - Create sales order → Confirm → Convert to delivery note (partial and full)
    - Verify delivered_qty updates and status changes

  - [ ]\* 20.4 Write integration test for complete end-to-end flow
    - Quotation → Sales Order → Invoice + Delivery Note → Verify CLOSED status

- [ ] 21. Final checkpoint - Ensure all tests pass
  - Run full test suite (unit, property, integration)
  - Verify all 27 correctness properties are tested
  - Ensure test coverage is adequate
  - Ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional property-based and integration tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout implementation
- Property tests validate universal correctness properties with 100+ iterations
- Unit tests validate specific examples and edge cases
- The implementation follows existing ERP patterns for consistency
- Database transactions ensure atomicity of document conversions
- Multi-tenancy isolation is enforced at all layers
