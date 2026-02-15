# Requirements Document: Tax and Extra Charges API

## Introduction

This document specifies the requirements for implementing Tax Templates and Extra Charges Templates in the ERP system. These features enable comprehensive tax management and additional charge handling across all transaction documents including Quotations, Sales Orders, Purchase Orders, Invoices, Delivery Notes, and Purchase Receipts.

The system will support flexible tax configurations at multiple levels (organization, item group, item), multiple tax types (GST, VAT, Sales Tax, etc.), compound taxes, and various extra charges (shipping, handling, packaging, insurance) with rule-based applicability.

## Glossary

- **Tax_Template**: A reusable configuration defining tax rules, rates, and applicability conditions
- **Tax_Rule**: An individual tax component within a template (e.g., CGST 9%, SGST 9%)
- **Extra_Charge_Template**: A reusable configuration defining additional charges and their calculation methods
- **Compound_Tax**: A tax calculated on the sum of base amount plus other taxes (tax on tax)
- **Tax_Category**: Classification of tax as Input Tax (purchases) or Output Tax (sales)
- **Tax_Jurisdiction**: Geographic or regulatory scope where a tax applies
- **Applicability_Rule**: Conditions determining when a tax or charge applies (location, item type, order value)
- **Tax_Breakdown**: Detailed line-by-line calculation of taxes for audit and reporting
- **Grand_Total**: Final amount including base amount, taxes, and extra charges
- **Net_Total**: Sum of all line item amounts before taxes and charges
- **Tax_Exemption**: A condition where normally applicable taxes are not charged
- **Organization**: A tenant in the multi-tenant system
- **Item**: A product or service that can be bought or sold
- **Item_Group**: A hierarchical category containing multiple items
- **Transaction_Document**: Any document that can have taxes applied (Quotation, Sales Order, Invoice, etc.)

## Requirements

### Requirement 1: Tax Template Management

**User Story:** As a finance manager, I want to create and manage tax templates, so that I can define reusable tax configurations for different scenarios.

#### Acceptance Criteria

1. WHEN a tax template is created, THE System SHALL require template_name, organization_id, and is_active status
2. THE Tax_Template SHALL include template_code, description, tax_category (Input/Output), and is_default flag
3. THE Tax_Template SHALL support multiple tax rules within a single template
4. WHEN a tax template is marked as default, THE System SHALL unmark any existing default template for the same organization and tax_category
5. THE Tax_Template SHALL store created_by, updated_by, created_at, and updated_at timestamps
6. THE Tax_Template SHALL support extra_data as JSONB for extensibility
7. WHEN a tax template is deleted, THE System SHALL perform soft delete by setting deleted_at timestamp
8. THE System SHALL prevent deletion of tax templates that are referenced by items, item_groups, or active transactions

### Requirement 2: Tax Rules within Templates

**User Story:** As a finance manager, I want to define multiple tax components within a template, so that I can handle complex tax structures like GST (CGST + SGST + IGST).

#### Acceptance Criteria

1. WHEN a tax rule is added to a template, THE System SHALL require tax_type, tax_rate, and account_head_id
2. THE Tax_Rule SHALL include rule_name, description, tax_rate (as percentage), and sequence for calculation order
3. THE Tax_Rule SHALL support is_compound flag to indicate if tax is calculated on base amount plus previous taxes
4. WHEN is_compound is true, THE System SHALL calculate tax on (net_total + sum of all non-compound taxes)
5. WHEN is_compound is false, THE System SHALL calculate tax on net_total only
6. THE Tax_Rule SHALL include account_head_id referencing chart_of_accounts for GL posting
7. THE System SHALL calculate taxes in sequence order, with non-compound taxes before compound taxes
8. THE Tax_Rule SHALL support applicability_conditions as JSONB for conditional application

### Requirement 3: Tax Template Applicability Rules

**User Story:** As a finance manager, I want to define when taxes apply based on conditions, so that I can handle different tax jurisdictions and scenarios.

#### Acceptance Criteria

