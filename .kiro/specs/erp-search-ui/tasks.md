# Implementation Plan: ERP Search UI

## Overview

This implementation plan breaks down the ERP search UI feature into discrete, incremental coding tasks. The plan follows a bottom-up approach, starting with foundational utilities and hooks, then building reusable components, and finally integrating everything into the application.

Each task builds on previous tasks, ensuring no orphaned code. All tasks are required for comprehensive implementation including full test coverage.

## Tasks

- [x] 1. Set up project structure and TypeScript types
  - Create `apps/platform/src/app/features/search/` directory structure
  - Create `types/search.types.ts` with all TypeScript interfaces (SearchRequest, SearchResponse, SearchResult, EntityTypeConfig, RecentSearch)
  - Create `constants/entityTypes.ts` with ENTITY_TYPE_CONFIGS mapping
  - Create `constants/searchKeys.ts` with React Query key factory functions
  - _Requirements: 3.6, 10.1, 10.2, 10.6_

- [ ] 2. Implement search API client service
  - [x] 2.1 Create SearchService class in `services/search.service.ts`
    - Implement `globalSearch(request: SearchRequest): Promise<SearchResponse>` method
    - Implement `localSearch(entityType: string, request: SearchRequest): Promise<SearchResponse>` method
    - Add JWT token retrieval from localStorage or auth context
    - Add Authorization header to all requests
    - Implement error handling for 401, 400, 500, and network errors
    - Map error status codes to user-friendly messages
    - _Requirements: 3.7, 7.2, 7.3, 7.4_

  - [x] 2.2 Write unit tests for SearchService
    - Test successful global search request
    - Test successful local search request
    - Test 401 error handling
    - Test 500 error handling
    - Test network error handling
    - Test Authorization header inclusion
    - _Requirements: 3.7, 7.2, 7.3, 7.4_

- [ ] 3. Implement custom hooks for search functionality
  - [x] 3.1 Create useDebouncedValue hook in `hooks/useDebouncedValue.ts`
    - Accept value and delay parameters
    - Use useState and useEffect to implement debouncing
    - Return debounced value
    - Clean up timeout on unmount
    - _Requirements: 4.1, 4.2, 4.3_

  - [x] 3.2 Write property test for useDebouncedValue
    - **Property 1: Debounced Search Requests**
    - **Validates: Requirements 1.3, 2.1, 4.1, 4.2, 4.3**
    - Generate random keystroke sequences
    - Verify exactly one value update after delay
    - Verify timer resets on new input

  - [x] 3.3 Create useKeyboardShortcut hook in `hooks/useKeyboardShortcut.ts`
    - Accept key, modifiers, and callback parameters
    - Listen to keydown events on document
    - Check for key and modifier combinations
    - Prevent default behavior when shortcut matches
    - Clean up event listener on unmount
    - _Requirements: 1.1, 5.3_

  - [x] 3.4 Write unit tests for useKeyboardShortcut
    - Test Ctrl+K triggers callback
    - Test Cmd+K triggers callback
    - Test Escape triggers callback
    - Test cleanup on unmount
    - _Requirements: 1.1, 5.3_

  - [x] 3.5 Create useRecentSearches hook in `hooks/useRecentSearches.ts`
    - Read from localStorage key `erp_recent_searches`
    - Implement addSearch function (max 5, deduplication, move to top)
    - Implement clearSearches function
    - Return recentSearches array and functions
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.7_

  - [x] 3.6 Write property tests for useRecentSearches
    - **Property 23: Recent Searches Limit**
    - **Validates: Requirements 8.2**
    - Generate random search sequences
    - Verify list never exceeds 5 items
    
  - [x] 3.7 Write property test for recent search deduplication
    - **Property 25: Recent Search Deduplication**
    - **Validates: Requirements 8.4**
    - Generate random queries with duplicates
    - Verify duplicates move to top
    - Verify no duplicate entries exist

  - [x] 3.8 Write property test for recent search eviction
    - **Property 24: Recent Search Eviction**
    - **Validates: Requirements 8.3**
    - Add 6+ searches
    - Verify oldest is removed when limit reached

  - [x] 3.9 Create useSearchNavigation hook in `hooks/useSearchNavigation.ts`
    - Track selectedIndex state
    - Implement handleKeyDown for Arrow Up/Down/Enter
    - Wrap selection at list boundaries
    - Call onSelect callback on Enter
    - _Requirements: 5.1, 5.2_

  - [x] 3.10 Write unit tests for useSearchNavigation
    - Test Arrow Down increments index
    - Test Arrow Up decrements index
    - Test wrapping at boundaries
    - Test Enter calls onSelect
    - _Requirements: 5.1, 5.2_

