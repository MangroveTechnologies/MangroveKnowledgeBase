"""
FastAPI routers for API and UI endpoints.
"""

from .api import router as api_router
from .ui import router as ui_router

__all__ = ["api_router", "ui_router"]
