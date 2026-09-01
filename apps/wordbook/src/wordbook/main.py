"""wordbook — a modifiable bilingual dictionary for Station 42.

Search a word in Spanish (rae-api.com) or English (dictionaryapi.dev), see its
definition blocks, and bookmark it into a two-section personal dictionary that
can be re-sorted alphabetically or by time added.

Shape (see ``apps/CLAUDE.md`` / ``docs/dual-ui.md``):

  * ``settings.py`` — ``Settings(BaseAppSettings)`` with the ``WORDBOOK_`` prefix
  * ``models.py``   — the normalized ``Entry`` / ``Sense`` shape
  * ``store.py``    — SQLite persistence under ``/data``
  * ``sources/``    — one client + parser per language, behind a TTL cache
  * ``api.py``      — the ``/api`` routes both UIs read from
  * ``ui.py``       — thin desktop (``/d/``) and mobile (``/m/``) handlers
  * ``main.py``     — logging + lifespan + ``health_router`` + routers + ``mount_dual_ui``

Routes: ``/`` redirects by device to ``/d/`` or ``/m/``; ``/api/...`` is JSON;
``/healthz`` is the probe; ``/static/...`` serves ``web/static/``.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from station_common import configure_logging, health_router
from station_common.web import mount_dual_ui
from wordbook import store
from wordbook.api import make_api_router
from wordbook.settings import settings
from wordbook.ui import make_ui_router

configure_logging(settings.log_level)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    store.init_db(settings.db_path)
    app.state.http = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.http_timeout, connect=4.0),
        headers={"user-agent": "station42-wordbook"},
        # Don't reuse connections: a source that stalls mid-response can otherwise
        # poison a pooled keep-alive connection and every later request with it.
        limits=httpx.Limits(max_keepalive_connections=0),
    )
    try:
        yield
    finally:
        await app.state.http.aclose()


app = FastAPI(title="wordbook", lifespan=lifespan)
app.include_router(health_router)
app.include_router(make_api_router())

desktop, mobile = mount_dual_ui(app, "wordbook")
app.include_router(make_ui_router(desktop, mobile))