- [ ] 4. Implement React Query hooks for search
  - [x] 4.1 Create queryClient configuration in `config/queryClient.ts`
    - Configure staleTime: 5 minutes
    - Configure gcTime: 10 minutes
    - Configure retry: 2
    - Configure refetchOnWindowFocus: false
    - _Requirements: 3.2, 3.3_

  - [x] 4.2 Create useGlobalSearch hook in `hooks/useGlobalSearch.ts`
    - Accept query parameter
    - Use useDebouncedValue with 300ms delay
    - Use useQuery with debounced query as key
    - Call SearchService.globalSearch
    - Enable query only when query length >= 2
    - Return data, isLoading, isError, error, refetch
    - _Requirements: 1.3, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 4.3 Write property test for useGlobalSearch caching
    - **Property 8: React Query Caching**
    - **Validates: Requirements 3.2**
    - Execute same query twice within 5 minutes
    - Verify second call uses cached data
    - Verify no second API request

  - [x] 4.4 Write property test for request cancellation
    - **Property 10: Request Cancellation**
    - **Validates: Requirements 3.4**
    - Generate rapid query sequence
    - Verify only latest query completes
    - Verify previous queries are cancelled

  - [x] 4.5 Create useLocalSearch hook in `hooks/useLocalSearch.ts`
    - Accept entityType and query parameters
    - Validate entityType against ENTITY_TYPE_CONFIGS
    - Use useDebouncedValue with 300ms delay
    - Use useQuery with debounced query as key
    - Call SearchService.localSearch
    - Enable query only when query length >= 2
    - Return data, isLoading, isError, error, refetch
    - _Requirements: 2.1, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 4.6 Write unit tests for useLocalSearch
    - Test valid entity type
    - Test invalid entity type throws error
    - Test debouncing behavior
    - Test query enabled only when length >= 2
    - _Requirements: 2.1_

- [x] 5. Checkpoint - Ensure all hooks and utilities are working
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement search result components
  - [x] 6.1 Create SearchResultItem component in `components/SearchResultItem.tsx`
    - Accept result, isHighlighted, onClick, onMouseEnter props
    - Render entity type badge with color from ENTITY_TYPE_CONFIGS
    - Render title in bold
    - Render snippet with highlighted query terms using dangerouslySetInnerHTML
    - Render metadata (format dates, numbers, currency)
    - Apply highlight styles when isHighlighted is true
    - Add ARIA labels for accessibility
    - _Requirements: 6.1, 6.3, 6.7, 5.4_

  - [x] 6.2 Write property test for SearchResultItem rendering
    - **Property 15: Search Result Display Format**
    - **Validates: Requirements 6.1**
    - Generate random search results
    - Verify title, badge, and snippet are rendered
    - Verify all required fields are present

  - [x] 6.3 Write property test for query term highlighting
    - **Property 16: Query Term Highlighting**
    - **Validates: Requirements 6.3**
    - Generate random snippets with query terms
    - Verify query terms are wrapped in <mark> tags

  - [x] 6.4 Write property test for metadata formatting
    - **Property 20: Metadata Formatting**
    - **Validates: Requirements 6.7**
    - Generate random metadata with dates/numbers/currency
    - Verify formatting matches user locale

  - [x] 6.5 Create SearchEmptyState component in `components/SearchEmptyState.tsx`
    - Accept query and suggestions props
    - Display "No results found for '[query]'" message
    - Display suggestions if provided
    - Add appropriate styling
    - _Requirements: 7.5_

  - [x] 6.6 Write unit test for SearchEmptyState
    - Test message displays with query
    - Test suggestions display when provided
    - _Requirements: 7.5_

  - [x] 6.7 Create SearchErrorState component in `components/SearchErrorState.tsx`
    - Accept error and onRetry props
    - Display user-friendly error message based on error type
    - Display retry button
    - Add appropriate styling
    - _Requirements: 7.2, 7.3, 7.4_

  - [x] 6.8 Write unit tests for SearchErrorState
    - Test network error message
    - Test auth error message
    - Test server error message
    - Test retry button calls onRetry
    - _Requirements: 7.2, 7.3, 7.4_

  - [x] 6.9 Create SearchLoadingState component in `components/SearchLoadingState.tsx`
    - Display loading spinner
    - Add appropriate styling and animation
    - _Requirements: 7.1_

