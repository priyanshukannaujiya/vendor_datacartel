"""
API Routers for VendorIQ.
"""
from app.routers.auth import router as auth_router
from app.routers.vendors import router as vendors_router
from app.routers.raw_materials import router as raw_materials_router
from app.routers.vendor_materials import router as vendor_materials_router
from app.routers.batches import router as batches_router
from app.routers.documents import router as documents_router
from app.routers.predictions import router as predictions_router
from app.routers.analytics import router as analytics_router
from app.routers.alerts import router as alerts_router
from app.routers.email_events import router as email_events_router
from app.routers.settings import router as settings_router

__all__ = [
    "auth_router",
    "vendors_router",
    "raw_materials_router",
    "vendor_materials_router",
    "batches_router",
    "documents_router",
    "predictions_router",
    "analytics_router",
    "alerts_router",
    "email_events_router",
    "settings_router",
]

