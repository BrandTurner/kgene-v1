/**
 * useCreateOrganism Hook - Create Organism Mutation
 *
 * 🎓 LEARNING NOTE: useMutation vs useQuery
 *
 * useQuery:  For READING data (GET requests)
 *   - Runs automatically on component mount
 *   - Caches results
 *   - Auto-refetches
 *
 * useMutation: For CHANGING data (POST/PUT/DELETE requests)
 *   - Runs manually when you call it
 *   - Doesn't cache results
 *   - Can invalidate queries to refetch data
 *
 * Example:
 *   const { data } = useQuery(...)        // Auto-fetches
 *   const { mutate } = useMutation(...)   // Manual trigger
 *   mutate({ code: "eco", name: "E. coli" })  // Call it when needed
 */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { createOrganism } from '../api/organisms'
import type { OrganismCreate } from '@/types'

/**
 * useCreateOrganism - Hook to create a new organism
 *
 * 🎓 LEARNING NOTE: useMutation Hook
 *
 * useMutation is for side effects that change server state.
 *
 * Return value properties:
 *   - mutate: Function to trigger the mutation
 *   - mutateAsync: Async version (returns Promise)
 *   - isPending: true while mutation is running
 *   - isSuccess: true if mutation succeeded
 *   - isError: true if mutation failed
 *   - data: Result of successful mutation
 *   - error: Error object if mutation failed
 *   - reset: Clear mutation state
 *
 * @returns React Query mutation result
 *
 * @example Basic usage
 * ```tsx
 * function CreateOrganismForm() {
 *   const createMutation = useCreateOrganism()
 *
 *   const handleSubmit = (e) => {
 *     e.preventDefault()
 *     createMutation.mutate({
 *       code: "eco",
 *       name: "Escherichia coli"
 *     })
 *   }
 *
 *   return (
 *     <form onSubmit={handleSubmit}>
 *       {createMutation.isPending && <p>Creating...</p>}
 *       {createMutation.isError && <p>Error: {createMutation.error.message}</p>}
 *       {createMutation.isSuccess && <p>Created!</p>}
 *       <button disabled={createMutation.isPending}>Create</button>
 *     </form>
 *   )
 * }
 * ```
 *
 * @example With callbacks
 * ```tsx
 * const createMutation = useCreateOrganism({
 *   onSuccess: (data) => {
 *     toast.success(`Created organism: ${data.name}`)
 *     navigate(`/organisms/${data.id}`)
 *   },
 *   onError: (error) => {
 *     if (error.code === 'DUPLICATE_ORGANISM') {
 *       toast.error('Organism already exists!')
 *     }
 *   }
 * })
 * ```
 */
