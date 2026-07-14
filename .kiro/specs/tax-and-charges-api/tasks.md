# Implementation Plan: Tax and Extra Charges API

## Overview

This implementation plan breaks down the Tax and Extra Charges API feature into discrete, incremental coding tasks. The approach follows a bottom-up strategy: first establishing the data layer (models and repositories), then building the service layer (business logic and calculations), and finally implementing the API layer (endpoints and integration).

The implementation will integrate seamlessly with existing transaction documents (Quotations, Sales Orders, Purchase Orders, Invoices) and maintain the established patterns in the codebase.

## Tasks

- [ ] 1. Create database models and migrations
  - [x] 1.1 Create TaxTemplate and TaxRule models
    - Create SQLAlchemy models in `core-service/app/models/tax_template.py`
    - Include all fields: template_code, template_name, tax_category, is_default, applicability_rules (JSONB)
    - Define relationship between TaxTemplate and TaxRule (one-to-many)
    - Add soft delete support with deleted_at timestamp
    - _Requirements: 1.1, 1.2, 1.5, 1.6_
  
  - [x] 1.2 Create ChargeTemplate model
    - Create SQLAlchemy model in `core-service/app/models/charge_template.py`
    - Include fields: template_code, charge_type, calculation_method, fixed_amount, percentage_rate, base_on
    - Include applicability_rules as JSONB
    - Add soft delete support
    - _Requirements: 6.1, 6.2, 6.3, 6.5, 6.6, 6.9_
  
  - [x] 1.3 Create TransactionTaxBreakdown and TransactionChargeBreakdown models
    - Create models in `core-service/app/models/transaction_breakdown.py`
    - TransactionTaxBreakdown: transaction_type, transaction_id, tax_template_id, tax_rule_id, tax_type, tax_rate, taxable_amount, tax_amount, is_compound, sequence
    - TransactionChargeBreakdown: transaction_type, transaction_id, charge_template_id, charge_type, calculation_method, charge_amount, is_auto_calculated
    - _Requirements: 11.1, 11.2, 11.3, 12.1, 12.2_
  
  - [x] 1.4 Create Alembic migration for new tables
    - Generate migration file for tax_templates, tax_rules, charge_templates, transaction_tax_breakdown, transaction_charge_breakdown tables
    - Add indexes on organization_id, tax_type, charge_type, transaction_type, transaction_id
    - Add foreign key constraints to chart_of_accounts
    - _Requirements: 20.3, 20.4_
  
  - [x] 1.5 Create Alembic migration to extend existing tables
    - Add sales_tax_template_id and purchase_tax_template_id to items table
    - Add sales_tax_template_id and purchase_tax_template_id to item_groups table
    - Add default_sales_tax_template_id and default_purchase_tax_template_id to organization_settings table
    - Add is_tax_exempt and tax_exemption_certificate_no to customers table
    - Add net_total, total_tax, total_charges columns to quotations, sales_orders, purchase_orders, invoices tables
    - _Requirements: 4.1, 4.2, 5.1, 13.1_

- [ ] 2. Create repository layer for tax and charge templates
  - [x] 2.1 Implement TaxTemplateRepository
    - Create `core-service/app/repositories/tax_template_repository.py`
    - Implement CRUD methods: create, get_by_id, list_templates, update, soft_delete
    - Implement get_default_template(organization_id, tax_category)
    - Implement get_applicable_template(context) with applicability rules evaluation
    - Add organization_id filtering to all queries
    - _Requirements: 1.1, 1.4, 3.8, 19.1_
  
  - [x] 2.2 Write property test for TaxTemplateRepository
    - **Property 3: Default Template Uniqueness**
    - **Validates: Requirements 1.4**
  
  - [x] 2.3 Implement ChargeTemplateRepository
    - Create `core-service/app/repositories/charge_template_repository.py`
    - Implement CRUD methods: create, get_by_id, list_templates, update, soft_delete
    - Implement get_applicable_charges(context) with applicability rules evaluation
    - Add organization_id filtering to all queries
    - _Requirements: 6.1, 7.8, 19.1_
  
  - [ ] 2.4 Write unit tests for repository layer
    - Test CRUD operations for tax templates
    - Test CRUD operations for charge templates
    - Test applicability rules evaluation
    - Test organization isolation
    - _Requirements: 19.1, 19.2_

