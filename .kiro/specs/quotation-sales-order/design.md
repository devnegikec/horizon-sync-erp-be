# Design Document: Quotation and Sales Order Management

## Overview

This design implements a complete sales workflow system for an ERP, enabling the progression: Quotation → Sales Order → Invoice → Delivery Note → Payment. The implementation follows existing patterns from the Invoice and Delivery Note modules, using SQLAlchemy ORM with PostgreSQL, FastAPI REST endpoints, and a layered architecture (Model → Repository → Service → API).

The system supports:

- Creating and managing sales quotations with status workflows
- Converting accepted quotations to sales orders
- Creating sales orders with quantity tracking (ordered, billed, delivered)
- Converting sales orders to invoices (with partial billing support)
- Converting sales orders to delivery notes (with partial delivery support)
- Multi-tenancy isolation and permission-based access control

## Architecture

### Layered Architecture

The implementation follows the existing 4-layer architecture:

1. **Model Layer** (`app/models/`): SQLAlchemy ORM models defining database schema
2. **Repository Layer** (`app/repositories/`): Data access logic and queries
3. **Service Layer** (`app/services/`): Business logic, validation, and orchestration
4. **API Layer** (`app/api/v1/endpoints/`): FastAPI REST endpoints with request/response handling

### Document Linking Pattern

Documents are linked using the existing `reference_type` and `reference_id` pattern:

- Sales Order → Quotation: `reference_type="Quotation"`, `reference_id=<quotation_id>`
- Invoice → Sales Order: `reference_type="Sales Order"`, `reference_id=<sales_order_id>`
- Delivery Note → Sales Order: `reference_type="Sales Order"`, `reference_id=<sales_order_id>`

### Status Workflow Management

Status transitions are validated in the service layer:

- **Quotation**: DRAFT → SENT → ACCEPTED/REJECTED/EXPIRED
- **Sales Order**: DRAFT → CONFIRMED → PARTIALLY_DELIVERED → DELIVERED → CLOSED (with CANCELLED available from any state except CLOSED)

## Components and Interfaces

### Database Models

#### Quotation Model

```python
class Quotation(Base):
    __tablename__ = "quotations"

    # Primary identification
    id: UUID (primary key)
    organization_id: UUID (indexed, not null)
    quotation_no: String(100) (not null)

    # Customer and dates
    customer_id: UUID (foreign key to customers.id, not null)
    quotation_date: DateTime(timezone=True) (not null)
    valid_until: DateTime(timezone=True) (nullable)

    # Status and financials
    status: Enum(QuotationStatus) (default=DRAFT, not null)
    grand_total: Numeric(15, 2) (default=0)
    currency: String(10) (default="INR")

    # Additional fields
    remarks: Text (nullable)
    submitted_at: DateTime(timezone=True) (nullable)
    extra_data: JSONB (nullable)

    # Audit fields
    created_by: UUID (nullable)
    updated_by: UUID (nullable)
    created_at: DateTime(timezone=True) (auto)
    updated_at: DateTime(timezone=True) (auto)

    # Relationships
    items: relationship("QuotationItem", cascade="all, delete-orphan")
    customer: relationship("Customer")
```

#### QuotationItem Model

```python
class QuotationItem(Base):
    __tablename__ = "quotation_items"

    # Primary identification
    id: UUID (primary key)
    organization_id: UUID (indexed, not null)
    quotation_id: UUID (foreign key to quotations.id, cascade delete, not null)

    # Item details
    item_id: UUID (foreign key to items.id, not null)
    qty: Numeric(15, 3) (not null)
    uom: String(50) (not null)
    rate: Numeric(15, 2) (not null)
    amount: Numeric(15, 2) (not null)

    # Ordering
    sort_order: Integer (default=0)

    # Additional fields
    extra_data: JSONB (nullable)

    # Audit fields
    created_at: DateTime(timezone=True) (auto)
    updated_at: DateTime(timezone=True) (auto)

    # Relationships
    quotation: relationship("Quotation", back_populates="items")
    item: relationship("Item")
```

#### SalesOrder Model

