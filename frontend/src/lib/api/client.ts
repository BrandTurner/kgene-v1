/**
 * API Client - Axios Instance with Interceptors
 *
 * 🎓 LEARNING NOTE: What is Axios?
 *
 * Axios is an HTTP client library (alternative to native fetch).
 *
 * Why Axios over fetch?
 *   - Automatic JSON transformation
 *   - Request/response interceptors (middleware)
 *   - Better error handling
 *   - Request cancellation
 *   - TypeScript-friendly
 *
 * Example comparison:
 *
 * Fetch (native):
 *   const response = await fetch(url)
 *   if (!response.ok) throw new Error(...)
 *   const data = await response.json()
 *
 * Axios:
 *   const { data } = await axios.get(url)  // Done!
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios'
import { ApiError, ErrorResponse } from '@/types'

/**
 * 🎓 LEARNING NOTE: import.meta.env (Vite environment variables)
 *
 * In Vite, environment variables are accessed via import.meta.env
 * (NOT process.env like in Create React App or Node.js)
 *
 * - Variables must start with VITE_ prefix to be exposed to client
 * - Defined in .env.development file
 * - Type-safe with TypeScript's ImportMetaEnv interface
 *
 * Example .env.development:
 *   VITE_API_BASE_URL=http://localhost:8000
 *
 * Access:
 *   import.meta.env.VITE_API_BASE_URL  // "http://localhost:8000"
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

/**
 * Create Axios instance with base configuration
 *
 * 🎓 LEARNING NOTE: axios.create()
 * Creates a new Axios instance with custom defaults.
 * All requests made with this instance inherit these settings.
 */
export const apiClient = axios.create({
  /**
   * Base URL: Prepended to all relative URLs
   * Example: axios.get('/organisms') → GET http://localhost:8000/organisms
   */
  baseURL: `${API_BASE_URL}/api`,

  /**
   * Timeout: Abort request after 30 seconds
   * Prevents hanging requests if backend is down
   */
  timeout: 30000,

  /**
   * Headers: Sent with every request
   */
  headers: {
    'Content-Type': 'application/json',
  },
})

/**
 * 🎓 LEARNING NOTE: Request Interceptors
 *
 * Interceptors run BEFORE the request is sent.
 * Use cases:
 *   - Add authentication tokens
 *   - Add correlation IDs for tracking
 *   - Log requests
 *   - Modify request data
 *
 * Flow:
 *   axios.get(url) → interceptor → HTTP request → server
 */
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    /**
     * Add correlation ID to every request
     *
     * 🎓 WHY?
     * The backend logs this ID with every operation.
     * If something goes wrong, we can trace the exact request.
     *
     * Example:
     *   Frontend: X-Request-ID: 550e8400-e29b-41d4-a716-446655440000
     *   Backend logs: [550e8400...] Processing organism creation
     *   Backend logs: [550e8400...] Duplicate organism error
     *   Backend response: correlation_id: 550e8400...
     *
     * Now you can search logs for "550e8400" and see the full story!
     */
    if (!config.headers['X-Request-ID']) {
      // 🎓 crypto.randomUUID(): Native browser API for UUID generation
      // Available in all modern browsers (Chrome 92+, Firefox 95+, Safari 15.4+)
      config.headers['X-Request-ID'] = crypto.randomUUID()
    }

    return config
  },
  (error) => {
    // Request interceptor error (rare - usually network issues before request sent)
    return Promise.reject(error)
  }
)

/**
 * 🎓 LEARNING NOTE: Response Interceptors
 *
 * Interceptors run AFTER the response is received.
 * Use cases:
 *   - Transform response data
 *   - Handle errors globally
 *   - Extract correlation IDs
 *   - Refresh auth tokens
 *
 * Flow:
 *   server → HTTP response → interceptor → axios.get() result
 */
apiClient.interceptors.response.use(
  (response) => {
    /**
     * Success response: Just return it
     * No transformation needed - Axios already parsed JSON
     */
    return response
  },
  (error: AxiosError<ErrorResponse>) => {
    /**
     * Error response: Transform into our ApiError class
     *
     * 🎓 LEARNING NOTE: Error Handling Flow
     *
     * When backend returns an error (4xx or 5xx status):
     *   1. Axios creates an AxiosError
     *   2. We intercept it here
     *   3. We extract error details from response.data
     *   4. We create an ApiError with structured data
     *   5. We reject the promise with ApiError
     *   6. Calling code can catch ApiError and handle it
     *
     * Example:
     *   try {
     *     await createOrganism({ code: "eco", name: "E. coli" })
     *   } catch (error) {
     *     if (error instanceof ApiError) {
     *       console.log(error.code)  // "DUPLICATE_ORGANISM"
     *       console.log(error.correlationId)  // "550e..."
     *     }
     *   }
     */

    if (error.response) {
      /**
       * Server responded with error status (4xx, 5xx)
       *
       * error.response.data: Backend's ErrorResponse
       * error.response.status: HTTP status code (400, 404, 500, etc.)
       */
      const errorData = error.response.data
      const statusCode = error.response.status

      // Create structured ApiError
      const apiError = new ApiError(
        errorData?.message || error.message || 'An unexpected error occurred',
        errorData?.code || 'UNKNOWN_ERROR',
        statusCode,
        errorData?.correlation_id,
        errorData?.details,
        errorData
      )

      // Log error for debugging (in development)
      if (import.meta.env.DEV) {
        console.error('API Error:', {
          code: apiError.code,
          message: apiError.message,
          correlationId: apiError.correlationId,
          statusCode: apiError.statusCode,
          details: apiError.details,
        })
      }

      return Promise.reject(apiError)
    } else if (error.request) {
      /**
       * Request was sent but no response received
       *
       * Common causes:
       *   - Backend is down
       *   - Network is offline
       *   - Request timed out
       *   - CORS blocked the request
       */
      const apiError = new ApiError(
        'No response from server. Please check your connection.',
        'NETWORK_ERROR',
        0, // No HTTP status since no response
        undefined,
        { originalError: error.message }
      )

      if (import.meta.env.DEV) {
        console.error('Network Error:', apiError)
      }

      return Promise.reject(apiError)
    } else {
      /**
       * Error happened during request setup (rare)
       *
       * Example: Invalid URL, malformed request
       */
      const apiError = new ApiError(
        error.message || 'Request setup failed',
        'REQUEST_ERROR',
        0,
        undefined,
        { originalError: error.message }
      )

      if (import.meta.env.DEV) {
        console.error('Request Error:', apiError)
      }

      return Promise.reject(apiError)
    }
  }
)

/**
 * 🎓 LEARNING NOTE: TypeScript Generics
 *
 * The <T> syntax means "generic type parameter".
 * It's a placeholder for a type that's specified when you call the function.
 *
 * Example without generics (bad):
 *   async function get(url: string): Promise<any>
 *   const data = await get('/organisms')  // data is 'any' - no type safety!
 *
 * Example with generics (good):
 *   async function get<T>(url: string): Promise<T>
 *   const data = await get<Organism[]>('/organisms')  // data is Organism[]!
 *
 * Now TypeScript knows:
 *   data[0].code  // ✅ TypeScript knows this exists
 *   data[0].foo   // ❌ TypeScript error: 'foo' doesn't exist on Organism
 */

/**
 * Export the configured Axios instance
 *
 * Usage in other files:
 *   import { apiClient } from '@/lib/api/client'
 *   const { data } = await apiClient.get<Organism[]>('/organisms')
 */
export default apiClient
