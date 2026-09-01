"""Dictionary sources, behind a two-layer cache.

L1 is a small in-process TTL cache (``settings.cache_ttl``) that collapses a
search + the bookmark that follows it into one call. L2 is the ``lookup_cache``
table in SQLite: a successful lookup is stored **forever** (source dictionaries
don't change), so a source is only ever hit for a word's *first* lookup — that
is what keeps rae-api.com's 100-req/day free tier spent on new words only. A
confirmed "not found" is trusted for ``settings.lookup_cache_days`` then
re-checked. :class:`SourceError` / :class:`RateLimited` are never cached, so the
app recovers the moment the source is healthy.
"""

from __future__ import annotations

import contextlib
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx
from starlette.concurrency import run_in_threadpool

from wordbook import store
from wordbook.models import Entry, Language, WordNotFound
from wordbook.settings import Settings
from wordbook.sources import freedict, rae

_FETCHERS = {"es": rae.fetch, "en": freedict.fetch}

#: Re-parse a stored raw payload back into an :class:`Entry`.
PARSERS = {"es": rae.parse, "en": freedict.parse}

# L1: key -> (expires_at_monotonic, kind, payload); kind "ok" -> (entry, raw),
# "notfound" -> the suggestions list.
_cache: dict[tuple[str, str], tuple[float, str, Any]] = {}


def clear_cache() -> None:
    """Drop both cache layers. Test helper."""
    _cache.clear()
    with contextlib.suppress(Exception):
        store.cache_clear()  # no-op if the store isn't initialised yet


def _payload_from_row(language: str, word: str, row: Any) -> tuple[str, Any]:
    """(kind, payload) from an L2 row, in the same shape L1 stores."""
    if row["kind"] == "ok":
        raw = json.loads(row["raw"])
        return "ok", (PARSERS[language](raw, word), raw)
    return "notfound", json.loads(row["raw"] or "[]")


def _l2_fresh(row: Any, settings: Settings) -> bool:
    if row["kind"] == "ok":
        return True
    cutoff = datetime.now(UTC) - timedelta(days=settings.lookup_cache_days)
    try:
        return datetime.fromisoformat(row["cached_at"]) > cutoff
    except ValueError:
        return False


def _deliver(word: str, kind: str, payload: Any) -> tuple[Entry, Any]:
    if kind == "ok":
        return payload  # (entry, raw)
    raise WordNotFound(word, payload if isinstance(payload, list) else [])


async def lookup(
    language: Language, word: str, *, client: httpx.AsyncClient, settings: Settings
) -> tuple[Entry, Any]:
    """Return ``(entry, raw_payload)`` for *word*, from cache when possible.

    Raises :class:`wordbook.models.WordNotFound` / :class:`~wordbook.models.SourceError`.
    """
    cf = word.casefold()
    key = (language, cf)

    hit = _cache.get(key)
    if hit and hit[0] > time.monotonic():
        return _deliver(word, hit[1], hit[2])

    row = await run_in_threadpool(store.cache_get, language, cf)
    if row is not None and _l2_fresh(row, settings):
        kind, payload = _payload_from_row(language, word, row)
        _cache[key] = (time.monotonic() + settings.cache_ttl, kind, payload)
        return _deliver(word, kind, payload)

    try:
        entry, raw = await _FETCHERS[language](client, word, settings=settings)
    except WordNotFound as exc:
        _cache[key] = (time.monotonic() + settings.cache_ttl, "notfound", exc.suggestions)
        await run_in_threadpool(
            store.cache_put,
            language=language,
            word=cf,
            kind="notfound",
            raw=json.dumps(exc.suggestions),
        )
        raise

    _cache[key] = (time.monotonic() + settings.cache_ttl, "ok", (entry, raw))
    await run_in_threadpool(
        store.cache_put,
        language=language,
        word=cf,
        kind="ok",
        source=entry.source,
        raw=json.dumps(raw, ensure_ascii=False),
    )
    return entry, raw
