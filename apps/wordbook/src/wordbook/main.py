"""wordbook — a Station 42 service.

Replace the endpoints with your own. The shape every app keeps (see
``apps/CLAUDE.md`` and ``docs/dual-ui.md``):

  * ``settings.py`` — ``Settings(BaseAppSettings)`` with the ``WORDBOOK_`` prefix
  * ``api.py``      — the logic, mounted under ``/api``
  * ``ui.py``       — thin desktop (``/d/``) and mobile (``/m/``) handlers
  * ``main.py``     — logging + ``health_router`` + the routers + ``mount_dual_ui``

Routes: ``/`` redirects by device to ``/d/`` or ``/m/``; ``/api/...`` is JSON;
``/healthz`` is the probe; ``/static/...`` serves ``web/static/``.
"""

from __future__ import annotations

from fastapi import FastAPI

from station_common import configure_logging, health_router
from station_common.web import mount_dual_ui
from wordbook.api import make_api_router
from wordbook.settings import settings
from wordbook.ui import make_ui_router

configure_logging(settings.log_level)

app = FastAPI(title="wordbook")
app.include_router(health_router)
app.include_router(make_api_router())

desktop, mobile = mount_dual_ui(app, "wordbook")
app.include_router(make_ui_router(desktop, mobile))
