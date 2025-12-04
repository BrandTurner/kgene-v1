/**
 * useDeleteOrganism Hook - Delete Organism Mutation
 *
 * 🎓 LEARNING NOTE: Delete Mutations
 *
 * DELETE mutations are similar to POST, but:
 *   - Usually take just an ID (not full object)
 *   - Often return void (no response body)
 *   - Should invalidate queries to remove deleted item from UI
 */

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { deleteOrganism } from '../api/organisms'

/**
 * useDeleteOrganism - Hook to delete an organism
 *
 * @returns React Query mutation result
 *
 * @example Basic usage
 * ```tsx
 * function OrganismRow({ organism }) {
 *   const deleteMutation = useDeleteOrganism()
 *
 *   const handleDelete = () => {
 *     if (confirm(`Delete ${organism.name}?`)) {
 *       deleteMutation.mutate(organism.id)
 *     }
 *   }
 *
 *   return (
 *     <div>
 *       {organism.name}
 *       <button
 *         onClick={handleDelete}
 *         disabled={deleteMutation.isPending}
 *       >
 *         {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
 *       </button>
 *     </div>
 *   )
 * }
 * ```
 *
 * @example With confirmation dialog
 * ```tsx
 * const deleteMutation = useDeleteOrganism({
 *   onSuccess: () => {
 *     toast.success('Organism deleted')
 *     setShowDialog(false)
 *   },
 *   onError: (error) => {
 *     toast.error(`Failed to delete: ${error.message}`)
 *   }
 * })
 * ```
 */
export function useDeleteOrganism() {
  const queryClient = useQueryClient()

  return useMutation({
    /**
     * Mutation function: Delete organism by ID
     *
     * Takes: organism ID (number)
     * Returns: void (DELETE usually returns no body)
     *
     * 🎓 LEARNING NOTE: Why void?
     * DELETE requests typically return:
     *   - 204 No Content (no response body)
     *   - 200 OK with simple message
     *
     * We don't need the response - we just care that it succeeded.
     */
    mutationFn: (organismId: number) => deleteOrganism(organismId),

    /**
     * On success: Invalidate queries to refresh the UI
     *
     * When we delete an organism:
     *   1. Organism is removed from database
     *   2. Our cached list still includes it (out of date!)
     *   3. Invalidate queries → refetch → list updated
     *
     * 🎓 LEARNING NOTE: Why invalidate on delete?
     *
     * Option 1: Invalidate (what we do):
     *   - Mark queries as stale
     *   - React Query refetches
     *   - Server is source of truth
     *   - Pros: Simple, always accurate
     *   - Cons: Extra API call
     *
     * Option 2: Optimistic update (more advanced):
     *   - Manually remove from cache
     *   - No refetch needed
     *   - Pros: Instant UI update, no extra API call
     *   - Cons: More complex, might miss server state changes
     *
     * For MVP, we use invalidation (simpler).
     */
    onSuccess: () => {
      /**
       * Invalidate ALL organism queries
       *
       * This refetches:
       *   - Main organism list
       *   - Filtered organism lists
       *   - Individual organism queries (if they fetch lists)
       *
       * The deleted organism will be gone from all lists.
       */
      queryClient.invalidateQueries({ queryKey: ['organisms'] })

      /**
       * 🎓 ALTERNATIVE: Optimistic Delete
       *
       * Remove organism from cache manually:
       *
       * ```typescript
       * queryClient.setQueriesData<Organism[]>(
       *   { queryKey: ['organisms'] },
       *   (old) => old?.filter(org => org.id !== organismId)
       * )
       * ```
       *
       * This immediately removes the organism from UI without refetching.
       * We might add this later for better UX.
       */
    },

    /**
     * 🎓 LEARNING NOTE: Error Handling
     *
     * DELETE can fail for several reasons:
     *   - 404 Not Found: Organism already deleted
     *   - 403 Forbidden: No permission to delete
     *   - 409 Conflict: Organism has dependent data
     *
     * Let calling component handle errors via callbacks or error state:
     *
     * ```tsx
     * const deleteMutation = useDeleteOrganism()
     *
     * if (deleteMutation.isError) {
     *   const error = deleteMutation.error as ApiError
     *   if (error.code === 'ORGANISM_NOT_FOUND') {
     *     return <p>Organism already deleted</p>
     *   }
     * }
     * ```
     */
  })
}

/**
 * 🎓 LEARNING NOTE: Mutation Lifecycle
 *
 * When you call deleteMutation.mutate(organismId):
 *
 * 1. isPending becomes true
 *    → Show loading spinner in UI
 *
 * 2. mutationFn() is called
 *    → DELETE /api/organisms/123
 *
 * 3a. If successful:
 *    → onSuccess() is called
 *    → Queries invalidated
 *    → Lists refetch (organism disappears)
 *    → isSuccess becomes true
 *    → isPending becomes false
 *
 * 3b. If failed:
 *    → onError() is called (if provided)
 *    → isError becomes true
 *    → error contains ApiError
 *    → isPending becomes false
 *
 * 4. onSettled() is called (if provided)
 *    → Always runs after success or error
 *    → Good place to hide loading states
 */

/**
 * 🎓 LEARNING NOTE: Comparing Query and Mutation Hooks
 *
 * useOrganisms (query):
 *   const { data, isLoading, error, refetch } = useOrganisms()
 *   - Auto-runs on mount
 *   - Returns data
 *   - Caches results
 *   - Auto-refetches
 *   - Used for: Reading data
 *
 * useDeleteOrganism (mutation):
 *   const { mutate, isPending, isSuccess, error } = useDeleteOrganism()
 *   mutate(organismId)
 *   - Manual trigger
 *   - Returns void
 *   - No caching
 *   - One-time execution
 *   - Used for: Changing data
 *
 * Together they make a complete data management solution!
 */
