"""
Custom Exception Hierarchy for KEGG Explore API

**What**: Domain-specific exceptions with structured error information
**Why**: Provides consistent error handling, better debugging, and clear API responses
**How**: All exceptions inherit from AppException with status_code, error_code, and context

**Philosophy**:
- Each exception maps to a specific HTTP status code
- Error codes help clients programmatically handle errors
- Context dict provides debugging information without exposing internals
- Separates user errors (400-level) from system errors (500-level)

**Usage Example**:
```python
# In an API endpoint:
if not organism:
    raise OrganismNotFoundError(organism_id=123)

# Gets handled globally and returns:
{
    "code": "ORGANISM_NOT_FOUND",
    "message": "Organism with id 123 not found",
    "timestamp": "2024-12-02T10:00:00Z",
    "correlation_id": "abc-123-def",
    "details": {"organism_id": 123}
}
```
"""

from typing import Any, Dict, Optional


# =============================================================================
# Base Exception
# =============================================================================

class AppException(Exception):
    """
    Base exception for all application errors.

    **What**: Foundation for custom exception hierarchy
    **Why**: Allows global exception handler to catch all app errors consistently
    **How**: Subclasses override status_code, error_code, and message_template

    **Attributes**:
    - status_code: HTTP status code (e.g., 404, 400, 500)
    - error_code: Machine-readable error identifier (e.g., "ORGANISM_NOT_FOUND")
    - message: Human-readable error message
    - details: Additional context for debugging (not exposed to external users)
    """

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"
    message_template: str = "An unexpected error occurred"

    def __init__(self, message: Optional[str] = None, **details: Any):
        """
        Initialize exception with optional custom message and context.

        **Args**:
        - message: Override default message_template
        - **details: Key-value pairs for debugging context (e.g., organism_id=123)

        **Example**:
        ```python
        raise OrganismNotFoundError(organism_id=123)
        # message_template is auto-formatted with organism_id
        ```
        """
        self.details = details

        # Format message with details if template contains placeholders
        if message:
            self.message = message
        else:
            try:
                self.message = self.message_template.format(**details)
            except KeyError:
                # If template references missing detail keys, use template as-is
                self.message = self.message_template

        super().__init__(self.message)


# =============================================================================
# 404 Not Found Errors
# =============================================================================

class OrganismNotFoundError(AppException):
    """
    Raised when organism lookup by ID or code fails.

    **When to use**: GET/PUT/DELETE /organisms/{id} endpoints
    **Status**: 404 Not Found
    **Example**: User requests organism ID 999 that doesn't exist
    """
    status_code = 404
    error_code = "ORGANISM_NOT_FOUND"
    message_template = "Organism with {key} {value} not found"

    def __init__(self, organism_id: Optional[int] = None, code: Optional[str] = None):
        if organism_id is not None:
            super().__init__(key="id", value=organism_id, organism_id=organism_id)
        elif code is not None:
            super().__init__(key="code", value=code, code=code)
        else:
            super().__init__(key="identifier", value="unknown")


class GeneNotFoundError(AppException):
    """
    Raised when gene lookup by ID fails.

    **When to use**: GET/PUT/DELETE /genes/{id} endpoints
    **Status**: 404 Not Found
    """
    status_code = 404
    error_code = "GENE_NOT_FOUND"
    message_template = "Gene with id {gene_id} not found"


class JobNotFoundError(AppException):
    """
    Raised when background job lookup fails.

    **When to use**: GET /processes/{id}/progress when job_id doesn't exist in Redis
    **Status**: 404 Not Found
    **Note**: Different from organism not found - this is for job tracking
    """
    status_code = 404
    error_code = "JOB_NOT_FOUND"
    message_template = "Job with id {job_id} not found or expired"


# =============================================================================
# 400 Bad Request Errors (User Input Errors)
# =============================================================================

class DuplicateOrganismError(AppException):
    """
    Raised when attempting to create organism with existing code.

    **When to use**: POST /organisms with duplicate code
    **Status**: 400 Bad Request
    **Why 400 not 409**: User error (should check before creating), not conflict
    """
    status_code = 400
    error_code = "DUPLICATE_ORGANISM"
    message_template = "Organism with code '{code}' already exists"


class InvalidOrganismCodeError(AppException):
    """
    Raised when organism code doesn't match KEGG format.

    **When to use**: POST/PUT /organisms with invalid code format
    **Status**: 400 Bad Request
    **Valid format**: 3-4 lowercase letters (e.g., "eco", "hsa", "mmu")
    """
    status_code = 400
    error_code = "INVALID_ORGANISM_CODE"
    message_template = "Invalid organism code '{code}'. Must be 3-4 lowercase letters (e.g., 'eco', 'hsa')"


