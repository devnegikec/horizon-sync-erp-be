# Design Document: ERP Search UI

## Overview

This document describes the technical design for implementing global and local search functionality in the ERP system UI. The solution provides users with two complementary search interfaces:

1. **Global Search**: A command palette-style modal (⌘K/Ctrl+K) accessible from anywhere in the application, searching across all entity types
2. **Local Search**: Embedded search inputs within data tables and list views, filtering specific entity types

The implementation leverages the existing Python FastAPI search-service backend, React Query for data fetching and caching, and follows modern UI patterns inspired by tools like [Linear](https://linear.app), [Superhuman](https://superhuman.com), and [Retool](https://retool.com).

**Key Design Principles:**
- **Performance First**: Debouncing, caching, and optimistic UI updates minimize perceived latency
- **Keyboard-Driven**: Full keyboard navigation support for power users
- **Accessibility**: WCAG 2.1 AA compliant with proper ARIA labels and focus management
- **Reusability**: Composable hooks and components for easy integration across the application
- **Type Safety**: Full TypeScript coverage with strict type checking

## Architecture

### High-Level Component Structure

```
┌─────────────────────────────────────────────────────────────┐
│                     Application Layer                        │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  GlobalSearch    │         │  LocalSearch     │         │
│  │  Component       │         │  Component       │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                            │                    │
│           └────────────┬───────────────┘                    │
│                        │                                    │
│  ┌─────────────────────▼──────────────────────┐            │
│  │         Search Hooks Layer                 │            │
│  │  ┌──────────────┐   ┌──────────────────┐  │            │
│  │  │useGlobalSearch│   │useLocalSearch    │  │            │
│  │  └──────┬───────┘   └────────┬─────────┘  │            │
│  │         │                    │             │            │
│  │         └──────────┬─────────┘             │            │
│  │                    │                       │            │
│  │  ┌─────────────────▼──────────────────┐   │            │
│  │  │    useDebouncedValue Hook          │   │            │
│  │  └─────────────────┬──────────────────┘   │            │
│  └────────────────────┼────────────────────────┘            │
│                       │                                    │
│  ┌────────────────────▼───────────────────────┐            │
│  │         React Query Layer                  │            │
│  │  ┌──────────────────────────────────────┐  │            │
│  │  │  useQuery with debounced queryKey    │  │            │
│  │  │  - Caching (5 min staleTime)         │  │            │
│  │  │  - Automatic retries (2x)            │  │            │
│  │  │  - Request cancellation              │  │            │
│  │  └──────────────────┬───────────────────┘  │            │
│  └─────────────────────┼────────────────────────┘            │
│                        │                                    │
│  ┌─────────────────────▼──────────────────────┐            │
│  │         API Client Layer                   │            │
│  │  ┌──────────────────────────────────────┐  │            │
│  │  │  searchApi.globalSearch()            │  │            │
│  │  │  searchApi.localSearch()             │  │            │
│  │  │  - JWT token injection               │  │            │
│  │  │  - Error handling                    │  │            │
│  │  │  - Request/response transformation   │  │            │
│  │  └──────────────────┬───────────────────┘  │            │
│  └─────────────────────┼────────────────────────┘            │
└────────────────────────┼─────────────────────────────────────┘
                         │
                         │ HTTP/JSON
                         │
┌────────────────────────▼─────────────────────────────────────┐
│                  Backend Layer                               │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Search Service (Python FastAPI)                     │   │
│  │  - POST /search/global                               │   │
│  │  - POST /search/{entity_type}                        │   │
│  │  - PostgreSQL full-text search                       │   │
│  │  - Redis caching                                     │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Input** → Component captures keystrokes
2. **Debouncing** → `useDebouncedValue` delays state update by 300ms
3. **Query Trigger** → Debounced value changes trigger React Query's `useQuery`
4. **API Call** → Search API client sends request with JWT token
5. **Response** → React Query caches result and updates component state
6. **Rendering** → Component displays results with loading/error states

## Components and Interfaces

### 1. GlobalSearch Component

**Purpose**: Command palette-style modal for searching across all entity types

**Props**:
```typescript
interface GlobalSearchProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate?: (entityType: string, entityId: string) => void;
}
```

**State Management**:
- `searchQuery`: Current search input value (local state)
- `debouncedQuery`: Debounced search query (from `useDebouncedValue`)
- `selectedIndex`: Currently highlighted result index (for keyboard navigation)
- `recentSearches`: Array of recent search queries (from localStorage)

**Key Features**:
- Modal overlay with backdrop blur
- Search input with keyboard shortcut hint (⌘K)
- Results grouped by entity type
- Recent searches display when input is empty
- Keyboard navigation (Arrow Up/Down, Enter, Escape)
- Loading spinner and error states
- Empty state with suggestions

**Accessibility**:
- `role="dialog"` with `aria-modal="true"`
- `aria-label="Global search"`
- Focus trap within modal
- Focus returns to trigger element on close
- ARIA live region for result count announcements

### 2. LocalSearch Component

**Purpose**: Embedded search input for filtering data tables

**Props**:
```typescript
interface LocalSearchProps {
  entityType: string;
  onResultsChange: (results: SearchResult[]) => void;
  placeholder?: string;
  className?: string;
}
```

**State Management**:
- `searchQuery`: Current search input value (local state)
- `debouncedQuery`: Debounced search query (from `useDebouncedValue`)

**Key Features**:
- Compact search input with search icon
- Clear button (X icon) when input has value
- Loading indicator inline with input
- Integrates with parent table/list component

**Accessibility**:
- `aria-label="Search {entityType}"`
- `aria-describedby` for error messages
- Clear button with `aria-label="Clear search"`

### 3. SearchResultItem Component

**Purpose**: Reusable component for displaying individual search results

**Props**:
```typescript
interface SearchResultItemProps {
  result: SearchResult;
  isHighlighted: boolean;
  onClick: () => void;
  onMouseEnter: () => void;
}
```

**Rendering**:
- Entity type badge with color coding
- Title with bold text
- Snippet with highlighted query terms (using `<mark>` tags)
- Metadata (e.g., date, status) formatted according to entity type

### 4. SearchEmptyState Component

**Purpose**: Display when no results are found

**Props**:
```typescript
interface SearchEmptyStateProps {
  query: string;
  suggestions?: string[];
}
```

### 5. SearchErrorState Component

**Purpose**: Display when search fails

**Props**:
```typescript
interface SearchErrorStateProps {
  error: Error;
  onRetry: () => void;
}
```

## Data Models

### TypeScript Interfaces

```typescript
// Search Request
interface SearchRequest {
  query: string;
  entity_types?: string[];
  filters?: Record<string, unknown>;
  page?: number;
  page_size?: number;
  sort_by?: string;
}

