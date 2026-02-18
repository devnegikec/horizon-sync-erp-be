---
inclusion: manual
---

# Tax and Charges API Context

This steering file provides comprehensive context about the Tax and Charges API for frontend development. Reference this when building UI components for tax templates, charge templates, tax calculations, and related features.

## Quick Links to Spec Files

#[[file:.kiro/specs/tax-and-charges-api/requirements.md]]
#[[file:.kiro/specs/tax-and-charges-api/design.md]]
#[[file:.kiro/specs/tax-and-charges-api/tasks.md]]

## Overview

The Tax and Charges API provides comprehensive tax management and additional charge handling across all transaction documents (Quotations, Sales Orders, Purchase Orders, Invoices). It supports:

- Multi-level tax inheritance (organization → item group → item)
- Complex tax structures including compound taxes (tax on tax)
- Flexible extra charges with rule-based applicability
- Detailed breakdowns for audit and reporting
- Multi-tenancy with organization isolation

## Core Concepts

### Tax Template
A reusable configuration defining tax rules, rates, and applicability conditions. Each template contains:
- **template_code**: Unique identifier within organization
- **template_name**: Display name
- **tax_category**: "Input" (purchases) or "Output" (sales)
- **is_default**: Flag for organization-level default
- **applicability_rules**: JSONB conditions for when tax applies
- **tax_rules**: Array of individual tax components

### Tax Rule
Individual tax component within a template (e.g., CGST 9%, SGST 9%):
- **tax_type**: Type of tax (GST, VAT, CGST, SGST, IGST, Sales Tax, etc.)
- **tax_rate**: Percentage rate
- **is_compound**: Whether calculated on base + other taxes
- **sequence**: Order of calculation
- **account_head_id**: GL account for posting

### Charge Template
Configuration for additional charges (shipping, handling, packaging, insurance):
- **charge_type**: Type of charge
- **calculation_method**: "FIXED" or "PERCENTAGE"
- **fixed_amount**: Amount for fixed charges
- **percentage_rate**: Rate for percentage charges
- **base_on**: "Net_Total" or "Grand_Total" (for percentage)
- **applicability_rules**: JSONB conditions

### Tax Inheritance Hierarchy
1. **Item level**: If item has tax template assigned, use it
2. **Item Group level**: If item has no template, inherit from item_group
3. **Organization level**: If neither has template, use organization default

## API Endpoints Reference

### Tax Template Management

#### Create Tax Template
```http
POST /api/v1/tax-templates
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "template_code": "GST_18",
  "template_name": "GST 18%",
  "description": "Standard GST rate for most goods",
  "tax_category": "Output",
  "is_default": false,
  "is_active": true,
  "applicability_rules": {
    "transaction_type": "Sales",
    "customer_location": {
      "country": "IN"
    }
  },
  "tax_rules": [
    {
      "rule_name": "CGST",
      "tax_type": "CGST",
      "tax_rate": 9.00,
      "account_head_id": "uuid",
      "is_compound": false,
      "sequence": 1
    },
    {
      "rule_name": "SGST",
      "tax_type": "SGST",
      "tax_rate": 9.00,
      "account_head_id": "uuid",
      "is_compound": false,
      "sequence": 2
    }
  ]
}
```

**Response: 201 Created**
```json
{
  "id": "uuid",
  "template_code": "GST_18",
  "template_name": "GST 18%",
  "organization_id": "uuid",
  "tax_category": "Output",
  "is_default": false,
  "is_active": true,
  "tax_rules": [...],
  "created_at": "2024-01-15T10:00:00Z",
  "created_by": "uuid"
}
```

#### List Tax Templates
```http
GET /api/v1/tax-templates?tax_category=Output&is_active=true&page=1&limit=20
Authorization: Bearer {token}
```

**Query Parameters:**
- `tax_category`: Filter by "Input" or "Output"
- `is_active`: Filter by active status
- `page`: Page number (default: 1)
- `limit`: Items per page (default: 20)

**Response: 200 OK**
```json
{
  "data": [
    {
      "id": "uuid",
      "template_code": "GST_18",
      "template_name": "GST 18%",
      "tax_category": "Output",
      "is_default": false,
      "is_active": true,
      "tax_rules_count": 2
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 5,
    "pages": 1
  }
}
```

#### Get Tax Template by ID
```http
GET /api/v1/tax-templates/{id}
Authorization: Bearer {token}
```