class InvalidStatusError(AppException):
    """
    Raised when status field contains invalid value.

    **When to use**: PUT /organisms with invalid status
    **Status**: 400 Bad Request
    **Valid values**: "pending", "complete", "error", or null
    """
    status_code = 400
    error_code = "INVALID_STATUS"
    message_template = "Invalid status '{status}'. Must be one of: pending, complete, error, or null"


class InvalidFilterParameterError(AppException):
    """
    Raised when query filter parameters are invalid.

    **When to use**: GET /organisms or /genes with invalid filter values
    **Status**: 400 Bad Request
    **Examples**: negative min_identity, invalid date format, unknown sort field
    """
    status_code = 400
    error_code = "INVALID_FILTER"
    message_template = "Invalid filter parameter: {reason}"


class OrganismAlreadyProcessingError(AppException):
    """
    Raised when attempting to start job for organism already being processed.

    **When to use**: POST /processes/{id}/start when status is "pending"
    **Status**: 400 Bad Request
    **Note**: Returns existing job_id to allow progress monitoring
    """
    status_code = 400
    error_code = "ORGANISM_ALREADY_PROCESSING"
    message_template = "Organism {organism_id} is already being processed (job_id: {job_id})"


# =============================================================================
# 422 Unprocessable Entity Errors (Validation)
# =============================================================================

class ValidationError(AppException):
    """
    Raised when Pydantic validation fails.

    **When to use**: Request body doesn't match schema
    **Status**: 422 Unprocessable Entity
    **Note**: FastAPI handles this automatically, but custom handler provides better format
    """
    status_code = 422
    error_code = "VALIDATION_ERROR"
    message_template = "Validation failed: {reason}"


# =============================================================================
# 500 Internal Server Errors (System Errors)
# =============================================================================

class KEGGServiceError(AppException):
    """
    Raised when KEGG API call fails after all retries.

    **When to use**: Background job encounters unrecoverable KEGG API error
    **Status**: 500 Internal Server Error
    **Note**: Not user's fault - external service failure
    **Logging**: Always log full traceback for debugging
    """
    status_code = 500
    error_code = "KEGG_SERVICE_ERROR"
    message_template = "KEGG API service error: {reason}"


class RedisConnectionError(AppException):
    """
    Raised when Redis connection fails.

    **When to use**:
    - Failed to connect to Redis for progress tracking
    - Failed to enqueue job to ARQ
    **Status**: 500 Internal Server Error
    **Mitigation**: Fall back to database status if Redis unavailable
    """
    status_code = 500
    error_code = "REDIS_CONNECTION_ERROR"
    message_template = "Redis connection failed: {reason}"


class DatabaseError(AppException):
    """
    Raised when database operation fails unexpectedly.

    **When to use**:
    - Connection failures
    - Transaction errors not related to constraints
    **Status**: 500 Internal Server Error
    **Note**: Don't use for constraint violations (those are 400 errors)
    """
    status_code = 500
    error_code = "DATABASE_ERROR"
    message_template = "Database operation failed: {reason}"


# =============================================================================
# 503 Service Unavailable Errors (Temporary)
# =============================================================================

class ServiceUnavailableError(AppException):
    """
    Raised when service is temporarily unavailable.

    **When to use**:
    - Database connection pool exhausted
    - Redis unavailable and fallback failed
    - KEGG API rate limit exceeded (after retries)
    **Status**: 503 Service Unavailable
    **Client action**: Retry after delay (Retry-After header can be added)
    """
    status_code = 503
    error_code = "SERVICE_UNAVAILABLE"
    message_template = "Service temporarily unavailable: {reason}"


# =============================================================================
# Convenience Functions
# =============================================================================

def is_client_error(exception: AppException) -> bool:
    """
    Check if exception is a client error (4xx) vs server error (5xx).

    **What**: Determines if error is user's fault or system's fault
    **Why**: Affects logging level (warn vs error) and monitoring alerts
    **Usage**:
    ```python
    if is_client_error(exc):
        logger.warning(f"Client error: {exc}")
    else:
        logger.error(f"Server error: {exc}", exc_info=True)
    ```
    """
    return 400 <= exception.status_code < 500


def is_retryable(exception: AppException) -> bool:
    """
    Check if client should retry the request.

    **What**: Indicates if request might succeed on retry
    **Why**: Helps clients implement smart retry logic
    **Returns**: True for 503, 429; False for 400, 404, 500
    """
    return exception.status_code in (429, 503)
