"""
VendorIQ - AI-Powered Supplier Qualification & Batch Intelligence Platform
Main FastAPI Application Entrypoint
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.errors import setup_exception_handlers

# Initialize FastAPI application with project metadata
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure centralized error handling conforming to PRD Section 27
setup_exception_handlers(app)

# Configure CORS restrictions conforming to PRD Section 26
# Only allowed origins from FRONTEND_URL and CORS_ORIGINS are accepted
cors_origins = settings.all_cors_origins
if not cors_origins:
    cors_origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
def health_check():
    """
    Health check endpoint returning the current operational status of the service.
    """
    return {"status": "healthy"}


@app.get("/api/health", tags=["Health"], include_in_schema=False)
def api_health_check():
    """
    Alternative /api/health path for consistency with base /api prefix.
    """
    return {"status": "healthy"}


# Register API v1 Routers under /api
from app.routers import (
    auth_router,
    vendors_router,
    raw_materials_router,
    vendor_materials_router,
    batches_router,
)

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(vendors_router, prefix=settings.API_V1_STR)
app.include_router(raw_materials_router, prefix=settings.API_V1_STR)
app.include_router(vendor_materials_router, prefix=settings.API_V1_STR)
app.include_router(batches_router, prefix=settings.API_V1_STR)