1. THE Tax_Template SHALL support applicability_rules as JSONB containing conditions
2. WHEN applicability_rules include customer_location, THE System SHALL match against customer shipping address
3. WHEN applicability_rules include supplier_location, THE System SHALL match against supplier address
4. WHEN applicability_rules include item_type, THE System SHALL match against item.item_type
5. WHEN applicability_rules include item_group, THE System SHALL match against item.item_group_id
6. WHEN applicability_rules include transaction_type, THE System SHALL match against document type (Sales/Purchase)
7. WHEN multiple conditions exist in applicability_rules, THE System SHALL require all conditions to match (AND logic)
8. THE System SHALL evaluate applicability_rules before applying taxes to transactions

### Requirement 4: Tax Assignment to Items and Item Groups

**User Story:** As a product manager, I want to assign tax templates to items and item groups, so that taxes are automatically applied when these items are used in transactions.

#### Acceptance Criteria

1. THE Item SHALL include sales_tax_template_id and purchase_tax_template_id as optional foreign keys
2. THE Item_Group SHALL include sales_tax_template_id and purchase_tax_template_id as optional foreign keys
3. WHEN an item has a tax template assigned, THE System SHALL use the item-level template
4. WHEN an item has no tax template but its item_group has one, THE System SHALL inherit the item_group template
5. WHEN neither item nor item_group has a tax template, THE System SHALL use the organization default template if configured
6. THE System SHALL support different tax templates for sales transactions vs purchase transactions
7. WHEN retrieving an item, THE System SHALL return the effective tax template (item > item_group > organization default)

### Requirement 5: Organization-Level Default Tax Templates

**User Story:** As a system administrator, I want to set default tax templates at organization level, so that all transactions have baseline tax configurations.

#### Acceptance Criteria

1. THE Organization_Settings SHALL include default_sales_tax_template_id and default_purchase_tax_template_id
2. WHEN creating a transaction without item-specific taxes, THE System SHALL apply organization default tax template
3. THE System SHALL allow overriding organization defaults at item_group or item level
4. WHEN organization default tax template is updated, THE System SHALL not affect existing transactions
5. THE System SHALL validate that default tax templates belong to the same organization

### Requirement 6: Extra Charge Template Management

**User Story:** As a logistics manager, I want to create and manage extra charge templates, so that I can define reusable configurations for shipping, handling, and other charges.

#### Acceptance Criteria

1. WHEN an extra charge template is created, THE System SHALL require template_name, charge_type, and organization_id
2. THE Extra_Charge_Template SHALL include charge_type (Shipping, Handling, Packaging, Insurance, Custom)
3. THE Extra_Charge_Template SHALL support calculation_method as either FIXED or PERCENTAGE
4. WHEN calculation_method is FIXED, THE System SHALL require fixed_amount
5. WHEN calculation_method is PERCENTAGE, THE System SHALL require percentage_rate and base_on (Net_Total/Grand_Total)
6. THE Extra_Charge_Template SHALL include account_head_id for GL posting
7. THE Extra_Charge_Template SHALL store is_active, created_by, updated_by, created_at, and updated_at
8. THE Extra_Charge_Template SHALL support extra_data as JSONB for extensibility
9. WHEN an extra charge template is deleted, THE System SHALL perform soft delete by setting deleted_at

### Requirement 7: Extra Charge Applicability Rules

**User Story:** As a logistics manager, I want to define when extra charges apply based on conditions, so that charges are automatically calculated based on order characteristics.

#### Acceptance Criteria

1. THE Extra_Charge_Template SHALL support applicability_rules as JSONB containing conditions
2. WHEN applicability_rules include min_order_value, THE System SHALL apply charge only if net_total >= min_order_value
3. WHEN applicability_rules include max_order_value, THE System SHALL apply charge only if net_total <= max_order_value
4. WHEN applicability_rules include customer_location, THE System SHALL match against customer shipping address
5. WHEN applicability_rules include total_weight, THE System SHALL calculate from sum of (item.weight_per_unit × qty)
6. WHEN applicability_rules include shipping_zone, THE System SHALL match against predefined zone mappings
7. WHEN multiple conditions exist, THE System SHALL require all conditions to match (AND logic)
8. THE System SHALL evaluate applicability_rules before applying charges to transactions

### Requirement 8: Applying Taxes to Transaction Documents

