/**
 * React Query Configuration
 *
 * 🎓 LEARNING NOTE: What is React Query?
 *
 * React Query (@tanstack/react-query) is a library for managing "server state"
 * in React applications.
 *
 * ## Server State vs Client State
 *
 * Client State (use useState):
 *   - UI state: "is modal open?"
 *   - Form inputs: "what did user type?"
 *   - Local toggles: "is sidebar collapsed?"
 *
 * Server State (use React Query):
 *   - Data from API: "list of organisms"
 *   - Remote resources: "user profile"
 *   - Cached data: "previous API responses"
 *
 * ## Why React Query? (THE BIG CHANGE from 2022!)
 *
 * OLD WAY (2020-2022) with useState + useEffect:
 * ```typescript
 * function Dashboard() {
 *   const [organisms, setOrganisms] = useState([])
 *   const [loading, setLoading] = useState(true)
 *   const [error, setError] = useState(null)
 *
 *   useEffect(() => {
 *     setLoading(true)
 *     fetch('/api/organisms')
 *       .then(r => r.json())
 *       .then(setOrganisms)
 *       .catch(setError)
 *       .finally(() => setLoading(false))
 *   }, [])
 *
 *   if (loading) return <div>Loading...</div>
 *   if (error) return <div>Error!</div>
 *   return <div>{organisms.map(...)}</div>
 * }
 * ```
 *
 * PROBLEMS with old way:
 *   ❌ No caching: Refetch every time component mounts
 *   ❌ No background refetching: Data gets stale
 *   ❌ Race conditions: Fast navigation causes wrong data
 *   ❌ No retry logic: One failure = permanent error
 *   ❌ Duplication: Copy-paste this code everywhere
 *
 * NEW WAY (2024) with React Query:
 * ```typescript
 * function Dashboard() {
 *   const { data: organisms, isLoading, error } = useOrganisms()
 *
 *   if (isLoading) return <div>Loading...</div>
 *   if (error) return <div>Error!</div>
 *   return <div>{organisms.map(...)}</div>
 * }
 * ```
 *
 * BENEFITS of React Query:
 *   ✅ Automatic caching: Data persists across navigation
 *   ✅ Background refetching: Data stays fresh automatically
 *   ✅ Deduplication: Multiple components = one request
 *   ✅ Automatic retries: Network failures handled
 *   ✅ Loading/error states: Built-in
 *   ✅ DevTools: See all queries in browser
 */

import { QueryClient } from '@tanstack/react-query'