export function useCreateOrganism() {
  /**
   * 🎓 LEARNING NOTE: useQueryClient Hook
   *
   * useQueryClient gives you access to the QueryClient instance.
   *
   * What can you do with it?
   *   - invalidateQueries: Mark queries as stale → refetch
   *   - setQueryData: Manually update cache
   *   - getQueryData: Read from cache
   *   - cancelQueries: Cancel in-flight requests
   *
   * Most common use: Invalidate queries after mutation
   */
  const queryClient = useQueryClient()

  return useMutation({
    /**
     * 🎓 MUTATION FUNCTION: The actual API call
     *
     * This function receives the variables passed to mutate():
     *   createMutation.mutate(variables)
     *                          ↓
     *   mutationFn: (variables) => createOrganism(variables)
     *
     * Must return a Promise that:
     *   - Resolves with the created organism
     *   - Rejects with an error
     */
    mutationFn: (organismData: OrganismCreate) => createOrganism(organismData),

    /**
     * 🎓 ON SUCCESS: Callback after successful mutation
     *
     * Called with the mutation result (created organism).
     *
     * Common use cases:
     *   - Show success toast
     *   - Navigate to new resource
     *   - Update local state
     *   - Invalidate related queries
     *
     * Why invalidate queries?
     *   When we create an organism, the organisms list is now out of date.
     *   Invalidating tells React Query: "This data is stale, refetch it!"
     *
     * @param data - The created organism returned by the API
     */
    onSuccess: () => {
      /**
       * Invalidate all queries with key ['organisms', ...]
       *
       * This refetches:
       *   - ['organisms']
       *   - ['organisms', { status: 'complete' }]
       *   - ['organisms', { code_pattern: 'eco' }]
       *   - ... any query starting with ['organisms']
       *
       * Why invalidate all organism queries?
       *   - The list needs the new organism
       *   - Filters might include the new organism
       *   - We want users to see the latest data
       *
       * 🎓 LEARNING NOTE: Partial Matching
       * queryKey: ['organisms'] matches ALL keys starting with 'organisms'
       */
      queryClient.invalidateQueries({ queryKey: ['organisms'] })

      /**
       * 🎓 ALTERNATIVE: Optimistic Update
       *
       * Instead of invalidating (refetch), we could manually update the cache:
       *
       * ```typescript
       * queryClient.setQueryData<Organism[]>(['organisms'], (old) => {
       *   return old ? [...old, data] : [data]
       * })
       * ```
       *
       * Pros: Instant UI update, no refetch needed
       * Cons: More complex, might miss server-side changes
       *
       * For now, we use invalidation (simpler, safer).
       */
    },

    /**
     * 🎓 ON ERROR: Callback if mutation fails
     *
     * Called with the error from the API.
     *
     * Common use cases:
     *   - Show error toast
     *   - Log error for debugging
     *   - Handle specific error codes
     *
     * @param error - ApiError thrown by createOrganism()
     */
    // onError: (error) => {
    //   // Let calling component handle errors
    //   // You can add global error handling here if needed
    //   console.error('Failed to create organism:', error)
    // },

    /**
     * 🎓 ON SETTLED: Callback after mutation completes (success or error)
     *
     * Always called after onSuccess or onError.
     *
     * Common use cases:
     *   - Hide loading spinner
     *   - Reset form
     *   - Close modal
     */
    // onSettled: () => {
    //   console.log('Mutation complete')
    // },
  })
}

/**
 * 🎓 LEARNING NOTE: How to Use Mutations
 *
 * There are TWO ways to call mutations:
 *
 * 1. mutate() - Fire and forget:
 *    ```tsx
 *    const createMutation = useCreateOrganism()
 *    createMutation.mutate({ code: "eco", name: "E. coli" })
 *    // Continues immediately, doesn't wait for result
 *    ```
 *
 * 2. mutateAsync() - Wait for result:
 *    ```tsx
 *    const createMutation = useCreateOrganism()
 *    try {
 *      const organism = await createMutation.mutateAsync({
 *        code: "eco",
 *        name: "E. coli"
 *      })
 *      console.log('Created:', organism.id)
 *    } catch (error) {
 *      console.error('Failed:', error)
 *    }
 *    ```
 *
 * When to use each?
 *   - mutate(): When you handle success/error via callbacks
 *   - mutateAsync(): When you need to await the result
 */

/**
 * 🎓 LEARNING NOTE: Mutation States
 *
 * Mutations have four states:
 *
 * 1. idle: Not started yet
 *    isPending: false, isSuccess: false, isError: false
 *
 * 2. pending: Currently running
 *    isPending: true, isSuccess: false, isError: false
 *
 * 3. success: Completed successfully
 *    isPending: false, isSuccess: true, isError: false, data: {...}
 *
 * 4. error: Failed
 *    isPending: false, isSuccess: false, isError: true, error: {...}
 *
 * You can use these states to show different UI:
 *   {isPending && <Spinner />}
 *   {isError && <Alert>{error.message}</Alert>}
 *   {isSuccess && <Success>Organism created!</Success>}
 */
