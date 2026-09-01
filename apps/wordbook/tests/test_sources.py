import asyncio
import json
from pathlib import Path

import httpx
import pytest
from wordbook.models import RateLimited, SourceError, WordNotFound
from wordbook.settings import settings
from wordbook.sources import freedict, rae

FIXTURES = Path(__file__).parent / "fixtures"


def fx(name: str):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def run(coro):
    return asyncio.run(coro)


def mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _no_retry_delay(monkeypatch):
    # Keep the failure-path tests fast; the retry tests opt back in.
    monkeypatch.setattr(settings, "http_retries", 0)


# ---- parsers ----------------------------------------------------------


def test_parse_en_hello():
    entry = freedict.parse(fx("en_hello.json"), "hello")
    assert (entry.word, entry.language, entry.source) == ("hello", "en", "freedictionaryapi.com")
    assert entry.source_url == "https://en.wiktionary.org/wiki/hello"
    assert "/həˈləʊ/" in entry.phonetics
    assert len(entry.senses) == 7  # interjection 5 + noun 1 + verb 1
    assert {s.part_of_speech for s in entry.senses} == {"interjection", "noun", "verb"}

    first = entry.senses[0]
    assert first.part_of_speech == "interjection"
    assert first.examples == ["Hello, everyone."]
    assert first.antonyms == []
    assert entry.senses[3].domains == ["colloquial"]  # sense tags carry the register


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


def test_parse_es_tolerates_null_lists():
    # RAE sends null (not []) for a homonym group that only has locutions,
    # and can send null for `meanings` itself.
    payload = {
        "data": {
            "word": "pero",
            "meanings": [
                {"senses": [{"meaning_number": 1, "category": "noun", "description": "Fruto."}]},
                {"senses": None, "locutions": [{"expression": "pero que muy", "senses": []}]},
            ],
        }
    }
    entry = rae.parse(payload, "pero")
    assert [s.text for s in entry.senses] == ["Fruto."]
    assert rae.parse({"data": {"word": "x", "meanings": None}}, "x").senses == []


# ---- fetch (HTTP mapping) -------------------------------------------


def test_fetch_en_success():
    async def go():
        async with mock_client(lambda req: httpx.Response(200, json=fx("en_hello.json"))) as c:
            entry, raw = await freedict.fetch(c, "hello", settings=settings)
        assert entry.word == "hello"
        assert isinstance(raw, dict)

    run(go())


def test_fetch_en_not_found_is_200_with_empty_entries():
    body = {"word": "zzz", "entries": [], "source": {"url": "https://en.wiktionary.org"}}

    async def go():
        async with mock_client(lambda req: httpx.Response(200, json=body)) as c:
            with pytest.raises(WordNotFound) as exc:
                await freedict.fetch(c, "zzz", settings=settings)
        assert exc.value.suggestions == []

    run(go())


def test_fetch_en_server_error():
    async def go():
        async with mock_client(lambda req: httpx.Response(503, text="down")) as c:
            with pytest.raises(SourceError):
                await freedict.fetch(c, "hello", settings=settings)

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


def test_fetch_429_rate_limited_from_header(monkeypatch):
    monkeypatch.setattr(settings, "http_retries", 3)
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(429, headers={"Retry-After": "3600"}, json={"ok": False})

    async def go():
        async with mock_client(handler) as c:
            with pytest.raises(RateLimited) as exc:
                await rae.fetch(c, "sol", settings=settings)
        assert exc.value.retry_after == 3600
        assert calls["n"] == 1  # a 429 is not retried

    run(go())


def test_fetch_429_reads_retry_after_from_body():
    body = {"ok": False, "error": "RATE_LIMIT_EXCEEDED", "retry_after": 120}

    async def go():
        async with mock_client(lambda req: httpx.Response(429, json=body)) as c:
            with pytest.raises(RateLimited) as exc:
                await rae.fetch(c, "sol", settings=settings)
        assert exc.value.retry_after == 120

    run(go())


def test_fetch_network_error_is_source_error():
    def boom(req: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("no route")

    async def go():
        async with mock_client(boom) as c:
            with pytest.raises(SourceError):
                await freedict.fetch(c, "hello", settings=settings)

    run(go())


def test_fetch_retries_transient_failure(monkeypatch):
    monkeypatch.setattr(settings, "http_retries", 2)
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(503)
        return httpx.Response(200, json=fx("en_hello.json"))

    async def go():
        async with mock_client(handler) as c:
            entry, _raw = await freedict.fetch(c, "hello", settings=settings)
        assert entry.word == "hello"
        assert calls["n"] == 3

    run(go())


def test_read_timeout_is_not_retried(monkeypatch):
    monkeypatch.setattr(settings, "http_retries", 3)
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        raise httpx.ReadTimeout("stalled")

    async def go():
        async with mock_client(handler) as c:
            with pytest.raises(SourceError):
                await freedict.fetch(c, "hello", settings=settings)
        assert calls["n"] == 1  # fail fast, no retry

    run(go())


def test_fetch_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(settings, "http_retries", 2)
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    async def go():
        async with mock_client(handler) as c:
            with pytest.raises(SourceError):
                await freedict.fetch(c, "hello", settings=settings)
        assert calls["n"] == 3  # initial + 2 retries

    run(go())


def test_lookup_caches_not_found(monkeypatch):
    from wordbook import sources

    sources.clear_cache()
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(404, json={"ok": False, "error": "NOT_FOUND", "suggestions": None})

    async def go():
        async with mock_client(handler) as c:
            for _ in range(3):
                with pytest.raises(WordNotFound):
                    await sources.lookup("es", "zzzznope", client=c, settings=settings)
        assert calls["n"] == 1  # only the first miss hit the network

    run(go())


def test_lookup_does_not_cache_source_error(monkeypatch):
    from wordbook import sources

    sources.clear_cache()
    calls = {"n": 0}

    def handler(req: httpx.Request) -> httpx.Response:
        calls["n"] += 1
        return httpx.Response(503)

    async def go():
        async with mock_client(handler) as c:
            for _ in range(3):
                with pytest.raises(SourceError):
                    await sources.lookup("en", "flaky", client=c, settings=settings)
        assert calls["n"] == 3  # retried every time, never cached

    run(go())