**User Story:** As a sales representative, I want taxes to be automatically calculated on quotations and sales orders, so that customers see accurate total amounts including taxes.

#### Acceptance Criteria

1. WHEN a line item is added to a transaction, THE System SHALL determine applicable tax template from item/item_group/organization
2. WHEN calculating taxes, THE System SHALL create tax breakdown entries for each applicable tax rule
3. THE System SHALL calculate net_total as sum of all line item amounts
4. THE System SHALL calculate each tax amount as (net_total × tax_rate / 100) for non-compound taxes
5. THE System SHALL calculate compound tax as ((net_total + sum_of_non_compound_taxes) × tax_rate / 100)
6. THE System SHALL calculate total_tax as sum of all tax amounts
7. THE System SHALL store tax breakdown with tax_template_id, tax_rule_id, tax_type, tax_rate, taxable_amount, and tax_amount
8. WHEN line items are modified, THE System SHALL recalculate all taxes automatically
9. THE System SHALL support manual override of auto-calculated taxes when user has appropriate permissions

### Requirement 9: Applying Extra Charges to Transaction Documents

**User Story:** As a sales representative, I want extra charges to be automatically calculated on orders, so that shipping and handling costs are included in the total.

#### Acceptance Criteria

1. WHEN creating a transaction, THE System SHALL evaluate all active extra charge templates for applicability
2. WHEN an extra charge template's applicability_rules match, THE System SHALL add the charge to the transaction
3. WHEN calculation_method is FIXED, THE System SHALL use fixed_amount as charge_amount
4. WHEN calculation_method is PERCENTAGE and base_on is Net_Total, THE System SHALL calculate as (net_total × percentage_rate / 100)
5. WHEN calculation_method is PERCENTAGE and base_on is Grand_Total, THE System SHALL calculate as ((net_total + total_tax) × percentage_rate / 100)
6. THE System SHALL store charge breakdown with charge_template_id, charge_type, description, charge_amount, and account_head_id
7. THE System SHALL allow manual addition of extra charges not from templates
8. THE System SHALL allow manual override of auto-calculated charges when user has appropriate permissions
9. WHEN line items or taxes are modified, THE System SHALL recalculate percentage-based charges automatically

### Requirement 10: Grand Total Calculation

**User Story:** As a finance manager, I want accurate grand total calculations including all taxes and charges, so that invoices reflect the correct amount due.

#### Acceptance Criteria

1. THE System SHALL calculate grand_total as net_total + total_tax + total_charges
2. WHEN any line item, tax, or charge changes, THE System SHALL recalculate grand_total automatically
3. THE System SHALL round grand_total to 2 decimal places
4. THE System SHALL store net_total, total_tax, total_charges, and grand_total separately for reporting
5. WHEN retrieving a transaction, THE System SHALL return complete breakdown of net_total, taxes, charges, and grand_total
6. THE System SHALL validate that grand_total equals the sum of components within rounding tolerance

### Requirement 11: Tax Breakdown Storage for Transactions

**User Story:** As an auditor, I want detailed tax breakdowns stored with each transaction, so that I can verify tax calculations and generate tax reports.

#### Acceptance Criteria

1. THE System SHALL create a Transaction_Tax_Breakdown table with transaction_type, transaction_id, tax_template_id, tax_rule_id
2. THE Transaction_Tax_Breakdown SHALL store tax_type, tax_rate, taxable_amount, tax_amount, and account_head_id
3. THE Transaction_Tax_Breakdown SHALL include is_compound flag and sequence for audit trail
4. WHEN a transaction is saved, THE System SHALL persist all tax breakdown entries atomically
5. WHEN a transaction is modified, THE System SHALL delete old tax breakdown entries and create new ones
6. THE System SHALL support querying tax breakdown by transaction_id, tax_type, and date range
7. THE Transaction_Tax_Breakdown SHALL include organization_id for multi-tenancy isolation

### Requirement 12: Extra Charge Breakdown Storage for Transactions

**User Story:** As a finance manager, I want detailed charge breakdowns stored with each transaction, so that I can analyze shipping costs and other charges.

#### Acceptance Criteria

