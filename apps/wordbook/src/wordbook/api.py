"""wordbook's JSON API — the logic both UIs read from. Served under ``/api``."""

from __future__ import annotations

from fastapi import APIRouter

from wordbook.settings import settings


def wordbook_info() -> dict[str, str]:
    """The payload the desktop UI, the mobile UI and ``GET /api/`` all render."""
    return {"service": "wordbook", "message": settings.greeting}


def make_api_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["wordbook"])

    @router.get("/", summary="Service info")
    def info() -> dict[str, str]:
        return wordbook_info()

    return router
