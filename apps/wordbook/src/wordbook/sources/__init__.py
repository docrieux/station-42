"""Dictionary sources: one per language, behind a small in-process TTL cache.

``lookup`` is what the API calls for a live search *and* for a bookmark, so the
cache turns "search then bookmark the same word" into a single upstream request
and softens rae-api.com's 100-req/day free tier. It also caches a confirmed
"not found" (a stable fact) so repeat searches of a missing word are instant. A
:class:`~wordbook.models.SourceError` is **not** cached, so the app recovers as
soon as the upstream is healthy again. Per process; cleared on restart (and by
:func:`clear_cache` in tests).
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from wordbook.models import Entry, Language, WordNotFound
from wordbook.settings import Settings
from wordbook.sources import freedict, rae

_FETCHERS = {"es": rae.fetch, "en": freedict.fetch}

#: Re-parse a stored raw payload back into an :class:`Entry`.
PARSERS = {"es": rae.parse, "en": freedict.parse}

# key -> (expires_at, kind, payload); kind is "ok" -> (entry, raw) or "notfound" -> suggestions
_cache: dict[tuple[str, str], tuple[float, str, Any]] = {}


def clear_cache() -> None:
    _cache.clear()


async def lookup(
    language: Language, word: str, *, client: httpx.AsyncClient, settings: Settings
) -> tuple[Entry, Any]:
    """Return ``(entry, raw_payload)`` for *word*, from cache when fresh.

    Raises :class:`wordbook.models.WordNotFound` / :class:`~wordbook.models.SourceError`.
    """
    key = (language, word.casefold())
    cached = _cache.get(key)
    if cached and cached[0] > time.monotonic():
        _, kind, payload = cached
        if kind == "ok":
            return payload
        raise WordNotFound(word, payload)

    try:
        entry, raw = await _FETCHERS[language](client, word, settings=settings)
    except WordNotFound as exc:
        _cache[key] = (time.monotonic() + settings.cache_ttl, "notfound", exc.suggestions)
        raise

    _cache[key] = (time.monotonic() + settings.cache_ttl, "ok", (entry, raw))
    return entry, raw
