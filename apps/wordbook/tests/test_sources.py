import asyncio
import json
from pathlib import Path

import httpx
import pytest
from wordbook.models import SourceError, WordNotFound
from wordbook.settings import settings
from wordbook.sources import dictionaryapi, rae

FIXTURES = Path(__file__).parent / "fixtures"


def fx(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def run(coro):
    return asyncio.run(coro)


def mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


# ---- parsers -------------------------------------------------------------


def test_parse_en_hello():
    entry = dictionaryapi.parse(fx("en_hello.json"), "hello")
    assert (entry.word, entry.language, entry.source) == ("hello", "en", "dictionaryapi.dev")
    assert entry.source_url == "https://en.wiktionary.org/wiki/hello"
    assert "/həˈləʊ/" in entry.phonetics
    assert len(entry.senses) == 7  # noun 1 + verb 1 + interjection 5
    assert {s.part_of_speech for s in entry.senses} == {"noun", "verb", "interjection"}

    interjections = [s for s in entry.senses if s.part_of_speech == "interjection"]
    assert interjections[0].examples == ["Hello, everyone."]
    assert entry.senses[0].antonyms == []  # noun: nothing at either level
    assert any("goodbye" in s.antonyms for s in interjections)  # meaning-level fallthrough


def test_parse_es_sol():
    entry = rae.parse(fx("es_sol.json"), "sol")
    assert (entry.word, entry.language, entry.source) == ("sol", "es", "rae-api.com")
    assert entry.source_url == "https://dle.rae.es/sol"
    assert entry.etymology == "Del lat. sol, solis."
    assert len(entry.senses) == 9  # 6 + 1 + 1 + 1 across four homonym groups; locutions dropped

    first = entry.senses[0]
    assert first.number == 1
    assert first.part_of_speech == "nombre masculino"
    assert first.text.startswith("Estrella luminosa")
    assert first.examples
    assert entry.senses[1].synonyms == ["astro", "estrella"]


def test_parse_es_amar_verb():
    entry = rae.parse(fx("es_amar.json"), "amar")
    assert entry.senses[0].part_of_speech == "verbo transitivo"
    assert "querer1" in entry.senses[0].synonyms
    assert entry.senses[1].usage == "rare"


# ---- fetch (HTTP mapping) ---------------------------------------------------


def test_fetch_en_success():
    async def go():
        async with mock_client(lambda req: httpx.Response(200, json=fx("en_hello.json"))) as c:
            entry, raw = await dictionaryapi.fetch(c, "hello", settings=settings)
        assert entry.word == "hello"
        assert isinstance(raw, list)

    run(go())


def test_fetch_en_not_found():
    async def go():
        async with mock_client(lambda req: httpx.Response(404, json=fx("en_notfound.json"))) as c:
            with pytest.raises(WordNotFound) as exc:
                await dictionaryapi.fetch(c, "zzz", settings=settings)
        assert exc.value.suggestions == []

    run(go())


def test_fetch_en_server_error():
    async def go():
        async with mock_client(lambda req: httpx.Response(503, text="down")) as c:
            with pytest.raises(SourceError):
                await dictionaryapi.fetch(c, "hello", settings=settings)

    run(go())


def test_fetch_es_success_and_key_header():
    seen = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["auth"] = req.headers.get("x-api-key")
        return httpx.Response(200, json=fx("es_sol.json"))

    async def go():
        async with mock_client(handler) as c:
            entry, _raw = await rae.fetch(c, "sol", settings=settings)
        assert entry.word == "sol"
        assert seen["auth"] is None  # no key configured in tests

    run(go())


def test_fetch_es_not_found_passes_suggestions():
    body = {"ok": False, "error": "NOT_FOUND", "suggestions": ["solo", "sal"]}

    async def go():
        async with mock_client(lambda req: httpx.Response(404, json=body)) as c:
            with pytest.raises(WordNotFound) as exc:
                await rae.fetch(c, "sll", settings=settings)
        assert exc.value.suggestions == ["solo", "sal"]

    run(go())


def test_fetch_network_error_is_source_error():
    def boom(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    async def go():
        async with mock_client(boom) as c:
            with pytest.raises(SourceError):
                await dictionaryapi.fetch(c, "hello", settings=settings)

    run(go())