**Response: 200 OK**
```json
{
  "id": "uuid",
  "template_code": "GST_18",
  "template_name": "GST 18%",
  "organization_id": "uuid",
  "tax_category": "Output",
  "is_default": false,
  "is_active": true,
  "applicability_rules": {...},
  "tax_rules": [
    {
      "id": "uuid",
      "rule_name": "CGST",
      "tax_type": "CGST",
      "tax_rate": 9.00,
      "account_head_id": "uuid",
      "is_compound": false,
      "sequence": 1
    }
  ],
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

#### Update Tax Template
```http
PUT /api/v1/tax-templates/{id}
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:** (partial update supported)
```json
{
  "template_name": "GST 18% Updated",
  "is_active": true,
  "tax_rules": [...]
}
```

#### Delete Tax Template
```http
DELETE /api/v1/tax-templates/{id}
Authorization: Bearer {token}
```

**Response: 204 No Content** (soft delete)

**Error Response: 409 Conflict** (if template is referenced)
```json
{
  "error": {
    "code": "TAX_TEMPLATE_IN_USE",
    "message": "Cannot delete tax template that is referenced by items",
    "details": {
      "template_id": "uuid",
      "referenced_by": {
        "items": ["item_id_1", "item_id_2"],
        "item_groups": [],
        "transactions": []
      }
    }
  }
}
```

#### Get Applicable Tax Template
```http
GET /api/v1/tax-templates/applicable?item_id={uuid}&transaction_type=Sales&customer_id={uuid}
Authorization: Bearer {token}
```

**Query Parameters:**
- `item_id`: Item to get tax template for
- `transaction_type`: "Sales" or "Purchase"
- `customer_id`: Customer for the transaction (optional)

**Response: 200 OK**
```json
{
  "template": {
    "id": "uuid",
    "template_code": "GST_18",
    "template_name": "GST 18%",
    "tax_rules": [...]
  },
  "source": "item"  // or "item_group" or "organization_default"
}
```

### Charge Template Management

#### Create Charge Template
```http
POST /api/v1/charge-templates
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "template_code": "SHIP_STANDARD",
  "template_name": "Standard Shipping",
  "charge_type": "Shipping",
  "description": "Standard shipping charges",
  "calculation_method": "PERCENTAGE",
  "percentage_rate": 5.00,
  "base_on": "Net_Total",
  "account_head_id": "uuid",
  "is_active": true,
  "applicability_rules": {
    "min_order_value": 0,
    "max_order_value": 1000
  }
}
```

**Charge Types:**
- `Shipping`
- `Handling`
- `Packaging`
- `Insurance`
- `Custom`

**Calculation Methods:**
- `FIXED`: Use `fixed_amount`
- `PERCENTAGE`: Use `percentage_rate` and `base_on`

**Base On (for PERCENTAGE):**
- `Net_Total`: Calculate on line items total before taxes
- `Grand_Total`: Calculate on total including taxes

#### List Charge Templates
```http
GET /api/v1/charge-templates?charge_type=Shipping&is_active=true
Authorization: Bearer {token}
```

#### Get Applicable Charges
```http
POST /api/v1/charge-templates/applicable
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "transaction_type": "Sales_Order",
  "net_total": 5000.00,
  "customer_id": "uuid",
  "shipping_address": {
    "country": "US",
    "state": "CA"
  },
  "total_weight": 50.5
}
```

**Response: 200 OK**
```json
{
  "applicable_charges": [
    {
      "template_id": "uuid",
      "template_code": "SHIP_STANDARD",
      "charge_type": "Shipping",
      "calculated_amount": 250.00
    }
  ]
}
```

### Tax Calculation Endpoints

#### Calculate Taxes (Preview)
```http
POST /api/v1/calculate-taxes
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "transaction_type": "Sales_Order",
  "customer_id": "uuid",
  "line_items": [
    {
      "item_id": "uuid",
      "qty": 10,
      "rate": 100.00,
      "amount": 1000.00
    }
  ],
  "shipping_address": {
    "country": "IN",
    "state": "MH"
  }
}
```

**Response: 200 OK**
```json
{
  "net_total": 1000.00,
  "tax_breakdown": [
    {
      "tax_type": "CGST",
      "tax_rate": 9.00,
      "taxable_amount": 1000.00,
      "tax_amount": 90.00,
      "is_compound": false
    },
    {
      "tax_type": "SGST",
      "tax_rate": 9.00,
      "taxable_amount": 1000.00,
      "tax_amount": 90.00,
      "is_compound": false
    }
  ],
  "total_tax": 180.00,
  "taxes_by_type": {
    "CGST": 90.00,
    "SGST": 90.00
  }
}
```

#### Calculate Charges (Preview)
```http
POST /api/v1/calculate-charges
Authorization: Bearer {token}
Content-Type: application/json
```

#### Calculate Complete Totals (Preview)
```http
POST /api/v1/calculate-totals
Authorization: Bearer {token}
Content-Type: application/json
```

**Request Body:**
```json
{
  "transaction_type": "Sales_Order",
  "customer_id": "uuid",
  "line_items": [...],
  "shipping_address": {...}
}
```

