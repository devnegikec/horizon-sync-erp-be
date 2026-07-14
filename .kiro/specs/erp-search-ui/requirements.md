# Requirements Document

## Introduction

This document specifies the requirements for implementing global and local search functionality in the ERP system UI. The feature provides users with comprehensive search capabilities across all entity types (global search) and within specific data contexts (local search), integrated with the existing Python FastAPI search-service backend.

The implementation will consist of React-based UI components in the horizon-sync frontend (Nx monorepo), utilizing React Query for API integration, and connecting to the existing search-service endpoints for data retrieval.

## Glossary

- **Global_Search**: A search interface accessible from anywhere in the application that searches across all entity types (items, customers, suppliers, invoices, warehouses, stock entries)
- **Local_Search**: A search interface embedded within specific views (tables, lists) that searches only within a single entity type
- **Search_Service**: The Python FastAPI backend service that provides search endpoints at `/search/global` and `/search/{entity_type}`
- **Entity_Type**: A category of business data (e.g., "items", "customers", "suppliers", "invoices", "warehouses", "stock_entries")
- **React_Query**: A data fetching and state management library for React applications
- **Search_Result**: An individual item returned from a search query containing entity_id, entity_type, title, snippet, relevance_score, and metadata
- **Debouncing**: A technique to delay API calls until the user stops typing for a specified duration
- **Keyboard_Shortcut**: A key combination (e.g., Ctrl+K or Cmd+K) that triggers an action
- **Autocomplete**: Suggestions displayed to users as they type in the search input
- **Recent_Searches**: A history of previous search queries stored locally for quick access

## Requirements

### Requirement 1: Global Search Component

**User Story:** As a user, I want to search across all entity types from anywhere in the application, so that I can quickly find any item, customer, supplier, invoice, warehouse, or stock entry without navigating to specific pages.

#### Acceptance Criteria

1. WHEN a user presses Ctrl+K (Windows/Linux) or Cmd+K (Mac), THE Global_Search SHALL open in a modal overlay
2. WHEN a user clicks the search input in the top navigation bar, THE Global_Search SHALL open in a modal overlay
3. WHEN a user types a query in the Global_Search, THE System SHALL send a request to the Search_Service `/search/global` endpoint after 300ms of inactivity
4. WHEN the Search_Service returns results, THE Global_Search SHALL display results grouped by Entity_Type with entity title, snippet, and metadata
5. WHEN a user clicks on a search result, THE System SHALL navigate to the detail page for that entity and close the Global_Search modal
6. WHEN a user presses Escape, THE Global_Search SHALL close
7. WHEN the Global_Search is open, THE System SHALL display the user's 5 most recent searches
8. WHEN a user clicks on a recent search, THE Global_Search SHALL execute that search query
9. WHEN the Search_Service returns zero results, THE Global_Search SHALL display an empty state message with suggestions
10. WHEN the Search_Service returns an error, THE Global_Search SHALL display a user-friendly error message

### Requirement 2: Local Search Component

**User Story:** As a user, I want to search within specific data tables and lists, so that I can quickly filter the visible data to find specific records without leaving the current view.

#### Acceptance Criteria

1. WHEN a user types in a Local_Search input within a data table, THE System SHALL send a request to the Search_Service `/search/{entity_type}` endpoint after 300ms of inactivity
2. WHEN the Search_Service returns results, THE Local_Search SHALL update the table to display only matching records
3. WHEN a user clears the Local_Search input, THE System SHALL display all records in the table
4. WHEN a user clicks the clear button in the Local_Search, THE System SHALL clear the search input and display all records
5. THE Local_Search SHALL display a loading indicator while the search request is in progress
6. WHEN the Search_Service returns zero results, THE Local_Search SHALL display an empty state message in the table
7. WHEN the Search_Service returns an error, THE Local_Search SHALL display a user-friendly error message

### Requirement 3: Backend Integration with React Query

**User Story:** As a developer, I want to use React Query for all search API calls, so that I can leverage caching, automatic retries, and consistent state management across the application.

#### Acceptance Criteria

1. THE System SHALL use React Query's `useQuery` hook for fetching search results
2. THE System SHALL configure React Query to cache search results for 5 minutes
3. THE System SHALL configure React Query to automatically retry failed requests up to 2 times
4. WHEN a search query is executed, THE System SHALL cancel any pending search requests for the same query key
5. THE System SHALL use React Query's `isLoading`, `isError`, and `data` states to manage UI rendering
6. THE System SHALL define TypeScript interfaces for all search request and response payloads matching the Search_Service schemas
7. THE System SHALL include the user's authentication token in all search API requests

### Requirement 4: Search Input Debouncing

**User Story:** As a user, I want the search to wait until I finish typing, so that the system doesn't make excessive API calls while I'm still entering my query.

#### Acceptance Criteria

1. WHEN a user types in any search input, THE System SHALL wait 300ms after the last keystroke before sending a search request
2. WHEN a user types additional characters within the 300ms window, THE System SHALL reset the timer
3. WHEN the debounce timer expires, THE System SHALL send exactly one search request with the current query text
4. THE System SHALL cancel any pending debounced requests when the search input is cleared

### Requirement 5: Keyboard Navigation and Accessibility