- [ ] 7. Implement LocalSearch component
  - [x] 7.1 Create LocalSearch component in `components/LocalSearch.tsx`
    - Accept entityType, onResultsChange, placeholder, className props
    - Use useState for searchQuery
    - Use useLocalSearch hook with entityType and searchQuery
    - Render search input with search icon
    - Render clear button (X icon) when input has value
    - Render inline loading indicator when isLoading
    - Call onResultsChange when data changes
    - Add ARIA labels for accessibility
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.5_

  - [x] 7.2 Write property test for LocalSearch table filtering
    - **Property 6: Local Search Table Filtering**
    - **Validates: Requirements 2.2**
    - Generate random search responses
    - Verify onResultsChange called with correct results
    - Verify only matching records are passed

  - [x] 7.3 Write property test for loading state display
    - **Property 7: Loading State Display**
    - **Validates: Requirements 2.5, 7.1**
    - Simulate loading state
    - Verify loading indicator is visible

  - [x] 7.4 Write unit tests for LocalSearch
    - Test clear button clears input
    - Test clear button calls onResultsChange with empty array
    - Test ARIA labels are present
    - Test loading indicator displays
    - Test error message displays
    - _Requirements: 2.3, 2.4, 2.5, 5.5_

- [ ] 8. Implement GlobalSearch component
  - [x] 8.1 Create GlobalSearch component in `components/GlobalSearch.tsx`
    - Accept isOpen, onClose, onNavigate props
    - Use useState for searchQuery and selectedIndex
    - Use useGlobalSearch hook with searchQuery
    - Use useRecentSearches hook
    - Use useSearchNavigation hook
    - Render modal overlay with backdrop blur
    - Render search input with keyboard shortcut hint (⌘K)
    - Render recent searches when input is empty
    - Render search results grouped by entity type
    - Render SearchLoadingState when isLoading
    - Render SearchEmptyState when no results
    - Render SearchErrorState when isError
    - Handle Escape key to close modal
    - Handle result click to navigate and close
    - Add focus trap within modal
    - Add ARIA labels for accessibility
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 1.10, 5.3, 5.4, 5.6, 5.7_

  - [x] 8.2 Write property test for result grouping
    - **Property 2: Result Grouping by Entity Type**
    - **Validates: Requirements 1.4, 6.2**
    - Generate random responses with mixed entity types
    - Verify results are grouped by entity type
    - Verify each group contains only that entity type

  - [x] 8.3 Write property test for navigation on result click
    - **Property 3: Navigation on Result Click**
    - **Validates: Requirements 1.5**
    - Generate random search results
    - Simulate click on each result
    - Verify navigation is triggered
    - Verify modal closes

  - [x] 8.4 Write property test for recent search execution
    - **Property 4: Recent Search Execution**
    - **Validates: Requirements 1.8, 8.6**
    - Generate random recent searches
    - Simulate click on each recent search
    - Verify input is populated
    - Verify search is executed

  - [x] 8.5 Write property test for error message display
    - **Property 5: Error Message Display**
    - **Validates: Requirements 1.10, 2.7**
    - Generate random error types
    - Verify appropriate error message is displayed

  - [x] 8.6 Write property test for keyboard navigation
    - **Property 12: Keyboard Navigation**
    - **Validates: Requirements 5.1**
    - Generate random result lists
    - Simulate Arrow Up/Down keys
    - Verify selection changes correctly
    - Verify wrapping at boundaries

  - [x] 8.7 Write property test for Enter key navigation
    - **Property 13: Enter Key Navigation**
    - **Validates: Requirements 5.2**
    - Generate random results
    - Highlight each result
    - Simulate Enter key
    - Verify navigation to detail page

  - [x] 8.8 Write property test for ARIA labels
    - **Property 14: ARIA Labels on Interactive Elements**
    - **Validates: Requirements 5.4**
    - Render component
    - Query all interactive elements
    - Verify each has appropriate ARIA label

  - [x] 8.9 Write unit tests for GlobalSearch
    - Test Ctrl+K opens modal
    - Test Cmd+K opens modal
    - Test Escape closes modal
    - Test recent searches display when input empty
    - Test focus management on open/close
    - Test focus trap within modal
    - _Requirements: 1.1, 1.6, 1.7, 5.3, 5.6, 5.7_

