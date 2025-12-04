/**
 * Error Type Definitions
 *
 * 🎓 LEARNING NOTE: Error Handling in TypeScript
 *
 * When API calls fail, the backend returns structured error responses.
 * These types help us handle errors in a type-safe way.
 */

/**
 * ErrorResponse - Standard error response from backend
 *
 * Matches backend: backend/app/core/error_handlers.py - ErrorResponse
 *
 * ALL backend errors follow this format, whether:
 *   - 400 Bad Request (validation error)
 *   - 404 Not Found (resource doesn't exist)
 *   - 409 Conflict (duplicate organism)
 *   - 500 Internal Server Error
 *
 * Example error response:
 * ```json
 * {
 *   "code": "ORGANISM_NOT_FOUND",
 *   "message": "Organism with id 123 not found",
 *   "timestamp": "2025-12-03T12:00:00Z",
 *   "correlation_id": "550e8400-e29b-41d4-a716-446655440000",
 *   "details": { "organism_id": 123 }
 * }
 * ```
 */
export interface ErrorResponse {
  /**
   * Machine-readable error code (SCREAMING_SNAKE_CASE)
   *
   * Common codes:
   *   - ORGANISM_NOT_FOUND
   *   - DUPLICATE_ORGANISM
   *   - VALIDATION_ERROR
   *   - INTERNAL_ERROR
   *   - DUPLICATE_ENTRY
   */
  code: string;

  /**
   * Human-readable error message
   *
   * Example: "Organism with code 'eco' already exists"
   */
  message: string;

  /**
   * ISO 8601 timestamp when error occurred
   *
   * Example: "2025-12-03T12:00:00Z"
   */
  timestamp: string;

  /**
   * 🎓 IMPORTANT: Correlation ID for debugging
   *
   * This UUID tracks the request through the backend.
   * ALWAYS display this to the user when an error occurs!
   *
   * Why? If a user reports a bug, you can search backend logs
   * for this ID to see exactly what happened.
   *
   * Example: "550e8400-e29b-41d4-a716-446655440000"
   */
  correlation_id?: string;

  /**
   * Additional error details (varies by error type)
   *
   * 🎓 LEARNING NOTE: Record<string, any>
   * This is TypeScript for "an object with string keys and any values"
   * Similar to: { [key: string]: any }
   *
   * Example validation error details:
   * {
   *   "field": "code",
   *   "error": "Organism code must be 3-4 lowercase letters"
   * }
   */
  details?: Record<string, any>;
}

/**
 * ValidationError - Pydantic validation error detail
 *
 * When you send invalid data (like code: "TOOLONG"),
 * the backend returns validation errors in this format.
 *
 * Example response for invalid organism code:
 * ```json
 * {
 *   "code": "VALIDATION_ERROR",
 *   "message": "Request validation failed",
 *   "details": {
 *     "errors": [
 *       {
 *         "field": "body.code",
 *         "message": "Organism code must be 3-4 lowercase letters. Got: 'TOOLONG'",
 *         "type": "value_error"
 *       }
 *     ]
 *   }
 * }
 * ```
 */
export interface ValidationErrorDetail {
  /** Field that failed validation (e.g., "body.code", "code") */
  field: string;

  /** Human-readable error message */
  message: string;

  /** Error type from Pydantic (e.g., "value_error", "type_error") */
  type: string;
}

/**
 * ApiError - Client-side error wrapper
 *
 * 🎓 LEARNING NOTE: Extending Error class
 * This creates a custom error type that's still instanceof Error.
 *
 * We extend the native Error class to add our structured error data.
 *
 * Usage in try/catch:
 * ```typescript
 * try {
 *   await createOrganism({ code: "eco", name: "E. coli" })
 * } catch (error) {
 *   if (error instanceof ApiError) {
 *     console.log(error.code)           // "DUPLICATE_ORGANISM"
 *     console.log(error.correlationId)  // "550e..."
 *     toast.error(`Error: ${error.message}. ID: ${error.correlationId}`)
 *   }
 * }
 * ```
 */
export class ApiError extends Error {
  /** Machine-readable error code */
  code: string;

  /** HTTP status code (400, 404, 500, etc.) */
  statusCode: number;

  /** Correlation ID for debugging */
  correlationId?: string;

  /** Additional error details */
  details?: Record<string, any>;

  /** Original error response from backend */
  response?: ErrorResponse;

  constructor(
    message: string,
    code: string,
    statusCode: number,
    correlationId?: string,
    details?: Record<string, any>,
    response?: ErrorResponse
  ) {
    super(message);
    this.name = 'ApiError';
    this.code = code;
    this.statusCode = statusCode;
    this.correlationId = correlationId;
    this.details = details;
    this.response = response;

    // 🎓 LEARNING NOTE: Error.captureStackTrace
    // Maintains proper stack trace for debugging
    // (only works in V8 engines like Chrome/Node)
    if (Error.captureStackTrace) {
      Error.captureStackTrace(this, ApiError);
    }
  }
}
