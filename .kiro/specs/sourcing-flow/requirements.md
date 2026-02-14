# Requirements Document: Sourcing Flow (Procure-to-Pay)

## Introduction

This document specifies the requirements for implementing a complete Sourcing Flow (Procure-to-Pay) in an existing ERP system. The flow encompasses the entire procurement lifecycle from internal demand identification through supplier payment, integrating with existing Suppliers, Purchase Receipt, Invoice, and Payment APIs while introducing new Material Request and RFQ capabilities.

The system will reuse existing architectural patterns (party_id/party_type, reference_type/reference_id, line items, status enums) and leverage a shared Transaction Engine to handle both purchase and sales workflows with appropriate discriminators.

## Glossary

- **Material_Request**: Internal document created by warehouse managers or project leads to signal demand for materials
- **RFQ**: Request for Quotation sent to multiple suppliers to gather pricing and terms
- **Purchase_Order**: Legally binding contract issued to a selected supplier for procurement
- **Receipt_Note**: Document recording physical arrival of goods at warehouse (uses existing Purchase Receipt API)
- **Purchase_Invoice**: Supplier bill recorded as accounts payable (uses existing Invoice API with PURCHASE type)
- **Payment_Made**: Outbound payment to supplier (uses existing Payment API with PAY type)
- **Transaction_Engine**: Generic service handling line items, taxes, totals, and calculations for both purchase and sales documents
- **Sourcing_Flow**: Complete workflow from Material Request through Payment Made
- **Stock_Increment**: Inventory increase triggered by Receipt


## Requirements

### Requirement 1: Material Request Creation

**User Story:** As a warehouse manager or project lead, I want to create Material Requests to signal internal demand for materials, so that the procurement process can be initiated.

#### Acceptance Criteria

1. WHEN a user creates a Material Request, THE System SHALL generate a unique identifier and set status to DRAFT
2. WHEN a Material Request is created, THE System SHALL record line items with item_id, quantity, required_date, and description
3. WHEN a Material Request is submitted, THE System SHALL validate that all line items have positive quantities and valid item references
4. WHEN a Material Request status changes from DRAFT to SUBMITTED, THE System SHALL prevent further modifications to line items
5. THE System SHALL support Material Request statuses: DRAFT, SUBMITTED, PARTIALLY_QUOTED, FULLY_QUOTED, CANCELLED

### Requirement 2: RFQ Creation and Management

**User Story:** As a procurement officer, I want to create RFQs from Material Requests and send them to multiple suppliers, so that I can gather competitive pricing and terms.

#### Acceptance Criteria

1. WHEN an RFQ is created from a Material Request, THE System SHALL copy all line items from the source Material Request
2. WHEN an RFQ is created, THE System SHALL record reference_type as MATERIAL_REQUEST and reference_id as the source Material Request ID
3. WHEN suppliers are added to an RFQ, THE System SHALL validate each supplier_id against the existing Suppliers API
4. WHEN an RFQ is sent to suppliers, THE System SHALL change status from DRAFT to SENT
5. THE System SHALL support RFQ statuses: DRAFT, SENT, PARTIALLY_RESPONDED, FULLY_RESPONDED, CLOSED
6. WHEN supplier quotes are received, THE System SHALL record quoted_price, quoted_delivery_date, and supplier_notes for each line item

### Requirement 3: Purchase Order Creation

**User Story:** As a procurement officer, I want to create Purchase Orders from selected RFQ quotes, so that I can formalize procurement contracts with suppliers.

#### Acceptance Criteria

1. WHEN a Purchase Order is created from an RFQ, THE System SHALL copy selected line items with supplier-quoted prices
2. WHEN a Purchase Order is created, THE System SHALL set party_type to SUPPLIER and party_id to the selected supplier
3. WHEN a Purchase Order is created, THE System SHALL invoke the Transaction_Engine to calculate line totals, taxes, and grand total
4. WHEN a Purchase Order is submitted, THE System SHALL validate that party_id references a valid supplier
5. THE System SHALL support Purchase Order statuses: DRAFT, SUBMITTED, PARTIALLY_RECEIVED, FULLY_RECEIVED, CLOSED, CANCELLED
6. WHEN a Purchase Order status changes to SUBMITTED, THE System SHALL prevent modifications to line items and pricing

### Requirement 4: Transaction Engine Integration

**User Story:** As a system architect, I want a shared Transaction Engine to handle calculations for both purchase and sales documents, so that calculation logic is consistent and maintainable.

#### Acceptance Criteria

1. WHEN the Transaction_Engine processes a document, THE System SHALL accept a transaction_type discriminator (PURCHASE or SALES)
2. WHEN line items are provided, THE Transaction_Engine SHALL calculate line_total as quantity × unit_price for each line
3. WHEN line totals are calculated, THE Transaction_Engine SHALL compute subtotal as the sum of all line_total values
4. WHEN tax rates are provided, THE Transaction_Engine SHALL calculate tax_amount as subtotal × tax_rate
5. WHEN all calculations are complete, THE Transaction_Engine SHALL compute grand_total as subtotal + tax_amount - discount_amount
6. THE Transaction_Engine SHALL return a calculation result containing line_totals, subtotal, tax_amount, discount_amount, and grand_total

### Requirement 5: Receipt Note Integration

**User Story:** As a warehouse operator, I want to record goods receipt against Purchase Orders using the existing Purchase Receipt API, so that inventory is updated and the procurement workflow advances.

#### Acceptance Criteria

