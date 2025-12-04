from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import organisms, genes, processes
from app.config import get_settings
from app.core.error_handlers import register_exception_handlers, CorrelationIDMiddleware

settings = get_settings()

# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Modern Python API for KEGG gene ortholog exploration",
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # React dev servers
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add correlation ID middleware for request tracing
# **What**: Adds X-Request-ID header to every request/response
# **Why**: Enables tracing errors across logs with correlation ID
# **How**: Checks for existing header, generates UUID if missing
app.add_middleware(CorrelationIDMiddleware)

# Register global exception handlers
# **What**: Converts all exceptions to structured JSON responses
# **Why**: Consistent error format across API, better debugging
# **How**: Handles AppException, ValidationError, DatabaseError, etc.
register_exception_handlers(app)

# Include API routers
app.include_router(organisms.router, prefix="/api", tags=["organisms"])
app.include_router(genes.router, prefix="/api", tags=["genes"])
app.include_router(processes.router, prefix="/api", tags=["processes"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "version": settings.app_version,
    }


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "KEGG Explore API",
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/api/health",
    }
