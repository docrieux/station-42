"""wordbook's two front-ends.

Thin handlers: they parse request params, call the service functions in
:mod:`wordbook.api` (the same ones ``/api`` uses), and render a template. Desktop
and mobile differ only in which ``Jinja2Templates`` env is used.

Routes:
  GET  /d/  /m/            the page (``?q=`` search, ``?lang=``, ``?sort=``,
                           ``?partial=result|list`` for the JS fragment swap)
  POST /d/bookmark /m/...  save the searched word          (no-JS fallback)
  POST /d/remove   /m/...  drop a saved word               (no-JS fallback)
"""

from __future__ import annotations

from contextlib import suppress
from enum import StrEnum
from urllib.parse import parse_qs

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from wordbook.api import Language, Sort, bookmark_word, dictionary_page, remove_word
from wordbook.models import SourceError, WordNotFound

_DEFAULT_LANG = "es"
_DEFAULT_SORT = "alpha_asc"
_COOKIE_MAX_AGE = 60 * 60 * 24 * 365
_PARTIALS = {"result": "_result.html", "list": "_dictlist.html"}


def _one_of(value: str | None, allowed: type[StrEnum], fallback: str) -> str:
    """Return ``value`` if it is a valid member value, else ``fallback``."""
    try:
        return allowed(value).value
    except ValueError:
        return fallback


def _pick_lang(request: Request, *, form_value: str | None = None) -> str:
    raw = form_value or request.query_params.get("lang") or request.cookies.get("wb_lang")
    return _one_of(raw, Language, _DEFAULT_LANG)


def _pick_sort(request: Request) -> str:
    raw = request.query_params.get("sort") or request.cookies.get("wb_sort")
    return _one_of(raw, Sort, _DEFAULT_SORT)


async def _form(request: Request) -> dict[str, str]:
    """Parse an ``application/x-www-form-urlencoded`` body without python-multipart."""
    body = (await request.body()).decode("utf-8")
    return {key: values[0] for key, values in parse_qs(body).items()}


def make_ui_router(desktop: Jinja2Templates, mobile: Jinja2Templates) -> APIRouter:
    router = APIRouter(include_in_schema=False)

    async def _render(templates: Jinja2Templates, prefix: str, request: Request) -> HTMLResponse:
        lang = _pick_lang(request)
        sort = _pick_sort(request)
        query = (request.query_params.get("q") or "").strip()
        template = _PARTIALS.get(request.query_params.get("partial", ""), "index.html")

        data = await dictionary_page(
            language=lang, sort=sort, query=query, client=request.app.state.http
        )
        data["prefix"] = prefix

        response = templates.TemplateResponse(request, template, data)
        response.set_cookie("wb_lang", lang, max_age=_COOKIE_MAX_AGE, samesite="lax")
        response.set_cookie("wb_sort", sort, max_age=_COOKIE_MAX_AGE, samesite="lax")
        return response

    async def _bookmark(prefix: str, request: Request) -> RedirectResponse:
        form = await _form(request)
        word = form.get("word", "").strip()
        lang = _pick_lang(request, form_value=form.get("lang") or None)
        if word:
            # A failed lookup is fine here: the redirect re-runs the search and
            # the page shows the not-found / unavailable card.
            with suppress(WordNotFound, SourceError):
                await bookmark_word(lang, word, client=request.app.state.http)
        return RedirectResponse(f"{prefix}/?lang={lang}&q={word}", status_code=303)

    async def _remove(prefix: str, request: Request) -> RedirectResponse:
        form = await _form(request)
        word = form.get("word", "").strip()
        lang = _pick_lang(request, form_value=form.get("lang") or None)
        if word:
            await remove_word(lang, word)
        return RedirectResponse(f"{prefix}/?lang={lang}", status_code=303)

    @router.get("/d/", response_class=HTMLResponse)
    async def desktop_page(request: Request) -> HTMLResponse:
        return await _render(desktop, "/d", request)

    @router.get("/m/", response_class=HTMLResponse)
    async def mobile_page(request: Request) -> HTMLResponse:
        return await _render(mobile, "/m", request)

    @router.post("/d/bookmark")
    async def desktop_bookmark(request: Request) -> RedirectResponse:
        return await _bookmark("/d", request)

    @router.post("/m/bookmark")
    async def mobile_bookmark(request: Request) -> RedirectResponse:
        return await _bookmark("/m", request)

    @router.post("/d/remove")
    async def desktop_remove(request: Request) -> RedirectResponse:
        return await _remove("/d", request)

    @router.post("/m/remove")
    async def mobile_remove(request: Request) -> RedirectResponse:
        return await _remove("/m", request)

    return router