```python
class SalesOrder(Base):
    __tablename__ = "sales_orders"

    # Primary identification
    id: UUID (primary key)
    organization_id: UUID (indexed, not null)
    sales_order_no: String(100) (not null)

    # Customer and dates
    customer_id: UUID (foreign key to customers.id, not null)
    order_date: DateTime(timezone=True) (not null)
    delivery_date: DateTime(timezone=True) (nullable)

    # Status and financials
    status: Enum(SalesOrderStatus) (default=DRAFT, not null)
    grand_total: Numeric(15, 2) (default=0)
    currency: String(10) (default="INR")

    # Reference linking
    reference_type: String(50) (nullable)
    reference_id: UUID (nullable)

    # Additional fields
    remarks: Text (nullable)
    submitted_at: DateTime(timezone=True) (nullable)
    extra_data: JSONB (nullable)

    # Audit fields
    created_by: UUID (nullable)
    updated_by: UUID (nullable)
    created_at: DateTime(timezone=True) (auto)
    updated_at: DateTime(timezone=True) (auto)

    # Relationships
    items: relationship("SalesOrderItem", cascade="all, delete-orphan")
    customer: relationship("Customer")
```

#### SalesOrderItem Model

```python
class SalesOrderItem(Base):
    __tablename__ = "sales_order_items"

    # Primary identification
    id: UUID (primary key)
    organization_id: UUID (indexed, not null)
    sales_order_id: UUID (foreign key to sales_orders.id, cascade delete, not null)

    # Item details
    item_id: UUID (foreign key to items.id, not null)
    qty: Numeric(15, 3) (not null)
    uom: String(50) (not null)
    rate: Numeric(15, 2) (not null)
    amount: Numeric(15, 2) (not null)

    # Quantity tracking
    billed_qty: Numeric(15, 3) (default=0, not null)
    delivered_qty: Numeric(15, 3) (default=0, not null)

    # Ordering
    sort_order: Integer (default=0)

    # Additional fields
    extra_data: JSONB (nullable)

    # Audit fields
    created_at: DateTime(timezone=True) (auto)
    updated_at: DateTime(timezone=True) (auto)

    # Relationships
    sales_order: relationship("SalesOrder", back_populates="items")
    item: relationship("Item")
```

### Enums (to be added to base.py)

```python
class QuotationStatus(str, enum.Enum):
    DRAFT = "draft"
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

class SalesOrderStatus(str, enum.Enum):
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PARTIALLY_DELIVERED = "partially_delivered"
    DELIVERED = "delivered"
    CLOSED = "closed"
    CANCELLED = "cancelled"
```

### Repository Layer

#### QuotationRepository

```python
class QuotationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> Quotation
    def get_by_id(self, quotation_id: UUID, organization_id: UUID) -> Quotation | None
    def list_quotations(
        self,
        organization_id: UUID,
        page: int,
        page_size: int,
        customer_id: UUID | None,
        status: str | None,
        sort_by: str,
        sort_order: str
    ) -> tuple[list[Quotation], int]
    def update(self, quotation: Quotation, data: dict) -> None
    def delete(self, quotation: Quotation) -> None
```

#### SalesOrderRepository

```python
class SalesOrderRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, data: dict) -> SalesOrder
    def get_by_id(self, sales_order_id: UUID, organization_id: UUID) -> SalesOrder | None
    def get_by_id_with_items(self, sales_order_id: UUID, organization_id: UUID) -> SalesOrder | None
    def list_sales_orders(
        self,
        organization_id: UUID,
        page: int,
        page_size: int,
        customer_id: UUID | None,
        status: str | None,
        sort_by: str,
        sort_order: str
    ) -> tuple[list[SalesOrder], int]
    def update(self, sales_order: SalesOrder, data: dict) -> None
    def delete(self, sales_order: SalesOrder) -> None
    def update_item_billed_qty(self, item_id: UUID, qty_to_add: Decimal) -> None
    def update_item_delivered_qty(self, item_id: UUID, qty_to_add: Decimal) -> None
```

### Service Layer

#### QuotationService

```python
class QuotationService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = QuotationRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict
    def get_by_id(self, quotation_id: UUID, organization_id: UUID) -> dict
    def get_list(...) -> tuple[list[dict], dict]
    def update(self, quotation_id: UUID, data: dict, organization_id: UUID, user_id: UUID) -> dict
    def delete(self, quotation_id: UUID, organization_id: UUID) -> None
    def update_status(self, quotation_id: UUID, new_status: str, organization_id: UUID, user_id: UUID) -> dict
    def convert_to_sales_order(self, quotation_id: UUID, organization_id: UUID, user_id: UUID) -> dict

    # Private methods
    def _validate_status_transition(self, current_status: QuotationStatus, new_status: QuotationStatus) -> None
    def _calculate_grand_total(self, items: list[dict]) -> Decimal
    def _to_response(self, quotation: Quotation) -> dict
```

