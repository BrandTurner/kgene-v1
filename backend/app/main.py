from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.api import organisms, genes

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

# Include API routers
app.include_router(organisms.router, prefix="/api", tags=["organisms"])
app.include_router(genes.router, prefix="/api", tags=["genes"])


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
