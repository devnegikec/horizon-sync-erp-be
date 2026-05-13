# Frontend Validation Guide — Inventory & Revenue Module

This document lists all field-level validations that must be implemented on the frontend for every feature tab in the Inventory & Revenue module. These rules are derived directly from the backend Pydantic schemas (source of truth).

---

## General Notes

- **Required fields** are marked with ⚠️ — form submission must be blocked if empty.
- **Max length** constraints should show character counters or truncate input.
- **Min value / Max value** constraints should be enforced on blur or on change.
- **Pattern** constraints should be validated with regex on blur.
- **UUID fields** referencing other entities should use dropdowns/pickers (not free text).
- All numeric fields with `ge=0` must not accept negative values.
- All numeric fields with `gt=0` must be strictly positive (> 0).

---

## 1. Items (Create / Edit)

**Source**: `core-service/app/schemas/item.py` → `ItemCreate`, `ItemUpdate`

### Basic Information

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `item_name` | string | ⚠️ Yes | min: 1 char, max: 255 chars |
| `item_code` | string | No | max: 100 chars |
| `description` | string | No | max: 1000 chars |
| `item_group_id` | UUID | No | Must be valid item group (dropdown) |
| `item_type` | string | Yes (default: "stock") | Allowed: stock, service, fixed_asset, consumable |
| `uom` (Unit of Measure) | string | Yes (default: "Nos") | max: 50 chars |
| `status` | string | Yes (default: "ACTIVE") | Allowed: ACTIVE, INACTIVE |

### Stock & Inventory

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `maintain_stock` | boolean | No (default: true) | Checkbox |
| `valuation_method` | string | No (default: "FIFO") | Allowed: FIFO, LIFO, Moving_Average |
| `allow_negative_stock` | boolean | No (default: false) | Checkbox |

### Variants

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `has_variants` | boolean | No (default: false) | Checkbox |
| `variant_of` | UUID | No | Must be valid item UUID (only if has_variants) |
| `variant_attributes` | JSON object | No | Must be valid JSON |

### Batch & Serial Numbers

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `has_batch_no` | boolean | No (default: false) | Checkbox |
| `has_serial_no` | boolean | No (default: false) | Checkbox |
| `batch_number_series` | string | No | max: 100 chars (shown only if has_batch_no) |
| `serial_number_series` | string | No | max: 100 chars (shown only if has_serial_no) |

### Pricing & Valuation

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `standard_rate` | decimal | Yes (default: 0.00) | Must be ≥ 0 |
| `valuation_rate` | decimal | No (default: 0.00) | Must be ≥ 0 |

### Reordering

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `enable_auto_reorder` | boolean | No (default: false) | Checkbox |
| `reorder_level` | integer | No (default: 0) | Must be ≥ 0 |
| `reorder_qty` | integer | No (default: 0) | Must be ≥ 0 |
| `min_order_qty` | integer | Yes (default: 1) | Must be ≥ 1 |
| `max_order_qty` | integer | No | If provided, must be ≥ 0 |

### Weight

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `weight_per_unit` | decimal | No | If provided, must be ≥ 0 |
| `weight_uom` | string | No | Dropdown selection |

### Quality Inspection

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `inspection_required_before_purchase` | boolean | No | Checkbox |
| `inspection_required_before_delivery` | boolean | No | Checkbox |
| `quality_inspection_template` | UUID | No | Dropdown (shown if either inspection is checked) |

### Tax Templates

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `sales_tax_template_id` | UUID | No | Dropdown from tax templates |
| `purchase_tax_template_id` | UUID | No | Dropdown from tax templates |

### Additional Info

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `barcode` | string | No | max: 100 chars |
| `image_url` | string | No | max: 500 chars, must be valid URL format |
| `images` | array of strings | No | Each must be valid URL |
| `tags` | array of strings | No | Free text tags |

---

## 2. Warehouses (Create / Edit)

**Source**: `core-service/app/schemas/warehouse.py` → `WarehouseCreate`, `WarehouseUpdate`

### Basic Information

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `name` | string | ⚠️ Yes | min: 1 char, max: 255 chars |
| `code` | string | ⚠️ Yes | min: 1 char, max: 50 chars |
| `description` | string | No | max: 1000 chars |
| `warehouse_type` | string | Yes (default: "warehouse") | Allowed: warehouse, store, virtual, transit |
| `parent_warehouse_id` | UUID | No | Dropdown from existing warehouses |