- [ ] 3. Implement tax calculation engine
  - [x] 3.1 Create TaxCalculationEngine service
    - Create `core-service/app/services/tax_calculation_engine.py`
    - Implement calculate_taxes(line_items, context) method
    - Implement calculate_line_item_taxes(line_item, tax_template) method
    - Implement apply_compound_taxes(base_amount, non_compound_taxes, compound_tax_rules) method
    - Handle tax exemptions (customer-level and line-item-level)
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 13.2, 13.4_
  
  - [ ] 3.2 Write property test for tax calculation correctness
    - **Property 5: Tax Calculation Correctness**
    - **Validates: Requirements 2.4, 2.5, 8.4, 8.5, 8.6**
  
  - [ ] 3.3 Write property test for tax sequence ordering
    - **Property 6: Tax Calculation Sequence Ordering**
    - **Validates: Requirements 2.7**
  
  - [ ] 3.4 Write property test for tax exemption
    - **Property 12: Tax Exemption Application**
    - **Validates: Requirements 13.2**
  
  - [ ] 3.5 Write unit tests for tax calculation edge cases
    - Test zero tax rate
    - Test 100% tax rate
    - Test empty line items
    - Test single non-compound tax
    - Test multiple compound taxes
    - _Requirements: 8.4, 8.5_

- [ ] 4. Implement charge calculation engine
  - [x] 4.1 Create ChargeCalculationEngine service
    - Create `core-service/app/services/charge_calculation_engine.py`
    - Implement calculate_charges(context, net_total, total_tax) method
    - Implement calculate_single_charge(charge_template, base_amount) method
    - Handle FIXED and PERCENTAGE calculation methods
    - Handle base_on (Net_Total vs Grand_Total) for percentage charges
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5_
  
  - [ ] 4.2 Write property test for charge calculation correctness
    - **Property 10: Charge Calculation Correctness**
    - **Validates: Requirements 9.3, 9.4, 9.5**
  
  - [ ] 4.3 Write unit tests for charge calculation scenarios
    - Test fixed amount charges
    - Test percentage on net total
    - Test percentage on grand total
    - Test multiple charges
    - Test applicability rules
    - _Requirements: 9.3, 9.4, 9.5_

- [ ] 5. Implement tax and charge template services
  - [x] 5.1 Create TaxTemplateService
    - Create `core-service/app/services/tax_template_service.py`
    - Implement create_template(template_data, user_id) with tax rules
    - Implement get_template(template_id, organization_id)
    - Implement update_template(template_id, template_data, user_id)
    - Implement delete_template(template_id, organization_id) with reference checking
    - Implement list_templates(organization_id, filters)
    - Implement set_as_default(template_id, organization_id, tax_category)
    - Implement get_applicable_template(context) using repository
    - _Requirements: 1.1, 1.4, 1.8, 3.8_
  
  - [ ] 5.2 Write property test for template required fields validation
    - **Property 1: Tax Template Required Fields Validation**
    - **Validates: Requirements 1.1**
  
  - [ ] 5.3 Write property test for template structure completeness
    - **Property 2: Tax Template Structure Completeness**
    - **Validates: Requirements 1.2**
  
  - [ ] 5.4 Write property test for referential integrity
    - **Property 4: Tax Template Referential Integrity**
    - **Validates: Requirements 1.8**
  
  - [x] 5.5 Create ChargeTemplateService
    - Create `core-service/app/services/charge_template_service.py`
    - Implement create_template(template_data, user_id)
    - Implement get_template(template_id, organization_id)
    - Implement update_template(template_id, template_data, user_id)
    - Implement delete_template(template_id, organization_id)
    - Implement list_templates(organization_id, filters)
    - Implement get_applicable_charges(context) using repository
    - _Requirements: 6.1, 7.8_
  
  - [ ] 5.6 Write property test for charge template validation
    - **Property 9: Charge Template Validation**
    - **Validates: Requirements 6.4, 6.5**
  
  - [ ] 5.7 Write unit tests for template services
    - Test template creation with valid data
    - Test template creation with missing fields
    - Test default template setting
    - Test template deletion with references
    - _Requirements: 1.1, 1.4, 1.8, 6.4, 6.5_