#### SalesOrderService

```python
class SalesOrderService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = SalesOrderRepository(db)

    def create(self, data: dict, organization_id: UUID, user_id: UUID) -> dict
    def get_by_id(self, sales_order_id: UUID, organization_id: UUID) -> dict
    def get_list(...) -> tuple[list[dict], dict]
    def update(self, sales_order_id: UUID, data: dict, organization_id: UUID, user_id: UUID) -> dict
    def delete(self, sales_order_id: UUID, organization_id: UUID) -> None
    def update_status(self, sales_order_id: UUID, new_status: str, organization_id: UUID, user_id: UUID) -> dict
    def convert_to_invoice(self, sales_order_id: UUID, items_to_bill: list[dict], organization_id: UUID, user_id: UUID) -> dict
    def convert_to_delivery_note(self, sales_order_id: UUID, items_to_deliver: list[dict], organization_id: UUID, user_id: UUID) -> dict

    # Private methods
    def _validate_status_transition(self, current_status: SalesOrderStatus, new_status: SalesOrderStatus) -> None
    def _validate_billing_quantities(self, sales_order: SalesOrder, items_to_bill: list[dict]) -> None
    def _validate_delivery_quantities(self, sales_order: SalesOrder, items_to_deliver: list[dict]) -> None
    def _update_billed_quantities(self, sales_order: SalesOrder, items_to_bill: list[dict]) -> None
    def _update_delivered_quantities(self, sales_order: SalesOrder, items_to_deliver: list[dict]) -> None
    def _check_and_update_delivery_status(self, sales_order: SalesOrder) -> None
    def _calculate_grand_total(self, items: list[dict]) -> Decimal
    def _to_response(self, sales_order: SalesOrder) -> dict
```

### API Layer

#### Quotation Endpoints

```
POST   /api/v1/quotations                          - Create quotation
GET    /api/v1/quotations                          - List quotations (paginated, filtered)
GET    /api/v1/quotations/{id}                     - Get quotation by ID
PUT    /api/v1/quotations/{id}                     - Update quotation
DELETE /api/v1/quotations/{id}                     - Delete quotation
PUT    /api/v1/quotations/{id}/status              - Update quotation status
POST   /api/v1/quotations/{id}/convert-to-sales-order - Convert to sales order
```

#### Sales Order Endpoints

```
POST   /api/v1/sales-orders                        - Create sales order
GET    /api/v1/sales-orders                        - List sales orders (paginated, filtered)
GET    /api/v1/sales-orders/{id}                   - Get sales order by ID
PUT    /api/v1/sales-orders/{id}                   - Update sales order
DELETE /api/v1/sales-orders/{id}                   - Delete sales order
PUT    /api/v1/sales-orders/{id}/status            - Update sales order status
POST   /api/v1/sales-orders/{id}/convert-to-invoice - Convert to invoice
POST   /api/v1/sales-orders/{id}/convert-to-delivery-note - Convert to delivery note
```

## Data Models

### Quotation Data Flow

1. **Creation**: User creates quotation with line items → Status = DRAFT
2. **Submission**: User sends quotation to customer → Status = SENT, submitted_at set
3. **Response**: Customer accepts/rejects or quotation expires → Status = ACCEPTED/REJECTED/EXPIRED
4. **Conversion**: If ACCEPTED, can convert to Sales Order

### Sales Order Data Flow

1. **Creation**: Created manually or from quotation → Status = DRAFT
2. **Confirmation**: User confirms order → Status = CONFIRMED, submitted_at set
3. **Fulfillment**:
   - Create invoices → Update billed_qty on line items
   - Create delivery notes → Update delivered_qty on line items, Status = PARTIALLY_DELIVERED or DELIVERED
4. **Closure**: When fully billed → Status = CLOSED

### Quantity Tracking Model

For each SalesOrderItem:

- `qty`: Total ordered quantity (immutable after confirmation)
- `billed_qty`: Cumulative billed quantity (0 ≤ billed_qty ≤ qty)
- `delivered_qty`: Cumulative delivered quantity (0 ≤ delivered_qty ≤ qty)
- Computed fields:
  - `pending_billing_qty = qty - billed_qty`
  - `pending_delivery_qty = qty - delivered_qty`

### Document Conversion Logic

#### Quotation → Sales Order

```
Input: Quotation (status = ACCEPTED)
Output: Sales Order (status = DRAFT)

Mapping:
- customer_id → customer_id
- currency → currency
- remarks → remarks
- quotation.id → reference_id, "Quotation" → reference_type
- order_date = current_date
- delivery_date = null
- For each quotation_item:
  - Copy item_id, qty, uom, rate, amount, sort_order
  - Set billed_qty = 0, delivered_qty = 0
```