### Address

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `address_line1` | string | No | max: 255 chars |
| `address_line2` | string | No | max: 255 chars |
| `city` | string | No | max: 100 chars |
| `state` | string | No | max: 100 chars |
| `postal_code` | string | No | max: 20 chars |
| `country` | string | No | max: 100 chars |

### Contact

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `contact_name` | string | No | max: 255 chars |
| `contact_phone` | string | No | max: 50 chars |
| `contact_email` | string | No | max: 255 chars, must be valid email format |

### Capacity

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `total_capacity` | integer | No | Must be ≥ 0 |
| `capacity_uom` | string | No | max: 50 chars |

### Accounting & Status

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `stock_account_id` | UUID | No | Dropdown from chart of accounts |
| `is_active` | boolean | No (default: true) | Checkbox |
| `is_default` | boolean | No (default: false) | Checkbox |

---

## 3. Item Groups (Create / Edit)

**Source**: `core-service/app/schemas/item_group.py` → `ItemGroupCreate`, `ItemGroupUpdate`

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `name` | string | ⚠️ Yes | min: 1 char, max: 255 chars |
| `code` | string | No | min: 1 char (if provided), max: 50 chars |
| `description` | string | No | max: 1000 chars |
| `parent_id` | UUID | No | Dropdown from existing item groups |
| `default_valuation_method` | string | No | Allowed: FIFO, LIFO, Moving_Average |
| `default_uom` | string | No | max: 50 chars |
| `sales_tax_template_id` | UUID | No | Dropdown from tax templates |
| `purchase_tax_template_id` | UUID | No | Dropdown from tax templates |
| `is_active` | boolean | No (default: true) | Checkbox |

---

## 4. Stock Entries (Create / Edit)

**Source**: `core-service/app/schemas/stock_entry.py` → `StockEntryCreate`, `StockEntryUpdate`

### Stock Entry Header

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `stock_entry_no` | string | No (auto-generated) | min: 1 char (if provided), max: 100 chars |
| `stock_entry_type` | string | ⚠️ Yes | Allowed: material_receipt, material_issue, material_transfer, manufacture, repack |
| `from_warehouse_id` | UUID | Conditional | Required for material_issue, material_transfer |
| `to_warehouse_id` | UUID | Conditional | Required for material_receipt, material_transfer |
| `posting_date` | datetime | ⚠️ Yes | Must be valid date |
| `posting_time` | string | No | max: 10 chars (format: HH:MM) |
| `status` | string | Yes (default: "draft") | Allowed: draft, submitted, cancelled |
| `reference_type` | string | No | max: 50 chars |
| `reference_id` | UUID | No | Valid reference UUID |
| `remarks` | string | No | max: 1000 chars |
| `total_value` | decimal | No | Computed field |
| `expense_account_id` | UUID | No | Dropdown from accounts |
| `cost_center_id` | UUID | No | Dropdown |

### Stock Entry Items (Line Items)

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `item_id` | UUID | ⚠️ Yes | Must select valid item |
| `source_warehouse_id` | UUID | Conditional | Required for issue/transfer |
| `target_warehouse_id` | UUID | Conditional | Required for receipt/transfer |
| `qty` | decimal | ⚠️ Yes | Must be > 0 (strictly positive) |
| `uom` | string | ⚠️ Yes | min: 1 char, max: 50 chars |
| `basic_rate` | decimal | No | If provided, must be ≥ 0 |
| `valuation_rate` | decimal | No | If provided, must be ≥ 0 |
| `batch_no` | string | No | max: 100 chars |
| `serial_nos` | array of strings | No | Each serial number as string |
| `description` | string | No | max: 1000 chars |
| `extra_data` | dict | No | Free text |

### Business Rules
- At least 1 line item is required
- `from_warehouse_id` is required when `stock_entry_type` is "material_issue" or "material_transfer"
- `to_warehouse_id` is required when `stock_entry_type` is "material_receipt" or "material_transfer"

---

## 5. Customers (Create / Edit)

