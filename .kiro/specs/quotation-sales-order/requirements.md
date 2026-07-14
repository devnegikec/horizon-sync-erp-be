# Requirements Document: Quotation and Sales Order Management

## Introduction

This document specifies the requirements for implementing Quotation and Sales Order features in the ERP system. These features enable the complete sales workflow from initial quote to final delivery and payment: Quotation → Sales Order → Invoice → Delivery Note → Payment.

The system will support creating sales quotations for customers, converting accepted quotations to sales orders, and generating invoices and delivery notes from sales orders with support for partial billing and partial delivery scenarios.

## Glossary

- **Quotation**: A formal document sent to customers with proposed prices and terms for products/services
- **Sales_Order**: A confirmed customer order that commits to purchase specific products/services
- **Invoice**: A billing document requesting payment (already exists in system)
- **Delivery_Note**: A document confirming shipment of goods (already exists in system)
- **Payment**: A record of money received or paid (already exists in system)
- **Line_Item**: An individual product/service entry within a document with quantity and price
- **Party**: A customer or supplier in the system
- **Organization**: A tenant in the multi-tenant system
- **Document_Conversion**: The process of creating a new document from an existing document
- **Partial_Billing**: Creating multiple invoices for portions of a sales order
- **Partial_Delivery**: Creating multiple delivery notes for portions of a sales order
- **Reference_Link**: A connection between documents using reference_type and reference_id fields
- **Status_Workflow**: The defined progression of status values for a document type
- **Quantity_Tracking**: Monitoring ordered, billed, and delivered quantities for sales order items

## Requirements

### Requirement 1: Quotation Management

**User Story:** As a sales representative, I want to create and manage quotations for customers, so that I can provide formal price proposals and track their acceptance status.

#### Acceptance Criteria

1. WHEN a quotation is created, THE System SHALL assign a unique quotation_no and set status to DRAFT
2. THE Quotation SHALL include organization_id, customer_id, quotation_date, valid_until date, grand_total, currency, and remarks
3. WHEN a quotation status is DRAFT, THE System SHALL allow modifications to all fields
4. WHEN a quotation status is SENT, THE System SHALL prevent modifications to line items and pricing
5. WHEN a quotation valid_until date has passed and status is SENT, THE System SHALL allow status change to EXPIRED
6. THE System SHALL support quotation status transitions: DRAFT → SENT → ACCEPTED/REJECTED/EXPIRED
7. WHEN a quotation status is ACCEPTED, REJECTED, or EXPIRED, THE System SHALL prevent further status changes
8. THE Quotation SHALL store created_by, updated_by, created_at, updated_at, and submitted_at timestamps
9. THE Quotation SHALL support extra_data as JSONB for extensibility

### Requirement 2: Quotation Line Items

**User Story:** As a sales representative, I want to add multiple products with quantities and prices to a quotation, so that I can provide detailed pricing information to customers.

#### Acceptance Criteria

1. WHEN a line item is added to a quotation, THE System SHALL require item_id, qty, uom, rate, and calculate amount as qty × rate
2. THE Quotation_Line_Item SHALL include organization_id, quotation_id, item_id, qty, uom, rate, amount, and sort_order
3. WHEN line items are modified, THE System SHALL recalculate the quotation grand_total as the sum of all line item amounts
4. THE System SHALL support multiple line items per quotation with sort_order for display ordering
5. WHEN a quotation is deleted, THE System SHALL cascade delete all associated line items
6. THE Quotation_Line_Item SHALL support extra_data as JSONB for extensibility

### Requirement 3: Sales Order Management

**User Story:** As a sales manager, I want to create and manage sales orders, so that I can track confirmed customer orders through fulfillment.

#### Acceptance Criteria

1. WHEN a sales order is created, THE System SHALL assign a unique sales_order_no and set status to DRAFT
2. THE Sales_Order SHALL include organization_id, customer_id, order_date, delivery_date, grand_total, currency, reference_type, reference_id, and remarks
3. WHEN a sales order has reference_type "Quotation", THE System SHALL store the quotation_id in reference_id
4. THE System SHALL support sales order status transitions: DRAFT → CONFIRMED → PARTIALLY_DELIVERED → DELIVERED → CLOSED
5. WHEN a sales order status is DRAFT, THE System SHALL allow modifications to all fields
6. WHEN a sales order status is CONFIRMED or later, THE System SHALL prevent modifications to line items that would invalidate existing invoices or delivery notes
7. THE System SHALL support CANCELLED status from any status except CLOSED
8. THE Sales_Order SHALL store created_by, updated_by, created_at, updated_at, and submitted_at timestamps
9. THE Sales_Order SHALL support extra_data as JSONB for extensibility

