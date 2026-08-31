"""hello — the reference Station 42 app.

Deliberately tiny. It proves the whole chain end to end (uv workspace build ->
container -> Caddy route -> HTTPS from a Tailscale device) *and* demonstrates the
dual-UI standard every app follows:

  * ``/``        -> 302 to ``/d/`` or ``/m/`` by device (station_common.web)
  * ``/d/``      -> desktop page      ``/m/`` -> mobile page
  * ``/api/``    -> JSON, the shared logic
  * ``/healthz`` -> liveness probe

Copy it with ``just new-app <name>`` and build your real thing. See
``apps/CLAUDE.md`` and ``docs/dual-ui.md``.
"""

from __future__ import annotations

from fastapi import FastAPI

from hello.api import make_api_router
from hello.settings import settings
from hello.ui import make_ui_router
from station_common import configure_logging, health_router
from station_common.web import mount_dual_ui

configure_logging(settings.log_level)

app = FastAPI(title="hello")
app.include_router(health_router)
app.include_router(make_api_router())

desktop, mobile = mount_dual_ui(app, "hello")
app.include_router(make_ui_router(desktop, mobile))