#### Sales Order → Invoice

```
Input: Sales Order + items_to_bill [{item_id, qty_to_bill}]
Output: Invoice (status = DRAFT, type = SALES)

Validation:
- For each item: qty_to_bill ≤ (item.qty - item.billed_qty)

Mapping:
- customer_id → party_id, "Customer" → party_type
- currency → currency
- remarks → remarks
- sales_order.id → reference_id, "Sales Order" → reference_type
- posting_date = current_date
- Create invoice items from items_to_bill

Side Effects:
- Update sales_order_item.billed_qty += qty_to_bill
- If all items fully billed: allow status change to CLOSED
```

#### Sales Order → Delivery Note

```
Input: Sales Order + items_to_deliver [{item_id, qty_to_deliver}]
Output: Delivery Note (status = DRAFT)

Validation:
- For each item: qty_to_deliver ≤ (item.qty - item.delivered_qty)

Mapping:
- customer_id → customer_id
- remarks → remarks
- sales_order.id → reference_id, "Sales Order" → reference_type
- delivery_date = current_date
- Create delivery note items from items_to_deliver

Side Effects:
- Update sales_order_item.delivered_qty += qty_to_deliver
- Update sales_order.status:
  - If all items fully delivered: DELIVERED
  - If some items partially delivered: PARTIALLY_DELIVERED
```

## Correctness Properties

_A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees._

### Core Data Model Properties

**Property 1: Line item amount calculation invariant**
_For any_ quotation line item or sales order line item, the amount field SHALL equal qty × rate
**Validates: Requirements 2.1, 4.1**

**Property 2: Document grand total calculation invariant**
_For any_ quotation or sales order with line items, the grand_total field SHALL equal the sum of all line item amounts
**Validates: Requirements 2.3, 4.4**

**Property 3: Cascade deletion preservation**
_For any_ quotation or sales order, when the parent document is deleted, all associated line items SHALL also be deleted
**Validates: Requirements 2.5, 4.6**

**Property 4: Required fields presence**
_For any_ created quotation, it SHALL have all required fields: id, organization*id, quotation_no, customer_id, quotation_date, status, grand_total, currency, created_at, updated_at
\_For any* created sales order, it SHALL have all required fields: id, organization_id, sales_order_no, customer_id, order_date, status, grand_total, currency, created_at, updated_at
**Validates: Requirements 1.2, 1.8, 3.2, 3.8**

**Property 5: JSONB extensibility support**
_For any_ quotation, sales order, or their line items, the extra_data field SHALL accept and preserve arbitrary valid JSON data
**Validates: Requirements 1.9, 2.6, 3.9, 4.7**

### Status Workflow Properties

**Property 6: Quotation status transition validity**
_For any_ quotation, status transitions SHALL only be allowed according to the workflow: DRAFT → SENT → (ACCEPTED | REJECTED | EXPIRED), and terminal states (ACCEPTED, REJECTED, EXPIRED) SHALL not allow further transitions
**Validates: Requirements 1.6, 1.7**

**Property 7: Sales order status transition validity**
_For any_ sales order, status transitions SHALL follow the workflow: DRAFT → CONFIRMED → PARTIALLY_DELIVERED → DELIVERED → CLOSED, with CANCELLED allowed from any state except CLOSED
**Validates: Requirements 3.4, 3.7**

**Property 8: Draft document mutability**
_For any_ quotation or sales order with status DRAFT, all fields SHALL be modifiable
**Validates: Requirements 1.3, 3.5**

**Property 9: Sent quotation immutability**
_For any_ quotation with status SENT, modifications to line items and pricing fields SHALL be prevented
**Validates: Requirements 1.4**

**Property 10: Document initialization**
_For any_ newly created quotation, the status SHALL be DRAFT and quotation*no SHALL be unique
\_For any* newly created sales order, the status SHALL be DRAFT and sales_order_no SHALL be unique
**Validates: Requirements 1.1, 3.1**

### Quantity Tracking Properties

**Property 11: Sales order quantity invariants**
_For any_ sales order line item, the following invariants SHALL always hold:

- 0 ≤ billed_qty ≤ qty
- 0 ≤ delivered_qty ≤ qty
- billed_qty and delivered_qty SHALL initialize to 0
  **Validates: Requirements 4.3, 8.1, 8.2**

