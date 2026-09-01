"""Dictionary sources: one per language, behind a small in-process TTL cache.

``lookup`` is what the API calls for a live search *and* for a bookmark, so the
cache turns "search then bookmark the same word" into a single upstream request
and softens rae-api.com's 100-req/day free tier. The cache is per process and is
cleared on restart; :func:`clear_cache` exists for tests.
"""

from __future__ import annotations

import time
from typing import Any

import httpx

from wordbook.models import Entry, Language
from wordbook.settings import Settings
from wordbook.sources import dictionaryapi, rae

_FETCHERS = {"es": rae.fetch, "en": dictionaryapi.fetch}

#: Re-parse a stored raw payload back into an :class:`Entry`.
PARSERS = {"es": rae.parse, "en": dictionaryapi.parse}

_cache: dict[tuple[str, str], tuple[float, Entry, Any]] = {}


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
        return cached[1], cached[2]

    entry, raw = await _FETCHERS[language](client, word, settings=settings)
    _cache[key] = (time.monotonic() + settings.cache_ttl, entry, raw)
    return entry, raw
