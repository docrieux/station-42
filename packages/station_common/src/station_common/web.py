"""Dual desktop / mobile UI wiring shared by every Station 42 app.

An app calls :func:`mount_dual_ui` once. It registers the ``/`` device redirect
and the ``/static`` mount and returns the two Jinja2 environments (one per UI).
The app then adds its own ``/d/`` and ``/m/`` routes using those environments.

See ``apps/CLAUDE.md`` and ``docs/dual-ui.md`` for the full contract.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path
from urllib.parse import urlencode

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

__all__ = ["UI_COOKIE", "is_mobile", "mount_dual_ui"]

# Query param and cookie an app/user can set to force one UI (``d`` or ``m``).
UI_COOKIE = "ui"
_UI_COOKIE_MAX_AGE = 60 * 60 * 24 * 365

_MOBILE_RE = re.compile(
    r"Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini|Mobile|Silk",
    re.IGNORECASE,
)


def is_mobile(request_or_ua: Request | str) -> bool:
    """True if the User-Agent looks like a phone/tablet. A hint, not a guarantee."""
    ua = request_or_ua
    if isinstance(ua, Request):
        ua = ua.headers.get("user-agent", "")
    return bool(_MOBILE_RE.search(ua or ""))


def _package_dir(import_name: str) -> Path:
    spec = importlib.util.find_spec(import_name)
    if spec is None or spec.origin is None:
        raise ModuleNotFoundError(f"cannot locate package {import_name!r}")
    return Path(spec.origin).parent


def mount_dual_ui(app: FastAPI, import_name: str) -> tuple[Jinja2Templates, Jinja2Templates]:
    """Wire ``/`` (device redirect) and ``/static`` for *app*.

    ``import_name`` is the app's top-level package (e.g. ``"hello"``). Its
    ``web/`` directory must contain ``static/`` and
    ``templates/{shared,desktop,mobile}/``.

    Returns ``(desktop, mobile)`` Jinja2 environments — register ``/d/`` and
    ``/m/`` routes with them. ``templates/shared/`` is on both search paths.
    """
    web = _package_dir(import_name) / "web"
    shared = str(web / "templates" / "shared")
    desktop = Jinja2Templates(directory=[str(web / "templates" / "desktop"), shared])
    mobile = Jinja2Templates(directory=[str(web / "templates" / "mobile"), shared])

    app.mount("/static", StaticFiles(directory=str(web / "static")), name="static")

    @app.get("/", include_in_schema=False)
    def _root(request: Request) -> RedirectResponse:
        choice = request.query_params.get("ui") or request.cookies.get(UI_COOKIE) or ""
        if choice not in ("d", "m"):
            choice = "m" if is_mobile(request) else "d"

        kept = [(k, v) for k, v in request.query_params.multi_items() if k != "ui"]
        target = f"/{choice}/" + (f"?{urlencode(kept)}" if kept else "")

        response = RedirectResponse(target, status_code=302)
        response.set_cookie(UI_COOKIE, choice, max_age=_UI_COOKIE_MAX_AGE, samesite="lax")
        return response

    return desktop, mobile