1. THE System SHALL create a Transaction_Charge_Breakdown table with transaction_type, transaction_id, charge_template_id
2. THE Transaction_Charge_Breakdown SHALL store charge_type, description, calculation_method, charge_amount, and account_head_id
3. WHEN a transaction is saved, THE System SHALL persist all charge breakdown entries atomically
4. WHEN a transaction is modified, THE System SHALL delete old charge breakdown entries and create new ones
5. THE System SHALL support querying charge breakdown by transaction_id, charge_type, and date range
6. THE Transaction_Charge_Breakdown SHALL include organization_id for multi-tenancy isolation
7. THE System SHALL store is_auto_calculated flag to distinguish auto vs manual charges

### Requirement 13: Tax Exemption Handling

**User Story:** As a sales representative, I want to mark certain transactions or customers as tax-exempt, so that no taxes are applied when legally appropriate.

#### Acceptance Criteria

1. THE Customer SHALL include is_tax_exempt flag and tax_exemption_certificate_no
2. WHEN a customer is marked tax-exempt, THE System SHALL not apply any sales taxes to transactions for that customer
3. THE System SHALL allow line-item level tax exemption via is_tax_exempt flag on transaction line items
4. WHEN a line item is marked tax-exempt, THE System SHALL exclude it from taxable_amount calculations
5. THE System SHALL store tax_exemption_reason in transaction extra_data for audit purposes
6. THE System SHALL require appropriate permissions to mark transactions or line items as tax-exempt
7. WHEN generating tax reports, THE System SHALL separately identify exempt transactions

### Requirement 14: REST API Endpoints for Tax Templates

**User Story:** As a frontend developer, I want REST API endpoints for tax templates, so that I can build user interfaces for tax configuration.

#### Acceptance Criteria

1. THE System SHALL provide POST /api/v1/tax-templates endpoint to create tax templates with rules
2. THE System SHALL provide GET /api/v1/tax-templates endpoint to list templates with pagination and filtering by tax_category
3. THE System SHALL provide GET /api/v1/tax-templates/{id} endpoint to retrieve a template with all tax rules
4. THE System SHALL provide PUT /api/v1/tax-templates/{id} endpoint to update templates and rules
5. THE System SHALL provide DELETE /api/v1/tax-templates/{id} endpoint to soft delete templates
6. THE System SHALL provide GET /api/v1/tax-templates/applicable endpoint to find applicable templates based on item_id and transaction context
7. WHEN API endpoints are called, THE System SHALL validate organization_id matches authenticated user's organization
8. WHEN API endpoints are called, THE System SHALL require appropriate permissions (tax_template.create, tax_template.read, tax_template.update)

### Requirement 15: REST API Endpoints for Extra Charge Templates

**User Story:** As a frontend developer, I want REST API endpoints for extra charge templates, so that I can build user interfaces for charge configuration.

#### Acceptance Criteria

1. THE System SHALL provide POST /api/v1/charge-templates endpoint to create charge templates
2. THE System SHALL provide GET /api/v1/charge-templates endpoint to list templates with pagination and filtering by charge_type
3. THE System SHALL provide GET /api/v1/charge-templates/{id} endpoint to retrieve a single template
4. THE System SHALL provide PUT /api/v1/charge-templates/{id} endpoint to update templates
5. THE System SHALL provide DELETE /api/v1/charge-templates/{id} endpoint to soft delete templates
6. THE System SHALL provide GET /api/v1/charge-templates/applicable endpoint to find applicable charges based on transaction context
7. WHEN API endpoints are called, THE System SHALL validate organization_id matches authenticated user's organization
8. WHEN API endpoints are called, THE System SHALL require appropriate permissions (charge_template.create, charge_template.read, charge_template.update)

### Requirement 16: Tax Calculation API Endpoints

**User Story:** As a frontend developer, I want API endpoints to calculate taxes for transactions, so that I can show real-time tax calculations as users build orders.

#### Acceptance Criteria

1. THE System SHALL provide POST /api/v1/calculate-taxes endpoint accepting transaction_type, line_items, customer_id, and shipping_address
2. WHEN calculate-taxes is called, THE System SHALL return net_total, tax breakdown by tax_type, total_tax, and grand_total
3. THE System SHALL provide POST /api/v1/calculate-charges endpoint accepting transaction context and line_items
4. WHEN calculate-charges is called, THE System SHALL return applicable charges with amounts and total_charges
5. THE System SHALL provide POST /api/v1/calculate-totals endpoint that returns complete breakdown including taxes and charges
6. THE System SHALL perform calculations without persisting data (preview mode)
7. WHEN API endpoints are called, THE System SHALL validate organization_id matches authenticated user's organization

