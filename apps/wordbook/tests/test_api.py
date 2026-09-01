import pytest
from fastapi.testclient import TestClient
from wordbook.main import app
from wordbook.models import SourceError, WordNotFound
from wordbook.sources import freedict


def _fake_en_payload(word: str) -> dict:
    return {
        "word": word,
        "entries": [
            {
                "partOfSpeech": "noun",
                "pronunciations": [{"type": "ipa", "text": "/x/", "tags": []}],
                "senses": [{"definition": f"def of {word}", "examples": ["an example"]}],
            }
        ],
        "source": {"url": f"https://en.wiktionary.org/wiki/{word}"},
    }


@pytest.fixture
def client(monkeypatch):
    async def fake_lookup(language, word, *, client, settings):
        w = word.strip()
        if w.casefold() in {"zzz", "notaword"}:
            raise WordNotFound(w, ["zza", "zzb"])
        if w.casefold() == "boom":
            raise SourceError("source down")
        raw = _fake_en_payload(w)
        return freedict.parse(raw, w), raw

    monkeypatch.setattr("wordbook.api.lookup", fake_lookup)
    with TestClient(app) as c:
        yield c


def test_healthz(client):
    assert client.get("/healthz").json() == {"status": "ok"}


def test_api_info(client):
    assert client.get("/api/").json()["service"] == "wordbook"


def test_lookup_ok(client):
    body = client.get("/api/lookup", params={"language": "en", "word": "hello"}).json()
    assert body["word"] == "hello"
    assert body["language"] == "en"
    assert body["senses"][0]["text"] == "def of hello"


def test_lookup_not_found_returns_suggestions(client):
    r = client.get("/api/lookup", params={"language": "en", "word": "zzz"})
    assert r.status_code == 404
    assert r.json()["detail"] == {"word": "zzz", "suggestions": ["zza", "zzb"]}


def test_lookup_source_error_is_502(client):
    r = client.get("/api/lookup", params={"language": "en", "word": "boom"})
    assert r.status_code == 502


def test_lookup_rejects_unknown_language(client):
    assert client.get("/api/lookup", params={"language": "fr", "word": "x"}).status_code == 422


def test_bookmark_creates_then_is_idempotent(client):
    first = client.post("/api/dictionary", json={"language": "en", "word": "hello"})
    assert first.status_code == 201
    assert first.json()["created"] is True
    assert first.json()["entry"]["word"] == "hello"

    again = client.post("/api/dictionary", json={"language": "en", "word": "hello"})
    assert again.status_code == 200
    assert again.json()["created"] is False

    listing = client.get("/api/dictionary", params={"language": "en"}).json()
    assert listing["count"] == 1


def test_bookmark_unknown_word_is_404(client):
    r = client.post("/api/dictionary", json={"language": "en", "word": "zzz"})
    assert r.status_code == 404


def test_dictionary_alpha_sort(client):
    for word in ("casa", "ave", "zorro"):
        client.post("/api/dictionary", json={"language": "en", "word": word})

    asc = client.get("/api/dictionary", params={"language": "en", "sort": "alpha_asc"}).json()
    assert [e["word"] for e in asc["entries"]] == ["ave", "casa", "zorro"]

    desc = client.get("/api/dictionary", params={"language": "en", "sort": "alpha_desc"}).json()
    assert [e["word"] for e in desc["entries"]] == ["zorro", "casa", "ave"]


def test_dictionary_rejects_bad_sort(client):
    r = client.get("/api/dictionary", params={"language": "en", "sort": "nope"})
    assert r.status_code == 422


def test_delete(client):
    client.post("/api/dictionary", json={"language": "en", "word": "hello"})
    assert client.delete("/api/dictionary/en/hello").status_code == 204
    assert client.delete("/api/dictionary/en/hello").status_code == 404
