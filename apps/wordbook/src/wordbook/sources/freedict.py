"""English source: freedictionaryapi.com (Wiktionary-derived), keyless.

``GET /api/v1/entries/en/<word>`` returns ``{word, entries[], source}``. Each
``entries[]`` item is one part of speech; its ``senses[]`` carry the
definitions. A word with no data comes back as HTTP 200 with ``entries: []``.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from wordbook.models import Entry, Sense, SourceError, WordNotFound
from wordbook.settings import Settings
from wordbook.sources._http import get as http_get

SOURCE = "freedictionaryapi.com"


def _collect(acc: list[Sense], sense: dict[str, Any], pos: str | None) -> None:
    text = sense.get("definition")
    if text:
        acc.append(
            Sense(
                number=len(acc) + 1,
                part_of_speech=pos,
                text=text,
                examples=sense.get("examples") or [],
                synonyms=sense.get("synonyms") or [],
                antonyms=sense.get("antonyms") or [],
                domains=sense.get("tags") or [],  # "colloquial", "countable", ...
            )
        )
    for sub in sense.get("subsenses") or []:
        _collect(acc, sub, pos)


def parse(payload: dict[str, Any], word: str) -> Entry:
    """Normalize the freedictionaryapi.com object into an :class:`Entry`."""
    phonetics: list[str] = []
    senses: list[Sense] = []

    for entry in payload.get("entries") or []:
        pos = entry.get("partOfSpeech")
        for pron in entry.get("pronunciations") or []:
            text = pron.get("text")
            if pron.get("type") == "ipa" and text and text not in phonetics:
                phonetics.append(text)
        for sense in entry.get("senses") or []:
            _collect(senses, sense, pos)

    return Entry(
        word=payload.get("word", word),
        language="en",
        source=SOURCE,
        source_url=(payload.get("source") or {}).get("url"),
        phonetics=phonetics,
        senses=senses,
    )


async def fetch(client: httpx.AsyncClient, word: str, *, settings: Settings) -> tuple[Entry, Any]:
    url = f"{settings.freedict_base_url}/api/v1/entries/en/{quote(word)}"
    response = await http_get(client, url, retries=settings.http_retries)

    if response.status_code == 404:
        raise WordNotFound(word)
    if response.status_code >= 400:
        raise SourceError(f"freedictionaryapi.com returned {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise SourceError("freedictionaryapi.com returned a non-JSON response") from exc
    if not isinstance(payload, dict) or not payload.get("entries"):
        raise WordNotFound(word)  # 200 with entries: [] means "no such word"
    return parse(payload, word), payload
