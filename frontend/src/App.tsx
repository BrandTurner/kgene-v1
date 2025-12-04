/**
 * App Component - Main Application Router
 *
 * 🎓 LEARNING NOTE: React Router v6
 *
 * React Router handles client-side routing (navigation without page reload).
 *
 * Key concepts:
 *   - BrowserRouter: Uses HTML5 history API (clean URLs)
 *   - Routes: Container for all route definitions
 *   - Route: Maps URL path to component
 *
 * Example:
 *   URL: /                 → Renders Dashboard component
 *   URL: /organisms/123    → Renders OrganismDetail component
 *   URL: /anything-else    → Renders NotFound component
 *
 * Changes from React Router v5 (if you used it in 2022):
 *   - <Routes> instead of <Switch>
 *   - element={<Component />} instead of component={Component}
 *   - No more exact prop (exact matching is default)
 *   - Nested routes work differently
 */

import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { ErrorBoundary } from 'react-error-boundary'
import Dashboard from '@/pages/Dashboard'

/**
 * 🎓 LEARNING NOTE: Error Boundary
 *
 * Error boundaries catch JavaScript errors in child components.
 *
 * Without error boundary:
 *   Component throws error → Entire app crashes → White screen of death
 *
 * With error boundary:
 *   Component throws error → Error boundary catches it → Shows fallback UI
 *
 * Note: Error boundaries only catch:
 *   ✅ Rendering errors
 *   ✅ Lifecycle method errors
 *   ✅ Constructor errors
 *
 * They don't catch:
 *   ❌ Event handler errors (use try/catch)
 *   ❌ Async errors (use try/catch)
 *   ❌ Errors in error boundary itself
 */
function ErrorFallback({ error }: { error: Error }) {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="max-w-md w-full bg-white shadow-lg rounded-lg p-6">
        <h2 className="text-2xl font-bold text-red-600 mb-4">
          Something went wrong
        </h2>
        <p className="text-gray-700 mb-4">
          {error.message}
        </p>
        <button
          onClick={() => window.location.reload()}
          className="bg-primary-500 text-white px-4 py-2 rounded hover:bg-primary-600 transition-colors"
        >
          Reload Page
        </button>
      </div>
    </div>
  )
}

/**
 * Main App component with routing and error handling
 */
function App() {
  return (
    <>
      {/**
       * Wrap entire app in ErrorBoundary
       * Any error in Dashboard or other components will be caught
       */}
      <ErrorBoundary
        FallbackComponent={ErrorFallback}
        onError={(error, errorInfo) => {
          /**
           * 🎓 LEARNING NOTE: Error Logging
           *
           * In production, you'd send this to error tracking service:
           *   - Sentry
           *   - LogRocket
           *   - Datadog
           *   - etc.
           *
           * For now, just console.error in development.
           */
          if (import.meta.env.DEV) {
            console.error('Error caught by boundary:', error, errorInfo)
          }
        }}
      >
        {/**
         * 🎓 LEARNING NOTE: BrowserRouter
         *
         * Provides routing context to all child components.
         * Uses HTML5 pushState API for navigation.
         *
         * Alternative routers:
         *   - HashRouter: Uses URL hash (#/path) - works without server config
         *   - MemoryRouter: In-memory history (for testing)
         *   - StaticRouter: Server-side rendering
         *
         * We use BrowserRouter for clean URLs and better SEO.
         */}
        <BrowserRouter>
          {/**
           * Main app layout
           *
           * 🎓 TAILWIND CLASSES EXPLAINED:
           *   - min-h-screen: Minimum height = 100vh (full viewport)
           *   - bg-gray-50: Light gray background (from tailwind.config.js)
           */}
          <div className="min-h-screen bg-gray-50">
            {/**
             * Header / Navigation
             *
             * 🎓 TAILWIND CLASSES:
             *   - bg-white: White background
             *   - shadow: Subtle box-shadow
             *   - border-b: Bottom border
             *   - border-gray-200: Light gray border color
             */}
            <header className="bg-white shadow border-b border-gray-200">
              {/**
               * 🎓 TAILWIND CLASSES:
               *   - max-w-7xl: Maximum width (1280px)
               *   - mx-auto: Margin auto (center horizontally)
               *   - px-4: Padding left/right 1rem
               *   - py-6: Padding top/bottom 1.5rem
               */}
              <div className="max-w-7xl mx-auto px-4 py-6">
                <h1 className="text-3xl font-bold text-gray-900">
                  KEGG Explore
                </h1>
                <p className="text-sm text-gray-600 mt-1">
                  Gene ortholog discovery and analysis
                </p>
              </div>
            </header>

            {/**
             * Main content area
             *
             * 🎓 TAILWIND CLASSES:
             *   - max-w-7xl: Constrain width for readability
             *   - mx-auto: Center content
             *   - px-4: Padding left/right
             *   - py-8: Padding top/bottom 2rem
             */}
            <main className="max-w-7xl mx-auto px-4 py-8">
              {/**
               * 🎓 LEARNING NOTE: Routes Component
               *
               * Routes scans all child <Route> components
               * and renders the first one that matches the current URL.
               *
               * Only ONE route renders at a time (like switch statement).
               */}
              <Routes>
                {/**
                 * 🎓 LEARNING NOTE: Route Component
                 *
                 * Props:
                 *   - path: URL pattern to match
                 *   - element: Component to render
                 *
                 * path="/" matches exactly "/"
                 * path="/organisms/:id" matches "/organisms/123" (with param)
                 * path="*" matches any unmatched routes (404)
                 */}
                <Route path="/" element={<Dashboard />} />

                {/**
                 * 🎓 TODO: Add more routes as we build features
                 *
                 * <Route path="/organisms/:id" element={<OrganismDetail />} />
                 * <Route path="/genes" element={<GeneBrowser />} />
                 * <Route path="/processes" element={<ProcessMonitor />} />
                 * <Route path="*" element={<NotFound />} />
                 */}
              </Routes>
            </main>
          </div>
        </BrowserRouter>
      </ErrorBoundary>
    </>
  )
}

/**
 * 🎓 LEARNING NOTE: Default Export
 *
 * export default App
 *
 * Allows importing without braces:
 *   import App from './App'    ✅ (default)
 *   import { App } from './App' ❌ (would need named export)
 *
 * Each file can have ONE default export and multiple named exports.
 */
export default App