**Property 12: Pending quantity calculations**
_For any_ sales order line item, the computed pending_billing_qty SHALL equal (qty - billed_qty) and pending_delivery_qty SHALL equal (qty - delivered_qty)
**Validates: Requirements 8.3, 8.4**

**Property 13: Billing quantity validation**
_For any_ sales order to invoice conversion, the requested billing quantities SHALL not exceed pending_billing_qty for each line item, and after conversion, billed_qty SHALL increase by the invoiced amount
**Validates: Requirements 6.5, 6.6, 6.8, 8.5**

**Property 14: Delivery quantity validation**
_For any_ sales order to delivery note conversion, the requested delivery quantities SHALL not exceed pending_delivery_qty for each line item, and after conversion, delivered_qty SHALL increase by the delivered amount
**Validates: Requirements 7.5, 7.6, 7.9, 8.6**

**Property 15: Automatic delivery status updates**
_For any_ sales order after delivery note creation:

- If all line items have delivered_qty = qty, status SHALL be DELIVERED
- If some but not all line items have delivered_qty > 0, status SHALL be PARTIALLY_DELIVERED
  **Validates: Requirements 7.7, 7.8**

**Property 16: Fully billed closure eligibility**
_For any_ sales order where all line items have billed_qty = qty, the status SHALL be allowed to transition to CLOSED
**Validates: Requirements 6.7**

### Document Conversion Properties

**Property 17: Quotation to sales order conversion**
_For any_ quotation with status ACCEPTED, converting to sales order SHALL:

- Create a new sales order with status DRAFT
- Copy customer_id, currency, and remarks
- Set reference_type to "Quotation" and reference_id to the quotation's id
- Set order_date to current date and delivery_date to null
- Preserve all line items with item_id, qty, uom, rate, amount, and sort_order
- Initialize billed_qty and delivered_qty to 0 for all line items
  **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5**

**Property 18: Quotation conversion precondition**
_For any_ quotation, conversion to sales order SHALL only be allowed when status is ACCEPTED
**Validates: Requirements 5.6**

**Property 19: Sales order to invoice conversion**
_For any_ sales order converted to invoice, the invoice SHALL:

- Have status DRAFT and invoice_type SALES
- Map customer_id to party_id with party_type "Customer"
- Copy currency and remarks
- Set reference_type to "Sales Order" and reference_id to the sales order's id
- Set posting_date to current date
  **Validates: Requirements 6.1, 6.2, 6.3, 6.4**

**Property 20: Sales order to delivery note conversion**
_For any_ sales order converted to delivery note, the delivery note SHALL:

- Have status DRAFT
- Copy customer_id and remarks
- Set reference_type to "Sales Order" and reference_id to the sales order's id
- Set delivery_date to current date
  **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

### Multi-Tenancy and Security Properties

**Property 21: Organization isolation**
_For any_ quotation or sales order operation, the system SHALL:

- Filter results by organization_id matching the authenticated user's organization
- Prevent access to documents belonging to other organizations
  **Validates: Requirements 9.8, 10.9, 11.1, 11.2**

**Property 22: Cross-organization reference validation**
_For any_ quotation or sales order, the customer_id and item_id references SHALL belong to the same organization_id as the document
**Validates: Requirements 11.3, 11.4**

**Property 23: Permission enforcement**
_For any_ API endpoint call, the system SHALL require appropriate permissions (quotation.create, quotation.read, quotation.update, sales_order.create, sales_order.read, sales_order.update) before allowing the operation
**Validates: Requirements 9.9, 10.10, 11.6**

**Property 24: Audit trail population**
_For any_ quotation or sales order, created_by and updated_by SHALL be set to the authenticated user's id
**Validates: Requirements 11.5**

### Audit Trail Properties

**Property 25: Automatic timestamp management**
_For any_ quotation or sales order:

- created_at SHALL be set automatically on creation
- updated_at SHALL be updated automatically on modification
- submitted_at SHALL be set when quotation status changes to SENT or sales order status changes to CONFIRMED
  **Validates: Requirements 12.1, 12.2, 12.3**

**Property 26: UUID usage**
_For any_ quotation, sales order, or line item, all id fields (primary keys and foreign keys) SHALL be valid UUIDs
**Validates: Requirements 12.4**

**Property 27: Document conversion atomicity**
_For any_ document conversion operation (quotation to sales order, sales order to invoice, sales order to delivery note), both the source document updates and target document creation SHALL complete atomically or not at all
**Validates: Requirements 12.6, 12.7**