**Source**: `core-service/app/schemas/customer.py` → `CustomerCreate`, `CustomerUpdate`

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `customer_name` | string | ⚠️ Yes | min: 1 char, max: 255 chars |
| `customer_code` | string | No | max: 50 chars |
| `email` | string | No | max: 255 chars, must be valid email format |
| `phone` | string | No | max: 50 chars |
| `address` | string | No | max: 1000 chars |
| `address_line1` | string | No | max: 255 chars |
| `address_line2` | string | No | max: 255 chars |
| `city` | string | No | max: 100 chars |
| `state` | string | No | max: 100 chars |
| `postal_code` | string | No | max: 20 chars |
| `country` | string | No | max: 100 chars |
| `tax_number` | string | No | max: 50 chars |
| `status` | string | Yes (default: "active") | Allowed: active, inactive, blocked |
| `credit_limit` | decimal | No (default: 0) | Must be ≥ 0 |
| `outstanding_balance` | decimal | No (default: 0) | Must be ≥ 0 |

---

## 6. Quotations (Create / Edit)

**Source**: `core-service/app/schemas/quotation.py` → `QuotationCreate`, `QuotationUpdate`

### Quotation Header

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `quotation_no` | string | No (auto-generated) | min: 1 char (if provided), max: 100 chars |
| `customer_id` | UUID | ⚠️ Yes | Must select valid customer |
| `quotation_date` | datetime | ⚠️ Yes | Must be valid date |
| `valid_until` | datetime | No | Must be ≥ quotation_date |
| `status` | string | Yes (default: "draft") | Allowed: draft, sent, accepted, rejected, expired |
| `grand_total` | decimal | No (default: 0) | Computed from line items |
| `currency` | string | Yes (default: "INR") | max: 10 chars |
| `remarks` | string | No | max: 1000 chars |
| `discount_type` | string | No (default: "percentage") | Allowed: flat, percentage |
| `discount_value` | decimal | No (default: 0) | Must be ≥ 0 |
| `discount_amount` | decimal | No (default: 0) | Must be ≥ 0 (computed) |

### Quotation Line Items

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `item_id` | UUID | ⚠️ Yes | Must select valid item |
| `qty` | decimal | ⚠️ Yes | Must be > 0 (strictly positive) |
| `uom` | string | ⚠️ Yes | min: 1 char, max: 50 chars |
| `rate` | decimal | ⚠️ Yes | Must be ≥ 0 |
| `amount` | decimal | ⚠️ Yes | Must be ≥ 0 (qty × rate) |
| `sort_order` | integer | No (default: 0) | Integer |
| `tax_template_id` | UUID | No | Auto-calculated from item if omitted |
| `tax_rate` | decimal | No (default: 0) | Must be ≥ 0 |
| `tax_amount` | decimal | No (default: 0) | Must be ≥ 0 |
| `total_amount` | decimal | No (default: 0) | Must be ≥ 0 (amount - discount + tax) |
| `discount_type` | string | No (default: "percentage") | Allowed: flat, percentage |
| `discount_value` | decimal | No (default: 0) | Must be ≥ 0 |
| `discount_amount` | decimal | No (default: 0) | Must be ≥ 0 |

### Business Rules
- At least 1 line item should be present
- `valid_until` must be on or after `quotation_date`
- If `discount_type` is "percentage", `discount_value` must be 0–100

---

## 7. Sales Orders (Create / Edit)

**Source**: `core-service/app/schemas/sales_order.py` → `SalesOrderCreate`, `SalesOrderUpdate`

### Sales Order Header

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `sales_order_no` | string | No (auto-generated) | min: 1 char (if provided), max: 100 chars |
| `customer_id` | UUID | ⚠️ Yes | Must select valid customer |
| `order_date` | datetime | ⚠️ Yes | Must be valid date |
| `delivery_date` | datetime | No | Must be ≥ order_date |
| `status` | string | Yes (default: "draft") | Allowed: draft, confirmed, partially_delivered, delivered, closed, cancelled |
| `grand_total` | decimal | No (default: 0) | Computed from line items |
| `currency` | string | Yes (default: "INR") | max: 10 chars |
| `discount_type` | string | No (default: "percentage") | Allowed: flat, percentage |
| `discount_value` | decimal | No (default: 0) | Must be ≥ 0 |
| `discount_amount` | decimal | No (default: 0) | Must be ≥ 0 (computed) |
| `reference_type` | string | No | max: 50 chars |
| `reference_id` | UUID | No | Valid reference |
| `remarks` | string | No | max: 1000 chars |

