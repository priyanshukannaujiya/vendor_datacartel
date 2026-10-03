import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine, Base
from app.api.routes.health import router as health_router
from app.api.routes.batches import router as batches_router
from app.api.routes.decisions import email_router as email_events_router
from app.api.routes.decisions import router as decisions_router
from app.models import AuditEvent, BatchDecision, EmailEvent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("vendoriq")

# Initialize database tables (for local dev / testing)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="VendorIQ: AI-Powered Supplier Qualification & Batch Intelligence Platform Backend"
)

# Enable CORS for React/Vite frontend (owned by Developer 4)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health router at root level
app.include_router(health_router)

# API routers under /api
app.include_router(batches_router, prefix=settings.API_PREFIX)
app.include_router(decisions_router, prefix=settings.API_PREFIX)
app.include_router(email_events_router, prefix=settings.API_PREFIX)


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.APP_NAME} in {settings.ENVIRONMENT} mode.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.APP_NAME}.")