### Requirement 4: Sales Order Line Items

**User Story:** As a sales manager, I want to add multiple products with quantities and prices to a sales order, so that I can specify exactly what the customer has ordered.

#### Acceptance Criteria

1. WHEN a line item is added to a sales order, THE System SHALL require item_id, qty, uom, rate, and calculate amount as qty × rate
2. THE Sales_Order_Line_Item SHALL include organization_id, sales_order_id, item_id, qty, uom, rate, amount, billed_qty, delivered_qty, and sort_order
3. THE Sales_Order_Line_Item SHALL initialize billed_qty and delivered_qty to 0 when created
4. WHEN line items are modified, THE System SHALL recalculate the sales order grand_total as the sum of all line item amounts
5. THE System SHALL support multiple line items per sales order with sort_order for display ordering
6. WHEN a sales order is deleted, THE System SHALL cascade delete all associated line items
7. THE Sales_Order_Line_Item SHALL support extra_data as JSONB for extensibility

### Requirement 5: Quotation to Sales Order Conversion

**User Story:** As a sales representative, I want to convert an accepted quotation to a sales order, so that I can efficiently create orders from approved quotes.

#### Acceptance Criteria

1. WHEN a quotation with status ACCEPTED is converted to sales order, THE System SHALL create a new sales order with status DRAFT
2. WHEN converting quotation to sales order, THE System SHALL copy customer_id, currency, remarks, and all line items
3. WHEN converting quotation to sales order, THE System SHALL set sales order reference_type to "Quotation" and reference_id to the quotation id
4. WHEN converting quotation to sales order, THE System SHALL set order_date to current date and delivery_date to null
5. WHEN converting quotation to sales order, THE System SHALL preserve line item details including item_id, qty, uom, rate, amount, and sort_order
6. THE System SHALL allow converting a quotation to sales order only when quotation status is ACCEPTED

### Requirement 6: Sales Order to Invoice Conversion

**User Story:** As an accounts manager, I want to create invoices from sales orders, so that I can bill customers for confirmed orders.

#### Acceptance Criteria

1. WHEN a sales order is converted to invoice, THE System SHALL create a new invoice with status DRAFT and invoice_type SALES
2. WHEN converting sales order to invoice, THE System SHALL copy customer_id to party_id, set party_type to "Customer", and copy currency and remarks
3. WHEN converting sales order to invoice, THE System SHALL set invoice reference_type to "Sales Order" and reference_id to the sales order id
4. WHEN converting sales order to invoice, THE System SHALL set posting_date to current date and due_date based on payment terms
5. WHEN converting sales order to invoice with partial billing, THE System SHALL allow specifying quantities to bill for each line item
6. WHEN an invoice is created from sales order, THE System SHALL update the sales order line item billed_qty by adding the invoiced quantity
7. WHEN all line items in a sales order have billed_qty equal to qty, THE System SHALL allow status change to CLOSED
8. THE System SHALL prevent billing quantities that would cause billed_qty to exceed ordered qty

### Requirement 7: Sales Order to Delivery Note Conversion

**User Story:** As a warehouse manager, I want to create delivery notes from sales orders, so that I can track shipments against customer orders.

#### Acceptance Criteria

1. WHEN a sales order is converted to delivery note, THE System SHALL create a new delivery note with status DRAFT
2. WHEN converting sales order to delivery note, THE System SHALL copy customer_id and remarks
3. WHEN converting sales order to delivery note, THE System SHALL set delivery note reference_type to "Sales Order" and reference_id to the sales order id
4. WHEN converting sales order to delivery note, THE System SHALL set delivery_date to current date
5. WHEN converting sales order to delivery note with partial delivery, THE System SHALL allow specifying quantities to deliver for each line item
6. WHEN a delivery note is created from sales order, THE System SHALL update the sales order line item delivered_qty by adding the delivered quantity
7. WHEN all line items in a sales order have delivered_qty equal to qty, THE System SHALL update status to DELIVERED
8. WHEN some but not all line items have delivered_qty greater than 0, THE System SHALL update status to PARTIALLY_DELIVERED
9. THE System SHALL prevent delivery quantities that would cause delivered_qty to exceed ordered qty

### Requirement 8: Quantity Tracking and Validation

**User Story:** As a sales manager, I want to track billed and delivered quantities against ordered quantities, so that I can monitor order fulfillment progress.

#### Acceptance Criteria

