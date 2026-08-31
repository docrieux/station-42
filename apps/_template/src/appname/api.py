"""appname's JSON API — the logic both UIs read from. Served under ``/api``."""

from __future__ import annotations

from fastapi import APIRouter

from appname.settings import settings


def appname_info() -> dict[str, str]:
    """The payload the desktop UI, the mobile UI and ``GET /api/`` all render."""
    return {"service": "appname", "message": settings.greeting}


def make_api_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["appname"])

    @router.get("/", summary="Service info")
    def info() -> dict[str, str]:
        return appname_info()

    return router