### Requirement 17: Integration with Existing Transaction Documents

**User Story:** As a system architect, I want tax and charge calculations integrated into existing transaction documents, so that all documents consistently handle taxes and charges.

#### Acceptance Criteria

1. THE System SHALL add net_total, total_tax, total_charges columns to quotations, sales_orders, purchase_orders, invoices tables
2. THE System SHALL modify grand_total calculation to include taxes and charges for all transaction documents
3. WHEN a quotation is converted to sales_order, THE System SHALL copy tax breakdown and charge breakdown
4. WHEN a sales_order is converted to invoice, THE System SHALL copy tax breakdown and charge breakdown
5. WHEN a purchase_order is converted to purchase_receipt, THE System SHALL copy tax breakdown and charge breakdown
6. THE System SHALL ensure transaction_type in breakdown tables matches source document type
7. THE System SHALL maintain referential integrity between transactions and their tax/charge breakdowns
8. WHEN a transaction is deleted, THE System SHALL cascade delete associated tax and charge breakdowns

### Requirement 18: Tax Reporting and Summaries

**User Story:** As a finance manager, I want tax reports and summaries, so that I can file tax returns and analyze tax liabilities.

#### Acceptance Criteria

1. THE System SHALL provide GET /api/v1/reports/tax-summary endpoint with date range and tax_type filters
2. WHEN generating tax summary, THE System SHALL group by tax_type and return total taxable_amount and total_tax_amount
3. THE System SHALL provide GET /api/v1/reports/tax-by-customer endpoint to analyze taxes collected per customer
4. THE System SHALL provide GET /api/v1/reports/tax-by-item endpoint to analyze taxes on different products
5. THE System SHALL support filtering reports by transaction_type (Sales/Purchase) and status
6. THE System SHALL return separate totals for Input Tax (purchases) and Output Tax (sales)
7. WHEN API endpoints are called, THE System SHALL filter by organization_id
8. WHEN API endpoints are called, THE System SHALL require appropriate permissions (reports.tax.read)

### Requirement 19: Multi-Tenancy and Security

**User Story:** As a system administrator, I want proper multi-tenancy isolation and permission controls, so that organizations can only access their own tax configurations.

#### Acceptance Criteria

1. FOR ALL tax template and charge template operations, THE System SHALL filter by organization_id matching authenticated user's organization
2. THE System SHALL prevent users from accessing templates belonging to other organizations
3. THE System SHALL validate that account_head_id references belong to the same organization_id
4. THE System SHALL validate that item_id and item_group_id references belong to the same organization_id
5. THE System SHALL store created_by and updated_by as authenticated user's id
6. THE System SHALL enforce permission checks using existing RBAC system
7. THE System SHALL create new permissions: tax_template.create, tax_template.read, tax_template.update, tax_template.delete
8. THE System SHALL create new permissions: charge_template.create, charge_template.read, charge_template.update, charge_template.delete
9. THE System SHALL create permission: transaction.override_tax for manual tax adjustments

### Requirement 20: Data Integrity and Audit Trail

**User Story:** As a compliance officer, I want complete audit trails for tax configurations and calculations, so that I can demonstrate compliance with tax regulations.

#### Acceptance Criteria

1. THE System SHALL automatically set created_at timestamp when creating templates
2. THE System SHALL automatically update updated_at timestamp when modifying templates
3. THE System SHALL use UUID for all primary keys and foreign keys
4. THE System SHALL use PostgreSQL database with proper indexes on organization_id, tax_type, and charge_type
5. THE System SHALL use database transactions to ensure atomicity of tax calculations and breakdown storage
6. THE System SHALL log all tax template changes to audit_logs table
7. THE System SHALL log all manual tax overrides to audit_logs table with old_values and new_values
8. WHEN tax calculations are performed, THE System SHALL store calculation timestamp and user_id in transaction extra_data
