"""
API Routers for VendorIQ.
"""
from app.routers.auth import router as auth_router
from app.routers.vendors import router as vendors_router
from app.routers.raw_materials import router as raw_materials_router
from app.routers.vendor_materials import router as vendor_materials_router
from app.routers.batches import router as batches_router

__all__ = [
    "auth_router",
    "vendors_router",
    "raw_materials_router",
    "vendor_materials_router",
    "batches_router",
]