/**
 * Create QueryClient with default options
 *
 * 🎓 LEARNING NOTE: QueryClient
 *
 * QueryClient is the brain of React Query.
 * It manages:
 *   - Cache storage
 *   - Query lifecycle
 *   - Refetch strategies
 *   - Mutations
 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      /**
       * 🎓 STALE TIME: How long data is considered "fresh"
       *
       * staleTime: 1000 * 60 * 5 = 5 minutes
       *
       * What this means:
       *   - Data fetched RIGHT NOW is "fresh" for 5 minutes
       *   - During those 5 minutes, React Query uses CACHED data
       *   - After 5 minutes, data becomes "stale"
       *   - Stale data can still be used, but will refetch in background
       *
       * Example:
       *   Time 0:00 - Fetch organisms (data is fresh)
       *   Time 0:30 - Revisit page → uses cache (fresh)
       *   Time 3:00 - Revisit page → uses cache (fresh)
       *   Time 6:00 - Revisit page → shows cache BUT refetches in background (stale)
       *
       * Why 5 minutes?
       *   - Organisms don't change frequently
       *   - Reduces unnecessary API calls
       *   - User still sees instant data (from cache)
       */
      staleTime: 1000 * 60 * 5,

      /**
       * 🎓 GC TIME: How long to keep unused data in cache
       *
       * gcTime: 1000 * 60 * 10 = 10 minutes
       * (Previously called "cacheTime" in React Query v4)
       *
       * What this means:
       *   - If NO components are using this data for 10 minutes, delete it
       *   - "Garbage collection" for memory management
       *
       * Example:
       *   Time 0:00 - Fetch organisms (data cached)
       *   Time 0:30 - Navigate away (data still cached)
       *   Time 9:00 - Data still in cache (might come back!)
       *   Time 11:00 - Data deleted from cache (unused for >10 min)
       *
       * Why 10 minutes?
       *   - Longer than staleTime (5 min) so data survives background refetch
       *   - Short enough to avoid memory bloat
       *   - Covers typical user session
       */
      gcTime: 1000 * 60 * 10,

      /**
       * 🎓 RETRY: Auto-retry failed requests
       *
       * retry: 3 = Try up to 3 times before giving up
       *
       * Retry delays (exponential backoff):
       *   - 1st retry: 1 second
       *   - 2nd retry: 2 seconds
       *   - 3rd retry: 4 seconds
       *
       * Why retry?
       *   - Network blips happen
       *   - Server might be temporarily down
       *   - Better UX: Don't show error immediately
       *
       * When NOT to retry?
       *   - 400 Bad Request (validation error) - won't fix itself
       *   - 404 Not Found - resource doesn't exist
       *   - 409 Conflict - duplicate entry
       *
       * React Query is smart: Only retries network errors and 5xx server errors
       */
      retry: 3,

      /**
       * 🎓 REFETCH ON WINDOW FOCUS: Refetch when user returns to tab
       *
       * refetchOnWindowFocus: false
       *
       * What this does:
       *   When disabled: Switching browser tabs does NOT refetch
       *   When enabled: Switching back to tab refetches data
       *
       * Why disable?
       *   - Our data doesn't change that frequently
       *   - staleTime already handles freshness
       *   - Reduces API calls
       *
       * You might enable this for:
       *   - Real-time dashboards
       *   - Messaging apps
       *   - Live data feeds
       */
      refetchOnWindowFocus: false,

      /**
       * 🎓 REFETCH ON MOUNT: Refetch when component mounts
       *
       * Default: true
       * Can override per-query
       *
       * What this means:
       *   - Component mounts → Check if data is stale → Refetch if needed
       *   - If data is fresh (within staleTime), use cache
       *
       * This is good! It keeps data fresh without excessive refetching.
       */

      /**
       * 🎓 REFETCH ON RECONNECT: Refetch when internet reconnects
       *
       * Default: true
       *
       * What this means:
       *   - Lost internet → Regain internet → Refetch all active queries
       *
       * Why?
       *   - Data might have changed while offline
       *   - User expects fresh data when back online
       */
    },

    mutations: {
      /**
       * 🎓 MUTATIONS: POST/PUT/DELETE operations
       *
       * Mutations are for CHANGING data on the server.
       * Queries are for READING data.
       *
       * Example:
       *   - useQuery: GET /api/organisms (read)
       *   - useMutation: POST /api/organisms (create)
       *   - useMutation: DELETE /api/organisms/1 (delete)
       *
       * Mutations don't retry by default (usually one attempt is enough)
       */
      retry: false,
    },
  },
})

/**
 * 🎓 LEARNING NOTE: How to Use QueryClient
 *
 * 1. Wrap your app in QueryClientProvider:
 *    ```tsx
 *    import { QueryClientProvider } from '@tanstack/react-query'
 *    import { queryClient } from '@/config/queryClient'
 *
 *    function App() {
 *      return (
 *        <QueryClientProvider client={queryClient}>
 *          <YourApp />
 *        </QueryClientProvider>
 *      )
 *    }
 *    ```
 *
 * 2. Use hooks in components:
 *    ```tsx
 *    import { useOrganisms } from '@/lib/hooks/useOrganisms'
 *
 *    function Dashboard() {
 *      const { data, isLoading } = useOrganisms()
 *      // React Query handles caching, refetching, error states!
 *    }
 *    ```
 *
 * 3. Invalidate queries after mutations:
 *    ```tsx
 *    const createMutation = useMutation({
 *      mutationFn: createOrganism,
 *      onSuccess: () => {
 *        // Refetch organisms list to show new organism
 *        queryClient.invalidateQueries({ queryKey: ['organisms'] })
 *      }
 *    })
 *    ```
 */

/**
 * Query Keys - Naming Convention
 *
 * 🎓 LEARNING NOTE: Query Keys
 *
 * Query keys identify cached data. Format: array of values
 *
 * Examples:
 *   ['organisms']              - All organisms
 *   ['organisms', { status: 'complete' }]  - Filtered organisms
 *   ['organism', 1]            - Single organism with ID 1
 *   ['processes', 5, 'progress']  - Progress for process 5
 *
 * Rules:
 *   - First element: Resource name (string)
 *   - Include filters/params that affect the data
 *   - Consistent ordering: ['organisms', filters] not [filters, 'organisms']
 *
 * Why arrays?
 *   - Partial matching: invalidateQueries(['organisms']) invalidates ALL organism queries
 *   - Type-safe: TypeScript can infer types from key structure
 *   - Flexible: Easy to add params
 */
