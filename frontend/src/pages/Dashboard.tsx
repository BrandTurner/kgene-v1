/**
 * Dashboard Page - Organism Management
 *
 * 🎓 LEARNING NOTE: Modern React Component Structure (2024)
 *
 * This component demonstrates:
 *   - React Query hooks (no useEffect for data fetching!)
 *   - TypeScript props and state
 *   - Shadcn UI components
 *   - Modern React patterns
 *   - Error handling
 *   - Loading states
 *
 * Compare to OLD way (2020-2022):
 *   - Would use useState + useEffect
 *   - Manual loading/error states
 *   - Manual cache management
 *   - More code, more bugs
 */

import { useState } from 'react'
import { Plus, Trash2, AlertCircle } from 'lucide-react'
import { useOrganisms, useCreateOrganism, useDeleteOrganism } from '@/lib/hooks'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useToast } from '@/hooks/use-toast'
import type { Organism, ApiError } from '@/types'

/**
 * 🎓 LEARNING NOTE: Function Component
 *
 * Modern React components are just functions that return JSX.
 *
 * export default function Dashboard() {
 *   return <div>Hello</div>
 * }
 *
 * Key points:
 *   - Must start with capital letter (Dashboard, not dashboard)
 *   - Can use hooks (useState, useEffect, custom hooks)
 *   - Return JSX (HTML-like syntax)
 *   - Props are function parameters
 */
