"""wordbook's JSON API — the logic both UIs read from. Served under ``/api``.

- ``GET  /api/lookup``            live search against a source (RAE / dictionaryapi)
- ``GET  /api/dictionary``        the saved words for one language, sorted
- ``POST /api/dictionary``        bookmark a word (server re-fetches from the source)
- ``DELETE /api/dictionary/{language}/{word}``   remove a saved word
"""

from __future__ import annotations

import json
import sqlite3
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from wordbook import store
from wordbook.models import Entry, SourceError, StoredEntry, WordNotFound
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


def wordbook_info() -> dict[str, str]:
    """Payload for ``GET /api/`` and the (placeholder) dual-UI templates."""
    return {"service": "wordbook", "message": "wordbook API — see /docs"}


def _stored(row: sqlite3.Row) -> StoredEntry:
    """Re-parse a saved raw payload into a :class:`StoredEntry`."""
    entry = PARSERS[row["language"]](json.loads(row["raw"]), row["word"])
    return StoredEntry(**entry.model_dump(), added_at=row["added_at"])


def _not_found(exc: WordNotFound) -> HTTPException:
    return HTTPException(status_code=404, detail={"word": exc.word, "suggestions": exc.suggestions})


def _unavailable(language: str) -> HTTPException:
    return HTTPException(status_code=502, detail=f"the {language} dictionary source is unavailable")


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
            entry, _raw = await lookup(
                language.value, word.strip(), client=request.app.state.http, settings=settings
            )
        except WordNotFound as exc:
            raise _not_found(exc) from exc
        except SourceError as exc:
            raise _unavailable(language.value) from exc
        return entry

    @router.get("/dictionary", summary="List the saved dictionary for one language")
    async def list_dictionary(
        language: Language,
        sort: Sort = Sort.added_desc,
    ) -> dict[str, Any]:
        rows = await run_in_threadpool(store.list_entries, language.value, sort.value)
        entries = [_stored(row) for row in rows]
        return {
            "language": language.value,
            "sort": sort.value,
            "count": len(entries),
            "entries": entries,
        }

    @router.post("/dictionary", summary="Bookmark a word into the dictionary")
    async def add_word(request: Request, body: BookmarkIn, response: Response) -> dict[str, Any]:
        try:
            entry, raw = await lookup(
                body.language.value,
                body.word.strip(),
                client=request.app.state.http,
                settings=settings,
            )
        except WordNotFound as exc:
            raise _not_found(exc) from exc
        except SourceError as exc:
            raise _unavailable(body.language.value) from exc

        created = await run_in_threadpool(
            store.upsert,
            word=entry.word,
            language=body.language.value,
            source=entry.source,
            raw=json.dumps(raw, ensure_ascii=False),
        )
        response.status_code = 201 if created else 200
        row = await run_in_threadpool(store.get_entry, body.language.value, entry.word)
        return {"created": created, "entry": _stored(row)}

    @router.delete(
        "/dictionary/{language}/{word}",
        status_code=204,
        summary="Remove a saved word",
    )
    async def delete_word(language: Language, word: str) -> Response:
        deleted = await run_in_threadpool(store.delete_entry, language.value, word)
        if not deleted:
            raise HTTPException(status_code=404, detail="not in the dictionary")
        return Response(status_code=204)

    return router