## Error Handling

### Validation Errors

1. **Invalid Status Transitions**: Return 400 Bad Request with message indicating valid transitions
2. **Quantity Constraint Violations**: Return 400 Bad Request with message indicating exceeded quantities
3. **Organization Mismatch**: Return 403 Forbidden when attempting cross-organization access
4. **Missing Permissions**: Return 403 Forbidden with message indicating required permission
5. **Resource Not Found**: Return 404 Not Found when quotation/sales order doesn't exist
6. **Invalid Reference**: Return 400 Bad Request when customer_id or item_id doesn't exist or belongs to different organization

### Business Logic Errors

1. **Conversion Precondition Failures**: Return 400 Bad Request when attempting to convert quotation not in ACCEPTED status
2. **Modification Restrictions**: Return 400 Bad Request when attempting to modify immutable fields (e.g., line items on SENT quotation)
3. **Duplicate Document Numbers**: Return 409 Conflict when quotation_no or sales_order_no already exists

### Database Errors

1. **Transaction Failures**: Rollback all changes and return 500 Internal Server Error
2. **Constraint Violations**: Return 400 Bad Request with appropriate message
3. **Connection Errors**: Return 503 Service Unavailable with retry guidance

### Error Response Format

All errors follow the existing FastAPI error response format:

```json
{
  "detail": "Human-readable error message"
}
```

## Testing Strategy

### Dual Testing Approach

The testing strategy employs both unit tests and property-based tests as complementary approaches:

- **Unit tests**: Verify specific examples, edge cases, and error conditions
- **Property tests**: Verify universal properties across all inputs through randomization
- Together they provide comprehensive coverage: unit tests catch concrete bugs, property tests verify general correctness

### Property-Based Testing

**Library**: Use `hypothesis` for Python property-based testing

**Configuration**: Each property test MUST run minimum 100 iterations to ensure comprehensive input coverage

**Test Tagging**: Each property test MUST include a comment tag referencing the design property:

```python
# Feature: quotation-sales-order, Property 1: Line item amount calculation invariant
@given(qty=st.decimals(min_value=0, max_value=10000, places=3),
       rate=st.decimals(min_value=0, max_value=100000, places=2))
@settings(max_examples=100)
def test_line_item_amount_calculation(qty, rate):
    amount = calculate_amount(qty, rate)
    assert amount == qty * rate
```

**Property Test Coverage**: Each correctness property (Property 1-27) MUST be implemented as a property-based test

### Unit Testing

**Focus Areas**:

- Specific examples demonstrating correct behavior
- Edge cases (empty line items, zero quantities, boundary dates)
- Error conditions (invalid status transitions, permission failures)
- Integration points (API endpoints, database transactions)

**Balance**: Avoid excessive unit tests for scenarios covered by property tests. Focus unit tests on:

- Concrete examples that illustrate requirements
- Error handling paths
- Integration between components
- Edge cases that are difficult to generate randomly

### Test Organization

```
tests/
├── unit/
│   ├── test_quotation_service.py
│   ├── test_sales_order_service.py
│   ├── test_quotation_api.py
│   └── test_sales_order_api.py
├── property/
│   ├── test_quotation_properties.py
│   ├── test_sales_order_properties.py
│   └── test_conversion_properties.py
└── integration/
    ├── test_quotation_to_sales_order_flow.py
    ├── test_sales_order_to_invoice_flow.py
    └── test_sales_order_to_delivery_note_flow.py
```

### Key Test Scenarios

**Unit Test Examples**:

1. Create quotation with multiple line items and verify grand_total
2. Attempt invalid status transition and verify error
3. Convert ACCEPTED quotation to sales order and verify all fields
4. Create invoice from sales order with partial quantities
5. Verify cascade deletion of line items
6. Test cross-organization access prevention
7. Test permission enforcement

**Property Test Examples**:

1. For any quotation line items, verify amount = qty × rate
2. For any sales order, verify quantity invariants hold after any operation
3. For any document conversion, verify atomicity
4. For any status transition sequence, verify only valid transitions succeed
5. For any organization, verify isolation from other organizations

### Database Testing

- Use test database with same schema as production
- Use database transactions in tests with rollback after each test
- Test migration scripts for creating tables and indexes
- Verify foreign key constraints and cascade behaviors

### API Testing

- Test all endpoints with valid and invalid inputs
- Test pagination, filtering, and sorting
- Test authentication and authorization
- Test error response formats
- Use FastAPI TestClient for endpoint testing