### Sales Order Line Items

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `item_id` | UUID | ⚠️ Yes | Must select valid item |
| `qty` | decimal | ⚠️ Yes | Must be > 0 (strictly positive) |
| `uom` | string | ⚠️ Yes | min: 1 char, max: 50 chars |
| `rate` | decimal | ⚠️ Yes | Must be ≥ 0 |
| `amount` | decimal | ⚠️ Yes | Must be ≥ 0 (qty × rate) |
| `sort_order` | integer | No (default: 0) | Integer |
| `tax_template_id` | UUID | No | Auto-calculated from item if omitted |
| `tax_rate` | decimal | No (default: 0) | Must be ≥ 0 |
| `tax_amount` | decimal | No (default: 0) | Must be ≥ 0 |
| `total_amount` | decimal | No (default: 0) | Must be ≥ 0 |
| `discount_type` | string | No (default: "percentage") | Allowed: flat, percentage |
| `discount_value` | decimal | No (default: 0) | Must be ≥ 0 |
| `discount_amount` | decimal | No (default: 0) | Must be ≥ 0 |

### Business Rules
- At least 1 line item should be present
- `delivery_date` must be on or after `order_date`
- If `discount_type` is "percentage", `discount_value` must be 0–100

---

## 8. Pick Lists (Create / Edit)

**Source**: `core-service/app/schemas/pick_list.py` → `PickListCreate`, `PickListUpdate`

### Pick List Header

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `pick_list_no` | string | No (auto-generated) | min: 1 char (if provided), max: 100 chars |
| `warehouse_id` | UUID | ⚠️ Yes | Must select valid warehouse |
| `status` | string | Yes (default: "draft") | Allowed: draft, in_progress, completed, cancelled |
| `pick_date` | datetime | No | Must be valid date |
| `reference_type` | string | No | max: 50 chars |
| `reference_id` | UUID | No | Valid reference |
| `remarks` | string | No | max: 1000 chars |

### Pick List Items

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `item_id` | UUID | ⚠️ Yes | Must select valid item |
| `warehouse_id` | UUID | ⚠️ Yes | Must select valid warehouse |
| `qty` | decimal | ⚠️ Yes | Must be > 0 (strictly positive) |
| `uom` | string | ⚠️ Yes | min: 1 char, max: 50 chars |
| `batch_no` | string | No | max: 100 chars |
| `serial_nos` | array of strings | No | Each serial number as string |
| `sort_order` | integer | No (default: 0) | Integer |

### Business Rules
- At least 1 line item is required

---

## 9. Delivery Notes (Create / Edit)

**Source**: `core-service/app/schemas/delivery_note.py` → `DeliveryNoteCreate`, `DeliveryNoteUpdate`

### Delivery Note Header

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `delivery_note_no` | string | No (auto-generated) | min: 1 char (if provided), max: 100 chars |
| `customer_id` | UUID | ⚠️ Yes | Must select valid customer |
| `delivery_date` | datetime | ⚠️ Yes | Must be valid date |
| `status` | string | Yes (default: "draft") | Allowed: draft, submitted, cancelled |
| `warehouse_id` | UUID | No | Dropdown from warehouses |
| `pick_list_id` | UUID | No | Reference to pick list |
| `reference_type` | string | No | max: 50 chars |
| `reference_id` | UUID | No | Valid reference |
| `remarks` | string | No | max: 1000 chars |

### Delivery Note Items

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `item_id` | UUID | ⚠️ Yes | Must select valid item |
| `qty` | decimal | ⚠️ Yes | Must be > 0 (strictly positive) |
| `uom` | string | ⚠️ Yes | min: 1 char, max: 50 chars |
| `rate` | decimal | No | If provided, must be ≥ 0 |
| `amount` | decimal | No | If provided, must be ≥ 0 |
| `warehouse_id` | UUID | No | Dropdown from warehouses |
| `batch_no` | string | No | max: 100 chars |
| `serial_nos` | array of strings | No | Each serial number as string |
| `sort_order` | integer | No (default: 0) | Integer |

### Business Rules
- At least 1 line item is required

---

## 10. Invoices (Create / Edit)

**Source**: `core-service/app/schemas/invoice.py` → `InvoiceCreate`, `InvoiceUpdate`, `InvoiceItemCreate`