// Search Result
interface SearchResult {
  entity_id: string;
  entity_type: string;
  title: string;
  snippet: string;
  relevance_score: number;
  metadata: Record<string, unknown>;
}

// Search Response
interface SearchResponse {
  results: SearchResult[];
  total_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next_page: boolean;
  has_previous_page: boolean;
  query_time_ms: number;
  suggestions?: string[];
}

// Entity Type Configuration
interface EntityTypeConfig {
  type: string;
  label: string;
  icon: React.ComponentType;
  color: string;
  route: string; // e.g., "/items/:id"
}

// Recent Search
interface RecentSearch {
  query: string;
  timestamp: number;
}
```

### Entity Type Configurations

```typescript
const ENTITY_TYPE_CONFIGS: Record<string, EntityTypeConfig> = {
  items: {
    type: 'items',
    label: 'Items',
    icon: Package,
    color: 'blue',
    route: '/inventory/items/:id',
  },
  customers: {
    type: 'customers',
    label: 'Customers',
    icon: Users,
    color: 'green',
    route: '/customers/:id',
  },
  suppliers: {
    type: 'suppliers',
    label: 'Suppliers',
    icon: Truck,
    color: 'purple',
    route: '/suppliers/:id',
  },
  invoices: {
    type: 'invoices',
    label: 'Invoices',
    icon: FileText,
    color: 'orange',
    route: '/invoices/:id',
  },
  warehouses: {
    type: 'warehouses',
    label: 'Warehouses',
    icon: Warehouse,
    color: 'indigo',
    route: '/warehouses/:id',
  },
  stock_entries: {
    type: 'stock_entries',
    label: 'Stock Entries',
    icon: ClipboardList,
    color: 'teal',
    route: '/inventory/stock-entries/:id',
  },
};
```

## Custom Hooks

### 1. useGlobalSearch Hook

**Purpose**: Encapsulates global search logic and state management

**Signature**:
```typescript
function useGlobalSearch(query: string): {
  data: SearchResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
}
```

**Implementation**:
- Uses React Query's `useQuery` with debounced query as key
- Configures 5-minute cache time
- Enables query only when query length >= 2 characters
- Handles request cancellation for stale queries

### 2. useLocalSearch Hook

**Purpose**: Encapsulates local search logic for specific entity types

**Signature**:
```typescript
function useLocalSearch(entityType: string, query: string): {
  data: SearchResponse | undefined;
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => void;
}
```

**Implementation**:
- Similar to `useGlobalSearch` but calls `/search/{entity_type}` endpoint
- Validates entity type against allowed types
- Throws error if entity type is invalid

### 3. useDebouncedValue Hook

**Purpose**: Debounces a value to reduce API calls

**Signature**:
```typescript
function useDebouncedValue<T>(value: T, delay: number): T
```

**Implementation**:
```typescript
function useDebouncedValue<T>(value: T, delay: number): T {
  const [debouncedValue, setDebouncedValue] = useState<T>(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => {
      clearTimeout(handler);
    };
  }, [value, delay]);

  return debouncedValue;
}
```

### 4. useKeyboardShortcut Hook

**Purpose**: Registers global keyboard shortcuts

**Signature**:
```typescript
function useKeyboardShortcut(
  key: string,
  modifiers: { ctrl?: boolean; meta?: boolean; shift?: boolean },
  callback: () => void
): void
```

**Implementation**:
- Listens to `keydown` events on document
- Checks for key and modifier combinations
- Prevents default behavior when shortcut matches
- Cleans up event listener on unmount

### 5. useRecentSearches Hook

**Purpose**: Manages recent searches in localStorage

**Signature**:
```typescript
function useRecentSearches(): {
  recentSearches: RecentSearch[];
  addSearch: (query: string) => void;
  clearSearches: () => void;
}
```

**Implementation**:
- Reads from `localStorage` key: `erp_recent_searches`
- Maintains maximum 5 searches
- Moves duplicate searches to top
- Removes oldest when limit exceeded

### 6. useSearchNavigation Hook

**Purpose**: Handles keyboard navigation through search results

**Signature**:
```typescript
function useSearchNavigation(
  results: SearchResult[],
  onSelect: (result: SearchResult) => void
): {
  selectedIndex: number;
  setSelectedIndex: (index: number) => void;
  handleKeyDown: (event: React.KeyboardEvent) => void;
}
```

**Implementation**:
- Tracks currently selected result index
- Handles Arrow Up/Down to change selection
- Handles Enter to select current result
- Wraps around at list boundaries

## API Client Layer

### Search API Client

**File**: `apps/platform/src/app/services/search.service.ts`

```typescript
import { environment } from '../../environments/environment';
import { SearchRequest, SearchResponse } from '../types/search.types';