export default function Dashboard() {
  /**
   * 🎓 LEARNING NOTE: useState Hook
   *
   * useState creates reactive state in functional components.
   *
   * Syntax:
   *   const [value, setValue] = useState(initialValue)
   *         ↑      ↑           ↑
   *      current  setter   initial
   *
   * When you call setValue():
   *   - Component re-renders
   *   - value updates to new value
   *   - UI reflects the change
   *
   * Example:
   *   const [count, setCount] = useState(0)
   *   setCount(1)  // count becomes 1, component re-renders
   */

  // Dialog state: Controls create organism modal
  const [showCreateDialog, setShowCreateDialog] = useState(false)

  // Delete confirmation state
  const [organismToDelete, setOrganismToDelete] = useState<Organism | null>(null)

  // Form state for create organism
  const [formData, setFormData] = useState({
    code: '',
    name: '',
  })

  /**
   * 🎓 LEARNING NOTE: Custom Hooks (React Query)
   *
   * These hooks handle ALL data fetching logic:
   *   - No useEffect needed!
   *   - No manual loading states!
   *   - No manual error handling!
   *   - Automatic caching and refetching!
   *
   * OLD WAY (2022) - Don't do this:
   *   const [organisms, setOrganisms] = useState([])
   *   const [loading, setLoading] = useState(true)
   *   const [error, setError] = useState(null)
   *   useEffect(() => {
   *     fetch('/api/organisms')
   *       .then(r => r.json())
   *       .then(setOrganisms)
   *       .catch(setError)
   *       .finally(() => setLoading(false))
   *   }, [])
   *
   * NEW WAY (2024) - Do this:
   *   const { data: organisms, isLoading, error } = useOrganisms()
   *
   * Benefits:
   *   - 80% less code
   *   - Automatic caching
   *   - Background refetching
   *   - No race conditions
   *   - Better TypeScript support
   */
  const { data: organisms, isLoading, error } = useOrganisms()
  const createMutation = useCreateOrganism()
  const deleteMutation = useDeleteOrganism()

  /**
   * 🎓 LEARNING NOTE: useToast Hook (Shadcn UI)
   *
   * Shows temporary notification messages.
   *
   * Usage:
   *   toast({ title: "Success", description: "Organism created" })
   *   toast({ title: "Error", description: error.message, variant: "destructive" })
   */
  const { toast } = useToast()

  /**
   * 🎓 LEARNING NOTE: Event Handlers
   *
   * Event handlers are functions that run when user interacts with UI.
   *
   * Common patterns:
   *   - onClick: Button clicks
   *   - onChange: Input changes
   *   - onSubmit: Form submissions
   *
   * Naming convention: handle + EventName
   *   - handleSubmit
   *   - handleChange
   *   - handleDelete
   */

  /**
   * Handle form submission to create organism
   *
   * 🎓 LEARNING NOTE: Form Events
   *
   * e.preventDefault() stops default form behavior (page reload)
   * In modern React, we handle forms with JavaScript, not HTML form submission
   */
  const handleCreateOrganism = async (e: React.FormEvent) => {
    e.preventDefault()

    /**
     * 🎓 LEARNING NOTE: Form Validation
     *
     * Always validate user input before sending to API!
     *
     * Backend will also validate (defense in depth),
     * but frontend validation gives instant feedback.
     */
    if (!formData.code || !formData.name) {
      toast({
        title: 'Validation Error',
        description: 'Please fill in all fields',
        variant: 'destructive',
      })
      return
    }

    // Validate organism code format (3-4 lowercase letters)
    if (!/^[a-z]{3,4}$/.test(formData.code)) {
      toast({
        title: 'Invalid Code',
        description: 'Organism code must be 3-4 lowercase letters (e.g., "eco", "hsa")',
        variant: 'destructive',
      })
      return
    }

    /**
     * 🎓 LEARNING NOTE: Async Mutations
     *
     * We use mutateAsync() to await the result and handle success/error.
     *
     * Alternative: Use mutate() with callbacks:
     *   createMutation.mutate(formData, {
     *     onSuccess: () => { ... },
     *     onError: () => { ... }
     *   })
     */
    try {
      await createMutation.mutateAsync(formData)

      // Success! Show notification
      toast({
        title: 'Success',
        description: `Organism "${formData.name}" created successfully`,
      })

      // Close dialog and reset form
      setShowCreateDialog(false)
      setFormData({ code: '', name: '' })
    } catch (error) {
      /**
       * 🎓 LEARNING NOTE: Type Guards
       *
       * TypeScript doesn't know what type 'error' is.
       * We use 'as ApiError' to tell TypeScript the type.
       *
       * Always check if error has expected properties before using them!
       */
      const apiError = error as ApiError

      /**
       * 🎓 LEARNING NOTE: Error Handling by Code
       *
       * Our backend returns structured errors with codes.
       * We can show different messages based on the error code.
       */
      if (apiError.code === 'DUPLICATE_ORGANISM') {
        toast({
          title: 'Duplicate Organism',
          description: `Organism with code "${formData.code}" already exists`,
          variant: 'destructive',
        })
      } else {
        toast({
          title: 'Error',
          description: apiError.message || 'Failed to create organism',
          variant: 'destructive',
        })
      }
    }
  }

  /**
   * Handle organism deletion
   *
   * Two-step process:
   *   1. User clicks delete → Show confirmation dialog
   *   2. User confirms → Actually delete
   */
  const handleDeleteOrganism = async () => {
    if (!organismToDelete) return

    try {
      await deleteMutation.mutateAsync(organismToDelete.id)

      toast({
        title: 'Deleted',
        description: `Organism "${organismToDelete.name}" deleted successfully`,
      })

      setOrganismToDelete(null)
    } catch (error) {
      const apiError = error as ApiError

      toast({
        title: 'Error',
        description: apiError.message || 'Failed to delete organism',
        variant: 'destructive',
      })
    }
  }

  /**
   * 🎓 LEARNING NOTE: Early Returns for Loading/Error States
   *
   * Pattern: Handle special states first, then render main content.
   *
   * Benefits:
   *   - Cleaner code (no nested if statements)
   *   - Clear separation of states
   *   - Easy to understand flow
   */

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-gray-500">
          Loading organisms...
        </div>
      </div>
    )
  }

  // Error state
  if (error) {
    const apiError = error as ApiError

    return (
      <Alert variant="destructive">
        <AlertCircle className="h-4 w-4" />
        <AlertDescription>
          <strong>Error loading organisms:</strong> {apiError.message}
          {apiError.correlationId && (
            <div className="mt-2 text-sm">
              Correlation ID: <code>{apiError.correlationId}</code>
            </div>
          )}
        </AlertDescription>
      </Alert>
    )
  }

  /**
   * 🎓 LEARNING NOTE: Main Render
   *
   * If we reach here, data is loaded and no errors.
   * organisms is now guaranteed to be defined (TypeScript knows this!)
   */
  return (
    <div className="space-y-6">
      {/**
       * 🎓 TAILWIND CLASSES:
       *   - space-y-6: Add 1.5rem vertical space between children
       */}

      {/* Page header with create button */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Organisms</h2>
          <p className="text-sm text-gray-600 mt-1">
            Manage organisms for gene analysis
          </p>
        </div>

        <Button
          onClick={() => setShowCreateDialog(true)}
          className="bg-primary-500 hover:bg-primary-600"
        >
          <Plus className="mr-2 h-4 w-4" />
          Create Organism
        </Button>
      </div>

      {/* Organisms table */}
      <Card>
        <CardHeader>
          <CardTitle>All Organisms</CardTitle>
          <CardDescription>
            {organisms?.length || 0} organism(s) total
          </CardDescription>
        </CardHeader>
        <CardContent>
          {organisms?.length === 0 ? (
            /* Empty state */
            <div className="text-center py-12 text-gray-500">
              <p className="text-lg font-medium">No organisms yet</p>
              <p className="text-sm mt-2">
                Create your first organism to get started
              </p>
            </div>
          ) : (
            /* Table with data */
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Code</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {organisms?.map((organism) => (
                  <TableRow key={organism.id}>
                    <TableCell className="font-mono">{organism.code}</TableCell>
                    <TableCell>{organism.name}</TableCell>
                    <TableCell>
                      {organism.status ? (
                        <Badge
                          variant={
                            organism.status === 'complete'
                              ? 'default'
                              : organism.status === 'error'
                              ? 'destructive'
                              : 'secondary'
                          }
                        >
                          {organism.status}
                        </Badge>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {new Date(organism.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setOrganismToDelete(organism)}
                      >
                        <Trash2 className="h-4 w-4 text-red-600" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Create organism dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create Organism</DialogTitle>
            <DialogDescription>
              Add a new organism for gene analysis
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleCreateOrganism} className="space-y-4">
            <div>
              <label className="text-sm font-medium">
                Organism Code
              </label>
              <Input
                placeholder="eco"
                value={formData.code}
                onChange={(e) =>
                  setFormData({ ...formData, code: e.target.value.toLowerCase() })
                }
                maxLength={4}
                pattern="[a-z]{3,4}"
              />
              <p className="text-xs text-gray-500 mt-1">
                3-4 lowercase letters (e.g., "eco", "hsa", "mmu")
              </p>
            </div>

            <div>
              <label className="text-sm font-medium">
                Organism Name
              </label>
              <Input
                placeholder="Escherichia coli K-12 MG1655"
                value={formData.name}
                onChange={(e) =>
                  setFormData({ ...formData, name: e.target.value })
                }
              />
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowCreateDialog(false)}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createMutation.isPending}
              >
                {createMutation.isPending ? 'Creating...' : 'Create'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog
        open={!!organismToDelete}
        onOpenChange={() => setOrganismToDelete(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Organism?</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{organismToDelete?.name}"? This action
              cannot be undone.
            </DialogDescription>
          </DialogHeader>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setOrganismToDelete(null)}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDeleteOrganism}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? 'Deleting...' : 'Delete'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
