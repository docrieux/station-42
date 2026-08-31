"""appname's two front-ends. Thin: fetch via :func:`appname_info`, render a template."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from appname.api import appname_info


def make_ui_router(desktop: Jinja2Templates, mobile: Jinja2Templates) -> APIRouter:
    router = APIRouter(include_in_schema=False)

    @router.get("/d/", response_class=HTMLResponse)
    def desktop_index(request: Request) -> HTMLResponse:
        return desktop.TemplateResponse(request, "index.html", {"info": appname_info()})

    @router.get("/m/", response_class=HTMLResponse)
    def mobile_index(request: Request) -> HTMLResponse:
        return mobile.TemplateResponse(request, "index.html", {"info": appname_info()})

    return router
