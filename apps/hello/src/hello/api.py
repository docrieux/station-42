"""hello's JSON API — the logic both UIs read from. Served under ``/api``."""

from __future__ import annotations

import platform

from fastapi import APIRouter

from hello.settings import settings


def hello_info() -> dict[str, str]:
    """The payload the desktop UI, the mobile UI and ``GET /api/`` all render."""
    return {
        "service": "hello",
        "message": settings.greeting,
        "host": platform.node(),
        "machine": platform.machine(),
    }


def make_api_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["hello"])

    @router.get("/", summary="Service + host info")
    def info() -> dict[str, str]:
        return hello_info()

    return router
