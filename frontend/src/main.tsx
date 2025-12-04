/**
 * Application Entry Point
 *
 * 🎓 LEARNING NOTE: This is the root of your React app
 *
 * Flow:
 *   1. Vite loads index.html
 *   2. index.html loads this file (main.tsx)
 *   3. This file renders React app into <div id="root">
 *
 * Key differences from Create React App:
 *   - Vite: main.tsx (NOT index.tsx)
 *   - Vite: Uses createRoot (React 18 concurrent rendering)
 *   - Vite: Imports .tsx extension explicitly
 */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { ReactQueryDevtools } from '@tanstack/react-query-devtools'
import { Toaster } from '@/components/ui/toaster'
import { queryClient } from '@/config/queryClient'
import './index.css'
import App from './App.tsx'

/**
 * 🎓 LEARNING NOTE: createRoot (React 18)
 *
 * React 18 introduced a new root API:
 *   - Old (React 17): ReactDOM.render(<App />, element)
 *   - New (React 18): createRoot(element).render(<App />)
 *
 * Benefits:
 *   - Concurrent rendering (better performance)
 *   - Automatic batching (fewer re-renders)
 *   - Transitions (smooth UI updates)
 *
 * The ! operator tells TypeScript: "I'm sure this element exists"
 * If #root doesn't exist, this would throw an error (which is good - fail fast!)
 */
createRoot(document.getElementById('root')!).render(
  /**
   * 🎓 LEARNING NOTE: StrictMode
   *
   * StrictMode is a development tool that:
   *   - Identifies unsafe code patterns
   *   - Warns about deprecated APIs
   *   - Double-invokes functions to catch side effects
   *
   * Only runs in development (removed in production build).
   *
   * You might see some functions called twice in console.log - this is intentional!
   */
  <StrictMode>
    {/**
     * 🎓 LEARNING NOTE: QueryClientProvider
     *
     * Makes React Query available to all child components.
     * Similar to Context Provider pattern.
     *
     * Any component can now use:
     *   - useQuery (read data)
     *   - useMutation (change data)
     *   - useQueryClient (access cache)
     *
     * Must wrap your entire app (or at least parts that need data fetching).
     */}
    <QueryClientProvider client={queryClient}>
      <App />

      {/**
       * 🎓 LEARNING NOTE: Toaster
       *
       * Shadcn UI toast notification component.
       * Displays success/error/info messages.
       *
       * Usage in components:
       *   import { useToast } from '@/hooks/use-toast'
       *   const { toast } = useToast()
       *   toast({ title: "Success!", description: "Organism created" })
       *
       * This component renders the toast container.
       * Individual toasts are triggered from anywhere in the app.
       */}
      <Toaster />

      {/**
       * 🎓 LEARNING NOTE: ReactQueryDevtools
       *
       * Developer tools for React Query.
       * Shows in bottom-right corner (only in development).
       *
       * Features:
       *   - See all queries and their states
       *   - View cached data
       *   - Manually trigger refetches
       *   - See query timing
       *
       * Click the React Query icon in browser to open.
       * Automatically hidden in production builds.
       */}
      <ReactQueryDevtools initialIsOpen={false} />
    </QueryClientProvider>
  </StrictMode>,
)
