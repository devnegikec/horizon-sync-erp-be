# Bugfix Requirements Document

## Introduction

This document addresses seven critical issues discovered during testing of the Chart of Accounts feature that impact functionality, data integrity, and UI consistency:

1. **Reports Not Downloading - Login Redirect**: Report generation redirects to login page instead of downloading
2. **Export PDF Not Working**: PDF export functionality fails or produces no output
3. **Configuration Page Has No Features**: System Configuration page appears empty with no configuration options
4. **Default Accounts Infrastructure Not Visible**: No UI interface to configure default accounts
5. **Account Type Color Theme Not Uniform**: Account type colors are inconsistent and distorted across components
6. **Child Accounts Have No Parent Account**: Chart of accounts lacks proper parent-child hierarchy due to wrong seed script
7. **Journal Tab Empty or Unnecessary**: Journal tab in Books page is empty with no controls

These issues prevent users from properly using the Chart of Accounts feature, accessing critical configuration settings, and maintaining data consistency.

## Bug Analysis

### Current Behavior (Defect)

1.1 WHEN user clicks "Generate Report" button in Reports tab THEN the system redirects to login page instead of downloading the report

1.2 WHEN user tries to export reports as PDF THEN the export fails or produces no output

1.3 WHEN user navigates to Configuration/System Configuration page THEN the page appears empty or has no configuration options displayed

1.4 WHEN user looks for default accounts setup in UI THEN there is no visible interface to configure default accounts (e.g., default cash account, default expense account)

1.5 WHEN account type badges are displayed across different components (AccountsTable, AccountManagement stat cards, AccountTreeView) THEN colors appear inconsistent and distorted with different color definitions for the same account types

1.6 WHEN viewing chart of accounts THEN most child accounts show empty parent account field because the admin seed endpoint calls wrong script (scripts/seed_data.py for inventory instead of seed_chart_of_accounts.py)

1.7 WHEN user clicks on Journal tab in Books page THEN the tab is empty with no controls or functionality

### Expected Behavior (Correct)

2.1 WHEN user clicks "Generate Report" button in Reports tab THEN the system SHALL download the report directly without authentication redirect by including proper authentication token in report download request

2.2 WHEN user tries to export reports as PDF THEN the system SHALL generate and download a properly formatted PDF file with report data

2.3 WHEN user navigates to Configuration/System Configuration page THEN the system SHALL display system settings, default accounts setup, and other configuration options

2.4 WHEN user looks for default accounts setup in UI THEN the system SHALL provide a visible interface to set up and manage default accounts (e.g., default cash account, default expense account) within the Configuration page

2.5 WHEN account type badges are displayed across different components THEN the system SHALL use uniform colors consistently across all components (AccountsTable, AccountManagement stat cards, AccountTreeView, etc.)

2.6 WHEN viewing chart of accounts after seeding THEN the system SHALL display accounts with proper parent-child hierarchy (e.g., "1100 - Current Assets" should have parent "1000 - Assets") by calling the correct seed_chart_of_accounts.py script

2.7 WHEN user clicks on Journal tab in Books page THEN the system SHALL either display journal entry UI controls OR the tab SHALL be removed if not required for MVP

### Unchanged Behavior (Regression Prevention)

3.1 WHEN the admin seed data endpoint is called in non-development mode (DEBUG=false) THEN the system SHALL CONTINUE TO return a 403 error preventing unauthorized data seeding

3.2 WHEN the seed script executes successfully THEN the system SHALL CONTINUE TO return a success message with output details and account creation count

3.3 WHEN the seed script times out or fails THEN the system SHALL CONTINUE TO return appropriate error messages with details

3.4 WHEN users interact with the accounts table (sorting, filtering, pagination) THEN the system SHALL CONTINUE TO function correctly with any UI updates

3.5 WHEN the inventory seed script `scripts/seed_data.py` is called directly THEN the system SHALL CONTINUE TO create inventory items (warehouses, item groups, items) as designed

3.6 WHEN users access other tabs in Books page (Chart of Accounts, Reports, Configuration) THEN the system SHALL CONTINUE TO function correctly regardless of Journal tab changes

3.7 WHEN users generate reports in other formats (CSV, Excel) THEN the system SHALL CONTINUE TO work correctly alongside PDF export functionality

3.8 WHEN account type badges are rendered with updated colors THEN the system SHALL CONTINUE TO support both light and dark mode color variants

3.9 WHEN users interact with existing configuration settings (if any) THEN the system SHALL CONTINUE TO save and load those settings correctly

3.10 WHEN default accounts are configured THEN the system SHALL CONTINUE TO validate that selected accounts exist and are of appropriate types