**Response: 200 OK**
```json
{
  "net_total": 1000.00,
  "tax_breakdown": [...],
  "total_tax": 180.00,
  "charge_breakdown": [
    {
      "charge_type": "Shipping",
      "description": "Standard Shipping",
      "charge_amount": 50.00
    }
  ],
  "total_charges": 50.00,
  "grand_total": 1230.00
}
```

### Tax Reporting Endpoints

#### Tax Summary Report
```http
GET /api/v1/reports/tax-summary?start_date=2024-01-01&end_date=2024-01-31&tax_type=CGST
Authorization: Bearer {token}
```

**Query Parameters:**
- `start_date`: Report start date (required)
- `end_date`: Report end date (required)
- `tax_type`: Filter by specific tax type (optional)
- `transaction_type`: Filter by "Sales" or "Purchase" (optional)

**Response: 200 OK**
```json
{
  "period": {
    "start_date": "2024-01-01",
    "end_date": "2024-01-31"
  },
  "summary": [
    {
      "tax_type": "CGST",
      "total_taxable_amount": 100000.00,
      "total_tax_amount": 9000.00,
      "transaction_count": 50
    }
  ],
  "input_tax_total": 5000.00,
  "output_tax_total": 13000.00,
  "net_tax_liability": 8000.00
}
```

#### Tax by Customer Report
```http
GET /api/v1/reports/tax-by-customer?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {token}
```

**Response: 200 OK**
```json
{
  "data": [
    {
      "customer_id": "uuid",
      "customer_name": "ABC Corp",
      "total_taxable_amount": 50000.00,
      "total_tax_amount": 9000.00,
      "transaction_count": 25
    }
  ]
}
```

#### Tax by Item Report
```http
GET /api/v1/reports/tax-by-item?start_date=2024-01-01&end_date=2024-01-31
Authorization: Bearer {token}
```

## Data Models for Frontend

### Tax Template
```typescript
interface TaxTemplate {
  id: string;
  organization_id: string;
  template_code: string;
  template_name: string;
  description?: string;
  tax_category: 'Input' | 'Output';
  is_default: boolean;
  is_active: boolean;
  applicability_rules: Record<string, any>;
  extra_data: Record<string, any>;
  tax_rules: TaxRule[];
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}

interface TaxRule {
  id: string;
  tax_template_id: string;
  rule_name: string;
  tax_type: string;
  description?: string;
  tax_rate: number;  // Percentage
  account_head_id: string;
  is_compound: boolean;
  sequence: number;
  applicability_conditions?: Record<string, any>;
}
```

### Charge Template
```typescript
interface ChargeTemplate {
  id: string;
  organization_id: string;
  template_code: string;
  template_name: string;
  charge_type: 'Shipping' | 'Handling' | 'Packaging' | 'Insurance' | 'Custom';
  description?: string;
  calculation_method: 'FIXED' | 'PERCENTAGE';
  fixed_amount?: number;
  percentage_rate?: number;
  base_on?: 'Net_Total' | 'Grand_Total';
  account_head_id: string;
  is_active: boolean;
  applicability_rules: Record<string, any>;
  extra_data: Record<string, any>;
  created_by: string;
  updated_by: string;
  created_at: string;
  updated_at: string;
}
```

### Transaction with Taxes and Charges
```typescript
interface Transaction {
  id: string;
  // ... other transaction fields
  net_total: number;
  total_tax: number;
  total_charges: number;
  grand_total: number;
  tax_breakdown: TaxBreakdownEntry[];
  charge_breakdown: ChargeBreakdownEntry[];
}

interface TaxBreakdownEntry {
  tax_template_id: string;
  tax_rule_id: string;
  tax_type: string;
  tax_rate: number;
  taxable_amount: number;
  tax_amount: number;
  is_compound: boolean;
  sequence: number;
  account_head_id: string;
}

interface ChargeBreakdownEntry {
  charge_template_id?: string;
  charge_type: string;
  description: string;
  calculation_method: string;
  charge_amount: number;
  account_head_id: string;
  is_auto_calculated: boolean;
}
```

## Permissions Required

### Tax Template Permissions
- `tax_template.create`: Create new tax templates
- `tax_template.read`: View tax templates
- `tax_template.update`: Modify tax templates
- `tax_template.delete`: Delete tax templates

### Charge Template Permissions
- `charge_template.create`: Create new charge templates
- `charge_template.read`: View charge templates
- `charge_template.update`: Modify charge templates
- `charge_template.delete`: Delete charge templates

### Other Permissions
- `transaction.override_tax`: Manually override calculated taxes
- `reports.tax.read`: Access tax reports

## UI Component Guidelines

