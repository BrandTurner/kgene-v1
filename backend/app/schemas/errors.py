"""
Error Response Schemas for API Consistency

**What**: Pydantic models for structured error responses
**Why**: Ensures all errors have consistent JSON format across API
**How**: FastAPI serializes exceptions using these schemas

**Standard Error Format**:
```json
{
    "code": "ORGANISM_NOT_FOUND",           // Machine-readable error code
    "message": "Organism with id 123...",   // Human-readable message
    "timestamp": "2024-12-02T10:00:00Z",   // When error occurred
    "correlation_id": "abc-123-def",        // Trace request across services
    "details": {"organism_id": 123}         // Debug context (dev only)
}
```

**Design Philosophy**:
- code: Allows clients to programmatically handle specific errors
- message: Shows to end users in UI
- timestamp: Helps correlate errors in logs
- correlation_id: Essential for debugging distributed systems
- details: Only included in development mode (not production)

**Usage in Exception Handler**:
```python
@app.exception_handler(AppException)
async def handle_app_exception(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.error_code,
            message=exc.message,
            ...
        ).model_dump()
    )
```
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """
    Standard error response for all API errors.

    **What**: Base error format returned by all endpoints
    **When**: Any exception occurs (AppException, database errors, validation errors)
    **Fields**:
    - code: ERROR_CODE in SCREAMING_SNAKE_CASE
    - message: Human-readable description
    - timestamp: ISO 8601 format (UTC)
    - correlation_id: Request ID for tracing
    - details: Optional debug info (not exposed in production)
    """

    code: str = Field(
        ...,
        description="Machine-readable error code (e.g., 'ORGANISM_NOT_FOUND')",
        examples=["ORGANISM_NOT_FOUND", "VALIDATION_ERROR", "DUPLICATE_ORGANISM"]
    )

    message: str = Field(
        ...,
        description="Human-readable error message for end users",
        examples=["Organism with id 123 not found", "Invalid organism code 'INVALID'"]
    )

    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the error occurred (UTC)",
        examples=["2024-12-02T10:00:00Z"]
    )

    correlation_id: Optional[str] = Field(
        None,
        description="Request ID for tracing across services (X-Request-ID header)",
        examples=["abc-123-def-456"]
    )

    details: Optional[Dict[str, Any]] = Field(
        None,
        description="Additional error context for debugging (development only)",
        examples=[{"organism_id": 123, "attempted_code": "INVALID"}]
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "code": "ORGANISM_NOT_FOUND",
                "message": "Organism with id 123 not found",
                "timestamp": "2024-12-02T10:00:00Z",
                "correlation_id": "abc-123-def",
                "details": {"organism_id": 123}
            }
        }


class ValidationErrorDetail(BaseModel):
    """
    Detailed validation error for a specific field.

    **What**: Describes what's wrong with a single field in request
    **When**: Pydantic validation fails (422 Unprocessable Entity)
    **Example**:
    ```json
    {
        "field": "organism.code",
        "message": "String should have at most 4 characters",
        "type": "string_too_long"
    }
    ```
    """

    field: str = Field(
        ...,
        description="Path to the invalid field (e.g., 'organism.code', 'genes[0].name')",
        examples=["organism.code", "min_identity", "genes[0].ortholog_identity"]
    )

    message: str = Field(
        ...,
        description="What's wrong with this field",
        examples=[
            "String should have at most 4 characters",
            "Input should be a valid number",
            "Field required"
        ]
    )

    type: str = Field(
        ...,
        description="Pydantic error type (machine-readable)",
        examples=["string_too_long", "missing", "value_error", "type_error"]
    )


class ValidationErrorResponse(ErrorResponse):
    """
    Extended error response for validation failures (422).

    **What**: Includes field-level validation errors
    **When**: Request body/params fail Pydantic validation
    **Why**: Helps clients know exactly which fields are invalid

    **Example**:
    ```json
    {
        "code": "VALIDATION_ERROR",
        "message": "Request validation failed",
        "timestamp": "2024-12-02T10:00:00Z",
        "correlation_id": "abc-123",
        "errors": [
            {
                "field": "organism.code",
                "message": "String should have at most 4 characters",
                "type": "string_too_long"
            },
            {
                "field": "organism.name",
                "message": "Field required",
                "type": "missing"
            }
        ]
    }
    ```
    """

    errors: List[ValidationErrorDetail] = Field(
        ...,
        description="List of field-level validation errors",
        min_length=1
    )

    class Config:
        """Pydantic configuration."""
        json_schema_extra = {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "timestamp": "2024-12-02T10:00:00Z",
                "correlation_id": "abc-123-def",
                "errors": [
                    {
                        "field": "organism.code",
                        "message": "String should have at most 4 characters",
                        "type": "string_too_long"
                    }
                ]
            }
        }


# =============================================================================
# OpenAPI Schema Examples
# =============================================================================

# These examples are used in endpoint decorators to document error responses
# Example usage:
# @router.get("/organisms/{id}", responses={404: {"model": ErrorResponse}})

ERROR_RESPONSE_404_EXAMPLE = {
    "description": "Resource not found",
    "content": {
        "application/json": {
            "example": {
                "code": "ORGANISM_NOT_FOUND",
                "message": "Organism with id 123 not found",
                "timestamp": "2024-12-02T10:00:00Z",
                "correlation_id": "abc-123-def"
            }
        }
    }
}

ERROR_RESPONSE_400_EXAMPLE = {
    "description": "Bad request - invalid input",
    "content": {
        "application/json": {
            "example": {
                "code": "DUPLICATE_ORGANISM",
                "message": "Organism with code 'eco' already exists",
                "timestamp": "2024-12-02T10:00:00Z",
                "correlation_id": "abc-123-def"
            }
        }
    }
}

ERROR_RESPONSE_422_EXAMPLE = {
    "description": "Validation error",
    "content": {
        "application/json": {
            "example": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "timestamp": "2024-12-02T10:00:00Z",
                "correlation_id": "abc-123-def",
                "errors": [
                    {
                        "field": "organism.code",
                        "message": "String should have at most 4 characters",
                        "type": "string_too_long"
                    }
                ]
            }
        }
    }
}

ERROR_RESPONSE_500_EXAMPLE = {
    "description": "Internal server error",
    "content": {
        "application/json": {
            "example": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "timestamp": "2024-12-02T10:00:00Z",
                "correlation_id": "abc-123-def"
            }
        }
    }
}
