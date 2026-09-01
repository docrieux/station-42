"""Spanish source: rae-api.com (unofficial RAE / dle.rae.es).

``GET /api/words/<word>`` returns ``{ok, data: {word, meanings[], suggestions}}``.
Senses live at ``data.meanings[].senses[]``, grouped by homonym / etymology.
A 404 body is ``{ok: false, error: "NOT_FOUND", suggestions}`` (``suggestions``
may be ``null``). Idioms (``locutions``) and verb ``conjugations`` are left in the
raw payload and not flattened into senses.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from wordbook.models import Entry, Sense, SourceError, WordNotFound
from wordbook.settings import Settings
from wordbook.sources._http import get as http_get

SOURCE = "rae-api.com"

_CATEGORY = {
    "noun": "nombre",
    "verb": "verbo",
    "adjective": "adjetivo",
    "adverb": "adverbio",
    "pronoun": "pronombre",
    "article": "artículo",
    "preposition": "preposición",
    "conjunction": "conjunción",
    "interjection": "interjección",
}
_GENDER = {
    "masculine": "masculino",
    "feminine": "femenino",
    "masculine_and_feminine": "masculino y femenino",
}
_VERB = {
    "transitive": "transitivo",
    "intransitive": "intransitivo",
    "pronominal": "pronominal",
    "transitive_and_intransitive": "transitivo e intransitivo",
    "impersonal": "impersonal",
}


def _clean(value: Any) -> str | None:
    return value or None


def _rae_pos(sense: dict[str, Any]) -> str | None:
    parts = [_CATEGORY.get(sense.get("category"), sense.get("category"))]
    if sense.get("gender"):
        parts.append(_GENDER.get(sense["gender"], sense["gender"]))
    if sense.get("verb_category"):
        parts.append(_VERB.get(sense["verb_category"], sense["verb_category"]))
    label = " ".join(p for p in parts if p)
    return label or None


def _related(sense: dict[str, Any], key: str) -> list[str]:
    v2 = sense.get(f"{key}_v2")
    if v2:
        return [item["word"] for item in v2 if item.get("word")]
    return sense.get(key) or []


def parse(payload: dict[str, Any], word: str) -> Entry:
    """Normalize the rae-api.com envelope into an :class:`Entry`."""
    data = payload.get("data") or {}
    etymology: str | None = None
    senses: list[Sense] = []

    # RAE uses null (not just an absent key) for empty lists, e.g. a homonym
    # group that only carries `locutions` has `"senses": null`.
    for group in data.get("meanings") or []:
        if etymology is None:
            etymology = _clean((group.get("origin") or {}).get("raw"))
        for sense in group.get("senses") or []:
            senses.append(
                Sense(
                    number=sense.get("meaning_number"),
                    part_of_speech=_rae_pos(sense),
                    text=sense.get("description") or sense.get("raw", ""),
                    examples=sense.get("examples") or [],
                    synonyms=_related(sense, "synonyms"),
                    antonyms=_related(sense, "antonyms"),
                    usage=_clean(sense.get("usage")),
                    regions=[r["name"] for r in sense.get("regions") or [] if r.get("name")],
                    domains=sense.get("fields") or [],
                )
            )

    return Entry(
        word=data.get("word", word),
        language="es",
        source=SOURCE,
        source_url=f"https://dle.rae.es/{quote(word)}",
        etymology=etymology,
        senses=senses,
    )


async def fetch(client: httpx.AsyncClient, word: str, *, settings: Settings) -> tuple[Entry, Any]:
    url = f"{settings.rae_base_url}/api/words/{quote(word)}"
    headers = {"X-API-Key": settings.rae_api_key} if settings.rae_api_key else None
    response = await http_get(client, url, headers=headers, retries=settings.http_retries)

    if response.status_code == 404:
        body = _safe_json(response)
        raise WordNotFound(word, body.get("suggestions") if isinstance(body, dict) else None)
    if response.status_code >= 400:
        raise SourceError(f"rae-api.com returned {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise SourceError("rae-api.com returned a non-JSON response") from exc
    if not isinstance(payload, dict) or not payload.get("ok") or "data" not in payload:
        raise WordNotFound(word)
    return parse(payload, word), payload


def _safe_json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return {}
