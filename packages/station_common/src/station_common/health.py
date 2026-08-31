"""A ready-made health endpoint.

Mount it on any FastAPI app::

    from station_common import health_router
    app.include_router(health_router)

``GET /healthz`` then returns ``{"status": "ok"}`` with HTTP 200. Container
``HEALTHCHECK`` directives and Caddy's passive health checks hit this path.
"""

from __future__ import annotations

from fastapi import APIRouter

health_router = APIRouter(tags=["health"])


@health_router.get("/healthz", summary="Liveness/readiness probe")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
