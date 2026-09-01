import pytest
from fastapi.testclient import TestClient
from wordbook.main import app
from wordbook.models import RateLimited, SourceError, WordNotFound
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
        if w.casefold() == "limited":
            raise RateLimited(120)
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


def test_lookup_rate_limited_is_429_with_retry_after(client):
    r = client.get("/api/lookup", params={"language": "es", "word": "limited"})
    assert r.status_code == 429
    assert r.headers["retry-after"] == "120"
    detail = r.json()["detail"]
    assert detail["retry_after"] == 120
    assert detail["reset_in"] == "2 min"
    assert detail["reset_at"].endswith("+00:00")  # UTC ISO


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


# ---- manual entries -------------------------------------------------


def test_manual_create(client):
    r = client.post(
        "/api/entries",
        json={
            "language": "es",
            "word": "guagua",
            "senses": [
                {"text": "autobús"},
                {"text": "bebé", "part_of_speech": "n", "example": "la guagua llora"},
            ],
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["outcome"] == "created"
    entry = body["entry"]
    assert entry["source"] == "manual"
    assert [s["number"] for s in entry["senses"]] == [1, 2]
    assert entry["senses"][1]["part_of_speech"] == "n"
    assert entry["senses"][1]["examples"] == ["la guagua llora"]


def test_manual_update_keeps_added_at(client):
    client.post("/api/entries", json={"language": "es", "word": "g", "senses": [{"text": "one"}]})
    first = client.get("/api/dictionary/es/g").json()

    r = client.post(
        "/api/entries", json={"language": "es", "word": "g", "senses": [{"text": "two"}]}
    )
    assert r.status_code == 200
    assert r.json()["outcome"] == "updated"

    now = client.get("/api/dictionary/es/g").json()
    assert [s["text"] for s in now["senses"]] == ["two"]
    assert now["added_at"] == first["added_at"]


def test_manual_rejects_empty(client):
    assert (
        client.post("/api/entries", json={"language": "es", "word": "x", "senses": []}).status_code
        == 422
    )
    assert (
        client.post(
            "/api/entries", json={"language": "es", "word": "x", "senses": [{"text": "  "}]}
        ).status_code
        == 422
    )


def test_manual_overrides_a_bookmarked_entry(client):
    client.post("/api/dictionary", json={"language": "en", "word": "hello"})
    r = client.post(
        "/api/entries",
        json={"language": "en", "word": "hello", "senses": [{"text": "my own definition"}]},
    )
    assert r.status_code == 200
    entry = client.get("/api/dictionary/en/hello").json()
    assert entry["source"] == "manual"
    assert [s["text"] for s in entry["senses"]] == ["my own definition"]


def test_get_single_entry_404(client):
    assert client.get("/api/dictionary/es/nope").status_code == 404