1. FOR ALL sales order line items, THE System SHALL maintain the invariant: 0 ≤ billed_qty ≤ qty
2. FOR ALL sales order line items, THE System SHALL maintain the invariant: 0 ≤ delivered_qty ≤ qty
3. WHEN retrieving a sales order, THE System SHALL calculate and return pending_billing_qty as qty - billed_qty for each line item
4. WHEN retrieving a sales order, THE System SHALL calculate and return pending_delivery_qty as qty - delivered_qty for each line item
5. WHEN creating an invoice from sales order, THE System SHALL validate that requested billing quantities do not exceed pending_billing_qty
6. WHEN creating a delivery note from sales order, THE System SHALL validate that requested delivery quantities do not exceed pending_delivery_qty

### Requirement 9: REST API Endpoints for Quotations

**User Story:** As a frontend developer, I want REST API endpoints for quotations, so that I can build user interfaces for quotation management.

#### Acceptance Criteria

1. THE System SHALL provide POST /api/v1/quotations endpoint to create quotations
2. THE System SHALL provide GET /api/v1/quotations endpoint to list quotations with pagination, filtering by customer_id and status, and sorting
3. THE System SHALL provide GET /api/v1/quotations/{id} endpoint to retrieve a single quotation with line items
4. THE System SHALL provide PUT /api/v1/quotations/{id} endpoint to update quotations
5. THE System SHALL provide DELETE /api/v1/quotations/{id} endpoint to delete quotations
6. THE System SHALL provide POST /api/v1/quotations/{id}/convert-to-sales-order endpoint to convert quotation to sales order
7. THE System SHALL provide PUT /api/v1/quotations/{id}/status endpoint to update quotation status
8. WHEN API endpoints are called, THE System SHALL validate organization_id matches the authenticated user's organization
9. WHEN API endpoints are called, THE System SHALL require appropriate permissions (quotation.create, quotation.read, quotation.update)

### Requirement 10: REST API Endpoints for Sales Orders

**User Story:** As a frontend developer, I want REST API endpoints for sales orders, so that I can build user interfaces for order management.

#### Acceptance Criteria

1. THE System SHALL provide POST /api/v1/sales-orders endpoint to create sales orders
2. THE System SHALL provide GET /api/v1/sales-orders endpoint to list sales orders with pagination, filtering by customer_id and status, and sorting
3. THE System SHALL provide GET /api/v1/sales-orders/{id} endpoint to retrieve a single sales order with line items and quantity tracking
4. THE System SHALL provide PUT /api/v1/sales-orders/{id} endpoint to update sales orders
5. THE System SHALL provide DELETE /api/v1/sales-orders/{id} endpoint to delete sales orders
6. THE System SHALL provide POST /api/v1/sales-orders/{id}/convert-to-invoice endpoint to convert sales order to invoice with optional partial quantities
7. THE System SHALL provide POST /api/v1/sales-orders/{id}/convert-to-delivery-note endpoint to convert sales order to delivery note with optional partial quantities
8. THE System SHALL provide PUT /api/v1/sales-orders/{id}/status endpoint to update sales order status
9. WHEN API endpoints are called, THE System SHALL validate organization_id matches the authenticated user's organization
10. WHEN API endpoints are called, THE System SHALL require appropriate permissions (sales_order.create, sales_order.read, sales_order.update)

### Requirement 11: Multi-Tenancy and Security

**User Story:** As a system administrator, I want proper multi-tenancy isolation and permission controls, so that organizations can only access their own data.

#### Acceptance Criteria

1. FOR ALL quotation and sales order operations, THE System SHALL filter by organization_id matching the authenticated user's organization
2. THE System SHALL prevent users from accessing quotations or sales orders belonging to other organizations
3. THE System SHALL validate that customer_id references belong to the same organization_id
4. THE System SHALL validate that item_id references belong to the same organization_id
5. THE System SHALL store created_by and updated_by as the authenticated user's id
6. THE System SHALL enforce permission checks using the existing authorization system

### Requirement 12: Data Integrity and Audit Trail

**User Story:** As a compliance officer, I want complete audit trails and data integrity, so that I can track all changes to quotations and sales orders.

#### Acceptance Criteria

1. THE System SHALL automatically set created_at timestamp when creating quotations or sales orders
2. THE System SHALL automatically update updated_at timestamp when modifying quotations or sales orders
3. THE System SHALL set submitted_at timestamp when quotation status changes to SENT or sales order status changes to CONFIRMED
4. THE System SHALL use UUID for all primary keys and foreign keys
5. THE System SHALL use PostgreSQL database with proper indexes on organization_id, customer_id, and status fields
6. THE System SHALL use database transactions to ensure atomicity of document conversions
7. WHEN converting documents, THE System SHALL ensure both source and target documents are created/updated atomically or not at all
