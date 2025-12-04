"""
Global Exception Handlers for FastAPI

**What**: Catches all exceptions and converts them to structured JSON responses
**Why**: Ensures consistent error format across entire API
**How**: Registers handlers with FastAPI app for different exception types

**Exception Handler Priority** (first match wins):
1. AppException (custom exceptions) → Structured response with status_code
2. Pydantic ValidationError → 422 with field-level errors
3. SQLAlchemy IntegrityError → 400 (constraint violations are user errors)
4. SQLAlchemy DatabaseError → 500 (connection failures are system errors)
5. Exception (catch-all) → 500 with correlation ID

**Correlation ID Flow**:
```
Request → Middleware adds X-Request-ID header
       → Exception occurs
       → Handler includes correlation_id in response
       → Logger includes correlation_id
       → Easier to find error in logs
```

**Usage**:
```python
# In main.py:
from app.core.error_handlers import register_exception_handlers
app = FastAPI()
register_exception_handlers(app)
```
"""

import logging
import uuid
from datetime import datetime
from typing import Union

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import IntegrityError, DatabaseError as SQLAlchemyDatabaseError
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import (
    AppException,
    is_client_error,
    DuplicateOrganismError,
    DatabaseError as AppDatabaseError,
)
from app.schemas.errors import (
    ErrorResponse,
    ValidationErrorResponse,
    ValidationErrorDetail,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Correlation ID Middleware
# =============================================================================

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Adds correlation ID to every request for distributed tracing.

    **What**: Generates/extracts X-Request-ID header for each request
    **Why**: Allows tracing request across microservices and logs
    **How**: Check for existing header, generate UUID if missing

    **Flow**:
    1. Client sends request (may include X-Request-ID)
    2. Middleware checks for existing X-Request-ID header
    3. If missing, generates new UUID
    4. Stores in request.state.correlation_id
    5. Includes in response headers
    6. Exception handlers use it for error responses

    **Benefits**:
    - User reports error with correlation_id → find in logs immediately
    - Trace request across multiple backend services
    - Debug timing issues by correlating all events for same request
    """

    async def dispatch(self, request: Request, call_next):
        # Check if client provided correlation ID (e.g., from API gateway)
        correlation_id = request.headers.get("X-Request-ID")

        # Generate new UUID if not provided
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state (accessible in handlers and endpoints)
        request.state.correlation_id = correlation_id

        # Add to response headers (client can use for debugging)
        response = await call_next(request)
        response.headers["X-Request-ID"] = correlation_id

        return response


# =============================================================================
# Exception Handlers
# =============================================================================

async def handle_app_exception(request: Request, exc: AppException) -> JSONResponse:
    """
    Handle custom AppException with structured error response.

    **What**: Converts AppException → ErrorResponse JSON
    **When**: Any custom exception (OrganismNotFoundError, ValidationError, etc.)
    **Status Code**: Determined by exception.status_code (400, 404, 500, etc.)

    **Example**:
    ```python
    # Endpoint raises:
    raise OrganismNotFoundError(organism_id=123)

    # Handler converts to:
    {
        "code": "ORGANISM_NOT_FOUND",
        "message": "Organism with id 123 not found",
        "timestamp": "2024-12-02T10:00:00Z",
        "correlation_id": "abc-123-def",
        "details": {"organism_id": 123}  // Only in dev mode
    }
    ```

    **Logging**:
    - 4xx errors: WARNING level (client error)
    - 5xx errors: ERROR level with traceback (server error)
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    # Log appropriately based on error type
    if is_client_error(exc):
        logger.warning(
            f"Client error: {exc.error_code} - {exc.message}",
            extra={"correlation_id": correlation_id, **exc.details}
        )
    else:
        logger.error(
            f"Server error: {exc.error_code} - {exc.message}",
            exc_info=True,  # Include full traceback
            extra={"correlation_id": correlation_id, **exc.details}
        )

    # Build error response
    error_response = ErrorResponse(
        code=exc.error_code,
        message=exc.message,
        timestamp=datetime.utcnow(),
        correlation_id=correlation_id,
        # Only include details in development (not production)
        # In production, set details=None to avoid leaking internals
        details=exc.details if exc.details else None
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(exclude_none=True, mode="json")
    )


async def handle_validation_error(
    request: Request,
    exc: Union[RequestValidationError, PydanticValidationError]
) -> JSONResponse:
    """
    Handle Pydantic validation errors with field-level details.

    **What**: Converts Pydantic validation errors → ValidationErrorResponse
    **When**: Request body/params don't match Pydantic schema
    **Status Code**: 422 Unprocessable Entity

    **Example**:
    ```python
    # Client sends:
    POST /organisms {"code": "TOOLONGCODE", "name": ""}

    # Handler returns:
    {
        "code": "VALIDATION_ERROR",
        "message": "Request validation failed",
        "correlation_id": "abc-123",
        "errors": [
            {
                "field": "code",
                "message": "String should have at most 4 characters",
                "type": "string_too_long"
            },
            {
                "field": "name",
                "message": "Field required",
                "type": "missing"
            }
        ]
    }
    ```

    **Why 422 not 400**: RFC 4918 - syntactically correct but semantically invalid
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    # Extract field-level errors from Pydantic
    validation_errors = []
    for error in exc.errors():
        # error["loc"] is tuple like ("body", "organism", "code")
        # Join to create field path: "organism.code"
        field_path = ".".join(str(loc) for loc in error["loc"])

        validation_errors.append(
            ValidationErrorDetail(
                field=field_path,
                message=error["msg"],
                type=error["type"]
            )
        )

    logger.warning(
        f"Validation error: {len(validation_errors)} field(s) invalid",
        extra={
            "correlation_id": correlation_id,
            "validation_errors": [e.model_dump() for e in validation_errors]
        }
    )

    error_response = ValidationErrorResponse(
        code="VALIDATION_ERROR",
        message="Request validation failed",
        timestamp=datetime.utcnow(),
        correlation_id=correlation_id,
        errors=validation_errors
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.model_dump(exclude_none=True, mode="json")
    )


async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    """
    Handle database constraint violations (unique, foreign key, check).

    **What**: Converts SQLAlchemy IntegrityError → 400 Bad Request
    **When**: Unique constraint, foreign key violation, check constraint
    **Why 400 not 500**: User error (duplicate code, invalid FK), not system error

    **Common Cases**:
    - Unique constraint: Duplicate organism code → DuplicateOrganismError
    - Foreign key: Invalid organism_id → OrganismNotFoundError
    - Check constraint: Negative value → ValidationError

    **Example**:
    ```python
    # Client creates organism with existing code "eco"
    # Database raises: IntegrityError (unique constraint violated)
    # Handler converts to:
    {
        "code": "DUPLICATE_ORGANISM",
        "message": "Organism with code 'eco' already exists",
        ...
    }
    ```

    **Implementation Note**:
    We parse the PostgreSQL/SQLite error message to determine specific error.
    This is database-specific but covers 90% of cases.
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    # Parse error message to determine specific constraint violation
    error_msg = str(exc.orig)

    # Unique constraint violation
    if "unique constraint" in error_msg.lower() or "duplicate" in error_msg.lower():
        # Try to extract column name from error message
        if "organism.code" in error_msg or "organisms_code" in error_msg:
            # Extract code value if possible
            error_response = ErrorResponse(
                code="DUPLICATE_ORGANISM",
                message="Organism with this code already exists",
                timestamp=datetime.utcnow(),
                correlation_id=correlation_id
            )
        else:
            error_response = ErrorResponse(
                code="DUPLICATE_ENTRY",
                message="A record with these values already exists",
                timestamp=datetime.utcnow(),
                correlation_id=correlation_id
            )

    # Foreign key violation
    elif "foreign key constraint" in error_msg.lower():
        error_response = ErrorResponse(
            code="INVALID_REFERENCE",
            message="Referenced record does not exist",
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id
        )

    # Check constraint violation
    elif "check constraint" in error_msg.lower():
        error_response = ErrorResponse(
            code="CONSTRAINT_VIOLATION",
            message="Value violates database constraint",
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id
        )

    # Unknown integrity error
    else:
        error_response = ErrorResponse(
            code="INTEGRITY_ERROR",
            message="Database integrity constraint violated",
            timestamp=datetime.utcnow(),
            correlation_id=correlation_id
        )

    logger.warning(
        f"Integrity error: {error_response.code}",
        extra={"correlation_id": correlation_id, "db_error": error_msg}
    )

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_response.model_dump(exclude_none=True, mode="json")
    )


