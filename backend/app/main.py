"""
VendorIQ - AI-Powered Supplier Qualification & Batch Intelligence Platform
Main FastAPI Application Entrypoint (Unified Backend)
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from app.core.config import settings
from app.core.errors import setup_exception_handlers
from app.core.database import get_engine, Base
from app.services.inbound_email_service import (
    start_inbound_email_worker,
    stop_inbound_email_worker,
)
import app.models  # Register all models on Base.metadata

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("vendoriq")

# Initialize FastAPI application with project metadata
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.PROJECT_DESCRIPTION,
    version=settings.VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Centralized Gzip response compression for fast API transport
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Configure centralized error handling
setup_exception_handlers(app)

# Configure CORS restrictions
# Allows FRONTEND_URL and CORS_ORIGINS from settings, with localhost defaults for local dev
cors_origins = settings.all_cors_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"^(https?://(localhost|127\.0\.0\.1)(:\d+)?|https://.*\.vercel\.app|https://.*\.onrender\.com)$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    try:
        # Create tables if not existing (especially useful for local dev / sqlite)
        engine = get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialized.")
    except Exception as e:
        logger.warning(f"Database schema auto-creation notice: {e}")
    start_inbound_email_worker()


@app.on_event("shutdown")
def on_shutdown():
    stop_inbound_email_worker()


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


# Register API Routers under /api
from app.routers import (
    auth_router,
    vendors_router,
    raw_materials_router,
    vendor_materials_router,
    batches_router,
    documents_router,
    predictions_router,
    analytics_router,
    alerts_router,
    email_events_router,
    settings_router,
)

app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(vendors_router, prefix=settings.API_V1_STR)
app.include_router(raw_materials_router, prefix=settings.API_V1_STR)
app.include_router(vendor_materials_router, prefix=settings.API_V1_STR)
app.include_router(batches_router, prefix=settings.API_V1_STR)
app.include_router(documents_router, prefix=settings.API_V1_STR)
app.include_router(predictions_router, prefix=settings.API_V1_STR)
app.include_router(analytics_router, prefix=settings.API_V1_STR)
app.include_router(alerts_router, prefix=settings.API_V1_STR)
app.include_router(email_events_router, prefix=settings.API_V1_STR)
app.include_router(settings_router, prefix=settings.API_V1_STR)