### Invoice Header

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `invoice_no` | string | No (auto-generated) | min: 1 char (if provided), max: 100 chars |
| `invoice_type` | string | ⚠️ Yes | Allowed: sales, purchase, Sales, Purchase |
| `party_id` | UUID | ⚠️ Yes | Must select valid customer/supplier |
| `party_type` | string | ⚠️ Yes | min: 1 char, max: 20 chars. Allowed: Customer, Supplier |
| `posting_date` | datetime | ⚠️ Yes | Must be valid date |
| `due_date` | datetime | No | Must be ≥ posting_date |
| `status` | string | Yes (default: "draft") | Allowed: draft, submitted, pending, paid, partial, overdue, cancelled |
| `grand_total` | decimal | No (default: 0) | Computed from line items |
| `outstanding_amount` | decimal | No (default: 0) | Computed |
| `currency` | string | Yes (default: "INR") | max: 10 chars |
| `discount_type` | string | No (default: "percentage") | Allowed: flat, percentage |
| `discount_value` | decimal | No (default: 0) | Must be ≥ 0 |
| `reference_type` | string | No | max: 50 chars |
| `reference_id` | UUID | No | Valid reference |
| `remarks` | string | No | max: 1000 chars |

### Invoice Line Items

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `item_id` | UUID | No | Select from items (optional for manual entry) |
| `item_code` | string | No | max: 100 chars |
| `item_name` | string | No | max: 255 chars |
| `description` | string | No | max: 1000 chars |
| `qty` | decimal | ⚠️ Yes | Must be > 0 (strictly positive) |
| `uom` | string | Yes (default: "Unit") | max: 50 chars |
| `rate` | decimal | No | Must be ≥ 0 |
| `amount` | decimal | No | Must be ≥ 0 |
| `sort_order` | integer | No | Integer |
| `tax_template_id` | string | No | Tax template reference |
| `tax_rate` | string | No | Numeric string |
| `tax_amount` | string | No | Numeric string |
| `discount_type` | string | No | Allowed: flat, percentage |
| `discount_value` | decimal | No | Must be ≥ 0 |
| `discount_amount` | decimal | No | Must be ≥ 0 |
| `total_amount` | string | No | Computed |

### Business Rules
- At least 1 line item is required
- `due_date` must be on or after `posting_date`
- `party_type` must match `invoice_type` (sales → Customer, purchase → Supplier)

---

## 11. Payments (Create / Edit)

**Source**: `core-service/app/schemas/payment_entry.py` → `PaymentEntryCreate`, `PaymentEntryUpdate`

### Payment Entry

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `payment_type` | string | ⚠️ Yes | Allowed: Customer_Payment, Supplier_Payment |
| `party_id` | UUID | ⚠️ Yes | Must select valid customer/supplier |
| `amount` | decimal | ⚠️ Yes | Must be > 0, max 2 decimal places |
| `currency_code` | string | Yes (default: "USD") | Exactly 3 uppercase letters (ISO 4217) |
| `payment_date` | datetime | ⚠️ Yes | Must be valid date, cannot be more than 30 days in the future |
| `payment_mode` | string | ⚠️ Yes | Allowed: Cash, Check, Bank_Transfer |
| `reference_no` | string | No | max: 100 chars |
| `bank_account_id` | UUID | Conditional | Required when payment_mode is "Bank_Transfer" |

### Cancel Payment

| Field | Type | Required | Validation Rules |
|-------|------|----------|-----------------|
| `cancellation_reason` | string | ⚠️ Yes | min: 10 chars |

### Business Rules
- `amount` must be > 0 with max 2 decimal places
- `currency_code` must be exactly 3 uppercase alphabetic characters
- `payment_date` cannot be more than 30 days in the future
- `bank_account_id` is required when `payment_mode` is "Bank_Transfer"
- Cancellation reason must be at least 10 characters

---

## Cross-Feature Validation Summary

### Common Patterns

| Pattern | Fields Affected | Rule |
|---------|----------------|------|
| Quantity fields | qty in all line items | Must be > 0 (strictly positive) |
| Rate/Amount fields | rate, amount, grand_total | Must be ≥ 0 |
| Discount percentage | discount_value when type=percentage | Must be 0–100 |
| Discount flat | discount_value when type=flat | Must be ≥ 0 |
| Document numbers | *_no fields | Auto-generated; if manual, min 1 char, max 100 chars |
| Status fields | All status dropdowns | Must match allowed enum values (regex pattern) |
| Date ordering | valid_until, delivery_date, due_date | Must be ≥ the primary date field |
| UUID references | All *_id fields | Must be valid UUID from dropdown/picker |
| Currency | currency, currency_code | max 10 chars or exactly 3 uppercase letters |

### Recommended UX Patterns