- [x] 6. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 7. Implement transaction integration service
  - [x] 7.1 Create TransactionIntegrationService
    - Create `core-service/app/services/transaction_integration_service.py`
    - Implement apply_taxes_and_charges(transaction, user_id)
    - Implement recalculate_totals(transaction)
    - Implement persist_tax_breakdown(transaction_id, transaction_type, tax_breakdown, organization_id)
    - Implement persist_charge_breakdown(transaction_id, transaction_type, charge_breakdown, organization_id)
    - Implement copy_taxes_and_charges(source_transaction, target_transaction)
    - _Requirements: 8.7, 8.8, 10.1, 10.2, 11.4, 11.5, 12.3, 12.4, 17.3, 17.4_
  
  - [ ] 7.2 Write property test for transaction totals calculation
    - **Property 11: Transaction Totals Calculation**
    - **Validates: Requirements 8.3, 10.1, 10.6**
  
  - [ ] 7.3 Write property test for document conversion data preservation
    - **Property 14: Document Conversion Data Preservation**
    - **Validates: Requirements 17.3, 17.4**
  
  - [ ] 7.4 Write unit tests for transaction integration
    - Test apply_taxes_and_charges on quotation
    - Test recalculate_totals when line items change
    - Test persist_tax_breakdown
    - Test persist_charge_breakdown
    - Test copy_taxes_and_charges during conversion
    - _Requirements: 8.7, 10.2, 11.4, 12.3, 17.3_

- [ ] 8. Create Pydantic schemas for API requests and responses
  - [x] 8.1 Create tax template schemas
    - Create `core-service/app/schemas/tax_template.py`
    - Define TaxRuleCreate, TaxRuleResponse schemas
    - Define TaxTemplateCreate, TaxTemplateUpdate, TaxTemplateResponse schemas
    - Define TaxTemplateListResponse with pagination
    - Include validation for required fields and enums
    - _Requirements: 1.1, 1.2, 14.1, 14.2, 14.3_
  
  - [ ] 8.2 Create charge template schemas
    - Create `core-service/app/schemas/charge_template.py`
    - Define ChargeTemplateCreate, ChargeTemplateUpdate, ChargeTemplateResponse schemas
    - Define ChargeTemplateListResponse with pagination
    - Include validation for calculation_method-specific fields
    - _Requirements: 6.1, 6.4, 6.5, 15.1, 15.2, 15.3_
  
  - [ ] 8.3 Create tax calculation schemas
    - Create `core-service/app/schemas/tax_calculation.py`
    - Define TaxContext, TaxBreakdownEntry, TaxCalculationResult schemas
    - Define ChargeContext, ChargeBreakdownEntry, ChargeCalculationResult schemas
    - Define CalculateTaxesRequest, CalculateTaxesResponse schemas
    - Define CalculateTotalsRequest, CalculateTotalsResponse schemas
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5_

- [ ] 9. Implement tax template API endpoints
  - [ ] 9.1 Create tax template router
    - Create `core-service/app/api/v1/endpoints/tax_templates.py`
    - Implement POST /api/v1/tax-templates endpoint
    - Implement GET /api/v1/tax-templates endpoint with pagination and filtering
    - Implement GET /api/v1/tax-templates/{id} endpoint
    - Implement PUT /api/v1/tax-templates/{id} endpoint
    - Implement DELETE /api/v1/tax-templates/{id} endpoint
    - Implement GET /api/v1/tax-templates/applicable endpoint
    - Add organization_id validation from authenticated user
    - Add permission checks (tax_template.create, tax_template.read, tax_template.update, tax_template.delete)
    - _Requirements: 14.1, 14.2, 14.3, 14.4, 14.5, 14.6, 14.7, 14.8, 19.6_
  
  - [ ] 9.2 Write integration tests for tax template endpoints
    - Test create template with valid data
    - Test create template with missing fields
    - Test list templates with filters
    - Test get template by id
    - Test update template
    - Test delete template
    - Test get applicable template
    - Test organization isolation
    - _Requirements: 14.1, 14.2, 14.3, 14.7, 19.1_