- [ ] 9. Implement responsive design and mobile support
  - [x] 9.1 Add responsive styles to GlobalSearch component
    - Add media query for screen width < 768px
    - Set modal to full screen width on mobile
    - Hide keyboard shortcut hint on mobile
    - Stack result information vertically on mobile
    - Ensure touch targets are minimum 44x44px
    - _Requirements: 9.1, 9.3, 9.4, 9.5_

  - [x] 9.2 Add responsive styles to LocalSearch component
    - Add media query for screen width < 768px
    - Adjust input width to fit screen on mobile
    - Ensure touch targets are minimum 44x44px
    - _Requirements: 9.2, 9.3_

  - [x] 9.3 Write property test for mobile full-screen modal
    - **Property 26: Mobile Full-Screen Modal**
    - **Validates: Requirements 9.1**
    - Set viewport width < 768px
    - Verify modal is full screen width

  - [x] 9.4 Write property test for mobile input width
    - **Property 27: Mobile Input Width**
    - **Validates: Requirements 9.2**
    - Set viewport width < 768px
    - Verify input adjusts to screen width

  - [x] 9.5 Write property test for touch target sizes
    - **Property 28: Touch Target Sizes**
    - **Validates: Requirements 9.3**
    - Query all interactive elements
    - Verify each is at least 44x44px

  - [x] 9.6 Write property test for mobile vertical stacking
    - **Property 29: Mobile Vertical Stacking**
    - **Validates: Requirements 9.4**
    - Set viewport width < 768px
    - Verify results stack vertically

- [ ] 10. Implement pagination for search results
  - [x] 10.1 Add pagination logic to GlobalSearch component
    - Display maximum 20 results per page
    - Show pagination controls when total_count > 20
    - Display total count of results
    - Handle page change events
    - Update useGlobalSearch to accept page parameter
    - _Requirements: 6.4, 6.5, 6.6_

  - [x] 10.2 Write property test for pagination limit
    - **Property 17: Pagination Limit**
    - **Validates: Requirements 6.4**
    - Generate responses with > 20 results
    - Verify only 20 results displayed per page

  - [x] 10.3 Write property test for pagination controls display
    - **Property 18: Pagination Controls Display**
    - **Validates: Requirements 6.5**
    - Generate responses with total_count > 20
    - Verify pagination controls are visible

  - [x] 10.4 Write property test for total count display
    - **Property 19: Total Count Display**
    - **Validates: Requirements 6.6**
    - Generate random search responses
    - Verify total count is displayed

- [ ] 11. Implement error logging and monitoring
  - [ ] 11.1 Add error logging to all search operations
    - Log errors to browser console with context
    - Include query, entity type, and error details
    - Add timestamps to log entries
    - _Requirements: 7.6_

  - [ ] 11.2 Write property test for error logging
    - **Property 21: Error Logging**
    - **Validates: Requirements 7.6**
    - Generate random errors
    - Verify each error is logged to console
    - Verify log includes sufficient detail