1. WHEN a Receipt Note is created, THE System SHALL use the existing Purchase Receipt API with reference_type as PURCHASE_ORDER
2. WHEN a Receipt Note is created, THE System SHALL validate that the referenced Purchase Order exists and has status SUBMITTED or PARTIALLY_RECEIVED
3. WHEN a Receipt Note is submitted, THE System SHALL trigger Stock_Increment for each received line item
4. WHEN all line items of a Purchase Order are fully received, THE System SHALL update Purchase Order status to FULLY_RECEIVED
5. WHEN some but not all line items are received, THE System SHALL update Purchase Order status to PARTIALLY_RECEIVED

### Requirement 6: Purchase Invoice Integration

**User Story:** As an accounts payable clerk, I want to record supplier invoices against Purchase Orders using the existing Invoice API, so that payment obligations are tracked.

#### Acceptance Criteria

1. WHEN a Purchase Invoice is created, THE System SHALL use the existing Invoice API with invoice_type as PURCHASE
2. WHEN a Purchase Invoice is created, THE System SHALL set reference_type as PURCHASE_ORDER and reference_id to the source Purchase Order
3. WHEN a Purchase Invoice is created, THE System SHALL validate that the referenced Purchase Order has status SUBMITTED, PARTIALLY_RECEIVED, or FULLY_RECEIVED
4. WHEN a Purchase Invoice is submitted, THE System SHALL invoke the Transaction_Engine with transaction_type PURCHASE to calculate totals
5. THE System SHALL support three-way matching: Purchase Order, Receipt Note, and Purchase Invoice line items

### Requirement 7: Payment Made Integration

**User Story:** As an accounts payable clerk, I want to record payments to suppliers using the existing Payment API, so that payment obligations are settled.

#### Acceptance Criteria

1. WHEN a Payment Made is created, THE System SHALL use the existing Payment API with payment_type as PAY
2. WHEN a Payment Made is created, THE System SHALL set reference_type as PURCHASE_INVOICE and reference_id to the source Purchase Invoice
3. WHEN a Payment Made is created, THE System SHALL validate that the referenced Purchase Invoice exists and has outstanding balance
4. WHEN a Payment Made is submitted, THE System SHALL reduce the outstanding balance of the referenced Purchase Invoice
5. WHEN a Purchase Invoice outstanding balance reaches zero, THE System SHALL update Purchase Invoice status to PAID

### Requirement 8: Workflow State Transitions

**User Story:** As a system administrator, I want clear state transition rules for all document types, so that workflow integrity is maintained.

#### Acceptance Criteria

1. WHEN a document status changes, THE System SHALL validate that the transition is allowed according to the state machine for that document type
2. WHEN a Material Request transitions from SUBMITTED to FULLY_QUOTED, THE System SHALL verify that all line items have associated RFQ responses
3. WHEN a Purchase Order transitions to CLOSED, THE System SHALL verify that status is FULLY_RECEIVED
4. WHEN a document is in a terminal state (CLOSED, CANCELLED, PAID), THE System SHALL prevent any further status transitions
5. THE System SHALL log all status transitions with timestamp, user_id, and previous_status

### Requirement 9: Reference Integrity

**User Story:** As a data architect, I want referential integrity maintained across all document relationships, so that data consistency is guaranteed.

#### Acceptance Criteria

1. WHEN an RFQ references a Material Request, THE System SHALL validate that the Material Request exists and has status SUBMITTED
2. WHEN a Purchase Order references an RFQ, THE System SHALL validate that the RFQ exists and has received supplier quotes
3. WHEN a Receipt Note references a Purchase Order, THE System SHALL validate that the Purchase Order exists and has status SUBMITTED or PARTIALLY_RECEIVED
4. WHEN a Purchase Invoice references a Purchase Order, THE System SHALL validate that the Purchase Order exists
5. WHEN a Payment Made references a Purchase Invoice, THE System SHALL validate that the Purchase Invoice exists and has status SUBMITTED or PARTIALLY_PAID

### Requirement 10: API Consistency

**User Story:** As a frontend developer, I want consistent API patterns across all document types, so that integration is predictable and maintainable.

#### Acceptance Criteria

1. THE System SHALL provide CRUD endpoints (Create, Read, Update, Delete) for Material Request and RFQ
2. THE System SHALL provide status transition endpoints following the pattern POST /api/{document_type}/{id}/submit
3. WHEN API responses are returned, THE System SHALL include standard fields: id, created_at, updated_at, created_by, status
4. WHEN validation errors occur, THE System SHALL return HTTP 400 with structured error messages containing field and reason
5. WHEN referenced entities are not found, THE System SHALL return HTTP 404 with entity_type and entity_id in the error response
6. THE System SHALL support pagination for list endpoints with query parameters: page, page_size, sort_by, sort_order

### Requirement 11: Data Persistence

**User Story:** As a database administrator, I want proper database schema design for new entities, so that data integrity and performance are optimized.

#### Acceptance Criteria

1. THE System SHALL store Material Request data in a material_requests table with columns: id, status, created_at, updated_at, created_by, notes
2. THE System SHALL store Material Request line items in a material_request_lines table with foreign key to material_requests
3. THE System SHALL store RFQ data in an rfqs table with columns: id, material_request_id, status, created_at, updated_at, created_by, closing_date
4. THE System SHALL store RFQ line items in an rfq_lines table with foreign key to rfqs
5. THE System SHALL store Purchase Order data in a purchase_orders table with columns: id, rfq_id, supplier_id, status, subtotal, tax_amount, grand_total, created_at, updated_at
6. THE System SHALL store Purchase Order line items in a purchase_order_lines table with foreign key to purchase_orders
7. THE System SHALL enforce foreign key constraints for all reference relationships
8. THE System SHALL create indexes on status columns and foreign key columns for query performance