- [ ] 10. Implement charge template API endpoints
  - [ ] 10.1 Create charge template router
    - Create `core-service/app/api/v1/endpoints/charge_templates.py`
    - Implement POST /api/v1/charge-templates endpoint
    - Implement GET /api/v1/charge-templates endpoint with pagination and filtering
    - Implement GET /api/v1/charge-templates/{id} endpoint
    - Implement PUT /api/v1/charge-templates/{id} endpoint
    - Implement DELETE /api/v1/charge-templates/{id} endpoint
    - Implement GET /api/v1/charge-templates/applicable endpoint
    - Add organization_id validation and permission checks
    - _Requirements: 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 15.7, 15.8, 19.6_
  
  - [ ] 10.2 Write integration tests for charge template endpoints
    - Test create charge template
    - Test list charge templates
    - Test get applicable charges
    - Test organization isolation
    - _Requirements: 15.1, 15.2, 15.6, 19.1_

- [ ] 11. Implement tax calculation API endpoints
  - [ ] 11.1 Create tax calculation router
    - Create `core-service/app/api/v1/endpoints/tax_calculations.py`
    - Implement POST /api/v1/calculate-taxes endpoint
    - Implement POST /api/v1/calculate-charges endpoint
    - Implement POST /api/v1/calculate-totals endpoint
    - All endpoints should perform calculations without persisting data (preview mode)
    - Add organization_id validation
    - _Requirements: 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7_
  
  - [ ] 11.2 Write integration tests for calculation endpoints
    - Test calculate-taxes with various line items
    - Test calculate-charges with different contexts
    - Test calculate-totals end-to-end
    - Test with tax-exempt customers
    - _Requirements: 16.1, 16.3, 16.5_

- [ ] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Integrate taxes and charges into quotation workflow
  - [ ] 13.1 Extend QuotationService to apply taxes and charges
    - Modify `core-service/app/services/quotation_service.py`
    - In create() method, call TransactionIntegrationService.apply_taxes_and_charges()
    - In update() method, call recalculate_totals() when line items change
    - Update _calculate_grand_total() to include taxes and charges
    - Persist tax and charge breakdowns
    - _Requirements: 8.1, 8.2, 8.7, 8.8, 10.1, 10.2, 17.1, 17.2_
  
  - [ ] 13.2 Update quotation response to include tax and charge breakdowns
    - Modify _to_response() in QuotationService to include net_total, total_tax, total_charges, tax_breakdown, charge_breakdown
    - _Requirements: 10.5_
  
  - [ ] 13.3 Write integration tests for quotation with taxes
    - Test create quotation with line items (taxes auto-calculated)
    - Test update quotation line items (taxes recalculated)
    - Test quotation with tax-exempt customer
    - _Requirements: 8.1, 8.2, 10.2, 13.2_

- [ ] 14. Integrate taxes and charges into sales order workflow
  - [ ] 14.1 Extend SalesOrderService to apply taxes and charges
    - Modify `core-service/app/services/sales_order_service.py`
    - In create() method, apply taxes and charges
    - In update() method, recalculate totals when line items change
    - Update _calculate_grand_total() to include taxes and charges
    - _Requirements: 8.1, 8.2, 10.1, 10.2, 17.1, 17.2_
  
  - [ ] 14.2 Update sales order response to include breakdowns
    - Modify _to_response() to include tax and charge breakdowns
    - _Requirements: 10.5_
  
  - [ ] 14.3 Update quotation-to-sales-order conversion to copy taxes and charges
    - Modify convert_to_sales_order() in QuotationService
    - Call TransactionIntegrationService.copy_taxes_and_charges()
    - _Requirements: 17.3_
  
  - [ ] 14.4 Write integration tests for sales order with taxes
    - Test create sales order with taxes
    - Test convert quotation to sales order (taxes copied)
    - _Requirements: 8.1, 17.3_

