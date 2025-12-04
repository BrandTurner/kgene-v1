/**
 * useOrganisms Hook - Fetch Organisms with React Query
 *
 * 🎓 LEARNING NOTE: Custom Hooks
 *
 * A custom hook is a JavaScript function that:
 *   - Starts with "use" (React convention)
 *   - Can call other hooks (useState, useEffect, useQuery, etc.)
 *   - Encapsulates reusable logic
 *
 * Why create custom hooks?
 *   - Reuse logic across components
 *   - Clean component code
 *   - Easier testing
 *   - Single source of truth
 *
 * Example WITHOUT custom hook:
 * ```tsx
 * function Dashboard() {
 *   const { data, isLoading } = useQuery({
 *     queryKey: ['organisms'],
 *     queryFn: getOrganisms
 *   })
 *   // Every component that needs organisms copies this code
 * }
 * ```
 *
 * Example WITH custom hook:
 * ```tsx
 * function Dashboard() {
 *   const { data, isLoading } = useOrganisms()
 *   // Clean! Reusable! Type-safe!
 * }
 * ```
 */

import { useQuery } from '@tanstack/react-query'
import { getOrganisms } from '../api/organisms'
import type { OrganismFilters } from '@/types'

/**
 * useOrganisms - Hook to fetch list of organisms
 *
 * 🎓 LEARNING NOTE: useQuery Hook
 *
 * useQuery is THE core hook of React Query for fetching data.
 *
 * What it does:
 *   1. Fetches data on component mount
 *   2. Caches the result
 *   3. Provides loading/error states
 *   4. Auto-refetches when data becomes stale
 *   5. Deduplicates requests (multiple components = one API call)
 *
 * Return value has MANY useful properties:
 *   - data: The fetched data (undefined while loading)
 *   - isLoading: true during first fetch
 *   - isFetching: true during ANY fetch (including background refetch)
 *   - error: Error object if fetch failed
 *   - refetch: Function to manually refetch
 *   - ... and more!
 *
 * @param filters - Optional filters for organism list
 * @returns React Query result with organisms data
 *
 * @example
 * ```tsx
 * function OrganismsList() {
 *   const { data: organisms, isLoading, error } = useOrganisms()
 *
 *   if (isLoading) return <div>Loading...</div>
 *   if (error) return <div>Error: {error.message}</div>
 *
 *   return (
 *     <ul>
 *       {organisms?.map(org => (
 *         <li key={org.id}>{org.name}</li>
 *       ))}
 *     </ul>
 *   )
 * }
 * ```
 *
 * @example With filters
 * ```tsx
 * function CompletedOrganisms() {
 *   const { data, isLoading } = useOrganisms({ status: 'complete' })
 *   // Only fetches completed organisms
 * }
 * ```
 */
export function useOrganisms(filters?: OrganismFilters) {
  return useQuery({
    /**
     * 🎓 QUERY KEY: Unique identifier for this query
     *
     * Format: [resource, params]
     *
     * Why include filters?
     *   - Different filters = different data = different cache entry
     *   - ['organisms'] and ['organisms', { status: 'complete' }] are separate
     *
     * React Query uses this key to:
     *   - Store data in cache
     *   - Deduplicate requests
     *   - Invalidate specific queries
     *
     * Example cache:
     *   ['organisms'] → [{id:1, code:'eco'}, {id:2, code:'hsa'}]
     *   ['organisms', {status:'complete'}] → [{id:1, code:'eco'}]
     */
    queryKey: ['organisms', filters],

    /**
     * 🎓 QUERY FUNCTION: Function that fetches the data
     *
     * Requirements:
     *   - Must be async or return a Promise
     *   - Should throw errors (don't catch them!)
     *   - Can accept a context object with signal for cancellation
     *
     * React Query will:
     *   - Call this function when needed
     *   - Cache the result
     *   - Handle loading/error states
     *   - Retry on failure (per queryClient config)
     */
    queryFn: () => getOrganisms(filters),

    /**
     * 🎓 ADDITIONAL OPTIONS (optional)
     *
     * You can override queryClient defaults per-query:
     *
     * staleTime: 1000 * 60 * 10,  // This query stays fresh for 10 min
     * gcTime: 1000 * 60 * 30,     // Keep in cache for 30 min
     * enabled: !!userId,          // Only run query if userId exists
     * refetchInterval: 5000,      // Poll every 5 seconds
     * retry: false,               // Don't retry this query
     *
     * We don't need any overrides for organisms list,
     * so we use the queryClient defaults (5 min stale, 10 min cache, 3 retries).
     */
  })
}

/**
 * 🎓 LEARNING NOTE: What Happens When You Call useOrganisms()?
 *
 * Step by step:
 *
 * 1. Component mounts:
 *    const { data, isLoading } = useOrganisms()
 *
 * 2. React Query checks cache:
 *    - Key: ['organisms', undefined]
 *    - Found in cache? If yes, return cached data immediately
 *    - Is data fresh (< 5 min old)? If yes, done!
 *    - Is data stale (> 5 min old)? Refetch in background
 *
 * 3. If no cache, fetch data:
 *    - isLoading = true
 *    - Call getOrganisms()
 *    - Wait for response
 *    - Store in cache with key ['organisms', undefined]
 *    - Update component: isLoading = false, data = result
 *
 * 4. User navigates away:
 *    - Component unmounts
 *    - Data stays in cache for gcTime (10 min)
 *
 * 5. User comes back (within 10 min):
 *    - Component mounts again
 *    - React Query finds data in cache
 *    - Shows cached data INSTANTLY
 *    - Checks if stale → refetch in background if needed
 *
 * 6. Two components use useOrganisms():
 *    - Both components get same cached data
 *    - Only ONE API call is made
 *    - This is called "deduplication"
 *
 * Benefits:
 *   ✅ Fast: Cached data = instant UI
 *   ✅ Fresh: Background refetch keeps data up-to-date
 *   ✅ Efficient: No duplicate requests
 *   ✅ Automatic: No useEffect, no manual state management
 */

/**
 * 🎓 LEARNING NOTE: Type Inference
 *
 * TypeScript is smart enough to infer types from our API functions!
 *
 * getOrganisms() returns Promise<Organism[]>
 *    ↓
 * useQuery automatically knows data is Organism[] | undefined
 *    ↓
 * const { data } = useOrganisms()
 * data is typed as: Organism[] | undefined
 *
 * This means:
 *   data?.[0].code  // ✅ TypeScript knows this is valid
 *   data?.[0].foo   // ❌ TypeScript error: 'foo' doesn't exist on Organism
 *
 * We don't need to manually specify types - TypeScript figures it out!
 */