1. **Inline validation**: Show errors on blur for text fields, on change for selects
2. **Submit blocking**: Disable submit button until all required fields pass validation
3. **Error messages**: Show field-specific error messages below each invalid field
4. **Character counters**: Show remaining characters for fields with max_length
5. **Computed fields**: Auto-calculate amount, tax_amount, total_amount, grand_total
6. **Conditional fields**: Show/hide fields based on toggles (e.g., reorder fields only when enable_auto_reorder is true)
7. **Line item minimum**: Validate at least 1 line item exists before submission for Quotations, Sales Orders, Stock Entries, Pick Lists, Delivery Notes, and Invoices

---

## Status Enum Reference

| Feature | Allowed Statuses |
|---------|-----------------|
| Items | ACTIVE, INACTIVE |
| Customers | active, inactive, blocked |
| Quotations | draft, sent, accepted, rejected, expired |
| Sales Orders | draft, confirmed, partially_delivered, delivered, closed, cancelled |
| Stock Entries | draft, submitted, cancelled |
| Pick Lists | draft, in_progress, completed, cancelled |
| Delivery Notes | draft, submitted, cancelled |
| Invoices | draft, submitted, pending, paid, partial, overdue, cancelled |
| Payments | Draft, Confirmed, Cancelled |

---

## Discount Type Reference

All features supporting discounts use the same pattern:

| discount_type | discount_value meaning | Validation |
|---------------|----------------------|------------|
| `percentage` | Percentage (0–100) | 0 ≤ value ≤ 100 |
| `flat` | Fixed currency amount | value ≥ 0 |

Applies to: Quotations, Sales Orders, Invoices (both header-level and line-item-level)

---

## Field Length Standards Reference

The following table documents the company-wide field length standards applied across all Inventory & Revenue module schemas. These are enforced at the backend (Pydantic schema) level and must be mirrored on the frontend.

| Field Category | Max Length | Rationale |
|---|---|---|
| **Names** (item_name, customer_name, warehouse name) | 255 | Industry standard for display names; accommodates long product titles |
| **Codes** (item_code, customer_code, warehouse code) | 50–100 | Short identifiers; 50 for user-facing codes, 100 for system-generated |
| **Description** | 1000 | Sufficient for detailed item specs, materials, dimensions |
| **Remarks** | 1000 | Internal notes on transactions; consistent with description |
| **Address (full/combined)** | 1000 | Multi-line addresses with building, floor, landmark details |
| **Address lines** (line1, line2) | 255 | Single address line per field |
| **City / State** | 100 | Covers all international city/state names |
| **Postal code** | 20 | Covers all global postal formats (UK: "SW1A 1AA", Brazil: "01001-000") |
| **Country** | 100 | Longest country name is ~56 chars; 100 provides buffer |
| **Phone** | 50 | International format with country code, extensions |
| **Email** | 255 | RFC 5321 standard maximum |
| **Tax number** | 50 | GST (15), VAT (varies), TIN (varies); 50 covers all |
| **Barcode** | 100 | EAN-13 (13), UPC-A (12), Code128 (up to ~80) |
| **Batch/Serial number series** | 100 | Series prefix patterns (e.g., "BATCH-2024-") |
| **Currency code** | 3–10 | ISO 4217 (3 chars); 10 for display labels |
| **UOM (Unit of Measure)** | 50 | Standard unit names ("Kilogram", "Square Meter") |
| **Reference numbers** (check no, UTR, doc no) | 100 | Bank references, document numbers |
| **Image URL** | 500 | Standard CDN URLs; increase to 2048 if using signed URLs |
| **Contact name** | 255 | Full names with titles |
| **Document numbers** (invoice_no, quotation_no, etc.) | 100 | Auto-generated with prefix + date + sequence |
| **Reference type** | 50 | Short type identifiers ("sales_order", "delivery_note") |

### Design Principles

1. **Consistency**: Same field type = same limit across all features (e.g., all `description` fields are 1000, all `remarks` are 1000)
2. **Safety margin**: Limits are set 2–3x above typical usage to avoid user frustration while preventing abuse
3. **Database alignment**: These limits should match the database column sizes (VARCHAR lengths in migrations)
4. **No unbounded strings**: Every user-input text field has an explicit max_length to prevent payload abuse and ensure predictable storage
5. **Numeric precision**: Monetary amounts use Decimal with max 2 decimal places; quantities allow up to 6 decimal places for fractional units

### When to Adjust

- **Increase** a limit if users report truncation or if a legitimate use case requires more space
- **Decrease** a limit if the field is being misused (e.g., pasting entire documents into a remarks field)
- **Never remove** a limit — always have an explicit max_length on every text field

---

*Document generated from backend Pydantic schemas. Last updated: May 2026*