const API_BASE_URL = environment.apiBaseUrl;

async function getAuthToken(): Promise<string> {
  // Retrieve JWT token from auth context or localStorage
  const token = localStorage.getItem('access_token');
  if (!token) {
    throw new Error('Authentication required');
  }
  return token;
}

export class SearchService {
  static async globalSearch(request: SearchRequest): Promise<SearchResponse> {
    const token = await getAuthToken();
    const response = await fetch(`${API_BASE_URL}/search/global`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Session expired. Please log in again.');
      }
      if (response.status === 500) {
        throw new Error('Search service unavailable. Please try again later.');
      }
      throw new Error('Unable to connect. Please check your connection and try again.');
    }

    return response.json();
  }

  static async localSearch(
    entityType: string,
    request: SearchRequest
  ): Promise<SearchResponse> {
    const token = await getAuthToken();
    const response = await fetch(`${API_BASE_URL}/search/${entityType}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      if (response.status === 401) {
        throw new Error('Session expired. Please log in again.');
      }
      if (response.status === 400) {
        throw new Error(`Invalid entity type: ${entityType}`);
      }
      if (response.status === 500) {
        throw new Error('Search service unavailable. Please try again later.');
      }
      throw new Error('Unable to connect. Please check your connection and try again.');
    }

    return response.json();
  }
}
```

## React Query Configuration

### Query Client Setup

**File**: `apps/platform/src/app/config/queryClient.ts`

```typescript
import { QueryClient } from '@tanstack/react-query';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
      retry: 2,
      refetchOnWindowFocus: false,
      refetchOnReconnect: true,
    },
  },
});
```

### Query Keys

```typescript
export const searchKeys = {
  all: ['search'] as const,
  global: (query: string) => [...searchKeys.all, 'global', query] as const,
  local: (entityType: string, query: string) =>
    [...searchKeys.all, 'local', entityType, query] as const,
};
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Debounced Search Requests

*For any* search input (global or local) and any sequence of keystrokes, the system should send exactly one API request 300ms after the last keystroke, and any keystrokes within the 300ms window should reset the timer.

**Validates: Requirements 1.3, 2.1, 4.1, 4.2, 4.3**

### Property 2: Result Grouping by Entity Type

*For any* global search response containing results from multiple entity types, the rendered output should display results grouped by entity type with section headers, where each group contains only results of that entity type.

**Validates: Requirements 1.4, 6.2**

### Property 3: Navigation on Result Click

*For any* search result displayed in the global search, clicking that result should trigger navigation to the entity's detail page and close the global search modal.

**Validates: Requirements 1.5**

### Property 4: Recent Search Execution

*For any* recent search item displayed in the global search, clicking that item should populate the search input with the query text and execute a search with that query.

**Validates: Requirements 1.8, 8.6**

### Property 5: Error Message Display

*For any* search request that fails (global or local), the system should display a user-friendly error message appropriate to the error type (network, authentication, or server error).

**Validates: Requirements 1.10, 2.7**

### Property 6: Local Search Table Filtering

*For any* local search response, the data table should display only the records present in the search results, and no other records.

**Validates: Requirements 2.2**

### Property 7: Loading State Display

*For any* search request in progress (global or local), the system should display a loading indicator in the appropriate location (modal for global, inline for local).

**Validates: Requirements 2.5, 7.1**

### Property 8: React Query Caching

*For any* search query, if the same query is executed twice within 5 minutes, the second execution should use cached data and not make a new API request.

**Validates: Requirements 3.2, 11.2**

### Property 9: Request Retry on Failure

*For any* search request that fails, the system should automatically retry the request up to 2 additional times before displaying an error.

**Validates: Requirements 3.3**

### Property 10: Request Cancellation

*For any* sequence of rapid search queries with the same query key, only the most recent query should complete, and all previous pending queries should be cancelled.

**Validates: Requirements 3.4**

### Property 11: Authentication Token Inclusion

*For any* search API request (global or local), the HTTP request should include an Authorization header with a valid JWT bearer token.

**Validates: Requirements 3.7**

### Property 12: Keyboard Navigation

*For any* list of search results displayed in the global search, pressing Arrow Down should move selection to the next result, pressing Arrow Up should move selection to the previous result, and selection should wrap around at list boundaries.

**Validates: Requirements 5.1**

### Property 13: Enter Key Navigation

*For any* highlighted search result in the global search, pressing the Enter key should navigate to that entity's detail page.

**Validates: Requirements 5.2**

### Property 14: ARIA Labels on Interactive Elements

*For any* interactive element in the search components (buttons, inputs, result items), the rendered HTML should include appropriate ARIA labels for screen reader accessibility.

**Validates: Requirements 5.4**

### Property 15: Search Result Display Format

*For any* search result rendered in the UI, the output should include the entity title, entity type badge, and text snippet as visible elements.

**Validates: Requirements 6.1**

### Property 16: Query Term Highlighting

*For any* search result snippet that contains the search query term, the query term should be wrapped in a highlight element (e.g., `<mark>` tag) in the rendered output.

**Validates: Requirements 6.3**

### Property 17: Pagination Limit

*For any* search response containing more than 20 results, only the first 20 results for the current page should be displayed in the UI.

**Validates: Requirements 6.4**

### Property 18: Pagination Controls Display

*For any* search response where total_count exceeds 20, pagination controls should be visible in the rendered UI.

**Validates: Requirements 6.5**

### Property 19: Total Count Display

*For any* search response, the total count of matching results should be displayed in the UI.

**Validates: Requirements 6.6**

### Property 20: Metadata Formatting

*For any* search result metadata containing dates, numbers, or currency values, those values should be formatted according to the user's locale settings.

**Validates: Requirements 6.7**

### Property 21: Error Logging

*For any* search error that occurs, the error should be logged to the browser console with sufficient detail for debugging.

**Validates: Requirements 7.6**

### Property 22: Recent Search Storage

*For any* search query executed in the global search, the query text should be stored in browser localStorage under the key `erp_recent_searches`.

**Validates: Requirements 8.1**

### Property 23: Recent Searches Limit

*For any* sequence of search queries, the number of recent searches stored in localStorage should never exceed 5.

**Validates: Requirements 8.2**

### Property 24: Recent Search Eviction

*For any* new search added when 5 recent searches already exist, the oldest search should be removed from the list.

**Validates: Requirements 8.3**

### Property 25: Recent Search Deduplication

*For any* search query that already exists in the recent searches list, executing that query again should move it to the top of the list (index 0) rather than creating a duplicate entry.

**Validates: Requirements 8.4**

### Property 26: Mobile Full-Screen Modal

*For any* device with screen width less than 768px, the global search modal should render at full screen width.

**Validates: Requirements 9.1**

### Property 27: Mobile Input Width

*For any* device with screen width less than 768px, the local search input should adjust its width to fit the screen.

**Validates: Requirements 9.2**

### Property 28: Touch Target Sizes

*For any* interactive element in the search components, the element should have a minimum tap target size of 44x44 pixels for touch accessibility.

**Validates: Requirements 9.3**

### Property 29: Mobile Vertical Stacking

*For any* search results displayed on a device with screen width less than 768px, the result information should be stacked vertically rather than horizontally.

**Validates: Requirements 9.4**

### Property 30: Hover Prefetch

*For any* recent search item, if the user hovers over it for more than 500ms, the system should prefetch the search results for that query.

**Validates: Requirements 11.6**

## Error Handling

### Error Types and Handling Strategy

1. **Network Errors** (fetch fails, timeout)
   - Display: "Unable to connect. Please check your connection and try again."
   - Action: Allow manual retry via retry button
   - Logging: Log full error to console

2. **Authentication Errors** (401 Unauthorized)
   - Display: "Session expired. Please log in again."
   - Action: Redirect to login page after 3 seconds
   - Logging: Log error and redirect action

3. **Server Errors** (500 Internal Server Error)
   - Display: "Search service unavailable. Please try again later."
   - Action: Allow manual retry via retry button
   - Logging: Log full error with request details

4. **Validation Errors** (400 Bad Request)
   - Display: Specific validation message from API
   - Action: Clear invalid input or show inline error
   - Logging: Log validation details

5. **Empty Results** (200 OK with zero results)
   - Display: "No results found for '[query]'. Try different keywords or check spelling."
   - Action: Show suggestions if available from API
   - Logging: Log query for analytics

### Error Boundary Implementation

Wrap search components in React Error Boundary to catch rendering errors:

```typescript
<ErrorBoundary
  fallback={<SearchErrorFallback />}
  onError={(error, errorInfo) => {
    console.error('Search component error:', error, errorInfo);
  }}
>
  <GlobalSearch />
</ErrorBoundary>
```

## Testing Strategy

### Dual Testing Approach

The testing strategy employs both unit tests and property-based tests to ensure comprehensive coverage:

- **Unit Tests**: Verify specific examples, edge cases, and error conditions
- **Property Tests**: Verify universal properties across all inputs using randomized test data

Both approaches are complementary and necessary for comprehensive coverage. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across a wide range of inputs.

### Unit Testing

**Framework**: Vitest with React Testing Library

**Test Categories**:

1. **Component Rendering Tests**
   - GlobalSearch renders with correct initial state
   - LocalSearch renders with entity type prop
   - SearchResultItem displays all required fields
   - Empty state displays when no results
   - Error state displays with retry button

2. **User Interaction Tests**
   - Clicking search input opens global search modal
   - Pressing Escape closes modal
   - Clicking result navigates to detail page
   - Clicking clear button clears input
   - Clicking recent search executes query

3. **Keyboard Navigation Tests**
   - Ctrl+K / Cmd+K opens global search
   - Arrow keys navigate through results
   - Enter key selects highlighted result
   - Tab key moves focus correctly

4. **Error Handling Tests**
   - Network error displays correct message
   - Auth error redirects to login
   - Server error displays correct message
   - Validation error displays inline

5. **Accessibility Tests**
   - All interactive elements have ARIA labels
   - Focus management works correctly
   - Screen reader announcements are present
   - Keyboard navigation is fully functional

**Example Unit Test**:
```typescript
describe('GlobalSearch', () => {
  it('should open when Ctrl+K is pressed', () => {
    render(<GlobalSearch isOpen={false} onClose={vi.fn()} />);
    
    fireEvent.keyDown(document, { key: 'k', ctrlKey: true });
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
  });
  
  it('should display recent searches when input is empty', () => {
    const recentSearches = ['test query', 'another search'];
    localStorage.setItem('erp_recent_searches', JSON.stringify(recentSearches));
    
    render(<GlobalSearch isOpen={true} onClose={vi.fn()} />);
    
    expect(screen.getByText('test query')).toBeInTheDocument();
    expect(screen.getByText('another search')).toBeInTheDocument();
  });
});
```

### Property-Based Testing

**Framework**: fast-check with Vitest

**Configuration**: Minimum 100 iterations per property test

**Test Tagging**: Each property test must reference its design document property using a comment:
```typescript
// Feature: erp-search-ui, Property 1: Debounced Search Requests
```

**Property Test Categories**:

1. **Debouncing Properties**
   - Property 1: Debounced search requests
   - Test with random keystroke sequences
   - Verify exactly one API call after 300ms

2. **Data Transformation Properties**
   - Property 2: Result grouping by entity type
   - Generate random search responses with mixed entity types
   - Verify grouping is correct

3. **State Management Properties**
   - Property 8: React Query caching
   - Generate random queries
   - Verify cache hits within 5 minutes

4. **Storage Properties**
   - Property 22-25: Recent searches management
   - Generate random search sequences
   - Verify storage limits, eviction, and deduplication

5. **UI Rendering Properties**
   - Property 15: Search result display format
   - Generate random search results
   - Verify all required fields are rendered

**Example Property Test**:
```typescript
import fc from 'fast-check';

// Feature: erp-search-ui, Property 1: Debounced Search Requests
describe('Property 1: Debounced Search Requests', () => {
  it('should send exactly one API request 300ms after last keystroke', async () => {
    await fc.assert(
      fc.asyncProperty(
        fc.array(fc.string({ minLength: 1, maxLength: 50 }), { minLength: 1, maxLength: 10 }),
        async (keystrokes) => {
          const apiCallSpy = vi.fn();
          const { result } = renderHook(() => useGlobalSearch(''));
          
          // Simulate rapid keystrokes
          for (const char of keystrokes) {
            act(() => {
              result.current.setQuery(char);
            });
            await new Promise(resolve => setTimeout(resolve, 50)); // 50ms between keystrokes
          }
          
          // Wait for debounce delay
          await new Promise(resolve => setTimeout(resolve, 350));
          
          // Verify exactly one API call was made
          expect(apiCallSpy).toHaveBeenCalledTimes(1);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// Feature: erp-search-ui, Property 23: Recent Searches Limit
describe('Property 23: Recent Searches Limit', () => {
  it('should never exceed 5 recent searches', () => {
    fc.assert(
      fc.property(
        fc.array(fc.string({ minLength: 1, maxLength: 100 }), { minLength: 1, maxLength: 20 }),
        (queries) => {
          const { result } = renderHook(() => useRecentSearches());
          
          // Add all queries
          queries.forEach(query => {
            act(() => {
              result.current.addSearch(query);
            });
          });
          
          // Verify limit is respected
          expect(result.current.recentSearches.length).toBeLessThanOrEqual(5);
        }
      ),
      { numRuns: 100 }
    );
  });
});

// Feature: erp-search-ui, Property 25: Recent Search Deduplication
describe('Property 25: Recent Search Deduplication', () => {
  it('should move duplicate searches to top of list', () => {
    fc.assert(
      fc.property(
        fc.array(fc.string({ minLength: 1, maxLength: 50 }), { minLength: 2, maxLength: 10 }),
        fc.integer({ min: 0, max: 4 }),
        (queries, duplicateIndex) => {
          const { result } = renderHook(() => useRecentSearches());
          
          // Add initial queries
          queries.forEach(query => {
            act(() => {
              result.current.addSearch(query);
            });
          });
          
          // Get a query that exists in the list
          const existingQuery = result.current.recentSearches[duplicateIndex % result.current.recentSearches.length]?.query;
          
          if (existingQuery) {
            // Add the duplicate
            act(() => {
              result.current.addSearch(existingQuery);
            });
            
            // Verify it's at the top
            expect(result.current.recentSearches[0].query).toBe(existingQuery);
            
            // Verify no duplicates exist
            const queryStrings = result.current.recentSearches.map(s => s.query);
            const uniqueQueries = new Set(queryStrings);
            expect(queryStrings.length).toBe(uniqueQueries.size);
          }
        }
      ),
      { numRuns: 100 }
    );
  });
});
```

### Integration Testing

**Framework**: Playwright for E2E tests

**Test Scenarios**:

1. **End-to-End Search Flow**
   - Open global search with keyboard shortcut
   - Type query and wait for results
   - Navigate with keyboard
   - Select result and verify navigation

2. **Local Search Integration**
   - Navigate to items table
   - Type in local search
   - Verify table filters correctly
   - Clear search and verify all items shown

3. **Error Recovery**
   - Simulate network failure
   - Verify error message
   - Restore network
   - Retry and verify success

4. **Mobile Responsiveness**
   - Test on mobile viewport
   - Verify full-screen modal
   - Verify touch targets
   - Verify vertical stacking

### Test Coverage Goals

- **Line Coverage**: Minimum 80%
- **Branch Coverage**: Minimum 75%
- **Function Coverage**: Minimum 85%
- **Property Tests**: All 30 properties must have corresponding tests

## Performance Considerations

### Optimization Strategies

1. **Code Splitting**
   - Lazy load GlobalSearch modal component
   - Reduces initial bundle size by ~50KB

2. **Memoization**
   - Use `React.memo` for SearchResultItem components
   - Use `useMemo` for expensive computations (filtering, sorting)
   - Use `useCallback` for event handlers passed to child components

3. **Virtualization**
   - Implement virtual scrolling for result lists > 100 items
   - Use `react-virtual` or `react-window` library

4. **Debouncing**
   - 300ms debounce delay balances responsiveness and API load
   - Prevents excessive API calls during typing

5. **Caching**
   - React Query caches results for 5 minutes
   - Reduces redundant API calls for repeated queries
   - Prefetch on hover for instant results

6. **Request Cancellation**
   - Cancel pending requests when new query is typed
   - Prevents race conditions and wasted bandwidth

### Performance Metrics

**Target Metrics**:
- Time to Interactive (TTI): < 3 seconds
- First Contentful Paint (FCP): < 1.5 seconds
- Search response time: < 500ms (backend target)
- Debounce delay: 300ms
- Modal open animation: < 200ms
- Keyboard navigation latency: < 50ms

**Monitoring**:
- Use React DevTools Profiler to identify slow renders
- Use Chrome DevTools Performance tab to measure interactions
- Log search query times for analytics

## Security Considerations

### Authentication and Authorization

1. **JWT Token Management**
   - Retrieve token from auth context or localStorage
   - Include token in Authorization header for all requests
   - Handle 401 errors by redirecting to login

2. **Token Expiration**
   - Detect expired tokens (401 response)
   - Display "Session expired" message
   - Redirect to login after 3 seconds
   - Clear any cached search data

### Input Sanitization

1. **Query Validation**
   - Backend validates query length (1-500 characters)
   - Frontend trims whitespace
   - Backend sanitizes SQL injection attempts

2. **XSS Prevention**
   - React automatically escapes rendered text
   - Use `dangerouslySetInnerHTML` only for trusted snippet highlighting
   - Sanitize snippet HTML from backend using DOMPurify

### Data Privacy

1. **Recent Searches**
   - Stored only in browser localStorage (client-side)
   - Not sent to backend or analytics
   - User can clear at any time

2. **Search Analytics**
   - Log only query text and result count (no PII)
   - Aggregate data for performance monitoring
   - Comply with data retention policies

## Deployment and Rollout

### Feature Flags

Use feature flags to control rollout:

```typescript
const FEATURE_FLAGS = {
  GLOBAL_SEARCH_ENABLED: true,
  LOCAL_SEARCH_ENABLED: true,
  SEARCH_PREFETCH_ENABLED: false, // Gradual rollout
  SEARCH_VIRTUALIZATION_ENABLED: false, // Performance optimization
};
```

### Rollout Plan

1. **Phase 1: Internal Testing** (Week 1)
   - Deploy to staging environment
   - Internal team testing
   - Fix critical bugs

2. **Phase 2: Beta Release** (Week 2)
   - Enable for 10% of users
   - Monitor performance metrics
   - Gather user feedback

3. **Phase 3: Gradual Rollout** (Week 3-4)
   - Increase to 50% of users
   - Monitor error rates and performance
   - Enable prefetch feature flag

4. **Phase 4: Full Release** (Week 5)
   - Enable for 100% of users
   - Monitor for 1 week
   - Enable virtualization for large result sets

### Monitoring and Alerts

**Metrics to Monitor**:
- Search API error rate (alert if > 5%)
- Search API latency (alert if p95 > 1s)
- Frontend error rate (alert if > 2%)
- Search usage (queries per day)
- Cache hit rate (target > 40%)

**Logging**:
- Log all search errors to console
- Send error reports to error tracking service (e.g., Sentry)
- Log performance metrics to analytics service

## Future Enhancements

### Phase 2 Features (Post-MVP)

1. **Advanced Filters**
   - Date range filters
   - Status filters
   - Custom field filters

2. **Search Suggestions**
   - Autocomplete based on popular searches
   - Typo correction
   - Related searches

3. **Search History Analytics**
   - Track most common searches
   - Identify search patterns
   - Improve search relevance

4. **Saved Searches**
   - Allow users to save frequent searches
   - Quick access to saved searches
   - Share searches with team members

5. **Voice Search**
   - Speech-to-text input
   - Mobile-first feature
   - Accessibility enhancement

6. **Search Filters in URL**
   - Persist search state in URL query params
   - Enable sharing search results via URL
   - Browser back/forward navigation support

## References

### External Resources

- [React Query Documentation](https://tanstack.com/query/latest) - Data fetching and caching patterns
- [Command Palette Design Patterns](https://blog.superhuman.com/how-to-build-a-remarkable-command-palette/) - UI/UX best practices (content rephrased for compliance with licensing restrictions)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/) - Accessibility standards
- [Debouncing in React](https://www.esparkinfo.com/qanda/reactjs/use-debounce-with-usequery-in-react-query) - Implementation patterns (content rephrased for compliance with licensing restrictions)

### Internal Documentation

- Search Service API Documentation: `horizon-sync-erp-be/search-service/README.md`
- Search Service Schemas: `horizon-sync-erp-be/search-service/app/schemas/search.py`
- Platform App Structure: `horizon-sync/apps/platform/`