- [ ] 15. Integrate taxes and charges into invoice workflow
  - [ ] 15.1 Extend invoice models and service
    - Add net_total, total_tax, total_charges columns to invoices table (if not already done in migration)
    - Create or extend InvoiceService to apply taxes and charges
    - _Requirements: 17.1, 17.2_
  
  - [ ] 15.2 Update sales-order-to-invoice conversion to copy taxes and charges
    - Modify convert_to_invoice() in SalesOrderService
    - Call TransactionIntegrationService.copy_taxes_and_charges()
    - _Requirements: 17.4_
  
  - [ ] 15.3 Write integration tests for invoice with taxes
    - Test create invoice with taxes
    - Test convert sales order to invoice (taxes copied)
    - _Requirements: 17.4_

- [ ] 16. Implement tax reporting endpoints
  - [ ] 16.1 Create tax reports router
    - Create `core-service/app/api/v1/endpoints/tax_reports.py`
    - Implement GET /api/v1/reports/tax-summary endpoint
    - Implement GET /api/v1/reports/tax-by-customer endpoint
    - Implement GET /api/v1/reports/tax-by-item endpoint
    - Add date range filtering, tax_type filtering, transaction_type filtering
    - Add organization_id filtering and permission checks (reports.tax.read)
    - _Requirements: 18.1, 18.2, 18.3, 18.4, 18.5, 18.6, 18.7, 18.8, 19.6_
  
  - [ ] 16.2 Write integration tests for tax reports
    - Test tax summary report with date range
    - Test tax by customer report
    - Test tax by item report
    - Test filtering by tax_type and transaction_type
    - _Requirements: 18.1, 18.3, 18.4, 18.5_

- [ ] 17. Create RBAC permissions for tax and charge features
  - [ ] 17.1 Add new permissions to database
    - Create migration or seed script to add permissions:
      - tax_template.create, tax_template.read, tax_template.update, tax_template.delete
      - charge_template.create, charge_template.read, charge_template.update, charge_template.delete
      - transaction.override_tax
      - reports.tax.read
    - _Requirements: 19.7, 19.8, 19.9_
  
  - [ ] 17.2 Update permission checking in endpoints
    - Ensure all tax template endpoints check appropriate permissions
    - Ensure all charge template endpoints check appropriate permissions
    - Ensure tax report endpoints check reports.tax.read permission
    - _Requirements: 14.8, 15.8, 18.8, 19.6_

- [ ] 18. Implement audit logging for tax operations
  - [ ] 18.1 Add audit logging to tax template operations
    - Log template creation, updates, deletions to audit_logs table
    - Include old_values and new_values for updates
    - _Requirements: 20.6_
  
  - [ ] 18.2 Add audit logging for manual tax overrides
    - Log when users manually override calculated taxes
    - Include old_values (calculated) and new_values (manual)
    - _Requirements: 20.7_
  
  - [ ] 18.3 Add calculation metadata to transactions
    - Store calculation timestamp and user_id in transaction extra_data
    - _Requirements: 20.8_

- [ ] 19. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 20. Register routers and update API documentation
  - [ ] 20.1 Register new routers in main API router
    - Add tax_templates, charge_templates, tax_calculations, tax_reports routers to `core-service/app/api/v1/api.py`
    - Ensure proper prefix and tags
  
  - [ ] 20.2 Update OpenAPI documentation
    - Verify all endpoints have proper descriptions
    - Verify request/response schemas are documented
    - Add examples for complex requests (tax templates with rules, calculation requests)

## Notes

- Tasks marked with `*` are optional property-based and unit tests that can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation and provide opportunities for user feedback
- Property tests validate universal correctness properties across randomized inputs
- Unit tests validate specific examples, edge cases, and integration points
- The implementation follows the existing codebase patterns (SQLAlchemy models, repository pattern, service layer, FastAPI routers)
- All database operations use transactions to ensure atomicity
- Multi-tenancy isolation is enforced at every layer (repository, service, API)
- RBAC permissions are checked at the API layer using existing authorization middleware