**User Story:** As a user, I want to navigate search results using my keyboard, so that I can efficiently interact with the search interface without using a mouse.

#### Acceptance Criteria

1. WHEN the Global_Search is open and results are displayed, THE System SHALL allow users to navigate results using Arrow Up and Arrow Down keys
2. WHEN a user presses Enter on a highlighted result, THE System SHALL navigate to that entity's detail page
3. WHEN a user presses Escape, THE System SHALL close the Global_Search modal
4. THE Global_Search SHALL include ARIA labels for screen readers on all interactive elements
5. THE Local_Search SHALL include ARIA labels for screen readers on the search input and clear button
6. WHEN the Global_Search opens, THE System SHALL automatically focus the search input field
7. WHEN the Global_Search closes, THE System SHALL return focus to the element that triggered it

### Requirement 6: Search Result Display and Formatting

**User Story:** As a user, I want search results to be clearly formatted with relevant information, so that I can quickly identify the correct entity from the results.

#### Acceptance Criteria

1. WHEN displaying a search result, THE System SHALL show the entity title, entity type badge, and a text snippet
2. WHEN displaying Global_Search results, THE System SHALL group results by Entity_Type with section headers
3. WHEN displaying a text snippet, THE System SHALL highlight matching query terms within the snippet
4. WHEN displaying search results, THE System SHALL show a maximum of 20 results per page
5. WHEN there are more than 20 results, THE System SHALL display pagination controls
6. THE System SHALL display the total count of matching results
7. WHEN displaying entity metadata, THE System SHALL format dates, numbers, and currency values according to user locale

### Requirement 7: Loading States and Error Handling

**User Story:** As a user, I want clear feedback when searches are loading or fail, so that I understand the system's status and can take appropriate action.

#### Acceptance Criteria

1. WHEN a search request is in progress, THE System SHALL display a loading spinner in the search results area
2. WHEN a search request fails due to network error, THE System SHALL display "Unable to connect. Please check your connection and try again."
3. WHEN a search request fails due to authentication error, THE System SHALL display "Session expired. Please log in again." and redirect to login after 3 seconds
4. WHEN a search request fails due to server error, THE System SHALL display "Search service unavailable. Please try again later."
5. WHEN a search returns zero results, THE System SHALL display "No results found for '[query]'. Try different keywords or check spelling."
6. THE System SHALL log all search errors to the browser console for debugging

### Requirement 8: Recent Searches History

**User Story:** As a user, I want to see my recent searches, so that I can quickly re-run common queries without retyping them.

#### Acceptance Criteria

1. WHEN a user executes a search in the Global_Search, THE System SHALL store the query text in browser localStorage
2. THE System SHALL maintain a maximum of 5 recent searches per user
3. WHEN storing a new search, THE System SHALL remove the oldest search if the limit is reached
4. WHEN storing a duplicate search, THE System SHALL move it to the top of the recent searches list
5. WHEN the Global_Search opens, THE System SHALL display recent searches if the search input is empty
6. WHEN a user clicks on a recent search, THE System SHALL populate the search input and execute the search
7. THE System SHALL provide a way to clear all recent searches

### Requirement 9: Responsive Design and Mobile Support

**User Story:** As a user on a mobile device, I want the search interface to work well on small screens, so that I can search effectively regardless of device.

#### Acceptance Criteria

1. WHEN the Global_Search is opened on a mobile device (screen width < 768px), THE System SHALL display the modal at full screen width
2. WHEN the Local_Search is displayed on a mobile device, THE System SHALL adjust the input width to fit the screen
3. THE System SHALL use touch-friendly tap targets with minimum 44x44px size for all interactive elements
4. WHEN displaying search results on mobile, THE System SHALL stack result information vertically for readability
5. THE System SHALL hide the keyboard shortcut hint (⌘K) on mobile devices

### Requirement 10: Search Component Reusability

**User Story:** As a developer, I want reusable search components, so that I can easily add search functionality to new pages without duplicating code.

#### Acceptance Criteria

1. THE System SHALL provide a `GlobalSearch` component that can be imported and used in any part of the application
2. THE System SHALL provide a `LocalSearch` component that accepts an `entityType` prop to specify which entity to search
3. THE System SHALL provide a `useGlobalSearch` hook that encapsulates global search logic and state
4. THE System SHALL provide a `useLocalSearch` hook that accepts an `entityType` parameter and encapsulates local search logic
5. THE System SHALL provide TypeScript type definitions for all component props and hook return values
6. THE System SHALL export all search-related types, hooks, and components from a single `@horizon-sync/search` module

### Requirement 11: Performance Optimization

**User Story:** As a user, I want search to be fast and responsive, so that I can find information quickly without waiting.

#### Acceptance Criteria

1. WHEN a user types in a search input, THE System SHALL debounce requests to avoid excessive API calls
2. THE System SHALL use React Query caching to avoid redundant API calls for identical queries within 5 minutes
3. THE System SHALL use React.memo or useMemo to prevent unnecessary re-renders of search result components
4. WHEN rendering large result lists, THE System SHALL implement virtualization if more than 100 results are displayed
5. THE System SHALL lazy-load the Global_Search modal code to reduce initial bundle size
6. THE System SHALL prefetch search results when a user hovers over a recent search for more than 500ms
