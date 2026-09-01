"""wordbook's behaviour + JSON API.

The service functions here are the single source of truth: the ``/api`` routes
below and the ``/d/`` `/m/`` handlers in :mod:`wordbook.ui` both call them, so
nothing is duplicated between the API and the two UIs (``docs/dual-ui.md``).

- ``GET  /api/lookup``            live search against a source (RAE / freedictionaryapi)
- ``GET  /api/dictionary``        the saved words for one language, sorted
- ``POST /api/dictionary``        bookmark a word (server re-fetches from the source)
- ``DELETE /api/dictionary/{language}/{word}``   remove a saved word
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from wordbook import store
from wordbook.models import Entry, RateLimited, SourceError, StoredEntry, WordNotFound
from wordbook.settings import settings
from wordbook.sources import PARSERS, lookup


class Language(StrEnum):
    es = "es"
    en = "en"


class Sort(StrEnum):
    alpha_asc = "alpha_asc"
    alpha_desc = "alpha_desc"
    added_asc = "added_asc"
    added_desc = "added_desc"


class BookmarkIn(BaseModel):
    language: Language
    word: str = Field(min_length=1)


# --------------------------------------------------------------------------- #
# Service layer — used by the routes below AND by wordbook.ui                 #
# --------------------------------------------------------------------------- #


def wordbook_info() -> dict[str, str]:
    """Payload for ``GET /api/``."""
    return {"service": "wordbook", "message": "wordbook API — see /docs"}


def _stored(row: sqlite3.Row) -> StoredEntry:
    """Re-parse a saved raw payload into a :class:`StoredEntry`."""
    entry = PARSERS[row["language"]](json.loads(row["raw"]), row["word"])
    return StoredEntry(**entry.model_dump(), added_at=row["added_at"])


async def search_word(language: str, word: str, *, client: Any) -> Entry:
    """Live lookup. Raises :class:`WordNotFound` / :class:`SourceError`."""
    entry, _raw = await lookup(language, word.strip(), client=client, settings=settings)
    return entry


async def bookmark_word(language: str, word: str, *, client: Any) -> tuple[bool, StoredEntry]:
    """Re-fetch from the source and save it. Returns ``(created, stored)``."""
    entry, raw = await lookup(language, word.strip(), client=client, settings=settings)
    created = await run_in_threadpool(
        store.upsert,
        word=entry.word,
        language=language,
        source=entry.source,
        raw=json.dumps(raw, ensure_ascii=False),
    )
    row = await run_in_threadpool(store.get_entry, language, entry.word)
    return created, _stored(row)


async def saved_entries(language: str, sort: str) -> list[StoredEntry]:
    rows = await run_in_threadpool(store.list_entries, language, sort)
    return [_stored(row) for row in rows]


async def is_saved(language: str, word: str) -> bool:
    row = await run_in_threadpool(store.get_entry, language, word)
    return row is not None


async def remove_word(language: str, word: str) -> bool:
    return await run_in_threadpool(store.delete_entry, language, word)


def _humanize(seconds: int) -> str:
    if seconds >= 3600:
        hours, rem = divmod(seconds, 3600)
        minutes = rem // 60
        return f"{hours}h {minutes}m" if minutes else f"{hours}h"
    if seconds >= 60:
        return f"{seconds // 60} min"
    return f"{seconds} s"


def _reset_info(retry_after: int | None) -> dict[str, Any]:
    """Turn a 'retry after N seconds' into fields the template can render.

    ``reset_at`` is a UTC ISO timestamp; the browser renders the local clock and
    a live countdown from it (see ``app.js``).
    """
    if not retry_after or retry_after <= 0:
        return {"retry_after": None, "reset_at": None, "reset_in": None}
    reset = (datetime.now(UTC) + timedelta(seconds=retry_after)).replace(microsecond=0)
    return {
        "retry_after": retry_after,
        "reset_at": reset.isoformat(),
        "reset_in": _humanize(retry_after),
    }


async def dictionary_page(*, language: str, sort: str, query: str, client: Any) -> dict[str, Any]:
    """Everything a ``/d/`` or ``/m/`` page needs, assembled once."""
    result: Entry | None = None
    error: dict[str, Any] | None = None
    saved = False
    if query:
        try:
            result = await search_word(language, query, client=client)
            saved = await is_saved(language, result.word)
        except WordNotFound as exc:
            error = {"kind": "not_found", "word": exc.word, "suggestions": exc.suggestions}
        except RateLimited as exc:
            error = {"kind": "rate_limited", "word": query, **_reset_info(exc.retry_after)}
        except SourceError:
            error = {"kind": "unavailable", "word": query, "suggestions": []}

    entries = await saved_entries(language, sort)
    return {
        "lang": language,
        "sort": sort,
        "query": query,
        "result": result,
        "saved": saved,
        "error": error,
        "entries": entries,
        "count": len(entries),
    }


# --------------------------------------------------------------------------- #
# HTTP routes — thin wrappers over the service layer                         #
# --------------------------------------------------------------------------- #


def _not_found(exc: WordNotFound) -> HTTPException:
    return HTTPException(status_code=404, detail={"word": exc.word, "suggestions": exc.suggestions})


def _unavailable(language: str) -> HTTPException:
    return HTTPException(status_code=502, detail=f"the {language} dictionary source is unavailable")


def _rate_limited(exc: RateLimited) -> HTTPException:
    return HTTPException(
        status_code=429,
        detail={"error": "rate_limited", **_reset_info(exc.retry_after)},
        headers={"Retry-After": str(exc.retry_after)} if exc.retry_after else None,
    )


def make_api_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["wordbook"])

    @router.get("/", summary="Service info")
    def info() -> dict[str, str]:
        return wordbook_info()

    @router.get("/lookup", summary="Look a word up in a live dictionary source")
    async def lookup_word(
        request: Request,
        language: Language,
        word: str = Query(min_length=1),
    ) -> Entry:
        try:
            return await search_word(language.value, word, client=request.app.state.http)
        except WordNotFound as exc:
            raise _not_found(exc) from exc
        except RateLimited as exc:
            raise _rate_limited(exc) from exc
        except SourceError as exc:
            raise _unavailable(language.value) from exc

    @router.get("/dictionary", summary="List the saved dictionary for one language")
    async def list_dictionary(language: Language, sort: Sort = Sort.added_desc) -> dict[str, Any]:
        entries = await saved_entries(language.value, sort.value)
        return {
            "language": language.value,
            "sort": sort.value,
            "count": len(entries),
            "entries": entries,
        }

    @router.post("/dictionary", summary="Bookmark a word into the dictionary")
    async def add_word(request: Request, body: BookmarkIn, response: Response) -> dict[str, Any]:
        try:
            created, stored = await bookmark_word(
                body.language.value, body.word, client=request.app.state.http
            )
        except WordNotFound as exc:
            raise _not_found(exc) from exc
        except RateLimited as exc:
            raise _rate_limited(exc) from exc
        except SourceError as exc:
            raise _unavailable(body.language.value) from exc
        response.status_code = 201 if created else 200
        return {"created": created, "entry": stored}

    @router.delete(
        "/dictionary/{language}/{word}",
        status_code=204,
        summary="Remove a saved word",
    )
    async def delete_word(language: Language, word: str) -> Response:
        if not await remove_word(language.value, word):
            raise HTTPException(status_code=404, detail="not in the dictionary")
        return Response(status_code=204)

    return router