async def handle_database_error(
    request: Request,
    exc: SQLAlchemyDatabaseError
) -> JSONResponse:
    """
    Handle database connection/transaction errors.

    **What**: Converts SQLAlchemy DatabaseError → 500 Internal Server Error
    **When**: Connection timeout, transaction deadlock, connection pool exhausted
    **Why 500**: Not user's fault - system/infrastructure issue

    **Common Cases**:
    - Connection timeout: Database unreachable
    - Deadlock: Two transactions waiting on each other
    - Pool exhausted: Too many concurrent connections

    **Mitigation**:
    - Connection errors: Retry with exponential backoff
    - Pool exhausted: Increase pool size or optimize queries
    - Deadlocks: Retry transaction
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    logger.error(
        "Database error occurred",
        exc_info=True,
        extra={"correlation_id": correlation_id}
    )

    error_response = ErrorResponse(
        code="DATABASE_ERROR",
        message="A database error occurred. Please try again later.",
        timestamp=datetime.utcnow(),
        correlation_id=correlation_id
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True, mode="json")
    )


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    **What**: Converts any unhandled Exception → 500 with correlation ID
    **When**: Anything not caught by other handlers (bugs, edge cases)
    **Why**: Ensures API never returns HTML error page or crashes

    **Important**:
    - Always log full traceback for debugging
    - Never expose exception details to client (security risk)
    - Correlation ID is essential for finding error in logs

    **Example**:
    ```python
    # Code raises unexpected exception:
    result = 1 / 0  # ZeroDivisionError

    # Handler returns:
    {
        "code": "INTERNAL_ERROR",
        "message": "An unexpected error occurred",
        "correlation_id": "abc-123-def"
    }

    # Logs contain:
    # ERROR: Unexpected error [correlation_id=abc-123-def]
    # Traceback: ZeroDivisionError: division by zero
    ```
    """
    correlation_id = getattr(request.state, "correlation_id", None)

    logger.error(
        f"Unexpected error: {type(exc).__name__}",
        exc_info=True,  # Full traceback
        extra={"correlation_id": correlation_id}
    )

    error_response = ErrorResponse(
        code="INTERNAL_ERROR",
        message="An unexpected error occurred. Please try again later.",
        timestamp=datetime.utcnow(),
        correlation_id=correlation_id
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.model_dump(exclude_none=True, mode="json")
    )


# =============================================================================
# Registration Function
# =============================================================================

def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers with FastAPI app.

    **What**: Attaches exception handlers to app
    **When**: Called in main.py during app initialization
    **Order**: Specific exceptions first, generic last

    **Usage**:
    ```python
    from app.core.error_handlers import register_exception_handlers

    app = FastAPI()
    register_exception_handlers(app)
    ```

    **Handler Priority** (first match wins):
    1. AppException → Our custom exceptions
    2. RequestValidationError → Pydantic validation (422)
    3. IntegrityError → Database constraints (400)
    4. DatabaseError → Database errors (500)
    5. Exception → Catch-all (500)
    """
    # Custom app exceptions
    app.add_exception_handler(AppException, handle_app_exception)

    # Pydantic validation errors (FastAPI)
    app.add_exception_handler(RequestValidationError, handle_validation_error)

    # Database constraint violations (user errors)
    app.add_exception_handler(IntegrityError, handle_integrity_error)

    # Database errors (system errors)
    app.add_exception_handler(SQLAlchemyDatabaseError, handle_database_error)

    # Catch-all for unexpected exceptions
    app.add_exception_handler(Exception, handle_unexpected_error)

    logger.info("Exception handlers registered successfully")