- [ ] 12. Implement hover prefetch optimization
  - [ ] 12.1 Add hover prefetch to recent searches
    - Use React Query's prefetchQuery
    - Trigger prefetch after 500ms hover
    - Cancel prefetch if hover ends before 500ms
    - _Requirements: 11.6_

  - [ ] 12.2 Write property test for hover prefetch
    - **Property 30: Hover Prefetch**
    - **Validates: Requirements 11.6**
    - Simulate hover on recent search items
    - Verify prefetch occurs after 500ms
    - Verify prefetch is cancelled if hover ends early

- [ ] 13. Checkpoint - Ensure all components are working
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Integrate GlobalSearch into application
  - [x] 14.1 Update Topbar component to integrate GlobalSearch
    - Import GlobalSearch component
    - Add state for isSearchOpen
    - Replace placeholder search input with clickable trigger
    - Add useKeyboardShortcut for Ctrl+K / Cmd+K
    - Render GlobalSearch modal with isOpen and onClose props
    - Implement onNavigate to use react-router navigation
    - _Requirements: 1.1, 1.2, 1.5_

  - [x] 14.2 Write integration test for Topbar search integration
    - Test clicking search input opens modal
    - Test Ctrl+K opens modal
    - Test navigation from search result
    - _Requirements: 1.1, 1.2, 1.5_

- [ ] 15. Create example usage of LocalSearch in data table
  - [ ] 15.1 Create example ItemsTable component with LocalSearch
    - Create `components/examples/ItemsTableWithSearch.tsx`
    - Integrate LocalSearch component with entityType="items"
    - Handle onResultsChange to filter table data
    - Add clear functionality
    - Demonstrate proper usage pattern
    - _Requirements: 2.1, 2.2, 2.3, 2.4_

  - [ ] 15.2 Write integration test for ItemsTable with LocalSearch
    - Test typing in search filters table
    - Test clearing search shows all items
    - Test loading state displays
    - Test error state displays
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [ ] 16. Add authentication token handling
  - [ ] 16.1 Update SearchService to retrieve token from auth context
    - Import useAuth hook or auth context
    - Retrieve access_token from context instead of localStorage
    - Handle missing token gracefully
    - _Requirements: 3.7_

  - [ ] 16.2 Write property test for authentication token inclusion
    - **Property 11: Authentication Token Inclusion**
    - **Validates: Requirements 3.7**
    - Generate random search requests
    - Verify Authorization header is present
    - Verify token format is correct

- [ ] 17. Implement lazy loading for GlobalSearch modal
  - [ ] 17.1 Add React.lazy and Suspense for GlobalSearch
    - Wrap GlobalSearch import with React.lazy
    - Add Suspense boundary with loading fallback
    - Measure bundle size reduction
    - _Requirements: 11.5_

  - [ ] 17.2 Test lazy loading behavior
    - Verify GlobalSearch is not in initial bundle
    - Verify component loads on demand
    - Verify loading fallback displays
    - _Requirements: 11.5_

- [ ] 18. Add React Error Boundary for search components
  - [ ] 18.1 Create SearchErrorBoundary component
    - Implement error boundary for search components
    - Display fallback UI on error
    - Log errors to console
    - Provide retry mechanism
    - _Requirements: 7.6_

  - [ ] 18.2 Wrap search components with error boundary
    - Wrap GlobalSearch in SearchErrorBoundary
    - Wrap LocalSearch in SearchErrorBoundary
    - Test error boundary catches rendering errors
    - _Requirements: 7.6_

- [ ] 19. Final checkpoint - End-to-end testing
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 20. Documentation and code cleanup
  - [ ] 20.1 Add JSDoc comments to all components and hooks
    - Document props, parameters, and return values
    - Add usage examples
    - Document accessibility features
    - _Requirements: All_

  - [ ] 20.2 Create README.md for search feature
    - Document component usage
    - Document hook usage
    - Add code examples
    - Document accessibility features
    - Document performance considerations
    - _Requirements: All_

  - [ ] 20.3 Update main application README
    - Add search feature to feature list
    - Add keyboard shortcuts documentation
    - Add troubleshooting section
    - _Requirements: All_

## Notes

- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties with minimum 100 iterations
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- All components should be accessible (WCAG 2.1 AA compliant)
- All code should be TypeScript with strict type checking
- All API calls should include authentication tokens
- All errors should be logged for debugging
