"""English source: dictionaryapi.dev (Free Dictionary API), keyless.

``GET /api/v2/entries/en/<word>`` returns a JSON array of entry objects. Senses
live at ``[].meanings[].definitions[]``; a 404 body is ``{title, message,
resolution}``.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from wordbook.models import Entry, Sense, SourceError, WordNotFound
from wordbook.settings import Settings

SOURCE = "dictionaryapi.dev"


def parse(payload: list[dict[str, Any]], word: str) -> Entry:
    """Normalize the dictionaryapi.dev array into an :class:`Entry`."""
    phonetics: list[str] = []
    senses: list[Sense] = []
    etymology: str | None = None
    source_url: str | None = None

    for entry in payload:
        for text in [entry.get("phonetic"), *(p.get("text") for p in entry.get("phonetics", []))]:
            if text and text not in phonetics:
                phonetics.append(text)
        if etymology is None and entry.get("origin"):
            etymology = entry["origin"]
        urls = entry.get("sourceUrls") or []
        if source_url is None and urls:
            source_url = urls[0]

        for meaning in entry.get("meanings", []):
            pos = meaning.get("partOfSpeech")
            for definition in meaning.get("definitions", []):
                example = definition.get("example")
                senses.append(
                    Sense(
                        number=len(senses) + 1,
                        part_of_speech=pos,
                        text=definition["definition"],
                        examples=[example] if example else [],
                        synonyms=definition.get("synonyms") or meaning.get("synonyms") or [],
                        antonyms=definition.get("antonyms") or meaning.get("antonyms") or [],
                    )
                )

    return Entry(
        word=payload[0].get("word", word) if payload else word,
        language="en",
        source=SOURCE,
        source_url=source_url,
        phonetics=phonetics,
        etymology=etymology,
        senses=senses,
    )


async def fetch(client: httpx.AsyncClient, word: str, *, settings: Settings) -> tuple[Entry, Any]:
    url = f"{settings.dictionaryapi_base_url}/api/v2/entries/en/{quote(word)}"
    try:
        response = await client.get(url)
    except httpx.RequestError as exc:  # DNS, connection, timeout
        raise SourceError(str(exc)) from exc

    if response.status_code == 404:
        raise WordNotFound(word)
    if response.status_code == 429 or response.status_code >= 500:
        raise SourceError(f"dictionaryapi.dev returned {response.status_code}")
    response.raise_for_status()

    payload = response.json()
    if not isinstance(payload, list) or not payload:
        raise WordNotFound(word)
    return parse(payload, word), payload