### Tax Template Form
**Required Fields:**
- Template Code (unique within organization)
- Template Name
- Tax Category (Input/Output radio buttons)
- At least one Tax Rule

**Tax Rule Fields:**
- Rule Name
- Tax Type (dropdown or autocomplete)
- Tax Rate (percentage input, 0-100)
- Account Head (dropdown from chart of accounts)
- Is Compound (checkbox)
- Sequence (auto-increment or manual)

**Optional Fields:**
- Description
- Is Default (checkbox)
- Is Active (checkbox, default true)
- Applicability Rules (JSON editor or form builder)

### Charge Template Form
**Required Fields:**
- Template Code
- Template Name
- Charge Type (dropdown)
- Calculation Method (FIXED/PERCENTAGE radio)
- Account Head

**Conditional Fields:**
- If FIXED: Fixed Amount (number input)
- If PERCENTAGE: Percentage Rate + Base On (Net_Total/Grand_Total)

### Transaction Forms (Quotation, Sales Order, etc.)
**Display Fields:**
- Net Total (sum of line items)
- Tax Breakdown (expandable table showing each tax)
- Total Tax
- Charge Breakdown (expandable table showing each charge)
- Total Charges
- Grand Total (prominent display)

**Actions:**
- "Recalculate Taxes" button (if manual changes made)
- "Override Tax" button (if user has permission)
- "Add Manual Charge" button

### Tax Reports UI
**Filters:**
- Date Range Picker (start_date, end_date)
- Tax Type Filter (multi-select)
- Transaction Type Filter (Sales/Purchase)
- Customer Filter (for tax-by-customer report)
- Item Filter (for tax-by-item report)

**Display:**
- Summary cards (Total Tax, Input Tax, Output Tax, Net Liability)
- Data table with sorting and pagination
- Export to CSV/Excel button

## Common Validation Rules

### Tax Template
- `template_code`: Required, unique within organization, alphanumeric with hyphens
- `template_name`: Required, max 200 characters
- `tax_category`: Required, must be "Input" or "Output"
- `tax_rules`: At least one rule required
- `tax_rate`: 0-100, up to 2 decimal places

### Charge Template
- `template_code`: Required, unique within organization
- `calculation_method`: Required, "FIXED" or "PERCENTAGE"
- If FIXED: `fixed_amount` required, must be > 0
- If PERCENTAGE: `percentage_rate` required (0-100), `base_on` required

### Calculations
- All amounts rounded to 2 decimal places
- Grand Total = Net Total + Total Tax + Total Charges
- Compound tax calculated on (Net Total + Non-Compound Taxes)

## Error Handling

### Common Error Codes
- `TAX_TEMPLATE_IN_USE`: Cannot delete template referenced by items/transactions
- `DEFAULT_TEMPLATE_EXISTS`: Another default template exists for this category
- `INSUFFICIENT_PERMISSIONS`: User lacks required permission
- `VALIDATION_ERROR`: Input validation failed
- `NOT_FOUND`: Resource not found
- `ORGANIZATION_MISMATCH`: Resource belongs to different organization

### Error Response Format
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      // Additional context
    }
  }
}
```

## Testing Considerations

When testing frontend components:
1. Test with tax-exempt customers (no taxes should apply)
2. Test with compound taxes (verify calculation order)
3. Test with multiple charges (fixed + percentage)
4. Test organization isolation (can't see other org's templates)
5. Test permission checks (buttons disabled without permission)
6. Test validation (required fields, numeric ranges)
7. Test real-time calculation updates
8. Test document conversion (taxes copied correctly)

## Performance Tips

1. **Debounce Calculations**: Don't recalculate on every keystroke
2. **Cache Templates**: Cache active templates in frontend state
3. **Lazy Load**: Load tax breakdown details on expand
4. **Pagination**: Use pagination for template lists
5. **Optimistic Updates**: Show immediate feedback, sync in background

## Related Backend Services

- **TaxCalculationEngine**: Core calculation logic
- **ChargeCalculationEngine**: Charge calculation logic
- **TransactionIntegrationService**: Applies taxes to transactions
- **TaxTemplateService**: Template CRUD operations
- **ChargeTemplateService**: Charge template CRUD operations

## Database Tables

- `tax_templates`: Tax template configurations
- `tax_rules`: Individual tax rules within templates
- `charge_templates`: Charge template configurations
- `transaction_tax_breakdown`: Tax breakdown per transaction
- `transaction_charge_breakdown`: Charge breakdown per transaction
- `items`: Extended with `sales_tax_template_id`, `purchase_tax_template_id`
- `item_groups`: Extended with tax template references
- `customers`: Extended with `is_tax_exempt`, `tax_exemption_certificate_no`
- `quotations`, `sales_orders`, `invoices`: Extended with `net_total`, `total_tax`, `total_charges`
